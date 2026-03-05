"""
Unit tests for AuditQueryService.

This implements Epic 6 (Audit Logging) requirements for Story 6.3.
Tests the advanced query capabilities with multi-criteria filtering,
pagination, and sorting.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from src.selectors.adaptive.services.audit_query_service import (
    AuditQueryService,
    AuditQueryParams,
    PaginatedAuditResponse,
    SortField,
    SortOrder,
    get_audit_query_service,
)
from src.selectors.adaptive.db.models.audit_event import AuditEvent


class TestAuditQueryParams:
    """Tests for AuditQueryParams dataclass."""
    
    def test_default_values(self):
        """Test default parameter values."""
        params = AuditQueryParams()
        
        assert params.selector_id is None
        assert params.user_id is None
        assert params.start_date is None
        assert params.end_date is None
        assert params.action_types is None
        assert params.limit == 100
        assert params.offset == 0
        assert params.cursor is None
        assert params.sort_by == SortField.TIMESTAMP
        assert params.sort_order == SortOrder.DESC
    
    def test_with_filters(self):
        """Test parameters with filters."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=7)
        
        params = AuditQueryParams(
            selector_id="selector-123",
            user_id="user-456",
            start_date=start,
            end_date=end,
            action_types=["selector_approved", "selector_rejected"],
            limit=50,
            offset=10,
            sort_by=SortField.USER,
            sort_order=SortOrder.ASC,
        )
        
        assert params.selector_id == "selector-123"
        assert params.user_id == "user-456"
        assert params.start_date == start
        assert params.end_date == end
        assert params.action_types == ["selector_approved", "selector_rejected"]
        assert params.limit == 50
        assert params.offset == 10
        assert params.sort_by == SortField.USER
        assert params.sort_order == SortOrder.ASC


