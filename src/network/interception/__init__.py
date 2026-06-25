"""Network interception module for capturing browser network traffic.

This module provides network response interception capabilities.
"""

from src.network.interception.exceptions import PatternError, TimingError
from src.network.interception.interceptor import (
    InterceptionConfig,
    NetworkInterceptor,
    NetworkListener,
    create_network_error,
)
from src.network.interception.models import CapturedResponse, InterceptedResponse
from src.network.interception.patterns import (
    is_regex_pattern,
    match_url,
    matches_prefix,
    matches_regex,
    matches_substring,
)

__all__ = [
    # New API
    "NetworkInterceptor",
    "CapturedResponse",
    "TimingError",
    "PatternError",
    # Pattern matching functions (for isolated testing)
    "matches_prefix",
    "matches_substring",
    "matches_regex",
    "match_url",
    "is_regex_pattern",
    # Backward compatibility
    "InterceptionConfig",
    "InterceptedResponse",
    "NetworkListener",
    "create_network_error",
]
