"""
Snapshot Capture Service for capturing DOM snapshots at failure time.

This service integrates with the failure detection system to capture
DOM snapshots when selector failures occur.
"""

import asyncio
import gzip
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING

from ..db.repositories.snapshot_repository import SnapshotRepository
from ..db.repositories.failure_event_repository import FailureEventRepository
from ..db.models import FailureEvent
from ..db.models.snapshot import Snapshot

if TYPE_CHECKING:
    from src.observability.events import Event


class SnapshotCaptureService:
    """
    Service for capturing DOM snapshots at failure time.
    
    This service:
    - Subscribes to selector failure events
    - Captures DOM snapshots using Playwright
    - Stores snapshots with metadata in the database
    - Provides retrieval and cleanup capabilities
    """
    
    # Default retention settings
    DEFAULT_RETENTION_DAYS = 30
    DEFAULT_MAX_SNAPSHOTS = 1000
    
    def __init__(
        self,
        snapshot_repository: SnapshotRepository,
        failure_repository: Optional[FailureEventRepository] = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        max_snapshots: int = DEFAULT_MAX_SNAPSHOTS,
    ):
        """
        Initialize the snapshot capture service.
        
        Args:
            snapshot_repository: Repository for storing snapshots
            failure_repository: Optional failure event repository for linking
            retention_days: Number of days to retain snapshots
            max_snapshots: Maximum number of snapshots to store
        """
        self.snapshot_repo = snapshot_repository
        self.failure_repo = failure_repository
        self.retention_days = retention_days
        self.max_snapshots = max_snapshots
        self._subscription_id: Optional[str] = None
        self._event_bus = None
    
    async def capture_on_failure(
        self,
        failure_event: FailureEvent,
        page: Any = None,
        html_content: Optional[str] = None,
    ) -> Optional["Snapshot"]:
        """
        Capture a DOM snapshot when a failure is detected.
        
        This method can be called in two ways:
        1. With a Playwright page object - will capture the current page content
        2. With pre-captured HTML content
        
        Args:
            failure_event: The failure event to link the snapshot to
            page: Optional Playwright page object for capturing
            html_content: Optional pre-captured HTML content
            
        Returns:
            Created Snapshot instance or None if capture failed
        """
        try:
            # Get HTML content either from page or provided content
            if page is not None:
                html_content = await self._capture_page_content(page)
            elif html_content is None:
                return None
            
            # Get viewport size and user agent
            viewport_size = None
            user_agent = None
            
            if page is not None:
                viewport_size = page.viewport_size
                try:
                    user_agent = await page.evaluate("navigator.userAgent")
                except Exception:
                    pass
            
            # Create the snapshot
            snapshot = self.snapshot_repo.create_snapshot(
                html_content=html_content,
                failure_id=failure_event.id,
                viewport_size=viewport_size,
                user_agent=user_agent,
                url=await self._get_page_url(page) if page else None,
                selector_context=failure_event.selector_id,
                correlation_id=failure_event.correlation_id,
            )
            
            return snapshot
            
        except Exception as e:
            # Log error but don't fail the failure detection
            import logging
            logging.getLogger(__name__).error(
                f"Failed to capture snapshot for failure {failure_event.id}: {e}"
            )
            return None
    
    async def _capture_page_content(self, page: Any) -> str:
        """
        Capture page content using Playwright.
        
        Args:
            page: Playwright page object
            
        Returns:
            HTML content of the page
        """
        return await page.content()
    
    async def _get_page_url(self, page: Any) -> Optional[str]:
        """
        Get current page URL.
        
        Args:
            page: Playwright page object
            
        Returns:
            Current URL or None
        """
        try:
            return page.url
        except Exception:
            return None
    
    async def capture_with_context(
        self,
        selector_id: str,
        html_content: str,
        failure_id: Optional[int] = None,
        viewport_size: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None,
        url: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> "Snapshot":
        """
        Capture a snapshot with explicit context (no Playwright needed).
        
        This is useful when HTML content is already available.
        
        Args:
            selector_id: The selector that failed
            html_content: HTML content to store
            failure_id: Optional failure event ID
            viewport_size: Optional viewport dimensions
            user_agent: Optional browser user agent
            url: Optional page URL
            correlation_id: Optional correlation ID
            
        Returns:
            Created Snapshot instance
        """
        return self.snapshot_repo.create_snapshot(
            html_content=html_content,
            failure_id=failure_id,
            viewport_size=viewport_size,
            user_agent=user_agent,
            url=url,
            selector_context=selector_id,
            correlation_id=correlation_id,
        )
    
    async def handle_event(self, event: "Event") -> None:
        """
        Handle selector failed event from the event bus.
        
        This is the event handler that gets called when a selector.failed
        event is published.
        
        Args:
            event: Event from the event bus
        """
        data = event.data
        
        # Extract failure details from event
        selector_name = data.get("selector_name", "")
        correlation_id = event.correlation_id
        
        # Get HTML content if available in event
        html_content = data.get("html_content")
        
        # Get viewport info if available
        viewport_size = data.get("viewport_size")
        user_agent = data.get("user_agent")
        url = data.get("url")
        
        # Create snapshot with the available context
        await self.capture_with_context(
            selector_id=selector_name,
            html_content=html_content or "<html><body>No content available</body></html>",
            failure_id=data.get("failure_id"),
            viewport_size=viewport_size,
            user_agent=user_agent,
            url=url,
            correlation_id=correlation_id,
        )
    
    def subscribe_to_events(self) -> str:
        """
        Subscribe to selector.failed events from the event bus.
        
        Returns:
            Subscription ID
        """
        from src.observability.events import (
            EventTypes, 
            subscribe_to_events,
        )
        
        # Store reference to unsubscribe later
        self._subscription_id = subscribe_to_events(
            EventTypes.SELECTOR_FAILED,
            self.handle_event,
        )
        
        return self._subscription_id
    
    def unsubscribe_from_events(self) -> bool:
        """
        Unsubscribe from selector.failed events.
        
        Returns:
            True if unsubscribed successfully
        """
        from src.observability.events import unsubscribe_from_events
        
        if self._subscription_id:
            result = unsubscribe_from_events(self._subscription_id)
            self._subscription_id = None
            return result
        return False
    
    def cleanup_old_snapshots(self) -> int:
        """
        Clean up snapshots older than retention period.
        
        Returns:
            Number of snapshots deleted
        """
        return self.snapshot_repo.delete_old_snapshots(self.retention_days)
    
    def cleanup_excess_snapshots(self) -> int:
        """
        Clean up excess snapshots beyond max count.
        
        Returns:
            Number of snapshots deleted
        """
        return self.snapshot_repo.delete_excess_snapshots(self.max_snapshots)
    
    def run_cleanup(self) -> Dict[str, int]:
        """
        Run full cleanup (age-based and count-based).
        
        Returns:
            Dictionary with cleanup results
        """
        deleted_old = self.cleanup_old_snapshots()
        deleted_excess = self.cleanup_excess_snapshots()
        
        return {
            "deleted_old": deleted_old,
            "deleted_excess": deleted_excess,
            "total_deleted": deleted_old + deleted_excess,
        }
    
    def get_snapshot_by_id(self, snapshot_id: int):
        """
        Get a snapshot by ID.
        
        Args:
            snapshot_id: Snapshot ID
            
        Returns:
            Snapshot instance or None
        """
        return self.snapshot_repo.get_by_id(snapshot_id)
    
    def get_snapshots_by_failure(self, failure_id: int):
        """
        Get snapshots linked to a failure event.
        
        Args:
            failure_id: Failure event ID
            
        Returns:
            Snapshot instance or None
        """
        return self.snapshot_repo.get_by_failure_id(failure_id)
    
    def get_recent_snapshots(self, limit: int = 100):
        """
        Get recent snapshots.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of Snapshot instances
        """
        return self.snapshot_repo.get_recent_snapshots(limit=limit)
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        return self.snapshot_repo.get_storage_stats()
