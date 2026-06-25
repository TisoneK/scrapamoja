"""
Health Status Display API endpoints.

This module provides REST API endpoints for:
- GET /api/v1/health - Get all selectors grouped by health status
- GET /api/v1/health/{selector_id} - Get single selector health
- GET /api/v1/health/config - Get health threshold configuration

Story: 6.2 - Selector Health Status Display
"""

from fastapi import APIRouter, HTTPException

from src.selectors.adaptive.services.health_status_service import (
    get_health_status_service,
    SelectorHealthInfo,
    HealthDashboardData,
)
from src.selectors.adaptive.api.schemas.health import (
    SelectorHealthResponse,
    SingleSelectorHealthResponse,
    HealthDashboardResponse,
    HealthStatusConfigResponse,
)

router = APIRouter(prefix="/api/v1/health", tags=["health"])


def _to_response(health_info: SelectorHealthInfo) -> SelectorHealthResponse:
    """Convert service result to API response."""
    return SelectorHealthResponse(
        selector_id=health_info.selector_id,
        status=health_info.status,
        confidence_score=health_info.confidence_score,
        last_failure=health_info.last_failure,
        recommended_action=health_info.recommended_action,
        alternatives=health_info.alternatives,
    )


def _to_dashboard_response(dashboard: HealthDashboardData) -> HealthDashboardResponse:
    """Convert dashboard data to API response."""
    return HealthDashboardResponse(
        healthy=[_to_response(h) for h in dashboard.healthy],
        degraded=[_to_response(h) for h in dashboard.degraded],
        failed=[_to_response(h) for h in dashboard.failed],
        total=dashboard.total,
        last_updated=dashboard.last_updated,
    )


@router.get(
    "",
    response_model=HealthDashboardResponse,
    summary="Get health dashboard",
    description="Get all selectors grouped by health status (healthy, degraded, failed)",
)
async def get_health_dashboard() -> HealthDashboardResponse:
    """
    Get health dashboard with all selectors grouped by status.
    
    Returns:
        HealthDashboardResponse with selectors grouped by health status
    """
    service = get_health_status_service()
    
    try:
        dashboard = service.get_dashboard()
        return _to_dashboard_response(dashboard)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get health dashboard: {str(e)}"
        )


@router.get(
    "/{selector_id}",
    response_model=SingleSelectorHealthResponse,
    summary="Get single selector health",
    description="Get health status for a specific selector by ID",
)
async def get_selector_health(
    selector_id: str,
) -> SingleSelectorHealthResponse:
    """
    Get health status for a single selector.
    
    Args:
        selector_id: The selector ID to query
        
    Returns:
        SingleSelectorHealthResponse with health details
    """
    service = get_health_status_service()
    
    try:
        health_info = service.get_selector_health(selector_id)
        
        return SingleSelectorHealthResponse(
            selector_id=health_info.selector_id,
            status=health_info.status,
            confidence_score=health_info.confidence_score,
            last_failure=health_info.last_failure,
            recommended_action=health_info.recommended_action,
            alternatives=health_info.alternatives,
            history_summary=None,  # Optional: later
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get selector health: {str(e)}"
        )


@router.get(
    "/config/thresholds",
    response_model=HealthStatusConfigResponse,
    summary="Get health threshold configuration",
    description="Get the current health status threshold configuration",
)
async def get_health_config() -> HealthStatusConfigResponse:
    """
    Get health threshold configuration.
    
    Returns:
        HealthStatusConfigResponse with threshold values
    """
    service = get_health_status_service()
    config = service.config
    
    return HealthStatusConfigResponse(
        healthy_threshold=config.healthy_threshold,
        degraded_threshold=config.degraded_threshold,
        failed_threshold=config.failed_threshold,
    )
