"""Telemetry integration for the BetB2B family scraper.

Wires the framework's telemetry system (`src/telemetry/`) into the
BetB2B scraper's lifecycle: bootstrap, feed polling, extraction, and
error handling. All telemetry is optional — the scraper works without
it, but when enabled it emits structured events for monitoring,
debugging, and alerting.

Usage::

    from src.sites.betb2b.telemetry_integration import BetB2BTelemetry

    # Enable telemetry (JSON file storage by default)
    tel = BetB2BTelemetry(skin, output_dir="./telemetry_output")

    # Or disable entirely (zero overhead)
    tel = BetB2BTelemetry.disabled(skin)

    async with BetB2BScraper(skin, ..., telemetry=tel) as scraper:
        result = await scraper.scrape(action="list_live")
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import BetB2BSkinConfig

logger = logging.getLogger(__name__)


@dataclass
class BetB2BTelemetryEvent:
    """A single telemetry datapoint from the betb2b scraper.

    Lightweight dict-serialisable event. Designed to be written to JSON
    files, pushed to InfluxDB, or forwarded to any collector without
    coupling to the framework's heavier ``TelemetryEvent`` pydantic model.
    """

    event_id: str = ""
    timestamp: str = ""
    skin: str = ""
    action: str = ""
    phase: str = ""       # bootstrap | poll | extract | dom_fallback | error
    duration_ms: float = 0.0
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = uuid.uuid4().hex[:16]
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "skin": self.skin,
            "action": self.action,
            "phase": self.phase,
            "duration_ms": round(self.duration_ms, 2),
            "success": self.success,
            **self.metadata,
        }


class BetB2BTelemetry:
    """Telemetry collector for the BetB2B family scraper.

    Emits structured events for every major phase of the scrape
    lifecycle. When ``enabled=False``, all methods are no-ops (zero
    overhead).

    Configuration is fully customizable:
      - ``output_dir``: where to write JSON event logs
      - ``enabled``: master switch (default True)
      - ``snapshot_on_error``: capture a snapshot (via the snapshot system)
        when a scrape phase fails
      - ``max_events_per_file``: rotate event files after this many events
      - ``include_captured_bodies``: whether to include raw feed response
        bodies in the telemetry events (large but useful for replay)
    """

    def __init__(
        self,
        skin: BetB2BSkinConfig,
        *,
        enabled: bool = True,
        output_dir: str = "./data/telemetry/betb2b",
        snapshot_on_error: bool = True,
        max_events_per_file: int = 1000,
        include_captured_bodies: bool = False,
    ) -> None:
        self.skin = skin
        self.enabled = enabled
        self.output_dir = Path(output_dir)
        self.snapshot_on_error = snapshot_on_error
        self.max_events_per_file = max_events_per_file
        self.include_captured_bodies = include_captured_bodies

        self._events: List[BetB2BTelemetryEvent] = []
        self._file_counter = 0
        self._session_id = uuid.uuid4().hex[:12]

        if self.enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Factory
    # ------------------------------------------------------------------ #
    @classmethod
    def disabled(cls, skin: BetB2BSkinConfig) -> "BetB2BTelemetry":
        """Return a no-op telemetry instance (zero overhead)."""
        return cls(skin, enabled=False)

    # ------------------------------------------------------------------ #
    # Recording API — called by BetB2BScraper at each lifecycle point
    # ------------------------------------------------------------------ #
    def record_bootstrap_start(self) -> None:
        if not self.enabled:
            return
        self._current_phase_start = time.monotonic()
        self._emit(phase="bootstrap", action="session_harvest", metadata={
            "domain": self.skin.domain,
            "proxy": self.skin.proxy_endpoint_id or "DIRECT",
        })

    def record_bootstrap_complete(
        self,
        *,
        cookie_count: int,
        session_age_seconds: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        if not self.enabled:
            return
        duration = (time.monotonic() - getattr(self, "_current_phase_start", time.monotonic())) * 1000
        self._emit(
            phase="bootstrap", action="session_harvest",
            success=success, duration_ms=duration,
            metadata={
                "cookie_count": cookie_count,
                "session_age_seconds": round(session_age_seconds, 2),
                "error": error,
            },
        )

    def record_feed_poll(
        self,
        *,
        feed: str,
        root: str,
        status: int,
        body_bytes: int,
        latency_ms: float,
        decoded: bool,
        event_count: int = 0,
    ) -> None:
        if not self.enabled:
            return
        self._emit(
            phase="poll", action=f"{root}_{feed}",
            success=(status >= 200 and status < 300 and decoded),
            duration_ms=latency_ms,
            metadata={
                "feed": feed,
                "root": root,
                "status": status,
                "body_bytes": body_bytes,
                "decoded": decoded,
                "event_count": event_count,
            },
        )

    def record_extraction(
        self,
        *,
        source: str,         # "api" | "dom"
        event_count: int,
        market_count: int,
        duration_ms: float,
        errors: Optional[List[str]] = None,
    ) -> None:
        if not self.enabled:
            return
        self._emit(
            phase="extract", action=f"extraction_{source}",
            success=len(errors or []) == 0,
            duration_ms=duration_ms,
            metadata={
                "source": source,
                "event_count": event_count,
                "market_count": market_count,
                "errors": errors or [],
            },
        )

    def record_dom_fallback(
        self,
        *,
        is_live: bool,
        event_count: int,
        duration_ms: float,
        error: Optional[str] = None,
    ) -> None:
        if not self.enabled:
            return
        self._emit(
            phase="dom_fallback",
            action="dom_fallback_live" if is_live else "dom_fallback_prematch",
            success=error is None,
            duration_ms=duration_ms,
            metadata={
                "is_live": is_live,
                "event_count": event_count,
                "error": error,
            },
        )

    def record_scrape_complete(
        self,
        *,
        action: str,
        total_events: int,
        total_captures: int,
        session_harvested: bool,
        scrape_duration_seconds: float,
        error: Optional[str] = None,
    ) -> None:
        if not self.enabled:
            return
        self._emit(
            phase="scrape_complete", action=action,
            success=error is None,
            duration_ms=scrape_duration_seconds * 1000,
            metadata={
                "total_events": total_events,
                "total_captures": total_captures,
                "session_harvested": session_harvested,
                "scrape_duration_seconds": round(scrape_duration_seconds, 3),
                "error": error,
            },
        )

    def record_snapshot_captured(
        self,
        *,
        snapshot_type: str,
        path: str,
        size_bytes: int,
    ) -> None:
        if not self.enabled:
            return
        self._emit(
            phase="snapshot", action=f"snapshot_{snapshot_type}",
            metadata={
                "snapshot_type": snapshot_type,
                "path": path,
                "size_bytes": size_bytes,
            },
        )

    # ------------------------------------------------------------------ #
    # Snapshot capture — delegates to the framework's snapshot system
    # ------------------------------------------------------------------ #
    async def capture_error_snapshot(
        self,
        page: Any = None,
        *,
        phase: str,
        error: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Capture a snapshot when something goes wrong.

        Uses the framework's ``SnapshotManager`` if available, falls back
        to a minimal JSON capture. Returns the path to the saved artifact,
        or None if snapshots are disabled / unavailable.
        """
        if not self.enabled or not self.snapshot_on_error:
            return None

        snapshot_path = None

        # Try the framework snapshot system first.
        try:
            from src.core.snapshot import (
                SnapshotContext, SnapshotConfig, SnapshotMode,
                get_snapshot_manager,
            )

            manager = get_snapshot_manager()
            context = SnapshotContext(
                site=self.skin.name,
                module="betb2b",
                component=phase,
                session_id=self._session_id,
            )
            config = SnapshotConfig(
                mode=SnapshotMode.SELECTOR,
                capture_html=True,
                capture_screenshot=True,
            )

            # If we have a page, do a full browser snapshot.
            if page is not None:
                bundle = await manager.capture_snapshot(page, context, config)
                if bundle and bundle.html_path:
                    snapshot_path = str(bundle.html_path)
            else:
                # No page — just log the error context as a JSON snapshot.
                snapshot_path = self._write_error_json(phase, error, extra_metadata)

        except Exception as exc:
            logger.debug("Framework snapshot unavailable, using JSON fallback: %s", exc)
            snapshot_path = self._write_error_json(phase, error, extra_metadata)

        if snapshot_path:
            import os
            size = os.path.getsize(snapshot_path) if os.path.exists(snapshot_path) else 0
            self.record_snapshot_captured(
                snapshot_type="error",
                path=snapshot_path,
                size_bytes=size,
            )

        return snapshot_path

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def flush(self) -> Optional[Path]:
        """Write buffered events to a JSON file. Returns the file path."""
        if not self.enabled or not self._events:
            return None

        self._file_counter += 1
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{self.skin.name}_{ts}_{self._file_counter}.json"
        filepath = self.output_dir / filename

        payload = {
            "session_id": self._session_id,
            "skin": self.skin.name,
            "domain": self.skin.domain,
            "event_count": len(self._events),
            "events": [e.to_dict() for e in self._events],
        }

        filepath.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        logger.info(
            "skin=%s flushed %d telemetry events to %s",
            self.skin.name, len(self._events), filepath,
        )

        self._events.clear()
        return filepath

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of collected telemetry for this session."""
        events = self._events
        total = len(events)
        successes = sum(1 for e in events if e.success)
        phases: Dict[str, List[float]] = {}
        for e in events:
            phases.setdefault(e.phase, []).append(e.duration_ms)

        return {
            "session_id": self._session_id,
            "skin": self.skin.name,
            "enabled": self.enabled,
            "total_events": total,
            "successes": successes,
            "failures": total - successes,
            "phases": {
                k: {
                    "count": len(v),
                    "avg_ms": round(sum(v) / len(v), 2) if v else 0,
                    "max_ms": round(max(v), 2) if v else 0,
                }
                for k, v in phases.items()
            },
            "output_dir": str(self.output_dir),
            "files_written": self._file_counter,
        }

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _emit(
        self,
        *,
        phase: str,
        action: str,
        success: bool = True,
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = BetB2BTelemetryEvent(
            skin=self.skin.name,
            action=action,
            phase=phase,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata or {},
        )
        self._events.append(event)
        logger.debug(
            "skin=%s tel phase=%s action=%s ok=%s dur=%.0fms",
            self.skin.name, phase, action, success, duration_ms,
        )

        # Auto-flush when we hit the limit.
        if len(self._events) >= self.max_events_per_file:
            self.flush()

    def _write_error_json(
        self,
        phase: str,
        error: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Fallback: write error context as a JSON file."""
        error_dir = self.output_dir / "snapshots"
        error_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = error_dir / f"{self.skin.name}_{phase}_{ts}.json"

        payload = {
            "session_id": self._session_id,
            "skin": self.skin.name,
            "domain": self.skin.domain,
            "phase": phase,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(extra or {}),
        }
        filepath.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return str(filepath)