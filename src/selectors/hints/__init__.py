"""
Selector hints module for YAML hint schema reading.

This module provides functionality for parsing and working with selector hints
from YAML configurations, including stability scores, priorities, and alternatives.
"""

from .models import HintSchema, SelectorHint
from .parser import parse_hints
from .strategy import HintBasedFallbackStrategy

__all__ = ["SelectorHint", "HintSchema", "parse_hints", "HintBasedFallbackStrategy"]
