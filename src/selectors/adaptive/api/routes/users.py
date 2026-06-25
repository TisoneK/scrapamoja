"""
API routes for user and view management endpoints.

This implements Story 7.2 (Technical and Non-Technical Views):
- User role detection and view switching
- View mode toggle
- Persistent view preference storage

Routes:
- GET /users/me - Get current user info
- PUT /users/me/preferences - Update user preferences
- POST /users/me/view-mode - Switch view mode
- GET /users/me/usage - Get view usage statistics
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ..schemas.users import (
    UserPreferenceCreateSchema,
    UserPreferenceUpdateSchema,
    UserPreferenceResponseSchema,
    UserPreferencesResponseSchema,
    UserInfoResponseSchema,
    ViewModeSwitchSchema,
    ViewModeSwitchResponseSchema,
    ViewUsageAnalyticsListSchema,
    UserRoleSchema,
    ViewModeSchema,
)
from ..services.view_service import ViewService, get_view_service
from ..db.models.user_preferences import UserRole, ViewMode


# Create router
router = APIRouter(prefix="/users", tags=["users"])


def _get_default_user_id() -> str:
    """
    Get default user ID for development.
    
    In production, this would come from authentication.
    """
    return "default_user"


@router.get(
    "/me",
    response_model=UserInfoResponseSchema,
    summary="Get current user info",
    description="Get current user information including role and view preferences",
)
async def get_current_user_info(
    user_id: Optional[str] = Query(None, description="User ID (optional, uses default if not provided)"),
    service: ViewService = Query(None, description="View service dependency"),
) -> UserInfoResponseSchema:
    """
    Get current user information including role and view preferences.
    
    Returns:
        User info with role, default view, and permissions
    """
    if service is None:
        service = get_view_service()
    
    # Use provided user_id or default
    uid = user_id or _get_default_user_id()
    
    info = service.get_user_info(uid)
    
    return UserInfoResponseSchema(data=info)


@router.post(
    "",
    response_model=UserPreferencesResponseSchema,
    summary="Create user preferences",
    description="Create new user preferences with role and view settings",
    responses={
        400: {"description": "Invalid request or user already exists"},
    },
)
async def create_user_preferences(
    request: UserPreferenceCreateSchema,
    service: ViewService = Query(None, description="View service dependency"),
) -> UserPreferencesResponseSchema:
    """
    Create new user preferences.
    
    Args:
        request: User preference creation request
        
    Returns:
        Created user preferences
    """
    if service is None:
        service = get_view_service()
    
    # Validate role
    if request.role not in UserRoleSchema.get_all():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles: {UserRoleSchema.get_all()}",
        )
    
    # Validate default_view if provided
    if request.default_view is not None and request.default_view not in ViewModeSchema.get_all():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid view mode. Valid modes: {ViewModeSchema.get_all()}",
        )
    
    try:
        preference = service.create_user_preference(
            user_id=request.user_id,
            role=request.role,
            default_view=request.default_view,
            custom_settings=request.custom_settings,
        )
        
        return UserPreferencesResponseSchema(
            data=UserPreferenceResponseSchema(**preference.to_dict())
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{target_user_id}",
    response_model=UserPreferencesResponseSchema,
    summary="Get user preferences",
    description="Get preferences for a specific user",
    responses={
        404: {"description": "User not found"},
    },
)
async def get_user_preferences(
    target_user_id: str,
    service: ViewService = Query(None, description="View service dependency"),
) -> UserPreferencesResponseSchema:
    """
    Get user preferences by user ID.
    
    Args:
        target_user_id: The user ID to look up
        
    Returns:
        User preferences
    """
    if service is None:
        service = get_view_service()
    
    preference = service.get_user_preference(target_user_id)
    
    if preference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {target_user_id} not found",
        )
    
    return UserPreferencesResponseSchema(
        data=UserPreferenceResponseSchema(**preference.to_dict())
    )


@router.put(
    "/me/preferences",
    response_model=UserPreferencesResponseSchema,
    summary="Update current user preferences",
    description="Update preferences for the current user",
    responses={
        404: {"description": "User not found"},
    },
)
async def update_user_preferences(
    request: UserPreferenceUpdateSchema,
    user_id: Optional[str] = Query(None, description="User ID (optional)"),
    service: ViewService = Query(None, description="View service dependency"),
) -> UserPreferencesResponseSchema:
    """
    Update current user preferences.
    
    Args:
        request: User preference update request
        user_id: Optional user ID override
        
    Returns:
        Updated user preferences
    """
    if service is None:
        service = get_view_service()
    
    # Use provided user_id or default
    uid = user_id or _get_default_user_id()
    
    # Validate role if provided
    if request.role is not None and request.role not in UserRoleSchema.get_all():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles: {UserRoleSchema.get_all()}",
        )
    
    # Validate default_view if provided
    if request.default_view is not None and request.default_view not in ViewModeSchema.get_all():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid view mode. Valid modes: {ViewModeSchema.get_all()}",
        )
    
    # Get the user repo to update
    from ..db.repositories.user_repository import UserPreferenceRepository
    repo = UserPreferenceRepository()
    
    updated = repo.update_user_preference(
        user_id=uid,
        role=request.role,
        default_view=request.default_view,
        custom_settings=request.custom_settings,
    )
    
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {uid} not found",
        )
    
    return UserPreferencesResponseSchema(
        data=UserPreferenceResponseSchema(**updated.to_dict())
    )


@router.post(
    "/me/view-mode",
    response_model=ViewModeSwitchResponseSchema,
    summary="Switch view mode",
    description="Switch the current user's view mode between technical and non-technical",
)
async def switch_view_mode(
    request: ViewModeSwitchSchema,
    user_id: Optional[str] = Query(None, description="User ID (optional)"),
    service: ViewService = Query(None, description="View service dependency"),
) -> ViewModeSwitchResponseSchema:
    """
    Switch user's view mode.
    
    Args:
        request: View mode switch request
        user_id: Optional user ID override
        
    Returns:
        View mode switch result
    """
    if service is None:
        service = get_view_service()
    
    # Use provided user_id or default
    uid = user_id or _get_default_user_id()
    
    result = service.switch_view_mode(uid, request.view_mode)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"],
        )
    
    return ViewModeSwitchResponseSchema(
        success=result["success"],
        message=result["message"],
        previous_view_mode=result["previous_view_mode"],
        new_view_mode=result["new_view_mode"],
        timestamp=datetime.utcnow(),
    )


@router.get(
    "/me/usage",
    response_model=ViewUsageAnalyticsListSchema,
    summary="Get view usage statistics",
    description="Get view usage statistics for the current user",
)
async def get_view_usage(
    user_id: Optional[str] = Query(None, description="User ID (optional)"),
    service: ViewService = Query(None, description="View service dependency"),
) -> ViewUsageAnalyticsListSchema:
    """
    Get view usage statistics for current user.
    
    Args:
        user_id: Optional user ID override
        
    Returns:
        View usage statistics
    """
    if service is None:
        service = get_view_service()
    
    # Use provided user_id or default
    uid = user_id or _get_default_user_id()
    
    stats = service.get_usage_statistics(user_id=uid)
    
    # For now, return the statistics as the data
    # In a full implementation, we'd return the actual usage records
    return ViewUsageAnalyticsListSchema(
        data=[],  # Empty for now, would populate from actual records
        total=stats.get("total_sessions", 0),
    )
