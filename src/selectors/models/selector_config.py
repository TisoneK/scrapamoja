"""
Core data models for YAML-based selector configuration system.

This module contains the primary data structures for representing
selector configurations, metadata, and resolution contexts.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class ValidationStatus(Enum):
    """Validation status for configurations."""
    VALID = "valid"
    INVALID = "invalid"
    PENDING = "pending"


@dataclass
class ConfigurationMetadata:
    """Metadata about a configuration file."""
    version: str
    last_updated: str
    description: str
    
    def __post_init__(self):
        """Validate metadata fields."""
        if not self.version:
            raise ValueError("Version is required")
        if not self.description:
            raise ValueError("Description is required")
        # Validate version format (semantic versioning)
        if not self.version.replace(".", "").replace("-", "").isdigit():
            raise ValueError(f"Invalid version format: {self.version}")


@dataclass
class ContextDefaults:
    """Default configuration inherited by child selectors."""
    page_type: str
    wait_strategy: str = "network_idle"
    timeout: int = 10000
    section: Optional[str] = None
    
    def __post_init__(self):
        """Validate context defaults."""
        if not self.page_type:
            raise ValueError("Page type is required")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        valid_wait_strategies = ["network_idle", "domcontentloaded", "load"]
        if self.wait_strategy not in valid_wait_strategies:
            raise ValueError(f"Invalid wait strategy: {self.wait_strategy}")


@dataclass
class ValidationDefaults:
    """Default validation rules inherited by selectors."""
    required: bool = False
    type: str = "string"
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    
    def __post_init__(self):
        """Validate validation defaults."""
        valid_types = ["string", "number", "boolean", "array", "object"]
        if self.type not in valid_types:
            raise ValueError(f"Invalid validation type: {self.type}")
        if self.min_length is not None and self.min_length < 0:
            raise ValueError("Min length cannot be negative")
        if self.max_length is not None and self.max_length < 0:
            raise ValueError("Max length cannot be negative")
        if (self.min_length is not None and self.max_length is not None and 
            self.min_length > self.max_length):
            raise ValueError("Min length cannot be greater than max length")


@dataclass
class ConfidenceConfig:
    """Confidence scoring configuration for selectors."""
    threshold: Optional[float] = None
    weight: Optional[float] = None
    boost_factors: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate confidence configuration."""
        if self.threshold is not None and (self.threshold < 0.0 or self.threshold > 1.0):
            raise ValueError("Threshold must be between 0.0 and 1.0")
        if self.weight is not None and self.weight <= 0:
            raise ValueError("Weight must be positive")
        for key, value in self.boost_factors.items():
            if not isinstance(key, str):
                raise ValueError("Boost factor keys must be strings")
            if not isinstance(value, (int, float)):
                raise ValueError("Boost factor values must be numbers")


@dataclass
class ValidationRule:
    """Validation configuration for a selector."""
    required: Optional[bool] = None
    type: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    
    def merge_with_defaults(self, defaults: ValidationDefaults) -> 'ValidationRule':
        """Merge this rule with validation defaults."""
        return ValidationRule(
            required=self.required if self.required is not None else defaults.required,
            type=self.type if self.type is not None else defaults.type,
            min_length=self.min_length if self.min_length is not None else defaults.min_length,
            max_length=self.max_length if self.max_length is not None else defaults.max_length,
            pattern=self.pattern if self.pattern is not None else defaults.pattern,
            custom_rules=self.custom_rules
        )


@dataclass
class StrategyDefinition:
    """Specific strategy instance with parameters."""
    type: str
    template: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    
    def __post_init__(self):
        """Validate strategy definition."""
        if not self.type:
            raise ValueError("Strategy type is required")
        if self.priority <= 0:
            raise ValueError("Priority must be positive")
        if self.template and self.parameters:
            raise ValueError("Cannot specify both template and parameters")


@dataclass
class SemanticSelector:
    """Individual selector definition with context, strategies, and validation."""
    name: str
    description: str
    context: str
    strategies: List[StrategyDefinition]
    validation: Optional[ValidationRule] = None
    confidence: Optional[ConfidenceConfig] = None
    
    def __post_init__(self):
        """Validate semantic selector."""
        if not self.name:
            raise ValueError("Selector name is required")
        if not self.description:
            raise ValueError("Description is required")
        if not self.context:
            raise ValueError("Context is required")
        if not self.strategies:
            raise ValueError("At least one strategy is required")
        
        # Validate strategies are ordered by priority
        priorities = [s.priority for s in self.strategies]
        if priorities != sorted(priorities):
            raise ValueError("Strategies must be ordered by priority")


@dataclass
class SelectorConfiguration:
    """Complete YAML configuration file with all components."""
    file_path: str
    metadata: ConfigurationMetadata
    selectors: Dict[str, SemanticSelector] = field(default_factory=dict)
    context_defaults: Optional[ContextDefaults] = None
    validation_defaults: Optional[ValidationDefaults] = None
    strategy_templates: Dict[str, 'StrategyTemplate'] = field(default_factory=dict)
    parent_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.file_path:
            raise ValueError("File path is required")
        if not self.selectors and not self.strategy_templates:
            raise ValueError("Configuration must contain selectors or templates")
        
        # Validate selector names are unique
        if len(self.selectors) != len(set(self.selectors.keys())):
            raise ValueError("Selector names must be unique within configuration")


@dataclass
class InheritanceChain:
    """Represents the inheritance hierarchy for a configuration."""
    child_path: str
    parent_paths: List[str]
    resolved_context: ContextDefaults
    resolved_validation: ValidationDefaults
    available_templates: Dict[str, 'StrategyTemplate'] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate inheritance chain."""
        if not self.child_path:
            raise ValueError("Child path is required")
        # Check for circular references
        if self.child_path in self.parent_paths:
            raise ValueError(f"Circular reference detected: {self.child_path}")


@dataclass
class SemanticIndexEntry:
    """Entry in the semantic index for fast lookup."""
    semantic_name: str
    context: str
    file_path: str
    resolved_selector: SemanticSelector
    last_modified: str
    
    def __post_init__(self):
        """Validate index entry."""
        if not self.semantic_name:
            raise ValueError("Semantic name is required")
        if not self.context:
            raise ValueError("Context is required")
        if not self.file_path:
            raise ValueError("File path is required")


@dataclass
class ResolutionContext:
    """Context for selector resolution operations."""
    current_page: str
    current_section: str
    tab_context: Optional[str] = None
    navigation_history: List[str] = field(default_factory=list)
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate resolution context."""
        if not self.current_page:
            raise ValueError("Current page is required")
        if not self.current_section:
            raise ValueError("Current section is required")


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    schema_version: str
    validation_time_ms: float


@dataclass
class ConfigurationState:
    """Current state of the configuration system."""
    loaded_configurations: Dict[str, SelectorConfiguration] = field(default_factory=dict)
    semantic_index: Dict[str, SemanticIndexEntry] = field(default_factory=dict)
    inheritance_cache: Dict[str, InheritanceChain] = field(default_factory=dict)
    last_reload: Optional[str] = None
    error_count: int = 0
    
    def __post_init__(self):
        """Validate configuration state."""
        if self.error_count < 0:
            raise ValueError("Error count cannot be negative")


# Import StrategyTemplate here to avoid circular imports
from .strategy_template import StrategyTemplate
