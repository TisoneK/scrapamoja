"""
Strategy patterns for Selector Engine.

This module provides various strategy implementations for locating DOM elements
based on different criteria such as text anchors, attributes, DOM relationships,
and semantic roles.
"""

from .base import BaseStrategyPattern, StrategyFactory
from .text_anchor import TextAnchorStrategy
from .attribute_match import AttributeMatchStrategy
from .dom_relationship import DOMRelationshipStrategy
from .role_based import RoleBasedStrategy
from .converter import (
    LegacyStrategy,
    LegacyStrategyType,
    StrategyFormat,
    convert_legacy_to_strategypattern,
    convert_legacy_strategies,
    convert_legacy_yaml,
    detect_format,
    is_legacy_format,
)

__all__ = [
    "BaseStrategyPattern",
    "StrategyFactory",
    "TextAnchorStrategy",
    "AttributeMatchStrategy",
    "DOMRelationshipStrategy",
    "RoleBasedStrategy",
    # Converter exports
    "LegacyStrategy",
    "LegacyStrategyType",
    "StrategyFormat",
    "convert_legacy_to_strategypattern",
    "convert_legacy_strategies",
    "convert_legacy_yaml",
    "detect_format",
    "is_legacy_format",
]
