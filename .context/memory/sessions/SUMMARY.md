# Session Summary (current group - prunable)

One line per session: date, agent, model, one-line outcome. Closed groups
are in .context/history/. Keep this small.
- 2026-09-07 — ZCode — GLM-5.3-Flash — Deploy regression fixed: `railway.worker.json` booted the worker with live ON since Aug (missed by the scheduled-only fix) → Supabase re-filled to 1.67 GB, restricted to Sep 27; all deploy surfaces now default live OFF, pinned by `test_deploy_configs_default_live_off`; operator must delete a stale dashboard `SCHED_LIVE_INTERVAL` var.
- 2026-09-07 — ZCode — GLM-5.3-Flash — Shipped the local fallback store (`ce24540`): Supabase write failures (quota read-only 25006 / connection outages) now fail over to a local SQLite mirror with a FIFO outbox; a throttled write-probe flips back and replays idempotently when the primary recovers — no more dropped writes during a restriction window (ADR-24).
- 2026-09-08 — Sam (S442) — GLM-5.3-Flash — Quota monitor + auto-prune shipped (`0398c94`, ADR-25): hourly pass reads primary pg_database_size, warns at 80%, prunes fact history older than 7 days at 92% (events/results kept); CLI `quota` one-shot; suite 251. Collab: answered Alex (S443)'s sweep note. Operator 1.67 GB prune still pending.
