"""``BETB2B_STORE_MODE`` — the env-only switch between environments.

One setting moves the same process between the hosted store and this
machine: ``auto`` (the historical DATABASE_URL behaviour), ``local`` (plain
local SQLite), ``mirror`` (write locally NOW + queue for replay, skipping the
doomed primary attempts), and ``remote`` (hosted-only, fail fast). No network:
the "hosted" primary is a SQLite-backed ORM store via ``DATABASE_URL`` (the
same code path Postgres runs); a down primary is simulated by patching the
fallback probe seam to raise a connection error.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from src.sites.betb2b import store, store_fallback, store_orm

MODE_ENV = "BETB2B_STORE_MODE"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Clean slate: no mode, no DATABASE_URL, fresh fallback state."""
    monkeypatch.delenv(MODE_ENV, raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("BETB2B_FALLBACK", raising=False)
    monkeypatch.setenv("BETB2B_FALLBACK_DB_PATH", str(tmp_path / "mirror.db"))
    monkeypatch.setenv("BETB2B_FALLBACK_PROBE_SECONDS", "0")
    store_orm._engines.clear()
    store_fallback._reset_for_tests()
    yield tmp_path
    store_orm._engines.clear()
    store_fallback._reset_for_tests()


def _result(event_id="EV1", skin="linebet"):
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
                                     {"name": "2", "price": 2.5, "is_suspended": False}]}]}],
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
# auto — the historical behaviour must not shift
# --------------------------------------------------------------------------- #
def test_auto_without_database_url_is_local_sqlite(env):
    conn = store.init_db(env / "odds.db")
    assert isinstance(conn, sqlite3.Connection)
    assert not store_fallback.active()


def test_auto_with_database_url_is_hosted(env, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{env / 'primary.db'}")
    conn = store.init_db()
    assert store._is_orm(conn)
    conn.close()
    assert not store_fallback.active()


# --------------------------------------------------------------------------- #
# local — this machine only, DATABASE_URL ignored
# --------------------------------------------------------------------------- #
def test_local_ignores_database_url(env, monkeypatch):
    # A routed-to-nothing Postgres URL: if local mode honoured it, init_db
    # would raise (or hang on connect) instead of returning the file store.
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.invalid:5432/x")
    monkeypatch.setenv(MODE_ENV, "local")
    conn = store.init_db(env / "odds.db")
    assert isinstance(conn, sqlite3.Connection)
    assert not store_fallback.active()
    store.persist_result(_result(), conn=conn)
    conn.close()


# --------------------------------------------------------------------------- #
# remote — fail fast when the hosted store is not configured
# --------------------------------------------------------------------------- #
def test_remote_without_database_url_raises(env, monkeypatch):
    monkeypatch.setenv(MODE_ENV, "remote")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        store.init_db(env / "odds.db")


def test_unknown_mode_raises(env, monkeypatch):
    monkeypatch.setenv(MODE_ENV, "lokal")
    with pytest.raises(ValueError, match=MODE_ENV):
        store.init_db(env / "odds.db")


# --------------------------------------------------------------------------- #
# mirror — the paused-provider mode
# --------------------------------------------------------------------------- #
def test_mirror_without_database_url_raises(env, monkeypatch):
    monkeypatch.setenv(MODE_ENV, "mirror")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        store.init_db()


def test_mirror_with_fallback_disabled_raises(env, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{env / 'primary.db'}")
    monkeypatch.setenv("BETB2B_FALLBACK", "0")
    monkeypatch.setenv(MODE_ENV, "mirror")
    with pytest.raises(RuntimeError, match="BETB2B_FALLBACK"):
        store.init_db()


def test_mirror_routes_writes_to_mirror_and_queues(env, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{env / 'primary.db'}")
    monkeypatch.setenv(MODE_ENV, "mirror")
    # Pretend the primary is still paused: every probe connection fails.
    def _down():
        raise OSError("[WinError 10061] No connection could be made")
    monkeypatch.setattr(store_fallback, "_connect_primary", _down)

    conn = store.init_db()
    assert isinstance(conn, sqlite3.Connection)          # writes land locally
    assert store_fallback.active()
    st = store_fallback.status()
    assert st["reason"].startswith("forced: BETB2B_STORE_MODE")

    store.persist_result(_result(event_id="EV9"), conn=conn)
    conn.close()

    assert _mirror_rows(env, "SELECT event_id FROM events")[0]["event_id"] == "EV9"
    assert _mirror_rows(env, "SELECT COUNT(*) AS n FROM fallback_outbox")[0]["n"] == 1
    assert _primary_count("events") == 0                # nothing reached the primary


def test_mirror_drains_once_primary_recovers(env, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{env / 'primary.db'}")
    monkeypatch.setenv(MODE_ENV, "mirror")
    real_connect = store_orm.connect

    def _down():
        raise OSError("connection refused")
    monkeypatch.setattr(store_fallback, "_connect_primary", _down)

    store.persist_result(_result(event_id="EV7"), None)   # via init_db → mirror
    assert store_fallback.active()
    assert _mirror_rows(env, "SELECT COUNT(*) AS n FROM fallback_outbox")[0]["n"] == 1

    monkeypatch.setattr(store_fallback, "_connect_primary", real_connect)
    store_fallback.maybe_probe_and_drain()
    assert not store_fallback.active()
    assert _primary_count("events") == 1
    assert _mirror_rows(env, "SELECT COUNT(*) AS n FROM fallback_outbox")[0]["n"] == 0
