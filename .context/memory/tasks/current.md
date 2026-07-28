# Current Task — Idle

**Status:** Idle — no session in progress.

Session 30 (2026-07-27, Claude Code / claude-opus-4-8, local) took betb2b from
"SQLite + proxy + browser" to a **deployed, Supabase-backed, remotely-controllable,
proxy-free** pipeline, and recorded the cross-repo architecture in all three repos.

**Where things stand:**
- **betb2b → Supabase is LIVE.** The scraper writes odds/events/h2h/jobs to a shared
  Supabase Postgres when `DATABASE_URL` is set (ADR-13 store cutover, `store_orm.py`).
  Verified end-to-end on Railway (18 events / 2,041 odds / 102 h2h in one run). This
  realizes ADR-11's intent — the F2 "persist path → ORM" is done via the dispatch in `store.py`.
- **Remote-control API is LIVE** (`/api/scraper/*`, `x-api-key`, single-flight background
  jobs, live `phase`) — ADR-12. Deployed at `scrapamoja.up.railway.app`.
- **Direct mode removes the proxy** (ADR-15): `--direct` / `BETB2B_DIRECT=1` → browser-free,
  proxy-free discovery via `GetSportsZip → GetChampZip → GetGameZip` (+ cookie-less H2H/stats).
  Live-verified: 32 leagues / 102 events / 7,659 odds in ~103s from a datacenter IP, no tunnel.
- **Cross-repo architecture recorded** — DB-mediated (Supabase is the bus; no point-to-point
  HTTP). scrapamoja ADR-14, scorewise-engine ADR-1, scorewise-website ADR-4 (+revision).
  Shared `db-architecture.md` + `api-contracts.md` in every repo's `.context/memory/system/`.

**Next (see tasks/backlog.md):**
- **Parallel/batch fetch** — biggest remaining speedup, now that there's no browser
  (bounded-concurrency `gather` over GetGameZip/H2H, replacing the sequential rate limit).
- **State-aware scheduler** — live ~10s / prematch ~3h / a results pass for finished games;
  env-configurable cadences + concurrency. Watch for datacenter-IP abuse limits — ramp slowly.
- **paripesa** domain fix (203 on GetSportsZip; other 7 skins OK).
- The **`predictions` table** design belongs to the **engine's own session** (its ADR-1).

**Deploy note:** on Railway set `DATABASE_URL` (Supabase pooler) + `BETB2B_DIRECT=1`; leave
`BETB2B_PROXY_URL` blank → the scraper runs standalone (no proxy, no browser). `GUNICORN_WORKERS=1`.
