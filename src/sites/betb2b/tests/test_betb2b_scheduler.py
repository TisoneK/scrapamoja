"""State-aware scheduler logic (no network) — skip conditions + age.

The passes themselves need live feeds (verified live: pass 1 fetches 117 new,
pass 2 skips all 117 as fresh). These tests pin the deterministic filter logic.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from src.sites.betb2b import store
from src.sites.betb2b.scheduler import BetB2BScheduler, _age_seconds


def test_age_seconds_handles_str_datetime_none():
    now = datetime.now(timezone.utc)
    assert _age_seconds(None) == float("inf")
    assert _age_seconds("garbage") == float("inf")
    assert _age_seconds((now - timedelta(hours=1)).isoformat()) > 3500
    assert _age_seconds(now - timedelta(seconds=5)) < 60
    # naive datetime is treated as UTC, not crash
    assert _age_seconds(datetime.utcnow() - timedelta(seconds=5)) < 120


def _seed_event(db, event_id):
    conn = store.init_db(db)
    res = {
        "skin": "linebet", "action": "list_prematch", "url": "u",
        "extracted_at": datetime.now(timezone.utc).isoformat(), "success": True,
        "event_count": 1, "scrape_duration_seconds": 1.0, "template_version": "1.0.0",
        "events": [{"event_id": event_id, "sport": "basketball", "sport_id": 3,
                    "competition": "L", "home": "A", "away": "B", "status": "scheduled",
                    "is_live": False}],
    }
    store.persist_result(res, db, conn=conn)
    conn.close()


def test_filter_scheduled_keeps_new_skips_fresh_and_started(tmp_path):
    db = str(tmp_path / "sched.db")
    store.init_db(db).close()
    _seed_event(db, "SEEN")   # just scraped → fresh

    s = BetB2BScheduler("linebet", db_path=db, refresh_window=3600, skip_started=True)
    future, past = time.time() + 7200, time.time() - 100
    pairs = [
        ("SEEN", future),   # in DB, fresh → skip
        ("NEW", future),    # not in DB → keep
        ("STARTED", past),  # start time passed → skip (live pass owns it)
    ]
    assert s._filter_scheduled(pairs) == ["NEW"]


def test_filter_scheduled_refetches_stale(tmp_path, monkeypatch):
    db = str(tmp_path / "sched2.db")
    store.init_db(db).close()
    _seed_event(db, "OLD")

    # refresh_window = 0 → even a just-seen match is "stale" and re-fetched
    s = BetB2BScheduler("linebet", db_path=db, refresh_window=0, skip_started=True)
    assert s._filter_scheduled([("OLD", time.time() + 7200)]) == ["OLD"]


def test_filter_scheduled_can_disable_skip_started(tmp_path):
    db = str(tmp_path / "sched3.db")
    store.init_db(db).close()
    s = BetB2BScheduler("linebet", db_path=db, refresh_window=3600, skip_started=False)
    # started + new → kept when skip_started is off
    assert s._filter_scheduled([("X", time.time() - 100)]) == ["X"]


def test_scheduler_skips_live_pass_when_disabled(tmp_path):
    """live_interval<=0 → the live pass (the storage firehose) is not run;
    scheduled still runs. The 'scheduled-only' low-storage mode (ADR-22)."""
    import asyncio

    db = str(tmp_path / "s.db")
    store.init_db(db).close()
    s = BetB2BScheduler("linebet", db_path=db, scheduled_interval=3600,
                        live_interval=0, results_interval=0)

    class _DummyScraper:
        async def close(self):
            pass

    s._scraper = _DummyScraper()  # non-None → run() skips start() (no network)
    calls = []

    async def _sched():
        calls.append("scheduled")
        s.stop()            # one iteration then unwind

    async def _live():
        calls.append("live")

    s._scheduled_pass = _sched
    s._live_pass = _live
    asyncio.run(asyncio.wait_for(s.run(), timeout=5))
    assert "scheduled" in calls
    assert "live" not in calls


def test_is_read_only_error_detects_25006():
    """Detect the read-only-transaction signal (SQLSTATE 25006 / message /
    SQLAlchemy .orig wrapping); ignore unrelated errors."""
    from src.sites.betb2b import store

    class _E(Exception):
        def __init__(self, msg, sqlstate=None):
            super().__init__(msg)
            self.sqlstate = sqlstate

    assert store.is_read_only_error(_E("cannot execute INSERT in a read-only transaction"))
    assert store.is_read_only_error(_E("boom", sqlstate="25006"))

    class _Wrap(Exception):
        def __init__(self, orig):
            super().__init__("wrapped")
            self.orig = orig

    assert store.is_read_only_error(_Wrap(_E("boom", sqlstate="25006")))
    assert not store.is_read_only_error(_E("some unrelated error"))
    assert not store.is_read_only_error(None)


def test_scheduler_backs_off_and_warns_on_read_only(tmp_path, caplog):
    """A read-only write does NOT crash the loop or hammer — it logs a throttled
    warning and backs off (ADR-21/22)."""
    import asyncio
    import logging

    db = str(tmp_path / "ro.db")
    store.init_db(db).close()
    s = BetB2BScheduler("linebet", db_path=db, scheduled_interval=3600,
                        live_interval=0, results_interval=0, read_only_backoff=3600)

    class _Dummy:
        async def close(self):
            pass

    s._scraper = _Dummy()

    class _RO(Exception):
        sqlstate = "25006"

    async def _sched():
        s.stop()  # unwind after this iteration
        raise _RO("cannot execute INSERT in a read-only transaction")

    s._scheduled_pass = _sched
    with caplog.at_level(logging.WARNING):
        asyncio.run(asyncio.wait_for(s.run(), timeout=5))
    assert any("READ-ONLY" in r.getMessage() for r in caplog.records)
