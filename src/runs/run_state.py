"""
Run state contract — the single source of truth for a scraping job's lifecycle.

This module defines RunStatus, RunStage, RunState, and RunEvent.
Every layer — UI, API, orchestrator, and backend — speaks this language.

Extends the existing patterns in:
  - src/interrupt_handling/state.py     (phase/enum/dataclass pattern)
  - src/resilience/coordinator.py       (DegradationContext shape)
  - src/resilience/failure_classifier.py (FailureType enum)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RunStatus(str, Enum):
    """Top-level lifecycle status of a run. Drives UI colour + affordances."""

    QUEUED = "queued"          # Waiting in job queue
    STARTING = "starting"      # Browser launching, pre-flight checks
    RUNNING = "running"        # Actively scraping
    PAUSED = "paused"          # User-paused; checkpoint saved
    STOPPING = "stopping"      # Graceful shutdown in progress
    COMPLETED = "completed"    # Finished cleanly
    FAILED = "failed"          # Terminal failure after all retries exhausted
    CANCELLED = "cancelled"    # User-cancelled


class RunStage(str, Enum):
    """
    Fine-grained execution stage within a run.
    Drives the live progress label in the Runs UI.
    Maps directly to the orchestrator's internal phases.
    """

    INITIALISING = "initialising"        # Browser pool, session setup
    NAVIGATING = "navigating"            # Moving to target URL
    HANDLING_CONSENT = "handling_consent"  # Cookie / consent popups
    EXTRACTING = "extracting"            # Selector engine active
    NORMALISING = "normalising"          # DataNormalizer processing
    PAGINATING = "paginating"            # Moving to next page
    RETRYING = "retrying"                # Resilience retry in progress
    CHECKPOINTING = "checkpointing"      # Saving checkpoint to disk
    STORING = "storing"                  # Writing to storage adapter
    FINISHING = "finishing"              # Cleanup, browser teardown


class FailureSeverityLevel(str, Enum):
    """
    Maps to resilience.models.failure_event.FailureSeverity.
    Kept separate so the contract has no hard import dependency on resilience.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# RunWarning / RunError — structured problem records
# ---------------------------------------------------------------------------


@dataclass
class RunWarning:
    """A non-fatal issue encountered during a run."""

    code: str                            # e.g. "selector_low_confidence"
    message: str
    stage: RunStage
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunError:
    """A fatal or recoverable error encountered during a run."""

    code: str                            # e.g. "selector_exhausted"
    message: str
    stage: RunStage
    severity: FailureSeverityLevel = FailureSeverityLevel.MEDIUM
    timestamp: float = field(default_factory=time.time)
    retryable: bool = True
    context: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# RunState — the core contract object
# ---------------------------------------------------------------------------


