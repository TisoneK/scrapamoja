"""
Quality control components for Selector Engine.

This module provides quality control automation, adaptive threshold adjustment,
and comprehensive quality monitoring as specified in the API contracts.
"""

from .control import QualityControlManager, get_quality_control_manager

__all__ = [
    "QualityControlManager",
    "get_quality_control_manager"
]
