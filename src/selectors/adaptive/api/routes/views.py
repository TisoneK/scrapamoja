"""
API routes for view mode endpoints.

This implements Story 7.2 (Technical and Non-Technical Views):
- View-adaptive failure responses
- Non-technical and technical view transformations

Routes:
- GET /views/failures/{id} - Get failure in specific view mode
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from .failures import _create_problem_detail
from ..schemas.failures import FailureDetailResponseSchema, ProblemDetailSchema
from ..schemas.users import ViewAdaptiveFailureResponse
from ..services.view_service import ViewService, get_view_service
from ..services.failure_service import FailureService, get_failure_service
from ..db.models.user_preferences import ViewMode


# Create router
router = APIRouter(prefix="/views", tags=["views"])


@router.get(
    "/failures/{failure_id}",
    response_model=ViewAdaptiveFailureResponse,
    summary="Get failure in view-adaptive format",
    description="Get failure details formatted for either technical or non-technical view. Automatically selects view mode based on user preferences if not specified.",
    responses={
        404: {"model": ProblemDetailSchema, "description": "Failure not found"},
    },
)
async def get_failure_adaptive(
    failure_id: int,
    view_mode: str = Query(
        None, 
        description="View mode: technical or non_technical. If not provided, uses user preference"
    ),
    user_id: Optional[str] = Query(None, description="User ID for permission checking and preference detection"),
    include_alternatives: bool = Query(True, description="Include proposed alternatives"),
    view_service: ViewService = Query(None, description="View service dependency"),
    failure_service: FailureService = Query(None, description="Failure service dependency"),
) -> ViewAdaptiveFailureResponse:
    """
    Get failure details in view-adaptive format.
    
    Automatically selects view mode based on user preferences if not explicitly provided.
    Returns either non-technical or technical view based on the view_mode parameter or user preferences.
    
    Args:
        failure_id: The failure ID
        view_mode: Target view mode (technical or non_technical). If None, uses user preference
        user_id: Optional user ID for permission checking and preference detection
        include_alternatives: Whether to include alternatives
        
    Returns:
        Failure data formatted for the appropriate view mode
    """
    if view_service is None:
        view_service = get_view_service()
    
    if failure_service is None:
        failure_service = get_failure_service()
    
    # Use provided user_id or default
    uid = user_id or "default_user"
    
    # Auto-select view mode if not provided
    if view_mode is None:
        user_info = view_service.get_user_info(uid)
        view_mode = user_info.get("default_view", ViewMode.NON_TECHNICAL)
    else:
        # Get user info for permission checking
        user_info = view_service.get_user_info(uid)
    
    user_role = user_info.get("user_role", "operations")
    
    # Validate view mode
    if not ViewMode.is_valid(view_mode):
        problem = _create_problem_detail(
            title="Invalid View Mode",
            detail=f"Invalid view mode: {view_mode}. Valid modes: {ViewMode.NON_TECHNICAL}, {ViewMode.TECHNICAL}",
            status_code=400,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=problem.model_dump(),
        )
    
    # For non-technical view, check if user has technical access
    if view_mode == ViewMode.TECHNICAL and user_role not in ["developer", "admin"]:
        problem = _create_problem_detail(
            title="Insufficient Permissions",
            detail="Technical view requires developer or admin role",
            status_code=403,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=problem.model_dump(),
        )
    
    # Get raw failure data
    detail = failure_service.get_failure_detail(
        failure_id=failure_id,
        include_alternatives=include_alternatives,
    )
    
    if detail is None:
        problem = _create_problem_detail(
            title="Not Found",
            detail=f"Failure with ID {failure_id} not found",
            status_code=404,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=problem.model_dump(),
        )
    
    # Transform to the appropriate view
    transformed = view_service.transform_failure_to_view(
        failure_data=detail,
        view_mode=view_mode,
        user_role=user_role,
    )
    
    # Add view mode metadata to response
    transformed["view_mode_used"] = view_mode
    transformed["auto_selected"] = view_mode is None
    transformed["user_role"] = user_role
    
    return ViewAdaptiveFailureResponse(failure=transformed)


@router.get(
    "/modes",
    summary="Get available view modes",
    description="Get list of available view modes and their descriptions",
)
async def get_view_modes() -> dict:
    """
    Get available view modes.
    
    Returns:
        Dictionary of available view modes
    """
    return {
        "view_modes": [
            {
                "id": "non_technical",
                "name": "Non-Technical View",
                "description": "Simplified view with plain language descriptions and visual previews",
                "target_users": ["Operations", "Non-technical staff"],
            },
            {
                "id": "technical",
                "name": "Technical View",
                "description": "Detailed view with full selector details, DOM structure, and confidence scores",
                "target_users": ["Developers", "Technical staff"],
            },
        ],
    }
