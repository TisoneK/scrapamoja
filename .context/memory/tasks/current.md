# Current Task — Idle

**Status:** Idle — no session in progress.

Last: **Session 31 (2026-07-28, Claude Code / claude-opus-4-8, local)** — betb2b
data-quality pass off an operator review of the Supabase tables. All pushed.

**Shipped this session:**
- **Outrights dropped** (`787972e`) — single-sided outright/futures markets no
  longer ingested as events; `_build_event` requires both home AND away.
- **Persist speedup** (`27edbee`, ADR-17) — batched H2H insert + bulk dedup +
  team cache; ~1000 Supabase round-trips → a handful.
- **ADR-16/17/18** (`11b6e66`); **ADR-19** + market-naming recon (`034f8bf`).
- **Sub-game dimension** (`b3e1c69`, ADR-19) — `SG[]` named per-period/per-stat
  groups (Rebounds/Assists/Fouls/quarters) → new `sub_games` table. The clean
  feed-sourced naming win; exact per-group `G` labels deferred (client-composed).

**Operator action outstanding:** run the Supabase cleanup (targeted DELETE or
full `TRUNCATE`) to clear pre-fix outright junk + old data — SQL was provided in
chat; the running scraper already carries all fixes.

**Next (tasks/backlog.md):**
- Parallel/batch fetch (ADR-17 fetch half — bounded-concurrency `gather`) — the
  biggest remaining speedup.
- Deploy the scheduler as a dedicated Railway worker (ADR-18).
- Results-pass endpoint research (ADR-16) — unblocks prediction grading.
- paripesa domain (203 on GetSportsZip).

**Deploy note:** on Railway set `DATABASE_URL` (Supabase pooler) + `BETB2B_DIRECT=1`; leave
`BETB2B_PROXY_URL` blank → the scraper runs standalone (no proxy, no browser). `GUNICORN_WORKERS=1`.
