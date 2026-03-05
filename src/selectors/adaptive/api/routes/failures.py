"""
API routes for failure management endpoints.

This module provides REST API endpoints for:
- GET /failures - List selector failures with filtering
- GET /failures/{id} - Get failure details with alternatives
- POST /failures/{id}/approve - Approve proposed selector
- POST /failures/{id}/reject - Reject proposed selector
- POST /failures/{id}/flag - Flag for developer review
- DELETE /failures/{id}/flag - Remove flag

Story: 4.3 - Flag Selectors for Developer Review
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from src.selectors.adaptive.api.schemas.failures import (
    FailureListResponseSchema,
    FailureDetailResponseSchema,
    ApprovalRequestSchema,
    RejectionRequestSchema,
    ApprovalResponseSchema,
    FlagRequestSchema,
    FlagResponseSchema,
    ProblemDetailSchema,
    FailureListItemSchema,
    FailureDetailSchema,
    AlternativeSelectorSchema,
    CustomSelectorRequestSchema,
    CustomSelectorResponseSchema,
)
from src.selectors.adaptive.services.failure_service import FailureService, get_failure_service
from src.selectors.adaptive.services.dom_analyzer import StrategyType


# Create router
router = APIRouter(prefix="/failures", tags=["failures"])


def _create_problem_detail(
    title: str,
    detail: str,
    status_code: int,
) -> ProblemDetailSchema:
    """Create a problem detail response."""
    return ProblemDetailSchema(
        type="about:blank",
        title=title,
        detail=detail,
        status=status_code,
    )


@router.get(
    "",
    response_model=FailureListResponseSchema,
    summary="List selector failures",
    description="Get a paginated list of selector failures with optional filtering",
)
async def list_failures(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    site: Optional[str] = Query(None, description="Filter by site"),
    error_type: Optional[str] = Query(None, description="Filter by error type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    flagged: Optional[bool] = Query(None, description="Filter by flagged status"),
    date_from: Optional[datetime] = Query(None, description="Filter from date (ISO8601)"),
    date_to: Optional[datetime] = Query(None, description="Filter to date (ISO8601)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    service: FailureService = Query(None, description="Failure service dependency"),
) -> FailureListResponseSchema:
    """
    List selector failures with optional filtering and pagination.
    
    Returns a paginated list of failures with summary information.
    """
    # Get service instance
    if service is None:
        service = get_failure_service()
    
    # Build filters dict for response
    filters = {}
    if sport:
        filters["sport"] = sport
    if site:
        filters["site"] = site
    if error_type:
        filters["error_type"] = error_type
    if severity:
        filters["severity"] = severity
    if flagged is not None:
        filters["flagged"] = flagged
    if date_from:
        filters["date_from"] = date_from.isoformat()
    if date_to:
        filters["date_to"] = date_to.isoformat()
    
    # Fetch failures
    failures, total = service.list_failures(
        sport=sport,
        site=site,
        error_type=error_type,
        severity=severity,
        flagged=flagged,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    
    # Build response
    return FailureListResponseSchema(
        data=[FailureListItemSchema(**f) for f in failures],
        total=total,
        page=page,
        page_size=page_size,
        filters=filters,
    )


@router.get(
    "/{failure_id}",
    response_model=FailureDetailResponseSchema,
    summary="Get failure details",
    description="Get detailed information about a specific failure including proposed alternatives",
    responses={
        404: {"model": ProblemDetailSchema, "description": "Failure not found"},
    },
)
async def get_failure_detail(
    failure_id: int,
    include_alternatives: bool = Query(True, description="Include proposed alternatives"),
    service: FailureService = Query(None, description="Failure service dependency"),
) -> FailureDetailResponseSchema:
    """
    Get detailed information about a selector failure.
    
    Returns the failure details including:
    - Failed selector information
    - Error context (sport, site, timestamp)
    - Proposed alternative selectors with confidence scores
    - Snapshot reference for visual preview
    - Flag status (if flagged for developer review)
    """
    # Get service instance
    if service is None:
        service = get_failure_service()
    
    # Fetch failure detail
    detail = service.get_failure_detail(
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
    
    # Build alternatives list
    alternatives = []
    for alt in detail.get("alternatives", []):
        alternatives.append(
            AlternativeSelectorSchema(
                selector=alt.get("selector", ""),
                strategy=alt.get("strategy", "css"),
                confidence_score=alt.get("confidence_score", 0.0),
                blast_radius=alt.get("blast_radius"),
                highlight_css=alt.get("highlight_css"),
                is_custom=alt.get("is_custom", False),
                custom_notes=alt.get("custom_notes"),
            )
        )
    
    # Parse flagged_at datetime if present
    flagged_at = None
    if detail.get("flagged_at"):
        try:
            flagged_at = datetime.fromisoformat(detail["flagged_at"])
        except (ValueError, TypeError):
            pass
    
    # Build response
    failure_detail = FailureDetailSchema(
        failure_id=detail["failure_id"],
        selector_id=detail["selector_id"],
        failed_selector=detail["failed_selector"],
        recipe_id=detail.get("recipe_id"),
        sport=detail.get("sport"),
        site=detail.get("site"),
        timestamp=detail["timestamp"],
        error_type=detail["error_type"],
        failure_reason=detail.get("failure_reason"),
        severity=detail.get("severity", "minor"),
        snapshot_id=detail.get("snapshot_id"),
        alternatives=alternatives,
        flagged=detail.get("flagged", False),
        flag_note=detail.get("flag_note"),
        flagged_at=flagged_at,
    )
    
    return FailureDetailResponseSchema(data=failure_detail)


@router.post(
    "/{failure_id}/approve",
    response_model=ApprovalResponseSchema,
    summary="Approve proposed selector",
    description="Approve an alternative selector for a failed selector",
    responses={
        404: {"model": ProblemDetailSchema, "description": "Failure not found"},
        400: {"model": ProblemDetailSchema, "description": "Invalid request"},
    },
)
async def approve_selector(
    failure_id: int,
    request: ApprovalRequestSchema,
    service: FailureService = Query(None, description="Failure service dependency"),
) -> ApprovalResponseSchema:
    """
    Approve a proposed alternative selector.
    
    This marks the selector as approved and triggers the update
    of the recipe configuration.
    """
    # Get service instance
    if service is None:
        service = get_failure_service()
    
    # Extract user ID from request (for now, use provided user_id or default)
    user_id = getattr(request, 'user_id', None) or (request.notes.get('user_id') if hasattr(request, 'notes') and request.notes else None)
    
    # Approve selector with user context for audit logging
    result = service.approve_alternative(
        failure_id=failure_id,
        selector=request.selector,
        notes=request.notes,
        user_id=user_id,  # Pass user_id for audit logging
    )
    
    if not result["success"]:
        if "not found" in result.get("message", "").lower():
            problem = _create_problem_detail(
                title="Not Found",
                detail=result["message"],
                status_code=404,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=problem.model_dump(),
            )
        else:
            problem = _create_problem_detail(
                title="Bad Request",
                detail=result["message"],
                status_code=400,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=problem.model_dump(),
            )
    
    return ApprovalResponseSchema(
        success=result["success"],
        message=result["message"],
        selector=result["selector"],
        failure_id=result["failure_id"],
        timestamp=datetime.fromisoformat(result["timestamp"]),
    )


@router.post(
    "/{failure_id}/reject",
    response_model=ApprovalResponseSchema,
    summary="Reject proposed selector",
    description="Reject an alternative selector with a reason",
    responses={
        404: {"model": ProblemDetailSchema, "description": "Failure not found"},
        400: {"model": ProblemDetailSchema, "description": "Invalid request"},
    },
)
async def reject_selector(
    failure_id: int,
    request: RejectionRequestSchema,
    service: FailureService = Query(None, description="Failure service dependency"),
) -> ApprovalResponseSchema:
    """
    Reject a proposed alternative selector.
    
    This marks the selector as rejected and records the reason
    for future learning.
    """
    # Get service instance
    if service is None:
        service = get_failure_service()
    
    # Extract user ID from request (for now, use provided user_id or default)
    user_id = getattr(request, 'user_id', None) or (request.notes.get('user_id') if hasattr(request, 'notes') and request.notes else None)
    
    # Reject the selector
    result = service.reject_alternative(
        failure_id=failure_id,
        selector=request.selector,
        reason=request.reason,
        suggested_alternative=request.suggested_alternative,
        user_id=user_id,  # Pass user_id for audit logging
    )
    
    if not result["success"]:
        if "not found" in result.get("message", "").lower():
            problem = _create_problem_detail(
                title="Not Found",
                detail=result["message"],
                status_code=404,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=problem.model_dump(),
            )
        else:
            problem = _create_problem_detail(
                title="Bad Request",
                detail=result["message"],
                status_code=400,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=problem.model_dump(),
            )
    
    return ApprovalResponseSchema(
        success=result["success"],
        message=result["message"],
        selector=result["selector"],
        failure_id=result["failure_id"],
        timestamp=datetime.fromisoformat(result["timestamp"]),
    )


@router.post(
    "/{failure_id}/flag",
    response_model=FlagResponseSchema,
    summary="Flag selector for developer review",
    description="Flag a selector failure for developer review with a note",
    responses={
        404: {"model": ProblemDetailSchema, "description": "Failure not found"},
        400: {"model": ProblemDetailSchema, "description": "Invalid request"},
    },
)
async def flag_failure(
    failure_id: int,
    request: FlagRequestSchema,
    service: FailureService = Query(None, description="Failure service dependency"),
) -> FlagResponseSchema:
    """
    Flag a selector failure for developer review.
    
    This allows operations team members to flag selectors that need
    technical review, with a note explaining what needs to be reviewed.
    """
    # Get service instance
    if service is None:
        service = get_failure_service()
    
    # Extract user ID from request (for now, use provided user_id or default)
    user_id = getattr(request, 'user_id', None) or (request.notes.get('user_id') if hasattr(request, 'notes') and request.notes else None)
    
    # Flag failure with user context for audit logging
    result = service.flag_failure(
        failure_id=failure_id,
        note=request.note,
        user_id=user_id,  # Pass user_id for audit logging
    )
    
    if not result["success"]:
        if "not found" in result.get("message", "").lower():
            problem = _create_problem_detail(
                title="Not Found",
                detail=result["message"],
                status_code=404,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=problem.model_dump(),
            )
        else:
            problem = _create_problem_detail(
                title="Bad Request",
                detail=result["message"],
                status_code=400,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=problem.model_dump(),
            )
    
    return FlagResponseSchema(
        success=result["success"],
        message=result["message"],
        failure_id=result["failure_id"],
        flagged=result["flagged"],
        flag_note=result["flag_note"],
        flagged_at=datetime.fromisoformat(result["flagged_at"]),
    )


@router.delete(
    "/{failure_id}/flag",
    response_model=FlagResponseSchema,
    summary="Remove flag from selector",
    description="Remove the flag from a selector failure",
    responses={
        404: {"model": ProblemDetailSchema, "description": "Failure not found"},
        400: {"model": ProblemDetailSchema, "description": "Invalid request"},
    },
)
async def unflag_failure(
    failure_id: int,
    service: FailureService = Query(None, description="Failure service dependency"),
) -> FlagResponseSchema:
    """
    Remove the flag from a selector failure.
    
    This allows removing the developer review flag once the issue
    has been addressed.
    """
    # Get service instance
    if service is None:
        service = get_failure_service()
    
    # Unflag the failure
    result = service.unflag_failure(
        failure_id=failure_id,
    )
    
    if not result["success"]:
        if "not found" in result.get("message", "").lower():
            problem = _create_problem_detail(
                title="Not Found",
                detail=result["message"],
                status_code=404,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=problem.model_dump(),
            )
        else:
            problem = _create_problem_detail(
                title="Bad Request",
                detail=result["message"],
                status_code=400,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=problem.model_dump(),
            )
    
    return FlagResponseSchema(
        success=result["success"],
        message=result["message"],
        failure_id=result["failure_id"],
        flagged=result["flagged"],
        flag_note="",
        flagged_at=datetime.utcnow(),
    )


@router.post(
    "/{failure_id}/custom-selector",
    response_model=CustomSelectorResponseSchema,
    summary="Create custom selector",
    description="Create a custom selector for a failure as an alternative to auto-proposed selectors",
    responses={
        404: {"model": ProblemDetailSchema, "description": "Failure not found"},
        400: {"model": ProblemDetailSchema, "description": "Invalid request"},
    },
)
async def create_custom_selector(
    failure_id: int,
    request: CustomSelectorRequestSchema,
    service: FailureService = Query(None, description="Failure service dependency"),
) -> CustomSelectorResponseSchema:
    """
    Create a custom selector for a failure.
    
    This allows users to manually create alternative selectors when the
    auto-proposal system cannot handle specific edge cases.
    # Create the custom selector
    result = service.create_custom_selector(
        failure_id=failure_id,
        selector_string=request.selector_string,
        strategy_type=request.strategy_type,
        notes=request.notes,
        user_id=user_id,  # Pass user_id for audit logging
    )
    
    if not result["success"]:
        if "not found" in result.get("message", "").lower():
            problem = _create_problem_detail(
                title="Not Found",
                detail=result["message"],
                status_code=404,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=problem.model_dump(),
            )
        else:
            problem = _create_problem_detail(
                title="Bad Request",
                detail=result["message"],
                status_code=400,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=problem.model_dump(),
            )
    
    return CustomSelectorResponseSchema(
        success=result["success"],
        message=result["message"],
        failure_id=result["failure_id"],
        selector=result["selector"],
        strategy_type=result["strategy_type"],
        is_custom=True,
        created_at=datetime.fromisoformat(result["created_at"]),
    )


