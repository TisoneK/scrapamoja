"""
Blast Radius Calculator Service.

This module provides blast radius calculation for proposed selector changes,
helping users understand the impact of approving a selector change.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from bs4 import BeautifulSoup

from src.observability.logger import get_logger

logger = get_logger("blast_radius")


class SeverityLevel(Enum):
    """Severity levels for blast radius impact assessment.
    
    - LOW: 1-2 affected selectors, 1 sport
    - MEDIUM: 3-5 affected selectors, 2-3 sports
    - HIGH: 6-10 affected selectors, 4+ sports
    - CRITICAL: 10+ affected selectors or critical selectors affected
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AffectedSelector:
    """Represents a selector that would be affected by a proposed change."""
    selector_string: str
    recipe_id: int
    sport: str
    confidence_score: float


@dataclass
class BlastRadiusResult:
    """Result of blast radius calculation for a proposed selector change."""
    proposed_selector: str
    affected_count: int
    affected_selectors: list[AffectedSelector] = field(default_factory=list)
    affected_sports: list[str] = field(default_factory=list)
    severity: SeverityLevel = SeverityLevel.LOW
    container_path: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "proposed_selector": self.proposed_selector,
            "affected_count": self.affected_count,
            "affected_selectors": [
                {
                    "selector_string": s.selector_string,
                    "recipe_id": s.recipe_id,
                    "sport": s.sport,
                    "confidence_score": s.confidence_score,
                }
                for s in self.affected_selectors
            ],
            "affected_sports": self.affected_sports,
            "severity": self.severity.value if isinstance(self.severity, SeverityLevel) else self.severity,
            "container_path": self.container_path,
        }


@dataclass
class BlastRadiusUI:
    """UI-friendly representation of blast radius result."""
    proposed_selector: str
    severity_badge: str  # Color-coded: green/yellow/orange/red
    severity_label: str  # "Low", "Medium", "High", "Critical"
    affected_count: int
    affected_sports: list[str]
    affected_selectors_preview: list[str]
    container_description: str
    
    @classmethod
    def from_result(cls, result: BlastRadiusResult) -> "BlastRadiusUI":
        """Convert BlastRadiusResult to UI-friendly format."""
        severity_colors = {
            SeverityLevel.LOW: "green",
            SeverityLevel.MEDIUM: "yellow",
            SeverityLevel.HIGH: "orange",
            SeverityLevel.CRITICAL: "red",
        }
        
        severity_labels = {
            SeverityLevel.LOW: "Low",
            SeverityLevel.MEDIUM: "Medium",
            SeverityLevel.HIGH: "High",
            SeverityLevel.CRITICAL: "Critical",
        }
        
        return cls(
            proposed_selector=result.proposed_selector,
            severity_badge=severity_colors.get(result.severity, "gray"),
            severity_label=severity_labels.get(result.severity, "Unknown"),
            affected_count=result.affected_count,
            affected_sports=result.affected_sports,
            affected_selectors_preview=[
                s.selector_string for s in result.affected_selectors[:5]
            ],
            container_description=result.container_path or "No shared containers",
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "proposed_selector": self.proposed_selector,
            "severity_badge": self.severity_badge,
            "severity_label": self.severity_label,
            "affected_count": self.affected_count,
            "affected_sports": self.affected_sports,
            "affected_selectors_preview": self.affected_selectors_preview,
            "container_description": self.container_description,
        }


@dataclass
class RecipeSelector:
    """Represents a selector from a recipe configuration."""
    selector_string: str
    recipe_id: int
    sport: str
    page_url: Optional[str] = None
    confidence_score: float = 0.0


