# Current Task — none

**Status:** idle — last session: 2026-09-08 Session 44 (Sam/S442; **quota monitor + auto-prune shipped**, `0398c94` + ADR-25: hourly scheduler pass reads the primary's `pg_database_size` — bypassing the ADR-24 fallback mirror — warns at 80% of `BETB2B_DB_LIMIT_MB` (500), auto-prunes fact history older than `BETB2B_PRUNE_DAYS` (7) at the 92% critical level; `events`/results always survive; CLI `quota` one-shot dry-run default; 4 new tests, suite **251 passed**). This ships the long-open ADR-22 retention pass. Collab: Alex (S443) ran a read-only secret-leak sweep, no overlap; notes on `collab/2026-09-08`. Committed + pushed.

**Supabase state (2026-09-08):** DB **1668 MB / 500 MB per-project (over 3.3×)** — dashboard read-only; egress reset this cycle (0 / 5 GB). Project flagged for **auto-pause** by the inactivity scanner (survivable: unpause within 90 days). Fair-Use window to **2026-09-27**. The monitor canNOT self-prune a read-only store — the one-time operator prune stands.

**⚠️ OPERATOR ACTIONS PENDING:**
1. **One-time prune of the 1.67 GB** (dashboard SQL editor, works despite read-only): `TRUNCATE odds_snapshots;` + optionally `TRUNCATE scrape_runs, event_states, period_scores, h2h_games, h2h_period_scores, statistics, sub_games;` — keep `events` + dims. TRUNCATE (not DELETE) so the quota accounting actually drops. After it: store self-caps from now on.
2. Railway worker → Variables → **delete `SCHED_LIVE_INTERVAL`** if set; redeploy the worker (brings the quota pass live) and confirm the startup log shows live DISABLED + quota pass scheduled.

**Next up (tasks/backlog.md):** ADR-20 addendum results-fetch capture (HIGH when writable); ADR-23 in-process last-odds cache before any live re-enable on a metered plan; egress monitoring only if it binds again.
