"""
Integration tests for Feature Flag API endpoints.

Tests cover:
- All CRUD operations via HTTP API
- Error handling and validation
- Performance requirements
- Authentication and authorization (mocked)
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.selectors.adaptive.api.app import create_app
from src.selectors.adaptive.api.routes.feature_flags import router
from src.selectors.adaptive.db.repositories.feature_flag_repository import FeatureFlagRepository
from src.selectors.adaptive.db.models.feature_flag import FeatureFlag
from src.selectors.adaptive.services.feature_flag_service import FeatureFlagService


@pytest.fixture
def test_app():
    """Create test FastAPI application."""
    app = create_app()
    # Ensure our router is included
    app.include_router(router, prefix="/test-feature-flags")
    return app


@pytest.fixture
def test_client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def mock_feature_service():
    """Mock feature flag service."""
    return Mock(spec=FeatureFlagService)


@pytest.fixture
def sample_feature_flag():
    """Sample feature flag for testing."""
    return FeatureFlag(
        id=1,
        sport="basketball",
        site=None,
        enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestFeatureFlagAPI:
    """Test suite for Feature Flag API endpoints."""
    
    def test_list_feature_flags_empty(self, test_client, mock_feature_service):
        """Test listing feature flags when none exist."""
        # Setup
        mock_feature_service.get_all_feature_flags.return_value = []
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.get("/test-feature-flags")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["count"] == 0
    
    def test_list_feature_flags_with_data(self, test_client, mock_feature_service, sample_feature_flag):
        """Test listing feature flags with data."""
        # Setup
        flags = [sample_feature_flag]
        mock_feature_service.get_all_feature_flags.return_value = flags
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.get("/test-feature-flags")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["data"]) == 1
        assert data["data"][0]["sport"] == "basketball"
        assert data["data"][0]["enabled"] is True
        assert data["data"][0]["site"] is None
    
    def test_list_feature_flags_filtered_by_sport(self, test_client, mock_feature_service, sample_feature_flag):
        """Test listing feature flags filtered by sport."""
        # Setup
        flags = [sample_feature_flag]
        mock_feature_service.get_feature_flags_by_sport.return_value = flags
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.get("/test-feature-flags?sport=basketball")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        mock_feature_service.get_feature_flags_by_sport.assert_called_once_with("basketball")
    
    def test_get_enabled_sports(self, test_client, mock_feature_service):
        """Test getting enabled sports."""
        # Setup
        enabled_sports = ["basketball", "tennis"]
        mock_feature_service.get_enabled_sports.return_value = enabled_sports
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.get("/test-feature-flags/enabled-sports")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["sports"] == enabled_sports
        assert data["count"] == 2
    
    def test_check_feature_flag_enabled(self, test_client, mock_feature_service):
        """Test checking feature flag status when enabled."""
        # Setup
        mock_feature_service.is_adaptive_enabled.return_value = True
        mock_feature_service.get_feature_flag.return_value = FeatureFlag(
            id=1, sport="basketball", enabled=True, site=None,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.get("/test-feature-flags/check?sport=basketball")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["sport"] == "basketball"
        assert data["enabled"] is True
        assert data["flag_exists"] is True
    
    def test_check_feature_flag_disabled(self, test_client, mock_feature_service):
        """Test checking feature flag status when disabled."""
        # Setup
        mock_feature_service.is_adaptive_enabled.return_value = False
        mock_feature_service.get_feature_flag.return_value = None
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.get("/test-feature-flags/check?sport=unknown_sport")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["sport"] == "unknown_sport"
        assert data["enabled"] is False
        assert data["flag_exists"] is False
    
    def test_get_feature_flag_stats(self, test_client, mock_feature_service):
        """Test getting feature flag statistics."""
        # Setup
        flags = [
            FeatureFlag(id=1, sport="basketball", enabled=True, site=None, created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
            FeatureFlag(id=2, sport="tennis", enabled=False, site=None, created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
            FeatureFlag(id=3, sport="basketball", enabled=False, site="flashscore", created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
        ]
        mock_feature_service.get_all_feature_flags.return_value = flags
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.get("/test-feature-flags/stats")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["total_flags"] == 3
        assert data["enabled_flags"] == 1
        assert data["disabled_flags"] == 2
        assert data["global_flags"] == 2  # basketball, tennis
        assert data["site_specific_flags"] == 1  # basketball@flashscore
        assert data["unique_sports"] == 2  # basketball, tennis
    
    def test_create_feature_flag_success(self, test_client, mock_feature_service, sample_feature_flag):
        """Test successful feature flag creation."""
        # Setup
        mock_feature_service.create_feature_flag.return_value = sample_feature_flag
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.post(
                "/test-feature-flags",
                json={"sport": "basketball", "enabled": True}
            )
        
        # Verify
        assert response.status_code == 201
        data = response.json()
        assert data["sport"] == "basketball"
        assert data["enabled"] is True
        mock_feature_service.create_feature_flag.assert_called_once_with("basketball", None, True)
    
    def test_create_feature_flag_conflict(self, test_client, mock_feature_service):
        """Test creating feature flag that already exists."""
        # Setup
        mock_feature_service.create_feature_flag.side_effect = ValueError("Feature flag already exists")
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.post(
                "/test-feature-flags",
                json={"sport": "basketball", "enabled": True}
            )
        
        # Verify
        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"].lower()
    
    def test_create_feature_flag_validation_error(self, test_client):
        """Test creating feature flag with invalid data."""
        # Test missing sport
        response = test_client.post("/test-feature-flags", json={"enabled": True})
        assert response.status_code == 422  # Validation error
        
        # Test invalid sport (empty string)
        response = test_client.post("/test-feature-flags", json={"sport": "", "enabled": True})
        assert response.status_code == 422
    
    def test_toggle_sport_flag_existing(self, test_client, mock_feature_service, sample_feature_flag):
        """Test toggling existing sport flag."""
        # Setup
        mock_feature_service.update_feature_flag.return_value = sample_feature_flag
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.patch(
                "/test-feature-flags/basketball",
                json={"enabled": True}
            )
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["sport"] == "basketball"
        assert data["enabled"] is True
        mock_feature_service.update_feature_flag.assert_called_once_with("basketball", None, True)
    
    def test_toggle_sport_flag_creates_new(self, test_client, mock_feature_service, sample_feature_flag):
        """Test toggling creates new flag when none exists."""
        # Setup
        mock_feature_service.update_feature_flag.return_value = None
        mock_feature_service.create_feature_flag.return_value = sample_feature_flag
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.patch(
                "/test-feature-flags/tennis",
                json={"enabled": True}
            )
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["sport"] == "tennis"
        assert data["enabled"] is True
        mock_feature_service.update_feature_flag.assert_called_once_with("tennis", None, True)
        mock_feature_service.create_feature_flag.assert_called_once_with("tennis", None, True)
    
    def test_update_site_specific_flag(self, test_client, mock_feature_service):
        """Test updating site-specific flag."""
        # Setup
        site_flag = FeatureFlag(
            id=2,
            sport="basketball",
            site="flashscore",
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_feature_service.update_feature_flag.return_value = site_flag
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.patch(
                "/test-feature-flags/basketball/sites/flashscore",
                json={"enabled": False}
            )
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["sport"] == "basketball"
        assert data["site"] == "flashscore"
        assert data["enabled"] is False
        mock_feature_service.update_feature_flag.assert_called_once_with("basketball", "flashscore", False)
    
    def test_update_site_specific_flag_not_found(self, test_client, mock_feature_service):
        """Test updating non-existent site-specific flag."""
        # Setup
        mock_feature_service.update_feature_flag.return_value = None
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.patch(
                "/test-feature-flags/unknown/sites/unknown",
                json={"enabled": True}
            )
        
        # Verify
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_delete_sport_flag(self, test_client, mock_feature_service):
        """Test deleting sport flag."""
        # Setup
        mock_feature_service.delete_feature_flag.return_value = True
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.delete("/test-feature-flags/basketball")
        
        # Verify
        assert response.status_code == 204
        assert response.content == b""  # No content for 204
        mock_feature_service.delete_feature_flag.assert_called_once_with("basketball", None)
    
    def test_delete_sport_flag_not_found(self, test_client, mock_feature_service):
        """Test deleting non-existent sport flag."""
        # Setup
        mock_feature_service.delete_feature_flag.return_value = False
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.delete("/test-feature-flags/unknown")
        
        # Verify
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_bulk_create_feature_flags(self, test_client, mock_feature_service):
        """Test bulk creating feature flags."""
        # Setup
        flags_data = [
            {"sport": "basketball", "enabled": False},
            {"sport": "tennis", "enabled": False},
            {"sport": "football", "enabled": True},
        ]
        created_flags = [
            FeatureFlag(id=1, sport="basketball", enabled=False, site=None, created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
            FeatureFlag(id=2, sport="tennis", enabled=False, site=None, created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
            FeatureFlag(id=3, sport="football", enabled=True, site=None, created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
        ]
        mock_feature_service.bulk_create_flags.return_value = created_flags
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.post(
                "/test-feature-flags/bulk",
                json={"flags": flags_data}
            )
        
        # Verify
        assert response.status_code == 201
        data = response.json()
        assert data["count"] == 3
        assert len(data["data"]) == 3
        mock_feature_service.bulk_create_flags.assert_called_once()
    
    def test_get_sport_feature_flags(self, test_client, mock_feature_service):
        """Test getting all flags for a specific sport."""
        # Setup
        flags = [
            FeatureFlag(id=1, sport="basketball", enabled=True, site=None, created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
            FeatureFlag(id=2, sport="basketball", enabled=False, site="flashscore", created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
        ]
        mock_feature_service.get_feature_flags_by_sport.return_value = flags
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            response = test_client.get("/test-feature-flags/basketball")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["data"]) == 2
        # Global flag should come first
        assert data["data"][0]["site"] is None
        assert data["data"][1]["site"] == "flashscore"
        mock_feature_service.get_feature_flags_by_sport.assert_called_once_with("basketball")


class TestFeatureFlagAPIPerformance:
    """Test performance requirements for Feature Flag API."""
    
    def test_api_response_time_under_500ms(self, test_client, mock_feature_service):
        """Test that API responses are under 500ms for basic operations."""
        # Setup
        mock_feature_service.get_all_feature_flags.return_value = []
        
        with patch('src.selectors.adaptive.api.routes.feature_flags.get_feature_flag_service', return_value=mock_feature_service):
            import time
            start_time = time.time()
            response = test_client.get("/test-feature-flags")
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
        
        # Verify
        assert response.status_code == 200
        assert response_time_ms < 500, f"Response time {response_time_ms}ms exceeds 500ms requirement"
    
    @pytest.mark.asyncio
    async def test_feature_flag_lookup_under_1ms(self, mock_feature_service):
        """Test that feature flag lookup is under 1ms (performance requirement)."""
        # Setup
        service = FeatureFlagService(db_path=":memory:", cache_ttl=60)
        
        # Create a flag first
        flag = service.create_feature_flag("performance_test", None, True)
        
        # Measure lookup time
        import time
        start_time = time.perf_counter()
        result = service.is_adaptive_enabled("performance_test", None)
        end_time = time.perf_counter()
        lookup_time_ms = (end_time - start_time) * 1000
        
        # Verify
        assert result is True
        assert lookup_time_ms < 1.0, f"Lookup time {lookup_time_ms}ms exceeds 1ms requirement"


class TestFeatureFlagAPIDocumentation:
    """Test API documentation and OpenAPI integration."""
    
    def test_api_docs_available(self, test_client):
        """Test that API documentation is available."""
        response = test_client.get("/docs")
        assert response.status_code == 200
        assert "html" in response.content.decode().lower()
    
    def test_openapi_schema_available(self, test_client):
        """Test that OpenAPI schema is available."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "/feature-flags" in schema["paths"]
        assert "/feature-flags/{sport}" in schema["paths"]
        assert "FeatureFlagResponseSchema" in str(schema["components"])
    
    def test_root_endpoint_includes_feature_flags(self, test_client):
        """Test that root endpoint includes feature flag endpoints."""
        response = test_client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        endpoints = data.get("endpoints", {})
        
        assert "feature_flags" in endpoints
        assert "feature_flag_check" in endpoints
        assert "enabled_sports" in endpoints
        assert "toggle_sport_flag" in endpoints
