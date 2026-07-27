"""Runner logic for the scraper control service (no browser, scrape stubbed).

Drives the real ScraperService queue/claim/persist path with ``_scrape`` faked,
so we exercise start → submit → claim → persist/finish without a live scrape.
"""

from __future__ import annotations

import asyncio

from src.sites.betb2b import store
from src.sites.betb2b.service import ScraperService, build_proxy_from_env


def _fake_result(job: dict) -> dict:
    return {
        "skin": job["skin"], "action": job["action"], "url": "https://x/feed",
        "extracted_at": "2026-07-26T00:00:00+00:00", "success": True,
        "event_count": 0, "scrape_duration_seconds": 0.1,
        "template_version": "1.0.0", "events": [],
    }


async def _drain(svc: ScraperService, path: str, job_id: int, tries: int = 200) -> dict:
    for _ in range(tries):
        conn = store.init_db(path)
        row = dict(store.get_job(conn, job_id))
        conn.close()
        if row["status"] in ("succeeded", "failed"):
            return row
        await asyncio.sleep(0.02)
    return row


def test_scraper_emit_phase_reports_and_is_safe():
    """The scraper's progress hook fires when set, and never breaks a scrape."""
    from src.sites.betb2b.cli.main import _load_skin
    from src.sites.betb2b.scraper import BetB2BScraper

    sc = BetB2BScraper(_load_skin("linebet"))
    seen = []
    sc.progress_cb = seen.append
    sc._emit_phase("bootstrapping")
    sc._emit_phase("scraping events (2/10)")
    assert seen == ["bootstrapping", "scraping events (2/10)"]

    # No callback set → no-op (no raise).
    sc.progress_cb = None
    sc._emit_phase("discovering")

    # A throwing callback is swallowed (progress must never break a scrape).
    def boom(_):
        raise RuntimeError("ui down")

    sc.progress_cb = boom
    sc._emit_phase("enriching")  # must not raise


def test_build_proxy_from_env_none_when_unset(monkeypatch):
    monkeypatch.delenv("BETB2B_PROXY_URL", raising=False)
    assert build_proxy_from_env() == (None, None)


def test_build_proxy_from_env_builds_manager(monkeypatch):
    # Regression: source must be a VALID ProxySource — 'env' raised
    # "'env' is not a valid ProxySource" at job runtime (live on Railway).
    monkeypatch.setenv("BETB2B_PROXY_URL", "http://user:pass@bore.pub:15224")
    monkeypatch.setenv("BETB2B_PROXY_COUNTRY", "KE")
    monkeypatch.setenv("BETB2B_PROXY_ID", "kenya")
    pm, endpoint_id = build_proxy_from_env()
    assert pm is not None and endpoint_id == "kenya"
    ep = pm.get("kenya")                    # resolves without raising
    assert ep is not None and ep.host == "bore.pub" and ep.port == 15224


def test_runner_runs_and_persists(tmp_path, monkeypatch):
    path = str(tmp_path / "odds.db")

    async def fake_scrape(self, job):
        return _fake_result(job)

    monkeypatch.setattr(ScraperService, "_scrape", fake_scrape)

    async def run():
        svc = ScraperService(path)
        await svc.start()
        jid = svc.submit(skin="linebet", action="list_live", sport="basketball")
        row = await _drain(svc, path, jid)
        await svc.stop()
        return row, path

    row, path = asyncio.run(run())
    assert row["status"] == "succeeded", row
    assert row["run_id"] is not None       # persisted a scrape_runs row
    conn = store.init_db(path)
    assert conn.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0] == 1
    conn.close()


def test_runner_marks_failure_with_reason(tmp_path, monkeypatch):
    path = str(tmp_path / "odds.db")

    async def boom(self, job):
        raise RuntimeError("geo/WAF block detected (status=203)")

    monkeypatch.setattr(ScraperService, "_scrape", boom)

    async def run():
        svc = ScraperService(path)
        await svc.start()
        jid = svc.submit(skin="linebet", action="list_live")
        row = await _drain(svc, path, jid)
        await svc.stop()
        return row

    row = asyncio.run(run())
    assert row["status"] == "failed"
    assert "WAF" in (row["error"] or "")   # caller sees a clear reason


def test_runner_surfaces_scrape_level_error(tmp_path, monkeypatch):
    """A scrape that returns an error result (e.g. timeout → 0 events) marks the
    job failed with the reason, not a silent 'succeeded/0'."""
    path = str(tmp_path / "odds.db")

    async def timed_out(self, job):
        r = _fake_result(job)
        r["error"] = "scrape 'list_prematch' timed out after 120.0s"
        r["success"] = False
        return r

    monkeypatch.setattr(ScraperService, "_scrape", timed_out)

    async def run():
        svc = ScraperService(path)
        await svc.start()
        jid = svc.submit(skin="linebet", action="list_prematch")
        row = await _drain(svc, path, jid)
        await svc.stop()
        return row

    row = asyncio.run(run())
    assert row["status"] == "failed"
    assert "timed out" in (row["error"] or "")


def test_single_flight_drains_multiple_jobs(tmp_path, monkeypatch):
    """Two queued jobs both complete (queue drains one-at-a-time)."""
    path = str(tmp_path / "odds.db")
    running = {"now": 0, "max": 0}

    async def fake_scrape(self, job):
        running["now"] += 1
        running["max"] = max(running["max"], running["now"])
        await asyncio.sleep(0.05)
        running["now"] -= 1
        return _fake_result(job)

    monkeypatch.setattr(ScraperService, "_scrape", fake_scrape)

    async def run():
        svc = ScraperService(path)
        await svc.start()
        j1 = svc.submit(skin="linebet", action="list_live")
        j2 = svc.submit(skin="melbet", action="list_prematch")
        r1 = await _drain(svc, path, j1)
        r2 = await _drain(svc, path, j2)
        await svc.stop()
        return r1, r2

    r1, r2 = asyncio.run(run())
    assert r1["status"] == "succeeded" and r2["status"] == "succeeded"
    assert running["max"] == 1             # never two scrapes at once
