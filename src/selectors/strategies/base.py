"""
Base strategy pattern implementation for Selector Engine.

Provides the abstract base class that all strategy patterns should inherit from,
implementing common functionality and enforcing the strategy pattern interface.
"""

import asyncio
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from playwright.async_api import Page, ElementHandle

from src.models.selector_models import (
    StrategyPattern, StrategyType, SelectorResult, ElementInfo,
    ValidationResult, ValidationRule, ValidationType
)
from src.selectors.context import DOMContext
from src.selectors.interfaces import IStrategyPattern
from src.observability.logger import get_logger
from src.utils.exceptions import (
    StrategyExecutionError, ValidationError, ConfigurationError
)


class BaseStrategyPattern(IStrategyPattern):
    """Base implementation for all strategy patterns."""
    
    def __init__(self, strategy_id: str, strategy_type: StrategyType, priority: int = 1):
        """
        Initialize strategy pattern.
        
        Args:
            strategy_id: Unique identifier for this strategy
            strategy_type: Type of strategy (TEXT_ANCHOR, ATTRIBUTE_MATCH, etc.)
            priority: Priority order (lower = higher priority)
        """
        self._strategy_id = strategy_id
        self._strategy_type = strategy_type
        self._priority = priority
        self._success_count = 0
        self._total_attempts = 0
        self._total_time = 0.0
        self._created_at = datetime.utcnow()
        self._last_updated = datetime.utcnow()
        self._logger = get_logger(f"strategy.{strategy_type.value}")
        
        # Validate initialization
        if not strategy_id or not strategy_id.strip():
            raise ConfigurationError(
                "strategy", "initialization", "Strategy ID cannot be empty"
            )
        if priority < 1:
            raise ConfigurationError(
                "strategy", "priority", "Priority must be >= 1"
            )
    
    @property
    def id(self) -> str:
        """Get strategy identifier."""
        return self._strategy_id
    
    @property
    def type(self) -> StrategyType:
        """Get strategy type."""
        return self._strategy_type
    
    @property
    def priority(self) -> int:
        """Get strategy priority."""
        return self._priority
    
    @abstractmethod
    async def attempt_resolution(self, selector: 'SemanticSelector', context: DOMContext) -> SelectorResult:
        """Attempt to resolve selector using this strategy."""
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate strategy-specific configuration."""
        issues = []
        
        # Common validation for all strategies
        if not isinstance(config, dict):
            issues.append("Configuration must be a dictionary")
            return issues
        
        # Strategy-specific validation
        issues.extend(self._validate_strategy_config(config))
        
        return issues
    
    def update_metrics(self, success: bool, resolution_time: float) -> None:
        """Update strategy performance metrics."""
        self._total_attempts += 1
        self._total_time += resolution_time
        if success:
            self._success_count += 1
        self._last_updated = datetime.utcnow()
        
        # Log performance update
        self._logger.debug(
            "strategy_metrics_updated",
            strategy_id=self._strategy_id,
            success=success,
            resolution_time=resolution_time,
            success_rate=self.get_success_rate(),
            avg_time=self.get_avg_resolution_time()
        )
    
    def get_success_rate(self) -> float:
        """Get success rate for this strategy."""
        if self._total_attempts == 0:
            return 0.0
        return self._success_count / self._total_attempts
    
    def get_avg_resolution_time(self) -> float:
        """Get average resolution time for this strategy."""
        if self._total_attempts == 0:
            return 0.0
        return self._total_time / self._total_attempts
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for this strategy."""
        return {
            "strategy_id": self._strategy_id,
            "strategy_type": self._strategy_type.value,
            "priority": self._priority,
            "success_rate": self.get_success_rate(),
            "avg_resolution_time": self.get_avg_resolution_time(),
            "total_attempts": self._total_attempts,
            "successful_attempts": self._success_count,
            "failed_attempts": self._total_attempts - self._success_count,
            "created_at": self._created_at.isoformat(),
            "last_updated": self._last_updated.isoformat()
        }
    
    def is_active(self) -> bool:
        """Check if strategy is currently active."""
        return True  # Base implementation - can be overridden
    
    def set_active(self, active: bool) -> None:
        """Set strategy active status."""
        # This would be used to disable strategies that consistently fail
        pass  # Base implementation - can be overridden
    
    async def _validate_element_found(self, element: Optional[ElementHandle]) -> bool:
        """Validate that element was found and is usable."""
        if element is None:
            return False
        
        try:
            # Check if element is attached to DOM
            is_attached = await element.is_attached()
            if not is_attached:
                return False
            
            # Check if element is visible
            is_visible = await element.is_visible()
            return is_visible
            
        except Exception as e:
            self._logger.warning(
                "element_validation_failed",
                strategy_id=self._strategy_id,
                error=str(e)
            )
            return False
    
    async def _extract_element_info(self, element: ElementHandle) -> ElementInfo:
        """Extract comprehensive element information."""
        try:
            # Basic element properties
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
            text_content = await element.evaluate("el => el.textContent || ''")
            
            # Attributes
            attributes = await element.evaluate("""
                el => {
                    const attrs = {};
                    for (const attr of el.attributes) {
                        attrs[attr.name] = attr.value;
                    }
                    return attrs;
                }
            """)
            
            # CSS classes
            class_list = await element.evaluate("el => Array.from(el.classList)")
            
            # DOM path
            dom_path = await self._get_dom_path(element)
            
            # Visibility and interactability
            visibility = await self._is_visible(element)
            interactable = await self._is_interactable(element)
            
            return ElementInfo(
                tag_name=tag_name,
                text_content=text_content.strip(),
                attributes=attributes,
                css_classes=class_list,
                dom_path=dom_path,
                visibility=visibility,
                interactable=interactable
            )
            
        except Exception as e:
            self._logger.error(
                "element_info_extraction_failed",
                strategy_id=self._strategy_id,
                error=str(e)
            )
            raise StrategyExecutionError(
                self._strategy_id, "home_team_name", 
                f"Failed to extract element info: {e}"
            )
    
    async def _get_dom_path(self, element: ElementHandle) -> str:
        """Generate DOM path for element."""
        return await element.evaluate("""
            el => {
                const path = [];
                let current = el;
                
                while (current && current !== document.body) {
                    let selector = current.tagName.toLowerCase();
                    
                    // Add ID if present
                    if (current.id) {
                        selector += '#' + current.id;
                    } else if (current.className) {
                        // Add first class if no ID
                        const classes = current.className.split(' ').filter(c => c);
                        if (classes.length > 0) {
                            selector += '.' + classes[0];
                        }
                    }
                    
                    // Add nth-child if needed for uniqueness
                    const siblings = Array.from(current.parentNode?.children || []);
                    const sameTagSiblings = siblings.filter(s => s.tagName === current.tagName);
                    if (sameTagSiblings.length > 1) {
                        const index = sameTagSiblings.indexOf(current) + 1;
                        selector += `:nth-child(${index})`;
                    }
                    
                    path.unshift(selector);
                    current = current.parentNode;
                }
                
                return 'body' + (path.length > 0 ? ' > ' + path.join(' > ') : '');
            }
        """)
    
    async def _is_visible(self, element: ElementHandle) -> bool:
        """Check if element is visible."""
        try:
            return await element.evaluate("""
                el => {
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0';
                }
            """)
        except Exception:
            return False
    
    async def _is_interactable(self, element: ElementHandle) -> bool:
        """Check if element is interactable."""
        try:
            return await element.evaluate("""
                el => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    
                    // Check if element is visible and not disabled
                    if (style.display === 'none' || 
                        style.visibility === 'hidden' || 
                        style.opacity === '0' ||
                        rect.width === 0 || 
                        rect.height === 0) {
                        return false;
                    }
                    
                    // Check if element is disabled
                    if (el.disabled || el.getAttribute('aria-disabled') === 'true') {
                        return false;
                    }
                    
                    // Check common interactable elements
                    const interactableTags = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'];
                    const interactableRoles = ['button', 'link', 'menuitem', 'option'];
                    
                    return interactableTags.includes(el.tagName) ||
                           interactableRoles.includes(el.getAttribute('role')) ||
                           el.onclick !== null ||
                           el.style.cursor === 'pointer';
                }
            """)
        except Exception:
            return False
    
    @abstractmethod
    def _validate_strategy_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate strategy-specific configuration."""
        pass
    
    async def _find_element_by_text_anchor(self, context: DOMContext, 
                                           anchor_text: str,
                                           proximity_selector: Optional[str] = None,
                                           case_sensitive: bool = False) -> Optional[ElementHandle]:
        """Find element by text anchor."""
        try:
            # Build CSS selector for text anchor
            if case_sensitive:
                text_selector = f"text='{anchor_text}'"
            else:
                text_selector = f"text='{anchor_text}'"
            
            if proximity_selector:
                # Find element near the anchor text
                elements = await context.page.query_selector_all(f"{proximity_selector}:has-text({text_selector})")
            else:
                # Find element containing the anchor text
                elements = await context.page.query_selector_all(f"*:contains({text_selector})")
            
            # Return the first matching element
            for element in elements:
                if await self._validate_element_found(element):
                    return element
            
            return None
            
        except Exception as e:
            self._logger.error(
                "text_anchor_search_failed",
                strategy_id=self._strategy_id,
                anchor_text=anchor_text,
                proximity_selector=proximity_selector,
                error=str(e)
            )
            return None
    
    async def _find_element_by_attribute(self, context: DOMContext,
                                         attribute: str,
                                         value_pattern: str,
                                         element_tag: Optional[str] = None) -> Optional[ElementHandle]:
        """Find element by attribute match."""
        try:
            # Build CSS selector for attribute match
            if element_tag:
                attribute_selector = f"{element_tag}[{attribute}~='{value_pattern}']"
            else:
                attribute_selector = f"[{attribute}~='{value_pattern}']"
            
            elements = await context.page.query_selector_all(attribute_selector)
            
            # Return the first matching element
            for element in elements:
                if await self._validate_element_found(element):
                    return element
            
            return None
            
        except Exception as e:
            self._logger.error(
                "attribute_match_search_failed",
                strategy_id=self._strategy_id,
                attribute=attribute,
                value_pattern=value_pattern,
                element_tag=element_tag,
                error=str(e)
            )
            return None
    
    async def _find_element_by_dom_relationship(self, context: DOMContext,
                                                parent_selector: str,
                                                child_index: int = 0,
                                                relationship_type: str = "child") -> Optional[ElementHandle]:
        """Find element by DOM relationship."""
        try:
            # Find parent element
            parent = await context.page.query_selector(parent_selector)
            if not parent:
                return None
            
            # Find child based on relationship type
            if relationship_type == "child":
                children = await parent.query_selector_all(f"> *:nth-child({child_index})")
                if len(children) > child_index:
                    element = children[child_index]
                    if await self._validate_element_found(element):
                        return element
            
            elif relationship_type == "descendant":
                if element_tag:
                    descendants = await parent.query_selector_all(f"{element_tag}")
                else:
                    descendants = await parent.query_selector_all("*")
                
                for descendant in descendants:
                    if await self._validate_element_found(descendant):
                        return descendant
            
            elif relationship_type == "sibling":
                siblings = await parent.query_selector_all(":scope > *")
                if len(siblings) > 0:
                    element = siblings[0]  # First sibling
                    if await self._validate_element_found(element):
                        return element
            
            return None
            
        except Exception as e:
            self._logger.error(
                "dom_relationship_search_failed",
                strategy_id=self._strategy_id,
                parent_selector=parent_selector,
                relationship_type=relationship_type,
                child_index=child_index,
                error=str(e)
            )
            return None
    
    async def _find_element_by_role(self, context: DOMContext,
                                     role: str,
                                     semantic_attribute: Optional[str] = None,
                                     expected_value: Optional[str] = None) -> Optional[ElementHandle]:
        """Find element by role or semantic attribute."""
        try:
            # Build CSS selector for role-based search
            if semantic_attribute and expected_value:
                role_selector = f"[{semantic_attribute}='{expected_value}'][role='{role}']"
            else:
                role_selector = f"[role='{role}']"
            
            elements = await context.page.query_selector_all(role_selector)
            
            # Return the first matching element
            for element in elements:
                if await self._validate_element_found(element):
                    return element
            
            return None
            
        except Exception as e:
            self._logger.error(
                "role_based_search_failed",
                strategy_id=self._strategy_id,
                role=role,
                semantic_attribute=semantic_attribute,
                expected_value=expected_value,
                error=str(e)
            )
            return None
    
    def _calculate_base_confidence(self, element_info: ElementInfo, 
                               validation_results: List[ValidationResult]) -> float:
        """Calculate base confidence score for element."""
        confidence = 0.0
        
        # Content validation score (40%)
        if validation_results:
            validation_score = sum(r.score * r.weight for r in validation_results)
            total_weight = sum(r.weight for r in validation_results)
            if total_weight > 0:
                confidence += (validation_score / total_weight) * 0.4
        
        # Element visibility (30%)
        if element_info.visibility:
            confidence += 0.3
        else:
            confidence -= 0.3
        
        # Element interactability (20%)
        if element_info.interactable:
            confidence += 0.2
        else:
            confidence -= 0.2
        
        # Tag appropriateness (10%)
        appropriate_tags = ['span', 'div', 'p', 'h1', 'h2', 'h3', 'section', 'article']
        if element_info.tag_name in appropriate_tags:
            confidence += 0.1
        else:
            confidence -= 0.1
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))
    
    def _apply_strategy_performance_penalty(self, base_confidence: float, 
                                     resolution_time: float) -> float:
        """Apply performance penalty to confidence score."""
        # Performance penalty for slow resolution
        if resolution_time > 1000:  # > 1 second is considered slow
            penalty = min(0.2, (resolution_time - 1000) / 10000)  # Max 20% penalty
            return max(0.0, base_confidence - penalty)
        
        return base_confidence
    
    def _log_resolution_attempt(self, selector_name: str, success: bool, 
                              resolution_time: float, confidence: float,
                              failure_reason: Optional[str] = None) -> None:
        """Log resolution attempt for debugging."""
        if success:
            self._logger.info(
                "strategy_resolution_success",
                strategy_id=self._strategy_id,
                selector_name=selector_name,
                confidence=confidence,
                resolution_time=resolution_time
            )
        else:
            self._logger.warning(
                "strategy_resolution_failed",
                strategy_id=self._strategy_id,
                selector_name=selector_name,
                resolution_time=resolution_time,
                failure_reason=failure_reason or "Unknown error"
            )


class StrategyFactory:
    """Factory for creating strategy instances."""
    
    @staticmethod
    def create_strategy(strategy_config: Dict[str, Any]) -> IStrategyPattern:
        """Create strategy instance from configuration."""
        strategy_type = StrategyType(strategy_config.get("type", "text_anchor"))
        strategy_id = strategy_config.get("id", f"auto_{strategy_type.value}_{datetime.utcnow().timestamp()}")
        priority = strategy_config.get("priority", 1)
        
        if strategy_type == StrategyType.TEXT_ANCHOR:
            from .text_anchor import TextAnchorStrategy
            return TextAnchorStrategy(strategy_id, priority, strategy_config)
        elif strategy_type == StrategyType.ATTRIBUTE_MATCH:
            from .attribute_match import AttributeMatchStrategy
            return AttributeMatchStrategy(strategy_id, priority, strategy_config)
        elif strategy_type == StrategyType.DOM_RELATIONSHIP:
            from .dom_relationship import DOMRelationshipStrategy
            return DOMRelationshipStrategy(strategy_id, priority, strategy_config)
        elif strategy_type == StrategyType.ROLE_BASED:
            from .role_based import RoleBasedStrategy
            return RoleBasedStrategy(strategy_id, priority, strategy_config)
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    @staticmethod
    def get_available_strategy_types() -> List[str]:
        """Get list of available strategy types."""
        return [strategy_type.value for strategy_type in StrategyType]


# Common utility functions for strategy validation

def validate_text_anchor_config(config: Dict[str, Any]) -> List[str]:
    """Validate text anchor strategy configuration."""
    issues = []
    
    # Check required fields
    if "anchor_text" not in config:
        issues.append("anchor_text is required for text anchor strategy")
    
    if "anchor_text" in config and not config["anchor_text"].strip():
        issues.append("anchor_text cannot be empty")
    
    # Validate optional fields
    if "proximity_selector" in config and not config["proximity_selector"].strip():
        issues.append("proximity_selector cannot be empty")
    
    if "case_sensitive" in config and not isinstance(config["case_sensitive"], bool):
        issues.append("case_sensitive must be a boolean")
    
    return issues


def validate_attribute_match_config(config: Dict[str, Any]) -> List[str]:
    """Validate attribute match strategy configuration."""
    issues = []
    
    # Check required fields
    if "attribute" not in config:
        issues.append("attribute is required for attribute match strategy")
    
    if "value_pattern" not in config:
        issues.append("value_pattern is required for attribute match strategy")
    
    if "attribute" in config and not config["attribute"].strip():
        issues.append("attribute cannot be empty")
    
    # Validate optional fields
    if "element_tag" in config and config["element_tag"] and not config["element_tag"].strip():
        issues.append("element_tag cannot be empty if specified")
    
    return issues


def validate_dom_relationship_config(config: Dict[str, Any]) -> List[str]:
    """Validate DOM relationship strategy configuration."""
    issues = []
    
    # Check required fields
    if "parent_selector" not in config:
        issues.append("parent_selector is required for DOM relationship strategy")
    
    if "relationship_type" not in config:
        issues.append("relationship_type is required for DOM relationship strategy")
    
    # Validate relationship type
    valid_relationships = ["child", "descendant", "sibling"]
    if config["relationship_type"] not in valid_relationships:
        issues.append(f"relationship_type must be one of: {valid_relationships}")
    
    # Validate child_index for child relationship
    if config["relationship_type"] == "child" and "child_index" in config:
        try:
            child_index = int(config["child_index"])
            if child_index < 0:
                issues.append("child_index must be >= 0")
        except (ValueError, TypeError):
            issues.append("child_index must be a non-negative integer")
    
    return issues


def validate_role_based_config(config: Dict[str, Any]) -> List[str]:
    """Validate role-based strategy configuration."""
    issues = []
    
    # Check required fields
    if "role" not in config:
        issues.append("role is required for role-based strategy")
    
    # Validate optional fields
    if "semantic_attribute" in config and not config["semantic_attribute"].strip():
        issues.append("semantic_attribute cannot be empty if specified")
    
    if "expected_value" in config and not config["expected_value"].strip():
        issues.append("expected_value cannot be empty if specified")
    
    return issues