@dataclass
class RunState:
    """
    Complete observable state of a single scraping run.

    This object is:
      - the language between RunController and the FastAPI layer
      - the source for SSE events streamed to the Electron UI
      - serialisable to JSON for persistence and resume

    Shape is intentionally close to the UI's expected payload so the
    API router can return it with minimal transformation.
    """

    # Identity
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scraper_id: str = ""           # Which site/scraper config is running
    scraper_name: str = ""         # Human label, e.g. "Flashscore Basketball"

    # Lifecycle
    status: RunStatus = RunStatus.QUEUED
    stage: RunStage = RunStage.INITIALISING

    # Progress
    progress: float = 0.0          # 0.0 → 1.0
    records_extracted: int = 0
    records_stored: int = 0
    pages_visited: int = 0
    pages_total: Optional[int] = None   # None = unknown (infinite scroll etc.)

    # Health
    warnings: List[RunWarning] = field(default_factory=list)
    errors: List[RunError] = field(default_factory=list)
    retry_count: int = 0
    retry_max: int = 3

    # Timing
    queued_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    # Execution config snapshot (what was used for this run)
    target_url: str = ""
    extraction_mode: str = "dom"   # dom | api | network | hybrid
    proxy_enabled: bool = False
    stealth_enabled: bool = True
    scheduled: bool = False
    schedule_expr: Optional[str] = None   # cron expression if scheduled

    # Checkpoint reference (for resume)
    checkpoint_path: Optional[str] = None
    resumable: bool = False

    # ---------------------------------------------------------------------------
    # Derived properties
    # ---------------------------------------------------------------------------

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at is None:
            return None
        end = self.completed_at or time.time()
        return round(end - self.started_at, 2)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def is_active(self) -> bool:
        return self.status in (RunStatus.STARTING, RunStatus.RUNNING, RunStatus.STOPPING)

    @property
    def is_terminal(self) -> bool:
        return self.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED)

    # ---------------------------------------------------------------------------
    # Mutations — always touch updated_at
    # ---------------------------------------------------------------------------

    def transition(self, status: RunStatus, stage: Optional[RunStage] = None) -> None:
        """Move to a new status, optionally update stage."""
        self.status = status
        if stage is not None:
            self.stage = stage
        self.updated_at = time.time()

        if status == RunStatus.RUNNING and self.started_at is None:
            self.started_at = time.time()
        if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            self.completed_at = time.time()

    def advance_stage(self, stage: RunStage) -> None:
        self.stage = stage
        self.updated_at = time.time()

    def record_warning(self, code: str, message: str, **context: Any) -> None:
        self.warnings.append(RunWarning(
            code=code, message=message, stage=self.stage, context=context
        ))
        self.updated_at = time.time()

    def record_error(
        self,
        code: str,
        message: str,
        severity: FailureSeverityLevel = FailureSeverityLevel.MEDIUM,
        retryable: bool = True,
        **context: Any,
    ) -> None:
        self.errors.append(RunError(
            code=code, message=message, stage=self.stage,
            severity=severity, retryable=retryable, context=context
        ))
        self.updated_at = time.time()

    def increment_records(self, extracted: int = 0, stored: int = 0) -> None:
        self.records_extracted += extracted
        self.records_stored += stored
        self.updated_at = time.time()

    def set_progress(self, value: float) -> None:
        self.progress = max(0.0, min(1.0, value))
        self.updated_at = time.time()

    # ---------------------------------------------------------------------------
    # Serialisation
    # ---------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        JSON-serialisable dict — this is what the FastAPI router returns
        and what the Electron UI consumes via SSE.
        """
        return {
            "run_id": self.run_id,
            "scraper_id": self.scraper_id,
            "scraper_name": self.scraper_name,
            "status": self.status.value,
            "stage": self.stage.value,
            "progress": round(self.progress, 4),
            "records_extracted": self.records_extracted,
            "records_stored": self.records_stored,
            "pages_visited": self.pages_visited,
            "pages_total": self.pages_total,
            "warning_count": self.warning_count,
            "error_count": self.error_count,
            "retry_count": self.retry_count,
            "retry_max": self.retry_max,
            "duration_seconds": self.duration_seconds,
            "queued_at": self.queued_at,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "target_url": self.target_url,
            "extraction_mode": self.extraction_mode,
            "proxy_enabled": self.proxy_enabled,
            "stealth_enabled": self.stealth_enabled,
            "scheduled": self.scheduled,
            "schedule_expr": self.schedule_expr,
            "resumable": self.resumable,
            "checkpoint_path": self.checkpoint_path,
            # Full warning/error lists for the detail view
            "warnings": [
                {"code": w.code, "message": w.message, "stage": w.stage.value,
                 "timestamp": w.timestamp, "context": w.context}
                for w in self.warnings
            ],
            "errors": [
                {"code": e.code, "message": e.message, "stage": e.stage.value,
                 "severity": e.severity.value, "retryable": e.retryable,
                 "timestamp": e.timestamp, "context": e.context}
                for e in self.errors
            ],
        }
