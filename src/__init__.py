"""
Scorewise Scraper - Semantic selector engine for web scraping.

This package provides a comprehensive selector engine with multi-strategy resolution,
confidence scoring, and production-ready features for reliable web scraping.
"""

# Core selector engine
from .selectors import (
    SelectorEngine, get_selector_engine,
    SelectorRegistry, get_selector_registry,
    ValidationEngine, get_validation_engine
)

# Models
from .models.selector_models import (
    SemanticSelector, StrategyPattern, StrategyType, SelectorResult,
    ElementInfo, ValidationRule, ValidationResult, ValidationType,
    DOMSnapshot, ConfidenceMetrics, SnapshotType, SnapshotMetadata
)

# Context
from .selectors.context import DOMContext

# Exceptions
from .utils.exceptions import (
    SelectorNotFoundError, ResolutionTimeoutError, ConfidenceThresholdError,
    StrategyExecutionError, ValidationError, ConfigurationError, StorageError
)

# Configuration
from .config.settings import get_config

# Observability
from .observability.logger import get_logger
from .observability.events import get_event_bus
from .observability.metrics import get_performance_monitor

__all__ = [
    # Core engine
    "SelectorEngine",
    "get_selector_engine",
    
    # Registry
    "SelectorRegistry",
    "get_selector_registry",
    
    # Confidence scoring
    "ConfidenceScorer",
    "get_confidence_scorer",
    
    # Validation
    "ValidationEngine",
    "get_validation_engine",
    
    # Models
    "SemanticSelector",
    "StrategyPattern",
    "StrategyType",
    "SelectorResult",
    "ElementInfo",
    "ValidationRule",
    "ValidationResult",
    "ValidationType",
    "DOMSnapshot",
    "ConfidenceMetrics",
    "SnapshotType",
    "SnapshotMetadata",
    
    # Context
    "DOMContext",
    
    # Exceptions
    "SelectorNotFoundError",
    "ResolutionTimeoutError",
    "ConfidenceThresholdError",
    "StrategyExecutionError",
    "ValidationError",
    "ConfigurationError",
    "StorageError",
    
    # Configuration
    "get_config",
    
    # Observability
    "get_logger",
    "get_event_bus",
    "get_performance_monitor"
]
