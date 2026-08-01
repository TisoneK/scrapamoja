# Current Task — Idle

**Status:** Idle — no session in progress.

Last: **Session 35 (2026-08-01, Buffy / deepseek-v4-flash, local macOS)** — `.context` sync.
Core updated **0.3.0 → 0.5.0** (session-scoped memory release); `kickoff.md` + `AGENTS.md`
regenerated for the new templates (Windows `pwsh` block + `memory/sessions/` skim note);
new `memory/sessions/` module seeded (README + SUMMARY with Sessions 30–35 backfill).
No product code touched. All pushed.

**Next (tasks/backlog.md):**
- Results-pass engine grading (ADR-16/20) — handoff to the engine session: grade HIT/MISS by
  reading `events` where `result_status=3` joined to ungraded `predictions`.
- paripesa domain (203 on GetSportsZip).
- ADR-19 market-naming build-out (new-builder GetGameZip MEC/SG names).
- Standalone scheduler on Railway is live (ADR-18); watch statisticfeed `529` noise; consider
  `BETB2B_CONCURRENCY=4` if noisy.
- Operator action from Session 31 still outstanding: run the Supabase cleanup to clear
  pre-fix outright junk.

**Deploy note:** on Railway set `DATABASE_URL` (Supabase pooler) + `BETB2B_DIRECT=1`; leave
`BETB2B_PROXY_URL` blank → the scraper runs standalone (no proxy, no browser). `GUNICORN_WORKERS=1`.
