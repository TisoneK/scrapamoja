"""
Blast Radius API endpoints.

This module provides REST API endpoints for:
- GET /api/v1/blast-radius/{selector_id} - Get single selector blast radius
- GET /api/v1/blast-radius?selector_ids=... - Batch query
- GET /api/v1/blast-radius/config - Get blast radius configuration
- GET /api/v1/blast-radius/summary - Get blast radius summary

Story: 6.3 - Blast Radius Calculation
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from src.selectors.adaptive.services.blast_radius_service import (
    get_blast_radius_service,
    BlastRadiusService,
)
from src.selectors.adaptive.api.schemas.blast_radius import (
    BlastRadiusResponse,
    BatchBlastRadiusResponse,
    BlastRadiusConfigResponse,
    BlastRadiusSummary,
    AffectedField,
    CascadingSelector,
)

router = APIRouter(prefix="/api/v1/blast-radius", tags=["blast-radius"])


def _to_response(result) -> BlastRadiusResponse:
    """Convert service result to API response."""
    return BlastRadiusResponse(
        failed_selector=result.failed_selector,
        affected_fields=[
            AffectedField(
                field_name=f.field_name,
                field_type=f.field_type,
                confidence_impact=f.confidence_impact
            )
            for f in result.affected_fields
        ],
        affected_records=result.affected_records,
        severity=result.severity,
        recommended_actions=result.recommended_actions,
        cascading_selectors=[
            CascadingSelector(
                selector_id=c.selector_id,
                dependency_type=c.dependency_type,
                potential_impact=c.potential_impact
            )
            for c in result.cascading_selectors
        ],
        timestamp=result.timestamp,
        confidence_score=result.confidence_score,
        message=result.message,
    )


@router.get(
    "/{selector_id}",
    response_model=BlastRadiusResponse,
    summary="Get blast radius for selector",
    description="Get blast radius calculation for a specific selector by ID",
)
async def get_blast_radius(
    selector_id: str,
    include_cascading: bool = Query(default=True, description="Include cascading selectors"),
    include_recommended_actions: bool = Query(default=True, description="Include recommended actions"),
) -> BlastRadiusResponse:
    """
    Get blast radius for a single selector.
    
    Args:
        selector_id: The selector ID to query
        include_cascading: Whether to include cascading selectors in the response
        include_recommended_actions: Whether to include recommended actions in the response
        
    Returns:
        BlastRadiusResponse with blast radius details
    """
    service = get_blast_radius_service()
    
    try:
        result = service.calculate_blast_radius(
            selector_id=selector_id,
            include_cascading=include_cascading,
            include_recommended_actions=include_recommended_actions,
        )
        return _to_response(result)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to calculate blast radius: {str(e)}"
        )


@router.get(
    "",
    response_model=BatchBlastRadiusResponse,
    summary="Get batch blast radius",
    description="Get blast radius calculations for multiple selectors",
)
async def get_batch_blast_radius(
    selector_ids: str = Query(
        ..., 
        description="Comma-separated list of selector IDs",
        example="home_team,away_team,score"
    ),
    include_cascading: bool = Query(default=True, description="Include cascading selectors"),
    include_recommended_actions: bool = Query(default=True, description="Include recommended actions"),
) -> BatchBlastRadiusResponse:
    """
    Get blast radius for multiple selectors in batch.
    
    Args:
        selector_ids: Comma-separated list of selector IDs
        include_cascading: Whether to include cascading selectors in the response
        include_recommended_actions: Whether to include recommended actions in the response
        
    Returns:
        BatchBlastRadiusResponse with blast radius for each selector
    """
    # Parse selector IDs
    selector_id_list = [s.strip() for s in selector_ids.split(",") if s.strip()]
    
    if not selector_id_list:
        raise HTTPException(
            status_code=400,
            detail="At least one selector_id is required"
        )
    
    if len(selector_id_list) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 selectors allowed per batch query"
        )
    
    service = get_blast_radius_service()
    
    try:
        results = service.calculate_batch_blast_radius(
            selector_ids=selector_id_list,
            include_cascading=include_cascading,
            include_recommended_actions=include_recommended_actions,
        )
        
        # Convert results to response format
        blast_radius_dict = {}
        for selector_id, result in results.items():
            blast_radius_dict[selector_id] = _to_response(result)
        
        from datetime import datetime, timezone
        return BatchBlastRadiusResponse(
            blast_radius=blast_radius_dict,
            total_calculated=len(blast_radius_dict),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to calculate batch blast radius: {str(e)}"
        )


@router.get(
    "/config",
    response_model=BlastRadiusConfigResponse,
    summary="Get blast radius configuration",
    description="Get the current blast radius threshold configuration",
)
async def get_blast_radius_config() -> BlastRadiusConfigResponse:
    """
    Get blast radius threshold configuration.
    
    Returns:
        BlastRadiusConfigResponse with threshold values
    """
    service = get_blast_radius_service()
    config = service.config
    
    return BlastRadiusConfigResponse(
        critical_confidence_threshold=config.critical_confidence_threshold,
        major_confidence_threshold=config.major_confidence_threshold,
        critical_fields=config.critical_fields,
    )


@router.get(
    "/summary",
    response_model=BlastRadiusSummary,
    summary="Get blast radius summary",
    description="Get summary statistics for blast radius across selectors",
)
async def get_blast_radius_summary(
    selector_ids: Optional[str] = Query(
        default=None, 
        description="Comma-separated list of selector IDs (if not provided, uses all failed selectors)",
    ),
) -> BlastRadiusSummary:
    """
    Get blast radius summary for selectors.
    
    Args:
        selector_ids: Optional comma-separated list of selector IDs
        
    Returns:
        BlastRadiusSummary with aggregate statistics
    """
    service = get_blast_radius_service()
    
    # If no selectors provided, try to get all unique selectors
    if selector_ids:
        selector_id_list = [s.strip() for s in selector_ids.split(",") if s.strip()]
    else:
        try:
            from src.selectors.adaptive.db.repositories.failure_event_repository import FailureEventRepository
            repo = FailureEventRepository()
            selector_id_list = repo.get_unique_selectors()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get selectors: {str(e)}"
            )
    
    if not selector_id_list:
        # Return empty summary
        return BlastRadiusSummary(
            total_affected_records=0,
            critical_count=0,
            major_count=0,
            minor_count=0,
            selectors_analyzed=0,
        )
    
    try:
        summary = service.get_blast_radius_summary(selector_id_list)
        
        return BlastRadiusSummary(
            total_affected_records=summary["total_affected_records"],
            critical_count=summary["critical_count"],
            major_count=summary["major_count"],
            minor_count=summary["minor_count"],
            selectors_analyzed=summary["selectors_analyzed"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to calculate blast radius summary: {str(e)}"
        )
