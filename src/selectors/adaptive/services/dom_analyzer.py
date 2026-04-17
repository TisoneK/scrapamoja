"""
DOM Analysis Service for analyzing captured DOM snapshots and generating alternative selectors.

This service analyzes HTML snapshots from selector failures and generates multiple
alternative selector strategies with confidence scores.

Story: 3.1 - Analyze DOM Structure

Integration:
- Uses FailureSnapshotService to retrieve HTML snapshots when snapshot_id provided
- Can accept raw html_content for simpler use cases
- Returns alternatives ready for confidence scoring (Story 3.2)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Type, Union
from bs4 import BeautifulSoup
import logging
import html

from src.observability.logger import get_logger

# Try to import FailureSnapshotService - may fail if core.snapshot not available
if TYPE_CHECKING:
    from src.selectors.adaptive.services.failure_snapshot import FailureSnapshotService

try:
    from src.selectors.adaptive.services.failure_snapshot import FailureSnapshotService
except ImportError:
    # Fallback if core.snapshot module not available
    FailureSnapshotService = None

# Import ScoringBreakdown and ConfidenceTier for type hints (optional - graceful fallback)
try:
    from src.selectors.adaptive.services.confidence_scorer import ScoringBreakdown, ConfidenceTier
except ImportError:
    ScoringBreakdown = None
    ConfidenceTier = None


class StrategyType(Enum):
    """Enumeration for alternative selector strategy types."""
    CSS = "css"
    XPATH = "xpath"
    TEXT_ANCHOR = "text_anchor"
    ATTRIBUTE_MATCH = "attribute_match"
    DOM_RELATIONSHIP = "dom_relationship"
    ROLE_BASED = "role_based"


@dataclass
class AlternativeSelector:
    """Data class representing an alternative selector with metadata.
    
    Attributes:
        selector_string: The actual selector string (CSS or XPath)
        strategy_type: Which strategy generated this selector
        confidence_score: Confidence score from 0.0 to 1.0
        element_description: Human-readable description of the selector
    """
    selector_string: str
    strategy_type: StrategyType
    confidence_score: float
    element_description: str
    
    # Extended fields for Story 3.2 (Confidence Scoring)
    # These are populated by ConfidenceScorer, not by DOMAnalyzer directly
    # Using Any to allow both dataclass and dict types without import coupling
    scoring_breakdown: Optional[Any] = None
    confidence_tier: Optional[Any] = None  # Accepts enum or string
    historical_stability: Optional[float] = None
    specificity_score: Optional[float] = None
    dom_similarity: Optional[float] = None
    
    # Extended fields for Story 3.3 (Blast Radius)
    # These are populated by BlastRadiusCalculator, not by DOMAnalyzer directly
    blast_radius_result: Optional[Any] = None  # BlastRadiusResult from blast_radius.py
    blast_radius_severity: Optional[str] = None  # low/medium/high/critical
    
    # Extended fields for Story 4.4 (Custom Selector Strategies)
    is_custom: bool = False  # Whether this is a custom (user-created) selector
    custom_notes: Optional[str] = None  # Notes from custom selector creator
    created_by: Optional[str] = None  # User identifier who created the custom selector
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "selector_string": self.selector_string,
            "strategy_type": self.strategy_type.value,
            "confidence_score": self.confidence_score,
            "element_description": self.element_description,
        }
        # Add extended fields from Story 3.2 if present
        # These are populated by ConfidenceScorer, stored as dicts to avoid coupling
        if self.scoring_breakdown is not None:
            result["scoring_breakdown"] = self.scoring_breakdown
        if self.confidence_tier is not None:
            result["confidence_tier"] = self.confidence_tier
        if self.historical_stability is not None:
            result["historical_stability"] = self.historical_stability
        if self.specificity_score is not None:
            result["specificity_score"] = self.specificity_score
        if self.dom_similarity is not None:
            result["dom_similarity"] = self.dom_similarity
        # Add extended fields from Story 3.3 (Blast Radius)
        if self.blast_radius_result is not None:
            # Convert BlastRadiusResult to dict if it's an object
            if hasattr(self.blast_radius_result, 'to_dict'):
                result["blast_radius_result"] = self.blast_radius_result.to_dict()
            else:
                result["blast_radius_result"] = self.blast_radius_result
        if self.blast_radius_severity is not None:
            result["blast_radius_severity"] = self.blast_radius_severity
        # Add extended fields from Story 4.4 (Custom Selector)
        if self.is_custom:
            result["is_custom"] = True
        if self.custom_notes is not None:
            result["custom_notes"] = self.custom_notes
        if self.created_by is not None:
            result["created_by"] = self.created_by
        return result


class DOMAnalyzer:
    """Service for analyzing DOM snapshots and generating alternative selectors.
    
    This service parses HTML snapshots from selector failures and generates
    multiple alternative selector strategies to help recover from failures.
    
    Strategy types:
    - CSS: ID-based, class-based, tag-class combinations
    - XPath: Element path-based selectors
    - TEXT_ANCHOR: Text content-based selectors
    - ATTRIBUTE_MATCH: Attribute-based selectors
    - DOM_RELATIONSHIP: Parent, sibling, child relationship selectors
    - ROLE_BASED: ARIA role-based selectors
    
    Integration:
    - Uses FailureSnapshotService to retrieve HTML snapshots
    - Uses FailureEvent for failed selector context
    - Returns alternatives ready for confidence scoring (Story 3.2)
    """
    
    # Confidence scores for different strategy types
    STRATEGY_CONFIDENCE = {
        StrategyType.CSS: {
            "id": 0.9,
            "class": 0.7,
            "tag_class": 0.6,
            "tag_only": 0.3,
        },
        StrategyType.XPATH: {
            "absolute": 0.5,
            "relative": 0.7,
            "attribute": 0.8,
        },
        StrategyType.TEXT_ANCHOR: {
            "exact": 0.8,
            "partial": 0.6,
            "contains": 0.5,
        },
        StrategyType.ATTRIBUTE_MATCH: {
            "data_attr": 0.75,
            "name_attr": 0.7,
            "href": 0.65,
            "any": 0.4,
        },
        StrategyType.DOM_RELATIONSHIP: {
            "parent_id": 0.75,
            "parent_class": 0.5,
            "sibling_id": 0.65,
            "child": 0.4,
        },
        StrategyType.ROLE_BASED: {
            "role": 0.85,
            "role_label": 0.9,
        },
    }

    # Maximum depth for XPath building to prevent infinite loops
    MAX_XPATH_DEPTH = 20

    def __init__(
        self,
        snapshot_service = None,
    ):
        """Initialize the DOM analyzer service.

        Args:
            snapshot_service: Optional FailureSnapshotService for loading HTML from snapshots.
                             If not provided, callers must pass html_content directly.
        """
        self._logger = get_logger("dom_analyzer")
        self._snapshot_service = snapshot_service

        # Track strategy metrics for confidence scoring
        self._strategy_metrics: dict = {}
    
    def _analyze_html_to_soup(self, html: str) -> Any:
        """Convert HTML string to BeautifulSoup object.
        
        This is a helper method used internally and by tests.
        
        Args:
            html: HTML string to parse
            
        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, 'lxml')
    
    async def _load_html_from_snapshot(self, snapshot_id: str) -> Optional[str]:
        """Load HTML content from a snapshot using FailureSnapshotService.

        Args:
            snapshot_id: ID of the snapshot to load

        Returns:
            HTML content string if found, None otherwise
        """
        if not self._snapshot_service and FailureSnapshotService:
            self._snapshot_service = FailureSnapshotService()

        if not self._snapshot_service:
            self._logger.warning("snapshot_service_unavailable", snapshot_id=snapshot_id)
            return None

        try:
            snapshot = await self._snapshot_service.get_failure_snapshot(snapshot_id)
            if snapshot and hasattr(snapshot, 'html'):
                return snapshot.html
            return None
        except Exception as e:
            self._logger.error(
                "load_snapshot_failed",
                snapshot_id=snapshot_id,
                error=str(e)
            )
            return None
    
    async def analyze_snapshot(
        self,
        html_content: Optional[str] = None,
        failed_selector: str = "",
        snapshot_id: Optional[str] = None,
        sport: Optional[str] = None,
        site: Optional[str] = None,
    ) -> List[AlternativeSelector]:
        """Analyze DOM snapshot and generate alternative selectors.

        This is the main entry point for DOM analysis. It parses the HTML content
        and generates alternative selectors using all available strategies.

        Integration options:
        - Provide html_content directly for simple use cases
        - Provide snapshot_id to load HTML via FailureSnapshotService

        Args:
            html_content: HTML content from the snapshot (optional if snapshot_id provided)
            failed_selector: The selector that failed (to find target element)
            snapshot_id: Optional snapshot ID to load HTML via FailureSnapshotService
            sport: Optional sport context for scoring adjustments (used by Story 3.2)
            site: Optional site context for scoring adjustments (used by Story 3.2)

        Returns:
            List of AlternativeSelector objects, sorted by confidence (highest first)
            Returns empty list if no alternatives found or HTML is invalid
        """
        # Load HTML from snapshot if snapshot_id provided
        if snapshot_id and not html_content:
            html_content = await self._load_html_from_snapshot(snapshot_id)

        if not html_content or not html_content.strip():
            self._logger.warning("analyze_empty_html", failed_selector=failed_selector)
            return []
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
        except Exception as e:
            self._logger.error(
                "analyze_parse_error",
                error=str(e),
                failed_selector=failed_selector
            )
            return []
        
        # Try to find the target element using the failed selector
        target = None
        if failed_selector:
            try:
                target = soup.select_one(failed_selector)
            except Exception as e:
                self._logger.warning(
                    "failed_selector_invalid",
                    selector=failed_selector,
                    error=str(e)
                )
        
        # If we can't find the target with failed selector, try to find by common attributes
        if not target:
            target = self._find_target_element_by_context(soup, failed_selector)
        
        if not target:
            self._logger.warning(
                "target_not_found",
                failed_selector=failed_selector
            )
            return []
        
        # Generate alternatives using all strategies
        alternatives: List[AlternativeSelector] = []
        
        # CSS strategies
        alternatives.extend(self._analyze_css(target, soup))
        
        # XPath strategies
        alternatives.extend(self._analyze_xpath(target, soup))
        
        # Text anchor strategies
        alternatives.extend(self._analyze_text_anchor(target, soup))
        
        # Attribute match strategies
        alternatives.extend(self._analyze_attribute_match(target, soup))
        
        # DOM relationship strategies
        alternatives.extend(self._analyze_dom_relationship(target, soup))
        
        # Role-based strategies
        alternatives.extend(self._analyze_role_based(target, soup))
        
        # Deduplicate and sort by confidence
        alternatives = self._deduplicate_alternatives(alternatives)
        alternatives.sort(key=lambda x: x.confidence_score, reverse=True)
        
        self._logger.info(
            "analyze_complete",
            alternatives_count=len(alternatives),
            failed_selector=failed_selector
        )
        
        return alternatives
    
    def _find_target_element_by_context(
        self,
        soup: BeautifulSoup,
        failed_selector: str
    ) -> Optional[Any]:
        """Try to find target element when failed selector doesn't work.
        
        Attempts to find the element using common heuristics when the 
        original selector fails.
        """
        # Try selecting with the selector as-is
        try:
            # If failed_selector looks like a CSS selector, try basic variations
            if failed_selector.startswith('#'):
                # Try as ID
                return soup.find(id=failed_selector[1:])
            elif failed_selector.startswith('.'):
                # Try as class
                return soup.find(class_=failed_selector[1:])
            else:
                # Try as tag
                return soup.find(failed_selector)
        except Exception:
            pass
        
        # Return first element as fallback (for analysis)
        return soup.find()
    
    def _analyze_css(
        self,
        target: Any,
        soup: BeautifulSoup
    ) -> List[AlternativeSelector]:
        """Generate CSS selector alternatives.
        
        Strategies:
        - ID-based: #element-id (highest confidence)
        - Class-based: .class-name (medium-high confidence)
        - Tag + class: div.class-name (medium confidence)
        - Tag only: div (low confidence)
        """
        alternatives = []
        
        # ID-based selector (highest confidence)
        element_id = target.get('id')
        if element_id:
            alternatives.append(AlternativeSelector(
                selector_string=f"#{element_id}",
                strategy_type=StrategyType.CSS,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.CSS]["id"],
                element_description=f"ID selector: #{element_id}"
            ))
        
        # Class-based selectors
        classes = target.get('class', [])
        if classes:
            # Single class selector
            primary_class = classes[0]
            alternatives.append(AlternativeSelector(
                selector_string=f".{primary_class}",
                strategy_type=StrategyType.CSS,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.CSS]["class"],
                element_description=f"Class selector: .{primary_class}"
            ))
            
            # Multiple classes combined
            if len(classes) > 1:
                combined_classes = '.'.join(classes)
                alternatives.append(AlternativeSelector(
                    selector_string=f".{combined_classes}",
                    strategy_type=StrategyType.CSS,
                    confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.CSS]["class"] - 0.1,
                    element_description=f"Multi-class selector: .{combined_classes}"
                ))
        
        # Tag + class combination
        if classes:
            alternatives.append(AlternativeSelector(
                selector_string=f"{target.name}.{' '.join(classes)}",
                strategy_type=StrategyType.CSS,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.CSS]["tag_class"],
                element_description=f"Tag-class combination: {target.name}.{classes[0]}"
            ))
        
        # Tag only (fallback)
        alternatives.append(AlternativeSelector(
            selector_string=target.name,
            strategy_type=StrategyType.CSS,
            confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.CSS]["tag_only"],
            element_description=f"Tag selector: {target.name}"
        ))
        
        return alternatives
    
    def _analyze_xpath(
        self,
        target: Any,
        soup: BeautifulSoup
    ) -> List[AlternativeSelector]:
        """Generate XPath selector alternatives.
        
        Strategies:
        - Absolute path: /html/body/div/span
        - Relative path: //div[@class='...']
        - Attribute-based: //*[@id='...']
        """
        alternatives = []
        
        # Build element path with depth limit
        path_parts = []
        current = target
        depth = 0
        while current and current.name and depth < self.MAX_XPATH_DEPTH:
            tag = current.name
            idx = 1
            sibling = current.previous_sibling
            while sibling:
                if sibling.name == tag:
                    idx += 1
                sibling = sibling.previous_sibling
            if idx > 1:
                path_parts.insert(0, f"{tag}[{idx}]")
            else:
                path_parts.insert(0, tag)
            current = current.parent
            depth += 1
        
        # Absolute path (lower confidence)
        absolute_path = '/' + '/'.join(path_parts)
        alternatives.append(AlternativeSelector(
            selector_string=absolute_path,
            strategy_type=StrategyType.XPATH,
            confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.XPATH]["absolute"],
            element_description=f"Absolute XPath: {absolute_path[:50]}..."
        ))
        
        # Relative path with attribute
        element_id = target.get('id')
        if element_id:
            rel_path = f"//{target.name}[@id='{element_id}']"
            alternatives.append(AlternativeSelector(
                selector_string=rel_path,
                strategy_type=StrategyType.XPATH,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.XPATH]["attribute"],
                element_description=f"XPath with ID: {target.name}[@id='{element_id}']"
            ))
        
        # Class-based relative path
        classes = target.get('class', [])
        if classes:
            rel_path = f"//{target.name}[@class='{classes[0]}']"
            alternatives.append(AlternativeSelector(
                selector_string=rel_path,
                strategy_type=StrategyType.XPATH,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.XPATH]["relative"],
                element_description=f"XPath with class: {target.name}[@class='{classes[0]}']"
            ))
        
        return alternatives
    
    def _analyze_text_anchor(
        self,
        target: Any,
        soup: BeautifulSoup
    ) -> List[AlternativeSelector]:
        """Generate text anchor selector alternatives.
        
        Strategies:
        - Exact text match
        - Partial text match
        - Contains text
        """
        alternatives = []
        
        # Get text content
        text = target.get_text(strip=True)
        if not text:
            return alternatives
        
        # Escape special characters for XPath safety
        escaped_text = html.escape(text, quote=True)
        escaped_partial = html.escape(text[:15], quote=True)
        
        # Truncate for readability
        display_text = text[:30] + "..." if len(text) > 30 else text
        
        # Exact text (for elements with unique text)
        # Using XPath contains() for broader matching
        alternatives.append(AlternativeSelector(
            selector_string=f"//*[text()='{escaped_text}']",
            strategy_type=StrategyType.TEXT_ANCHOR,
            confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.TEXT_ANCHOR]["exact"],
            element_description=f"Exact text: '{display_text}'"
        ))
        
        # Partial/contains text
        if len(text) > 3:
            alternatives.append(AlternativeSelector(
                selector_string=f"//*[contains(text(),'{escaped_partial}')]",
                strategy_type=StrategyType.TEXT_ANCHOR,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.TEXT_ANCHOR]["partial"],
                element_description=f"Partial text: contains '{text[:15]}...'"
            ))
        
        # For link elements, try using link text
        if target.name in ('a', 'button'):
            alternatives.append(AlternativeSelector(
                selector_string=f"//{target.name}[text()='{escaped_text}']",
                strategy_type=StrategyType.TEXT_ANCHOR,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.TEXT_ANCHOR]["exact"] + 0.1,
                element_description=f"{target.name} with exact text"
            ))
        
        return alternatives
    
    def _analyze_attribute_match(
        self,
        target: Any,
        soup: BeautifulSoup
    ) -> List[AlternativeSelector]:
        """Generate attribute-based selector alternatives.
        
        Strategies:
        - Data attributes: data-testid, data-cy, data-test
        - Name attribute
        - Href for links
        - Any unique attribute
        """
        alternatives = []
        
        # Data attributes (highest confidence for test automation)
        data_attrs = {k: v for k, v in target.attrs.items() 
                      if k.startswith('data-')}
        for attr, value in data_attrs.items():
            if isinstance(value, str):
                alternatives.append(AlternativeSelector(
                    selector_string=f"[{attr}='{value}']",
                    strategy_type=StrategyType.ATTRIBUTE_MATCH,
                    confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.ATTRIBUTE_MATCH]["data_attr"],
                    element_description=f"Data attribute: {attr}='{value}'"
                ))
        
        # Name attribute
        name = target.get('name')
        if name:
            alternatives.append(AlternativeSelector(
                selector_string=f"[name='{name}']",
                strategy_type=StrategyType.ATTRIBUTE_MATCH,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.ATTRIBUTE_MATCH]["name_attr"],
                element_description=f"Name attribute: name='{name}'"
            ))
        
        # Href for links
        href = target.get('href')
        if href and target.name == 'a':
            alternatives.append(AlternativeSelector(
                selector_string=f"a[href='{href}']",
                strategy_type=StrategyType.ATTRIBUTE_MATCH,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.ATTRIBUTE_MATCH]["href"],
                element_description=f"Link href: {href[:30]}..."
            ))
        
        # Type attribute for inputs
        input_type = target.get('type')
        if input_type and target.name == 'input':
            alternatives.append(AlternativeSelector(
                selector_string=f"input[type='{input_type}']",
                strategy_type=StrategyType.ATTRIBUTE_MATCH,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.ATTRIBUTE_MATCH]["name_attr"],
                element_description=f"Input type: type='{input_type}'"
            ))
        
        # Title attribute
        title = target.get('title')
        if title:
            alternatives.append(AlternativeSelector(
                selector_string=f"[title='{title}']",
                strategy_type=StrategyType.ATTRIBUTE_MATCH,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.ATTRIBUTE_MATCH]["any"],
                element_description=f"Title attribute: title='{title}'"
            ))
        
        # Alt attribute for images
        alt = target.get('alt')
        if alt and target.name == 'img':
            alternatives.append(AlternativeSelector(
                selector_string=f"img[alt='{alt}']",
                strategy_type=StrategyType.ATTRIBUTE_MATCH,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.ATTRIBUTE_MATCH]["any"],
                element_description=f"Image alt: alt='{alt}'"
            ))
        
        return alternatives
    
    def _analyze_dom_relationship(
        self,
        target: Any,
        soup: BeautifulSoup
    ) -> List[AlternativeSelector]:
        """Generate DOM relationship-based selector alternatives.
        
        Strategies:
        - Parent with ID
        - Parent with class
        - Sibling with ID
        - Child relationships
        """
        alternatives = []
        
        # Parent with ID
        parent = target.parent
        while parent:
            parent_id = parent.get('id')
            if parent_id:
                alternatives.append(AlternativeSelector(
                    selector_string=f"#{parent_id} {target.name}",
                    strategy_type=StrategyType.DOM_RELATIONSHIP,
                    confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.DOM_RELATIONSHIP]["parent_id"],
                    element_description=f"Child of #{parent_id}: #{parent_id} {target.name}"
                ))
                break
            parent = parent.parent
        
        # Parent with class
        parent = target.parent
        while parent:
            parent_class = parent.get('class', [])
            if parent_class:
                alternatives.append(AlternativeSelector(
                    selector_string=f".{parent_class[0]} {target.name}",
                    strategy_type=StrategyType.DOM_RELATIONSHIP,
                    confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.DOM_RELATIONSHIP]["parent_class"],
                    element_description=f"Child of .{parent_class[0]}: .{parent_class[0]} {target.name}"
                ))
                break
            parent = parent.parent
        
        # Previous sibling with ID
        prev_sibling = target.previous_sibling
        while prev_sibling:
            if hasattr(prev_sibling, 'get'):
                sibling_id = prev_sibling.get('id')
                if sibling_id:
                    alternatives.append(AlternativeSelector(
                        selector_string=f"#{sibling_id} + {target.name}",
                        strategy_type=StrategyType.DOM_RELATIONSHIP,
                        confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.DOM_RELATIONSHIP]["sibling_id"],
                        element_description=f"Adjacent to #{sibling_id}: #{sibling_id} + {target.name}"
                    ))
                    break
            prev_sibling = prev_sibling.previous_sibling
        
        # Direct child selector
        parent = target.parent
        if parent:
            parent_tag = parent.name if parent.name else 'div'
            alternatives.append(AlternativeSelector(
                selector_string=f"{parent_tag} > {target.name}",
                strategy_type=StrategyType.DOM_RELATIONSHIP,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.DOM_RELATIONSHIP]["child"],
                element_description=f"Direct child: {parent_tag} > {target.name}"
            ))
        
        return alternatives
    
    def _analyze_role_based(
        self,
        target: Any,
        soup: BeautifulSoup
    ) -> List[AlternativeSelector]:
        """Generate ARIA role-based selector alternatives.
        
        Strategies:
        - Role attribute
        - Role with label
        """
        alternatives = []
        
        # ARIA role
        role = target.get('role')
        if role:
            alternatives.append(AlternativeSelector(
                selector_string=f"[role='{role}']",
                strategy_type=StrategyType.ROLE_BASED,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.ROLE_BASED]["role"],
                element_description=f"ARIA role: role='{role}'"
            ))
        
        # Role with label (highest confidence)
        aria_label = target.get('aria-label')
        if role and aria_label:
            alternatives.append(AlternativeSelector(
                selector_string=f"[role='{role}'][aria-label='{aria_label}']",
                strategy_type=StrategyType.ROLE_BASED,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.ROLE_BASED]["role_label"],
                element_description=f"Role with label: role='{role}', aria-label='{aria_label}'"
            ))
        
        # Labeledby
        aria_labelledby = target.get('aria-labelledby')
        if role and aria_labelledby:
            alternatives.append(AlternativeSelector(
                selector_string=f"[role='{role}'][aria-labelledby='{aria_labelledby}']",
                strategy_type=StrategyType.ROLE_BASED,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.ROLE_BASED]["role_label"] - 0.05,
                element_description=f"Role with labelledby"
            ))
        
        # aria-label without role
        if not role and aria_label:
            alternatives.append(AlternativeSelector(
                selector_string=f"[aria-label='{aria_label}']",
                strategy_type=StrategyType.ROLE_BASED,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.ROLE_BASED]["role"] - 0.1,
                element_description=f"ARIA label: aria-label='{aria_label}'"
            ))
        
        # aria-describedby
        aria_describedby = target.get('aria-describedby')
        if aria_describedby:
            alternatives.append(AlternativeSelector(
                selector_string=f"[aria-describedby='{aria_describedby}']",
                strategy_type=StrategyType.ROLE_BASED,
                confidence_score=self.STRATEGY_CONFIDENCE[StrategyType.ROLE_BASED]["role"] - 0.15,
                element_description=f"ARIA describedby"
            ))
        
        return alternatives
    
    def _deduplicate_alternatives(
        self,
        alternatives: List[AlternativeSelector]
    ) -> List[AlternativeSelector]:
        """Remove duplicate selectors, keeping highest confidence."""
        seen = {}
        for alt in alternatives:
            key = alt.selector_string
            if key not in seen or alt.confidence_score > seen[key].confidence_score:
                seen[key] = alt
        return list(seen.values())


# Module-level instance for convenience
dom_analyzer = DOMAnalyzer()
