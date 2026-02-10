"""
Browser configuration and settings management.

This module provides configuration classes for browser instances including
stealth settings, resource limits, and session parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import json


class BrowserType(Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class SessionStatus(Enum):
    """Browser session lifecycle states."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    CLOSING = "closing"
    TERMINATED = "terminated"
    FAILED = "failed"
    CLEANUP_ERROR = "cleanup_error"


@dataclass
class StealthConfiguration:
    """Stealth settings for anti-bot detection avoidance."""
    user_agent: Optional[str] = None
    viewport: Optional[Dict[str, int]] = None
    locale: str = "en-US"
    timezone: str = "America/New_York"
    geolocation: Optional[Dict[str, float]] = None
    permissions: List[str] = field(default_factory=lambda: ["geolocation"])
    extra_http_headers: Dict[str, str] = field(default_factory=dict)
    bypass_csp: bool = True
    ignore_https_errors: bool = False


@dataclass
class ResourceLimits:
    """Resource usage limits for browser sessions."""
    max_memory_mb: int = 1024
    max_cpu_percent: float = 80.0
    max_tab_count: int = 10
    session_timeout_minutes: int = 30
    cleanup_threshold_memory: float = 0.8
    cleanup_threshold_cpu: float = 0.9


@dataclass
class BrowserConfiguration:
    """Complete configuration for browser sessions."""
    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = True
    stealth: StealthConfiguration = field(default_factory=StealthConfiguration)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    proxy: Optional[Dict[str, Any]] = None
    launch_options: Dict[str, Any] = field(default_factory=dict)
    context_options: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "browser_type": self.browser_type.value,
            "headless": self.headless,
            "stealth": {
                "user_agent": self.stealth.user_agent,
                "viewport": self.stealth.viewport,
                "locale": self.stealth.locale,
                "timezone": self.stealth.timezone,
                "geolocation": self.stealth.geolocation,
                "permissions": self.stealth.permissions,
                "extra_http_headers": self.stealth.extra_http_headers,
                "bypass_csp": self.stealth.bypass_csp,
                "ignore_https_errors": self.stealth.ignore_https_errors
            },
            "resource_limits": {
                "max_memory_mb": self.resource_limits.max_memory_mb,
                "max_cpu_percent": self.resource_limits.max_cpu_percent,
                "max_tab_count": self.resource_limits.max_tab_count,
                "session_timeout_minutes": self.resource_limits.session_timeout_minutes,
                "cleanup_threshold_memory": self.resource_limits.cleanup_threshold_memory,
                "cleanup_threshold_cpu": self.resource_limits.cleanup_threshold_cpu
            },
            "proxy": self.proxy,
            "launch_options": self.launch_options,
            "context_options": self.context_options
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrowserConfiguration":
        """Create configuration from dictionary."""
        config = cls()
        
        # Browser type
        if "browser_type" in data:
            config.browser_type = BrowserType(data["browser_type"])
        
        # Headless mode
        if "headless" in data:
            config.headless = data["headless"]
        
        # Stealth configuration
        if "stealth" in data:
            stealth_data = data["stealth"]
            config.stealth = StealthConfiguration(
                user_agent=stealth_data.get("user_agent"),
                viewport=stealth_data.get("viewport"),
                locale=stealth_data.get("locale", "en-US"),
                timezone=stealth_data.get("timezone", "America/New_York"),
                geolocation=stealth_data.get("geolocation"),
                permissions=stealth_data.get("permissions", ["geolocation"]),
                extra_http_headers=stealth_data.get("extra_http_headers", {}),
                bypass_csp=stealth_data.get("bypass_csp", True),
                ignore_https_errors=stealth_data.get("ignore_https_errors", False)
            )
        
        # Resource limits
        if "resource_limits" in data:
            limits_data = data["resource_limits"]
            config.resource_limits = ResourceLimits(
                max_memory_mb=limits_data.get("max_memory_mb", 1024),
                max_cpu_percent=limits_data.get("max_cpu_percent", 80.0),
                max_tab_count=limits_data.get("max_tab_count", 10),
                session_timeout_minutes=limits_data.get("session_timeout_minutes", 30),
                cleanup_threshold_memory=limits_data.get("cleanup_threshold_memory", 0.8),
                cleanup_threshold_cpu=limits_data.get("cleanup_threshold_cpu", 0.9)
            )
        
        # Proxy and options
        config.proxy = data.get("proxy")
        config.launch_options = data.get("launch_options", {})
        config.context_options = data.get("context_options", {})
        
        return config
