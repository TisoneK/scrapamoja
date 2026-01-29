"""
Data models for YAML-based selector configuration system.

This module contains all the data structures used to represent
selector configurations, inheritance chains, and resolution contexts.
"""

from .selector_config import (
    SelectorConfiguration,
    ConfigurationMetadata,
    ContextDefaults,
    ValidationDefaults,
    SemanticSelector,
    StrategyDefinition,
    ValidationRule,
    ConfidenceConfig,
    InheritanceChain,
    SemanticIndexEntry,
    ResolutionContext,
    ValidationResult,
    ConfigurationState,
)

from .strategy_template import StrategyTemplate

__all__ = [
    "SelectorConfiguration",
    "ConfigurationMetadata", 
    "ContextDefaults",
    "ValidationDefaults",
    "SemanticSelector",
    "StrategyDefinition",
    "ValidationRule",
    "ConfidenceConfig",
    "InheritanceChain",
    "SemanticIndexEntry",
    "ResolutionContext",
    "ValidationResult",
    "ConfigurationState",
    "StrategyTemplate",
]
