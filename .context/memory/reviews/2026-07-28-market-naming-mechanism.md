# Recon — how betb2b/1xbet names market groups (2026-07-28)

**Agent:** Claude Code / claude-opus-4-8 (local). **Method:** proxy (`bore.pub`)
+ Playwright network capture of the real linebet SPA + direct feed probes.
**Trigger:** `markets.name` in Supabase is saved as `"G=27"` (raw group id) for
markets whose group id isn't in `markets.py`.

## The question
`GetGameZip` markets carry only numeric `G` (group) / `T` (type) ids. One WNBA
game has ~64 distinct `G`; `markets.py::DEFAULT_MARKET_GROUPS` names ~15 → the
rest fall back to `f"G={g_id}"`. Where does the SPA get the human names?

## What was ruled out (with evidence)
- **`bets_model_short_en_<N>.json` (traincdn) is the WRONG id-space.** These
  files (the user's lead) are the "bet-constructor" templates. Verified: they
  cannot reproduce a single known basketball market — the dict maps feed `G=17`
  (Total) → "Match Result Including Overtime", `G=62` (Individual Total Away) →
  "Draw In At Least One Half", `G=14` (To Win Match) → "Goal Interval". Their
  internal group space uses e.g. Asian Handicap = `G 1008`, not feed `G 2`.
  Union across files is globally consistent (0 name conflicts, 5331 groups) but
  simply not the feed's space. `bets_model_map_short_en.json` is a manifest
  (templateId 1-77 → entry-range in the `_0` master), not a feed-G map.
- **No un-gated `GetGroupsZip`-style dictionary** — GetGroupsZip /
  GetGroupSubGamesZip / GetSubGamesZip all 404.
- **The odds grid is canvas/virtualised** (`market-grid-canvas`) → no market
  text in the DOM. This is why every prior DOM market-extraction logged
  `markets=0` and the `(G,T)` map was hand-verified (ADR-7).

## The actual mechanism (traced end-to-end)
1. The SPA renders the game with a **new-builder** `GetGameZip` variant (not the
   one the scraper uses):
   ```
   /service-api/LineFeed/GetGameZip?id=<CI>&lng=en&isSubGames=true&GroupEvents=true
       &countevents=250&grMode=4&partner=189&topGroups=&country=87&marketType=1&isNewBuilder=true
   ```
   - Uses the event's **`CI`** id (not `I`). (`CI` is present on every event.)
   - Returns, in addition to the market groups:
     - **`MEC[]`** — the market filter **categories** with REAL names:
       `{MT, EC(count), N}` → `Popular / Total / Handicap / Result + Total /
       Points / Special / Asian markets / Other / All markets`.
     - **`SG[]`** — **sub-games** with REAL names in `TG`: `Rebounds`, `Assists`,
       `Three-Point Field Goals Scored`, `Two-Point Field Goals Scored`,
       `Free Throws Scored`, `Fouls`, per-quarter/half (`PN`), `Players' stats`.
     - **`GE[]`** — the market groups: `{G, GS, E}` — still numeric.
2. Per-group names are **composed client-side** (`entry-242f057a68.js`):
   `name = groupNames[groupShortId] ?? getMarketGroupTemplatesByGroupId(groupId).name`
   where `groupId = feed G` (a **"foreignId"**, cf.
   `GAME_PINNED_MARKET_GROUP_FOREIGN_IDS`) and `groupShortId = feed GS`. The
   templates come from the per-sport bet-models (`bets_model_short_en_0.json`
   master + the map), resolved with **sport context** — which is the step that
   reconciles feed-G to the internal template space. There is **no static
   feed-G→name file**; it's client logic.

## Consequence for the scraper
- **Shippable now (no full resolution):** call `GetGameZip` with the new-builder
  params → capture `MEC` category names + `SG.TG` sub-game names straight from
  the feed. Combined with the verified `(G,T)` core map, that names markets
  meaningfully (category + known core) and adds the sub-game dimension we don't
  currently store.
- **Exact exotic per-group labels:** require replicating the client's sport-aware
  template resolution (deep, uncertain) OR the ADR-7 render-and-read cross-map.
  Deferred — cosmetic; odds + `(G,T)` ids are already captured correctly. **Never
  guess names — a wrong label is worse than an honest `G=<n>`.**

See ADR-19. Backlog: "Map remaining GetGameZip market-group ids to names".
