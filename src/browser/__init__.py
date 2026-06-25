"""
Browser Lifecycle Management Module.

This module provides centralized browser instance creation, session isolation,
resource monitoring, and state persistence for the Scorewise scraper system.

Features:
- Browser authority pattern with asyncio-compatible concurrent session management
- Automatic resource cleanup and monitoring
- Stealth configuration support
- State persistence and recovery
- Structured logging with correlation IDs
"""

from .session import BrowserSession, SessionStatus
from .manager import BrowserManager, get_browser_manager
from .config import BrowserConfiguration, BrowserType
from .monitoring import ResourceMetrics

__all__ = [
    "BrowserSession",
    "SessionStatus", 
    "BrowserManager",
    "get_browser_manager",
    "BrowserConfiguration",
    "BrowserType",
    "ResourceMetrics"
]
