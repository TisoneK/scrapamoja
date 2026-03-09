"""
Export format validation tests for audit trail functionality.

Tests for JSON and CSV export formats to ensure compliance
and data integrity.
"""

import pytest
import json
import csv
import io
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from src.selectors.adaptive.api.app import create_app
from src.selectors.adaptive.db.models.audit_event import AuditEvent
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestAuditExportFormats:
    """Integration tests for audit export format validation."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(create_app())
    
    @pytest.fixture
    def comprehensive_audit_events(self):
        """Create comprehensive sample audit events for export testing."""
        base_time = datetime.now(timezone.utc)
        return [
            AuditEvent(
                id=1,
                action_type="selector_approved",
                timestamp=base_time - timedelta(hours=3),
                selector_id="sel-001",
                selector="div.content",
                user_id="user1",
                failure_id=101,
                context_snapshot={"page": "https://example.com", "dom_depth": 5},
                after_state="div.content",
                confidence_at_time=0.85,
                notes="Good selector"
            ),
            AuditEvent(
                id=2,
                action_type="selector_rejected",
                timestamp=base_time - timedelta(hours=2),
                selector_id="sel-001",
                selector="span.content",
                user_id="user2",
                failure_id=101,
                context_snapshot={"page": "https://example.com", "dom_depth": 5},
                before_state="span.content",
                confidence_at_time=0.45,
                reason="Too specific",
                suggested_alternative="div.content",
                notes="User suggested alternative"
            ),
            AuditEvent(
                id=3,
                action_type="selector_flagged",
                timestamp=base_time - timedelta(hours=1),
                selector_id="sel-002",
                selector="div.sidebar",
                user_id="user3",
                failure_id=102,
                context_snapshot={"page": "https://example.com/about", "dom_depth": 4},
                confidence_at_time=0.60,
                notes="Flagged for review"
            ),
            AuditEvent(
                id=4,
                action_type="custom_selector_created",
                timestamp=base_time,
                selector_id="sel-003",
                selector="article.post",
                user_id="user1",
                failure_id=103,
                context_snapshot={"page": "https://example.com/blog", "dom_depth": 6},
                after_state="article.post",
                confidence_at_time=0.95,
                notes="Custom selector for blog posts"
            ),
        ]
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_json_export_format_validation(self, mock_get_service, client, comprehensive_audit_events):
        """Test JSON export format compliance and data integrity."""
        # Arrange
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = comprehensive_audit_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/export/json")
        
        # Assert - Response format
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]
        assert ".json" in response.headers["content-disposition"]
        
        # Parse JSON content
        json_data = response.json()
        
        # Validate structure
        assert "export_metadata" in json_data
        assert "audit_events" in json_data
        
        # Validate export metadata
        metadata = json_data["export_metadata"]
        required_metadata_fields = ["exported_at", "filters_applied", "total_events"]
        for field in required_metadata_fields:
            assert field in metadata
        
        assert isinstance(metadata["exported_at"], str)
        assert isinstance(metadata["total_events"], int)
        assert isinstance(metadata["filters_applied"], dict)
        
        # Validate audit events
        events = json_data["audit_events"]
        assert isinstance(events, list)
        assert len(events) == 4
        
        # Validate event structure
        for event in events:
            required_event_fields = [
                "id", "action_type", "timestamp", "selector_id", 
                "selector", "user_id", "created_at"
            ]
            for field in required_event_fields:
                assert field in event, f"Missing field {field} in event"
            
            # Validate data types
            assert isinstance(event["id"], int)
            assert isinstance(event["action_type"], str)
            assert isinstance(event["selector"], str)
            assert isinstance(event["user_id"], str)
            
            # Validate optional fields can be None
            optional_fields = [
                "failure_id", "context_snapshot", "before_state", 
                "after_state", "confidence_at_time", "reason", 
                "suggested_alternative", "notes"
            ]
            for field in optional_fields:
                assert field in event, f"Missing optional field {field} in event"
        
        # Validate specific event data integrity
        approval_event = events[0]
        assert approval_event["action_type"] == "selector_approved"
        assert approval_event["user_id"] == "user1"
        assert approval_event["confidence_at_time"] == 0.85
        assert approval_event["notes"] == "Good selector"
        
        rejection_event = events[1]
        assert rejection_event["action_type"] == "selector_rejected"
        assert rejection_event["user_id"] == "user2"
        assert rejection_event["reason"] == "Too specific"
        assert rejection_event["suggested_alternative"] == "div.content"
        
        # Validate context snapshot serialization
        assert isinstance(approval_event["context_snapshot"], dict)
        assert approval_event["context_snapshot"]["page"] == "https://example.com"
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_csv_export_format_validation(self, mock_get_service, client, comprehensive_audit_events):
        """Test CSV export format compliance and data integrity."""
        # Arrange
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = comprehensive_audit_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/export/csv")
        
        # Assert - Response format
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv"
        assert "attachment" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]
        
        # Parse CSV content
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        lines = list(csv_reader)
        
        # Validate structure
        assert len(lines) >= 5  # Header + 4 data lines
        
        # Validate header
        header = lines[0]
        expected_columns = [
            "id", "timestamp", "action_type", "selector_id", "selector",
            "user_id", "failure_id", "before_state", "after_state",
            "confidence_at_time", "reason", "suggested_alternative", "notes"
        ]
        assert len(header) == len(expected_columns)
        for col in expected_columns:
            assert col in header
        
        # Validate data rows
        for i, event in enumerate(comprehensive_audit_events):
            row = lines[i + 1]  # Skip header
            assert len(row) == len(expected_columns)
            
            # Validate required fields
            assert row[0] == str(event.id)  # id
            assert row[2] == event.action_type  # action_type
            assert row[4] == event.selector  # selector
            assert row[5] == event.user_id  # user_id
            
            # Validate timestamp format
            if event.timestamp:
                assert row[1] == event.timestamp.isoformat()
            
            # Validate optional fields
            assert row[6] == str(event.failure_id) if event.failure_id else ""  # failure_id
            assert row[7] == event.before_state or ""  # before_state
            assert row[8] == event.after_state or ""  # after_state
            assert row[9] == str(event.confidence_at_time) if event.confidence_at_time else ""  # confidence_at_time
            assert row[10] == event.reason or ""  # reason
            assert row[11] == event.suggested_alternative or ""  # suggested_alternative
            assert row[12] == event.notes or ""  # notes
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_json_export_with_filters(self, mock_get_service, client, comprehensive_audit_events):
        """Test JSON export with applied filters."""
        # Arrange
        filtered_events = [event for event in comprehensive_audit_events if event.user_id == "user1"]
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = filtered_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/export/json?user_ids=user1&action_types=selector_approved,custom_selector_created")
        
        # Assert
        assert response.status_code == 200
        json_data = response.json()
        
        # Validate filters are recorded in metadata
        filters = json_data["export_metadata"]["filters_applied"]
        assert filters["user_ids"] == ["user1"]
        assert filters["action_types"] == ["selector_approved", "custom_selector_created"]
        
        # Validate filtered events
        events = json_data["audit_events"]
        assert len(events) == 2  # user1 has 2 events matching the filters
        assert all(event["user_id"] == "user1" for event in events)
        assert all(event["action_type"] in ["selector_approved", "custom_selector_created"] for event in events)
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_csv_export_with_date_range(self, mock_get_service, client, comprehensive_audit_events):
        """Test CSV export with date range filtering."""
        # Arrange
        base_time = datetime.now(timezone.utc)
        start_date = base_time - timedelta(hours=2, minutes=30)
        end_date = base_time - timedelta(minutes=30)
        
        # Only event 2 (rejection) falls in this range
        filtered_events = [event for event in comprehensive_audit_events 
                         if start_date <= event.timestamp <= end_date]
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = filtered_events
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get(f"/audit/export/csv?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}")
        
        # Assert
        assert response.status_code == 200
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        lines = list(csv_reader)
        
        # Should have header + 1 data line
        assert len(lines) == 2
        
        # Validate the filtered event
        row = lines[1]
        assert row[5] == "user2"  # user_id
        assert row[2] == "selector_rejected"  # action_type
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_export_large_dataset_performance(self, mock_get_service, client):
        """Test export performance with large dataset."""
        # Arrange
        large_dataset = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(1000):
            event = AuditEvent(
                id=i + 1,
                action_type="selector_approved" if i % 2 == 0 else "selector_rejected",
                timestamp=base_time - timedelta(minutes=i),
                selector_id=f"sel-{i // 10:03d}",
                selector=f"div.element-{i}",
                user_id=f"user-{(i % 10) + 1}",
                after_state=f"div.element-{i}" if i % 2 == 0 else None,
                before_state=f"div.element-{i}" if i % 2 == 1 else None,
                confidence_at_time=0.5 + (i % 50) / 100,
            )
            large_dataset.append(event)
        
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = large_dataset
        mock_get_service.return_value = mock_service
        
        # Act
        response = client.get("/audit/export/json")
        
        # Assert
        assert response.status_code == 200
        json_data = response.json()
        
        # Validate all events are exported
        assert json_data["export_metadata"]["total_events"] == 1000
        assert len(json_data["audit_events"]) == 1000
        
        # Validate data integrity for sample events
        first_event = json_data["audit_events"][0]
        assert first_event["id"] == 1
        assert first_event["user_id"] == "user-1"
        
        last_event = json_data["audit_events"][-1]
        assert last_event["id"] == 1000
        assert last_event["user_id"] == "user-10"
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_export_empty_dataset(self, mock_get_service, client):
        """Test export with empty dataset."""
        # Arrange
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = []
        mock_get_service.return_value = mock_service
        
        # Act - JSON export
        json_response = client.get("/audit/export/json")
        assert json_response.status_code == 200
        json_data = json_response.json()
        assert json_data["export_metadata"]["total_events"] == 0
        assert len(json_data["audit_events"]) == 0
        
        # Act - CSV export
        csv_response = client.get("/audit/export/csv")
        assert csv_response.status_code == 200
        csv_content = csv_response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        lines = list(csv_reader)
        
        # Should only have header, no data rows
        assert len(lines) == 1
        assert lines[0][0] == "id"  # First column is id
    
    @patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service')
    def test_export_special_characters_handling(self, mock_get_service, client):
        """Test export handles special characters correctly."""
        # Arrange
        events_with_special_chars = [
            AuditEvent(
                id=1,
                action_type="selector_approved",
                timestamp=datetime.now(timezone.utc),
                selector_id="sel-001",
                selector="div.content[data-test=\"special&chars\"]",
                user_id="user@domain.com",
                after_state="div.content[data-test=\"special&chars\"]",
                notes="Selector with quotes: \"test\" and ampersand & symbols",
                reason="Contains <xml> like tags & special chars"
            ),
        ]
        
        mock_service = Mock()
        mock_service.get_chronological_audit_trail.return_value = events_with_special_chars
        mock_get_service.return_value = mock_service
        
        # Act - JSON export
        json_response = client.get("/audit/export/json")
        assert json_response.status_code == 200
        json_data = json_response.json()
        
        event = json_data["audit_events"][0]
        assert "&" in event["selector"]
        assert "\"" in event["selector"]
        assert event["user_id"] == "user@domain.com"
        assert "&" in event["notes"]
        assert "<" in event["reason"]
        
        # Act - CSV export
        csv_response = client.get("/audit/export/csv")
        assert csv_response.status_code == 200
        csv_content = csv_response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        lines = list(csv_reader)
        
        # CSV should properly escape special characters
        row = lines[1]  # Data row
        assert "&" in row[4]  # selector column
        assert "@" in row[5]  # user_id column
        assert "&" in row[12]  # notes column
    
    def test_export_filename_format(self, client):
        """Test export filename follows expected format."""
        # Arrange
        with patch('src.selectors.adaptive.services.audit_trail_service.get_audit_trail_service') as mock_get_service:
            mock_service = Mock()
            mock_service.get_chronological_audit_trail.return_value = []
            mock_get_service.return_value = mock_service
            
            # Act - JSON export
            json_response = client.get("/audit/export/json")
            json_disposition = json_response.headers["content-disposition"]
            
            # Act - CSV export
            csv_response = client.get("/audit/export/csv")
            csv_disposition = csv_response.headers["content-disposition"]
            
            # Assert filename format
            assert "audit_trail_" in json_disposition
            assert ".json" in json_disposition
            assert "attachment" in json_disposition
            
            assert "audit_trail_" in csv_disposition
            assert ".csv" in csv_disposition
            assert "attachment" in csv_disposition
            
            # Validate timestamp format (YYYYMMDD_HHMMSS)
            import re
            timestamp_pattern = r'\d{8}_\d{6}'
            assert re.search(timestamp_pattern, json_disposition)
            assert re.search(timestamp_pattern, csv_disposition)
