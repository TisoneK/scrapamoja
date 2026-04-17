"""
Failures / escalation API router.

All routes are mounted under the prefix ``/failures`` in main.py.

Delegates entirely to the adaptive module's FailureService, which owns
the real persistent database at data/adaptive.db and receives live failure
events from the scraper via the in-process event bus.

Endpoints
---------
GET    /failures                          – paginated list with filters
GET    /failures/{id}                     – full detail with alternatives
POST   /failures/{id}/approve             – approve an alternative selector
POST   /failures/{id}/reject              – reject an alternative selector
POST   /failures/{id}/flag                – flag for developer review
DELETE /failures/{id}/flag                – remove flag
POST   /failures/{id}/custom-selector     – submit a custom replacement
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.schemas import (
    AlternativeSelectorOut,
    ApprovalRequest,
    ApprovalResponse,
    BlastRadiusInfo,
    CustomSelectorRequest,
    CustomSelectorResponse,
    FailureDetailOut,
    FailureDetailResponse,
    FailureListItem,
    FailureListResponse,
    FlagRequest,
    FlagResponse,
    RejectionRequest,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_path() -> str:
    """
    Resolve the shared adaptive database path.

    Respects ``ADAPTIVE_DB_PATH`` so tests and CI can override it.
    Falls back to ``<project-root>/data/adaptive.db``.
    """
    env = os.environ.get("ADAPTIVE_DB_PATH")
    if env:
        return env
    project_root = Path(__file__).resolve().parents[3]  # src/api/routers/ → root
    db_dir = project_root / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "adaptive.db")


def _get_failure_service():
    """Return a FailureService wired to the shared DB path."""
    from src.selectors.adaptive.services.failure_service import FailureService

    return FailureService(db_path=_db_path())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _map_alternative(alt_dict: dict) -> AlternativeSelectorOut:
    """Convert an alternative dict from FailureService to the output schema."""
    blast_radius: Optional[BlastRadiusInfo] = None
    br = alt_dict.get("blast_radius")
    if br:
        blast_radius = BlastRadiusInfo(
            affected_count=br.get("affected_count", 0),
            affected_sports=br.get("affected_sports", []),
            severity=br.get("severity", "low"),
            container_path=br.get("container_path", ""),
        )

    return AlternativeSelectorOut(
        selector=alt_dict.get("selector", ""),
        strategy=alt_dict.get("strategy", "css"),
        confidence_score=float(alt_dict.get("confidence_score", 0.0)),
        blast_radius=blast_radius,
        highlight_css=alt_dict.get("highlight_css"),
        is_custom=bool(alt_dict.get("is_custom", False)),
        custom_notes=alt_dict.get("custom_notes"),
    )


def _parse_timestamp(value) -> datetime:
    """Coerce a timestamp value (str, datetime, or None) to datetime."""
    if value is None:
        return _utcnow()
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return _utcnow()


def _dict_to_list_item(d: dict) -> FailureListItem:
    return FailureListItem(
        failure_id=d["failure_id"],
        selector_id=d["selector_id"],
        failed_selector=d.get("failed_selector", d["selector_id"]),
        recipe_id=d.get("recipe_id"),
        sport=d.get("sport"),
        site=d.get("site"),
        timestamp=_parse_timestamp(d.get("timestamp")),
        error_type=d.get("error_type", "exception"),
        severity=d.get("severity", "minor"),
        has_alternatives=bool(d.get("has_alternatives", False)),
        alternative_count=int(d.get("alternative_count", 0)),
        flagged=bool(d.get("flagged", False)),
        flag_note=d.get("flag_note"),
    )


def _dict_to_detail(d: dict) -> FailureDetailOut:
    alts = [_map_alternative(a) for a in d.get("alternatives", [])]
    alts.sort(key=lambda a: a.confidence_score, reverse=True)

    return FailureDetailOut(
        failure_id=d["failure_id"],
        selector_id=d["selector_id"],
        failed_selector=d.get("failed_selector", d["selector_id"]),
        recipe_id=d.get("recipe_id"),
        sport=d.get("sport"),
        site=d.get("site"),
        timestamp=_parse_timestamp(d.get("timestamp")),
        error_type=d.get("error_type", "exception"),
        failure_reason=d.get("failure_reason"),
        severity=d.get("severity", "minor"),
        snapshot_id=d.get("snapshot_id"),
        alternatives=alts,
        flagged=bool(d.get("flagged", False)),
        flag_note=d.get("flag_note"),
        flagged_at=_parse_timestamp(d.get("flagged_at"))
        if d.get("flagged_at")
        else None,
    )


# ===========================================================================
# Routes
# ===========================================================================


@router.get(
    "",
    response_model=FailureListResponse,
    summary="List selector failures",
)
def list_failures(
    sport: Optional[str] = Query(None, description="Filter by sport"),
    site: Optional[str] = Query(None, description="Filter by site"),
    error_type: Optional[str] = Query(None, description="Filter by error type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    flagged: Optional[bool] = Query(None, description="Filter by flagged state"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=200, description="Rows per page"),
) -> FailureListResponse:
    """Return a paginated list of selector failures, newest first."""
    svc = _get_failure_service()

    results, total = svc.list_failures(
        sport=sport,
        site=site,
        error_type=error_type,
        severity=severity,
        flagged=flagged,
        page=page,
        page_size=page_size,
    )

    active_filters: dict = {}
    if sport:
        active_filters["sport"] = sport
    if site:
        active_filters["site"] = site
    if error_type:
        active_filters["error_type"] = error_type
    if severity:
        active_filters["severity"] = severity
    if flagged is not None:
        active_filters["flagged"] = flagged

    return FailureListResponse(
        data=[_dict_to_list_item(r) for r in results],
        total=total,
        page=page,
        page_size=page_size,
        filters=active_filters,
    )


@router.get(
    "/{failure_id}",
    response_model=FailureDetailResponse,
    summary="Get full failure detail",
)
def get_failure(failure_id: int) -> FailureDetailResponse:
    """Return the full failure record including alternative selectors."""
    svc = _get_failure_service()
    detail = svc.get_failure_detail(failure_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failure not found: id={failure_id}",
        )
    return FailureDetailResponse(data=_dict_to_detail(detail))


@router.post(
    "/{failure_id}/approve",
    response_model=ApprovalResponse,
    summary="Approve an alternative selector",
)
async def approve_selector(failure_id: int, body: ApprovalRequest) -> ApprovalResponse:
    """Record operator approval of a proposed alternative selector."""
    svc = _get_failure_service()

    # Verify the failure exists first
    if svc.get_failure_detail(failure_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failure not found: id={failure_id}",
        )

    try:
        await svc.approve_alternative(
            failure_id=failure_id,
            selector=body.selector,
            notes=body.notes,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return ApprovalResponse(
        success=True,
        message=f"Selector approved for failure #{failure_id}.",
        selector=body.selector,
        failure_id=failure_id,
        timestamp=_utcnow(),
    )


@router.post(
    "/{failure_id}/reject",
    response_model=ApprovalResponse,
    summary="Reject an alternative selector",
)
async def reject_selector(failure_id: int, body: RejectionRequest) -> ApprovalResponse:
    """Record operator rejection of a proposed alternative selector."""
    svc = _get_failure_service()

    if svc.get_failure_detail(failure_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failure not found: id={failure_id}",
        )

    try:
        await svc.reject_alternative(
            failure_id=failure_id,
            selector=body.selector,
            reason=body.reason,
            suggested_alternative=body.suggested_alternative,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return ApprovalResponse(
        success=True,
        message=f"Selector rejected for failure #{failure_id}. Reason: {body.reason}",
        selector=body.selector,
        failure_id=failure_id,
        timestamp=_utcnow(),
    )


@router.post(
    "/{failure_id}/flag",
    response_model=FlagResponse,
    summary="Flag a failure for developer review",
)
def flag_failure(failure_id: int, body: FlagRequest) -> FlagResponse:
    """Mark a failure as needing developer attention."""
    svc = _get_failure_service()

    if svc.get_failure_detail(failure_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failure not found: id={failure_id}",
        )

    result = svc.flag_failure(failure_id=failure_id, note=body.note)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to flag failure.",
        )

    now = _utcnow()
    return FlagResponse(
        success=True,
        message=f"Failure #{failure_id} flagged for review.",
        failure_id=failure_id,
        flagged=True,
        flag_note=body.note,
        flagged_at=now,
    )


@router.delete(
    "/{failure_id}/flag",
    response_model=FlagResponse,
    summary="Remove flag from a failure",
)
def unflag_failure(failure_id: int) -> FlagResponse:
    """Clear the developer-review flag on a failure."""
    svc = _get_failure_service()

    detail = svc.get_failure_detail(failure_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failure not found: id={failure_id}",
        )

    previous_note = detail.get("flag_note") or ""
    previous_flagged_at = (
        _parse_timestamp(detail.get("flagged_at"))
        if detail.get("flagged_at")
        else _utcnow()
    )

    result = svc.unflag_failure(failure_id=failure_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unflag failure.",
        )

    return FlagResponse(
        success=True,
        message=f"Flag removed from failure #{failure_id}.",
        failure_id=failure_id,
        flagged=False,
        flag_note=previous_note,
        flagged_at=previous_flagged_at,
    )


@router.post(
    "/{failure_id}/custom-selector",
    response_model=CustomSelectorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a custom replacement selector",
)
def create_custom_selector(
    failure_id: int,
    body: CustomSelectorRequest,
) -> CustomSelectorResponse:
    """Allow an operator to propose their own selector string as a replacement."""
    svc = _get_failure_service()

    if svc.get_failure_detail(failure_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failure not found: id={failure_id}",
        )

    try:
        from src.selectors.adaptive.services.dom_analyzer import StrategyType

        strategy = StrategyType(body.strategy_type)
    except (ValueError, ImportError):
        strategy = body.strategy_type  # pass through as string if enum unavailable

    result = svc.create_custom_selector(
        failure_id=failure_id,
        selector_string=body.selector_string,
        strategy_type=strategy,
        notes=body.notes,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create custom selector.",
        )

    now = _utcnow()
    selector_str = (
        result.get("selector", body.selector_string)
        if isinstance(result, dict)
        else body.selector_string
    )

    return CustomSelectorResponse(
        success=True,
        message=f"Custom selector added to failure #{failure_id}.",
        failure_id=failure_id,
        selector=selector_str,
        strategy_type=body.strategy_type,
        is_custom=True,
        created_at=now,
    )
