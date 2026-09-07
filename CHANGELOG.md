# Changelog

All notable changes to Scrapamoja. Format loosely based on [Keep a Changelog](https://keepachangelog.com/).
Technical detail lives in the session reviews at `.context/memory/reviews/`;
this file is the plain-language public record.

## [Unreleased]

### Added — the scraper keeps collecting when the shared database is unavailable (2026-09-07, session 43)

The scheduled scraper now survives the shared database going down or being
locked. When the free hosting quota locks the database to read-only — or it
can't be reached at all — the scraper used to simply stop saving data and wait.
It now switches to a local fallback database on the machine it runs on, keeps
writing there, and remembers every write it made in a replay queue. It
periodically checks whether the main database accepts writes again; the first
check that succeeds switches collection back and replays everything that was
queued, so no scrape results are lost during an outage or a quota restriction.
The switch, the recovery, and how much is queued are all logged. Set
`BETB2B_FALLBACK=0` to turn the behavior off and get the old fail-loudly
instead.

### Fixed — the always-on scraper boots with live-odds polling OFF again (2026-09-07, session 42)

The scheduled scraper worker on Railway was accidentally re-enabled to poll live
(continuously changing) odds every 15 seconds — the mode that filled the shared
database past the free hosting quota in August. When the low-storage default was
introduced, only one of the two launch configurations was updated, so the worker
service kept booting with live polling on. Both launch configurations now default
to scheduled-only (pre-match odds every 3 hours + final results every 10 minutes);
a new test fails if either config ever ships with live polling on by default.
The deploy guide no longer instructs enabling live polling, and warns that
variables set in the Railway dashboard override the config-file defaults — a
stale dashboard variable can silently re-enable live polling.

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
