"""
Feature-flags API router.

All routes are mounted under the prefix ``/feature-flags`` in main.py.

Delegates entirely to the adaptive module's FeatureFlagService, which owns
the real persistent database at data/adaptive.db and is shared with the
scraper's in-process feature-flag checks.

Route ordering matters: static path segments (``/check``, ``/stats``, etc.)
must be declared *before* the ``/{sport}`` path-parameter routes so FastAPI
does not capture them as a sport name.
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.schemas import (
    AuditLogEntryOut,
    AuditLogResponse,
    EnabledSportsResponse,
    FeatureFlagCheckResponse,
    FeatureFlagCreateRequest,
    FeatureFlagListResponse,
    FeatureFlagOut,
    FeatureFlagStatsResponse,
    FeatureFlagUpdateRequest,
)
from src.selectors.adaptive.services.feature_flag_service import (
    FeatureFlagService,
    get_feature_flag_service,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_path() -> str:
    """
    Resolve the shared adaptive database path.

    Respects the ``ADAPTIVE_DB_PATH`` environment variable so the test suite
    and CI can override it.  Falls back to ``<project-root>/data/adaptive.db``.
    """
    env = os.environ.get("ADAPTIVE_DB_PATH")
    if env:
        return env
    project_root = Path(__file__).resolve().parents[3]  # src/api/routers/ → root
    db_dir = project_root / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "adaptive.db")


def _svc() -> FeatureFlagService:
    """Return a FeatureFlagService wired to the shared DB path."""
    return FeatureFlagService(db_path=_db_path())


def _to_out(flag) -> FeatureFlagOut:
    """Convert an adaptive FeatureFlag model instance to the API output schema."""
    return FeatureFlagOut(
        id=flag.id,
        sport=flag.sport,
        site=flag.site,
        enabled=flag.enabled,
        description=getattr(flag, "description", None),
        created_at=flag.created_at,
        updated_at=flag.updated_at,
    )


# ===========================================================================
# Static routes  (must come before /{sport})
# ===========================================================================


@router.get(
    "",
    response_model=FeatureFlagListResponse,
    summary="List feature flags",
)
def list_feature_flags(
    sport: Optional[str] = Query(None, description="Filter by sport name"),
    site: Optional[str] = Query(None, description="Filter by site name"),
) -> FeatureFlagListResponse:
    """Return all feature flags, optionally filtered by sport and/or site."""
    svc = _svc()

    if sport:
        flags = svc.get_feature_flags_by_sport(sport)
    else:
        flags = svc.get_all_feature_flags()

    if site:
        flags = [f for f in flags if f.site == site]

    # Sort newest-updated first
    flags = sorted(flags, key=lambda f: f.updated_at, reverse=True)

    return FeatureFlagListResponse(
        data=[_to_out(f) for f in flags],
        count=len(flags),
    )


@router.post(
    "",
    response_model=FeatureFlagOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a feature flag",
)
def create_feature_flag(body: FeatureFlagCreateRequest) -> FeatureFlagOut:
    """Create a new feature flag.  Returns 409 if (sport, site) already exists."""
    svc = _svc()
    try:
        flag = svc.create_feature_flag(
            sport=body.sport,
            site=body.site,
            enabled=body.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _to_out(flag)


@router.get(
    "/check",
    response_model=FeatureFlagCheckResponse,
    summary="Check whether a feature flag is enabled",
)
def check_feature_flag(
    sport: str = Query(..., description="Sport to check"),
    site: Optional[str] = Query(None, description="Site to check (omit for global)"),
) -> FeatureFlagCheckResponse:
    """
    Resolve the effective enabled state for (sport, site).

    Lookup order:
    1. Site-specific flag  (sport + site)
    2. Global flag         (sport, site IS NULL)
    3. Default: disabled (flag_exists=False)
    """
    svc = _svc()
    flag = svc.get_feature_flag(sport, site)
    enabled = svc.is_adaptive_enabled(sport, site)
    return FeatureFlagCheckResponse(
        sport=sport,
        site=site,
        enabled=enabled,
        flag_exists=flag is not None,
    )


@router.get(
    "/enabled-sports",
    response_model=EnabledSportsResponse,
    summary="List sports with at least one enabled flag",
)
def get_enabled_sports() -> EnabledSportsResponse:
    svc = _svc()
    sports = sorted(svc.get_enabled_sports())
    return EnabledSportsResponse(sports=sports, count=len(sports))


@router.get(
    "/stats",
    response_model=FeatureFlagStatsResponse,
    summary="Aggregate feature-flag statistics",
)
def get_feature_flag_stats() -> FeatureFlagStatsResponse:
    svc = _svc()
    flags = svc.get_all_feature_flags()
    total = len(flags)
    enabled = sum(1 for f in flags if f.enabled)
    global_count = sum(1 for f in flags if f.site is None)
    site_specific = total - global_count
    unique_sports = len({f.sport for f in flags})
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
def get_site_flags() -> FeatureFlagListResponse:
    svc = _svc()
    flags = [f for f in svc.get_all_feature_flags() if f.site is not None]
    flags = sorted(flags, key=lambda f: (f.sport, f.site or ""))
    return FeatureFlagListResponse(
        data=[_to_out(f) for f in flags],
        count=len(flags),
    )


@router.get(
    "/audit-log",
    response_model=AuditLogResponse,
    summary="Retrieve audit log entries for feature-flag mutations",
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
) -> AuditLogResponse:
    """
    Return audit log entries from the adaptive module's audit_log table.

    The adaptive module records selector decisions (approve / reject / flag)
    rather than flag mutations, so the ``action`` field in each entry reflects
    the selector-decision vocabulary.  Front-end filters that use the feature-flag
    vocabulary (create / update / toggle / delete) are applied server-side by
    mapping to the closest equivalent action_type values.
    """
    try:
        from src.selectors.adaptive.db.repositories.audit_event_repository import (
            AuditEventRepository,
        )
    except ImportError:
        # Graceful degradation: return empty log if audit module unavailable
        return AuditLogResponse(
            data=[],
            count=0,
            page=1,
            page_size=limit,
            total_pages=1,
            has_more=False,
        )

    repo = AuditEventRepository(db_path=_db_path())

    # Map the UI's feature-flag action vocabulary to the adaptive module's
    # action_type values so filters work sensibly across both worlds.
    _ACTION_MAP = {
        "create": "custom_selector_created",
        "update": "selector_approved",
        "toggle": "selector_approved",
        "delete": "selector_rejected",
    }

    try:
        all_entries = repo.get_recent_audit_events(limit=10_000)
    except Exception:
        all_entries = []

    # Apply filters
    if sport:
        all_entries = [
            e
            for e in all_entries
            if (e.selector_id or "").lower().startswith(sport.lower())
        ]
    if site:
        all_entries = [
            e for e in all_entries if site.lower() in (e.selector_id or "").lower()
        ]
    if action and action != "all":
        target_action = _ACTION_MAP.get(action, action)
        all_entries = [e for e in all_entries if e.action_type == target_action]
    if user:
        all_entries = [
            e for e in all_entries if user.lower() in (e.user_id or "").lower()
        ]

    total = len(all_entries)
    page_entries = all_entries[offset : offset + limit]

    page_size = limit
    page = (offset // page_size) + 1 if page_size else 1
    total_pages = max(1, math.ceil(total / page_size)) if page_size else 1

    def _entry_to_out(e) -> AuditLogEntryOut:
        # Map adaptive action_type → UI action vocabulary
        _REVERSE_ACTION_MAP = {
            "custom_selector_created": "create",
            "selector_approved": "update",
            "selector_rejected": "delete",
            "selector_flagged": "toggle",
        }
        ui_action = _REVERSE_ACTION_MAP.get(e.action_type, "update")

        # Derive sport/site from selector_id (format: sport.site.element)
        selector_id = e.selector_id or ""
        parts = selector_id.split(".")
        entry_sport = parts[0] if parts else selector_id
        entry_site = parts[1] if len(parts) > 1 else None

        return AuditLogEntryOut(
            id=e.id,
            action=ui_action,
            sport=entry_sport,
            site=entry_site,
            old_value=None,
            new_value=None,
            user=e.user_id or "system",
            timestamp=e.timestamp,
            description=e.notes or e.reason,
        )

    return AuditLogResponse(
        data=[_entry_to_out(e) for e in page_entries],
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
def get_sport_flags(sport: str) -> FeatureFlagListResponse:
    svc = _svc()
    flags = svc.get_feature_flags_by_sport(sport)
    flags = sorted(flags, key=lambda f: (f.site or ""))
    return FeatureFlagListResponse(
        data=[_to_out(f) for f in flags],
        count=len(flags),
    )


@router.patch(
    "/{sport}",
    response_model=FeatureFlagOut,
    summary="Update / toggle a sport's global flag",
)
def update_sport_flag(sport: str, body: FeatureFlagUpdateRequest) -> FeatureFlagOut:
    svc = _svc()
    flag = svc.update_feature_flag(sport, site=None, enabled=body.enabled)
    if flag is None:
        # Auto-create if it doesn't exist yet (idempotent upsert)
        flag = svc.create_feature_flag(sport=sport, site=None, enabled=body.enabled)
    return _to_out(flag)


@router.delete(
    "/{sport}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a sport's global flag",
)
def delete_sport_flag(sport: str) -> None:
    svc = _svc()
    deleted = svc.delete_feature_flag(sport, site=None)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag not found: sport={sport!r} (global)",
        )


@router.get(
    "/{sport}/sites/{site}",
    response_model=FeatureFlagOut,
    summary="Get a site-specific flag",
)
def get_site_flag(sport: str, site: str) -> FeatureFlagOut:
    svc = _svc()
    flag = svc.get_feature_flag(sport, site)
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag not found: sport={sport!r}, site={site!r}",
        )
    return _to_out(flag)


@router.patch(
    "/{sport}/sites/{site}",
    response_model=FeatureFlagOut,
    summary="Update / toggle a site-specific flag",
)
def update_site_flag(
    sport: str,
    site: str,
    body: FeatureFlagUpdateRequest,
) -> FeatureFlagOut:
    svc = _svc()
    flag = svc.update_feature_flag(sport, site=site, enabled=body.enabled)
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag not found: sport={sport!r}, site={site!r}",
        )
    return _to_out(flag)


@router.delete(
    "/{sport}/sites/{site}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a site-specific flag",
)
def delete_site_flag(sport: str, site: str) -> None:
    svc = _svc()
    deleted = svc.delete_feature_flag(sport, site=site)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag not found: sport={sport!r}, site={site!r}",
        )