# =============================================================================
# Weights endpoints for Learning (Story 5.1)
# =============================================================================


@router.get(
    "/weights",
    response_model=dict,
    summary="Get approval learning weights",
    description="Get current approval weights for all strategy types",
)
async def get_weights(
    service: FailureService = Query(None, description="Failure service dependency"),
) -> dict:
    """
    Get current approval weights for all strategies.
    
    Returns the approval learning weights that have been accumulated
    from human approvals of proposed selectors.
    """
    # Get service instance
    if service is None:
        service = get_failure_service()
    
    # Get weights from confidence scorer
    weights = service.confidence_scorer.get_approval_weights()
    
    return {
        "data": {
            "weights": weights,
            "total_strategies": len(weights),
        }
    }


@router.get(
    "/weights/{strategy}",
    response_model=dict,
    summary="Get approval weight for strategy",
    description="Get approval weight boost for a specific strategy type",
)
async def get_strategy_weight(
    strategy: str,
    service: FailureService = Query(None, description="Failure service dependency"),
) -> dict:
    """
    Get approval weight for a specific strategy.
    
    Returns the boost amount for the specified strategy type.
    """
    # Get service instance
    if service is None:
        service = get_failure_service()
    
    # Get boost for strategy
    from src.selectors.adaptive.services.dom_analyzer import StrategyType
    
    try:
        strategy_type = StrategyType(strategy)
    except ValueError:
        problem = _create_problem_detail(
            title="Invalid Strategy",
            detail=f"Invalid strategy type: {strategy}",
            status_code=400,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=problem.model_dump(),
        )
    
    boost = service.confidence_scorer.get_strategy_boost(strategy_type)
    
    return {
        "data": {
            "strategy": strategy,
            "boost": boost,
        }
    }
