"""
Integration tests for Audit Query API endpoints.

This implements Epic 6 (Audit Logging) requirements for Story 6.3.
Tests the actual HTTP endpoints to ensure they work correctly.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from src.selectors.adaptive.api.app import create_app
from src.selectors.adaptive.services.audit_query_service import get_audit_query_service
from src.selectors.adaptive.db.repositories.audit_event_repository import AuditEventRepository


class TestAuditQueryAPIIntegration:
    """Integration tests for audit query API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample audit data for testing."""
        # Get the audit query service and repository
        audit_service = get_audit_query_service()
        repository = audit_service.repository
        
        # Create sample events
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        events = []
        for i in range(10):
            event = repository.create_audit_event(
                action_type=["selector_approved", "selector_rejected", "selector_flagged"][i % 3],
                selector=f"div.test-{i % 3}",
                user_id=f"user-{i % 2}",
                selector_id=f"selector-{i % 3}",
                confidence_at_time=0.8 + (i * 0.02),
                reason=f"Test reason {i}",
            )
            events.append(event)
        
        yield events
        
        # Cleanup - delete test data
        session = repository.get_session()
        try:
            for event in events:
                session.delete(event)
            session.commit()
        finally:
            session.close()
    
    def test_query_audit_log_basic(self, client, sample_data):
        """Test basic audit log query endpoint."""
        response = client.get("/audit/log")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "events" in data
        assert "total_count" in data
        assert "has_more" in data
        assert "filters_applied" in data
        assert isinstance(data["events"], list)
        assert data["total_count"] >= 0
    
    def test_query_audit_log_with_filters(self, client, sample_data):
        """Test audit log query with filters."""
        # Test with selector_id filter
        response = client.get("/audit/log?selector_id=selector-0")
        assert response.status_code == 200
        data = response.json()
        assert data["filters_applied"]["selector_id"] == "selector-0"
        
        # Test with user_id filter
        response = client.get("/audit/log?user_id=user-0")
        assert response.status_code == 200
        data = response.json()
        assert data["filters_applied"]["user_id"] == "user-0"
        
        # Test with action_types filter
        response = client.get("/audit/log?action_types=selector_approved")
        assert response.status_code == 200
        data = response.json()
        assert "selector_approved" in data["filters_applied"]["action_types"]
    
    def test_query_audit_log_with_date_range(self, client, sample_data):
        """Test audit log query with date range."""
        start_date = "2024-01-01T00:00:00Z"
        end_date = "2024-01-02T00:00:00Z"
        
        response = client.get(f"/audit/log?start_date={start_date}&end_date={end_date}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["filters_applied"]["start_date"] == start_date
        assert data["filters_applied"]["end_date"] == end_date
    
    def test_query_audit_log_invalid_date_range(self, client):
        """Test audit log query with invalid date range."""
        start_date = "2024-01-02T00:00:00Z"
        end_date = "2024-01-01T00:00:00Z"  # End before start
        
        response = client.get(f"/audit/log?start_date={start_date}&end_date={end_date}")
        assert response.status_code == 400
        assert "start_date must be before end_date" in response.json()["detail"]
    
    def test_query_audit_log_with_pagination(self, client, sample_data):
        """Test audit log query with pagination."""
        response = client.get("/audit/log?limit=5&offset=2")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["events"]) <= 5
        assert data["filters_applied"]["limit"] == 5
        assert data["filters_applied"]["offset"] == 2
    
    def test_query_audit_log_with_sorting(self, client, sample_data):
        """Test audit log query with sorting."""
        # Test sorting by timestamp
        response = client.get("/audit/log?sort_by=timestamp&sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        assert data["filters_applied"]["sort_by"] == "timestamp"
        assert data["filters_applied"]["sort_order"] == "asc"
        
        # Test sorting by user_id
        response = client.get("/audit/log?sort_by=user_id&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        assert data["filters_applied"]["sort_by"] == "user_id"
        assert data["filters_applied"]["sort_order"] == "desc"
    
    def test_query_by_selector_endpoint(self, client, sample_data):
        """Test selector-specific audit query endpoint."""
        selector_id = "selector-0"
        response = client.get(f"/audit/log/selector/{selector_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "selector_id" in data
        assert data["selector_id"] == selector_id
        assert "events" in data
        assert "total_count" in data
        assert "has_more" in data
        assert "filters_applied" in data
    
    def test_query_by_user_endpoint(self, client, sample_data):
        """Test user-specific audit query endpoint."""
        user_id = "user-0"
        response = client.get(f"/audit/log/user/{user_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "user_id" in data
        assert data["user_id"] == user_id
        assert "events" in data
        assert "total_count" in data
        assert "has_more" in data
        assert "filters_applied" in data
    
    def test_query_by_date_range_endpoint(self, client, sample_data):
        """Test date range audit query endpoint."""
        start = "2024-01-01T00:00:00Z"
        end = "2024-01-02T00:00:00Z"
        
        response = client.get(f"/audit/log/date-range?start={start}&end={end}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "start_date" in data
        assert "end_date" in data
        assert data["start_date"] == start
        assert data["end_date"] == end
        assert "events" in data
        assert "total_count" in data
        assert "has_more" in data
        assert "filters_applied" in data
    
    def test_query_by_date_range_endpoint_missing_dates(self, client):
        """Test date range endpoint with missing required parameters."""
        response = client.get("/audit/log/date-range?start=2024-01-01T00:00:00Z")
        assert response.status_code == 422  # Validation error
        
        response = client.get("/audit/log/date-range?end=2024-01-02T00:00:00Z")
        assert response.status_code == 422  # Validation error
    
    def test_query_by_date_range_endpoint_invalid_dates(self, client):
        """Test date range endpoint with invalid date format."""
        response = client.get("/audit/log/date-range?start=invalid-date&end=2024-01-02T00:00:00Z")
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]
    
    def test_cursor_based_pagination(self, client, sample_data):
        """Test cursor-based pagination."""
        # First request to get a cursor
        response = client.get("/audit/log?limit=3")
        assert response.status_code == 200
        data = response.json()
        
        if data["has_more"] and data["next_cursor"]:
            # Use cursor for next page
            cursor = data["next_cursor"]
            response = client.get(f"/audit/log?limit=3&cursor={cursor}")
            assert response.status_code == 200
            data = response.json()
            assert "events" in data
            assert "has_more" in data
    
    def test_limit_validation(self, client, sample_data):
        """Test limit parameter validation."""
        # Test limit too high
        response = client.get("/audit/log?limit=1001")
        assert response.status_code == 422  # Validation error
        
        # Test limit too low
        response = client.get("/audit/log?limit=0")
        assert response.status_code == 422  # Validation error
        
        # Test negative limit
        response = client.get("/audit/log?limit=-1")
        assert response.status_code == 422  # Validation error
    
    def test_offset_validation(self, client, sample_data):
        """Test offset parameter validation."""
        # Test negative offset
        response = client.get("/audit/log?offset=-1")
        assert response.status_code == 422  # Validation error
        
        # Test valid offset
        response = client.get("/audit/log?offset=5")
        assert response.status_code == 200
    
    def test_openapi_docs_available(self, client):
        """Test that OpenAPI docs are available."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "html" in response.headers["content-type"]
        
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "html" in response.headers["content-type"]
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
    
    def test_root_endpoint_shows_audit_endpoints(self, client):
        """Test that root endpoint shows audit query endpoints."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        endpoints = data["endpoints"]
        assert "audit_query" in endpoints
        assert "selector_audit_query" in endpoints
        assert "user_audit_query" in endpoints
        assert "date_range_audit_query" in endpoints


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
