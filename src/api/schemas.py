"""
Pydantic v2 request / response schemas for the Scrapamoja API.

These schemas are the single source of truth for the JSON contract between
the FastAPI backend and the React UI.  TypeScript types in
``ui/app/src/types/featureFlag.ts`` and ``ui/app/src/hooks/useFailures.ts``
must stay in sync with the shapes defined here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# Feature-flag schemas
# ===========================================================================


# ── Responses ────────────────────────────────────────────────────────────────


class FeatureFlagOut(_Base):
    """Full representation of a feature-flag row (returned to the UI)."""

    id: int
    sport: str
    site: str | None
    enabled: bool
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class FeatureFlagListResponse(_Base):
    """Paginated / filtered list of feature flags."""

    data: list[FeatureFlagOut]
    count: int


class FeatureFlagCheckResponse(_Base):
    """Result of the /check endpoint."""

    sport: str
    site: str | None
    enabled: bool
    flag_exists: bool


class EnabledSportsResponse(_Base):
    """List of sport names that have at least one enabled flag."""

    sports: list[str]
    count: int


class FeatureFlagStatsResponse(_Base):
    """Aggregate statistics shown on the Feature Flags page header."""

    total_flags: int
    enabled_flags: int
    disabled_flags: int
    global_flags: int
    site_specific_flags: int
    unique_sports: int


# ── Requests ─────────────────────────────────────────────────────────────────


class FeatureFlagCreateRequest(_Base):
    """Body for POST /feature-flags."""

    sport: str = Field(..., min_length=1, max_length=64)
    site: str | None = Field(None, max_length=64)
    enabled: bool
    description: str | None = None


class FeatureFlagUpdateRequest(_Base):
    """Body for PATCH /feature-flags/{sport} and …/sites/{site}."""

    enabled: bool
    description: str | None = None


class FeatureFlagToggleRequest(_Base):
    """Minimal body used by toggle-only callers."""

    enabled: bool


# ===========================================================================
# Audit-log schemas
# ===========================================================================


class AuditLogEntryOut(_Base):
    """
    One audit-log row.

    Matches the shape expected by ``AuditLogViewer.tsx``:
    id, action, sport, site?, old_value?, new_value?, user, timestamp, description?
    """

    id: int
    action: str  # create | update | toggle | delete
    sport: str
    site: str | None
    old_value: bool | None
    new_value: bool | None
    user: str
    timestamp: datetime
    description: str | None = None


class AuditLogResponse(_Base):
    """Paginated audit-log result."""

    data: list[AuditLogEntryOut]
    count: int
    page: int
    page_size: int
    total_pages: int
    has_more: bool


# ===========================================================================
# Failure / escalation schemas
# ===========================================================================


# ── Sub-models ───────────────────────────────────────────────────────────────


class BlastRadiusInfo(_Base):
    """Blast-radius metadata attached to an alternative selector."""

    affected_count: int
    affected_sports: list[str]
    severity: str  # low | medium | high | critical
    container_path: str


class AlternativeSelectorOut(_Base):
    """One candidate replacement selector proposed for a failure."""

    selector: str
    strategy: str  # css | xpath | text | attribute
    confidence_score: float
    blast_radius: BlastRadiusInfo | None = None
    highlight_css: str | None = None
    is_custom: bool = False
    custom_notes: str | None = None


# ── List-view item ───────────────────────────────────────────────────────────


class FailureListItem(_Base):
    """Lightweight row returned by GET /failures (list view)."""

    failure_id: int
    selector_id: str
    failed_selector: str
    recipe_id: str | None = None
    sport: str | None = None
    site: str | None = None
    timestamp: datetime
    error_type: str
    severity: str
    has_alternatives: bool
    alternative_count: int
    flagged: bool = False
    flag_note: str | None = None


class FailureListResponse(_Base):
    """Paginated list of selector failures."""

    data: list[FailureListItem]
    total: int
    page: int
    page_size: int
    filters: dict[str, Any] = Field(default_factory=dict)


# ── Detail view ──────────────────────────────────────────────────────────────


class FailureDetailOut(_Base):
    """Full failure record with alternative selectors (detail view)."""

    failure_id: int
    selector_id: str
    failed_selector: str
    recipe_id: str | None = None
    sport: str | None = None
    site: str | None = None
    timestamp: datetime
    error_type: str
    failure_reason: str | None = None
    severity: str
    snapshot_id: int | None = None
    alternatives: list[AlternativeSelectorOut] = Field(default_factory=list)
    flagged: bool = False
    flag_note: str | None = None
    flagged_at: datetime | None = None


class FailureDetailResponse(_Base):
    """Wrapper matching ``{ data: FailureDetail }`` expected by the UI."""

    data: FailureDetailOut


# ── Approval / rejection ─────────────────────────────────────────────────────


class ApprovalRequest(_Base):
    """Body for POST /failures/{id}/approve."""

    selector: str
    notes: str | None = None


class RejectionRequest(_Base):
    """Body for POST /failures/{id}/reject."""

    selector: str
    reason: str
    suggested_alternative: str | None = None


class ApprovalResponse(_Base):
    """Response from /approve and /reject endpoints."""

    success: bool
    message: str
    selector: str
    failure_id: int
    timestamp: datetime


# ── Flagging ──────────────────────────────────────────────────────────────────


class FlagRequest(_Base):
    """Body for POST /failures/{id}/flag."""

    note: str


class FlagResponse(_Base):
    """Response from POST / DELETE /failures/{id}/flag."""

    success: bool
    message: str
    failure_id: int
    flagged: bool
    flag_note: str
    flagged_at: datetime


# ── Custom selector ───────────────────────────────────────────────────────────


class CustomSelectorRequest(_Base):
    """Body for POST /failures/{id}/custom-selector."""

    selector_string: str
    strategy_type: str
    notes: str | None = None


class CustomSelectorResponse(_Base):
    """Response from POST /failures/{id}/custom-selector."""

    success: bool
    message: str
    failure_id: int
    selector: str
    strategy_type: str
    is_custom: bool
    created_at: datetime


# ===========================================================================
# Generic error response
# ===========================================================================


class ApiError(_Base):
    """Standard error body (mirrors TypeScript ``ApiError``)."""

    detail: str
    status: int | None = None
