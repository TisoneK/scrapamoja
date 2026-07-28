# Current Task — betb2b data-quality: market naming (ADR-19)

**Status:** ACTIVE — Session 31 (2026-07-28, Claude Code / claude-opus-4-8, local).

## This session so far (shipped + pushed)
1. **Outrights dropped** (`787972e`) — single-sided outright/futures markets
   (Special bets, Results of the championship, season/award winners) were
   ingested as events (title in `home`, null `away`) → junk teams. `_build_event`
   now requires both home AND away. Verified live (WNBA 9/9 both teams; Special
   bets 1/1 single-sided). Supabase cleanup SQL handed to the operator.
2. **Persist speedup** (`27edbee`, ADR-17) — batched H2H `insert().returning()`,
   bulk change-only dedup, in-memory team cache. ~1000 round-trips → a handful.
3. **ADR-16/17/18** (`11b6e66`) recorded earlier this session.

## Now: market naming (ADR-19) — planning pushed, implementing next
Root cause + full mechanism traced (proxy + Playwright) →
`reviews/2026-07-28-market-naming-mechanism.md`, decision in **ADR-19**.

**Implementation plan (next):**
- [ ] Add the **new-builder** `GetGameZip` params to `client.py::fetch_game`
      (`isNewBuilder=true&GroupEvents=true&marketType=1&countevents=250`), id via
      the event's `CI`. Validate the response parses for **prematch + live**.
- [ ] Parse `MEC[]` (category names) + `SG[].TG` (sub-game names) in
      `extraction/rules.py`; keep the verified `(G,T)` map for core markets and
      use the `MEC` category as the group label where `(G,T)` is unknown
      (replaces bare `"G=<n>"`).
- [ ] Decide sub-game-name storage (new dimension vs. market scope) — small
      schema/store touch if added.
- [ ] Tests: new-builder fixture → assert category names + sub-game names;
      assert core `(G,T)` still resolves; no regression to `"G=<n>"` for known groups.
- [ ] Verify live via the operator's proxy / a Railway run; then log Session 31
      exit + clear this file.

**Deferred (ADR-19):** exact exotic per-group labels (client sport-aware template
resolution / ADR-7 render-and-read) — cosmetic, odds+ids already correct.

## Also open (tasks/backlog.md)
- Parallel/batch fetch (ADR-17 fetch half — bounded-concurrency `gather`).
- Deploy scheduler as a Railway worker (ADR-18).
- Results-pass endpoint research (ADR-16).
- paripesa domain (203 on GetSportsZip).

**Deploy note:** on Railway set `DATABASE_URL` (Supabase pooler) + `BETB2B_DIRECT=1`; leave
`BETB2B_PROXY_URL` blank → the scraper runs standalone (no proxy, no browser). `GUNICORN_WORKERS=1`.
