"""Alembic environment — ADR-11.

Resolves the database URL via the shared factory (src.core.db) so migrations
run against DATABASE_URL (Railway Postgres in deployed envs) or the SQLite
fallback. Both metadata objects — the Selector Engine adaptive ``Base`` and
the betb2b ``Base`` — are merged so a single migration stream creates every
table in the consolidated store (ADR-11 point 3: one Postgres instance,
separate schemas/tables).
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `src` importable when alembic is invoked from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.db import resolve_database_url, is_postgres  # noqa: E402
from src.selectors.adaptive.db.models.recipe import Base as AdaptiveBase  # noqa: E402
from src.sites.betb2b.models import Base as BetB2BBase  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Merge both metadata sets — every table, both stores, one migration stream.
target_metadata = [AdaptiveBase.metadata, BetB2BBase.metadata]


def run_migrations_offline() -> None:
    url = resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = resolve_database_url()
    connectable = engine_from_config(
        {"sqlalchemy.url": url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite has no ALTER for most things; render_batch keeps migrations
            # runnable there (the local/CI fallback). Postgres ignores it.
            render_as_batch=not is_postgres(url),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
