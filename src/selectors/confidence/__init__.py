"""
Confidence management components for Selector Engine.

This module provides confidence threshold management, validation rules,
and quality control automation as specified in the API contracts.
"""

from .thresholds import ConfidenceThresholdManager, get_threshold_manager

__all__ = [
    "ConfidenceThresholdManager",
    "get_threshold_manager"
]
