# Recon — the finished-match results endpoint (closes ADR-16's open research, 2026-07-28)

**Agent:** Claude Code / claude-opus-4-8 (local). **Method:** proxy-free probing from a
datacenter IP (same as the ADR-15 GetSportsZip win). **Goal:** find where a finished match's
final score lives once the Line/Live feeds drop it — the input that grades predictions.

## The endpoint
```
GET https://<skin>/service-api/statisticfeed/api/v1/Game?id=<id>&lng=en&ref=<partner>&fcountry=<country>&gr=<gr>
```
- Same `statisticfeed` host + param grammar we already use for H2H (`/v1/Game/h2h`) and stats
  (`/v2/Game/statistic`). **Un-gated, proxy-free, browser-free** (verified from a datacenter IP).
- `204` = valid endpoint, no data (minor/virtual leagues have no statistic coverage); `404` =
  no such endpoint. Discovered via the 204-vs-404 distinction: real sibling endpoints are
  `v1/Game`, `v1/Game/events` (204-capable); the guessed `v1/Game/{result,get,info,score,…}`
  are all 404.

## The payload (`entity` = THIS game)
`v1/Game` returns `{teams, gameShorts, sportId, entity}` — a **superset of the H2H endpoint**
(`teams`+`gameShorts` == H2H). The new part is **`entity`**, the game's own record:

| field | meaning |
|---|---|
| `id` | statisticfeed game id (stable, retained) |
| `status` | **2 = live, 3 = FINISHED** (1 = not started) — the finished flag |
| `subStatus` | finer detail (3 = finished normal; 38 seen on a 5-period/OT game) |
| `score1`, `score2` | **final score** (team1 / team2) |
| `winner` | **1 = team1 won, 2 = team2 won** (0 = undecided/live) |
| `subScore1/2` | e.g. shootout/OT sub-score |
| `periods[]` | per-period finals: `{type, title, score1, score2}` — `type` 18/19/20/21 = Q1–Q4 (matches our `_PERIOD_TYPE_NAMES`), so QUARTER/HALF scopes are gradeable |
| `teamId1/2`, `dateStart`, `stageTitle`, `tournamentTitle`, `headToHead` | context |

## Proven facts
- **Retention:** finished games from **6–18 days ago** still return full `entity` results
  (`status:3`, final score, winner). statisticfeed is a persistent history/stats service — so
  "the feed drops the match" (LineFeed/LiveFeed) does NOT lose the result. This is the crux
  ADR-16 was unsure about.
- **`winner` matches the score** on all samples (110-128→2, 134-132→1, 118-113→1).
- **Live vs finished:** a live game shows `status:2` with the running score; the same shape
  flips to `status:3` + final score when done.
- The LineFeed event id resolves `v1/Game` **while the match is in the feed** (id maps
  LineFeed→statisticfeed). Whether the LineFeed id still resolves *after* the feed drops the
  match was not observable this session (no just-finished game in the live sample). **Robust
  design avoids depending on it** (below).

## Results-pass design (for the scheduler's third pass — ADR-16 §1)
1. **During live/scheduled scraping, capture `entity.id`** (the statisticfeed game id) + current
   `status` onto the event. Cheap: `v1/Game` is a superset of the H2H call we already make, so it
   can **replace `/Game/h2h`** — one call yields H2H (gameShorts) AND the entity (id/score/status).
2. **Results pass:** for events with `start_time + ~2.5h < now` and no final result yet, query
   `v1/Game?id=<stored entity.id>` (guaranteed to retain). When `status == 3`, write the final
   `score1/score2` + `winner` + `periods` to Supabase (`event_states` final row, or a result
   field on `events`). Map team1/team2 → home/away by LineFeed O1/O2 order (same convention as
   the H2H `score1/score2` we already store).
   - Shortcut worth trying at implementation: `v1/Game?id=<LineFeedEventId>` directly (skips the
     pre-capture) — use it if it resolves post-finish; keep the entity.id path as the guarantee.
3. **Engine grades** HIT/MISS from the stored result (its ADR-1/2 domain, DB-mediated).

## Net
ADR-16's blocking open research is **resolved** — the endpoint, the finished flag (`status:3`),
the score/winner/period fields, and multi-week retention are all confirmed live and proxy-free.
The results pass is now a build, not a research question. Bonus: `v1/Game` can consolidate the
H2H call.
