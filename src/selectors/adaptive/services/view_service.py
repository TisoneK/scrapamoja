"""
View Service for transforming failure data between technical and non-technical views.

This implements Story 7.2 (Technical and Non-Technical Views) requirements.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..db.models.user_preferences import UserPreference, ViewMode, UserRole
from ..db.repositories.user_repository import UserPreferenceRepository, ViewUsageRepository
from .visual_preview_service import get_visual_preview_service
from .dom_viewer_service import get_dom_viewer_service
from src.observability.logger import get_logger


class ViewService:
    """Service for managing view mode and transforming data between views."""
    
    # Mapping of technical error types to non-technical descriptions
    ERROR_DESCRIPTIONS = {
        "element_not_found": "The required information could not be found on the page",
        "selector_invalid": "The selector used to find the information is no longer valid",
        "timeout": "The page took too long to load and the operation timed out",
        "stale_element": "The page content changed and the information could not be found",
        "navigation_error": "There was a problem loading the page",
        "unknown": "An unexpected error occurred while extracting the information",
    }
    
    # Mapping of technical error types to business impact
    ERROR_IMPACT = {
        "element_not_found": "High - Live data may not be updating",
        "selector_invalid": "Medium - Some content may not be displayed correctly",
        "timeout": "Medium - Data updates may be delayed",
        "stale_element": "Low - Brief display issues may occur",
        "navigation_error": "High - Page may not load properly",
        "unknown": "Medium - Some features may not work as expected",
    }
    
    # Suggested actions for non-technical users
    SUGGESTED_ACTIONS = {
        "element_not_found": "The technical team will investigate and propose a solution",
        "selector_invalid": "A new selector will be created automatically",
        "timeout": "Please try again in a few minutes",
        "stale_element": "The system will retry automatically",
        "navigation_error": "Please refresh the page and try again",
        "unknown": "The technical team has been notified",
    }
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the view service.
        
        Args:
            db_path: Optional path to SQLite database file.
        """
        self._logger = get_logger("view_service")
        self.user_repo = UserPreferenceRepository(db_path)
        self.usage_repo = ViewUsageRepository(db_path)
        self.visual_preview_service = get_visual_preview_service()
        self.dom_viewer_service = get_dom_viewer_service()
    
    def get_user_info(
        self, 
        user_id: str, 
        include_permissions: bool = True
    ) -> Dict[str, Any]:
        """
        Get user information including role and view preferences.
        
        Args:
            user_id: The user ID
            include_permissions: Whether to include permissions in response
            
        Returns:
            Dictionary with user info
        """
        preference = self.user_repo.get_by_user_id(user_id)
        
        if preference is None:
            # Return default for unknown users
            return {
                "user_id": user_id,
                "user_role": UserRole.OPERATIONS,
                "default_view": ViewMode.NON_TECHNICAL,
                "available_views": [ViewMode.NON_TECHNICAL, ViewMode.TECHNICAL],
                "permissions": ["approve", "reject", "escalate"] if include_permissions else [],
            }
        
        permissions = self._get_permissions_for_role(preference.role)
        
        return {
            "user_id": preference.user_id,
            "user_role": preference.role,
            "default_view": preference.default_view,
            "available_views": [ViewMode.NON_TECHNICAL, ViewMode.TECHNICAL],
            "permissions": permissions if include_permissions else [],
        }
    
    def switch_view_mode(
        self, 
        user_id: str, 
        new_view_mode: str
    ) -> Dict[str, Any]:
        """
        Switch user's view mode.
        
        Args:
            user_id: The user ID
            new_view_mode: The new view mode
            
        Returns:
            Dictionary with switch result
        """
        # Validate view mode
        if not ViewMode.is_valid(new_view_mode):
            return {
                "success": False,
                "message": f"Invalid view mode: {new_view_mode}. Valid modes: {ViewMode.NON_TECHNICAL}, {ViewMode.TECHNICAL}",
                "previous_view_mode": None,
                "new_view_mode": None,
            }
        
        # Get current preference
        preference = self.user_repo.get_by_user_id(user_id)
        
        if preference is None:
            return {
                "success": False,
                "message": f"User {user_id} not found",
                "previous_view_mode": None,
                "new_view_mode": new_view_mode,
            }
        
        previous_view_mode = preference.last_view_mode or preference.default_view
        
        # Switch view mode
        updated = self.user_repo.switch_view_mode(user_id, new_view_mode)
        
        if updated is None:
            return {
                "success": False,
                "message": "Failed to update view mode",
                "previous_view_mode": previous_view_mode,
                "new_view_mode": new_view_mode,
            }
        
        return {
            "success": True,
            "message": f"View mode switched from {previous_view_mode} to {new_view_mode}",
            "previous_view_mode": previous_view_mode,
            "new_view_mode": new_view_mode,
        }
    
    def transform_failure_to_view(
        self,
        failure_data: Dict[str, Any],
        view_mode: str,
        user_role: str = UserRole.OPERATIONS,
    ) -> Dict[str, Any]:
        """
        Transform failure data based on view mode and user role.
        
        Args:
            failure_data: The raw failure data from the database
            view_mode: The target view mode (technical or non_technical)
            user_role: The user's role
            
        Returns:
            Transformed failure data for the specific view
        """
        if view_mode == ViewMode.NON_TECHNICAL:
            return self._transform_to_non_technical(failure_data)
        else:
            return self._transform_to_technical(failure_data)
    
    def _transform_to_non_technical(self, failure_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform failure data to non-technical view.
        
        Args:
            failure_data: The raw failure data
            
        Returns:
            Non-technical view of the failure
        """
        error_type = failure_data.get("error_type", "unknown")
        
        # Get plain language description
        description = self.ERROR_DESCRIPTIONS.get(
            error_type, 
            self.ERROR_DESCRIPTIONS["unknown"]
        )
        
        # Add selector context if available
        selector = failure_data.get("failed_selector", "")
        if selector:
            # Convert technical selector to plain language
            # Extract meaningful part from selector
            selector_name = self._extract_selector_name(selector)
            description = f"{description} ({selector_name})"
        
        # Get business impact
        impact = self.ERROR_IMPACT.get(
            error_type,
            self.ERROR_IMPACT["unknown"]
        )
        
        # Get suggested action
        suggested_action = self.SUGGESTED_ACTIONS.get(
            error_type,
            self.SUGGESTED_ACTIONS["unknown"]
        )
        
        # Generate visual preview
        visual_preview = None
        try:
            visual_preview = self.visual_preview_service.generate_selector_preview(
                selector=selector,
                highlight_color="#FF6B6B"
            )
        except Exception as e:
            # Log error but don't fail the transformation
            self._logger.error(f"Failed to generate visual preview: {e}")
        
        return {
            "failure_id": failure_data.get("failure_id"),
            "non_technical": {
                "description": description,
                "impact": impact,
                "visual_preview": visual_preview,
                "suggested_action": suggested_action,
            },
        }
    
    def _transform_to_technical(self, failure_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform failure data to technical view.
        
        Args:
            failure_data: The raw failure data
            
        Returns:
            Technical view of the failure
        """
        # Extract alternatives if present
        alternatives = []
        for alt in failure_data.get("alternatives", []):
            alternatives.append({
                "selector": alt.get("selector", ""),
                "strategy": alt.get("strategy", "css"),
                "confidence": alt.get("confidence_score", 0.0),
                "blast_radius": alt.get("blast_radius"),
                "is_custom": alt.get("is_custom", False),
            })
        
        # Generate DOM structure analysis
        dom_analysis = None
        try:
            selector = failure_data.get("failed_selector", "")
            dom_analysis_result = self.dom_viewer_service.analyze_dom_structure(selector)
            dom_analysis = dom_analysis_result.to_dict()
            
            # Add DOM alternatives to the alternatives list
            if dom_analysis_result.potential_alternatives:
                alternatives.extend(dom_analysis_result.potential_alternatives)
                
        except Exception as e:
            self._logger.error(f"Failed to generate DOM analysis: {e}")
        
        return {
            "failure_id": failure_data.get("failure_id"),
            "technical": {
                "selector": failure_data.get("failed_selector", ""),
                "strategy": failure_data.get("strategy", "css"),
                "confidence": failure_data.get("confidence_score", 0.0),
                "dom_path": failure_data.get("dom_path", ""),
                "error": failure_data.get("failure_reason", ""),
                "error_type": failure_data.get("error_type", ""),
                "snapshot_id": failure_data.get("snapshot_id"),
                "alternatives": alternatives,
                "severity": failure_data.get("severity", "minor"),
                "dom_analysis": dom_analysis,
            },
        }
    
    def _extract_selector_name(self, selector: str) -> str:
        """
        Extract a human-readable name from a CSS selector.
        
        Args:
            selector: The CSS selector string
            
        Returns:
            Human-readable name
        """
        # Remove common prefixes and get the meaningful part
        cleaned = selector.strip()
        
        # Handle common patterns
        if cleaned.startswith("."):
            # Class selector - get the class name
            class_name = cleaned[1:]
            return f"'{class_name}' element"
        elif cleaned.startswith("#"):
            # ID selector
            id_name = cleaned[1:]
            return f"'{id_name}' element"
        elif cleaned.startswith("["):
            # Attribute selector
            return "attribute-based element"
        else:
            # Generic or complex selector
            return "selected element"
    
    def _get_permissions_for_role(self, role: str) -> List[str]:
        """
        Get permissions for a given role.
        
        Args:
            role: The user role
            
        Returns:
            List of permission strings
        """
        base_permissions = ["view"]
        
        if role == UserRole.OPERATIONS:
            return base_permissions + ["approve", "reject", "escalate"]
        elif role == UserRole.DEVELOPER:
            return base_permissions + ["approve", "reject", "create_custom_selector", "view_technical"]
        elif role == UserRole.ADMIN:
            return base_permissions + ["approve", "reject", "create_custom_selector", "view_technical", "manage_users"]
        
        return base_permissions
    
    def create_user_preference(
        self,
        user_id: str,
        role: str = UserRole.OPERATIONS,
        default_view: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None,
    ) -> UserPreference:
        """
        Create a new user preference.
        
        Args:
            user_id: Unique user identifier
            role: User role
            default_view: Default view mode preference
            custom_settings: Custom settings
            
        Returns:
            Created user preference
        """
        return self.user_repo.create_user_preference(
            user_id=user_id,
            role=role,
            default_view=default_view,
            custom_settings=custom_settings,
        )
    
    def get_user_preference(self, user_id: str) -> Optional[UserPreference]:
        """
        Get user preference by user ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            User preference if found
        """
        return self.user_repo.get_by_user_id(user_id)
    
    def get_usage_statistics(
        self,
        user_id: Optional[str] = None,
        view_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get view usage statistics.
        
        Args:
            user_id: Optional user ID to filter by
            view_mode: Optional view mode to filter by
            
        Returns:
            Usage statistics
        """
        return self.usage_repo.get_usage_statistics(user_id, view_mode)


# Global instance for dependency injection
_view_service: Optional[ViewService] = None


def get_view_service() -> ViewService:
    """Get or create the global view service instance."""
    global _view_service
    if _view_service is None:
        _view_service = ViewService()
    return _view_service
