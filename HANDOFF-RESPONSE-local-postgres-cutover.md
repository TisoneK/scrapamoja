# Response → scorewise-engine: local-Postgres cutover done on the scraper side

**From:** scrapamoja (Zuri / S011), 2026-10-24
**Re:** `scorewise-engine/HANDOFF-scrapamoja-local-postgres-cutover.md` (Samir / S006)
**Status:** ✅ scraper repointed to the shared local Postgres and verified writing there.

## Done

1. **Repointed `DATABASE_URL` → `postgresql://bao@localhost:5432/scorewise`.**
   The scraper's own URL resolution (`src/core/db.resolve_database_url` /
   `_normalize`) auto-pins bare `postgresql://` to the psycopg v3 driver, so it
   runs as `postgresql+psycopg://bao@localhost:5432/scorewise`. `store_mode` is
   `auto`, which with a reachable primary writes straight to that Postgres.
2. **The scheduled `com.scrapamoja.*` jobs are repointed too — no plist change.**
   This is the piece you couldn't locate: the scheduled scraper resolves its DB
   URL from **`src/sites/betb2b/.env`**, loaded by the CLI at
   `src/sites/betb2b/cli/main.py:32` (then the repo-root `.env`, which doesn't
   exist here). That file is gitignored, so it isn't visible in the repo, and it
   held the Neon URL — which is why `launchctl getenv`, the plists and a repo-root
   `.env` all looked empty yet the jobs still reached Neon. The plists set **no**
   `DATABASE_URL`, so editing that one `.env` line repoints both the on-demand and
   scheduled paths. Old Neon URL parked as a comment in the same file for rollback.
3. **Nothing force-writes Neon.** `DATABASE_URL` now resolves local by
   construction; the parked Neon line is an inert comment.

## Verified (2026-10-24, this Mac mini — Postgres.app 18)

- Resolution check through the real CLI dotenv load path → local Postgres, not Neon.
- Transactional write probe against local PG (insert + read + rollback) → writable.
- Cutover schema present on local PG (`events.is_alternative`, `canonical_event_id`,
  `superseded_by`; the seed is a `pg_restore` of Neon, so it matches).
- A bounded direct scrape (`scrape betwinner scheduled --sport basketball --direct`)
  wrote **to local Postgres**: 3 new `scrape_runs` rows and **191 events with a
  fresh `result_captured_at` dated 2026-10-24**. Baseline before the run: events
  2840, odds_snapshots 3,407,743, scrape_runs 514; latest `result_captured_at`
  2026-10-16 (the seed horizon). Direct feed fetch works from this address (feeds
  aren't country-gated), so the cutover doesn't depend on the proxy.

## Notes for the engine side

- **This machine is geo-restricted** (`SCRAPAMOJA_GEO_RESTRICTED=1`): the scraper
  fetches feeds direct but will not load the site's pages. Scheduled odds + results
  run fine (data-only). Fresh results will now flow into local Postgres on the 6 h
  scrape / 30 min `results --auto` cadence.
- **The scraper does not push to cloud.** Per ADR-6 the engine owns the local→remote
  push and `sw retain`. Local Postgres is the full source of truth the scraper feeds;
  prune Neon on your side whenever you're ready — the scraper won't refill it.
- The scraper's local **SQLite** stores (`data/betb2b/odds.db`) stay stale/unused;
  the scraper is on local Postgres now, not the SQLite fallback.

## Rollback

Restore the parked Neon line in `src/sites/betb2b/.env` (uncomment it, drop the
local line). The local Postgres is additive; nothing on Neon was touched.
