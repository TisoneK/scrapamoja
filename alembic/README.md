# Alembic — ADR-11 schema migrations

The repo had **no migration tool** before ADR-11. This directory adds Alembic,
configured to manage the consolidated store: both the Selector Engine adaptive
schema (`src/selectors/adaptive/db/models/`) and the betb2b schema
(`src/sites/betb2b/models.py`) in one migration stream, per ADR-11 point 3
("consolidate the three SQLite DBs into the one Postgres instance").

## How it resolves the database

`alembic/env.py` uses `src.core.db.resolve_database_url()`, so the target is:

- `DATABASE_URL` env var → Railway Postgres in deployed envs
- otherwise → the SQLite fallback (`ADAPTIVE_DB_PATH` or `data/adaptive.db`)

You never put a connection string in `alembic.ini`.

## Commands

```bash
# Apply all migrations to the resolved DB (deploy: DATABASE_URL=… ; local: SQLite)
python -m alembic -c alembic.ini upgrade head

# Roll back the last migration
python -m alembic -c alembic.ini downgrade -1

# Generate a new migration after editing ORM models
DATABASE_URL=sqlite:////tmp/autogen.db python -m alembic -c alembic.ini revision --autogenerate -m "<message>"

# Show current state
python -m alembic -c alembic.ini current
python -m alembic -c alembic.ini history
```

## Notes

- `render_as_batch=True` on SQLite (env.py) — SQLite can't ALTER most things;
  batch mode recreates tables to apply changes. Postgres ignores it.
- `compare_type=True` — autogenerate detects type changes (important for the
  ADR-11 SQLite-ism ports: Integer→Boolean, Text→DateTime(timezone=True)).
- The baseline migration (`c7ea08fedb55`) creates all 27 tables (14 adaptive +
  13 betb2b). It is the starting point; the live Railway Postgres gets it on
  first `upgrade head`.
