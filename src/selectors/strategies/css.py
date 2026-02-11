"""
CSS selector strategy implementation for Selector Engine.

Implements CSS-based element location using standard CSS selectors
as specified in the strategy pattern interface.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.selector_models import (
    StrategyType, SelectorResult, ElementInfo, ValidationResult,
    ValidationRule, ValidationType, SemanticSelector
)
from src.selectors.context import DOMContext
from src.selectors.strategies.base import BaseStrategyPattern
from src.utils.exceptions import StrategyExecutionError


class CSSStrategy(BaseStrategyPattern):
    """Strategy for finding elements based on CSS selectors."""
    
    def __init__(self, strategy_id: str, priority: int = 1, config: Optional[Dict[str, Any]] = None):
        """
        Initialize CSS strategy.
        
        Args:
            strategy_id: Unique identifier for this strategy
            priority: Priority order (lower = higher priority)
            config: Strategy configuration dictionary
        """
        super().__init__(strategy_id, StrategyType.CSS, priority)
        
        # Store configuration
        self._config = config or {}
        
        # Validate configuration
        issues = self.validate_config(self._config)
        if issues:
            raise ValueError(f"Invalid CSS strategy configuration: {issues}")
    
    async def attempt_resolution(self, selector: SemanticSelector, context: DOMContext) -> SelectorResult:
        """
        Attempt to resolve selector using CSS strategy.
        
        Args:
            selector: Semantic selector definition
            context: DOM context for resolution
            
        Returns:
            SelectorResult with resolution attempt details
        """
        start_time = datetime.utcnow()
        
        try:
            # Get CSS selector from configuration
            css_selector = self._config.get('selector')
            if not css_selector:
                return SelectorResult(
                    selector_name=selector.name,
                    strategy_used=self.id,
                    element_info=None,
                    confidence_score=0.0,
                    resolution_time=(datetime.utcnow() - start_time).total_seconds(),
                    validation_results=[],
                    success=False,
                    failure_reason="CSS selector not specified in configuration"
                )
            
            # Use Playwright to query elements
            page = context.page
            if not page:
                return SelectorResult(
                    selector_name=selector.name,
                    strategy_used=self.id,
                    element_info=None,
                    confidence_score=0.0,
                    resolution_time=(datetime.utcnow() - start_time).total_seconds(),
                    validation_results=[],
                    success=False,
                    failure_reason="No page context available"
                )
            
            # Execute CSS selector
            elements = await page.query_selector_all(css_selector)
            
            if not elements:
                return SelectorResult(
                    selector_name=selector.name,
                    strategy_used=self.id,
                    element_info=None,
                    confidence_score=0.0,
                    resolution_time=(datetime.utcnow() - start_time).total_seconds(),
                    validation_results=[],
                    success=False,
                    failure_reason=f"No elements found for CSS selector: {css_selector}"
                )
            
            # Create element info for first element (or all if needed)
            element_infos = []
            for element in elements:
                try:
                    # Get element properties
                    text = await element.text_content()
                    tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                    
                    element_info = ElementInfo(
                        element_id=f"css_{hash(css_selector)}_{len(element_infos)}",
                        tag_name=tag_name,
                        text_content=text or "",
                        attributes={},
                        xpath=f"css:{css_selector}",
                        css_selector=css_selector,
                        confidence=1.0,  # CSS selectors are precise
                        metadata={
                            'strategy': 'css',
                            'selector': css_selector,
                            'elements_found': len(elements)
                        }
                    )
                    element_infos.append(element_info)
                except Exception as e:
                    # Continue with other elements if one fails
                    continue
            
            if not element_infos:
                return SelectorResult(
                    selector_name=selector.name,
                    strategy_used=self.id,
                    element_info=None,
                    confidence_score=0.0,
                    resolution_time=(datetime.utcnow() - start_time).total_seconds(),
                    validation_results=[],
                    success=False,
                    failure_reason="Failed to extract element information"
                )
            
            # Return successful result with first element
            return SelectorResult(
                selector_name=selector.name,
                strategy_used=self.id,
                element_info=element_infos[0],
                confidence_score=element_infos[0].confidence,
                resolution_time=(datetime.utcnow() - start_time).total_seconds(),
                validation_results=[],
                success=True
            )
            
        except Exception as e:
            return SelectorResult(
                selector_name=selector.name,
                strategy_used=self.id,
                element_info=None,
                confidence_score=0.0,
                resolution_time=(datetime.utcnow() - start_time).total_seconds(),
                validation_results=[],
                success=False,
                failure_reason=f"CSS strategy execution failed: {str(e)}"
            )
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate CSS strategy configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of validation error messages
        """
        issues = []
        
        # Check for required selector field
        if 'selector' not in config:
            issues.append("CSS selector is required")
        elif not isinstance(config['selector'], str):
            issues.append("CSS selector must be a string")
        elif not config['selector'].strip():
            issues.append("CSS selector cannot be empty")
        
        return issues
    
    def _validate_strategy_config(self) -> List[str]:
        """
        Validate the strategy's internal configuration.
        
        Returns:
            List of validation error messages
        """
        return self.validate_config(self._config)
    
    def get_supported_element_types(self) -> List[str]:
        """
        Get list of element types this strategy supports.
        
        Returns:
            List of supported element tag names
        """
        # CSS strategy supports all element types
        return ['*']
    
    async def get_confidence_score(self, element_info: ElementInfo, context: DOMContext) -> float:
        """
        Calculate confidence score for CSS strategy result.
        
        Args:
            element_info: Element information from resolution
            context: DOM context
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # CSS selectors are precise, so base confidence is high
        base_confidence = 0.9
        
        # Adjust based on selector complexity
        css_selector = self._config.get('selector', '')
        if ':' in css_selector:  # Pseudo-selectors
            base_confidence -= 0.1
        if ' ' in css_selector:  # Descendant selectors
            base_confidence -= 0.05
        
        return max(0.0, min(1.0, base_confidence))
