"""
Production Resilience & Reliability Module

This module provides comprehensive failure handling, retry mechanisms, checkpointing,
resource lifecycle control, and auto-abort policies for the Scorewise scraper.

Components:
- retry: Retry mechanisms with exponential backoff and failure classification
- checkpoint: Progress saving and resume capability with integrity validation
- resource: System resource monitoring and automatic cleanup
- abort: Intelligent failure detection and automatic shutdown policies
- failure_handler: Centralized failure coordination and recovery
"""

from .config import ResilienceConfiguration
from .failure_handler import FailureHandler

__version__ = "1.0.0"
__all__ = [
    "ResilienceConfiguration",
    "FailureHandler",
]
