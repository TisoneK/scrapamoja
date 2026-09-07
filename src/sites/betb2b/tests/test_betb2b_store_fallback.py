"""Local fallback store (store_fallback) — failover, outbox, recovery.

The "primary" in these tests is a real SQLite-backed ORM store via
``DATABASE_URL`` (the same code path Postgres runs); failures are injected by
patching ``store_orm`` write functions to raise a read-only-transaction error
(SQLSTATE 25006) — exactly what Supabase returns when a project is over
quota. No network.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from src.sites.betb2b import store, store_fallback, store_orm


# --------------------------------------------------------------------------- #
# fixtures + helpers
# --------------------------------------------------------------------------- #
class ReadOnlyError(Exception):
    """Psycopg's read-only-transaction failure, shaped like the real thing."""

    def __init__(self, msg="cannot execute INSERT in a read-only transaction"):
        super().__init__(msg)
        self.sqlstate = "25006"


@pytest.fixture()
def fb_env(tmp_path, monkeypatch):
    """A sqlite 'primary' via DATABASE_URL + clean fallback module state."""
    primary = tmp_path / "primary.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{primary}")
    monkeypatch.setenv("BETB2B_FALLBACK_DB_PATH", str(tmp_path / "mirror.db"))
    monkeypatch.setenv("BETB2B_FALLBACK_PROBE_SECONDS", "0")
    store_orm._engines.clear()
    store_fallback._reset_for_tests()
    yield tmp_path
    store_orm._engines.clear()
    store_fallback._reset_for_tests()


def _result(skin="linebet", event_id="EV1", **extra):
    return {
        "skin": skin, "action": "list_prematch", "url": "https://x",
        "extracted_at": datetime.now(timezone.utc).isoformat(), "success": True,
        "event_count": 1, "scrape_duration_seconds": 1.0, "template_version": "1",
        "events": [{"event_id": event_id, "sport": "basketball", "sport_id": 3,
                    "competition": "NBA", "home": "A", "away": "B",
                    "status": "scheduled", "is_live": False,
                    "markets": [{"name": "1x2", "market_type": "1x2", "raw_g": 1,
                                 "selections": [
                                     {"name": "1", "price": 1.5, "is_suspended": False},
                                     {"name": "2", "price": 2.5, "is_suspended": False}]}],
                    **extra}],
    }


def _mirror_rows(tmp_path, sql, params=()):
    conn = sqlite3.connect(str(tmp_path / "mirror.db"))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _primary_count(table):
    conn = store_orm.connect()
    from sqlalchemy import text
    try:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# classification
# --------------------------------------------------------------------------- #
def test_classify_failure_matrix():
    assert store_fallback.classify_failure(ReadOnlyError()) == "read_only"
    assert store_fallback.classify_failure(
        Exception("cannot execute INSERT in a read-only transaction")) == "read_only"
    assert store_fallback.classify_failure(ConnectionRefusedError()) == "connectivity"
    assert store_fallback.classify_failure(Exception("connection refused")) == "connectivity"
    assert store_fallback.classify_failure(Exception("too many connections")) == "connectivity"

    class _E(Exception):
        sqlstate = "57P03"

    assert store_fallback.classify_failure(_E("cannot connect now")) == "connectivity"

    class _Wrap(Exception):
        orig = ReadOnlyError()

    assert store_fallback.classify_failure(_Wrap("wrapped")) == "read_only"

    # Not eligible: our bugs and request problems fail loudly.
    assert store_fallback.classify_failure(ValueError("bad data")) is None

    class _Integrity(Exception):
        sqlstate = "23505"

    assert store_fallback.classify_failure(_Integrity("duplicate key")) is None

    class _Auth(Exception):
        sqlstate = "28P01"

    assert store_fallback.classify_failure(_Auth("password authentication failed")) is None
    assert store_fallback.classify_failure(None) is None


# --------------------------------------------------------------------------- #
# failover on write
# --------------------------------------------------------------------------- #
def test_write_failover_queues_and_mirrors(fb_env, monkeypatch):
    def _boom(conn, result):
        raise ReadOnlyError()

    monkeypatch.setattr(store_orm, "persist_result", _boom)
    run_id = store.persist_result(_result(), fb_env / "ignored.db")

    assert isinstance(run_id, int) and run_id > 0
    assert store_fallback.active()
    st = store_fallback.status()
    assert st["active"] and st["reason"] == "read_only"
    # the event landed in the mirror (full schema, not just the outbox)
    ev = _mirror_rows(fb_env, "SELECT event_id, home_name FROM events")
    assert ev and ev[0]["event_id"] == "EV1"
    # and the payload is queued for replay
    outbox = _mirror_rows(fb_env, "SELECT kind, payload FROM fallback_outbox")
    assert len(outbox) == 1 and outbox[0]["kind"] == "persist"
    assert '"event_id": "EV1"' in outbox[0]["payload"] or "'event_id': 'EV1'" in outbox[0]["payload"]


