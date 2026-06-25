"""
Storage extensions for adaptive selector system.

This module provides storage extensions that integrate with the existing
core snapshot system while adding adaptive-specific functionality.
"""

from .extension import AdaptiveStorageExtension, get_adaptive_storage

__all__ = [
    "AdaptiveStorageExtension",
    "get_adaptive_storage",
]
