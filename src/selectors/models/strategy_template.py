"""
Strategy template model for reusable selector strategies.

This module defines the StrategyTemplate dataclass for creating
reusable strategy definitions that can be referenced by multiple selectors.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from .selector_config import ValidationRule, ConfidenceConfig


@dataclass
class StrategyTemplate:
    """Reusable strategy definition that can be referenced by multiple selectors."""
    type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    validation: Optional[ValidationRule] = None
    confidence: Optional[ConfidenceConfig] = None
    
    def __post_init__(self):
        """Validate strategy template."""
        if not self.type:
            raise ValueError("Strategy type is required")
        
        # Validate strategy type is supported
        supported_types = [
            "text_anchor",
            "attribute_match", 
            "css_selector",
            "xpath",
            "dom_relationship",
            "role_based"
        ]
        if self.type not in supported_types:
            raise ValueError(f"Unsupported strategy type: {self.type}")
        
        # Validate parameters based on strategy type
        self._validate_parameters()
    
    def _validate_parameters(self):
        """Validate parameters based on strategy type."""
        required_params = {
            "text_anchor": ["pattern"],
            "attribute_match": ["attribute"],
            "css_selector": ["selector"],
            "xpath": ["expression"],
            "dom_relationship": ["relationship_type"],
            "role_based": ["role"]
        }
        
        if self.type in required_params:
            for param in required_params[self.type]:
                if param not in self.parameters:
                    raise ValueError(f"Missing required parameter '{param}' for strategy type '{self.type}'")
    
    def apply_parameters(self, override_parameters: Dict[str, Any]) -> 'StrategyTemplate':
        """Create a new template with override parameters applied."""
        merged_parameters = self.parameters.copy()
        merged_parameters.update(override_parameters)
        
        return StrategyTemplate(
            type=self.type,
            parameters=merged_parameters,
            validation=self.validation,
            confidence=self.confidence
        )
    
    def to_strategy_definition(self, 
                             override_parameters: Optional[Dict[str, Any]] = None,
                             priority: int = 1) -> 'StrategyDefinition':
        """Convert template to a strategy definition."""
        from .selector_config import StrategyDefinition
        
        parameters = self.parameters.copy()
        if override_parameters:
            parameters.update(override_parameters)
        
        return StrategyDefinition(
            type=self.type,
            parameters=parameters,
            priority=priority
        )
