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

__all__ = [
    "BaseStrategyPattern",
    "StrategyFactory",
    "TextAnchorStrategy",
    "AttributeMatchStrategy",
    "DOMRelationshipStrategy",
    "RoleBasedStrategy"
]