def test_failover_mode_serves_reads_from_mirror(fb_env, monkeypatch):
    monkeypatch.setattr(store_orm, "persist_result", lambda conn, r: (_ for _ in ()).throw(ReadOnlyError()))
    store.persist_result(_result(), None)

    conn = store.init_db(None)          # mode active → mirror, not the primary
    assert isinstance(conn, sqlite3.Connection)
    seen = store.events_last_seen(conn, ["EV1", "NOPE"])
    conn.close()
    assert "EV1" in seen and "NOPE" not in seen


def test_connect_failover_hands_out_mirror(fb_env, monkeypatch):
    def _unreachable():
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr(store_orm, "connect", _unreachable)
    conn = store.init_db(fb_env / "ignored.db")
    assert isinstance(conn, sqlite3.Connection)
    assert store_fallback.status()["reason"] == "connectivity"
    conn.close()


def test_record_result_failover_queues_result_op(fb_env, monkeypatch):
    monkeypatch.setattr(store_orm, "record_result",
                        lambda conn, *a, **k: (_ for _ in ()).throw(ReadOnlyError()))
    conn = store.init_db(None)          # primary conn (mode not yet active)
    store.record_result(conn, "EV1", stat_game_id="SG1", score_home=10,
                        score_away=8, winner=1, status=3,
                        at=datetime.now(timezone.utc).isoformat())
    conn.close()
    assert store_fallback.active()
    outbox = _mirror_rows(fb_env, "SELECT kind, payload FROM fallback_outbox")
    assert len(outbox) == 1 and outbox[0]["kind"] == "result"
    assert '"status": 3' in outbox[0]["payload"]


# --------------------------------------------------------------------------- #
# recovery: probe → flip back → drain
# --------------------------------------------------------------------------- #
def test_recovery_replays_outbox_into_primary(fb_env, monkeypatch):
    real_persist = store_orm.persist_result

    # 1) primary write fails → fallback
    def _boom(conn, result):
        raise ReadOnlyError()

    monkeypatch.setattr(store_orm, "persist_result", _boom)
    store.persist_result(_result(event_id="EV1"), None)
    store.persist_result(_result(event_id="EV2", skin="melbet"), None)
    assert store_fallback.active()
    assert len(_mirror_rows(fb_env, "SELECT seq FROM fallback_outbox")) == 2

    # 2) primary recovers → probe flips back and drains in order
    monkeypatch.setattr(store_orm, "persist_result", real_persist)
    store_fallback.maybe_probe_and_drain()

    assert not store_fallback.active()
    assert _mirror_rows(fb_env, "SELECT seq FROM fallback_outbox") == []
    assert _primary_count("events") == 2
    assert _primary_count("odds_snapshots") == 4   # 2 selections × 2 events
    st = store_fallback.status()
    assert st["drained"] == 2
    assert st["flips"] >= 1   # ≥: probes elsewhere in the suite may have flipped too


def test_recovery_keeps_fallback_when_primary_still_read_only(fb_env, monkeypatch):
    def _boom(conn, result):
        raise ReadOnlyError()

    # Both seams fail while read-only: the probe's INSERT and persist_result.
    monkeypatch.setattr(store_fallback, "_probe_primary_writable", lambda: False)
    monkeypatch.setattr(store_orm, "persist_result", _boom)
    store.persist_result(_result(), None)
    assert store_fallback.active()

    store_fallback._state["_last_probe_at"] = 0.0   # re-arm the throttle
    store_fallback.maybe_probe_and_drain()          # probe fails → stay local
    assert store_fallback.active()
    assert len(_mirror_rows(fb_env, "SELECT seq FROM fallback_outbox")) == 1


def test_drain_stops_and_reactivates_on_primary_failure(fb_env, monkeypatch):
    """The primary degrades again mid-drain (e.g. quota returns between probe
    and replay): stop, keep the undrained rows, go back to fallback."""
    real_persist = store_orm.persist_result

    def _boom(conn, result):
        raise ReadOnlyError()

    monkeypatch.setattr(store_orm, "persist_result", _boom)
    store.persist_result(_result(event_id="A"), None)
    store.persist_result(_result(event_id="B"), None)
    assert store_fallback.active() and len(_mirror_rows(fb_env, "SELECT seq FROM fallback_outbox")) == 2

    calls = {"n": 0}

    def _flaky(conn, result):
        calls["n"] += 1
        if calls["n"] == 1:
            return real_persist(conn, result)   # first replay lands…
        raise ReadOnlyError()                    # …then the primary breaks again

    monkeypatch.setattr(store_orm, "persist_result", _flaky)
    store_fallback.maybe_probe_and_drain()
    assert store_fallback.active()              # back in fallback mode
    remaining = _mirror_rows(fb_env, "SELECT seq FROM fallback_outbox")
    assert len(remaining) == 1                  # the not-yet-replayed payload stays
    assert _primary_count("events") == 1


def test_probe_throttle_blocks_hammering(fb_env, monkeypatch):
    monkeypatch.setenv("BETB2B_FALLBACK_PROBE_SECONDS", "9999")
    monkeypatch.setattr(store_orm, "persist_result",
                        lambda conn, r: (_ for _ in ()).throw(ReadOnlyError()))
    store.persist_result(_result(), None)
    assert store_fallback.active()

    calls = []
    monkeypatch.setattr(store_fallback, "_probe_primary_writable",
                        lambda: calls.append(1) or True)
    store_fallback._state["_last_probe_at"] = 0.0
    store_fallback.maybe_probe_and_drain()      # throttle re-armed → probes once
    assert calls == [1]
    store_fallback.maybe_probe_and_drain()      # still inside the throttle window
    assert calls == [1]


