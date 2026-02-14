"""
Browser Session Entity

This module defines the BrowserSession entity for browser lifecycle management,
following the data model specification.
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
import structlog

from ..exceptions import BrowserError


class SessionStatus(Enum):
    """Browser session lifecycle states."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    CLOSING = "closing"
    TERMINATED = "terminated"
    FAILED = "failed"
    CLEANUP_ERROR = "cleanup_error"


@dataclass
class ResourceMetrics:
    """Resource usage metrics for browser sessions."""
    session_id: str
    context_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    disk_usage_mb: float = 0.0
    network_requests_count: int = 0
    open_tabs_count: int = 0
    process_handles_count: int = 0
    alert_status: str = "normal"  # normal, warning, critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "context_id": self.context_id,
            "timestamp": self.timestamp,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "disk_usage_mb": self.disk_usage_mb,
            "network_requests_count": self.network_requests_count,
            "open_tabs_count": self.open_tabs_count,
            "process_handles_count": self.process_handles_count,
            "alert_status": self.alert_status
        }


@dataclass
class BrowserConfiguration:
    """Browser configuration settings."""
    config_id: str
    browser_type: str = "chromium"
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False
    user_agent: Optional[str] = None
    proxy_server: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    proxy_bypass_list: List[str] = field(default_factory=list)
    fingerprint_randomization: bool = True
    mouse_movement_simulation: bool = True
    typing_simulation: bool = True
    scroll_simulation: bool = True
    timing_randomization: bool = True
    permissions: List[str] = field(default_factory=list)
    ignore_https_errors: bool = False
    locale: str = "en-US"
    timezone: str = "America/New_York"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "config_id": self.config_id,
            "browser_type": self.browser_type,
            "headless": self.headless,
            "viewport": {
                "width": self.viewport_width,
                "height": self.viewport_height,
                "device_scale_factor": self.device_scale_factor,
                "is_mobile": self.is_mobile,
                "has_touch": self.has_touch
            },
            "user_agent": self.user_agent,
            "proxy_settings": {
                "server": self.proxy_server,
                "username": self.proxy_username,
                "password": self.proxy_password,
                "bypass_list": self.proxy_bypass_list
            } if self.proxy_server else None,
            "stealth_settings": {
                "fingerprint_randomization": self.fingerprint_randomization,
                "mouse_movement_simulation": self.mouse_movement_simulation,
                "typing_simulation": self.typing_simulation,
                "scroll_simulation": self.scroll_simulation,
                "timing_randomization": self.timing_randomization
            },
            "permissions": self.permissions,
            "ignore_https_errors": self.ignore_https_errors,
            "locale": self.locale,
            "timezone": self.timezone
        }


class BrowserSession:
    """Represents a browser instance with its configuration, state, and resource usage."""
    
    def __init__(
        self,
        session_id: str,
        browser_type: str,
        configuration: Optional[BrowserConfiguration] = None,
        process_id: Optional[int] = None,
        site: Optional[str] = None  # Add site context for hierarchical storage
    ):
        self.session_id = session_id
        self.browser_type = browser_type
        self.site = site  # Store site context for hierarchical storage
        self.configuration = configuration or BrowserConfiguration(
            config_id=f"default_{session_id}",
            browser_type=browser_type
        )
        self.status = SessionStatus.INITIALIZING
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.process_id = process_id
        self.resource_metrics = ResourceMetrics(session_id=session_id)
        self.contexts: List[str] = []  # List of context IDs
        self.logger = structlog.get_logger("browser.session")
        
        # Internal state
        self._playwright_browser = None
        self._lock = asyncio.Lock()
        
    def update_status(self, new_status: SessionStatus) -> None:
        """Update session status."""
        old_status = self.status
        self.status = new_status
        self.last_activity = datetime.now()
        
        self.logger.info(
            "Session status updated",
            session_id=self.session_id,
            old_status=old_status.value,
            new_status=new_status.value
        )
        
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
        
    def add_context(self, context_id: str) -> None:
        """Add a context to this session."""
        if context_id not in self.contexts:
            self.contexts.append(context_id)
            self.update_activity()
            
    def remove_context(self, context_id: str) -> None:
        """Remove a context from this session."""
        if context_id in self.contexts:
            self.contexts.remove(context_id)
            self.update_activity()
            
    def update_resource_metrics(self, metrics: ResourceMetrics) -> None:
        """Update resource metrics."""
        self.resource_metrics = metrics
        self.update_activity()
        
    def is_active(self) -> bool:
        """Check if session is in active state."""
        return self.status == SessionStatus.ACTIVE
        
    def is_healthy(self) -> bool:
        """Check if session is healthy."""
        return self.status in [SessionStatus.INITIALIZING, SessionStatus.ACTIVE]
        
    def can_create_context(self) -> bool:
        """Check if session can create new contexts."""
        return self.is_active() and self.status != SessionStatus.CLOSING
        
    def get_session_age_seconds(self) -> float:
        """Get session age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
        
    def get_idle_time_seconds(self) -> float:
        """Get idle time in seconds."""
        return (datetime.now() - self.last_activity).total_seconds()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "browser_type": self.browser_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "configuration": self.configuration.to_dict(),
            "resource_metrics": self.resource_metrics.to_dict(),
            "contexts": self.contexts.copy(),
            "process_id": self.process_id,
            "session_age_seconds": self.get_session_age_seconds(),
            "idle_time_seconds": self.get_idle_time_seconds()
        }
        
    async def validate_state(self) -> bool:
        """Validate session state and consistency."""
        async with self._lock:
            try:
                # Validate status transitions
                if self.status == SessionStatus.ACTIVE and not self._playwright_browser:
                    self.logger.warning(
                        "Session marked active but no browser instance",
                        session_id=self.session_id
                    )
                    return False
                    
                # Validate resource metrics
                if self.resource_metrics.memory_usage_mb < 0:
                    self.logger.warning(
                        "Invalid memory usage in metrics",
                        session_id=self.session_id,
                        memory_usage=self.resource_metrics.memory_usage_mb
                    )
                    return False
                    
                if not 0 <= self.resource_metrics.cpu_usage_percent <= 100:
                    self.logger.warning(
                        "Invalid CPU usage in metrics",
                        session_id=self.session_id,
                        cpu_usage=self.resource_metrics.cpu_usage_percent
                    )
                    return False
                    
                return True
                
            except Exception as e:
                self.logger.error(
                    "Session validation failed",
                    session_id=self.session_id,
                    error=str(e),
                    error_type=type(e).__name__
                )
                return False
                
    def __str__(self) -> str:
        """String representation."""
        return f"BrowserSession(id={self.session_id}, type={self.browser_type}, status={self.status.value})"
        
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"BrowserSession(id={self.session_id}, type={self.browser_type}, "
                f"status={self.status.value}, contexts={len(self.contexts)}, "
                f"created={self.created_at.isoformat()})")
