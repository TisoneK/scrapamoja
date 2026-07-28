"""Background scrape-job runner for the remote-control API.

A single-flight, DB-driven job runner: the control API enqueues jobs into the
``scraper_jobs`` table; this service claims and runs them **one at a time**
(one Chromium bootstrap at a time — ADR-1's memory concern) inside the API
process, persisting results to the betb2b odds store.

Deploy note: run the web service with ``GUNICORN_WORKERS=1`` so a single runner
owns the queue. The DB claim (``store.claim_next_job``) is the single-flight
guard regardless, but one worker keeps it deterministic and avoids parallel
browser bootstraps competing for memory.

The proxy is read from ``BETB2B_PROXY_*`` env (same contract as the CLI). If no
proxy is configured — or the egress IP is WAF-blocked — the scrape fails and
the job is marked ``failed`` with the error, so the caller sees a clear status
rather than a hang.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse

from . import store
from .cli.main import _load_skin
from .scraper import BetB2BScraper

logger = logging.getLogger(__name__)

DB_PATH_ENV = "BETB2B_DB_PATH"
DEFAULT_DB_PATH = "data/betb2b/odds.db"

# A full prematch scrape (bootstrap + per-league GetChampZip + per-match
# GetGameZip, rate-limited) runs ~135–165s — well over BetB2BScraper.scrape's
# 120s default, which would time out and discard everything (0 events). Give
# background jobs a realistic cap; override with BETB2B_SCRAPE_TIMEOUT.
SCRAPE_TIMEOUT_ENV = "BETB2B_SCRAPE_TIMEOUT"
DEFAULT_SCRAPE_TIMEOUT = 300.0


def db_path() -> str:
    return os.environ.get(DB_PATH_ENV, DEFAULT_DB_PATH)


def build_proxy_from_env() -> Tuple[Optional[object], Optional[str]]:
    """Build a ProxyManager from ``BETB2B_PROXY_*`` env, or ``(None, None)``.

    Same env contract as the CLI: ``BETB2B_PROXY_URL`` (may embed creds, or
    supply ``BETB2B_PROXY_USER``/``PASS`` separately), ``BETB2B_PROXY_COUNTRY``,
    ``BETB2B_PROXY_ID``, ``BETB2B_PROXY_DOMAIN``.
    """
    proxy_url = os.environ.get("BETB2B_PROXY_URL")
    if not proxy_url:
        return None, None

    user = os.environ.get("BETB2B_PROXY_USER")
    pw = os.environ.get("BETB2B_PROXY_PASS")
    if user and pw and "@" not in proxy_url:
        p = urlparse(proxy_url)
        netloc = f"{user}:{pw}@{p.hostname}"
        if p.port:
            netloc += f":{p.port}"
        proxy_url = urlunparse(p._replace(netloc=netloc))

    country = os.environ.get("BETB2B_PROXY_COUNTRY", "")
    endpoint_id = os.environ.get("BETB2B_PROXY_ID", "proxy")
    domain = os.environ.get("BETB2B_PROXY_DOMAIN", "*")

    from src.network.proxy import build_proxy_manager

    pm = build_proxy_manager({
        "endpoints": [
            # source must be a valid ProxySource; an env-supplied proxy is "manual".
            {"id": endpoint_id, "url": proxy_url, "country": country, "source": "manual"},
        ],
        "routing": [{"pattern": f"*.{domain}", "target": endpoint_id}],
    })
    return pm, endpoint_id


class ScraperService:
    """Owns the scrape-job queue: enqueue, then run claimed jobs one at a time."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or db_path()
        self._wake = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._stopping = False

    # -- lifecycle ------------------------------------------------------- #
    async def start(self) -> None:
        conn = store.init_db(self.path)
        orphans = store.reset_orphan_jobs(conn)  # a crash mid-run left 'running' rows
        conn.close()
        if orphans:
            logger.warning("scraper service: reset %d orphaned running job(s)", orphans)
        self._stopping = False
        self._wake.set()  # process any jobs already 'queued' from before restart
        self._task = asyncio.create_task(self._consume(), name="scraper-job-runner")
        logger.info("scraper service started (db=%s)", self.path)

    async def stop(self) -> None:
        self._stopping = True
        self._wake.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("scraper service stopped")

    # -- public API ------------------------------------------------------ #
    def submit(
        self, *, skin: str, action: str, sport: Optional[str] = None,
        subgames: bool = False, count: Optional[int] = None,
        created_by: Optional[str] = None,
    ) -> int:
        """Create a queued job and wake the runner. Returns the job_id."""
        conn = store.init_db(self.path)
        job_id = store.create_job(
            conn, skin=skin, action=action, sport=sport,
            subgames=subgames, count=count, created_by=created_by,
        )
        conn.close()
        self._wake.set()
        return job_id

    # -- internals ------------------------------------------------------- #
    async def _consume(self) -> None:
        while not self._stopping:
            await self._wake.wait()
            self._wake.clear()
            # Drain every claimable job, one at a time (single-flight).
            while not self._stopping:
                conn = store.init_db(self.path)
                job = store.claim_next_job(conn)
                conn.close()
                if job is None:
                    break
                await self._run_job(dict(job))

    async def _run_job(self, job: dict) -> None:
        job_id = job["job_id"]
        logger.info("scraper job %d: running skin=%s action=%s sport=%s",
                    job_id, job["skin"], job["action"], job.get("sport"))
        try:
            result = await self._scrape(job)
            # persist_result on Postgres is SYNCHRONOUS (psycopg) and fires many
            # network round-trips — run it off the event loop so it can't block
            # the uvicorn heartbeat (→ gunicorn WORKER TIMEOUT / SIGABRT) or stall
            # the API. The scrape itself is async and stays on the loop.
            await asyncio.to_thread(self._persist_and_finish, job_id, result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("scraper job %d failed", job_id)
            await asyncio.to_thread(self._fail_job, job_id, str(exc)[:500])

    def _persist_and_finish(self, job_id: int, result: dict) -> None:
        """Blocking DB work — always called via asyncio.to_thread."""
        conn = store.init_db(self.path)
        try:
            store.update_job_phase(conn, job_id, "persisting")
            run_id = store.persist_result(result, self.path, conn=conn)
            # A scrape-level error (e.g. timeout) yields an empty result — mark
            # the job failed with that reason instead of a silent "succeeded/0".
            scrape_error = result.get("error")
            if scrape_error:
                store.finish_job(conn, job_id, status="failed", run_id=run_id,
                                 event_count=result.get("event_count"),
                                 error=str(scrape_error)[:500])
                logger.warning("scraper job %d: scrape error — %s", job_id, scrape_error)
            else:
                store.finish_job(conn, job_id, status="succeeded", run_id=run_id,
                                 event_count=result.get("event_count"))
                logger.info("scraper job %d: succeeded (%s events)",
                            job_id, result.get("event_count"))
        finally:
            conn.close()

    def _fail_job(self, job_id: int, error: str) -> None:
        conn = store.init_db(self.path)
        try:
            store.finish_job(conn, job_id, status="failed", error=error)
        finally:
            conn.close()

    async def _scrape(self, job: dict) -> dict:
        skin = _load_skin(job["skin"])
        if job.get("subgames"):
            skin.features["subgames"] = True
        # ADR-15: BETB2B_DIRECT=1 makes the deployed scraper run browser+proxy-free
        # (GetSportsZip discovery). Lets Railway drop the proxy entirely for odds.
        if os.environ.get("BETB2B_DIRECT", "").lower() in ("1", "true", "yes"):
            skin.features["direct"] = True
        pm, _ = build_proxy_from_env()
        job_id = job["job_id"]

        def _write_phase(phase: str) -> None:
            conn = store.init_db(self.path)
            try:
                store.update_job_phase(conn, job_id, phase)
            finally:
                conn.close()

        timeout = float(os.environ.get(SCRAPE_TIMEOUT_ENV, DEFAULT_SCRAPE_TIMEOUT))
        async with BetB2BScraper(skin, proxy_manager=pm, sport=job.get("sport")) as scraper:
            scraper.progress_cb = _write_phase   # live phase → scraper_jobs.phase
            return await scraper.scrape(
                action=job["action"], count=int(job.get("count") or 50),
                timeout_seconds=timeout,
            )
