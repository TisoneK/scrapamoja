"""
Database configuration and session management.

Uses SQLite for development via SQLAlchemy 2.x async engine.
The database file is created at the project root as `scrapamoja.db`.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Resolve project root: src/api/database.py → ../../  (project root)
_HERE = Path(__file__).resolve()
PROJECT_ROOT = _HERE.parent.parent.parent  # scrapamoja/

DB_PATH = Path(
    os.environ.get("SCRAPAMOJA_DB_PATH", str(PROJECT_ROOT / "scrapamoja.db"))
)

DATABASE_URL = f"sqlite:///{DB_PATH}"

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
    echo=os.environ.get("SCRAPAMOJA_SQL_ECHO", "").lower() in {"1", "true"},
)


# Enable WAL mode and foreign-key enforcement for every connection.
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):  # noqa: ANN001
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    """
    Yield a SQLAlchemy session and close it when the request is done.

    Usage in a FastAPI route::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Table initialisation helper
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Create all tables that haven't been created yet.

    Import all model modules *before* calling this so that their ``Base``
    subclasses are registered with the metadata.
    """
    # Local import to avoid circular imports at module load time.
    from src.api import models  # noqa: F401  (registers models with Base)

    Base.metadata.create_all(bind=engine)
