"""
Feature-flags API router.

All routes are mounted under the prefix ``/feature-flags`` in main.py.

Route ordering matters: static path segments (``/check``, ``/stats``, etc.)
are declared *before* the ``/{sport}`` path-parameter routes so FastAPI does
not mistakenly capture them as a sport name.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.models import AuditLog, FeatureFlag
from src.api.schemas import (
    AuditLogResponse,
    EnabledSportsResponse,
    FeatureFlagCheckResponse,
    FeatureFlagCreateRequest,
    FeatureFlagListResponse,
    FeatureFlagOut,
    FeatureFlagStatsResponse,
    FeatureFlagUpdateRequest,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_flag_or_404(db: Session, sport: str, site: Optional[str]) -> FeatureFlag:
    """Return the flag or raise HTTP 404."""
    stmt = select(FeatureFlag).where(FeatureFlag.sport == sport)
    if site is None:
        stmt = stmt.where(FeatureFlag.site.is_(None))
    else:
        stmt = stmt.where(FeatureFlag.site == site)
    flag = db.scalars(stmt).first()
    if flag is None:
        detail = f"Feature flag not found: sport={sport!r}" + (
            f", site={site!r}" if site else " (global)"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return flag


def _write_audit(
    db: Session,
    flag: FeatureFlag,
    action: str,
    old_value: Optional[bool],
    new_value: Optional[bool],
    description: Optional[str] = None,
    user: str = "system",
) -> None:
    """Append one row to the audit log (called inside the same transaction)."""
    entry = AuditLog(
        flag_id=flag.id,
        sport=flag.sport,
        site=flag.site,
        action=action,
        old_value=old_value,
        new_value=new_value,
        user=user,
        description=description,
        timestamp=_utcnow(),
    )
    db.add(entry)


# ===========================================================================
# Static routes  (must come before /{sport} to avoid path-param capture)
# ===========================================================================


@router.get(
    "",
    response_model=FeatureFlagListResponse,
    summary="List feature flags",
)
def list_feature_flags(
    sport: Optional[str] = Query(None, description="Filter by sport name"),
    site: Optional[str] = Query(None, description="Filter by site name"),
    db: Session = Depends(get_db),
) -> FeatureFlagListResponse:
    """Return all feature flags, optionally filtered by sport and/or site."""
    stmt = select(FeatureFlag).order_by(FeatureFlag.updated_at.desc())
    if sport:
        stmt = stmt.where(FeatureFlag.sport.ilike(f"%{sport}%"))
    if site:
        stmt = stmt.where(FeatureFlag.site.ilike(f"%{site}%"))

    flags = db.scalars(stmt).all()
    return FeatureFlagListResponse(
        data=[FeatureFlagOut.model_validate(f) for f in flags],
        count=len(flags),
    )


@router.post(
    "",
    response_model=FeatureFlagOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a feature flag",
)
def create_feature_flag(
    body: FeatureFlagCreateRequest,
    db: Session = Depends(get_db),
) -> FeatureFlagOut:
    """Create a new feature flag.  Raises 409 if (sport, site) already exists."""
    existing_stmt = select(FeatureFlag).where(FeatureFlag.sport == body.sport)
    if body.site is None:
        existing_stmt = existing_stmt.where(FeatureFlag.site.is_(None))
    else:
        existing_stmt = existing_stmt.where(FeatureFlag.site == body.site)

    if db.scalars(existing_stmt).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Feature flag already exists: sport={body.sport!r}"
                + (f", site={body.site!r}" if body.site else " (global)")
            ),
        )

    now = _utcnow()
    flag = FeatureFlag(
        sport=body.sport,
        site=body.site,
        enabled=body.enabled,
        description=body.description,
        created_at=now,
        updated_at=now,
    )
    db.add(flag)
    db.flush()  # populate flag.id before writing audit entry

    _write_audit(
        db,
        flag,
        action="create",
        old_value=None,
        new_value=body.enabled,
        description=(
            body.description
            or f"Created {'site-specific' if body.site else 'global'} flag "
            f"for {body.sport!r}"
            + (f" on {body.site!r}" if body.site else "")
        ),
    )

    db.commit()
    db.refresh(flag)
    return FeatureFlagOut.model_validate(flag)


@router.get(
    "/check",
    response_model=FeatureFlagCheckResponse,
    summary="Check whether a feature flag is enabled",
)
def check_feature_flag(
    sport: str = Query(..., description="Sport to check"),
    site: Optional[str] = Query(None, description="Site to check (omit for global)"),
    db: Session = Depends(get_db),
) -> FeatureFlagCheckResponse:
    """
    Resolve the effective enabled state for (sport, site).

    Lookup order:
    1. Site-specific flag  (sport + site)
    2. Global flag         (sport, site IS NULL)
    3. Default: disabled (flag_exists=False)
    """
    # Site-specific lookup
    if site:
        site_stmt = (
            select(FeatureFlag)
            .where(FeatureFlag.sport == sport)
            .where(FeatureFlag.site == site)
        )
        site_flag = db.scalars(site_stmt).first()
        if site_flag is not None:
            return FeatureFlagCheckResponse(
                sport=sport,
                site=site,
                enabled=site_flag.enabled,
                flag_exists=True,
            )

    # Global fallback
    global_stmt = (
        select(FeatureFlag)
        .where(FeatureFlag.sport == sport)
        .where(FeatureFlag.site.is_(None))
    )
    global_flag = db.scalars(global_stmt).first()
    if global_flag is not None:
        return FeatureFlagCheckResponse(
            sport=sport,
            site=site,
            enabled=global_flag.enabled,
            flag_exists=True,
        )

    # Not found → disabled by default
    return FeatureFlagCheckResponse(
        sport=sport,
        site=site,
        enabled=False,
        flag_exists=False,
    )


@router.get(
    "/enabled-sports",
    response_model=EnabledSportsResponse,
    summary="List sports with at least one enabled flag",
)
def get_enabled_sports(db: Session = Depends(get_db)) -> EnabledSportsResponse:
    stmt = (
        select(FeatureFlag.sport)
        .where(FeatureFlag.enabled.is_(True))
        .distinct()
        .order_by(FeatureFlag.sport)
    )
    sports = list(db.scalars(stmt).all())
    return EnabledSportsResponse(sports=sports, count=len(sports))


@router.get(
    "/stats",
    response_model=FeatureFlagStatsResponse,
    summary="Aggregate feature-flag statistics",
)
def get_feature_flag_stats(db: Session = Depends(get_db)) -> FeatureFlagStatsResponse:
    total = db.scalar(select(func.count()).select_from(FeatureFlag)) or 0
    enabled = (
        db.scalar(
            select(func.count())
            .select_from(FeatureFlag)
            .where(FeatureFlag.enabled.is_(True))
        )
        or 0
    )
    global_count = (
        db.scalar(
            select(func.count())
            .select_from(FeatureFlag)
            .where(FeatureFlag.site.is_(None))
        )
        or 0
    )
    site_specific = (
        db.scalar(
            select(func.count())
            .select_from(FeatureFlag)
            .where(FeatureFlag.site.isnot(None))
        )
        or 0
    )
    unique_sports = (
        db.scalar(
            select(func.count(FeatureFlag.sport.distinct())).select_from(FeatureFlag)
        )
        or 0
    )

    return FeatureFlagStatsResponse(
        total_flags=total,
        enabled_flags=enabled,
        disabled_flags=total - enabled,
        global_flags=global_count,
        site_specific_flags=site_specific,
        unique_sports=unique_sports,
    )


@router.get(
    "/sites",
    response_model=FeatureFlagListResponse,
    summary="List all site-specific flags",
)
def get_site_flags(db: Session = Depends(get_db)) -> FeatureFlagListResponse:
    stmt = (
        select(FeatureFlag)
        .where(FeatureFlag.site.isnot(None))
        .order_by(FeatureFlag.sport, FeatureFlag.site)
    )
    flags = db.scalars(stmt).all()
    return FeatureFlagListResponse(
        data=[FeatureFlagOut.model_validate(f) for f in flags],
        count=len(flags),
    )


@router.get(
    "/audit-log",
    response_model=AuditLogResponse,
    summary="Retrieve audit log entries",
)
def get_audit_log(
    sport: Optional[str] = Query(None),
    site: Optional[str] = Query(None),
    action: Optional[str] = Query(
        None, description="create | update | toggle | delete"
    ),
    user: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> AuditLogResponse:
    """Return paginated audit-log entries, newest first."""
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())

    if sport:
        stmt = stmt.where(AuditLog.sport.ilike(f"%{sport}%"))
    if site:
        stmt = stmt.where(AuditLog.site.ilike(f"%{site}%"))
    if action and action != "all":
        stmt = stmt.where(AuditLog.action == action)
    if user:
        stmt = stmt.where(AuditLog.user.ilike(f"%{user}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    entries = db.scalars(stmt.offset(offset).limit(limit)).all()

    page_size = limit
    page = (offset // page_size) + 1 if page_size else 1
    total_pages = max(1, math.ceil(total / page_size)) if page_size else 1

    from src.api.schemas import AuditLogEntryOut  # local import avoids circular

    return AuditLogResponse(
        data=[AuditLogEntryOut.model_validate(e) for e in entries],
        count=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_more=(offset + page_size) < total,
    )


# ===========================================================================
# Sport-scoped routes  /{sport}  and  /{sport}/sites/{site}
# ===========================================================================


@router.get(
    "/{sport}",
    response_model=FeatureFlagListResponse,
    summary="Get all flags for a sport",
)
def get_sport_flags(
    sport: str,
    db: Session = Depends(get_db),
) -> FeatureFlagListResponse:
    stmt = (
        select(FeatureFlag)
        .where(FeatureFlag.sport == sport)
        .order_by(FeatureFlag.site.nullsfirst())
    )
    flags = db.scalars(stmt).all()
    return FeatureFlagListResponse(
        data=[FeatureFlagOut.model_validate(f) for f in flags],
        count=len(flags),
    )


@router.patch(
    "/{sport}",
    response_model=FeatureFlagOut,
    summary="Update / toggle a sport's global flag",
)
def update_sport_flag(
    sport: str,
    body: FeatureFlagUpdateRequest,
    db: Session = Depends(get_db),
) -> FeatureFlagOut:
    flag = _get_flag_or_404(db, sport, site=None)
    old_enabled = flag.enabled
    flag.enabled = body.enabled
    if body.description is not None:
        flag.description = body.description
    flag.updated_at = _utcnow()

    action = "toggle" if old_enabled != body.enabled else "update"
    _write_audit(
        db,
        flag,
        action=action,
        old_value=old_enabled,
        new_value=body.enabled,
        description=(
            f"{'Enabled' if body.enabled else 'Disabled'} global flag for {sport!r}"
            if action == "toggle"
            else f"Updated global flag for {sport!r}"
        ),
    )
    db.commit()
    db.refresh(flag)
    return FeatureFlagOut.model_validate(flag)


@router.delete(
    "/{sport}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a sport's global flag",
)
def delete_sport_flag(
    sport: str,
    db: Session = Depends(get_db),
) -> None:
    flag = _get_flag_or_404(db, sport, site=None)
    _write_audit(
        db,
        flag,
        action="delete",
        old_value=flag.enabled,
        new_value=None,
        description=f"Deleted global flag for {sport!r}",
    )
    db.delete(flag)
    db.commit()


@router.get(
    "/{sport}/sites/{site}",
    response_model=FeatureFlagOut,
    summary="Get a site-specific flag",
)
def get_site_flag(
    sport: str,
    site: str,
    db: Session = Depends(get_db),
) -> FeatureFlagOut:
    flag = _get_flag_or_404(db, sport, site=site)
    return FeatureFlagOut.model_validate(flag)


@router.patch(
    "/{sport}/sites/{site}",
    response_model=FeatureFlagOut,
    summary="Update / toggle a site-specific flag",
)
def update_site_flag(
    sport: str,
    site: str,
    body: FeatureFlagUpdateRequest,
    db: Session = Depends(get_db),
) -> FeatureFlagOut:
    flag = _get_flag_or_404(db, sport, site=site)
    old_enabled = flag.enabled
    flag.enabled = body.enabled
    if body.description is not None:
        flag.description = body.description
    flag.updated_at = _utcnow()

    action = "toggle" if old_enabled != body.enabled else "update"
    _write_audit(
        db,
        flag,
        action=action,
        old_value=old_enabled,
        new_value=body.enabled,
        description=(
            f"{'Enabled' if body.enabled else 'Disabled'} {sport!r} flag on {site!r}"
            if action == "toggle"
            else f"Updated {sport!r} flag on {site!r}"
        ),
    )
    db.commit()
    db.refresh(flag)
    return FeatureFlagOut.model_validate(flag)


@router.delete(
    "/{sport}/sites/{site}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a site-specific flag",
)
def delete_site_flag(
    sport: str,
    site: str,
    db: Session = Depends(get_db),
) -> None:
    flag = _get_flag_or_404(db, sport, site=site)
    _write_audit(
        db,
        flag,
        action="delete",
        old_value=flag.enabled,
        new_value=None,
        description=f"Deleted {sport!r} flag on {site!r}",
    )
    db.delete(flag)
    db.commit()
