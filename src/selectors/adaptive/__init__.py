"""
Adaptive module for selector API integration.

This module provides the AdaptiveAPIClient for calling the adaptive REST API
to get alternative selector suggestions when primary selectors fail.
"""

from src.selectors.adaptive.api_client import AdaptiveAPIClient
from src.selectors.adaptive.sync_adapter import SyncAdaptiveAPIClient

__all__ = ["AdaptiveAPIClient", "SyncAdaptiveAPIClient"]
