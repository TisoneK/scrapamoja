"""
FastAPI router — /runs

Exposes RunController to the Electron UI over HTTP + SSE.
Drop this file into src/api/routers/runs.py and register it in src/api/main.py.

Follows the exact same style as the existing routers in:
  - src/api/routers/failures.py
  - src/api/routers/feature_flags.py
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .run_state import RunStatus
from .run_controller import RunController

router = APIRouter(prefix="/runs", tags=["runs"])


# ---------------------------------------------------------------------------
# Dependency — singleton controller injected by FastAPI
# ---------------------------------------------------------------------------

def get_controller() -> RunController:
    """
    Override this in main.py with the actual singleton:

        from .run_controller import RunController
        _controller = RunController()

        @app.on_event("startup")
        async def _startup():
            await _controller.start()

        app.dependency_overrides[get_controller] = lambda: _controller
    """
    raise RuntimeError("RunController not initialised — check lifespan setup")


# ---------------------------------------------------------------------------
# Request / Response schemas — Pydantic v2, matching existing schemas.py style
# ---------------------------------------------------------------------------

class StartRunRequest(BaseModel):
    scraper_id: str = Field(..., min_length=1)
    scraper_name: str = Field(..., min_length=1)
    target_url: str = Field(..., min_length=1)
    extraction_mode: str = Field("dom", pattern="^(dom|api|network|hybrid)$")
    proxy_enabled: bool = False
    stealth_enabled: bool = True
    schedule_expr: Optional[str] = None
    priority: int = Field(0, ge=0, le=10)
    resume_from: Optional[str] = None


class RunSummary(BaseModel):
    """Lightweight representation for list endpoints."""
    run_id: str
    scraper_id: str
    scraper_name: str
    status: str
    stage: str
    progress: float
    records_extracted: int
    warning_count: int
    error_count: int
    duration_seconds: Optional[float]
    started_at: Optional[float]
    queued_at: float


class RunDetail(RunSummary):
    """Full run state for the detail / stream views."""
    target_url: str
    extraction_mode: str
    proxy_enabled: bool
    stealth_enabled: bool
    scheduled: bool
    schedule_expr: Optional[str]
    resumable: bool
    checkpoint_path: Optional[str]
    retry_count: int
    retry_max: int
    records_stored: int
    pages_visited: int
    pages_total: Optional[int]
    warnings: list
    errors: list
    updated_at: float
    completed_at: Optional[float]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=RunDetail, status_code=202)
async def start_run(
    body: StartRunRequest,
    controller: RunController = Depends(get_controller),
):
    """
    Enqueue a new scraping run.
    Returns immediately with status=queued; poll /runs/{run_id} or
    subscribe to /runs/{run_id}/stream for live updates.
    """
    state = await controller.start_run(
        scraper_id=body.scraper_id,
        scraper_name=body.scraper_name,
        target_url=body.target_url,
        extraction_mode=body.extraction_mode,
        proxy_enabled=body.proxy_enabled,
        stealth_enabled=body.stealth_enabled,
        schedule_expr=body.schedule_expr,
        priority=body.priority,
        resume_from=body.resume_from,
    )
    return RunDetail(**state.to_dict())


@router.get("", response_model=List[RunSummary])
async def list_runs(
    status: Optional[str] = Query(None),
    scraper_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    controller: RunController = Depends(get_controller),
):
    """Return runs filtered by status and/or scraper, newest first."""
    status_enum = RunStatus(status) if status else None
    runs = controller.list_runs(status=status_enum, scraper_id=scraper_id, limit=limit)
    return [RunSummary(**r.to_dict()) for r in runs]


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(
    run_id: str,
    controller: RunController = Depends(get_controller),
):
    """Full state snapshot for a single run."""
    try:
        state = controller.get_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return RunDetail(**state.to_dict())


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: str,
    controller: RunController = Depends(get_controller),
):
    """
    SSE stream — yields RunEvents as they occur.
    The Electron UI connects here and updates its local state reactively.

    Event types: state_changed | progress | record_extracted |
                 warning | error | log | checkpoint_saved |
                 run_completed | run_failed | run_cancelled
    """
    try:
        controller.get_run(run_id)  # validate exists
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    return StreamingResponse(
        controller.stream_run(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


@router.post("/{run_id}/stop", response_model=RunDetail)
async def stop_run(
    run_id: str,
    controller: RunController = Depends(get_controller),
):
    """Gracefully stop a run. Saves checkpoint before terminating."""
    try:
        state = await controller.stop_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return RunDetail(**state.to_dict())


@router.post("/{run_id}/pause", response_model=RunDetail)
async def pause_run(
    run_id: str,
    controller: RunController = Depends(get_controller),
):
    """Pause a running job. Checkpoint is saved; can be resumed."""
    try:
        state = await controller.pause_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RunDetail(**state.to_dict())


@router.post("/{run_id}/resume", response_model=RunDetail)
async def resume_run(
    run_id: str,
    controller: RunController = Depends(get_controller),
):
    """Resume a paused run from its last checkpoint."""
    try:
        state = await controller.resume_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RunDetail(**state.to_dict())


@router.delete("/{run_id}", response_model=RunDetail)
async def cancel_run(
    run_id: str,
    controller: RunController = Depends(get_controller),
):
    """Hard cancel — no checkpoint saved."""
    try:
        state = await controller.cancel_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return RunDetail(**state.to_dict())
