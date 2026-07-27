"""Remote-control API for the betb2b scraper.

Trigger scrapes, monitor jobs, and read the odds store — over HTTP, secured
with an API key (``x-api-key`` header vs the ``SCRAPER_API_KEY`` env). Scrapes
run as single-flight background jobs inside this service (see
:mod:`src.sites.betb2b.service`); the deployed egress needs an allowed-country
proxy via ``BETB2B_PROXY_*`` or runs fail with a clear status.
"""

from __future__ import annotations

import hmac
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from src.sites.betb2b import store
from src.sites.betb2b.service import ScraperService

router = APIRouter()

# One runner owns the queue for this process (see service docstring: deploy with
# GUNICORN_WORKERS=1 for deterministic single-flight).
service = ScraperService()

# Friendly status aliases → canonical scrape actions.
_ACTION_ALIASES = {
    "live": "list_live",
    "prematch": "list_prematch",
    "scheduled": "list_prematch",
    "all": "list_all",
}
_VALID_ACTIONS = {
    "list_live", "list_prematch", "list_all",
    "raw_capture", "sports_short", "top_champs",
}


# --------------------------------------------------------------------------- #
# Auth — fail closed: 503 if no key configured, 401 if wrong/missing.
# --------------------------------------------------------------------------- #
def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    expected = os.environ.get("SCRAPER_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="scraper control API disabled: set SCRAPER_API_KEY",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="invalid or missing x-api-key")


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class RunRequest(BaseModel):
    skin: str = Field("linebet", description="Skin name, or comma-list (linebet,melbet).")
    action: str = Field("list_live", description="live/prematch/all or list_live/list_prematch/…")
    sport: Optional[str] = Field(None, description="Sport slug, e.g. basketball. None = all.")
    subgames: bool = Field(False, description="Also fetch per-quarter/half sub-games (ADR-7).")
    count: Optional[int] = Field(None, ge=1, le=200, description="count= query param (default 50).")


class JobOut(BaseModel):
    job_id: int
    skin: str
    sport: Optional[str]
    action: str
    subgames: bool
    count: Optional[int]
    status: str
    phase: Optional[str] = None
    # Postgres returns timestamptz as datetime; SQLite returns ISO strings.
    # `datetime` accepts both (str is parsed) and serializes to ISO in JSON.
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    run_id: Optional[int]
    event_count: Optional[int]
    error: Optional[str]

    @classmethod
    def from_row(cls, row) -> "JobOut":
        d = dict(row)
        d["subgames"] = bool(d.get("subgames"))
        return cls(**{k: d.get(k) for k in cls.model_fields})


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@router.post("/runs", response_model=JobOut, status_code=202,
             dependencies=[Depends(require_api_key)])
def trigger_run(req: RunRequest) -> JobOut:
    """Queue a scrape. Returns immediately with the job (status=queued)."""
    action = _ACTION_ALIASES.get(req.action.lower(), req.action)
    if action not in _VALID_ACTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"unknown action {req.action!r}; valid: {sorted(_VALID_ACTIONS)}",
        )
    job_id = service.submit(
        skin=req.skin, action=action, sport=req.sport,
        subgames=req.subgames, count=req.count, created_by="api",
    )
    conn = store.init_db(service.path)
    row = store.get_job(conn, job_id)
    conn.close()
    return JobOut.from_row(row)


@router.get("/runs", response_model=List[JobOut],
            dependencies=[Depends(require_api_key)])
def list_runs(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter: queued/running/succeeded/failed"),
) -> List[JobOut]:
    conn = store.init_db(service.path)
    rows = store.list_jobs(conn, limit=limit, status=status)
    conn.close()
    return [JobOut.from_row(r) for r in rows]


@router.get("/runs/{job_id}", response_model=JobOut,
            dependencies=[Depends(require_api_key)])
def get_run(job_id: int) -> JobOut:
    conn = store.init_db(service.path)
    row = store.get_job(conn, job_id)
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return JobOut.from_row(row)


@router.get("/skins", dependencies=[Depends(require_api_key)])
def list_skins() -> dict:
    from src.sites.betb2b.cli.main import _list_skins
    return {"skins": _list_skins()}


@router.get("/sports", dependencies=[Depends(require_api_key)])
def list_sports() -> dict:
    from src.sites.betb2b.sports import list_sport_scraper_summaries
    return {"sports": [s.get("slug") for s in list_sport_scraper_summaries()]}


@router.get("/counts", dependencies=[Depends(require_api_key)])
def store_counts() -> dict:
    """Row counts per table — quick coverage/health of the odds store."""
    conn = store.init_db(service.path)
    try:
        return store.counts(conn)
    finally:
        conn.close()


@router.get("/odds/{event_id}", dependencies=[Depends(require_api_key)])
def latest_event_odds(
    event_id: str,
    skin: Optional[str] = Query(None, description="Restrict to one skin."),
) -> dict:
    """Most recent odds snapshot per selection for an event (cross-skin)."""
    conn = store.init_db(service.path)
    try:
        rows = store.latest_odds(conn, event_id, skin=skin)
        return {"event_id": event_id, "odds": [dict(r) for r in rows]}
    finally:
        conn.close()
