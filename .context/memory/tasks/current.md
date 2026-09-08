# Current Task — none

**Status:** idle — last session: 2026-09-08 Session 44 (Sam/S442; **quota monitor + auto-prune shipped**, `0398c94` + ADR-25: hourly scheduler pass reads the primary's `pg_database_size` — bypassing the ADR-24 fallback mirror — warns at 80% of `BETB2B_DB_LIMIT_MB` (500), auto-prunes fact history older than `BETB2B_PRUNE_DAYS` (7) at the 92% critical level; `events`/results always survive; CLI `quota` one-shot dry-run default; 4 new tests, suite **251 passed**). This ships the long-open ADR-22 retention pass. Collab: Alex (S443) ran a read-only secret-leak sweep, no overlap; notes on `collab/2026-09-08`. Committed + pushed.

**Supabase state (2026-09-08):** DB **1668 MB / 500 MB per-project (over 3.3×)** — dashboard read-only; egress reset this cycle (0 / 5 GB). Project flagged for **auto-pause** by the inactivity scanner (survivable: unpause within 90 days). Fair-Use window to **2026-09-27**. The monitor canNOT self-prune a read-only store — the one-time operator prune stands.

**⚠️ OPERATOR ACTIONS PENDING:**
1. **One-time prune of the 1.67 GB** — CORRECTED 2026-09-08 (two gotchas hit live): (a) the plain SQL editor hits 25006 → run inside a session-level override; (b) TRUNCATE of a referenced table must list ALL referencing tables **in the same statement** (FK catalog check fires even when the referencing table is empty — `odds_snapshots.run_id → scrape_runs`). The working single statement (after `SET default_transaction_read_only = off;` in the same session):
   ```sql
   TRUNCATE odds_snapshots, scrape_runs, event_states, period_scores,
            h2h_games, h2h_period_scores, statistics, sub_games;
   ```
   (or `TRUNCATE scrape_runs, event_states, period_scores, h2h_games, h2h_period_scores, statistics, sub_games CASCADE;`). Keep `events` + dims. Precedent: 2026-08-05 wipe went 1,603 MB → 11 MB (one statement, all tables, CASCADE). **Do NOT** `ALTER DATABASE … default_transaction_read_only=off` (platform-wide bypass). Supabase lifts read-only on its own cadence once under the limit — possibly a "restore" click on the dashboard banner. After it: the monitor self-caps from now on.
2. Railway worker → Variables → **delete `SCHED_LIVE_INTERVAL`** if set; redeploy the worker (brings the quota pass live) and confirm the startup log shows live DISABLED + quota pass scheduled.

**Next up (tasks/backlog.md):** ADR-20 addendum results-fetch capture (HIGH when writable); ADR-23 in-process last-odds cache before any live re-enable on a metered plan; egress monitoring only if it binds again.
