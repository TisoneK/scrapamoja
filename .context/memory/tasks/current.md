# Current Task — none

**Status:** idle — last session: 2026-09-07 Session 43 (local fallback store shipped: Supabase write failures — the over-quota read-only restriction (SQLSTATE 25006) or connection outages — now fail over to a local SQLite mirror with a FIFO outbox (`fallback_outbox`); a throttled write-probe flips back and replays idempotently when the primary recovers. Commit `ce24540`. See ADR-24 + `reviews/2026-09-07-review-2.md`.)

**Supabase state (2026-09-07):** DB **1.67 GB / 1.1 GB (over)** — Fair-Use restrictions active until **2026-09-27** (writes dropped by Supabase; dashboard access intact). The fallback store now captures what the scraper would have lost during this window (worker's ephemeral disk unless `BETB2B_FALLBACK_DB_PATH` points at a Volume). Operator confirmed: stay free, scheduled-only basketball.

**⚠️ OPERATOR ACTION PENDING:** Railway dashboard → **worker** service → Variables → **delete `SCHED_LIVE_INTERVAL`** (or set `0`) if present. A dashboard-set variable overrides the config `:-0` fallback and would keep live ON despite `9cb7fcf`. Then redeploy the worker and confirm the startup log says the live pass is DISABLED.

**Next up (tasks/backlog.md):** ADR-22 retention pass (priority raised); ADR-20 addendum results-fetch capture; ADR-23 in-process last-odds cache before any live re-enable on a metered plan.