class BlastRadiusCalculator:
    """Service for calculating blast radius of proposed selector changes.
    
    This service analyzes the potential impact of approving a selector change
    by identifying all selectors that share ancestor containers with the proposed
    selector.
    """
    
    MAX_ANCESTOR_DEPTH = 5
    
    # Container elements to consider as significant boundaries
    CONTAINER_TAGS = frozenset({
        'div', 'section', 'article', 'main', 'nav', 
        'header', 'footer', 'aside', 'form', 'fieldset'
    })
    
    def __init__(self) -> None:
        """Initialize the blast radius calculator."""
        self._logger = logger
    
    async def calculate_blast_radius(
        self,
        proposed_selector: str,
        html_content: str,
        all_selectors: list[RecipeSelector],
    ) -> BlastRadiusResult:
        """Calculate the blast radius for a proposed selector change.
        
        Args:
            proposed_selector: The selector string being proposed
            html_content: HTML content for DOM analysis
            all_selectors: List of all selectors to check for impact
            
        Returns:
            BlastRadiusResult with impact assessment
        """
        # Find proposed selector's ancestors
        ancestors = self._find_ancestor_containers(html_content, proposed_selector)
        
        if not ancestors:
            self._logger.debug(
                f"No ancestor containers found for selector: {proposed_selector}"
            )
            return BlastRadiusResult(
                proposed_selector=proposed_selector,
                affected_count=0,
                severity=SeverityLevel.LOW,
                container_path="",
            )
        
        # Find affected selectors
        affected = []
        for selector in all_selectors:
            if self._shares_ancestor(selector.selector_string, html_content, ancestors):
                affected.append(AffectedSelector(
                    selector_string=selector.selector_string,
                    recipe_id=selector.recipe_id,
                    sport=selector.sport,
                    confidence_score=selector.confidence_score,
                ))
        
        # Extract unique sports
        affected_sports = list(set(s.sport for s in affected))
        
        # Calculate severity
        severity = self._calculate_severity(len(affected), len(affected_sports))
        
        container_path = ancestors[0] if ancestors else ""
        
        return BlastRadiusResult(
            proposed_selector=proposed_selector,
            affected_count=len(affected),
            affected_selectors=affected,
            affected_sports=affected_sports,
            severity=severity,
            container_path=container_path,
        )
    
    def _find_ancestor_containers(
        self,
        html: str,
        selector: str,
    ) -> list[str]:
        """Find ancestor containers of the target element.
        
        Args:
            html: HTML content to parse
            selector: CSS selector to find
            
        Returns:
            List of ancestor container identifiers (IDs or class signatures)
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            target = soup.select_one(selector)
            
            if not target:
                self._logger.debug(f"Selector not found in HTML: {selector}")
                return []
            
            ancestors = []
            current = target.parent
            
            for _ in range(self.MAX_ANCESTOR_DEPTH):
                if current is None:
                    break
                    
                if current.name in self.CONTAINER_TAGS:
                    # Add identifiable attributes
                    container_id = current.get('id', '')
                    classes = current.get('class') or []
                    container_class = ' '.join(classes[:2])
                    
                    if container_id:
                        ancestors.append(f"#{container_id}")
                    elif container_class:
                        ancestors.append(f".{container_class.replace(' ', '.')}")
                
                current = current.parent
            
            return ancestors
            
        except Exception as e:
            self._logger.warning(f"Error finding ancestors: {e}")
            return []
    
    def _shares_ancestor(
        self,
        selector_string: str,
        html: str,
        proposed_ancestors: list[str],
    ) -> bool:
        """Check if a selector shares any ancestor containers with the proposed selector.
        
        Args:
            selector_string: The selector to check
            html: HTML content for analysis
            proposed_ancestors: List of ancestor identifiers from proposed selector
            
        Returns:
            True if the selector shares at least one ancestor container
        """
        if not proposed_ancestors:
            return False
            
        try:
            soup = BeautifulSoup(html, 'lxml')
            target = soup.select_one(selector_string)
            
            if not target:
                return False
            
            # Check if any of this selector's ancestors match
            current = target.parent
            for _ in range(self.MAX_ANCESTOR_DEPTH):
                if current is None:
                    break
                    
                if current.name in self.CONTAINER_TAGS:
                    container_id = current.get('id', '')
                    classes = current.get('class') or []
                    container_class = ' '.join(classes[:2])
                    
                    candidate = None
                    if container_id:
                        candidate = f"#{container_id}"
                    elif container_class:
                        candidate = f".{container_class.replace(' ', '.')}"
                    
                    if candidate and candidate in proposed_ancestors:
                        return True
                
                current = current.parent
            
            return False
            
        except Exception as e:
            self._logger.warning(f"Error checking ancestor sharing: {e}")
            return False
    
    def _calculate_severity(
        self,
        affected_count: int,
        sport_count: int,
    ) -> SeverityLevel:
        """Calculate severity based on affected count and sports.
        
        Args:
            affected_count: Number of affected selectors
            sport_count: Number of affected sports
            
        Returns:
            SeverityLevel based on impact
        """
        # Critical: 10+ affected OR critical selectors
        if affected_count >= 10:
            return SeverityLevel.CRITICAL
        
        # High: 6-10 affected OR 4+ sports
        if affected_count >= 6 or sport_count >= 4:
            return SeverityLevel.HIGH
        
        # Medium: 3-5 affected OR 2-3 sports
        if affected_count >= 3 or sport_count >= 2:
            return SeverityLevel.MEDIUM
        
        # Low: 1-2 affected, 1 sport
        return SeverityLevel.LOW


# Module-level instance for convenience
blast_radius_calculator = BlastRadiusCalculator()


def get_blast_radius_calculator() -> BlastRadiusCalculator:
    """Get global blast radius calculator instance."""
    return blast_radius_calculator