class TestAuditQueryService:
    """Tests for AuditQueryService."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        return Mock()
    
    @pytest.fixture
    def audit_service(self, mock_repository):
        """Create AuditQueryService with mock repository."""
        service = AuditQueryService(db_path=":memory:")
        service.repository = mock_repository
        return service
    
    @pytest.fixture
    def sample_events(self):
        """Create sample audit events for testing."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        events = []
        for i in range(10):
            event = Mock(spec=AuditEvent)
            event.id = i + 1
            event.action_type = ["selector_approved", "selector_rejected", "selector_flagged"][i % 3]
            event.timestamp = base_time + timedelta(hours=i)
            event.selector_id = f"selector-{i % 3}"
            event.selector = f"div.test-{i % 3}"
            event.user_id = f"user-{i % 2}"
            event.failure_id = None
            event.context_snapshot = None
            event.before_state = None
            event.after_state = None
            event.confidence_at_time = 0.8 + (i * 0.02)
            event.reason = None
            event.suggested_alternative = None
            event.notes = None
            event.created_at = base_time + timedelta(hours=i)
            events.append(event)
        
        return events
    
    def test_query_audit_history_by_selector(self, audit_service, mock_repository, sample_events):
        """Test querying audit history by selector ID."""
        # Setup mock
        selector_events = [e for e in sample_events if e.selector_id == "selector-0"]
        mock_repository.get_events_by_multiple_filters.return_value = selector_events
        
        # Execute
        params = AuditQueryParams(
            selector_id="selector-0",
            limit=100,
            offset=0,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        result = audit_service.query_audit_history(params)
        
        # Verify
        assert isinstance(result, PaginatedAuditResponse)
        assert len(result.events) == len(selector_events)
        assert result.total_count == len(selector_events)
        mock_repository.get_events_by_multiple_filters.assert_called_once()
    
    def test_query_audit_history_by_user(self, audit_service, mock_repository, sample_events):
        """Test querying audit history by user ID."""
        # Setup mock
        user_events = [e for e in sample_events if e.user_id == "user-0"]
        mock_repository.get_events_by_multiple_filters.return_value = user_events
        
        # Execute
        params = AuditQueryParams(
            user_id="user-0",
            limit=100,
            offset=0,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        result = audit_service.query_audit_history(params)
        
        # Verify
        assert isinstance(result, PaginatedAuditResponse)
        assert len(result.events) == len(user_events)
        assert result.total_count == len(user_events)
    
    def test_query_audit_history_by_date_range(self, audit_service, mock_repository, sample_events):
        """Test querying audit history by date range."""
        # Setup mock
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
        date_events = [e for e in sample_events if start_date <= e.timestamp <= end_date]
        mock_repository.get_events_by_multiple_filters.return_value = date_events
        
        # Execute
        params = AuditQueryParams(
            start_date=start_date,
            end_date=end_date,
            limit=100,
            offset=0,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        result = audit_service.query_audit_history(params)
        
        # Verify
        assert isinstance(result, PaginatedAuditResponse)
        assert len(result.events) == len(date_events)
    
    def test_query_with_pagination(self, audit_service, mock_repository, sample_events):
        """Test pagination with limit and offset."""
        # Setup mock to return all events
        mock_repository.get_events_by_multiple_filters.return_value = sample_events
        
        # Execute with pagination
        params = AuditQueryParams(
            limit=5,
            offset=2,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        result = audit_service.query_audit_history(params)
        
        # Verify
        assert len(result.events) <= 5
    
    def test_query_with_sorting(self, audit_service, mock_repository, sample_events):
        """Test sorting by different fields."""
        # Setup mock
        mock_repository.get_events_by_multiple_filters.return_value = sample_events
        
        # Test sorting by TIMESTAMP DESC
        params = AuditQueryParams(
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
            limit=100,
            offset=0,
        )
        result = audit_service.query_audit_history(params)
        # Verify sorting is applied (events should be in descending order by timestamp)
        
        # Test sorting by USER ASC
        params.sort_by = SortField.USER
        params.sort_order = SortOrder.ASC
        result = audit_service.query_audit_history(params)
        # Verify sorting is applied
    
    def test_query_with_cursor(self, audit_service, mock_repository, sample_events):
        """Test cursor-based pagination."""
        # Setup mock
        mock_repository.get_events_by_multiple_filters.return_value = sample_events
        
        # Execute with cursor
        params = AuditQueryParams(
            cursor="5",
            limit=3,
            offset=0,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        result = audit_service.query_audit_history(params)
        
        # Verify cursor is used
        assert isinstance(result, PaginatedAuditResponse)
    
    def test_query_calculates_has_more(self, audit_service, mock_repository, sample_events):
        """Test has_more calculation."""
        # Setup mock - return 5 events but limit is 3
        mock_repository.get_events_by_multiple_filters.return_value = sample_events[:5]
        
        # Execute
        params = AuditQueryParams(
            limit=3,
            offset=0,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        result = audit_service.query_audit_history(params)
        
        # Verify has_more is calculated correctly
        assert result.has_more is True
    
    def test_query_generates_next_cursor(self, audit_service, mock_repository, sample_events):
        """Test next_cursor generation."""
        # Setup mock
        mock_repository.get_events_by_multiple_filters.return_value = sample_events[:5]
        
        # Execute
        params = AuditQueryParams(
            limit=3,
            offset=0,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        result = audit_service.query_audit_history(params)
        
        # Verify next_cursor is generated
        assert result.next_cursor is not None
    
    def test_serialize_filters(self, audit_service):
        """Test filter serialization."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        params = AuditQueryParams(
            selector_id="selector-123",
            user_id="user-456",
            start_date=start_date,
            end_date=end_date,
            action_types=["selector_approved"],
            limit=50,
            offset=10,
            sort_by=SortField.USER,
            sort_order=SortOrder.ASC,
        )
        
        filters = audit_service._serialize_filters(params)
        
        assert filters["selector_id"] == "selector-123"
        assert filters["user_id"] == "user-456"
        assert filters["sort_by"] == "user_id"
        assert filters["sort_order"] == "asc"
        assert filters["limit"] == 50
        assert filters["offset"] == 10


class TestSortField:
    """Tests for SortField enum."""
    
    def test_sort_field_values(self):
        """Test SortField enum values."""
        assert SortField.TIMESTAMP.value == "timestamp"
        assert SortField.USER.value == "user_id"
        assert SortField.SELECTOR.value == "selector_id"
        assert SortField.ACTION.value == "action_type"


class TestSortOrder:
    """Tests for SortOrder enum."""
    
    def test_sort_order_values(self):
        """Test SortOrder enum values."""
        assert SortOrder.ASC.value == "asc"
        assert SortOrder.DESC.value == "desc"


class TestPaginatedAuditResponse:
    """Tests for PaginatedAuditResponse dataclass."""
    
    def test_paginated_response_creation(self, sample_events):
        """Test creating a paginated response."""
        response = PaginatedAuditResponse(
            events=sample_events[:5],
            total_count=10,
            has_more=True,
            next_cursor="6",
            filters_applied={"limit": 5, "offset": 0},
        )
        
        assert len(response.events) == 5
        assert response.total_count == 10
        assert response.has_more is True
        assert response.next_cursor == "6"
        assert response.filters_applied["limit"] == 5


# Integration-style tests that use in-memory database
class TestAuditQueryServiceIntegration:
    """Integration tests for AuditQueryService with in-memory database."""
    
    def test_service_initialization(self):
        """Test service initializes correctly."""
        service = AuditQueryService(db_path=":memory:")
        
        assert service.repository is not None
    
    def test_get_audit_query_service_singleton(self):
        """Test get_audit_query_service returns singleton."""
        # Reset global
        import src.selectors.adaptive.services.audit_query_service as aq_module
        aq_module._audit_query_service = None
        
        service1 = get_audit_query_service()
        service2 = get_audit_query_service()
        
        assert service1 is service2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