def test_post_recovery_leftover_drain(fb_env, monkeypatch):
    """A drain capped mid-way leaves rows queued; successful primary writes
    keep draining them (maybe_finish_drain)."""
    real_persist = store_orm.persist_result

    def _boom(conn, result):
        raise ReadOnlyError()

    # Phase 1 — failover: writes fail, probe fails too (real read-only does both).
    monkeypatch.setattr(store_orm, "persist_result", _boom)
    monkeypatch.setattr(store_fallback, "_probe_primary_writable", lambda: False)
    for eid in ("E1", "E2", "E3"):
        store.persist_result(_result(event_id=eid), None)
    assert store_fallback.active()

    # Phase 2 — recovery with a capped drain: 2 of 3 replayed.
    monkeypatch.setattr(store_orm, "persist_result", real_persist)
    monkeypatch.setattr(store_fallback, "_probe_primary_writable", lambda: True)
    monkeypatch.setenv("BETB2B_FALLBACK_DRAIN_MAX", "2")
    store_fallback.maybe_probe_and_drain()
    assert not store_fallback.active()
    assert len(_mirror_rows(fb_env, "SELECT seq FROM fallback_outbox")) == 1

    # Phase 3 — the next successful primary write drains the leftover.
    store_fallback._state["_last_drain_at"] = 0.0   # drop the opportunistic hold
    store.persist_result(_result(event_id="E4"), None)
    assert len(_mirror_rows(fb_env, "SELECT seq FROM fallback_outbox")) == 0
    assert _primary_count("events") == 4


# --------------------------------------------------------------------------- #
# outbox cap + disabled mode
# --------------------------------------------------------------------------- #
def test_outbox_cap_drops_oldest(fb_env, monkeypatch):
    monkeypatch.setenv("BETB2B_FALLBACK_OUTBOX_MAX", "2")
    monkeypatch.setattr(store_orm, "persist_result",
                        lambda conn, r: (_ for _ in ()).throw(ReadOnlyError()))
    for eid in ("E1", "E2", "E3"):
        store.persist_result(_result(event_id=eid), None)
    rows = _mirror_rows(fb_env, "SELECT seq FROM fallback_outbox ORDER BY seq")
    assert len(rows) == 2
    assert store_fallback.status()["dropped"] == 1
    # oldest (E1) gone, E3 retained
    payloads = " ".join(r["payload"] for r in _mirror_rows(
        fb_env, "SELECT payload FROM fallback_outbox"))
    assert '"E1"' not in payloads and '"E3"' in payloads


def test_fallback_disabled_fails_loudly(fb_env, monkeypatch):
    monkeypatch.setenv("BETB2B_FALLBACK", "0")
    monkeypatch.setattr(store_orm, "persist_result",
                        lambda conn, r: (_ for _ in ()).throw(ReadOnlyError()))
    with pytest.raises(ReadOnlyError):
        store.persist_result(_result(), None)
    assert not store_fallback.active()


def test_non_eligible_failure_raises(fb_env, monkeypatch):
    monkeypatch.setattr(store_orm, "persist_result",
                        lambda conn, r: (_ for _ in ()).throw(ValueError("bad payload")))
    with pytest.raises(ValueError):
        store.persist_result(_result(), None)
    assert not store_fallback.active()
    assert not (fb_env / "mirror.db").exists()   # mirror never created for our bugs


# --------------------------------------------------------------------------- #
# scheduler composition (test the seam end-to-end, not just the parts)
# --------------------------------------------------------------------------- #
def test_scheduler_persist_survives_read_only_and_lands_locally(fb_env, monkeypatch):
    from src.sites.betb2b.extraction.models import Event, EventStatus, Sport
    from src.sites.betb2b.scheduler import BetB2BScheduler

    monkeypatch.setattr(store_orm, "persist_result",
                        lambda conn, r: (_ for _ in ()).throw(ReadOnlyError()))
    s = BetB2BScheduler("linebet", db_path=str(fb_env / "sched.db"),
                        scheduled_interval=3600, live_interval=0, results_interval=0)
    s._scraper = type("S", (), {"skin": type("K", (), {"name": "linebet",
                                                       "base_url": "https://x"})()})()
    ev = Event(event_id="EV9", competition="NBA", sport=Sport.BASKETBALL,
               home="H", away="A", status=EventStatus.NOT_STARTED)
    s._persist("list_prematch", [ev])       # must not raise

    assert store_fallback.active()
    evs = _mirror_rows(fb_env, "SELECT event_id FROM events")
    assert [e["event_id"] for e in evs] == ["EV9"]
    # next init_db hands out the mirror — reads (skip filter) keep working
    conn = store.init_db(str(fb_env / "sched.db"))
    assert isinstance(conn, sqlite3.Connection)
    conn.close()
