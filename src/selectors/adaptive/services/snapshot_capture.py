"""
Snapshot Capture Service for capturing DOM snapshots during selector failures.

Provides a high-level interface for capturing, storing, and cleaning up
DOM snapshots with configurable retention policies.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from ..db.repositories.snapshot_repository import SnapshotRepository
from ..db.models.snapshot import Snapshot
from src.observability.logger import get_logger


class SnapshotCaptureService:
    """Service for capturing and managing DOM snapshots on selector failures."""

    def __init__(
        self,
        snapshot_repository: Optional[SnapshotRepository] = None,
        retention_days: int = 30,
        max_snapshots: int = 1000,
    ):
        """Initialize snapshot capture service.

        Args:
            snapshot_repository: Repository for snapshot persistence.
            retention_days: Days to retain snapshots before cleanup.
            max_snapshots: Maximum number of snapshots to keep.
        """
        self._logger = get_logger("snapshot_capture_service")
        self._repository = snapshot_repository or SnapshotRepository()
        self.retention_days = retention_days
        self.max_snapshots = max_snapshots

    @property
    def repository(self) -> SnapshotRepository:
        """Get the underlying repository."""
        return self._repository

    async def capture_with_context(
        self,
        selector_id: str,
        html_content: Optional[str] = None,
        failure_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        viewport_size: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Optional[Snapshot]:
        """Capture a snapshot with provided context.

        Args:
            selector_id: CSS selector that failed.
            html_content: HTML content to snapshot.
            failure_id: Associated failure event ID.
            correlation_id: Correlation ID for tracing.
            viewport_size: Browser viewport dimensions.
            user_agent: Browser user agent string.
            url: Page URL.

        Returns:
            Created Snapshot or None if no content provided.
        """
        if not html_content:
            self._logger.warning("No HTML content provided for snapshot capture")
            return None

        return self._repository.create_snapshot(
            html_content=html_content,
            failure_id=failure_id,
            viewport_size=viewport_size,
            user_agent=user_agent,
            url=url,
            selector_context=selector_id,
            correlation_id=correlation_id,
        )

    async def capture_on_failure(
        self,
        failure_event: Any,
        html_content: Optional[str] = None,
        page: Any = None,
    ) -> Optional[Snapshot]:
        """Capture a snapshot when a selector failure occurs.

        Args:
            failure_event: The failure event that triggered the capture.
            html_content: Pre-provided HTML content.
            page: Playwright page to extract content from.

        Returns:
            Created Snapshot or None if no content available.
        """
        if html_content is None and page is not None:
            try:
                html_content = await page.content()
            except Exception as e:
                self._logger.error(f"Failed to extract HTML from page: {e}")
                return None

        if html_content is None:
            return None

        return self._repository.create_snapshot(
            html_content=html_content,
            failure_id=getattr(failure_event, "id", None),
            selector_context=getattr(failure_event, "selector_id", None),
            correlation_id=getattr(failure_event, "correlation_id", None),
        )

    def cleanup_old_snapshots(self) -> int:
        """Delete snapshots older than retention_days.

        Returns:
            Number of snapshots deleted.
        """
        return self._repository.delete_old_snapshots(days_old=self.retention_days)

    def cleanup_excess_snapshots(self) -> int:
        """Delete oldest snapshots exceeding max_snapshots limit.

        Returns:
            Number of snapshots deleted.
        """
        return self._repository.delete_excess_snapshots(keep_count=self.max_snapshots)

    def run_cleanup(self) -> Dict[str, int]:
        """Run full cleanup (old + excess).

        Returns:
            Dictionary with deletion counts.
        """
        deleted_old = self.cleanup_old_snapshots()
        deleted_excess = self.cleanup_excess_snapshots()
        return {
            "deleted_old": deleted_old,
            "deleted_excess": deleted_excess,
            "total_deleted": deleted_old + deleted_excess,
        }

    def get_snapshot_by_id(self, snapshot_id: int) -> Optional[Snapshot]:
        """Get snapshot by ID."""
        return self._repository.get_by_id(snapshot_id)

    def get_snapshots_by_failure(self, failure_id: int) -> Optional[Snapshot]:
        """Get most recent snapshot by failure ID."""
        return self._repository.get_by_failure_id(failure_id)

    def get_recent_snapshots(self, limit: int = 10) -> List[Snapshot]:
        """Get recent snapshots."""
        return self._repository.get_recent_snapshots(limit=limit)

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return self._repository.get_storage_stats()
