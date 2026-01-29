"""
Configuration system for YAML-based selector definitions.

This module provides the infrastructure for loading, validating, and resolving
YAML selector configurations with inheritance and semantic indexing.
"""

from .loader import IConfigurationLoader, ConfigurationLoader
from .validator import ConfigurationValidator
from .inheritance import IInheritanceResolver, InheritanceResolver
from .index import ISemanticIndex, SemanticIndex
from .watcher import IConfigurationWatcher, ConfigurationWatcher, create_configuration_watcher

__all__ = [
    "IConfigurationLoader",
    "ConfigurationLoader", 
    "ConfigurationValidator",
    "IInheritanceResolver",
    "InheritanceResolver",
    "ISemanticIndex",
    "SemanticIndex",
    "IConfigurationWatcher",
    "ConfigurationWatcher",
    "create_configuration_watcher",
]
