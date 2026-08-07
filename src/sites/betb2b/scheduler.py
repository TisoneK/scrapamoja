"""State-aware betb2b scheduler (ADR-14/15 follow-up).

Runs decoupled scrape passes on their own cadences. Matches flow between passes
by **feed root + DB state**, not by any cross-scraper trigger (ADR-14 — Supabase
is the bus):

  - **scheduled** (~3h): LineFeed discovery → skip matches already scraped
    recently or already kicked off → fetch only new/stale prematch odds.
  - **live** (~15s): LiveFeed discovery → fetch (always; live odds move fast).
  - **results** (~10min): finished-match final scores (ADR-16/20) — the Line/Live
    feeds drop a match once it ends, so this reads statisticfeed `v1/Game` for
    real matches past ~2.5h with no result yet and stamps score/winner on finish.

Single-flight: passes share one lock, so only one scrape runs at a time (one
httpx pool, no self-contention). Browser-free/proxy-free via direct mode.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from . import store
from .cli.main import _load_skin
from .extraction.models import BetB2BScrapeResult
from .scraper import BetB2BScraper

logger = logging.getLogger(__name__)


def _age_seconds(last_seen) -> float:
    """Seconds since `last_seen` (ISO str from SQLite, or datetime from PG)."""
    if last_seen is None:
        return float("inf")
    if isinstance(last_seen, datetime):
        dt = last_seen
    else:
        try:
            dt = datetime.fromisoformat(str(last_seen).replace("Z", "+00:00"))
        except ValueError:
            return float("inf")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds()


class BetB2BScheduler:
    def __init__(
        self, skin_name: str, *, sport: Optional[str] = "basketball",
        db_path: Optional[str] = None, direct: bool = True,
        scheduled_interval: float = 10800.0,   # 3h
        live_interval: float = 15.0,           # 15s
        refresh_window: float = 10800.0,       # re-scrape a prematch match after 3h
        skip_started: bool = True,
        rate_limit_per_minute: int = 120,
        results_interval: float = 600.0,       # 10min — results pass cadence
        result_min_age: float = 9000.0,        # 2.5h — a match this old should be done
        read_only_backoff: float = 900.0,      # 15min — pause when the DB is read-only
    ) -> None:
        self.skin_name = skin_name
        self.sport = sport
        self.db_path = db_path or store_orm_db_path()
        self.direct = direct
        self.scheduled_interval = scheduled_interval
        self.live_interval = live_interval
        self.refresh_window = refresh_window
        self.skip_started = skip_started
        self.rate_limit_per_minute = rate_limit_per_minute
        self.results_interval = results_interval
        self.result_min_age = result_min_age
        self.read_only_backoff = read_only_backoff
        self._scraper: Optional[BetB2BScraper] = None
        self._lock = asyncio.Lock()
        self._stop = asyncio.Event()
        self._ro_warned_at: Dict[str, float] = {}   # per-pass warning throttle

    # -- lifecycle ------------------------------------------------------- #
    async def start(self) -> None:
        skin = _load_skin(self.skin_name)
        self._scraper = BetB2BScraper(
            skin, sport=self.sport, direct=self.direct,
            rate_limit_per_minute=self.rate_limit_per_minute,
            telemetry_enabled=False,
        )
        await self._scraper.start()

    async def run(self) -> None:
        """Run the passes until stop(); blocks."""
        if self._scraper is None:
            await self.start()
        logger.info("scheduler start: skin=%s sport=%s scheduled=%.0fs live=%.0fs results=%.0fs refresh=%.0fs",
                    self.skin_name, self.sport, self.scheduled_interval,
                    self.live_interval, self.results_interval, self.refresh_window)
        # A pass with interval <= 0 is DISABLED. The `live` pass is the dominant
        # data producer (15s polling of constantly-moving odds); disabling it
        # (SCHED_LIVE_INTERVAL=0) is the "scheduled-only" low-storage mode — see
        # ADR-22. Re-enable it (positive interval) once on a paid tier.
        loops = []
        for name, fn, interval in (
            ("scheduled", self._scheduled_pass, self.scheduled_interval),
            ("live", self._live_pass, self.live_interval),
            ("results", self._results_pass, self.results_interval),
        ):
            if interval > 0:
                loops.append(self._loop(name, fn, interval))
            else:
                logger.info("scheduler %s pass DISABLED (interval<=0)", name)
        try:
            await asyncio.gather(*loops)
        finally:
            if self._scraper is not None:
                await self._scraper.close()

    def stop(self) -> None:
        self._stop.set()

    async def _loop(self, name: str, fn, interval: float) -> None:
        while not self._stop.is_set():
            delay = interval
            try:
                async with self._lock:          # single-flight across passes
                    await fn()
            except Exception as exc:             # noqa: BLE001 — a pass must never kill the loop
                if store.is_read_only_error(exc):
                    # Supabase restricts an over-quota project to read-only (the
                    # HTTP layer's 402). Don't hammer it with doomed writes every
                    # `interval`s — back off, warn (throttled), auto-resume when
                    # the DB is writable again. See ADR-21/22.
                    delay = max(interval, self.read_only_backoff)
                    now = time.monotonic()
                    if now - self._ro_warned_at.get(name, 0.0) > 300:
                        logger.warning(
                            "scheduler %s pass: DB is READ-ONLY (Supabase over-quota / "
                            "restricted) — pausing writes, backing off %ds (not retrying at "
                            "%ds). Free up space or upgrade; not hammering the server.",
                            name, int(delay), int(interval))
                        self._ro_warned_at[name] = now
                else:
                    logger.exception("scheduler %s pass failed", name)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass  # interval (or backoff) elapsed → run again

    # -- passes ---------------------------------------------------------- #
    async def _scheduled_pass(self) -> None:
        sc = self._scraper
        pairs = await sc.discover_ids(is_live=False)          # [(id, start_epoch)]
        to_fetch = self._filter_scheduled(pairs)
        logger.info("scheduled: %d discovered → %d to fetch (new/stale, not started)",
                    len(pairs), len(to_fetch))
        if not to_fetch:
            return
        events = await sc.fetch_events(to_fetch, is_live=False)
        await self._enrich(events)
        self._persist("list_prematch", events)

    async def _live_pass(self) -> None:
        sc = self._scraper
        pairs = await sc.discover_ids(is_live=True)            # LiveFeed = live games
        ids = [i for i, _ in pairs]
        if not ids:
            return
        events = await sc.fetch_events(ids, is_live=True)
        await self._enrich(events)
        logger.info("live: %d live matches fetched", len(events))
        self._persist("list_live", events)

    async def _results_pass(self) -> None:
        """Capture finished-match final scores (ADR-16/20). State-driven: query
        the DB for real matches past `result_min_age` with no result yet, fetch
        each via statisticfeed `v1/Game` (by retained stat_game_id, else the event
        id), and write score/winner when `status==3`. No cross-scraper trigger."""
        sc = self._scraper
        conn = store.init_db(self.db_path)
        try:
            pending = store.events_needing_results(conn, min_age_seconds=self.result_min_age)
        finally:
            conn.close()
        if not pending:
            return
        sem = asyncio.Semaphore(sc.concurrency)
        out: List[Tuple[str, dict]] = []

        async def _one(eid: str, stat_id: Optional[str]) -> None:
            async with sem:
                res = await sc.fetch_result(stat_id or eid)   # prefer the retained id
            if res:
                out.append((eid, res))

        await asyncio.gather(*[_one(eid, sid) for eid, sid in pending])

        conn = store.init_db(self.db_path)
        finished = 0
        at = datetime.now(timezone.utc).isoformat()
        try:
            for eid, res in out:
                store.record_result(
                    conn, eid, stat_game_id=res.get("stat_game_id"),
                    score_home=res.get("score_home"), score_away=res.get("score_away"),
                    winner=res.get("winner"), status=res.get("status"), at=at)
                if res.get("status") == 3:
                    finished += 1
        finally:
            conn.close()
        logger.info("results: %d pending → %d checked → %d finished captured",
                    len(pending), len(out), finished)

    # -- helpers --------------------------------------------------------- #
    def _filter_scheduled(self, pairs: List[Tuple[str, object]]) -> List[str]:
        """Skip conditions (deliberate): skip a discovered prematch match if it
        has already kicked off (→ the live pass owns it) or was scraped within
        the refresh window. Keep new + stale."""
        now = time.time()
        conn = store.init_db(self.db_path)
        try:
            last_seen = store.events_last_seen(conn, [i for i, _ in pairs])
        finally:
            conn.close()
        keep: List[str] = []
        for eid, start in pairs:
            try:
                started = self.skip_started and start is not None and float(start) <= now
            except (TypeError, ValueError):
                started = False
            if started:
                continue
            if _age_seconds(last_seen.get(eid)) >= self.refresh_window:
                keep.append(eid)   # new (inf age) or stale
        return keep

    async def _enrich(self, events) -> None:
        sc = self._scraper
        if events and sc.skin.features.get("h2h", True):
            await sc._enrich_with_h2h(events)
        if events and sc.skin.features.get("stats", True):
            await sc._enrich_with_stats(events)

    def _persist(self, action: str, events) -> None:
        sc = self._scraper
        result = BetB2BScrapeResult(
            skin=sc.skin.name, action=action, url=sc.skin.base_url, events=events,
        ).to_dict()
        conn = store.init_db(self.db_path)
        try:
            run_id = store.persist_result(result, self.db_path, conn=conn)
        finally:
            conn.close()
        logger.info("%s: %d events persisted (run %s)", action, len(events), run_id)


def store_orm_db_path() -> str:
    from .service import db_path
    return db_path()
