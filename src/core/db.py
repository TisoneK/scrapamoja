"""Shared database engine factory — the ADR-11 connection layer.

Env-driven single integration point so the scraper, the Selector Engine, and
the FastAPI control plane all reach the **same** store through one code path:

* ``DATABASE_URL`` set  → that URL is used verbatim (Postgres in deployed envs,
  any SQLAlchemy URL otherwise — e.g. ``postgresql+psycopg://...``).
* ``DATABASE_URL`` unset → SQLite fallback. The file path comes from
  ``ADAPTIVE_DB_PATH`` (legacy, kept for the Selector Engine) or defaults to
  ``<cwd>/data/adaptive.db``. Tests pass ``:memory:`` or a temp path.

This is the ADR-11 "keep SQLite as the local-dev / test fallback" rule (point 6)
and the "one SQLAlchemy code path" rule, made concrete. The betb2b store and the
adaptive repositories both import :func:`get_engine` / :func:`get_session_factory`
instead of building their own ``create_engine(f"sqlite:///...")``.

Two back ends, one path: callers never branch on the URL scheme. The only
backend-specific tweak is SQLite's ``check_same_thread=False`` (the stdlib
default rejects cross-thread connection use, which FastAPI/gunicorn needs).

ADR-11 also retires ADR-1 point 5's Volume mount + ``ADAPTIVE_DB_PATH`` *as a
deploy concern* — in deployed envs ``DATABASE_URL`` points at the Railway
Postgres plugin and ``ADAPTIVE_DB_PATH`` is simply ignored. ``ADAPTIVE_DB_PATH``
stays supported for local/CI SQLite only, so nothing that currently sets it
breaks.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

__all__ = [
    "DATABASE_URL_ENV",
    "ADAPTIVE_DB_PATH_ENV",
    "resolve_database_url",
    "get_engine",
    "get_session_factory",
    "is_postgres",
    "default_sqlite_path",
]

DATABASE_URL_ENV = "DATABASE_URL"
ADAPTIVE_DB_PATH_ENV = "ADAPTIVE_DB_PATH"


def default_sqlite_path() -> str:
    """The SQLite file used when neither ``DATABASE_URL`` nor a path is given.

    Mirrors the Selector Engine's pre-ADR-11 default (``data/adaptive.db``
    under the cwd) so local runs keep working unchanged.
    """
    db_dir = Path(os.getcwd()) / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "adaptive.db")


def resolve_database_url(explicit: str | None = None) -> str:
    """Resolve the SQLAlchemy URL to use, ADR-11 precedence:

    1. ``explicit`` argument (caller overrides — used by tests and by the
       betb2b store, which has its own ``odds.db`` file in local mode).
    2. ``DATABASE_URL`` env var (deployed → Railway Postgres).
    3. ``ADAPTIVE_DB_PATH`` env var → SQLite at that path (local/CI legacy).
    4. ``<cwd>/data/adaptive.db`` (local default).

    A bare path (no scheme) is treated as a SQLite file path and wrapped as
    ``sqlite:///<path>`` — this preserves the pre-ADR-11 calling convention
    where repositories received a filesystem path, not a URL.
    """
    if explicit:
        return _normalize(explicit)

    env_url = os.environ.get(DATABASE_URL_ENV)
    if env_url:
        return _normalize(env_url)   # pin the psycopg driver on bare postgres URLs

    adaptive_path = os.environ.get(ADAPTIVE_DB_PATH_ENV)
    if adaptive_path:
        return _normalize(adaptive_path)

    return _normalize(default_sqlite_path())


def _normalize(value: str) -> str:
    """Accept either a full SQLAlchemy URL or a bare filesystem path.

    ``:memory:`` is returned as-is; a bare path becomes ``sqlite:///<path>``.
    Postgres URLs are pinned to the **psycopg (v3)** driver: Supabase (and most
    tooling) hand out a bare ``postgresql://`` / ``postgres://`` URL, but with no
    ``+driver`` SQLAlchemy defaults to psycopg2 — which isn't installed. We ship
    psycopg v3, so rewrite the scheme to ``postgresql+psycopg://``.
    """
    if value == ":memory:":
        return value
    if "://" in value:
        if value.startswith("postgres://"):          # some providers' legacy form
            value = "postgresql://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):          # bare → force psycopg v3
            value = "postgresql+psycopg://" + value[len("postgresql://"):]
        return value
    return f"sqlite:///{value}"


def is_postgres(url: str | None = None) -> bool:
    """True when the resolved URL is a PostgreSQL backend.

    Used by migration / copy scripts that need to know which dialect they run
    against (e.g. to skip SQLite-only pragmas).
    """
    u = url or resolve_database_url()
    return u.startswith("postgresql") or u.startswith("postgres:")


def get_engine(url: str | None = None, *, echo: bool = False) -> Engine:
    """Build a SQLAlchemy :class:`~sqlalchemy.Engine` for the resolved URL.

    SQLite gets ``check_same_thread=False`` so the engine is usable from
    FastAPI request handlers / gunicorn workers (the same reason every
    adaptive repository set it before). Postgres needs no such arg; passing
    it would raise. Connection-pool sizing is left to SQLAlchemy defaults
    (suitable for the control plane's modest concurrency).
    """
    resolved = resolve_database_url(url)
    # resolve_database_url returns ":memory:" verbatim (it has no scheme), but
    # create_engine needs a full URL — normalize here so callers can pass the
    # bare ":memory:" sentinel for in-memory SQLite tests.
    if resolved == ":memory:":
        resolved = "sqlite:///:memory:"
    kwargs: dict = {"echo": echo}
    if resolved.startswith("sqlite"):
        # :memory: needs an absolute path-free form; file SQLite needs the
        # thread shim. StaticPool keeps :memory: shared across sessions.
        if resolved == "sqlite:///:memory:" or resolved == "sqlite://":
            from sqlalchemy.pool import StaticPool
            kwargs["connect_args"] = {"check_same_thread": False}
            kwargs["poolclass"] = StaticPool
        else:
            kwargs["connect_args"] = {"check_same_thread": False}
    elif resolved.startswith("postgresql"):
        # Supabase's transaction pooler (pgBouncer, port 6543) does NOT support
        # prepared statements, which psycopg v3 uses by default → disable them.
        # pool_pre_ping avoids handing out a pooled connection the pooler dropped.
        kwargs["connect_args"] = {"prepare_threshold": None}
        kwargs["pool_pre_ping"] = True
    engine = create_engine(resolved, **kwargs)
    logger.debug("db engine created: backend=%s", "postgres" if is_postgres(resolved) else "sqlite")
    return engine


def get_session_factory(engine: Engine | None = None) -> sessionmaker:
    """A :class:`~sqlalchemy.orm.sessionmaker` bound to ``engine`` (or a fresh one)."""
    return sessionmaker(bind=engine or get_engine(), expire_on_commit=False)
