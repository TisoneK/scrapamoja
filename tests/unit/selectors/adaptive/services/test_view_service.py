"""
Unit tests for ViewService.

This implements Story 7.2 (Technical and Non-Technical Views) requirements.
Tests the view mode transformation and user preference management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from src.selectors.adaptive.services.view_service import ViewService
from src.selectors.adaptive.db.models.user_preferences import UserRole, ViewMode


class TestViewServiceInit:
    """Tests for ViewService initialization."""
    
    def test_default_initialization(self):
        """Test default service initialization."""
        service = ViewService()
        
        assert service is not None
        assert service.user_repo is not None
        assert service.usage_repo is not None
    
    def test_custom_db_path(self):
        """Test initialization with custom database path."""
        service = ViewService(db_path="/tmp/test.db")
        
        assert service is not None


class TestViewModeValidation:
    """Tests for view mode validation."""
    
    @pytest.fixture
    def service(self):
        """Create view service instance."""
        return ViewService()
    
    def test_valid_non_technical_view(self, service):
        """Test that non_technical view mode is valid."""
        assert ViewMode.is_valid("non_technical") is True
    
    def test_valid_technical_view(self, service):
        """Test that technical view mode is valid."""
        assert ViewMode.is_valid("technical") is True
    
    def test_invalid_view_mode(self, service):
        """Test that invalid view mode returns False."""
        assert ViewMode.is_valid("invalid") is False
        assert ViewMode.is_valid("") is False
    
    def test_get_default_for_operations_role(self, service):
        """Test default view mode for operations role."""
        default = ViewMode.get_default_for_role(UserRole.OPERATIONS)
        assert default == ViewMode.NON_TECHNICAL
    
    def test_get_default_for_developer_role(self, service):
        """Test default view mode for developer role."""
        default = ViewMode.get_default_for_role(UserRole.DEVELOPER)
        assert default == ViewMode.TECHNICAL
    
    def test_get_default_for_admin_role(self, service):
        """Test default view mode for admin role."""
        default = ViewMode.get_default_for_role(UserRole.ADMIN)
        assert default == ViewMode.TECHNICAL


class TestUserRoleValidation:
    """Tests for user role validation."""
    
    def test_valid_operations_role(self):
        """Test that operations role is valid."""
        assert UserRole.is_valid("operations") is True
    
    def test_valid_developer_role(self):
        """Test that developer role is valid."""
        assert UserRole.is_valid("developer") is True
    
    def test_valid_admin_role(self):
        """Test that admin role is valid."""
        assert UserRole.is_valid("admin") is True
    
    def test_invalid_role(self):
        """Test that invalid role returns False."""
        assert UserRole.is_valid("invalid") is False
        assert UserRole.is_valid("") is False


class TestNonTechnicalViewTransformation:
    """Tests for non-technical view transformation."""
    
    @pytest.fixture
    def service(self):
        """Create view service instance."""
        return ViewService()
    
    def test_transform_element_not_found(self, service):
        """Test transformation of element_not_found error."""
        failure_data = {
            "failure_id": 1,
            "failed_selector": ".team-name",
            "error_type": "element_not_found",
        }
        
        result = service.transform_failure_to_view(
            failure_data=failure_data,
            view_mode=ViewMode.NON_TECHNICAL,
            user_role=UserRole.OPERATIONS,
        )
        
        assert result["failure_id"] == 1
        assert "non_technical" in result
        assert "description" in result["non_technical"]
        assert "impact" in result["non_technical"]
        assert "suggested_action" in result["non_technical"]
    
    def test_transform_selector_invalid(self, service):
        """Test transformation of selector_invalid error."""
        failure_data = {
            "failure_id": 2,
            "failed_selector": "#score-board",
            "error_type": "selector_invalid",
        }
        
        result = service.transform_failure_to_view(
            failure_data=failure_data,
            view_mode=ViewMode.NON_TECHNICAL,
            user_role=UserRole.OPERATIONS,
        )
        
        assert result["failure_id"] == 2
        assert "description" in result["non_technical"]
        assert "impact" in result["non_technical"]
    
    def test_transform_timeout(self, service):
        """Test transformation of timeout error."""
        failure_data = {
            "failure_id": 3,
            "failed_selector": ".live-score",
            "error_type": "timeout",
        }
        
        result = service.transform_failure_to_view(
            failure_data=failure_data,
            view_mode=ViewMode.NON_TECHNICAL,
            user_role=UserRole.OPERATIONS,
        )
        
        assert result["failure_id"] == 3
        assert "description" in result["non_technical"]
        assert "suggested_action" in result["non_technical"]
    
    def test_transform_unknown_error(self, service):
        """Test transformation of unknown error type."""
        failure_data = {
            "failure_id": 4,
            "failed_selector": ".unknown",
            "error_type": "unknown",
        }
        
        result = service.transform_failure_to_view(
            failure_data=failure_data,
            view_mode=ViewMode.NON_TECHNICAL,
            user_role=UserRole.OPERATIONS,
        )
        
        assert result["failure_id"] == 4
        assert "non_technical" in result


class TestTechnicalViewTransformation:
    """Tests for technical view transformation."""
    
    @pytest.fixture
    def service(self):
        """Create view service instance."""
        return ViewService()
    
    def test_transform_to_technical_view(self, service):
        """Test transformation to technical view."""
        failure_data = {
            "failure_id": 1,
            "failed_selector": ".team-name",
            "strategy": "css",
            "confidence_score": 0.85,
            "dom_path": "div.container > span.team-name",
            "failure_reason": "Element not found in DOM",
            "error_type": "element_not_found",
            "severity": "minor",
            "alternatives": [
                {
                    "selector": ".team-name-v2",
                    "strategy": "css",
                    "confidence_score": 0.92,
                    "blast_radius": None,
                    "is_custom": False,
                }
            ],
        }
        
        result = service.transform_failure_to_view(
            failure_data=failure_data,
            view_mode=ViewMode.TECHNICAL,
            user_role=UserRole.DEVELOPER,
        )
        
        assert result["failure_id"] == 1
        assert "technical" in result
        assert result["technical"]["selector"] == ".team-name"
        assert result["technical"]["strategy"] == "css"
        assert result["technical"]["confidence"] == 0.85
        assert result["technical"]["dom_path"] == "div.container > span.team-name"
        assert len(result["technical"]["alternatives"]) == 1
    
    def test_transform_technical_view_without_alternatives(self, service):
        """Test technical view without alternatives."""
        failure_data = {
            "failure_id": 2,
            "failed_selector": "#score",
            "strategy": "xpath",
            "confidence_score": 0.75,
            "dom_path": "div#main > div#score",
            "failure_reason": "Stale element reference",
            "error_type": "stale_element",
            "severity": "moderate",
        }
        
        result = service.transform_failure_to_view(
            failure_data=failure_data,
            view_mode=ViewMode.TECHNICAL,
            user_role=UserRole.DEVELOPER,
        )
        
        assert result["failure_id"] == 2
        assert "technical" in result
        assert result["technical"]["alternatives"] == []


class TestUserInfo:
    """Tests for user info retrieval."""
    
    @pytest.fixture
    def service(self):
        """Create view service instance."""
        return ViewService()
    
    @patch('src.selectors.adaptive.services.view_service.UserPreferenceRepository')
    def test_get_user_info_existing_user(self, mock_repo_class, service):
        """Test getting info for existing user."""
        mock_pref = Mock()
        mock_pref.user_id = "user_123"
        mock_pref.role = UserRole.OPERATIONS
        mock_pref.default_view = ViewMode.NON_TECHNICAL
        mock_pref.last_view_mode = ViewMode.NON_TECHNICAL
        
        mock_repo = Mock()
        mock_repo.get_by_user_id.return_value = mock_pref
        service.user_repo = mock_repo
        
        info = service.get_user_info("user_123")
        
        assert info["user_id"] == "user_123"
        assert info["user_role"] == UserRole.OPERATIONS
        assert info["default_view"] == ViewMode.NON_TECHNICAL
        assert "permissions" in info
    
    @patch('src.selectors.adaptive.services.view_service.UserPreferenceRepository')
    def test_get_user_info_unknown_user(self, mock_repo_class, service):
        """Test getting info for unknown user returns defaults."""
        mock_repo = Mock()
        mock_repo.get_by_user_id.return_value = None
        service.user_repo = mock_repo
        
        info = service.get_user_info("unknown_user")
        
        assert info["user_id"] == "unknown_user"
        assert info["user_role"] == UserRole.OPERATIONS
        assert info["default_view"] == ViewMode.NON_TECHNICAL


class TestPermissions:
    """Tests for role-based permissions."""
    
    @pytest.fixture
    def service(self):
        """Create view service instance."""
        return ViewService()
    
    def test_operations_permissions(self, service):
        """Test operations role permissions."""
        perms = service._get_permissions_for_role(UserRole.OPERATIONS)
        
        assert "view" in perms
        assert "approve" in perms
        assert "reject" in perms
        assert "escalate" in perms
    
    def test_developer_permissions(self, service):
        """Test developer role permissions."""
        perms = service._get_permissions_for_role(UserRole.DEVELOPER)
        
        assert "view" in perms
        assert "approve" in perms
        assert "reject" in perms
        assert "create_custom_selector" in perms
        assert "view_technical" in perms
    
    def test_admin_permissions(self, service):
        """Test admin role permissions."""
        perms = service._get_permissions_for_role(UserRole.ADMIN)
        
        assert "view" in perms
        assert "approve" in perms
        assert "reject" in perms
        assert "create_custom_selector" in perms
        assert "view_technical" in perms
        assert "manage_users" in perms


class TestSelectorNameExtraction:
    """Tests for selector name extraction."""
    
    @pytest.fixture
    def service(self):
        """Create view service instance."""
        return ViewService()
    
    def test_class_selector(self, service):
        """Test extracting name from class selector."""
        name = service._extract_selector_name(".team-name")
        assert "team-name" in name
    
    def test_id_selector(self, service):
        """Test extracting name from ID selector."""
        name = service._extract_selector_name("#score-board")
        assert "score-board" in name
    
    def test_attribute_selector(self, service):
        """Test extracting name from attribute selector."""
        name = service._extract_selector_name("[data-testid=score]")
        assert "attribute" in name.lower()
    
    def test_complex_selector(self, service):
        """Test handling of complex selector."""
        name = service._extract_selector_name("div.container > span.score")
        assert "element" in name.lower()


class TestViewModeSwitch:
    """Tests for view mode switching."""
    
    @pytest.fixture
    def service(self):
        """Create view service instance."""
        return ViewService()
    
    @patch('src.selectors.adaptive.services.view_service.UserPreferenceRepository')
    def test_switch_view_mode_success(self, mock_repo_class, service):
        """Test successful view mode switch."""
        mock_pref = Mock()
        mock_pref.user_id = "user_123"
        mock_pref.last_view_mode = ViewMode.NON_TECHNICAL
        mock_pref.default_view = ViewMode.NON_TECHNICAL
        
        mock_repo = Mock()
        mock_repo.get_by_user_id.return_value = mock_pref
        mock_repo.switch_view_mode.return_value = mock_pref
        service.user_repo = mock_repo
        
        result = service.switch_view_mode("user_123", ViewMode.TECHNICAL)
        
        assert result["success"] is True
        assert result["new_view_mode"] == ViewMode.TECHNICAL
    
    @patch('src.selectors.adaptive.services.view_service.UserPreferenceRepository')
    def test_switch_view_mode_invalid(self, mock_repo_class, service):
        """Test switching to invalid view mode."""
        result = service.switch_view_mode("user_123", "invalid_mode")
        
        assert result["success"] is False
    
    @patch('src.selectors.adaptive.services.view_service.UserPreferenceRepository')
    def test_switch_view_mode_user_not_found(self, mock_repo_class, service):
        """Test switching for non-existent user."""
        mock_repo = Mock()
        mock_repo.get_by_user_id.return_value = None
        service.user_repo = mock_repo
        
        result = service.switch_view_mode("unknown_user", ViewMode.TECHNICAL)
        
        assert result["success"] is False
