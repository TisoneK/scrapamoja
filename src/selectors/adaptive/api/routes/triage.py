"""
API routes for fast triage operations.

Provides optimized endpoints for quick failure triage:
- GET /triage/failures - Optimized failure listing with cursor pagination
- POST /triage/failures/{id}/quick-approve - One-click approval
- POST /triage/bulk-approve - Bulk approve multiple failures
- POST /triage/bulk-reject - Bulk reject multiple failures
- POST /triage/escalate - Quick escalation workflow
- GET /triage/performance - Performance metrics

Story: 7.3 - Fast Triage Workflow
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status

from src.selectors.adaptive.api.schemas.triage import (
    FastTriageListResponseSchema,
    QuickApproveRequestSchema,
    QuickApproveResponseSchema,
    BulkActionRequestSchema,
    BulkActionResponseSchema,
    EscalateRequestSchema,
    EscalateResponseSchema,
    PerformanceSummaryResponseSchema,
    TriageSummarySchema,
    FailureCountsSchema,
    PerformanceMetricsSchema,
    BulkPerformanceSchema,
)


# Create router
router = APIRouter(prefix="/triage", tags=["triage"])


def _create_error_response(
    title: str,
    detail: str,
    status_code: int,
) -> dict:
    """Create an error response."""
    return {
        "type": "about:blank",
        "title": title,
        "detail": detail,
        "status": status_code,
    }


@router.get(
    "/failures",
    response_model=FastTriageListResponseSchema,
    summary="Get failures for fast triage",
    description="Optimized failure listing with cursor-based pagination for quick initial loads",
)
async def get_failures_fast(
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    cursor: Optional[int] = Query(None, description="Cursor for pagination"),
    sport: Optional[str] = Query(None, description="Filter by sport"),
    site: Optional[str] = Query(None, description="Filter by site"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    sort_by: str = Query("severity", description="Sort by: severity, timestamp"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
):
    """
    Get failures with optimized loading for fast triage.
    
    Uses cursor-based pagination and minimal field loading for
    quick initial page loads under 2 seconds.
    """
    # Import here to avoid circular imports
    from src.selectors.adaptive.services.fast_triage_service import get_fast_triage_service
    
    service = get_fast_triage_service()
    
    result = service.get_failures_fast(
        limit=limit,
        cursor=cursor,
        sport=sport,
        site=site,
        severity=severity,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    # Build response
    return FastTriageListResponseSchema(
        failures=[TriageSummarySchema(**f) for f in result["failures"]],
        next_cursor=result.get("next_cursor"),
        counts=FailureCountsSchema(**result["counts"]),
        performance=PerformanceMetricsSchema(**result["performance"]),
    )


@router.post(
    "/failures/{failure_id}/quick-approve",
    response_model=QuickApproveResponseSchema,
    summary="One-click approval",
    description="Quickly approve the highest confidence selector for a failure",
)
async def quick_approve(
    failure_id: int,
    request: QuickApproveRequestSchema,
):
    """
    One-click approval using highest confidence selector.
    
    Automatically selects and approves the selector with the
    highest confidence score.
    """
    from src.selectors.adaptive.services.fast_triage_service import get_fast_triage_service
    
    service = get_fast_triage_service()
    
    result = service.quick_approve(
        failure_id=failure_id,
        user_id=request.user_id,
    )
    
    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_create_error_response(
                title="Approval Failed",
                detail=result.get("message", "Could not approve selector"),
                status_code=400,
            ),
        )
    
    return QuickApproveResponseSchema(
        success=result["success"],
        message=result.get("message", ""),
        failure_id=result["failure_id"],
        selector=result.get("selector", ""),
        confidence=result.get("confidence", 0.0),
        performance=PerformanceMetricsSchema(**result["performance"]),
    )


@router.post(
    "/bulk-approve",
    response_model=BulkActionResponseSchema,
    summary="Bulk approve failures",
    description="Approve multiple failures at once with automatic selector selection",
)
async def bulk_approve(
    request: BulkActionRequestSchema,
):
    """
    Bulk approve multiple failures.
    
    Uses the specified strategy to select the best selector
    for each failure and approves them all at once.
    """
    from src.selectors.adaptive.services.fast_triage_service import get_fast_triage_service
    
    service = get_fast_triage_service()
    
    result = service.bulk_approve(
        failure_ids=request.failure_ids,
        strategy=request.strategy,
        user_id=request.user_id,
    )
    
    return BulkActionResponseSchema(
        success=result["success"],
        operation_id=result["operation_id"],
        total=result["total"],
        success_count=result["success_count"],
        failure_count=result["failure_count"],
        results=result["results"],
        performance=BulkPerformanceSchema(**result["performance"]),
    )


@router.post(
    "/bulk-reject",
    response_model=BulkActionResponseSchema,
    summary="Bulk reject failures",
    description="Reject multiple failures at once",
)
async def bulk_reject(
    request: BulkActionRequestSchema,
):
    """
    Bulk reject multiple failures.
    
    Rejects all specified failures with the provided reason.
    """
    from src.selectors.adaptive.services.fast_triage_service import get_fast_triage_service
    
    service = get_fast_triage_service()
    
    result = service.bulk_reject(
        failure_ids=request.failure_ids,
        reason=request.reason,
        user_id=request.user_id,
    )
    
    return BulkActionResponseSchema(
        success=result["success"],
        operation_id=result["operation_id"],
        total=result["total"],
        success_count=result["success_count"],
        failure_count=result["failure_count"],
        results=result["results"],
        performance=BulkPerformanceSchema(**result["performance"]),
    )


@router.post(
    "/escalate",
    response_model=EscalateResponseSchema,
    summary="Quick escalation",
    description="Flag multiple failures for developer review in one action",
)
async def quick_escalate(
    request: EscalateRequestSchema,
):
    """
    Quick escalation workflow.
    
    Flags multiple failures for developer review,
    suitable for complex cases that can't be quickly resolved.
    """
    from src.selectors.adaptive.services.fast_triage_service import get_fast_triage_service
    
    service = get_fast_triage_service()
    
    result = service.quick_escalate(
        failure_ids=request.failure_ids,
        reason=request.reason,
        user_id=request.user_id,
    )
    
    return EscalateResponseSchema(
        success=result["success"],
        operation_id=result["operation_id"],
        total=result["total"],
        success_count=result["success_count"],
        failure_count=result["failure_count"],
        results=result["results"],
        performance=BulkPerformanceSchema(**result["performance"]),
    )


@router.get(
    "/performance",
    response_model=PerformanceSummaryResponseSchema,
    summary="Get performance metrics",
    description="Retrieve performance metrics for triage operations",
)
async def get_performance(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
):
    """
    Get performance metrics summary.
    
    Returns average response times and target achievement
    for triage operations over the specified time period.
    """
    from src.selectors.adaptive.services.fast_triage_service import get_fast_triage_service
    
    service = get_fast_triage_service()
    
    result = service.get_performance_summary(hours=hours)
    
    return PerformanceSummaryResponseSchema(**result)
