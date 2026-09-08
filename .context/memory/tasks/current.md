# Current Task — none

**Status:** idle — last session: 2026-09-07 Session 43 (local fallback store shipped: Supabase write failures — the over-quota read-only restriction (SQLSTATE 25006) or connection outages — now fail over to a local SQLite mirror with a FIFO outbox (`fallback_outbox`); a throttled write-probe flips back and replays idempotently when the primary recovers. Commit `ce24540`. See ADR-24 + `reviews/2026-09-07-review-2.md`.)

**Supabase state (2026-09-08):** DB **1668 MB / 500 MB per-project (over 3.3×)** — dashboard confirms read-only mode; egress already reset this cycle (0 / 5 GB), so **DB size is the only active constraint**. Fair-Use window runs to **2026-09-27**, but the dashboard SQL editor retains full access — pruning does NOT have to wait for the reset. NEW (2026-09-08): Supabase's inactivity scanner flagged the project for **auto-pause** (7+ days low activity); pausing is survivable (unpause within 90 days) but pointless to fight while over quota. Operator confirmed: stay free, scheduled-only basketball.

**⚠️ OPERATOR DECISION (pause + quota, 2026-09-08):** prune now vs let it pause. Either way the 1.67 GB must come down before writes resume. Prune-now path (recommended): dashboard SQL editor → `TRUNCATE odds_snapshots` (optionally `scrape_runs`, `event_states`, `period_scores`, `h2h_games`, `h2h_period_scores`, `statistics`, `sub_games`) — operator-gated destructive; keeps `events` (results/grades), dims, schema. DELETE alone won't shrink reported size — use TRUNCATE (instant reclaim). If the project pauses anyway: unpause from dashboard, then prune, then writes resume (fallback outbox replays per ADR-24).

**⚠️ OPERATOR ACTION PENDING:** Railway dashboard → **worker** service → Variables → **delete `SCHED_LIVE_INTERVAL`** (or set `0`) if present. A dashboard-set variable overrides the config `:-0` fallback and would keep live ON despite `9cb7fcf`. Then redeploy the worker and confirm the startup log says the live pass is DISABLED.

**Next up (tasks/backlog.md):** ADR-22 retention pass (priority raised); ADR-20 addendum results-fetch capture; ADR-23 in-process last-odds cache before any live re-enable on a metered plan.
