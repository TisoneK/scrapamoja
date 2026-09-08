"""State-aware scheduler logic (no network) — skip conditions + age.

The passes themselves need live feeds (verified live: pass 1 fetches 117 new,
pass 2 skips all 117 as fresh). These tests pin the deterministic filter logic.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from src.sites.betb2b import store, store_orm
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
    from src.sites.betb2b import store, store_orm

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


def test_deploy_configs_default_live_off():
    """The Railway worker boots with the live pass DISABLED by default.

    The live pass (15s odds polling) is the dominant data producer — an
    accidentally-on default re-fills the database past the Supabase free tier
    within weeks. The config-file default was once `15` while the Procfile said
    `0`; the deployed worker uses the config file, so live ran unchecked. Pin
    every deploy surface to live-off unless deliberately overridden by
    SCHED_LIVE_INTERVAL in the environment.
    """
    import json
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parents[4]

    worker = json.loads((repo / "railway.worker.json").read_text(encoding="utf-8"))
    cmd = worker["deploy"]["startCommand"]
    m = re.search(r"--live-interval \$\{SCHED_LIVE_INTERVAL:-(\d+(?:\.\d+)?)\}", cmd)
    assert m, f"worker startCommand has no --live-interval fallback: {cmd}"
    assert float(m.group(1)) == 0.0, (
        "railway.worker.json defaults SCHED_LIVE_INTERVAL to "
        f"{m.group(1)} — must default to 0 (live pass off)"
    )

    procfile = (repo / "Procfile").read_text(encoding="utf-8")
    worker_line = next(
        ln for ln in procfile.splitlines() if ln.startswith("worker:")
    )
    m = re.search(r"--live-interval \$\{SCHED_LIVE_INTERVAL:-(\d+(?:\.\d+)?)\}", worker_line)
    assert m, f"Procfile worker line has no --live-interval fallback: {worker_line}"
    assert float(m.group(1)) == 0.0, (
        "Procfile defaults SCHED_LIVE_INTERVAL to "
        f"{m.group(1)} — must default to 0 (live pass off)"
    )


# --------------------------------------------------------------------------- #
# Quota monitor (hosted-store size) + retention prune                          #
# --------------------------------------------------------------------------- #
def test_quota_evaluate_levels():
    from src.sites.betb2b import quota

    MB = 1024 * 1024
    # unknown size → unknown level
    assert quota.evaluate(None) is None
    ok = quota.evaluate(100 * MB, limit=500)
    assert ok["level"] == "ok" and not ok["over"]
    warn = quota.evaluate(0.81 * 500 * MB, limit=500)
    assert warn["level"] == "warn" and not warn["over"]
    crit = quota.evaluate(0.93 * 500 * MB, limit=500)
    assert crit["level"] == "critical" and not crit["over"]
    over = quota.evaluate(1.2 * 500 * MB, limit=500)
    assert over["level"] == "critical" and over["over"]
    # thresholds are overrideable
    assert quota.evaluate(0.5 * 100 * MB, limit=100, warn=40, critical=45)["level"] == "critical"


def test_db_bytes_sqlite_and_prune_roundtrip(tmp_path):
    """db_bytes works on a SQLite store; prune_expired deletes aged fact rows
    (odds tick history first among them) and KEEPS the events row (results)."""
    db = str(tmp_path / "q.db")
    conn = store.init_db(db)
    res = {
        "skin": "linebet", "action": "list_prematch", "url": "u",
        "extracted_at": datetime.now(timezone.utc).isoformat(), "success": True,
        "event_count": 1, "scrape_duration_seconds": 1.0, "template_version": "1.0.0",
        "events": [{
            "event_id": "OLD1", "sport": "basketball", "sport_id": 3,
            "competition": "L", "home": "A", "away": "B", "status": "scheduled",
            "is_live": False,
            "start_time": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "markets": [{"name": "1x2", "market_type": "1x2", "raw_g": 1,
                         "scope": "FULL_MATCH",
                         "selections": [{"name": "1", "price": 1.5, "is_suspended": False}]}],
        }],
    }
    store.persist_result(res, db, conn=conn)
    assert store.db_bytes(conn) and store.db_bytes(conn) > 0

    # nothing is older than the prune window at 60 days → no deletions
    counts = store.prune_counts(conn, days=60)
    assert sum(counts.values()) == 0
    # at 7 days the aged rows are counted and then deleted
    counts7 = store.prune_counts(conn, days=7)
    assert counts7["odds_snapshots"] >= 1 and counts7["events"] == 1
    pruned = store.prune_expired(conn, days=7)
    assert pruned["odds_snapshots"] == counts7["odds_snapshots"]
    assert pruned["events_pruned"] == 1
    # the event survives with its dimension rows; only its fact history goes
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM odds_snapshots").fetchone()[0] == 0
    conn.close()


def test_quota_pass_prunes_when_critical(tmp_path, monkeypatch, caplog):
    """The scheduler's quota pass prunes aged fact history only at the
    critical level; ok/warn just log. (Auto-retention is what keeps the
    hosted store under the platform's size limit.)"""
    import asyncio
    import logging

    from src.sites.betb2b import quota

    db = str(tmp_path / "qp.db")
    conn = store.init_db(db)
    res = {
        "skin": "linebet", "action": "list_prematch", "url": "u",
        "extracted_at": datetime.now(timezone.utc).isoformat(), "success": True,
        "event_count": 1, "scrape_duration_seconds": 1.0, "template_version": "1.0.0",
        "events": [{
            "event_id": "OLD1", "sport": "basketball", "sport_id": 3,
            "competition": "L", "home": "A", "away": "B", "status": "scheduled",
            "is_live": False,
            "start_time": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "markets": [{"name": "1x2", "market_type": "1x2", "raw_g": 1,
                         "scope": "FULL_MATCH",
                         "selections": [{"name": "1", "price": 1.5, "is_suspended": False}]}],
        }],
    }
    store.persist_result(res, db, conn=conn)
    conn.close()

    s = BetB2BScheduler("linebet", db_path=db, scheduled_interval=0,
                        live_interval=0, results_interval=0, quota_interval=0)

    size_mb = {"v": 30.0}

    class _Conn:
        def close(self):
            pass

    def _fake_connect():
        return _Conn()

    def _fake_db_bytes(_conn):
        return int(size_mb["v"] * 1024 * 1024)

    def _fake_prune_expired(_conn, *, days, batch, commit=True):
        s.pruned_args = (days, batch)
        return {"odds_snapshots": 42, "events_pruned": 3}

    monkeypatch.setattr(store_orm, "connect", _fake_connect)
    monkeypatch.setattr(store_orm, "db_bytes", _fake_db_bytes)
    monkeypatch.setattr(store_orm, "prune_expired", _fake_prune_expired)

    # warn level → no prune
    size_mb["v"] = 0.85 * quota.limit_mb()
    with caplog.at_level(logging.INFO):
        asyncio.run(s._quota_pass())
    assert not hasattr(s, "pruned_args")

    # critical level → prune with the env-configured window/batch
    size_mb["v"] = 0.95 * quota.limit_mb()
    with caplog.at_level(logging.INFO):
        asyncio.run(s._quota_pass())
    assert s.pruned_args == (quota.prune_days(), quota.prune_batch())
    assert any("quota prune" in r.getMessage() for r in caplog.records)


def test_quota_pass_tolerates_unreachable_primary(tmp_path, monkeypatch, caplog):
    """A dead primary must not kill the quota pass (fallback may own writes)."""
    import asyncio
    import logging

    from src.sites.betb2b import store_orm

    db = str(tmp_path / "qd.db")
    store.init_db(db).close()
    s = BetB2BScheduler("linebet", db_path=db, scheduled_interval=0,
                        live_interval=0, results_interval=0, quota_interval=0)

    def _boom():
        raise ConnectionError("no route to host")

    monkeypatch.setattr(store_orm, "connect", _boom)
    with caplog.at_level(logging.WARNING):
        asyncio.run(s._quota_pass())   # must not raise
    assert any("unreachable" in r.getMessage() for r in caplog.records)
