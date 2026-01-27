"""
Browser Model Enums

This module defines enumerations for browser lifecycle management.
"""

from enum import Enum


class SessionStatus(Enum):
    """Browser session lifecycle states."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    CLOSING = "closing"
    TERMINATED = "terminated"
    FAILED = "failed"
    CLEANUP_ERROR = "cleanup_error"


class AlertStatus(Enum):
    """Resource alert status levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class BrowserType(Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class CleanupLevel(Enum):
    """Resource cleanup levels."""
    GENTLE = "gentle"      # Close inactive tabs only
    MODERATE = "moderate"  # Close tabs and clear cache
    AGGRESSIVE = "aggressive"  # Close everything and force cleanup
    FORCE = "force"        # Terminate processes


class ContextStatus(Enum):
    """Browser context/tab status."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    LOADING = "loading"
    IDLE = "idle"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


class StateStatus(Enum):
    """Browser state persistence status."""
    SAVING = "saving"
    SAVED = "saved"
    LOADING = "loading"
    LOADED = "loaded"
    CORRUPTED = "corrupted"
    EXPIRED = "expired"


class ProxyType(Enum):
    """Proxy connection types."""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"
