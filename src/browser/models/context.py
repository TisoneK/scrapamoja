"""
Tab Context Entity

This module defines the TabContext entity for browser tab management.
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import structlog

from .enums import ContextStatus


@dataclass
class NavigationHistory:
    """Navigation history for a browser context."""
    urls: List[str] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    titles: List[str] = field(default_factory=list)
    max_entries: int = 100
    
    def add_navigation(self, url: str, title: Optional[str] = None) -> None:
        """Add a navigation entry."""
        self.urls.append(url)
        self.timestamps.append(time.time())
        self.titles.append(title or "")
        
        # Limit history size
        if len(self.urls) > self.max_entries:
            self.urls.pop(0)
            self.timestamps.pop(0)
            self.titles.pop(0)
            
    def get_current_url(self) -> Optional[str]:
        """Get current URL."""
        return self.urls[-1] if self.urls else None
        
    def get_current_title(self) -> Optional[str]:
        """Get current page title."""
        return self.titles[-1] if self.titles else None
        
    def get_history_count(self) -> int:
        """Get number of navigation entries."""
        return len(self.urls)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "urls": self.urls.copy(),
            "timestamps": self.timestamps.copy(),
            "titles": self.titles.copy(),
            "max_entries": self.max_entries,
            "current_url": self.get_current_url(),
            "current_title": self.get_current_title(),
            "history_count": self.get_history_count()
        }


class TabContext:
    """Represents a browser tab with its own navigation history and DOM state."""
    
    def __init__(
        self,
        context_id: str,
        session_id: str,
        url: Optional[str] = None,
        title: Optional[str] = None
    ):
        self.context_id = context_id
        self.session_id = session_id
        self.url = url
        self.title = title
        self.navigation_history = NavigationHistory()
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.is_active = False
        self.dom_state: Optional[Dict[str, Any]] = None
        self.status = ContextStatus.INITIALIZING
        
        # Internal state
        self._playwright_context = None
        self._playwright_page = None
        self._lock = asyncio.Lock()
        self.logger = structlog.get_logger("browser.context")
        
        # Add initial navigation if URL provided
        if url:
            self.navigation_history.add_navigation(url, title)
            
    def update_status(self, new_status: ContextStatus) -> None:
        """Update context status."""
        old_status = self.status
        self.status = new_status
        self.last_activity = datetime.now()
        
        self.logger.info(
            "Context status updated",
            context_id=self.context_id,
            session_id=self.session_id,
            old_status=old_status.value,
            new_status=new_status.value
        )
        
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
        
    def navigate_to(self, url: str, title: Optional[str] = None) -> None:
        """Record navigation to new URL."""
        self.url = url
        self.title = title
        self.navigation_history.add_navigation(url, title)
        self.update_activity()
        
        self.logger.info(
            "Navigation recorded",
            context_id=self.context_id,
            session_id=self.session_id,
            url=url,
            title=title
        )
        
    def update_title(self, title: str) -> None:
        """Update page title."""
        self.title = title
        self.update_activity()
        
    def set_active(self, active: bool) -> None:
        """Set context as active/inactive."""
        self.is_active = active
        self.update_activity()
        
    def update_dom_state(self, dom_state: Dict[str, Any]) -> None:
        """Update DOM state snapshot."""
        self.dom_state = dom_state
        self.update_activity()
        
    def is_healthy(self) -> bool:
        """Check if context is healthy."""
        return self.status in [ContextStatus.INITIALIZING, ContextStatus.ACTIVE, ContextStatus.IDLE]
        
    def can_navigate(self) -> bool:
        """Check if context can navigate to new URLs."""
        return self.is_healthy() and self.status != ContextStatus.CLOSING
        
    def get_context_age_seconds(self) -> float:
        """Get context age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
        
    def get_idle_time_seconds(self) -> float:
        """Get idle time in seconds."""
        return (datetime.now() - self.last_activity).total_seconds()
        
    def get_navigation_count(self) -> int:
        """Get number of navigations."""
        return self.navigation_history.get_history_count()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "url": self.url,
            "title": self.title,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_active": self.is_active,
            "dom_state": self.dom_state,
            "navigation_history": self.navigation_history.to_dict(),
            "context_age_seconds": self.get_context_age_seconds(),
            "idle_time_seconds": self.get_idle_time_seconds(),
            "navigation_count": self.get_navigation_count()
        }
        
    async def validate_state(self) -> bool:
        """Validate context state and consistency."""
        async with self._lock:
            try:
                # Validate navigation history consistency
                if self.url and self.navigation_history.get_current_url() != self.url:
                    self.logger.warning(
                        "URL mismatch between context and navigation history",
                        context_id=self.context_id,
                        context_url=self.url,
                        history_url=self.navigation_history.get_current_url()
                    )
                    return False
                    
                # Validate status
                if self.status == ContextStatus.ACTIVE and not self._playwright_page:
                    self.logger.warning(
                        "Context marked active but no page instance",
                        context_id=self.context_id
                    )
                    return False
                    
                return True
                
            except Exception as e:
                self.logger.error(
                    "Context validation failed",
                    context_id=self.context_id,
                    error=str(e),
                    error_type=type(e).__name__
                )
                return False
                
    def __str__(self) -> str:
        """String representation."""
        return f"TabContext(id={self.context_id}, url={self.url}, status={self.status.value})"
        
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"TabContext(context_id={self.context_id}, "
                f"session_id={self.session_id}, "
                f"url={self.url}, "
                f"title={self.title}, "
                f"status={self.status.value}, "
                f"active={self.is_active}, "
                f"created={self.created_at.isoformat()})")
    
    async def verify_isolation(self) -> Dict[str, bool]:
        """Verify tab isolation from other contexts."""
        isolation_results = {
            "navigation_history_isolated": True,
            "dom_state_isolated": True,
            "status_isolated": True,
            "activity_isolated": True
        }
        
        try:
            # Verify navigation history isolation
            if self.navigation_history.get_current_url() != self.url:
                isolation_results["navigation_history_isolated"] = False
                self.logger.warning(
                    "Navigation history isolation violation",
                    context_id=self.context_id,
                    expected_url=self.url,
                    actual_url=self.navigation_history.get_current_url()
                )
            
            # Verify DOM state isolation (if available)
            if self.dom_state and self._playwright_page:
                try:
                    current_url = self._playwright_page.url
                    if current_url != self.url:
                        isolation_results["dom_state_isolated"] = False
                        self.logger.warning(
                            "DOM state isolation violation",
                            context_id=self.context_id,
                            expected_url=self.url,
                            actual_url=current_url
                        )
                except Exception as e:
                    self.logger.warning(
                        "DOM state verification failed",
                        context_id=self.context_id,
                        error=str(e)
                    )
            
            # Verify status consistency
            if self.status == ContextStatus.ACTIVE and not self.is_active:
                isolation_results["status_isolated"] = False
                self.logger.warning(
                    "Status isolation violation",
                    context_id=self.context_id,
                    status=self.status.value,
                    is_active=self.is_active
                )
            
            # Verify activity tracking
            if self.get_idle_time_seconds() < 0:
                isolation_results["activity_isolated"] = False
                self.logger.warning(
                    "Activity tracking isolation violation",
                    context_id=self.context_id,
                    idle_time=self.get_idle_time_seconds()
                )
            
        except Exception as e:
            self.logger.error(
                "Isolation verification failed",
                context_id=self.context_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Mark all as failed on exception
            for key in isolation_results:
                isolation_results[key] = False
        
        return isolation_results
    
    async def cleanup_resources(self) -> bool:
        """Clean up tab resources and state."""
        try:
            cleanup_success = True
            
            # Clear navigation history
            if self.navigation_history:
                self.navigation_history.urls.clear()
                self.navigation_history.timestamps.clear()
                self.navigation_history.titles.clear()
            
            # Clear DOM state
            self.dom_state = None
            
            # Clear Playwright references
            if self._playwright_page:
                try:
                    await self._playwright_page.close()
                except Exception as e:
                    self.logger.warning(
                        "Page cleanup failed",
                        context_id=self.context_id,
                        error=str(e)
                    )
                    cleanup_success = False
                finally:
                    self._playwright_page = None
            
            if self._playwright_context:
                try:
                    await self._playwright_context.close()
                except Exception as e:
                    self.logger.warning(
                        "Context cleanup failed",
                        context_id=self.context_id,
                        error=str(e)
                    )
                    cleanup_success = False
                finally:
                    self._playwright_context = None
            
            # Update status
            self.update_status(ContextStatus.CLOSED)
            
            # Clear activity tracking
            self.is_active = False
            
            self.logger.info(
                "Tab resources cleaned up",
                context_id=self.context_id,
                cleanup_success=cleanup_success
            )
            
            return cleanup_success
            
        except Exception as e:
            self.logger.error(
                "Tab cleanup failed",
                context_id=self.context_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def isolate_from_other_tabs(self, other_tabs: List['TabContext']) -> Dict[str, bool]:
        """Ensure isolation from other tabs and resolve conflicts."""
        isolation_results = {
            "url_conflicts_resolved": True,
            "title_conflicts_resolved": True,
            "state_conflicts_resolved": True,
            "resource_conflicts_resolved": True
        }
        
        try:
            # Check for URL conflicts
            conflicting_urls = [
                tab for tab in other_tabs 
                if tab.context_id != self.context_id and tab.url == self.url
            ]
            
            if conflicting_urls:
                # Add timestamp to URL to make it unique
                timestamp = int(time.time())
                self.url = f"{self.url}?tab_id={self.context_id}&t={timestamp}"
                self.logger.info(
                    "URL conflict resolved",
                    context_id=self.context_id,
                    original_url=self.url.split('?')[0],
                    new_url=self.url,
                    conflicting_tabs=[tab.context_id for tab in conflicting_urls]
                )
            
            # Check for title conflicts
            conflicting_titles = [
                tab for tab in other_tabs 
                if tab.context_id != self.context_id and tab.title == self.title
            ]
            
            if conflicting_titles:
                # Add context ID to title to make it unique
                self.title = f"{self.title} ({self.context_id[:8]})"
                self.logger.info(
                    "Title conflict resolved",
                    context_id=self.context_id,
                    original_title=self.title.split(' (')[0],
                    new_title=self.title,
                    conflicting_tabs=[tab.context_id for tab in conflicting_titles]
                )
            
            # Verify no shared Playwright instances
            for tab in other_tabs:
                if tab.context_id != self.context_id:
                    if (tab._playwright_page == self._playwright_page or 
                        tab._playwright_context == self._playwright_context):
                        isolation_results["resource_conflicts_resolved"] = False
                        self.logger.error(
                            "Resource sharing detected",
                            context_id=self.context_id,
                            conflicting_tab=tab.context_id,
                            shared_page=tab._playwright_page == self._playwright_page,
                            shared_context=tab._playwright_context == self._playwright_context
                        )
            
            # Verify state isolation
            current_isolation = await self.verify_isolation()
            isolation_results["state_conflicts_resolved"] = all(current_isolation.values())
            
        except Exception as e:
            self.logger.error(
                "Tab isolation check failed",
                context_id=self.context_id,
                error=str(e),
                error_type=type(e).__name__
            )
            for key in isolation_results:
                isolation_results[key] = False
        
        return isolation_results
