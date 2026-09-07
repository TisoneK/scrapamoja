# Current Task — none

**Status:** idle — last session: 2026-09-07 Session 42 (deploy regression fix: `railway.worker.json` booted the worker with the live pass ON since 2026-08-07 — re-filled Supabase 28 MB → 1.67 GB; now defaults live OFF on every deploy surface + regression test + RAILWAY.md dashboard-var warning). Committed + pushed (`9cb7fcf`, `0650066`).

**Supabase state (2026-09-07):** DB **1.67 GB / 1.1 GB (over)** — Fair-Use restrictions active until **2026-09-27** (writes dropped; dashboard access intact). Scheduler read-only backoff (ADR-21 §1b) handles the window. DB size is *stored*, not a flow: it stays 1.67 GB until data is pruned/wiped once writable. Operator confirmed 2026-09-07: **stay free, scheduled-only basketball** (no Pro).

**⚠️ OPERATOR ACTION PENDING:** Railway dashboard → **worker** service → Variables → **delete `SCHED_LIVE_INTERVAL`** (or set `0`) if present. A dashboard-set variable overrides the config `:-0` fallback and would keep live ON despite `9cb7fcf`. Then redeploy the worker and confirm the startup log says the live pass is DISABLED.

**Next up (tasks/backlog.md):**
- **ADR-22 retention pass — priority raised:** the only mechanism keeping scheduled-only under quota long-term, and the path to shrink the 1.67 GB when writable (vs an operator-authorized wipe).
- Fix results-fetch capture (ADR-20 addendum) — HIGH when writable. In-process last-odds cache (ADR-23) before any live re-enable on a metered plan.
