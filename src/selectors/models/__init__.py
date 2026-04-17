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

# Re-export from flat models.py for backward compatibility
import sys, os as _os
import importlib.util as _util
_flat = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), 'models.py')
_spec = _util.spec_from_file_location('_selectors_models_flat', _flat)
_mod = _util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
YAMLSelector = _mod.YAMLSelector
SelectorStrategy = _mod.SelectorStrategy
SelectorType = _mod.SelectorType
LoadResult = _mod.LoadResult
RegistryStats = _mod.RegistryStats
del _flat, _spec, _mod, _util, _os, sys

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
