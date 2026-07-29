"""State-aware betb2b scheduler (ADR-14/15 follow-up).

Runs decoupled scrape passes on their own cadences. Matches flow between passes
by **feed root + DB state**, not by any cross-scraper trigger (ADR-14 — Supabase
is the bus):

  - **scheduled** (~3h): LineFeed discovery → skip matches already scraped
    recently or already kicked off → fetch only new/stale prematch odds.
  - **live** (~15s): LiveFeed discovery → fetch (always; live odds move fast).
  - **results** (finished-match final scores): TODO — the Line/Live feeds drop a
    match once it ends, so this needs the results/history endpoint (research).

Single-flight: passes share one lock, so only one scrape runs at a time (one
httpx pool, no self-contention). Browser-free/proxy-free via direct mode.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import List, Optional, Tuple

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
        self._scraper: Optional[BetB2BScraper] = None
        self._lock = asyncio.Lock()
        self._stop = asyncio.Event()

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
        try:
            await asyncio.gather(
                self._loop("scheduled", self._scheduled_pass, self.scheduled_interval),
                self._loop("live", self._live_pass, self.live_interval),
                self._loop("results", self._results_pass, self.results_interval),
            )
        finally:
            if self._scraper is not None:
                await self._scraper.close()

    def stop(self) -> None:
        self._stop.set()

    async def _loop(self, name: str, fn, interval: float) -> None:
        while not self._stop.is_set():
            try:
                async with self._lock:          # single-flight across passes
                    await fn()
            except Exception:                    # noqa: BLE001 — a pass must never kill the loop
                logger.exception("scheduler %s pass failed", name)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass  # interval elapsed → run again

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
