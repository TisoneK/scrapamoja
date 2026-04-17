"""
API routes for Feature Flag management endpoints.

This implements Story 8.1 (Sport-Based Feature Flags) requirements:
- GET /feature-flags endpoint to list all flags
- PATCH /feature-flags/{sport} endpoint to toggle sport flags
- Additional endpoints for comprehensive flag management
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status, Path
from fastapi.responses import JSONResponse

from ..schemas.feature_flags import (
    FeatureFlagCreateSchema,
    FeatureFlagUpdateSchema,
    FeatureFlagResponseSchema,
    FeatureFlagListResponseSchema,
    FeatureFlagToggleSchema,
    FeatureFlagCheckSchema,
    FeatureFlagCheckResponseSchema,
    FeatureFlagBulkCreateSchema,
    EnabledSportsResponseSchema,
    FeatureFlagStatsResponseSchema,
)
from ..services.feature_flag_service import FeatureFlagService, get_feature_flag_service
from ..db.models.feature_flag import FeatureFlag


# Create router
router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


def _get_default_user_id() -> str:
    """
    Get default user ID for development.
    
    In production, this would come from authentication.
    """
    return "default_user"


def _feature_flag_to_response(flag: FeatureFlag) -> FeatureFlagResponseSchema:
    """Convert FeatureFlag model to response schema."""
    return FeatureFlagResponseSchema(
        id=flag.id,
        sport=flag.sport,
        site=flag.site,
        enabled=flag.enabled,
        created_at=flag.created_at,
        updated_at=flag.updated_at,
    )


@router.get(
    "",
    response_model=FeatureFlagListResponseSchema,
    summary="List all feature flags",
    description="Get all feature flags with optional filtering by sport or site",
)
async def list_feature_flags(
    sport: Optional[str] = Query(None, description="Filter by sport name"),
    site: Optional[str] = Query(None, description="Filter by site name"),
    service: FeatureFlagService = Query(None, description="Feature flag service dependency"),
) -> FeatureFlagListResponseSchema:
    """
    List all feature flags.
    
    Args:
        sport: Optional sport filter
        site: Optional site filter
        service: Feature flag service (dependency injection)
        
    Returns:
        List of feature flags matching filters
    """
    if service is None:
        service = get_feature_flag_service()
    
    if sport:
        flags = service.get_feature_flags_by_sport(sport)
    else:
        flags = service.get_all_feature_flags()
    
    # Apply site filter if provided
    if site:
        flags = [flag for flag in flags if flag.site == site]
    
    response_data = [_feature_flag_to_response(flag) for flag in flags]
    
    return FeatureFlagListResponseSchema(
        data=response_data,
        count=len(response_data)
    )


@router.get(
    "/enabled-sports",
    response_model=EnabledSportsResponseSchema,
    summary="Get enabled sports",
    description="Get list of sports with adaptive system enabled",
)
async def get_enabled_sports(
    service: FeatureFlagService = Query(None, description="Feature flag service dependency"),
) -> EnabledSportsResponseSchema:
    """
    Get list of sports with adaptive system enabled.
    
    Args:
        service: Feature flag service (dependency injection)
        
    Returns:
        List of enabled sports
    """
    if service is None:
        service = get_feature_flag_service()
    
    enabled_sports = service.get_enabled_sports()
    
    return EnabledSportsResponseSchema(
        sports=enabled_sports,
        count=len(enabled_sports)
    )


@router.get(
    "/check",
    response_model=FeatureFlagCheckResponseSchema,
    summary="Check feature flag status",
    description="Check if adaptive system is enabled for a specific sport/site",
)
async def check_feature_flag(
    sport: str = Query(..., description="Sport name to check"),
    site: Optional[str] = Query(None, description="Optional site name to check"),
    service: FeatureFlagService = Query(None, description="Feature flag service dependency"),
) -> FeatureFlagCheckResponseSchema:
    """
    Check if adaptive system is enabled for a sport/site.
    
    Args:
        sport: Sport name
        site: Optional site name
        service: Feature flag service (dependency injection)
        
    Returns:
        Feature flag status
    """
    if service is None:
        service = get_feature_flag_service()
    
    flag = service.get_feature_flag(sport, site)
    enabled = service.is_adaptive_enabled(sport, site)
    
    return FeatureFlagCheckResponseSchema(
        sport=sport,
        site=site,
        enabled=enabled,
        flag_exists=flag is not None
    )


@router.get(
    "/stats",
    response_model=FeatureFlagStatsResponseSchema,
    summary="Get feature flag statistics",
    description="Get statistics about feature flags usage",
)
async def get_feature_flag_stats(
    service: FeatureFlagService = Query(None, description="Feature flag service dependency"),
) -> FeatureFlagStatsResponseSchema:
    """
    Get feature flag statistics.
    
    Args:
        service: Feature flag service (dependency injection)
        
    Returns:
        Feature flag statistics
    """
    if service is None:
        service = get_feature_flag_service()
    
    all_flags = service.get_all_feature_flags()
    
    total_flags = len(all_flags)
    enabled_flags = len([f for f in all_flags if f.enabled])
    disabled_flags = total_flags - enabled_flags
    global_flags = len([f for f in all_flags if f.site is None])
    site_specific_flags = total_flags - global_flags
    unique_sports = len(set(f.sport for f in all_flags))
    
    return FeatureFlagStatsResponseSchema(
        total_flags=total_flags,
        enabled_flags=enabled_flags,
        disabled_flags=disabled_flags,
        global_flags=global_flags,
        site_specific_flags=site_specific_flags,
        unique_sports=unique_sports
    )


@router.get(
    "/{sport}",
    response_model=FeatureFlagListResponseSchema,
    summary="Get feature flags for sport",
    description="Get all feature flags for a specific sport (global + site-specific)",
)
async def get_sport_feature_flags(
    sport: str = Path(..., description="Sport name"),
    service: FeatureFlagService = Query(None, description="Feature flag service dependency"),
) -> FeatureFlagListResponseSchema:
    """
    Get all feature flags for a specific sport.
    
    Args:
        sport: Sport name
        service: Feature flag service (dependency injection)
        
    Returns:
        List of feature flags for the sport
    """
    if service is None:
        service = get_feature_flag_service()
    
    flags = service.get_feature_flags_by_sport(sport)
    response_data = [_feature_flag_to_response(flag) for flag in flags]
    
    return FeatureFlagListResponseSchema(
        data=response_data,
        count=len(response_data)
    )


@router.post(
    "",
    response_model=FeatureFlagResponseSchema,
    summary="Create feature flag",
    description="Create a new feature flag",
    status_code=status.HTTP_201_CREATED,
)
async def create_feature_flag(
    flag_data: FeatureFlagCreateSchema,
    service: FeatureFlagService = Query(None, description="Feature flag service dependency"),
) -> FeatureFlagResponseSchema:
    """
    Create a new feature flag.
    
    Args:
        flag_data: Feature flag creation data
        service: Feature flag service (dependency injection)
        
    Returns:
        Created feature flag
        
    Raises:
        HTTPException: If flag already exists
    """
    if service is None:
        service = get_feature_flag_service()
    
    try:
        flag = service.create_feature_flag(
            sport=flag_data.sport,
            site=flag_data.site,
            enabled=flag_data.enabled,
        )
        return _feature_flag_to_response(flag)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.post(
    "/bulk",
    response_model=FeatureFlagListResponseSchema,
    summary="Bulk create feature flags",
    description="Create multiple feature flags at once",
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_feature_flags(
    bulk_data: FeatureFlagBulkCreateSchema,
    service: FeatureFlagService = Query(None, description="Feature flag service dependency"),
) -> FeatureFlagListResponseSchema:
    """
    Create multiple feature flags at once.
    
    Args:
        bulk_data: Bulk creation data
        service: Feature flag service (dependency injection)
        
    Returns:
        List of created feature flags
    """
    if service is None:
        service = get_feature_flag_service()
    
    flags_data = [flag.model_dump() for flag in bulk_data.flags]
    flags = service.bulk_create_flags(flags_data)
    response_data = [_feature_flag_to_response(flag) for flag in flags]
    
    return FeatureFlagListResponseSchema(
        data=response_data,
        count=len(response_data)
    )


@router.patch(
    "/{sport}",
    response_model=FeatureFlagResponseSchema,
    summary="Toggle sport flag",
    description="Toggle adaptive system for a sport (global flag)",
)
async def toggle_sport_flag(
    sport: str = Path(..., description="Sport name"),
    flag_data: FeatureFlagToggleSchema = ...,
    service: FeatureFlagService = Query(None, description="Feature flag service dependency"),
) -> FeatureFlagResponseSchema:
    """
    Toggle adaptive system for a sport.
    
    Args:
        sport: Sport name
        service: Feature flag service (dependency injection)
        flag_data: Toggle data with new enabled state
        
    Returns:
        Updated feature flag
        
    Raises:
        HTTPException: If flag not found
    """
    if service is None:
        service = get_feature_flag_service()
    
    # Update with specific enabled state from request
    flag = service.update_feature_flag(sport, None, flag_data.enabled)
    
    if flag is None:
        # Create new flag if it doesn't exist
        flag = service.create_feature_flag(sport, None, flag_data.enabled)
    
    return _feature_flag_to_response(flag)


@router.patch(
    "/{sport}/sites/{site}",
    response_model=FeatureFlagResponseSchema,
    summary="Update site-specific flag",
    description="Update feature flag for a specific sport and site",
)
async def update_site_flag(
    sport: str = Path(..., description="Sport name"),
    site: str = Path(..., description="Site name"),
    flag_data: FeatureFlagUpdateSchema = ...,
    service: FeatureFlagService = Query(None, description="Feature flag service dependency"),
) -> FeatureFlagResponseSchema:
    """
    Update feature flag for a specific sport and site.
    
    Args:
        sport: Sport name
        site: Site name
        flag_data: Update data
        service: Feature flag service (dependency injection)
        
    Returns:
        Updated feature flag
        
    Raises:
        HTTPException: If flag not found
    """
    if service is None:
        service = get_feature_flag_service()
    
    flag = service.update_feature_flag(sport, site, flag_data.enabled)
    
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag not found for sport '{sport}' and site '{site}'"
        )
    
    return _feature_flag_to_response(flag)


@router.delete(
    "/{sport}",
    summary="Delete sport flag",
    description="Delete global feature flag for a sport",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_sport_flag(
    sport: str = Path(..., description="Sport name"),
    service: FeatureFlagService = Query(None, description="Feature flag service dependency"),
) -> None:
    """
    Delete global feature flag for a sport.
    
    Args:
        sport: Sport name
        service: Feature flag service (dependency injection)
        
    Raises:
        HTTPException: If flag not found
    """
    if service is None:
        service = get_feature_flag_service()
    
    deleted = service.delete_feature_flag(sport, None)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag not found for sport '{sport}'"
        )


@router.delete(
    "/{sport}/sites/{site}",
    summary="Delete site-specific flag",
    description="Delete feature flag for a specific sport and site",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_site_flag(
    sport: str = Path(..., description="Sport name"),
    site: str = Path(..., description="Site name"),
    service: FeatureFlagService = Query(None, description="Feature flag service dependency"),
) -> None:
    """
    Delete feature flag for a specific sport and site.
    
    Args:
        sport: Sport name
        site: Site name
        service: Feature flag service (dependency injection)
        
    Raises:
        HTTPException: If flag not found
    """
    if service is None:
        service = get_feature_flag_service()
    
    deleted = service.delete_feature_flag(sport, site)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag not found for sport '{sport}' and site '{site}'"
        )


@router.get(
    "/sites",
    response_model=FeatureFlagListResponseSchema,
    summary="List site-specific feature flags",
    description="Get all feature flags that have site-specific values (excluding global flags)",
)
async def list_site_flags() -> FeatureFlagListResponseSchema:
    """
    Get all site-specific feature flags.
    
    Returns:
        List of site-specific feature flags
    """
    service = get_feature_flag_service()
    
    all_flags = service.get_all_feature_flags()
    site_flags = [flag for flag in all_flags if flag.site is not None]
    
    return FeatureFlagListResponseSchema(
        flags=[_feature_flag_to_response(flag) for flag in site_flags],
        total=len(site_flags)
    )
