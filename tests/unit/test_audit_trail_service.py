"""
Unit tests for AuditTrailService.

Tests for chronological ordering, connected decision detection, and user attribution.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from typing import List

from src.selectors.adaptive.services.audit_trail_service import AuditTrailService
from src.selectors.adaptive.db.models.audit_event import AuditEvent


@pytest.mark.unit
class TestAuditTrailService:
    """Test cases for AuditTrailService."""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock audit event repository."""
        return Mock()
    
    @pytest.fixture
    def audit_trail_service(self, mock_repository):
        """Create audit trail service with mocked repository."""
        with patch('src.selectors.adaptive.services.audit_trail_service.AuditEventRepository', return_value=mock_repository):
            return AuditTrailService()
    
    @pytest.fixture
    def sample_audit_events(self):
        """Create sample audit events for testing."""
        base_time = datetime.now(timezone.utc)
        return [
            AuditEvent(
                id=1,
                action_type="selector_approved",
                timestamp=base_time - timedelta(hours=3),
                selector_id="sel-001",
                selector="div.content",
                user_id="user1",
                after_state="div.content",
                confidence_at_time=0.85
            ),
            AuditEvent(
                id=2,
                action_type="selector_rejected",
                timestamp=base_time - timedelta(hours=2),
                selector_id="sel-001",
                selector="span.content",
                user_id="user2",
                before_state="span.content",
                reason="Too specific"
            ),
            AuditEvent(
                id=3,
                action_type="selector_approved",
                timestamp=base_time - timedelta(hours=1),
                selector_id="sel-002",
                selector="div.main",
                user_id="user1",
                after_state="div.main",
                confidence_at_time=0.92
            ),
            AuditEvent(
                id=4,
                action_type="selector_flagged",
                timestamp=base_time - timedelta(minutes=30),
                selector_id="sel-003",
                selector="div.sidebar",
                user_id="user3"
            ),
            AuditEvent(
                id=5,
                action_type="custom_selector_created",
                timestamp=base_time,
                selector_id="sel-004",
                selector="article.post",
                user_id="user1",
                after_state="article.post"
            ),
        ]
    
    def test_get_chronological_audit_trail_all_events(self, audit_trail_service, mock_repository, sample_audit_events):
        """Test getting complete chronological audit trail."""
        # Arrange
        mock_repository.get_all_events.return_value = sample_audit_events
        
        # Act
        result = audit_trail_service.get_chronological_audit_trail()
        
        # Assert
        assert len(result) == 5
        # Should be in chronological order (oldest first)
        assert result[0].id == 1
        assert result[1].id == 2
        assert result[2].id == 3
        assert result[3].id == 4
        assert result[4].id == 5
        
        mock_repository.get_all_events.assert_called_once()
    
    def test_get_chronological_audit_trail_with_date_filter(self, audit_trail_service, mock_repository, sample_audit_events):
        """Test getting chronological audit trail with date range filter."""
        # Arrange
        base_time = datetime.now(timezone.utc)
        start_date = base_time - timedelta(hours=2, minutes=30)
        end_date = base_time - timedelta(minutes=30)
        
        # Should return events 2, 3, 4 (within date range)
        filtered_events = [event for event in sample_audit_events 
                         if start_date <= event.timestamp <= end_date]
        mock_repository.get_events_by_multiple_filters.return_value = filtered_events
        
        # Act
        result = audit_trail_service.get_chronological_audit_trail(
            start_date=start_date,
            end_date=end_date
        )
        
        # Assert
        assert len(result) == 3
        assert all(start_date <= event.timestamp <= end_date for event in result)
        mock_repository.get_events_by_multiple_filters.assert_called_once_with(
            user_ids=None, action_types=None, selector_ids=None,
            start_date=start_date, end_date=end_date, limit=1000
        )
    
    def test_detect_connected_decisions_approval_after_rejection(self, audit_trail_service, mock_repository, sample_audit_events):
        """Test detecting connected decisions (approval after rejection for same selector)."""
        # Arrange
        mock_repository.get_events_by_selector_id.return_value = [
            event for event in sample_audit_events if event.selector_id == "sel-001"
        ]
        
        # Act
        result = audit_trail_service.detect_connected_decisions("sel-001")
        
        # Assert
        assert len(result) == 1
        connection = result[0]
        assert connection["type"] == "rejection_after_approval"
        assert connection["rejection_event"].id == 2  # rejection comes first chronologically
        assert connection["approval_event"].id == 1  # approval comes after rejection in our sample data
        assert connection["selector_id"] == "sel-001"
    
    def test_detect_connected_decisions_rejection_after_approval(self, audit_trail_service, mock_repository, sample_audit_events):
        """Test detecting connected decisions (rejection after approval for same selector)."""
        # Arrange
        # Create events where rejection happens after approval
        base_time = datetime.now(timezone.utc)
        events = [
            AuditEvent(
                id=1,
                action_type="selector_approved",
                timestamp=base_time - timedelta(hours=1),
                selector_id="sel-001",
                selector="div.content",
                user_id="user1",
                after_state="div.content"
            ),
            AuditEvent(
                id=2,
                action_type="selector_rejected",
                timestamp=base_time,
                selector_id="sel-001",
                selector="div.content",
                user_id="user2",
                before_state="div.content",
                reason="Found better alternative"
            ),
        ]
        mock_repository.get_events_by_selector_id.return_value = events
        
        # Act
        result = audit_trail_service.detect_connected_decisions("sel-001")
        
        # Assert
        assert len(result) == 1
        connection = result[0]
        assert connection["type"] == "rejection_after_approval"
        assert connection["approval_event"].id == 1
        assert connection["rejection_event"].id == 2
    
    def test_detect_connected_decisions_no_connections(self, audit_trail_service, mock_repository):
        """Test detecting connected decisions when none exist."""
        # Arrange
        base_time = datetime.now(timezone.utc)
        events = [
            AuditEvent(
                id=1,
                action_type="selector_approved",
                timestamp=base_time - timedelta(hours=2),
                selector_id="sel-001",
                selector="div.content",
                user_id="user1",
                after_state="div.content"
            ),
            AuditEvent(
                id=2,
                action_type="selector_approved",
                timestamp=base_time - timedelta(hours=1),
                selector_id="sel-002",
                selector="div.main",
                user_id="user1",
                after_state="div.main"
            ),
        ]
        mock_repository.get_events_by_selector_id.return_value = events
        
        # Act
        result = audit_trail_service.detect_connected_decisions("sel-001")
        
        # Assert
        assert len(result) == 0
    
    def test_get_user_decision_history(self, audit_trail_service, mock_repository, sample_audit_events):
        """Test getting decision history for a specific user."""
        # Arrange
        user_events = [event for event in sample_audit_events if event.user_id == "user1"]
        # Sort in reverse chronological order (most recent first) as repository does
        user_events_sorted = sorted(user_events, key=lambda x: x.timestamp, reverse=True)
        mock_repository.get_by_user_id.return_value = user_events_sorted
        
        # Act
        result = audit_trail_service.get_user_decision_history("user1")
        
        # Assert
        assert len(result) == 3  # user1 has events with ids 1, 3, 5
        assert all(event.user_id == "user1" for event in result)
        # Should be in reverse chronological order (most recent first)
        assert result[0].id == 5  # Most recent
        assert result[1].id == 3
        assert result[2].id == 1  # Oldest
        
        mock_repository.get_by_user_id.assert_called_once_with("user1", limit=100)
    
    def test_get_user_decision_history_with_limit(self, audit_trail_service, mock_repository, sample_audit_events):
        """Test getting user decision history with custom limit."""
        # Arrange
        user_events = [event for event in sample_audit_events if event.user_id == "user1"]
        # Sort in reverse chronological order and take first 2
        user_events_sorted = sorted(user_events, key=lambda x: x.timestamp, reverse=True)
        user_events_limited = user_events_sorted[:2]
        mock_repository.get_by_user_id.return_value = user_events_limited
        
        # Act
        result = audit_trail_service.get_user_decision_history("user1", limit=2)
        
        # Assert
        assert len(result) == 2
        mock_repository.get_by_user_id.assert_called_once_with("user1", limit=2)
    
    def test_get_user_decision_history_with_filters(self, audit_trail_service, mock_repository, sample_audit_events):
        """Test getting user decision history with action type filter."""
        # Arrange
        user_approval_events = [
            event for event in sample_audit_events 
            if event.user_id == "user1" and event.action_type == "selector_approved"
        ]
        # Sort in reverse chronological order as repository does
        user_approval_events_sorted = sorted(user_approval_events, key=lambda x: x.timestamp, reverse=True)
        mock_repository.get_by_user_id_and_action_type.return_value = user_approval_events_sorted
        
        # Act
        result = audit_trail_service.get_user_decision_history(
            "user1", 
            action_type="selector_approved"
        )
        
        # Assert
        assert len(result) == 2  # user1 has 2 approvals
        assert all(event.action_type == "selector_approved" for event in result)
        mock_repository.get_by_user_id_and_action_type.assert_called_once_with(
            "user1", "selector_approved", limit=100
        )
    
    def test_get_audit_trail_with_user_filtering(self, audit_trail_service, mock_repository, sample_audit_events):
        """Test getting audit trail filtered by specific users."""
        # Arrange
        user_ids = ["user1", "user2"]
        filtered_events = [
            event for event in sample_audit_events 
            if event.user_id in user_ids
        ]
        mock_repository.get_events_by_multiple_filters.return_value = filtered_events
        
        # Act
        result = audit_trail_service.get_chronological_audit_trail(user_ids=user_ids)
        
        # Assert
        assert len(result) == 4  # user1 (3 events) + user2 (1 event)
        assert all(event.user_id in user_ids for event in result)
        mock_repository.get_events_by_multiple_filters.assert_called_once_with(
            user_ids=user_ids, action_types=None, selector_ids=None,
            start_date=None, end_date=None, limit=1000
        )
    
    def test_get_audit_trail_with_action_type_filtering(self, audit_trail_service, mock_repository, sample_audit_events):
        """Test getting audit trail filtered by action types."""
        # Arrange
        action_types = ["selector_approved", "selector_rejected"]
        filtered_events = [
            event for event in sample_audit_events 
            if event.action_type in action_types
        ]
        mock_repository.get_events_by_multiple_filters.return_value = filtered_events
        
        # Act
        result = audit_trail_service.get_chronological_audit_trail(action_types=action_types)
        
        # Assert
        assert len(result) == 3  # 2 approvals + 1 rejection
        assert all(event.action_type in action_types for event in result)
        mock_repository.get_events_by_multiple_filters.assert_called_once_with(
            user_ids=None, action_types=action_types, selector_ids=None,
            start_date=None, end_date=None, limit=1000
        )
    
    def test_get_audit_trail_with_selector_filtering(self, audit_trail_service, mock_repository, sample_audit_events):
        """Test getting audit trail filtered by selector IDs."""
        # Arrange
        selector_ids = ["sel-001", "sel-002"]
        filtered_events = [
            event for event in sample_audit_events 
            if event.selector_id in selector_ids
        ]
        mock_repository.get_events_by_multiple_filters.return_value = filtered_events
        
        # Act
        result = audit_trail_service.get_chronological_audit_trail(selector_ids=selector_ids)
        
        # Assert
        assert len(result) == 3  # sel-001 (2 events) + sel-002 (1 event)
        assert all(event.selector_id in selector_ids for event in result)
        mock_repository.get_events_by_multiple_filters.assert_called_once_with(
            user_ids=None, action_types=None, selector_ids=selector_ids,
            start_date=None, end_date=None, limit=1000
        )
    
    def test_get_audit_trail_combined_filters(self, audit_trail_service, mock_repository, sample_audit_events):
        """Test getting audit trail with multiple filters combined."""
        # Arrange
        user_ids = ["user1"]
        action_types = ["selector_approved"]
        filtered_events = [
            event for event in sample_audit_events 
            if event.user_id in user_ids and event.action_type in action_types
        ]
        mock_repository.get_events_by_multiple_filters.return_value = filtered_events
        
        # Act
        result = audit_trail_service.get_chronological_audit_trail(
            user_ids=user_ids,
            action_types=action_types
        )
        
        # Assert
        assert len(result) == 2  # user1 has 2 approvals
        assert all(event.user_id in user_ids and event.action_type in action_types for event in result)
        mock_repository.get_events_by_multiple_filters.assert_called_once_with(
            user_ids=user_ids, action_types=action_types, selector_ids=None
        )
