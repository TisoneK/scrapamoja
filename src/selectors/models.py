"""
Base data models for YAML selector system.

This module defines the core entities for the YAML selector loading system
including YAMLSelector, SelectorStrategy, and supporting data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)


class SelectorType(Enum):
    """Supported selector types."""
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ATTRIBUTE = "attribute"


class StrategyType(Enum):
    """Supported strategy types."""
    TEXT_ANCHOR = "text_anchor"
    ATTRIBUTE_MATCH = "attribute_match"
    DOM_RELATIONSHIP = "dom_relationship"
    ROLE_BASED = "role_based"
    CSS = "css"


class ErrorType(Enum):
    """Types of validation errors."""
    SYNTAX_ERROR = "syntax_error"
    STRUCTURE_ERROR = "structure_error"
    VALIDATION_ERROR = "validation_error"
    FILE_ERROR = "file_error"
    CONFIGURATION_ERROR = "configuration_error"


class Severity(Enum):
    """Error severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class SelectorStrategy:
    """Represents a single selector resolution strategy with configuration."""
    
    type: StrategyType
    priority: int
    config: Dict[str, Any]
    confidence_threshold: float = 0.8
    enabled: bool = True
    
    def __post_init__(self):
        """Validate strategy configuration after initialization."""
        if self.priority < 1:
            raise ValueError("Strategy priority must be positive integer")
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
    
    def validate(self) -> List[str]:
        """Validate strategy configuration and return list of errors."""
        errors = []
        
        if not self.config:
            errors.append("Strategy configuration cannot be empty")
        
        # Strategy-specific validation
        if self.type == StrategyType.TEXT_ANCHOR:
            if "anchor_text" not in self.config:
                errors.append("Text anchor strategy requires 'anchor_text' in config")
        
        elif self.type == StrategyType.ATTRIBUTE_MATCH:
            if "attribute" not in self.config:
                errors.append("Attribute match strategy requires 'attribute' in config")
            if "value_pattern" not in self.config:
                errors.append("Attribute match strategy requires 'value_pattern' in config")
        
        elif self.type == StrategyType.DOM_RELATIONSHIP:
            if "relationship_type" not in self.config:
                errors.append("DOM relationship strategy requires 'relationship_type' in config")
            if "target_selector" not in self.config:
                errors.append("DOM relationship strategy requires 'target_selector' in config")
        
        elif self.type == StrategyType.ROLE_BASED:
            if "role" not in self.config:
                errors.append("Role-based strategy requires 'role' in config")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy to dictionary representation."""
        return {
            "type": self.type.value,
            "priority": self.priority,
            "config": self.config,
            "confidence_threshold": self.confidence_threshold,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SelectorStrategy":
        """Create strategy from dictionary representation."""
        return cls(
            type=StrategyType(data["type"]),
            priority=data["priority"],
            config=data.get("config", {}),
            confidence_threshold=data.get("confidence_threshold", 0.8),
            enabled=data.get("enabled", True)
        )


@dataclass
class YAMLSelector:
    """Represents a selector configuration loaded from a YAML file."""
    
    id: str
    name: str
    selector_type: SelectorType
    pattern: str
    strategies: List[SelectorStrategy]
    file_path: str
    description: Optional[str] = None
    validation_rules: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    loaded_at: Optional[datetime] = None
    version: str = "1.0.0"
    
    def __post_init__(self):
        """Validate selector configuration after initialization."""
        if not self.id or not self.id.strip():
            raise ValueError("Selector ID cannot be empty")
        if not self.name or not self.name.strip():
            raise ValueError("Selector name cannot be empty")
        if not self.pattern or not self.pattern.strip():
            raise ValueError("Selector pattern cannot be empty")
        if not self.strategies:
            raise ValueError("Selector must have at least one strategy")
        
        # Validate strategies
        strategy_priorities = [s.priority for s in self.strategies]
        if len(strategy_priorities) != len(set(strategy_priorities)):
            raise ValueError("Strategy priorities must be unique within selector")
        
        # Set loaded_at if not provided
        if self.loaded_at is None:
            self.loaded_at = datetime.utcnow()
    
    def validate(self) -> List[str]:
        """Validate selector configuration and return list of errors."""
        errors = []
        
        # Basic validation
        if not self.id:
            errors.append("Selector ID is required")
        if not self.name:
            errors.append("Selector name is required")
        if not self.pattern:
            errors.append("Selector pattern is required")
        if not self.strategies:
            errors.append("At least one strategy is required")
        
        # Strategy validation
        for i, strategy in enumerate(self.strategies):
            strategy_errors = strategy.validate()
            for error in strategy_errors:
                errors.append(f"Strategy {i+1}: {error}")
        
        # Cross-field validation
        if self.selector_type == SelectorType.CSS:
            # Basic CSS pattern validation
            if not self.pattern.strip().startswith(('.', '#', '[', '*')):
                errors.append("CSS selector pattern should start with '.', '#', '[', or '*'")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert selector to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "selector_type": self.selector_type.value,
            "pattern": self.pattern,
            "strategies": [s.to_dict() for s in self.strategies],
            "validation_rules": self.validation_rules,
            "metadata": self.metadata,
            "file_path": self.file_path,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "YAMLSelector":
        """Create selector from dictionary representation."""
        strategies = [
            SelectorStrategy.from_dict(s_data) 
            for s_data in data.get("strategies", [])
        ]
        
        loaded_at = None
        if data.get("loaded_at"):
            loaded_at = datetime.fromisoformat(data["loaded_at"])
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            selector_type=SelectorType(data["selector_type"]),
            pattern=data["pattern"],
            strategies=strategies,
            validation_rules=data.get("validation_rules"),
            metadata=data.get("metadata"),
            file_path=data["file_path"],
            loaded_at=loaded_at,
            version=data.get("version", "1.0.0")
        )


@dataclass
class SelectorValidationError:
    """Represents a validation error for a selector configuration."""
    
    selector_id: str
    error_type: ErrorType
    field_path: str
    error_message: str
    severity: Severity = Severity.ERROR
    suggested_fix: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            "selector_id": self.selector_id,
            "error_type": self.error_type.value,
            "field_path": self.field_path,
            "error_message": self.error_message,
            "severity": self.severity.value,
            "suggested_fix": self.suggested_fix,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SelectorValidationError":
        """Create error from dictionary representation."""
        return cls(
            selector_id=data["selector_id"],
            error_type=ErrorType(data["error_type"]),
            field_path=data["field_path"],
            error_message=data["error_message"],
            severity=Severity(data.get("severity", "error")),
            suggested_fix=data.get("suggested_fix"),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


@dataclass
class ValidationResult:
    """Result of selector validation."""
    
    is_valid: bool
    errors: List[SelectorValidationError] = field(default_factory=list)
    warnings: List[SelectorValidationError] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings."""
        return len(self.warnings) > 0
    
    def add_error(self, error: SelectorValidationError):
        """Add validation error."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: SelectorValidationError):
        """Add validation warning."""
        self.warnings.append(warning)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings]
        }


@dataclass
class LoadResult:
    """Result of loading selectors from directory."""
    
    success: bool
    selectors_loaded: int
    selectors_failed: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    loading_time_ms: float = 0.0
    
    @property
    def total_selectors(self) -> int:
        """Get total number of selectors processed."""
        return self.selectors_loaded + self.selectors_failed
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_selectors == 0:
            return 0.0
        return (self.selectors_loaded / self.total_selectors) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "success": self.success,
            "selectors_loaded": self.selectors_loaded,
            "selectors_failed": self.selectors_failed,
            "total_selectors": self.total_selectors,
            "success_rate": self.success_rate,
            "errors": self.errors,
            "warnings": self.warnings,
            "loading_time_ms": self.loading_time_ms
        }


@dataclass
class RegistryStats:
    """Statistics for selector registry."""
    
    total_selectors: int = 0
    enabled_selectors: int = 0
    disabled_selectors: int = 0
    last_loaded: Optional[datetime] = None
    loading_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    validation_errors: int = 0
    validation_warnings: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary representation."""
        return {
            "total_selectors": self.total_selectors,
            "enabled_selectors": self.enabled_selectors,
            "disabled_selectors": self.disabled_selectors,
            "last_loaded": self.last_loaded.isoformat() if self.last_loaded else None,
            "loading_time_ms": self.loading_time_ms,
            "cache_hit_rate": self.cache_hit_rate,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings
        }
