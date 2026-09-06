# Current Task — none

**Status:** idle — last session: 2026-09-06 Session 41 (`.context` sync on the Windows machine: core 0.8.0 → 0.16.1, kickoff/AGENTS regen, no product code). Committed + pushed.

**⚠️ OPERATOR DECISION DUE NOW (2026-09-06):** the Supabase grace period ends **today** (ADR-21 §5 / ADR-23). Decide Pro vs stay-free before Fair-Use restrictions return (402 / read-only). Free tier is viable only with live OFF (current state: scheduled-only, `SCHED_LIVE_INTERVAL=0`) + the ADR-22 retention pass; full live capture needs Pro. The app degrades gracefully either way (read-only backoff, ADR-21 §1b).

**Supabase state (unchanged since 2026-08-05):** DB 28 MB / 500 MB (fine — wipe held) · egress 9.21 GB / 5 GB (over; per-cycle flow) · scheduled-only mode (live OFF) · read-only write-backoff in place.

**Next up (see tasks/backlog.md):**
- **Supabase Pro vs stay-free** (above) — operator call, deadline today.
- **Retention pass (ADR-22)** + **in-process last-odds dedup cache (ADR-23)** — both needed *before re-enabling live* on a metered plan (retention = DB size, cache = egress).
- **Fix results-fetch capture (ADR-20 addendum)** — capture `stat_game_id`/`entity.id` for ~every event (today ~2%); HIGH when writable.
- live sub-game (G,GS,T) capture · MEC persistence to store · paripesa 203 · scheduler stats `529` watch.

**Done this session (41):** `.context` sync only — core 0.8.0 → 0.16.1 (update + migrate backfill; PS-update backfill skip logged as a flaw), kickoff.md + AGENTS.md regenerated for 0.16.1, first Windows-run sync (CRLF verify false-positive diagnosed = known 0.9.1 fix), betb2b suite green on the Windows venv (232 passed). See `agents/sessions.md`.
