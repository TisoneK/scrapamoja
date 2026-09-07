# Session Summary (current group - prunable)

One line per session: date, agent, model, one-line outcome. Closed groups
are in .context/history/. Keep this small.
- 2026-09-07 — ZCode — GLM-5.3-Flash — Deploy regression fixed: `railway.worker.json` booted the worker with live ON since Aug (missed by the scheduled-only fix) → Supabase re-filled to 1.67 GB, restricted to Sep 27; all deploy surfaces now default live OFF, pinned by `test_deploy_configs_default_live_off`; operator must delete a stale dashboard `SCHED_LIVE_INTERVAL` var.
