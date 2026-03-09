"""
Scrapamoja API – FastAPI application entry point.

Usage
-----
Run from the project root (scrapamoja/):

    uvicorn src.api.main:app --reload --port 8000

Or via the helper script:

    python -m src.api.main
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import failures as failures_router
from src.api.routers import feature_flags as feature_flags_router

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared DB path
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
    project_root = Path(__file__).resolve().parents[2]  # src/api/main.py → root
    db_dir = project_root / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "adaptive.db")


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Tracks active WebSocket connections and broadcasts messages to them."""

    def __init__(self) -> None:
        self._active: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._active.append(ws)
        logger.debug("WebSocket connected. Total: %d", len(self._active))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            try:
                self._active.remove(ws)
            except ValueError:
                pass
        logger.debug("WebSocket disconnected. Total: %d", len(self._active))

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Send *data* (serialised as JSON) to every connected client."""
        if not self._active:
            return
        text = json.dumps(data, default=str)
        dead: list[WebSocket] = []
        async with self._lock:
            targets = list(self._active)
        for ws in targets:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


ws_manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Startup / shutdown lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001
    """Seed demo feature flags on first startup, then yield."""
    _seed_demo_flags()
    logger.info("Scrapamoja API started.")
    yield
    logger.info("Scrapamoja API shutting down.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    application = FastAPI(
        title="Scrapamoja API",
        description=(
            "REST API for the Scrapamoja scraper control plane.\n\n"
            "Provides feature-flag management and selector-failure escalation "
            "endpoints consumed by the React UI at `ui/app/`.\n\n"
            "All data is persisted in the shared adaptive module database at "
            "`data/adaptive.db` (overridable via `ADAPTIVE_DB_PATH`)."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Allow the Vite dev server (port 5173) and any production origin.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    application.include_router(
        feature_flags_router.router,
        prefix="/feature-flags",
        tags=["Feature Flags"],
    )
    application.include_router(
        failures_router.router,
        prefix="/failures",
        tags=["Failures / Escalation"],
    )

    # ── Health check ──────────────────────────────────────────────────────────
    @application.get("/health", tags=["Meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "scrapamoja-api"}

    # ── WebSocket – feature-flag live updates ─────────────────────────────────
    @application.websocket("/ws/feature-flags")
    async def ws_feature_flags(websocket: WebSocket) -> None:
        """
        Bi-directional WebSocket channel for real-time feature-flag updates.

        The UI sends ``{ type: "flag_toggled", data: {...} }`` messages when a
        toggle is performed optimistically; the server echoes the event back to
        all other connected clients so their caches can be invalidated.
        """
        await ws_manager.connect(websocket)
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_text(
                        json.dumps({"type": "error", "detail": "Invalid JSON"})
                    )
                    continue

                msg_type = message.get("type", "")

                if msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

                elif msg_type == "flag_toggled":
                    # Broadcast to *all* clients (including sender) so every
                    # tab invalidates its React-Query cache.
                    await ws_manager.broadcast(
                        {
                            "type": "flag_updated",
                            "data": message.get("data", {}),
                        }
                    )

                else:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "detail": f"Unknown message type: {msg_type!r}",
                            }
                        )
                    )

        except WebSocketDisconnect:
            await ws_manager.disconnect(websocket)

    return application


app = create_app()


# ---------------------------------------------------------------------------
# Demo-data seeding  (feature flags only; failures come from the scraper)
# ---------------------------------------------------------------------------

_DEMO_FLAGS = [
    # (sport, site, enabled, description)
    ("football", None, True, "Global adaptive selectors for all football scraping"),
    ("football", "flashscore", True, "Flashscore-specific football selector overrides"),
    ("basketball", None, True, "Global adaptive selectors for basketball"),
    (
        "basketball",
        "flashscore",
        False,
        "Flashscore basketball — disabled pending review",
    ),
    ("tennis", None, True, "Global adaptive selectors for tennis"),
    ("tennis", "flashscore", True, "Flashscore tennis selectors"),
    ("cricket", None, False, "Cricket scraping — under development"),
    ("rugby", None, True, "Rugby union & league global flag"),
    (
        "adaptive_selector_system",
        None,
        True,
        "Master switch for the adaptive selector engine",
    ),
]


def _seed_demo_flags() -> None:
    """
    Insert demo feature flags on first startup using FeatureFlagService.

    Uses the service's ``create_feature_flag`` which raises ``ValueError``
    if a flag already exists — we catch that and skip silently so re-starts
    are idempotent.
    """
    try:
        from src.selectors.adaptive.services.feature_flag_service import (
            FeatureFlagService,
        )

        svc = FeatureFlagService(db_path=_db_path())

        seeded = 0
        for sport, site, enabled, _desc in _DEMO_FLAGS:
            try:
                svc.create_feature_flag(sport=sport, site=site, enabled=enabled)
                seeded += 1
            except ValueError:
                pass  # already exists — skip

        if seeded:
            logger.info("Demo feature flags seeded: %d new flags.", seeded)
        else:
            logger.info("Demo feature flags already present — nothing to seed.")

    except Exception as exc:
        logger.warning("Demo flag seeding failed (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
