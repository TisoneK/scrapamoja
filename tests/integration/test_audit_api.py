"""
Integration tests for Audit Trail API endpoints.

Tests for the audit trail API functionality including filtering,
export, and connected decision detection.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from src.selectors.adaptive.api.app import create_app
from src.selectors.adaptive.db.models.audit_event import AuditEvent


@pytest.mark.integration
class TestAuditAPI:
    """Integration tests for audit trail API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(create_app())
    
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
        ]
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_get_audit_trail_basic(self, mock_get_service, client, sample_audit_events):
        """Test getting audit trail without filters."""
        # Arrange
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = sample_audit_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/trail")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total_count" in data
        assert "filters_applied" in data
        assert data["total_count"] == 3
        assert len(data["events"]) == 3
        
        mock_service.get_chronological_audit_trail.assert_called_once_with(
            start_date=None, end_date=None, user_ids=None, 
            action_types=None, selector_ids=None, limit=1000
        )
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_get_audit_trail_with_filters(self, mock_get_service, client, sample_audit_events):
        """Test getting audit trail with filters."""
        # Arrange
        filtered_events = [event for event in sample_audit_events if event.user_id == "user1"]
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = filtered_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/trail?user_ids=user1&user_ids=user2&action_types=selector_approved")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2  # user1 has 2 approvals
        assert data["filters_applied"]["user_ids"] == ["user1", "user2"]
        assert data["filters_applied"]["action_types"] == ["selector_approved"]
        
        mock_service.get_chronological_audit_trail.assert_called_once_with(
            start_date=None, end_date=None, user_ids=["user1", "user2"],
            action_types=["selector_approved"], selector_ids=None, limit=1000
        )
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_get_audit_trail_with_date_range(self, mock_get_service, client, sample_audit_events):
        """Test getting audit trail with date range."""
        # Arrange
        base_time = datetime.now(timezone.utc)
        start_date = base_time - timedelta(hours=2, minutes=30)
        end_date = base_time - timedelta(minutes=30)
        
        filtered_events = [event for event in sample_audit_events 
                         if start_date <= event.timestamp <= end_date]
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = filtered_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get(f"/audit/trail?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1  # Only event 2 falls in the range
        
        mock_service.get_chronological_audit_trail.assert_called_once()
        call_args = mock_service.get_chronological_audit_trail.call_args
        assert call_args[1]["start_date"] == start_date
        assert call_args[1]["end_date"] == end_date
    
    def test_get_audit_trail_invalid_date_format(self, client):
        """Test getting audit trail with invalid date format."""
        # Act
        response = client.get("/audit/trail?start_date=invalid-date")
        
        # Assert
        assert response.status_code == 400
        assert "Invalid start_date format" in response.json()["detail"]
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_get_selector_audit_trail(self, mock_get_service, client, sample_audit_events):
        """Test getting audit trail for specific selector."""
        # Arrange
        selector_events = [event for event in sample_audit_events if event.selector_id == "sel-001"]
        trail_data = {
            "selector_id": "sel-001",
            "events": selector_events,
            "event_count": 2,
            "user_summary": {"user1": {"event_count": 1, "action_types": ["selector_approved"]},
                             "user2": {"event_count": 1, "action_types": ["selector_rejected"]}},
            "action_type_summary": {"selector_approved": 1, "selector_rejected": 1},
            "connected_decisions": [
                {
                    "type": "rejection_after_approval",
                    "selector_id": "sel-001",
                    "time_difference": timedelta(hours=1),
                    "approval_event": selector_events[0],
                    "rejection_event": selector_events[1],
                }
            ]
        }
        
        mock_service = Mock()
        mock_service.get_selector_audit_trail.return_value = trail_data
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/trail/sel-001")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["selector_id"] == "sel-001"
        assert data["event_count"] == 2
        assert "user_summary" in data
        assert "action_type_summary" in data
        assert "connected_decisions" in data
        assert len(data["connected_decisions"]) == 1
        assert data["connected_decisions"][0]["type"] == "rejection_after_approval"
        
        mock_service.get_selector_audit_trail.assert_called_once_with(
            selector_id="sel-001", include_connected_decisions=True, limit=100
        )
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_get_user_decision_history(self, mock_get_service, client, sample_audit_events):
        """Test getting decision history for specific user."""
        # Arrange
        user_events = [event for event in sample_audit_events if event.user_id == "user1"]
        mock_service = Mock()
        mock_service.get_user_decision_history.return_value = user_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/trail/user/user1")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user1"
        assert data["event_count"] == 2
        assert len(data["events"]) == 2
        assert data["filters_applied"]["action_type"] is None
        
        mock_service.get_user_decision_history.assert_called_once_with(
            user_id="user1", action_type=None, start_date=None, end_date=None, limit=100
        )
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_get_user_decision_history_with_action_filter(self, mock_get_service, client, sample_audit_events):
        """Test getting user decision history with action type filter."""
        # Arrange
        user_approval_events = [
            event for event in sample_audit_events 
            if event.user_id == "user1" and event.action_type == "selector_approved"
        ]
        mock_service = Mock()
        mock_service.get_user_decision_history.return_value = user_approval_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/trail/user/user1?action_type=selector_approved")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["event_count"] == 2
        assert data["filters_applied"]["action_type"] == "selector_approved"
        
        mock_service.get_user_decision_history.assert_called_once_with(
            user_id="user1", action_type="selector_approved", start_date=None, end_date=None, limit=100
        )
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_get_audit_trail_summary(self, mock_get_service, client):
        """Test getting audit trail summary."""
        # Arrange
        summary_data = {
            "total_events": 150,
            "unique_users": 5,
            "action_counts": {
                "selector_approved": 80,
                "selector_rejected": 50,
                "selector_flagged": 20
            },
            "user_activity": {
                "user1": {"total_events": 30, "approvals": 20, "rejections": 10},
                "user2": {"total_events": 25, "approvals": 15, "rejections": 10}
            },
            "date_range": {"start": None, "end": None},
            "average_approval_confidence": 0.87
        }
        
        mock_service = Mock()
        mock_service.get_audit_trail_summary.return_value = summary_data
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/summary")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 150
        assert data["unique_users"] == 5
        assert data["average_approval_confidence"] == 0.87
        assert "action_counts" in data
        assert "user_activity" in data
        
        mock_service.get_audit_trail_summary.assert_called_once_with(start_date=None, end_date=None)
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_export_audit_trail_json(self, mock_get_service, client, sample_audit_events):
        """Test exporting audit trail as JSON."""
        # Arrange
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = sample_audit_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/export/json")
        
        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]
        assert ".json" in response.headers["content-disposition"]
        
        data = response.json()
        assert "export_metadata" in data
        assert "audit_events" in data
        assert len(data["audit_events"]) == 3
        assert data["export_metadata"]["total_events"] == 3
        
        mock_service.get_chronological_audit_trail.assert_called_once_with(
            start_date=None, end_date=None, user_ids=None,
            action_types=None, selector_ids=None, limit=10000
        )
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_export_audit_trail_csv(self, mock_get_service, client, sample_audit_events):
        """Test exporting audit trail as CSV."""
        # Arrange
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = sample_audit_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/export/csv")
        
        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv"
        assert "attachment" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]
        
        # Check CSV content
        csv_content = response.content.decode('utf-8')
        lines = csv_content.split('\n')
        assert len(lines) >= 4  # Header + 3 data lines + empty line
        
        # Check header
        header = lines[0]
        expected_columns = ["id", "timestamp", "action_type", "selector_id", "selector"]
        for col in expected_columns:
            assert col in header
        
        mock_service.get_chronological_audit_trail.assert_called_once_with(
            start_date=None, end_date=None, user_ids=None,
            action_types=None, selector_ids=None, limit=10000
        )
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_export_with_filters(self, mock_get_service, client, sample_audit_events):
        """Test exporting audit trail with filters."""
        # Arrange
        filtered_events = [event for event in sample_audit_events if event.user_id == "user1"]
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = filtered_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/export/json?user_ids=user1&action_types=selector_approved")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["export_metadata"]["filters_applied"]["user_ids"] == ["user1"]
        assert data["export_metadata"]["filters_applied"]["action_types"] == ["selector_approved"]
        assert data["export_metadata"]["total_events"] == 2
        
        mock_service.get_chronological_audit_trail.assert_called_once_with(
            start_date=None, end_date=None, user_ids=["user1"],
            action_types=["selector_approved"], selector_ids=None, limit=10000
        )
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_export_with_limit(self, mock_get_service, client, sample_audit_events):
        """Test exporting audit trail with custom limit."""
        # Arrange
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = sample_audit_events[:1]
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/export/json?limit=1")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["export_metadata"]["total_events"] == 1
        
        mock_service.get_chronological_audit_trail.assert_called_once_with(
            start_date=None, end_date=None, user_ids=None,
            action_types=None, selector_ids=None, limit=1
        )
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_audit_api_error_handling(self, mock_get_service, client):
        """Test API error handling."""
        # Arrange
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.side_effect = Exception("Database error")
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/trail")
        
        # Assert
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]
