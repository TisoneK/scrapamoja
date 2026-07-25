# Changelog

All notable changes to Scrapamoja. Format loosely based on [Keep a Changelog](https://keepachangelog.com/).
Technical detail lives in the session reviews at `.context/memory/reviews/`;
this file is the plain-language public record.

## [Unreleased]

### Added — ADR-11: shared PostgreSQL store foundation (2026-07-25, session 29)

The data store can now move from per-file SQLite databases to a single shared
PostgreSQL database (Railway plugin), so the scraper, the prediction engine,
and the apps can all read from one place through the Python/FastAPI layer.

- **One database connection layer.** A new shared module resolves the database
  from the `DATABASE_URL` environment variable: when set, the app talks to
  PostgreSQL (the deployed setup); when unset, it falls back to the local
  SQLite files. Existing local runs and tests keep working unchanged.
- **PostgreSQL driver and a migration tool.** Added `psycopg` (the Postgres
  driver) and `alembic` (schema migrations — the project had none). The first
  migration creates every table in the consolidated store in one stream.
- **Portable schema for the betting data.** The betb2b odds/stats schema is now
  declared as database-agnostic models (was SQLite-only raw SQL): booleans for
  flags, timezone-aware timestamps, auto-incrementing keys that work on both
  databases. The hot query paths (latest odds per event, events by start time)
  now have dedicated indexes.
- **One-time data copy tool.** A script moves existing rows from the old SQLite
  files into the new shared database, for the production cutover.

### Notes
- The live scraper still writes betting data through its original SQLite path
  for now; the shared-Postgres write path is the next step (operator-side,
  needs the Railway database provisioned).
- Local development and tests continue to use SQLite automatically — no setup
  change required for contributors.
