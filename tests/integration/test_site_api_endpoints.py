"""
Integration tests for site-based feature flag API endpoints.

Tests Story 8.2 (Site-Based Feature Flags) requirements:
- PATCH /feature-flags/sites/{site} endpoint (already exists)
- GET /feature-flags/sites endpoint to list site flags (newly added)
- Proper API responses and error handling
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from fastapi import status

from src.selectors.adaptive.api.routes.feature_flags import router
from src.selectors.adaptive.services.feature_flag_service import FeatureFlagService
from src.main import app


@pytest.mark.integration
class TestSiteBasedAPIEndpoints:
    """Test site-based feature flag API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def temp_service(self):
        """Create temporary feature flag service for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            service = FeatureFlagService(db_path)
            yield service
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    def test_get_sites_endpoint_returns_only_site_flags(self, client, temp_service):
        """Test that GET /feature-flags/sites returns only site-specific flags."""
        # Mock the service dependency
        app.dependency_overrides[FeatureFlagService] = lambda: temp_service
        
        # Create test data
        temp_service.create_feature_flag("basketball", None, True)   # Global flag
        temp_service.create_feature_flag("basketball", "flashscore", False)  # Site flag
        temp_service.create_feature_flag("tennis", "flashscore", True)   # Site flag
        temp_service.create_feature_flag("football", None, False)  # Global flag
        
        # Test the new endpoint
        response = client.get("/feature-flags/sites")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only return site-specific flags
        assert data["total"] == 2
        assert len(data["flags"]) == 2
        
        # Verify correct flags returned
        site_names = [flag["site"] for flag in data["flags"]]
        assert "flashscore" in site_names
        assert all(flag["site"] is not None for flag in data["flags"])
        
        # Verify global flags are not included
        sports = [flag["sport"] for flag in data["flags"]]
        assert "basketball" in sports
        assert "tennis" in sports
        assert "football" not in sports  # This was global only
    
    def test_get_sites_endpoint_empty_result(self, client, temp_service):
        """Test GET /feature-flags/sites when no site flags exist."""
        # Mock the service dependency
        app.dependency_overrides[FeatureFlagService] = lambda: temp_service
        
        # Create only global flags
        temp_service.create_feature_flag("basketball", None, True)
        temp_service.create_feature_flag("tennis", None, False)
        
        # Test the endpoint
        response = client.get("/feature-flags/sites")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["flags"]) == 0
    
    def test_patch_site_endpoint_still_works(self, client, temp_service):
        """Test that PATCH /feature-flags/{sport}/sites/{site} still works."""
        # Mock the service dependency
        app.dependency_overrides[FeatureFlagService] = lambda: temp_service
        
        # Create initial flag
        temp_service.create_feature_flag("basketball", "flashscore", False)
        
        # Test updating the flag
        response = client.patch(
            "/feature-flags/basketball/sites/flashscore",
            json={"enabled": True}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["sport"] == "basketball"
        assert data["site"] == "flashscore"
        assert data["enabled"] is True
        
        # Verify in service
        flag = temp_service.get_feature_flag("basketball", "flashscore")
        assert flag is not None
        assert flag.enabled is True
    
    def test_patch_site_endpoint_not_found(self, client, temp_service):
        """Test PATCH /feature-flags/{sport}/sites/{site} when flag doesn't exist."""
        # Mock the service dependency
        app.dependency_overrides[FeatureFlagService] = lambda: temp_service
        
        # Try to update non-existent flag
        response = client.patch(
            "/feature-flags/basketball/sites/nonexistent",
            json={"enabled": True}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_delete_site_endpoint_still_works(self, client, temp_service):
        """Test that DELETE /feature-flags/{sport}/sites/{site} still works."""
        # Mock the service dependency
        app.dependency_overrides[FeatureFlagService] = lambda: temp_service
        
        # Create initial flag
        temp_service.create_feature_flag("basketball", "flashscore", False)
        
        # Test deleting the flag
        response = client.delete("/feature-flags/basketball/sites/flashscore")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deletion
        flag = temp_service.get_feature_flag("basketball", "flashscore")
        assert flag is None
    
    def test_api_response_format_consistency(self, client, temp_service):
        """Test that API responses follow consistent format."""
        # Mock the service dependency
        app.dependency_overrides[FeatureFlagService] = lambda: temp_service
        
        # Create test data
        temp_service.create_feature_flag("basketball", "flashscore", True)
        
        # Test sites endpoint
        sites_response = client.get("/feature-flags/sites")
        sites_data = sites_response.json()
        
        # Verify response structure
        assert "flags" in sites_data
        assert "total" in sites_data
        assert isinstance(sites_data["flags"], list)
        assert isinstance(sites_data["total"], int)
        
        # Verify flag structure
        flag = sites_data["flags"][0]
        required_fields = ["id", "sport", "site", "enabled", "created_at", "updated_at"]
        for field in required_fields:
            assert field in flag
        
        # Test individual site flag endpoint
        flag_response = client.get("/feature-flags/basketball/sites/flashscore")
        flag_data = flag_response.json()
        
        # Verify individual flag response structure
        for field in required_fields:
            assert field in flag_data
    
    def test_site_flag_hierarchy_in_api(self, client, temp_service):
        """Test that API respects hierarchy: site overrides global."""
        # Mock the service dependency
        app.dependency_overrides[FeatureFlagService] = lambda: temp_service
        
        # Create conflicting flags
        temp_service.create_feature_flag("basketball", None, True)   # Global enabled
        temp_service.create_feature_flag("basketball", "flashscore", False)  # Site disabled
        
        # Check via API that site flag takes precedence
        response = client.get("/feature-flags/basketball/sites/flashscore")
        data = response.json()
        
        assert data["enabled"] is False  # Site flag overrides global
        
        # Verify in service too
        flag = temp_service.get_feature_flag("basketball", "flashscore")
        assert flag.enabled is False


@pytest.mark.integration
class TestAPIIntegrationWithMigration:
    """Test API endpoints with migration data."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_api_with_migration_data_structure(self, client):
        """Test API with data from migration 002_add_site_flags.sql."""
        # This test verifies that the API works with the actual migration data structure
        # and returns the expected format for site-based flags
        
        # Test the sites endpoint
        response = client.get("/feature-flags/sites")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should have the expected structure even if empty (depends on DB state)
        assert "flags" in data
        assert "total" in data
        assert isinstance(data["flags"], list)
        assert isinstance(data["total"], int)
