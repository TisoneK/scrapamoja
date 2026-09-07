# Agent Sessions (append-only within the current group)

One entry per agent session in the CURRENT group, newest at the bottom.
Closed groups live in .context/history/ and .context/archive/ (not read
at session start). Rotate with context-history.

<!-- TEMPLATE - copy below the last entry and FILL IN every placeholder:
---
## YYYY-MM-DD - Session N
- **Agent:** <name> | **Model:** <model id> | **Platform:** <machine/sandbox + OS> | **Role:** <engineer, or overlay> | **Core:** <version>
- **Task:** <what this session set out to do>
- **Commits:** <count> (<first-sha>..<last-sha>)
- **Outcome:** <done / partial / blocked>
- **Open items:** <pointers into tasks/backlog.md, or "none">
- **Notes:** .context/memory/sessions/<date>-<N>/notes.md  (or "none")
-->
---
## 2026-09-07 — Session 42
- **Agent:** ZCode | **Model:** GLM-5.3-Flash | **Platform:** TisoneK-Windows (Windows 11) | **Role:** engineer | **Core:** 0.16.1
- **Task:** operator: set live fetch false (scheduled-only basketball) + Supabase over-quota email (DB 1.67 GB / 1.1 GB, restricted until 2026-09-27)
- **Commits:** 2 (`9cb7fcf` fix(deploy) worker live-off default + regression test + RAILWAY.md/CHANGELOG; `0650066` docs(review))
- **Outcome:** done — root cause: the ADR-22 scheduled-only fix missed `railway.worker.json` (worker deploys via config-as-code, which overrides the dashboard); live pass ran since 2026-08-07 and re-filled the DB. All deploy surfaces now default live OFF; `test_deploy_configs_default_live_off` pins Procfile + worker JSON; RAILWAY.md documents the dashboard-var override risk.
- **Open items:** ADR-22 retention pass (priority raised); operator: delete dashboard `SCHED_LIVE_INTERVAL` on the worker service; when writable again: prune/wipe the 1.67 GB. See tasks/backlog.md.
- **Report:** .context/memory/reviews/2026-09-07-review.md
---
## 2026-09-07 — Session 43
- **Agent:** ZCode | **Model:** GLM-5.3-Flash | **Platform:** TisoneK-Windows (Windows 11) | **Role:** engineer | **Core:** 0.16.1
- **Task:** operator: local fallback store — if Supabase fails or gets restricted, switch writes to a local SQLite store instead of dropping them, and replay to Supabase on recovery
- **Commits:** 1 (`ce24540` feat(store) — store_fallback.py + store seams + 14 tests + RAILWAY.md/CHANGELOG)
- **Outcome:** done — failover on 25006/connection-class failures to a local mirror (same schema), FIFO outbox, throttled write-probe recovery, bounded idempotent drain through the store's own dedup paths. Suite 247 passed (233 + 14).
- **Open items:** ADR-22 retention pass (unchanged); fallback mirror is ephemeral on the worker unless `BETB2B_FALLBACK_DB_PATH` points at a Volume; outbox cap revisit if live polling returns. See tasks/backlog.md + ADR-24.
- **Report:** .context/memory/reviews/2026-09-07-review-2.md
