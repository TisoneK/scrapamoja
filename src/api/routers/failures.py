"""
Failures / escalation API router.

All routes are mounted under the prefix ``/failures`` in main.py.

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

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.api.database import get_db
from src.api.models import Failure, FailureAlternative
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
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_failure_or_404(db: Session, failure_id: int) -> Failure:
    """Return the Failure row (with alternatives eagerly loaded) or raise 404."""
    stmt = (
        select(Failure)
        .where(Failure.id == failure_id)
        .options(selectinload(Failure.alternatives))
    )
    failure = db.scalars(stmt).first()
    if failure is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failure not found: id={failure_id}",
        )
    return failure


def _alternative_to_schema(alt: FailureAlternative) -> AlternativeSelectorOut:
    """Convert a FailureAlternative ORM row to its Pydantic output schema."""
    blast_radius: Optional[BlastRadiusInfo] = None
    if alt.blast_radius_affected_count is not None:
        affected_sports: list[str] = []
        if alt.blast_radius_affected_sports:
            try:
                affected_sports = json.loads(alt.blast_radius_affected_sports)
            except (json.JSONDecodeError, TypeError):
                affected_sports = []
        blast_radius = BlastRadiusInfo(
            affected_count=alt.blast_radius_affected_count,
            affected_sports=affected_sports,
            severity=alt.blast_radius_severity or "low",
            container_path=alt.blast_radius_container_path or "",
        )

    return AlternativeSelectorOut(
        selector=alt.selector,
        strategy=alt.strategy,
        confidence_score=alt.confidence_score,
        blast_radius=blast_radius,
        highlight_css=alt.highlight_css,
        is_custom=alt.is_custom,
        custom_notes=alt.custom_notes,
    )


def _failure_to_detail(failure: Failure) -> FailureDetailOut:
    """Map a Failure ORM row (with loaded alternatives) to FailureDetailOut."""
    alternatives = [_alternative_to_schema(a) for a in failure.alternatives]
    alternatives.sort(key=lambda a: a.confidence_score, reverse=True)

    return FailureDetailOut(
        failure_id=failure.id,
        selector_id=failure.selector_id,
        failed_selector=failure.failed_selector,
        recipe_id=failure.recipe_id,
        sport=failure.sport,
        site=failure.site,
        timestamp=failure.timestamp,
        error_type=failure.error_type,
        failure_reason=failure.failure_reason,
        severity=failure.severity,
        snapshot_id=failure.snapshot_id,
        alternatives=alternatives,
        flagged=failure.flagged,
        flag_note=failure.flag_note,
        flagged_at=failure.flagged_at,
    )


def _failure_to_list_item(failure: Failure) -> FailureListItem:
    """Map a Failure ORM row to the lightweight list-view schema."""
    alt_count = len(failure.alternatives)
    return FailureListItem(
        failure_id=failure.id,
        selector_id=failure.selector_id,
        failed_selector=failure.failed_selector,
        recipe_id=failure.recipe_id,
        sport=failure.sport,
        site=failure.site,
        timestamp=failure.timestamp,
        error_type=failure.error_type,
        severity=failure.severity,
        has_alternatives=alt_count > 0,
        alternative_count=alt_count,
        flagged=failure.flagged,
        flag_note=failure.flag_note,
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
    severity: Optional[str] = Query(
        None, description="Filter by severity (low|medium|high|critical)"
    ),
    flagged: Optional[bool] = Query(None, description="Filter by flagged state"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=200, description="Rows per page"),
    db: Session = Depends(get_db),
) -> FailureListResponse:
    """
    Return a paginated list of selector failures.

    Failures are returned newest-first.  The ``alternatives`` relationship is
    loaded lazily via a count sub-query to keep the list query fast.
    """
    stmt = (
        select(Failure)
        .options(selectinload(Failure.alternatives))
        .order_by(Failure.timestamp.desc())
    )

    if sport:
        stmt = stmt.where(Failure.sport == sport)
    if site:
        stmt = stmt.where(Failure.site == site)
    if error_type:
        stmt = stmt.where(Failure.error_type == error_type)
    if severity:
        stmt = stmt.where(Failure.severity == severity)
    if flagged is not None:
        stmt = stmt.where(Failure.flagged.is_(flagged))

    # Total count (before pagination)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    offset = (page - 1) * page_size
    failures = db.scalars(stmt.offset(offset).limit(page_size)).all()

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
        data=[_failure_to_list_item(f) for f in failures],
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
def get_failure(
    failure_id: int,
    db: Session = Depends(get_db),
) -> FailureDetailResponse:
    """Return the full failure record including all alternative selectors."""
    failure = _get_failure_or_404(db, failure_id)
    return FailureDetailResponse(data=_failure_to_detail(failure))


@router.post(
    "/{failure_id}/approve",
    response_model=ApprovalResponse,
    summary="Approve an alternative selector",
)
def approve_selector(
    failure_id: int,
    body: ApprovalRequest,
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    """
    Record operator approval of a proposed (or custom) alternative selector.

    In the current implementation this marks the failure as reviewed by
    adding an approved alternative with ``confidence_score = 1.0`` and
    ``is_custom = False`` if the selector is not already present, then
    clears the flagged state.  A future story can wire this to the adaptive
    selector database.
    """
    failure = _get_failure_or_404(db, failure_id)

    # Check whether the selector already exists as an alternative.
    existing = next(
        (a for a in failure.alternatives if a.selector == body.selector), None
    )
    if existing is None:
        # Add it as an approved custom entry so the history is preserved.
        alt = FailureAlternative(
            failure_id=failure.id,
            selector=body.selector,
            strategy="css",
            confidence_score=1.0,
            is_custom=True,
            custom_notes=body.notes,
            created_at=_utcnow(),
        )
        db.add(alt)

    # Clear flag if set.
    failure.flagged = False
    failure.flag_note = None
    failure.flagged_at = None

    db.commit()

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
def reject_selector(
    failure_id: int,
    body: RejectionRequest,
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    """
    Record operator rejection of a proposed alternative selector.

    The rejected selector is removed from the alternatives list so it won't
    appear again in the UI.  If a ``suggested_alternative`` is provided it is
    stored as a new custom alternative with a moderate confidence score.
    """
    failure = _get_failure_or_404(db, failure_id)

    # Remove the rejected alternative if it exists.
    for alt in list(failure.alternatives):
        if alt.selector == body.selector:
            db.delete(alt)
            break

    # Store operator's suggestion as a new custom alternative.
    if body.suggested_alternative:
        suggestion = FailureAlternative(
            failure_id=failure.id,
            selector=body.suggested_alternative,
            strategy="css",
            confidence_score=0.5,
            is_custom=True,
            custom_notes=f"Suggested after rejecting: {body.reason}",
            created_at=_utcnow(),
        )
        db.add(suggestion)

    db.commit()

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
def flag_failure(
    failure_id: int,
    body: FlagRequest,
    db: Session = Depends(get_db),
) -> FlagResponse:
    """Mark a failure as needing developer attention."""
    failure = _get_failure_or_404(db, failure_id)

    now = _utcnow()
    failure.flagged = True
    failure.flag_note = body.note
    failure.flagged_at = now

    db.commit()

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
def unflag_failure(
    failure_id: int,
    db: Session = Depends(get_db),
) -> FlagResponse:
    """Clear the developer-review flag on a failure."""
    failure = _get_failure_or_404(db, failure_id)

    now = _utcnow()
    failure.flagged = False
    previous_note = failure.flag_note or ""
    previous_flagged_at = failure.flagged_at or now
    failure.flag_note = None
    failure.flagged_at = None

    db.commit()

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
    db: Session = Depends(get_db),
) -> CustomSelectorResponse:
    """
    Allow an operator to propose their own selector string as a replacement.

    The new alternative is stored with ``is_custom=True`` and a default
    confidence score of 0.75 so it floats near the top of the list without
    displacing high-confidence machine-generated candidates.
    """
    failure = _get_failure_or_404(db, failure_id)

    now = _utcnow()
    alt = FailureAlternative(
        failure_id=failure.id,
        selector=body.selector_string,
        strategy=body.strategy_type,
        confidence_score=0.75,
        is_custom=True,
        custom_notes=body.notes,
        created_at=now,
    )
    db.add(alt)
    db.commit()
    db.refresh(alt)

    return CustomSelectorResponse(
        success=True,
        message=f"Custom selector added to failure #{failure_id}.",
        failure_id=failure_id,
        selector=alt.selector,
        strategy_type=alt.strategy,
        is_custom=True,
        created_at=now,
    )
