"""
Interrupt handling module for safe scraping operations.

This module provides comprehensive interrupt handling capabilities including:
- Signal capture and handling (SIGINT, SIGTERM)
- Resource cleanup coordination
- Data preservation during interrupts
- User feedback during shutdown
- Configurable shutdown behavior
"""

from .handler import InterruptHandler
from .resource_manager import ResourceManager
from .config import InterruptConfig
from .feedback import FeedbackProvider

__all__ = [
    'InterruptHandler',
    'ResourceManager', 
    'InterruptConfig',
    'FeedbackProvider'
]

__version__ = '1.0.0'
