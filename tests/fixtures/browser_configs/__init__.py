"""
Browser configuration fixtures for testing.

This module provides pre-configured browser settings for different
testing scenarios including stealth configurations and resource limits.
"""

from .chromium_headless import CHROMIUM_HEADLESS_CONFIG
from .firefox_stealth import FIREFOX_STEALTH_CONFIG
from .webkit_mobile import WEBKIT_MOBILE_CONFIG

__all__ = [
    "CHROMIUM_HEADLESS_CONFIG",
    "FIREFOX_STEALTH_CONFIG", 
    "WEBKIT_MOBILE_CONFIG"
]
