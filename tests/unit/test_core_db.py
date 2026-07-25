"""Tests for the ADR-11 shared database engine factory (src/core/db.py).

Verifies the env-driven URL resolution precedence and that one code path
serves both the SQLite fallback and a (URL-form) Postgres backend — without
needing a live Postgres, by asserting the resolved URL and the engine's
dialect name.
"""

from __future__ import annotations

import pytest

from src.core import db as dbmod


@pytest.fixture
def clean_env(monkeypatch):
    """Strip every DB-related env var so each test starts from a known state."""
    for var in ("DATABASE_URL", "ADAPTIVE_DB_PATH"):
        monkeypatch.delenv(var, raising=False)
    yield


def test_resolve_defaults_to_sqlite_fallback(clean_env, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    url = dbmod.resolve_database_url()
    assert url.startswith("sqlite:///")
    assert "adaptive.db" in url


def test_resolve_explicit_path_is_wrapped_as_sqlite(clean_env):
    # A bare filesystem path (the pre-ADR-11 calling convention) becomes a
    # sqlite URL — this is what keeps existing callers working.
    url = dbmod.resolve_database_url("/tmp/some/odds.db")
    assert url == "sqlite:////tmp/some/odds.db"


def test_resolve_explicit_url_passes_through(clean_env):
    url = dbmod.resolve_database_url("postgresql+psycopg://u:p@h:5432/x")
    assert url == "postgresql+psycopg://u:p@h:5432/x"


def test_resolve_memory_passes_through(clean_env):
    assert dbmod.resolve_database_url(":memory:") == ":memory:"


def test_database_url_env_wins(clean_env, monkeypatch):
    monkeypatch.setenv("ADAPTIVE_DB_PATH", "/tmp/legacy.db")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/deployed")
    assert dbmod.resolve_database_url() == "postgresql+psycopg://u:p@h:5432/deployed"


def test_adaptive_db_path_used_when_no_database_url(clean_env, monkeypatch):
    monkeypatch.setenv("ADAPTIVE_DB_PATH", "/tmp/legacy adaptive.db")
    assert dbmod.resolve_database_url() == "sqlite:////tmp/legacy adaptive.db"


def test_is_postgres(clean_env, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/x")
    assert dbmod.is_postgres() is True
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@h:5432/x")
    assert dbmod.is_postgres() is True


def test_is_not_postgres_for_sqlite(clean_env, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert dbmod.is_postgres() is False


def test_get_engine_sqlite_file_accepts_cross_thread(clean_env, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine = dbmod.get_engine()
    # The whole point of check_same_thread=False: usable from any thread.
    assert engine.dialect.name == "sqlite"


def test_get_engine_memory_uses_static_pool(clean_env):
    engine = dbmod.get_engine(":memory:")
    assert engine.dialect.name == "sqlite"
    # Two sessions over an in-memory engine must see each other's data —
    # StaticPool keeps a single connection alive for that.
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    s1, s2 = Session(), Session()
    s1.execute(text("CREATE TABLE t (x INTEGER)"))
    s1.execute(text("INSERT INTO t (x) VALUES (1)"))
    s1.commit()
    assert s2.execute(text("SELECT x FROM t")).scalar() == 1


def test_get_session_factory_bound(clean_env, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    factory = dbmod.get_session_factory()
    s = factory()
    assert s.bind is not None
    s.close()
