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
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.api.database import SessionLocal, init_db
from src.api.routers import failures as failures_router
from src.api.routers import feature_flags as feature_flags_router

logger = logging.getLogger(__name__)

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
    """Initialise the database and seed demo data on first run."""
    init_db()
    _seed_demo_data()
    logger.info("Scrapamoja API started. Database initialised.")
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
            "endpoints consumed by the React UI at `ui/app/`."
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
# Demo-data seeding
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

_DEMO_FAILURES = [
    {
        "selector_id": "football.flashscore.match_score",
        "failed_selector": ".event__score--home",
        "recipe_id": "flashscore-football-v2",
        "sport": "football",
        "site": "flashscore",
        "error_type": "not_found",
        "failure_reason": "Element not found after 5 retries — possible DOM restructure",
        "severity": "high",
        "alternatives": [
            {
                "selector": ".smh__participantName--home",
                "strategy": "css",
                "confidence_score": 0.91,
                "blast_radius_affected_count": 3,
                "blast_radius_affected_sports": '["football", "futsal"]',
                "blast_radius_severity": "medium",
                "blast_radius_container_path": ".event__match",
                "highlight_css": ".smh__participantName--home { outline: 2px solid #6366f1; }",
            },
            {
                "selector": "//div[contains(@class,'event__score')][1]",
                "strategy": "xpath",
                "confidence_score": 0.78,
                "blast_radius_affected_count": 1,
                "blast_radius_affected_sports": '["football"]',
                "blast_radius_severity": "low",
                "blast_radius_container_path": ".event__match",
            },
        ],
    },
    {
        "selector_id": "tennis.flashscore.player_name",
        "failed_selector": ".participant__participantName",
        "recipe_id": "flashscore-tennis-v1",
        "sport": "tennis",
        "site": "flashscore",
        "error_type": "stale_element",
        "failure_reason": "StaleElementReferenceException after navigation",
        "severity": "medium",
        "alternatives": [
            {
                "selector": ".participant__participantName--home",
                "strategy": "css",
                "confidence_score": 0.85,
            }
        ],
    },
    {
        "selector_id": "basketball.flashscore.quarter_scores",
        "failed_selector": ".smh__part--home",
        "recipe_id": "flashscore-basketball-v1",
        "sport": "basketball",
        "site": "flashscore",
        "error_type": "timeout",
        "failure_reason": "Element wait timeout exceeded (30s)",
        "severity": "critical",
        "alternatives": [],
        "flagged": True,
        "flag_note": "No alternatives found — needs manual selector research",
    },
]


def _seed_demo_data() -> None:
    """
    Insert demo feature flags and selector failures on first startup.

    Uses ``INSERT OR IGNORE`` semantics: if rows already exist nothing changes,
    so re-starts don't duplicate data.
    """
    from sqlalchemy import select

    from src.api.models import Failure as FailureModel
    from src.api.models import FailureAlternative, FeatureFlag

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # ── Feature flags ─────────────────────────────────────────────────────
        for sport, site, enabled, description in _DEMO_FLAGS:
            stmt = select(FeatureFlag).where(FeatureFlag.sport == sport)
            stmt = (
                stmt.where(FeatureFlag.site.is_(None))
                if site is None
                else stmt.where(FeatureFlag.site == site)
            )
            if db.scalars(stmt).first() is None:
                flag = FeatureFlag(
                    sport=sport,
                    site=site,
                    enabled=enabled,
                    description=description,
                    created_at=now,
                    updated_at=now,
                )
                db.add(flag)

        db.flush()

        # ── Selector failures ─────────────────────────────────────────────────
        for fdata in _DEMO_FAILURES:
            stmt = select(FailureModel).where(
                FailureModel.selector_id == fdata["selector_id"]
            )
            if db.scalars(stmt).first() is None:
                failure = FailureModel(
                    selector_id=fdata["selector_id"],
                    failed_selector=fdata["failed_selector"],
                    recipe_id=fdata.get("recipe_id"),
                    sport=fdata.get("sport"),
                    site=fdata.get("site"),
                    error_type=fdata.get("error_type", "not_found"),
                    failure_reason=fdata.get("failure_reason"),
                    severity=fdata.get("severity", "medium"),
                    flagged=fdata.get("flagged", False),
                    flag_note=fdata.get("flag_note"),
                    flagged_at=now if fdata.get("flagged") else None,
                    timestamp=now,
                )
                db.add(failure)
                db.flush()

                for alt_data in fdata.get("alternatives", []):
                    alt = FailureAlternative(
                        failure_id=failure.id,
                        selector=alt_data["selector"],
                        strategy=alt_data.get("strategy", "css"),
                        confidence_score=alt_data.get("confidence_score", 0.5),
                        blast_radius_affected_count=alt_data.get(
                            "blast_radius_affected_count"
                        ),
                        blast_radius_affected_sports=alt_data.get(
                            "blast_radius_affected_sports"
                        ),
                        blast_radius_severity=alt_data.get("blast_radius_severity"),
                        blast_radius_container_path=alt_data.get(
                            "blast_radius_container_path"
                        ),
                        highlight_css=alt_data.get("highlight_css"),
                        is_custom=False,
                        created_at=now,
                    )
                    db.add(alt)

        db.commit()
        logger.info("Demo data seeded successfully.")

    except Exception as exc:
        db.rollback()
        logger.warning("Demo data seeding failed (non-fatal): %s", exc)
    finally:
        db.close()


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
