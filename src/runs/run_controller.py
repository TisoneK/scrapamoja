"""
RunController — the coordination surface between the backend engine and the UI.

Responsibilities:
  - Owns the in-memory run registry (run_id → RunState)
  - Wraps the existing resilience / interrupt_handling machinery
  - Exposes a clean async API that the FastAPI router calls directly
  - Publishes RunEvents that SSE streams to the Electron UI

What it does NOT do:
  - Does not re-implement retry, checkpoint, or browser logic
    (those live in resilience/ and interrupt_handling/)
  - Does not touch storage directly
    (delegates to src/storage/adapter.py)
  - Does not know about React or Electron

Design: one singleton per process, managed by FastAPI lifespan.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional

from .run_state import RunState, RunStatus, RunStage, FailureSeverityLevel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RunEvent — the SSE payload
# ---------------------------------------------------------------------------


class RunEventType(str, Enum):
    """
    Event types emitted over the SSE stream.
    The Electron UI subscribes to GET /runs/{run_id}/stream
    and reacts to these event types to update its local state.
    """

    STATE_CHANGED = "state_changed"        # status or stage transition
    PROGRESS = "progress"                  # incremental progress tick
    RECORD_EXTRACTED = "record_extracted"  # one record just landed
    WARNING = "warning"                    # non-fatal issue
    ERROR = "error"                        # error recorded
    LOG = "log"                            # raw log line for the live log panel
    CHECKPOINT_SAVED = "checkpoint_saved"  # checkpoint written to disk
    RUN_COMPLETED = "run_completed"        # terminal success
    RUN_FAILED = "run_failed"             # terminal failure
    RUN_CANCELLED = "run_cancelled"        # user cancelled


@dataclass
class RunEvent:
    """A single event emitted during a run."""

    event_type: RunEventType
    run_id: str
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        """Format as SSE wire format: 'event: ...\ndata: ...\n\n'"""
        import json
        payload = json.dumps({
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            **self.data,
        })
        return f"event: {self.event_type.value}\ndata: {payload}\n\n"


# ---------------------------------------------------------------------------
# RunScheduler — thin job queue with worker pool
# ---------------------------------------------------------------------------


@dataclass
class ScheduledRun:
    """A run that has been queued but not started."""
    run_id: str
    scraper_id: str
    config: Dict[str, Any]
    priority: int = 0               # higher = runs sooner
    scheduled_at: float = field(default_factory=time.time)
    cron_expr: Optional[str] = None


class RunScheduler:
    """
    Priority-aware job queue backed by asyncio.

    Wraps asyncio.PriorityQueue so the RunController stays decoupled
    from queue mechanics. Later this can be swapped for a persistent
    queue (SQLite, Redis) without changing the RunController interface.
    """

    def __init__(self, max_concurrent: int = 3) -> None:
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._max_concurrent = max_concurrent
        self._active_count = 0
        self._lock = asyncio.Lock()

    async def enqueue(self, run: ScheduledRun) -> None:
        # PriorityQueue is min-heap; negate priority so higher = sooner
        await self._queue.put((-run.priority, run.scheduled_at, run))

    async def dequeue(self) -> Optional[ScheduledRun]:
        if self._queue.empty():
            return None
        _, _, run = await self._queue.get()
        return run

    @property
    def queue_depth(self) -> int:
        return self._queue.qsize()

    async def can_start(self) -> bool:
        async with self._lock:
            return self._active_count < self._max_concurrent

    async def mark_started(self) -> None:
        async with self._lock:
            self._active_count += 1

    async def mark_finished(self) -> None:
        async with self._lock:
            self._active_count = max(0, self._active_count - 1)


# ---------------------------------------------------------------------------
# RunController
# ---------------------------------------------------------------------------


class RunController:
    """
    Central coordinator for all scraping runs.

    Lifecycle:
        controller = RunController()
        await controller.start()          # starts the dispatcher loop
        ...
        await controller.stop()           # graceful shutdown

    The FastAPI router holds a reference to the singleton instance
    and calls start_run / stop_run / pause_run / resume_run / get_run.
    """

    def __init__(self, max_concurrent: int = 3) -> None:
        self._runs: Dict[str, RunState] = {}
        self._event_queues: Dict[str, asyncio.Queue] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._scheduler = RunScheduler(max_concurrent)
        self._dispatcher_task: Optional[asyncio.Task] = None
        self._shutdown = False

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background dispatcher loop."""
        self._dispatcher_task = asyncio.create_task(
            self._dispatcher_loop(), name="run_dispatcher"
        )
        logger.info("RunController started")

    async def stop(self) -> None:
        """Gracefully shut down all active runs and the dispatcher."""
        self._shutdown = True
        # Cancel active runs
        for run_id, task in list(self._tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=10.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
        logger.info("RunController stopped")

    # -------------------------------------------------------------------------
    # Public API — called by FastAPI router
    # -------------------------------------------------------------------------

    async def start_run(
        self,
        scraper_id: str,
        scraper_name: str,
        target_url: str,
        extraction_mode: str = "dom",
        proxy_enabled: bool = False,
        stealth_enabled: bool = True,
        schedule_expr: Optional[str] = None,
        priority: int = 0,
        resume_from: Optional[str] = None,
    ) -> RunState:
        """
        Create a RunState, enqueue it, and return immediately.
        The run starts asynchronously when a worker slot is free.
        """
        state = RunState(
            scraper_id=scraper_id,
            scraper_name=scraper_name,
            target_url=target_url,
            extraction_mode=extraction_mode,
            proxy_enabled=proxy_enabled,
            stealth_enabled=stealth_enabled,
            scheduled=schedule_expr is not None,
            schedule_expr=schedule_expr,
            checkpoint_path=resume_from,
            resumable=resume_from is not None,
        )
        self._runs[state.run_id] = state
        self._event_queues[state.run_id] = asyncio.Queue(maxsize=500)

        scheduled = ScheduledRun(
            run_id=state.run_id,
            scraper_id=scraper_id,
            config={
                "target_url": target_url,
                "extraction_mode": extraction_mode,
                "proxy_enabled": proxy_enabled,
                "stealth_enabled": stealth_enabled,
                "resume_from": resume_from,
            },
            priority=priority,
        )
        await self._scheduler.enqueue(scheduled)
        logger.info("Enqueued run %s for scraper %s", state.run_id, scraper_id)
        return state

    async def stop_run(self, run_id: str) -> RunState:
        """Gracefully stop a run. Saves checkpoint before terminating."""
        state = self._get_or_raise(run_id)
        if state.is_terminal:
            return state
        state.transition(RunStatus.STOPPING)
        await self._emit(run_id, RunEventType.STATE_CHANGED, {"status": state.status.value})

        task = self._tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=15.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        state.transition(RunStatus.CANCELLED)
        await self._emit(run_id, RunEventType.RUN_CANCELLED, state.to_dict())
        return state

    async def pause_run(self, run_id: str) -> RunState:
        """
        Pause a run. The underlying engine checkpoints current position.
        The run can be resumed later via resume_run().
        """
        state = self._get_or_raise(run_id)
        if state.status != RunStatus.RUNNING:
            raise ValueError(f"Run {run_id} is not running (status={state.status.value})")

        # Signal the running task to checkpoint and pause
        # The task watches _paused flags on the state object
        state.transition(RunStatus.PAUSED, RunStage.CHECKPOINTING)
        state.resumable = True
        await self._emit(run_id, RunEventType.STATE_CHANGED, {
            "status": state.status.value,
            "stage": state.stage.value,
        })
        logger.info("Paused run %s", run_id)
        return state

    async def resume_run(self, run_id: str) -> RunState:
        """Resume a paused run from its last checkpoint."""
        state = self._get_or_raise(run_id)
        if state.status != RunStatus.PAUSED:
            raise ValueError(f"Run {run_id} is not paused (status={state.status.value})")

        state.transition(RunStatus.QUEUED)
        scheduled = ScheduledRun(
            run_id=run_id,
            scraper_id=state.scraper_id,
            config={"resume_from": state.checkpoint_path},
        )
        await self._scheduler.enqueue(scheduled)
        await self._emit(run_id, RunEventType.STATE_CHANGED, {"status": state.status.value})
        return state

    async def cancel_run(self, run_id: str) -> RunState:
        """Hard cancel — no checkpoint saved."""
        state = self._get_or_raise(run_id)
        task = self._tasks.get(run_id)
        if task and not task.done():
            task.cancel()
        state.transition(RunStatus.CANCELLED)
        await self._emit(run_id, RunEventType.RUN_CANCELLED, state.to_dict())
        return state

    def get_run(self, run_id: str) -> RunState:
        return self._get_or_raise(run_id)

    def list_runs(
        self,
        status: Optional[RunStatus] = None,
        scraper_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[RunState]:
        """Return runs filtered by status and/or scraper, newest first."""
        runs = list(self._runs.values())
        if status:
            runs = [r for r in runs if r.status == status]
        if scraper_id:
            runs = [r for r in runs if r.scraper_id == scraper_id]
        runs.sort(key=lambda r: r.queued_at, reverse=True)
        return runs[:limit]

    async def stream_run(self, run_id: str) -> AsyncIterator[str]:
        """
        Async generator yielding SSE-formatted strings.
        The FastAPI router pipes this directly into a StreamingResponse.

        Usage:
            @router.get("/runs/{run_id}/stream")
            async def stream(run_id: str):
                return StreamingResponse(
                    controller.stream_run(run_id),
                    media_type="text/event-stream",
                )
        """
        self._get_or_raise(run_id)  # validate run exists
        queue = self._event_queues[run_id]

        # Immediately send current state as first event
        state = self._runs[run_id]
        yield RunEvent(
            event_type=RunEventType.STATE_CHANGED,
            run_id=run_id,
            data=state.to_dict(),
        ).to_sse()

        while True:
            try:
                event: RunEvent = await asyncio.wait_for(queue.get(), timeout=25.0)
                yield event.to_sse()
                if event.event_type in (
                    RunEventType.RUN_COMPLETED,
                    RunEventType.RUN_FAILED,
                    RunEventType.RUN_CANCELLED,
                ):
                    break
            except asyncio.TimeoutError:
                # Heartbeat — keeps the SSE connection alive
                yield ": heartbeat\n\n"

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _get_or_raise(self, run_id: str) -> RunState:
        state = self._runs.get(run_id)
        if state is None:
            raise KeyError(f"Run not found: {run_id}")
        return state

    async def _emit(
        self,
        run_id: str,
        event_type: RunEventType,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Put an event on the run's SSE queue (non-blocking)."""
        queue = self._event_queues.get(run_id)
        if queue is None:
            return
        event = RunEvent(event_type=event_type, run_id=run_id, data=data or {})
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("SSE queue full for run %s — dropping event %s", run_id, event_type)

    async def _dispatcher_loop(self) -> None:
        """
        Background loop that dequeues scheduled runs and
        spawns worker tasks when concurrency slots are free.
        """
        logger.info("Dispatcher loop started")
        while not self._shutdown:
            try:
                if await self._scheduler.can_start():
                    scheduled = await self._scheduler.dequeue()
                    if scheduled:
                        await self._scheduler.mark_started()
                        task = asyncio.create_task(
                            self._run_worker(scheduled),
                            name=f"run_worker_{scheduled.run_id}",
                        )
                        self._tasks[scheduled.run_id] = task
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Dispatcher loop error")

    async def _run_worker(self, scheduled: ScheduledRun) -> None:
        """
        Execute a single run.

        This is the integration point with the Scrapamoja engine.
        It delegates to the site-specific orchestrator (e.g. FlashscoreOrchestrator)
        and wires its events into the RunState / SSE machinery.
        """
        run_id = scheduled.run_id
        state = self._runs[run_id]

        try:
            state.transition(RunStatus.STARTING, RunStage.INITIALISING)
            await self._emit(run_id, RunEventType.STATE_CHANGED, {
                "status": state.status.value, "stage": state.stage.value
            })

            # ----------------------------------------------------------------
            # Integration point — swap this stub for the real engine call:
            #
            #   orchestrator = await build_orchestrator(scheduled.config)
            #   async for event in orchestrator.run():
            #       await self._handle_engine_event(run_id, state, event)
            #
            # The orchestrator emits dicts; _handle_engine_event translates
            # them into RunState mutations + SSE events.
            # ----------------------------------------------------------------

            state.transition(RunStatus.RUNNING, RunStage.NAVIGATING)
            await self._emit(run_id, RunEventType.STATE_CHANGED, {
                "status": state.status.value, "stage": state.stage.value
            })

            # Stub: real engine would drive progress here
            # ...

            state.transition(RunStatus.COMPLETED)
            await self._emit(run_id, RunEventType.RUN_COMPLETED, state.to_dict())

        except asyncio.CancelledError:
            if state.status not in (RunStatus.CANCELLED, RunStatus.PAUSED):
                state.transition(RunStatus.CANCELLED)
                await self._emit(run_id, RunEventType.RUN_CANCELLED, state.to_dict())
        except Exception as exc:
            logger.exception("Run %s failed: %s", run_id, exc)
            state.record_error(
                code="unhandled_exception",
                message=str(exc),
                severity=FailureSeverityLevel.CRITICAL,
                retryable=False,
            )
            state.transition(RunStatus.FAILED)
            await self._emit(run_id, RunEventType.RUN_FAILED, state.to_dict())
        finally:
            await self._scheduler.mark_finished()

    async def _handle_engine_event(
        self,
        run_id: str,
        state: RunState,
        event: Dict[str, Any],
    ) -> None:
        """
        Translate a raw engine event into a RunState mutation + SSE emission.
        Called by _run_worker once the real engine integration is wired in.

        Expected engine event shape (from FlashscoreOrchestrator / resilience events):
            {
                "type": "progress" | "record" | "warning" | "error" | "stage" | "checkpoint",
                "payload": { ... }
            }
        """
        event_type = event.get("type")
        payload = event.get("payload", {})

        if event_type == "stage":
            try:
                stage = RunStage(payload["stage"])
                state.advance_stage(stage)
                await self._emit(run_id, RunEventType.STATE_CHANGED, {
                    "stage": stage.value
                })
            except ValueError:
                pass

        elif event_type == "progress":
            state.set_progress(payload.get("value", state.progress))
            state.pages_visited = payload.get("pages_visited", state.pages_visited)
            state.pages_total = payload.get("pages_total", state.pages_total)
            await self._emit(run_id, RunEventType.PROGRESS, {
                "progress": state.progress,
                "pages_visited": state.pages_visited,
                "pages_total": state.pages_total,
            })

        elif event_type == "record":
            state.increment_records(extracted=1, stored=payload.get("stored", 0))
            await self._emit(run_id, RunEventType.RECORD_EXTRACTED, {
                "records_extracted": state.records_extracted,
                "record": payload.get("data"),
            })

        elif event_type == "warning":
            state.record_warning(
                code=payload.get("code", "unknown"),
                message=payload.get("message", ""),
            )
            await self._emit(run_id, RunEventType.WARNING, {
                "code": payload.get("code"),
                "message": payload.get("message"),
            })

        elif event_type == "error":
            state.record_error(
                code=payload.get("code", "unknown"),
                message=payload.get("message", ""),
                severity=FailureSeverityLevel(
                    payload.get("severity", FailureSeverityLevel.MEDIUM.value)
                ),
                retryable=payload.get("retryable", True),
            )
            state.retry_count = payload.get("retry_count", state.retry_count)
            await self._emit(run_id, RunEventType.ERROR, payload)

        elif event_type == "checkpoint":
            state.checkpoint_path = payload.get("path")
            state.resumable = True
            await self._emit(run_id, RunEventType.CHECKPOINT_SAVED, {
                "checkpoint_path": state.checkpoint_path
            })

        elif event_type == "log":
            await self._emit(run_id, RunEventType.LOG, {
                "level": payload.get("level", "info"),
                "message": payload.get("message", ""),
            })
