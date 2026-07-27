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
            {"id": endpoint_id, "url": proxy_url, "country": country, "source": "env"},
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
            conn = store.init_db(self.path)
            run_id = store.persist_result(result, self.path, conn=conn)
            store.finish_job(
                conn, job_id, status="succeeded", run_id=run_id,
                event_count=result.get("event_count"),
            )
            conn.close()
            logger.info("scraper job %d: succeeded (%s events)",
                        job_id, result.get("event_count"))
        except Exception as exc:  # noqa: BLE001
            logger.exception("scraper job %d failed", job_id)
            conn = store.init_db(self.path)
            store.finish_job(conn, job_id, status="failed", error=str(exc)[:500])
            conn.close()

    async def _scrape(self, job: dict) -> dict:
        skin = _load_skin(job["skin"])
        if job.get("subgames"):
            skin.features["subgames"] = True
        pm, _ = build_proxy_from_env()
        async with BetB2BScraper(skin, proxy_manager=pm, sport=job.get("sport")) as scraper:
            return await scraper.scrape(
                action=job["action"], count=int(job.get("count") or 50),
            )
