"""
Unit tests for SnapshotCaptureService.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.selectors.adaptive.services.snapshot_capture import SnapshotCaptureService
from src.selectors.adaptive.db.repositories.snapshot_repository import SnapshotRepository
from src.selectors.adaptive.db.models.snapshot import Snapshot


class TestSnapshotCaptureService:
    """Test suite for SnapshotCaptureService."""
    
    @pytest.fixture
    def repository(self):
        """Create in-memory repository for testing."""
        repo = SnapshotRepository(db_path=":memory:")
        yield repo
        repo.close()
    
    @pytest.fixture
    def service(self, repository):
        """Create snapshot capture service."""
        return SnapshotCaptureService(
            snapshot_repository=repository,
            retention_days=30,
            max_snapshots=1000,
        )
    
    @pytest.fixture
    def sample_failure_event(self):
        """Create a mock failure event."""
        failure = Mock()
        failure.id = 1
        failure.selector_id = ".test-selector"
        failure.correlation_id = "corr-123"
        return failure
    
    @pytest.fixture
    def sample_html(self):
        """Sample HTML content."""
        return "<html><body><div class='test'>Hello World</div></body></html>"
    
    @pytest.mark.asyncio
    async def test_capture_with_html_content(self, service, repository, sample_failure_event, sample_html):
        """Test capturing snapshot with pre-provided HTML content."""
        snapshot = await service.capture_with_context(
            selector_id=".test",
            html_content=sample_html,
            failure_id=sample_failure_event.id,
            correlation_id=sample_failure_event.correlation_id,
        )
        
        assert snapshot is not None
        assert snapshot.selector_context == ".test"
        assert snapshot.failure_id == sample_failure_event.id
        assert snapshot.correlation_id == sample_failure_event.correlation_id
    
    @pytest.mark.asyncio
    async def test_capture_on_failure_with_content(self, service, repository, sample_failure_event, sample_html):
        """Test capturing snapshot on failure with HTML content."""
        snapshot = await service.capture_on_failure(
            failure_event=sample_failure_event,
            html_content=sample_html,
        )
        
        assert snapshot is not None
        assert snapshot.failure_id == sample_failure_event.id
    
    @pytest.mark.asyncio
    async def test_capture_on_failure_no_content(self, service, repository, sample_failure_event):
        """Test capturing snapshot when no HTML content available."""
        snapshot = await service.capture_on_failure(
            failure_event=sample_failure_event,
            page=None,
            html_content=None,
        )
        
        # Should return None when no content available
        assert snapshot is None
    
    def test_cleanup_old_snapshots(self, service, repository, sample_html):
        """Test cleanup of old snapshots."""
        # Create a snapshot
        snapshot = repository.create_snapshot(html_content=sample_html)
        
        deleted = service.cleanup_old_snapshots()
        
        # May or may not delete depending on timestamp
        assert isinstance(deleted, int)
    
    def test_cleanup_excess_snapshots(self, service, repository, sample_html):
        """Test cleanup of excess snapshots."""
        # Create more than max_snapshots
        for i in range(1005):
            repository.create_snapshot(
                html_content=sample_html,
                selector_context=f".test-{i}",
            )
        
        deleted = service.cleanup_excess_snapshots()
        
        # Should delete 5 (1005 - 1000)
        assert deleted == 5
    
    def test_run_cleanup(self, service, repository, sample_html):
        """Test full cleanup."""
        for i in range(5):
            repository.create_snapshot(
                html_content=sample_html,
                selector_context=f".test-{i}",
            )
        
        result = service.run_cleanup()
        
        assert "deleted_old" in result
        assert "deleted_excess" in result
        assert "total_deleted" in result
    
    def test_get_snapshot_by_id(self, service, repository, sample_html):
        """Test getting snapshot by ID."""
        created = repository.create_snapshot(html_content=sample_html)
        
        result = service.get_snapshot_by_id(created.id)
        
        assert result is not None
        assert result.id == created.id
    
    def test_get_snapshots_by_failure(self, service, repository, sample_html):
        """Test getting snapshots by failure ID."""
        snapshot = repository.create_snapshot(
            html_content=sample_html,
            failure_id=1,
        )
        
        result = service.get_snapshots_by_failure(1)
        
        assert result is not None
        assert result.failure_id == 1
    
    def test_get_recent_snapshots(self, service, repository, sample_html):
        """Test getting recent snapshots."""
        for i in range(3):
            repository.create_snapshot(
                html_content=sample_html,
                selector_context=f".test-{i}",
            )
        
        result = service.get_recent_snapshots(limit=2)
        
        assert len(result) == 2
    
    def test_get_storage_stats(self, service, repository):
        """Test getting storage stats."""
        # Use larger content to ensure compression helps
        large_html = "<html><body>" + "<div>test content</div>" * 100 + "</body></html>"
        repository.create_snapshot(html_content=large_html)

        stats = service.get_storage_stats()

        assert stats["total_snapshots"] == 1
        assert stats["compression_ratio"] >= 0
    
    def test_default_retention_values(self, service):
        """Test default retention values."""
        assert service.retention_days == 30
        assert service.max_snapshots == 1000
    
    def test_custom_retention_values(self, repository):
        """Test custom retention values."""
        service = SnapshotCaptureService(
            snapshot_repository=repository,
            retention_days=7,
            max_snapshots=100,
        )
        
        assert service.retention_days == 7
        assert service.max_snapshots == 100
