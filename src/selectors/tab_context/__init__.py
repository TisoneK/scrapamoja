"""
Tab context management components for Selector Engine.

This module provides tab context detection, management, and isolation
for SPA applications as specified in User Story 3.
"""

from .tab_manager import TabContextManager, get_tab_context_manager

__all__ = [
    "TabContextManager",
    "get_tab_context_manager"
]
