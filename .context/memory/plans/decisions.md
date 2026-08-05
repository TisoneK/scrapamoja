# Architectural Decisions (append-only, ADR-style)

Decisions already made — future agents respect these rather than
relitigating them. To reverse one, append a new ADR that supersedes it.

<!-- TEMPLATE — copy below the last entry:
---
## ADR-N: <short title> (YYYY-MM-DD)
- **Status:** accepted | superseded by ADR-M
- **Context:** <what forced the decision>
- **Decision:** <what was decided>
- **Consequences:** <trade-offs accepted; what future agents must respect>
-->

---
## ADR-1: Deploy the FastAPI control plane to Railway via Dockerfile (2026-07-17)
- **Status:** accepted
- **Context:** Scrapamoja ships two entry points — `src/api/main.py` (a long-running FastAPI control plane exposing feature-flag + failure-escalation REST endpoints, consumed by the React UI at `ui/app/`) and `src/main.py` (a CLI for one-off scrape jobs). The project needed a public deployment target. Railway was chosen because (a) the user already had a Railway account with a generous plan (8 vCPU / 8 GB per-replica cap), (b) Railway's GitHub integration gives auto-deploy on push to `main`, and (c) Railway supports Dockerfile builders — necessary because the app pulls in Playwright + Chromium, which need OS-level deps that Nixpacks (Railway's default buildpack) can't easily install.
- **Decision:**
  1. Deploy ONLY the FastAPI control plane (`src/api/main:app`) as the long-running web service. The CLI ships inside the image for `railway run python -m src.main ...` invocations but is NOT the deployed process.
  2. Use a multi-stage Dockerfile on `python:3.12-slim-bookworm`: builder stage installs Python deps, runtime stage copies the venv + installs `playwright install --with-deps chromium` + runs as non-root `appuser` (uid 10001) + starts gunicorn with uvicorn workers.
  3. Do NOT deploy the React UI in the same service. The UI is a separate Vite SPA — deploy it as a separate Railway static site pointing at the API service's public URL.
  4. Do NOT run scrape jobs inside the API service in production. Each Chromium spawn costs ~500 MB; under load they'd compete with API requests for the same browser pool. Run scrapes as `railway run` jobs or a separate worker service.
  5. Mount a Railway Volume at `/app/data` for the SQLite DB (`ADAPTIVE_DB_PATH=/app/data/adaptive.db`) — without it, every redeploy wipes feature flags + failure events.
- **Consequences:**
  - Image is ~1.5 GB (Chromium + Playwright + Python deps). First deploy takes ~5–8 min; subsequent builds hit the cache.
  - Minimum viable service size is 1 GB RAM (Chromium needs ~500 MB just to spawn). The 8 GB plan headroom is more than enough — `GUNICORN_WORKERS=2` is the conservative default; safe to bump to 4–8 under real traffic.
  - The non-root `appuser` constraint surfaced an import-time `os.makedirs` smell in `src/core/snapshot/__init__.py` (see `inefficiencies/log.md` 2026-07-17 entry). Dockerfile fix applied; source-level fix backlogged.
  - Future agents: do NOT add the UI build to this Dockerfile. If the UI needs to ship in the same image, add a separate `Dockerfile.ui` and a multi-stage build that serves the built static assets from the FastAPI app via `StaticFiles` — but that's a separate decision (would require superceding this ADR).
  - Future agents: if you swap the DB from SQLite to Postgres (Railway has a Postgres add-on), remove the Volume mount and the `ADAPTIVE_DB_PATH` env var; the Dockerfile's pre-created `/app/data` dir becomes unnecessary but harmless.

---
## ADR-2: Model a site's "access/transport" as a separate axis from its "extraction mode"; reserve `sw_replay` as a future 5th mode (2026-07-17)
- **Status:** accepted
- **Context:** `ExtractionMode` (in `src/sites/base/site_config.py`) has 4 values — `raw` / `playwright` / `intercepted` / `hybrid` — which all answer "HOW do I get the data out" (DOM vs API). Session 11's live linebet recon + the operator's prior abandoned linebet attempt revealed those 4 values conflate a second, orthogonal concern: "HOW is the data transported and what's required to reach it." Concretely, linebet:
  - is `playwright`-extractable (odds render in the DOM) but **NOT** `intercepted`-able (the odds feed is invisible to page/context network interception + the HAR);
  - serves live odds from a `/LineFeed/` endpoint (1xbet/melbet-family; heavily compressed; terse single-letter-key JSON) whose **auth token (with expiry) + a referer-like navigation header are injected by a service worker** (`ivpn-sw.js`) from an IndexedDB store (`vpn/headers`), so a plain HTTP scraper never has them;
  - is geo-gated at the nginx edge (needs an allowed-country proxy) and runs mirror-domain failover (`domain-sw.js`).
  These are transport/access facts, not extraction-mechanism facts. See `src/sites/linebet/RECON.md`.
- **Decision:**
  1. **Do not add a new ExtractionMode reflexively.** linebet ships as `playwright` (DOM extraction) today — the 4 modes stay clean.
  2. **Add an `AccessProfile` descriptor to `SiteConfig`** to record the orthogonal transport/access facts, e.g. `geo_gated: bool`, `requires_proxy: bool`, `transport: dom|xhr|websocket|service_worker`, `interceptable: bool`, `mirror_domains: bool`, `header_source: page|cookies|indexeddb`. This is where "why interception won't work here" lives.
  3. **Reserve `sw_replay` (a.k.a. `worker_mediated`) as a FUTURE 5th ExtractionMode**, added ONLY when direct-API odds polling (sub-second, browserless) becomes a real requirement. Its recipe: read the SW-injected headers from IndexedDB at runtime → replay the `/LineFeed/` request with them → decompress → parse. It is distinct from `intercepted` (passive observation — impossible when a SW mediates the transport) and from `hybrid` (cookie/session harvest — insufficient, because the "session" here is SW header-injection + domain rewriting, and the token expires).
  4. **The classifier (the project deliverable) must emit BOTH** an `ExtractionMode` AND an `AccessProfile`. Key discriminating signal for SW transport: *"the DOM contains the data but network interception yields nothing"* → service-worker transport → recommend `playwright` (or `sw_replay`), flag `interceptable: false`, and record proxy/geo preconditions.
- **Consequences:**
  - Future agents: do NOT relitigate this by adding `service_worker` as an ExtractionMode value. If direct-API odds become required, add `sw_replay` per point 3 and keep the AccessProfile axis separate.
  - `InterceptedConfig`/`HybridConfig` stay as-is; a new `AccessProfile` model (and, later, `SwReplayConfig`) are additive.
  - The linebet package can adopt the AccessProfile now (`geo_gated + requires_proxy + transport: service_worker + interceptable: false + header_source: indexeddb`) as the first real example, even while it extracts via `playwright`.

---
## ADR-3: Linebet extraction mode is `hybrid` (cookie-harvest → direct httpx polling); refines ADR-2 (2026-07-18)
- **Status:** accepted (refines ADR-2 — does NOT reverse the AccessProfile axis; corrects the linebet-specific classification)
- **Context:** ADR-2 (2026-07-17) recorded that linebet's odds looked "service-worker-mediated / not interceptable / DOM-only," and reserved a future `sw_replay` mode for it. On 2026-07-18, with the Kenya proxy live, a live capture using an in-page `window.fetch` wrapper (init script) found the odds are a plain XHR — `GET /service-api/LiveFeed/Get1x2_VZip` (+ siblings `GetSportsShortZip`, `WebGetTopChampsZip`, `main-line-feed/v1`) — returning gzipped 1xbet terse-key JSON. Crucially, the endpoint was **replayed from `httpx` with no browser**: `status 200, Success=true, 9 events`, and it worked **without** the `x-hd` token. The earlier "invisible to interception" observation was a Playwright surfacing quirk (`page.on("response")`/context events/HAR missed these specific fetches), NOT a service-worker transport. See `src/sites/linebet/RECON.md` "SOLVED".
- **Decision:**
  1. **Linebet's extraction mode is `hybrid`**, not `playwright`/DOM-only and not a new `sw_replay` mode. Recipe: bootstrap a browser once through an allowed-country proxy to harvest session cookies (the framework's `HybridConfig` + `SessionHarvester` already model exactly this), then poll the `LiveFeed`/`main-line-feed` endpoints directly with `httpx`.
  2. **Requirements to replay the odds feed:** allowed-country proxy + base betting headers (`is-srv:false`, `x-app-n:__BETTING_APP__`, `x-svc-source:__BETTING_APP__`, `x-requested-with:XMLHttpRequest`) + harvested cookies. `x-hd`/IndexedDB/service-worker header injection is an anti-block/telemetry layer and is NOT required for the odds feed.
  3. **`sw_replay` as a future 5th mode is NO LONGER motivated by linebet.** Keep it only as a hypothetical for some other site that genuinely gates data behind SW-injected headers; do not build it for linebet.
- **Consequences:**
  - ADR-2's core point stands: the AccessProfile axis is still useful — linebet's profile is `geo_gated: true, requires_proxy: true, interceptable: true (via in-page fetch hook / httpx replay), transport: xhr, header_source: page+cookies`. (Note `interceptable` flips to true vs the ADR-2 draft.)
  - The classifier's discriminating lesson is refined: "DOM has data but `page.on(response)` shows nothing" does NOT imply a SW transport — verify with an in-page `fetch`/XHR hook before concluding non-interceptable. A tool quirk masqueraded as an architecture.
  - Next build step (backlog): implement the linebet `hybrid` scraper against these endpoints + map the terse `T`/`G` market ids.

---
## ADR-4: BetB2B direct-API is best-effort; DOM extraction is the primary path (2026-07-19)
- **Status:** accepted (refines ADR-3)
- **Context:** ADR-3 (2026-07-18) recorded linebet as `hybrid` (cookie-harvest → httpx `LiveFeed`/`LineFeed` polling) after a proven httpx replay. On 2026-07-19 (Session 13) that replay was re-verified and now returns **`406 feed/NotAcceptableException`** with the same base headers + cookies — AND a bare in-browser `fetch` also 406s. Two platform changes: (1) the feed request moved into a **worker context**, invisible to page `fetch`/XHR hooks and page-target CDP Network; (2) `ivpn-sw.js` now injects a required header (`x-dt` ← `x-project-id`) from a store the app fills via `postMessage`, active only when the SW is registered with `?i=`, and the old IndexedDB `vpn/headers` store is gone. So the direct-API auth-header contract **rotates** — it is not a stable static recipe. The endpoints/params/schema (RECON.md) are unchanged.
- **Decision:**
  1. **DOM extraction is the primary betb2b extractor** (`playwright` path) — the rendered odds are drift-proof against the API auth-header churn.
  2. **Direct-API (httpx `LiveFeed`/`LineFeed`) is a best-effort optimization**, not the contract. When used, capture the genuine request headers **per session** at the worker level (CDP `Target.setAutoAttach {autoAttach:true,flatten:true}` to the service-worker/worker target + `Network.enable`), replay those, and treat `406` as a **re-harvest / DOM-fallback trigger**, never a hard failure.
  3. Do NOT chase the specific injected header value in code — it rotates. Do NOT capture the feed via page `fetch`/XHR wrappers or a page-target CDP session (they see nothing now).
- **Consequences:**
  - The `src/sites/betb2b/` base scraper needs a DOM extractor added as the primary path; `BetB2BFeedClient` (httpx) becomes the fast-path with a DOM fallback + 406→re-harvest handling.
  - RECON.md carries a "MOVING TARGET" warning atop the direct-API section.
  - This is a live example of the README's "handles anti-bot measures / selector drift" promise — the framework must degrade gracefully, not depend on a frozen contract.

---
## ADR-5: `GetGameZip` (per-match) is the reliable market-depth path for DOM-extracted events, live and prematch — refines ADR-4 (2026-07-21)
- **Status:** accepted
- **Context:** ADR-4 established DOM extraction as primary and the direct-API feeds as best-effort (the list feeds — `Get1x2_VZip` etc. — return 406 from auth-header rotation). But the DOM grid renders at most one shallow market per event ("To Win Match"/"1x2"), which is insufficient for the downstream odds-comparison use case. Session 25 confirmed (from a WAF-blocked datacenter IP, direct) that the **per-match** endpoint `/(?:Line|Live)Feed/GetGameZip?id=<eventId>` returns HTTP 200 with the full nested `E[]`/`AE[]` market tree — even though the SPA and the *list* feeds are blocked/406 from the same IP. Verified: prematch id → 10 markets/33 selections; live ids → 40/9/7 markets with live scores.
- **Decision:** DOM extraction supplies clean events (teams, numeric id, live score); market depth comes from enriching each DOM stub via `GetGameZip?id=` (`LineFeed` for prematch, `LiveFeed` for live), capped by `skin.enrich_dom_with_odds` + `max_odds_fetch`. The enrichment condition is "the event lacks a deep tree" (`len(markets) > 1`), NOT "has no markets" — the DOM stub always carries a shallow 1-market grid stub, so guarding on truthy-markets skips everything (the Session 24 "0 fetched" bug).
- **Consequences:** The scraper always makes one extra per-match request per event (rate-limited, capped). `GetGameZip` is NOT SW/auth-gated the way the list feeds are, so it needs no `x-dt` rotation handling — do not chase the list-feed 406 (ADR-4 stands). Market-group id→name mapping is incomplete (some markets label as `G=NN`); odds are still captured. Future: a console-script/direct GetGameZip-only prematch path could bypass the browser entirely for allowed-country IPs, but the DOM step is still needed for the event-id list when the SPA is the only source of ids.

---
## ADR-6: Scraped odds data gets a structured SQLite store (time-series), not loose JSON (2026-07-21)
- **Status:** accepted
- **Context:** Both scrapers (betb2b `storage.py`, flashscore `OutputFormatter`) emit each run as a standalone JSON blob to stdout or `--output`. Nothing dedups matches, tracks odds over time, or joins across skins. The existing SQLite DBs (`data/adaptive.db`, `data/audit_log.db`) hold the Selector Engine subsystem (recipes/weights/audit/snapshots) — NOT scraped sports data. So the actual product (events/odds) had no queryable home, blocking the odds-comparison use case that Sessions 18–25 kept pointing at.
- **Decision:** Add `src/sites/betb2b/store.py` — a SQLite store with 4 tables: `scrape_runs` (provenance), `events` (one row per match, UPSERT on `event_id` since all skins share backend ids), `event_states` (time-series of live status/score), `odds_snapshots` (time-series of prices, one row per selection per run). Input is the plain `BetB2BScrapeResult.to_dict()` dict, so it works on live scrapes AND saved JSON. Persistence is **opt-in and additive** — a `--db [PATH]` flag on `scrape`; JSON output is unchanged. SQLite first (stdlib, one file), schema kept Postgres-portable (TEXT/INTEGER/REAL, ISO-8601 timestamps).
- **Consequences:** Enables the three queries loose JSON couldn't — line movement (`line_movement`), cross-skin comparison (`cross_skin_odds`, join on shared `event_id`), and dedup (events UPSERT). Validated on real Session-25 captures: 5 skins → 16 deduped events, 5505 odds snapshots; cross-skin Phoenix Asian-Handicap query returned 5 bookmaker prices sorted. Trade-offs: (1) odds_snapshots grows one row per selection per run — a busy live poll writes a lot; a future "only insert on price change" dedup + retention policy is backlogged. (2) betb2b-only for now; flashscore/other sites would need their models mapped to the same schema (or a shared `src/storage/odds/`). (3) still file-based SQLite — a real deployment would migrate to Postgres (schema is ready). This does NOT replace the JSON path (telemetry, snapshots, `view`), it adds a structured layer beside it.

---
## ADR-6 REVISION (2026-07-21, same session) — the store is the full match model, not odds-only
- **Correction to ADR-6 above:** the first cut (commit `961f569`) had 4 tables and folded everything into events + odds — effectively treating odds as the whole DB. The operator flagged that the scraper already captures sports, countries, leagues, teams, period scores, and H2H, and those must be first-class in ONE betb2b DB (skin is a column, never a per-skin DB).
- **Revised schema (commit `ebfbf30`):** dimensions (skin-agnostic, UPSERT) `sports`, `countries`, `leagues`, `teams`, `events`, `markets`; facts (skin-scoped time-series) `scrape_runs`, `event_states`, `period_scores`, `odds_snapshots`, `h2h_games`, `statistics`. `events` FK → sport/league/country/home_team/away_team; `teams` carry the H2H backend id + country (enriched from `h2h_data.teams[]`); `odds_snapshots` references a `markets` dimension by `market_id` and is now just one fact table. Validated on the real 5-skin captures (1 sport / 8 countries / 12 leagues / 46 teams / 16 events / 41 markets / 113 period_scores / 5505 odds / 376 h2h_games). The ADR-6 decision (SQLite-first, opt-in `--db`, Postgres-portable, additive to JSON) is unchanged — only the table set is broader.

---
## ADR-7: Scoped ingestion to scorewise-engine — one betb2b match → N prediction scopes (2026-07-21, Session 26 investigation)
- **Status:** proposed (design; enabling store fix in progress)
- **Context:** The engine's `PredictionScope` has 9 values — FULL_MATCH, FIRST_HALF, SECOND_HALF, QUARTER_1..4, HOME_TEAM_TOTAL, AWAY_TEAM_TOTAL. Scope is metadata-only to the pipeline; what changes per scope is the INPUT: `odds.match_total` (the rung whose **Over-odds is nearest 1.85**) + H2H scores that **match the scope** (Q1 scope → Q1 H2H scores, not full-match). So one betb2b match → up to 9 `PredictRequest`s, each carrying that scope's total line + scope-matched H2H, POSTed to `/api/ingest`.
- **Data availability (verified on real captures):**
  - **H2H per-scope scores: AVAILABLE in the feed.** 43/43 played `h2h_data.game_shorts` carry `periods[]` = per-quarter {home_score, away_score, period_key} (period_key 18/19/20/21 = Q1–Q4 per Session-21 `_PERIOD_TYPE_NAMES`). So: FULL=score1/score2; QUARTER_n=periods[n]; FIRST_HALF=Q1+Q2, SECOND_HALF=Q3+Q4; HOME/AWAY_TEAM_TOTAL=home/away side across games. Future fixtures (score 0-0, status=1) must be filtered out.
  - **Full-match odds: AVAILABLE.** "Total Over/Under" market → match_total + over/under; "Moneyline 3-way"/"To Win Match" → home/away odds.
  - **Quarter/half/team-total odds: PRESENT but UNMAPPED.** They are the `G=NNNN` markets (the event had 40 markets, only 4 name-mapped). `markets.py::DEFAULT_MARKET_GROUPS` maps groups 3/17 (full total), 9 (BTTS), a few others — NOT the basketball quarter/half/individual-total groups.
- **Decision (design):**
  1. **FULL_MATCH ingestion is buildable now** (full total market + score1/score2 H2H).
  2. **Scoped (half/quarter/team) ingestion has two blockers:** (a) STORE must keep h2h `periods[]` — the `h2h_games` table currently drops them (fixing now — new `h2h_period_scores` table or periods on h2h_games); (b) MARKET G-map must gain the basketball quarter/half/individual-total group ids so the scope's total line is selectable by name.
  3. **Exporter lives in the scraper** (`src/sites/betb2b/export/scorewise.py`): `event_to_predict_requests(event) -> List[PredictRequest]` (one per available scope) + an httpx ingest client (chunk ≤100, source="betb2b-scraper"). Read from the store via a scope-aware query. Repos stay isolated (scraper only knows the engine's HTTP contract).
  4. **match_total selection = the totals rung whose over_odds is closest to 1.85** (engine's calculation-line rule), per scope.
  5. **Cross-skin:** ingest one consensus/best line per match, not one per skin (the store makes this a query).
- **Consequences:** enables full-match predictions immediately; half/quarter/team predictions after the store keeps h2h periods (done in this session) + the G-map is extended (backlog, needs the basketball group-id table). The H2H `periods[]` data is already flowing from GetGameZip — only the store dropped it.

---
## ADR-7 addendum (2026-07-21) — the "all modes" market taxonomy + how to map it
- **Structure confirmed (real captures):** betb2b delivers prediction scopes across TWO places:
  1. **Main event** E[]/AE[] = FULL-match markets. Combined total = `G=17`(or 3)`/T=9,10` (Over/Under, line=full total). Asian handicap = `G=2/T=7,8`. Moneyline/To-Win = `G=14/T=182,183` (2-way) and `G=101/T=401,402,403` (3-way). **Single-team ("full match single teams") totals** = the `individual_total` group (`G=4` in the code; a distinct group with ~half-magnitude lines) — combined-vs-individual is the key both-teams/single-team split the operator called out.
  2. **Sub-games `SG[]`** = per-QUARTER / per-HALF scopes. Each is a SEPARATE event with its own id `I` + `PN` (e.g. "1st quarter", "1 Half"); its markets are NOT inline — fetch `GetGameZip?id=<sub I>`. Each sub-game repeats the same market types scoped to that period (its own combined total, individual totals, handicap). Short formats (3x3) have NO sub-games (single period).
- **Market identity = (G, GS, T), not T alone.** `GS` is the group-specifier; the current `lookup_market` keys on `T` only and MISLABELS total variants (e.g. `G=62/T=13` → wrongly "Double Chance"; it has a line, so it's a total not a double-chance). Fix: key the lookup on `(G, GS, T)`.
- **Mapping method (do with ONE clean 5v5 capture — NBA/EuroLeague, has sub-games):** GetGameZip the main event + every `SG` sub-game; for each, enumerate `(G, GS, T)` → (scope, market_name, selection, is_individual, side) using: line magnitude (full~146 / half~73 / quarter~36 / individual~half-of-combined), Over/Under structure, and the sub-game `PN` for the period. Then extend `markets.py::DEFAULT_MARKET_GROUPS`/types and rewrite `lookup_market` to `(G,GS,T)`. Also add SG sub-game fetching to the scraper enrichment so scoped markets are captured + tagged with their `PredictionScope`.
- **Decision:** do NOT commit a guessed map — a mislabelled total feeds wrong odds to the engine (wrong predictions), which is worse than the `G=NNNN` placeholder. Blocked on a clean quartered-game capture (proxy was flapping + card was 3x3-heavy on 2026-07-21).

---
## ADR-7 VERIFIED MAPPING (2026-07-21) — betb2b basketball market (G,T) → mode, from a real PBA game
Ground truth: `GetGameZip id=352961836` San Miguel Beermen(HOME/O1) v Converge Fiberxers(AWAY/O2), PBA, + all 11 sub-games (raw saved). Handicap G=2/T=7 P=-5.5 → home favored (scores more → higher individual total). **(G,T) is stable across ALL scopes; the SCOPE = which (sub-)game the market is in.**

**CONFIRMED (G,T) → (market_name, selection):**
| G | T | market | selection | note |
|---|---|--------|-----------|------|
| 17 | 9 / 10 | **Total** (combined, both teams) | Over / Under | line=full total (~216 full, ~104 half, ~52 quarter) |
| 15 | 11 / 12 | **Individual Total — HOME** | Over / Under | ~half of combined; HOME=team1 (T=11/12) |
| 62 | 13 / 14 | **Individual Total — AWAY** | Over / Under | AWAY=team2 (T=13/14). **FIXES current bug: T=13,14 wrongly mapped to "Double Chance"** |
| 2 | 7 / 8 | **Asian Handicap** | W1(home) / W2(away) | P=handicap line |
| 14 | 182 / 183 | **To Win Match** (moneyline 2-way) | 1(home) / 2(away) | no line |
| 1 | 1 / 2 / 3 | **1x2** | 1 / X / 2 | seen in sub-games |
| 101 | 401 / 402 / 403 | **Moneyline 3-way** | 1 / 2 / X | no line |

**SCOPE ← sub-game:** main event = FULL_MATCH. Fetch each `main.Value.SG[].I` via GetGameZip; `PN` → scope: "1st/2nd/3rd/4th quarter"=QUARTER_1..4, "1 Half"=FIRST_HALF, "2 Half"=SECOND_HALF. Each sub-game repeats the SAME (G,T) groups scoped to its period. HOME/AWAY_TEAM_TOTAL scopes = main-event G=15 / G=62.

**UNCERTAIN (do NOT guess, left as G=NN):** G=8/T=4,6; G=91/T=755,757; G=92/T=766,767; G=27/T=424-426; and the many no-line prop groups (G=176,228,230,232,234,236,238,920,922,930,934,936,1144,1148,2663,2665,2766,2768,3017-3023,7733,7735,9854,10487-10489).

**IMPLEMENTATION TODO (was cut for tokens — NOT yet coded):**
1. `markets.py`: add a `(G,T)` keyed lookup that takes precedence over the T-only map; add the CONFIRMED rows above; the T-only map's `T=11/12→"Total"` and `T=13/14→"Double Chance"` are WRONG for basketball — (G,T) overrides fix them.
2. `rules.py::lookup_market`: check `(G,T)` first, fall back to T-only, then G-only.
3. Scraper: fetch `SG[]` sub-games per event, tag each scoped market with its `PredictionScope`; store needs a `scope`/`period` column on `markets` or `odds_snapshots` (or a `scoped_markets` table). Then scoped ingestion (ADR-7) has real per-scope totals.
4. Add the `BETB2B_ENGINE_URL` + `BETB2B_ENGINE_TOKEN` to `.context/memory/secrets/` and test a live POST.

### Capability Matrix (current status, 2026-07-22)

| Capability | Status | Why |
|-----------|--------|-----|
| `FULL_MATCH` ingestion | ✅ **Buildable** | Market mapped (G=17/T=9,10), H2H scores flowing, team-total H2H bug fixed (`20eda23`) |
| H2H period scores in DB | ✅ **Done** | `h2h_period_scores` table (`d0117eb`), 172 period rows on a real capture |
| H2H per scope (code) | ✅ **Implemented** | `_h2h_for_scope()` aggregates periods for QUARTER_1..4, FIRST/SECOND_HALF; zeroes non-relevant team for HOME/AWAY_TEAM_TOTAL. See ADR-8 for contract. |
| `QUARTER_1..4` ingestion | ❌ **Blocked** | Market group IDs for quarter combined totals not yet mapped. H2H works. |
| `FIRST_HALF` / `SECOND_HALF` ingestion | ❌ **Blocked** | Same blocker — half combined totals not mapped. H2H works (period aggregation). |
| `HOME_TEAM_TOTAL` / `AWAY_TEAM_TOTAL` ingestion | ✅ **Buildable** | Markets mapped (G=15/T=11,12 home, G=62/T=13,14 away). H2H bug fixed in Session 27. |
| Live POST to engine | ⏳ **Built, untested** | `post_ingest()` in `scorewise.py` + `scrape --ingest` flag. Needs `BETB2B_ENGINE_URL` + `BETB2B_ENGINE_TOKEN` in secrets to test. |
| Cross-skin consensus | 📝 **Design only** | Send ONE best line per match across skins. The store makes this a query (`cross_skin_odds`) but no ingest flow built for it yet. |
| Sub-game (`SG[]`) fetching | ❌ **Unimplemented** | Scraper doesn't fetch sub-games per event. ADR-7 addendum describes the method; not yet coded. |
Raw captures were in scratchpad (pba/main.json + sub_*.json) — re-fetch id=352961836 to reproduce.

---

## ADR-8 — H2H scope contract rule (exporter)

**Date:** 2026-07-22  
**Status:** adopted  
**Context:** Session 27 discovered that `_h2h_for_scope()` was sending full match
scores for HOME_TEAM_TOTAL and AWAY_TEAM_TOTAL scopes. The engine's
`H2HMatch` docstring says *"Scores must correspond to the same scope as the
prediction"*, and `s02_h2h_totals.py` always computes `total = home_score +
away_score`. Violating this contract produces false HIGH predictions because
full match totals (~180) are compared against individual team lines (~89).

**Decision:** The exporter MUST zero out the non-relevant team's H2H score when
building team-total scopes. Specifically:

| Scope | home_score | away_score | Engine sum | Meaning |
|-------|-----------|-----------|------------|---------|
| FULL_MATCH | O1 (full match) | O2 (full match) | game total | Total points |
| HOME_TEAM_TOTAL | O1 (full match) | **0** | O1 | Home team's points |
| AWAY_TEAM_TOTAL | **0** | O2 (full match) | O2 | Away team's points |
| QUARTER_1..4 / HALF | period home | period away | period total | Period total points |

**Rationale:**
1. The engine pipeline always sums — it does not inspect scope to decide
   whether to sum. This is by design (s02 is generic).
2. Team-total predictions are about ONE team's output — the other team's
   score is noise. Zeroing it makes the sum represent only the relevant team.
3. This matches betting semantics: "Home Team Total Over 89.5" means "will
   the home team score ≥90?" — only the home team's points matter.

**Enforcement:**
- `_h2h_for_scope()` in `export/scorewise.py` applies the zero-out logic.
- Add unit tests that assert: for each scope, the home+away sum matches the
  scope-relevant score (engine-visible number).
- Verify script `scripts/verify_h2h_per_scope.py` displays the engine total
  alongside the line so a human can spot future violations.

---

## CORRECTION (2026-07-22, Session 28) — the ADR-7 capability matrix above is stale

The capability matrix added in `db3046c` (Session 27) contradicts what Sessions
26–27 actually shipped. Append-only file, so the rows stay — read them with this
correction. Verified against the code on 2026-07-22:

| Matrix row | It says | Actually |
|---|---|---|
| `QUARTER_1..4` ingestion | ❌ Blocked — market group IDs not mapped | Mapped in `f321319`; `DEFAULT_MARKET_GT` in `markets.py` |
| `FIRST_HALF`/`SECOND_HALF` ingestion | ❌ Blocked — same | Same — mapped |
| Sub-game (`SG[]`) fetching | ❌ Unimplemented | Shipped in `5bd38cc` (`scraper.py::_enrich_with_subgames`) |
| Live POST to engine | ⏳ Built, untested | Confirmed live in Session 26 — HTTP 200, real predictions returned |

**But the corrected rows still overstate reality**, for a reason none of those
sessions noticed: `_enrich_with_subgames` is gated on
`skin.features["subgames"]`, which defaulted to `False`, was set by no skin YAML,
and had no CLI flag. It never ran. So the half and quarter scopes were **mapped
and implemented but unreachable** — `scrape --ingest` emitted 3 of 9 scopes
(FULL_MATCH + the two team totals) and reported success. Fixed by `5f6e6db`
(`--subgames` on `scrape` and `poll`).

**Consequence for anyone reading Session 27's numbers:** its reported run_3
breakdown (11 FIRST_HALF, 11 SECOND_HALF, 44 quarter requests) cannot have
happened. That document also states, correctly, that all 4,115 odds snapshots
were stored with `scope='FULL_MATCH'` — which is exactly why. The run yielded
~30 requests, not 96, and the HOME_TEAM_TOTAL asymmetry investigated there was
chased through variables that were never in play. **Half/quarter ingestion has
never been exercised end-to-end against live data.** Do that first, with
`--subgames`, before trusting any per-scope count in the record.

---

## ADR-9: A pipeline's composition gets one end-to-end assertion, not more unit tests (2026-07-22, Session 28)

- **Status:** accepted
- **Context:** Three defects found in Session 28 share one shape — a component
  verified in isolation, a composition never run. The exporter's tests build
  market dicts with `scope` pre-set, proving it handles scoped markets; nothing
  proved a scrape ever produces one (F1). The CLI grammar tests proved the
  parser; nothing proved `python -m …cli.main` runs anything at all (F2). ADR-8
  itself came from the same shape one level down: fields validated, the sum the
  engine derives from them never simulated.
- **Decision:** Every pipeline in this repo carries at least one assertion over
  its **composition**, not only its parts. For betb2b → engine, that is: a
  scrape result fed to `build_ingest_matches` and checked for the scope set it
  should contain. Fixtures may stand in for the network, but the seam between
  stages must be crossed by the test, not assumed.
- **Consequences:** Slightly slower suites, and fixtures that must be refreshed
  when the feed shape moves. Accepted — three High findings in one session all
  lived in seams that more unit tests could not reach. Corollary: a regression
  test for a bug must be **seen red** against the unfixed code (mutate the fix,
  run, confirm failure). An unfalsified regression test is a claim, not a guard.

---

## ADR-10: ADR-7 is blocked downstream — the engine stores one prediction per match_id, not per (match_id, scope) (2026-07-22, Session 28)

- **Status:** accepted (finding); ADR-7 remains correct on the scraper side but cannot be realized until the engine changes
- **Context:** The first-ever `--subgames --ingest` run (2026-07-22, linebet basketball prematch, via the user's bore.pub proxy) produced **65 requests from 11 events across all 9 scopes** — the half and quarter scopes had never been generated before (`5f6e6db`). POST → HTTP 200, `succeeded=36 failed=29 added=3 updated=62`.

  `added=3` was the tell: 28 half/quarter requests were entirely new `(match_id, scope)` pairs, so a scope-keyed store would have added at least 28. Querying `/api/predictions` afterwards:

  **11 of 11 matches store exactly one record, and it is the LAST scope sent.**

  Send order per event is FULL_MATCH → halves → quarters → HOME_TEAM_TOTAL → AWAY_TEAM_TOTAL, so every match ends up stored as `AWAY_TEAM_TOTAL` — except the one event with no away-total market, stored as `HOME_TEAM_TOTAL`. Observed: 10 AWAY + 1 HOME from this run. Zero half or quarter records stored, despite 16 of them being accepted.

- **Decision:** Record this as a downstream blocker and stop attributing it to scraper-side causes. The scraper's job — one match → N scoped `PredictRequest`s with scope-matched lines and H2H — is done and now verified against live data. Realizing it requires **scorewise-engine** (a different repo) to key its prediction store by `(match_id, scope)`.

- **Consequences:**
  1. Until the engine changes, `--subgames` costs ~6 extra requests per event and 54 of every 65 scoped predictions are discarded on arrival. Use it to validate the pipeline, not to feed production.
  2. **This resolves the "HOME_TEAM_TOTAL asymmetry"** that Session 27 investigated (10 sent, 1 stored, 9 AWAY) — it is the identical signature, not engine state from old runs and not market data. See the CORRECTION above.
  3. The 29 failures are a separate, understood cause: the engine requires strict H2H and only 4 of 11 events had any (the rest returned `204 No Content` from the statisticfeed endpoint). 36 accepted = exactly the 36 requests carrying H2H. Not a defect.
  4. **ADR-8 confirmed on live data:** team-total H2H now sums to 86 / 91 / 109 against lines of 90.5 / 84.5 / 114.5. Pre-fix it would have compared game totals of 175 / 154 / 214 against those same lines — the false-HIGH mechanism, observed directly rather than inferred.

---

## ADR-10 RESOLVED (2026-07-22, Session 28) — the fix was written but never deployed; ADR-7 now works end-to-end

The engine-side fix existed the whole time: `152bd48` in scorewise-engine
("merge predictions by (match_id, scope) not match_id alone"), authored
08:35 UTC and pushed — **2h33m before** the run that measured the old
behaviour. It was not live, because the deploy failed at the build stage and
**a failed Railway build leaves the previous deployment serving**. Every
endpoint answered normally while running stale code. Root cause: the service's
Root Directory was the repo root, which has no Python project (the app is at
`repos/engine/`); Railpack could not detect a language. Fixed on the Railway
side by the operator.

**Verified live, then verified end-to-end** (same 11-event scrape, re-ingested
from `data/telemetry/betb2b/result_snapshots/linebet_list_prematch_20260722_110956_1.json`):

```
65 requests sent, 65 stored — every scope survives
FULL_MATCH 11/11 | FIRST_HALF 7/7 | SECOND_HALF 5/5
QUARTER_1..4 6/6, 5/5, 5/5, 5/5 | HOME_TT 11/11 | AWAY_TT 10/10
11 matches, 3–9 scopes each (was: 11 matches, exactly 1 scope each)
added=64 updated=1 — the 1 update was a probe record
```

**ADR-7's premise is delivered.** `--subgames` is now a production feed, not
just a validation tool.

**What generalizes (this is the part worth keeping):** a deployment that fails
is invisible from the outside — the old one keeps serving and every probe
against the API answers 200. Two sessions attributed stale *deployment*
behaviour to the scraper's data and the engine's code. Neither was wrong about
what they measured; both were wrong about what they were measuring. **A green
push is not a live fix.** Assert the new behaviour against the deployed
service before drawing any conclusion from its output — for this contract the
one-line probe is: POST a `(match_id, scope)` pair whose `match_id` exists but
whose scope does not; `added: 1` means the fix is live, `added: 0` means it is
not.

**Still open:** the 29 of 65 failures are unchanged and understood — the engine
requires strict H2H and only 4 of 11 events had any (statisticfeed returns 204
for minor leagues). Backlogged separately as a coverage question, not a defect.

---

## ADR-11: BetB2B data moves to a shared Railway PostgreSQL; apps/services integrate via the DB, reached through the Python API (2026-07-25, spec kickoff)

- **Status:** accepted (design; completes the "future Postgres" note in ADR-6 and supersedes ADR-1 point 5's Volume-mounted SQLite; no code shipped yet — this ADR authorizes the migration spec)
- **Context:** The betb2b product data (`data/betb2b/odds.db`) and the Selector Engine's operational state (`data/adaptive.db` feature flags + `data/audit_log.db`) are all file-based **SQLite**. Two forces make that a ceiling: (1) Railway's filesystem is ephemeral — every redeploy wipes the DB unless a Volume is mounted (ADR-1 point 5; RAILWAY.md), and even then SQLite can't be safely shared by concurrent network clients; (2) the operator wants to link independent services — **scorewise, the scraper, and apps (mobile / website / desktop)** — through **one shared database as the integration point, not shared codebases**. SQLite (single-writer, file-local) cannot be that shared store. The betb2b schema is already a clean relational model (`sports`, `leagues`, `teams`, `events`, `odds_snapshots`, `h2h_games`, `scrape_runs`, …) with FK relationships and ISO-8601 timestamps — deliberately kept "Postgres-portable" since ADR-6. The stack already depends on **SQLAlchemy 2.0**, so the engine swap is mostly a connection-string change, not a rewrite. Access-model decision (operator, 2026-07-25): **all apps/services reach the data through the project's Python/FastAPI layer**, not by connecting to the DB directly.
- **Decision:**
  1. **Engine: PostgreSQL, hosted as the Railway Postgres plugin** — same platform as the deployed control plane (ADR-1), `DATABASE_URL` injected by Railway, private networking between the API service and the DB. No separate infra to manage or bill.
  2. **Rejected: Supabase (or any direct-to-DB BaaS).** Its value-add — auto REST/realtime APIs, per-platform client SDKs, row-level security — is dead weight here because every consumer goes through our own FastAPI service (the access-model decision above). The FastAPI layer is the single front door; only the scraper + API hold DB credentials, giving a clean trust boundary. Revisit ONLY if a future requirement has app clients talking to the DB directly (that would supersede this ADR).
  3. **Consolidate the three SQLite DBs into the one Postgres instance** as separate tables/schemas: betb2b product data (`odds.db`), plus the Selector Engine's `adaptive.db` (feature flags/failure events) and `audit_log.db`. This also retires ADR-1 point 5's Volume mount + `ADAPTIVE_DB_PATH` env var (their whole purpose was to survive redeploys — Postgres does that natively).
  4. **Keep InfluxDB separate.** `influxdb-client` is for metrics/observability (a time-series/telemetry concern), NOT shared business data. Do not fold it into Postgres.
  5. **Add Alembic for schema migrations.** The repo has none today; once multiple services depend on the schema, versioned migrations are mandatory, not optional.
  6. **Keep SQLite as the local-dev / test fallback.** Connection is env-driven (`DATABASE_URL`); local runs and CI stay on SQLite files, only deployed environments point at Railway Postgres. The store code already reads/writes via SQLAlchemy, so both back ends are supported by one code path.
- **Consequences:**
  - The SQLite-isms in the existing schema need porting: `INTEGER PRIMARY KEY` → `IDENTITY`/`SERIAL`; `TEXT` timestamps (`start_time`, `first_seen`, `extracted_at`, …) → `timestamptz`; `success INTEGER` (0/1) → `boolean`. A one-time data copy (SQLAlchemy script over the shared models) moves existing rows.
  - Index the hot query paths that back ADR-6's three queries: at minimum `odds_snapshots(event_id, extracted_at)` and `events(start_time)`; the cross-skin join already keys on the shared backend `event_id`.
  - The scorewise-engine ADR-7/ADR-10 pipeline is unaffected by this change — it talks to the engine over HTTP, not to this DB. This ADR is about the scraper/product data store and the services that read it, not the prediction store.
  - Future agents: do NOT reach for Supabase/Firebase/Mongo for this data — the decision is Postgres-relational, and the access path is via the Python API (points 1–2). Do NOT merge InfluxDB into it (point 4). If file-SQLite is still in a deployed path after this ships, that's the migration being incomplete, not a second supported deployment mode.


---

## ADR-11 PROGRESS (2026-07-25, Session 29) — code-layer foundation shipped; Railway cutover pending

Session 29 shipped the four code-layer increments that make ADR-11 executable,
all verified green on the SQLite fallback (189 tests):

1. `e03da90` — shared env-driven engine factory (`src/core/db.py`): `DATABASE_URL`
   → Postgres (deploy), else SQLite fallback. One SQLAlchemy code path, both
   backends. Deps: `psycopg[binary]` + `alembic` added.
2. `3629183` — 9 adaptive repository `create_engine(f"sqlite:///...")` sites →
   `get_engine(db_path)`. The adaptive/SQLAlchemy half of ADR-11 point 3.
3. `39e1c02` — portable betb2b ORM models (`src/sites/betb2b/models.py`) + ADR-11
   hot-path indexes. Ports the SQLite-isms: `SurrogatePK = BigInteger().with_variant(Integer, "sqlite")`
   (autoincrements on both backends), `Boolean` for success/is_live/is_suspended,
   `DateTime(timezone=True)` for timestamps (→ timestamptz on Postgres).
4. `c0802a2` — Alembic baseline (`c7ea08fedb55`, 27 tables) + one-time data-copy
   script (`scripts/migrate_sqlite_to_postgres.py`, proven to move rows).

**Two premise corrections from discovery** (future agents: read these before
quoting ADR-11's text):
- The store is **two SQLite files, not three**: `audit_log` is a *table* in
  `adaptive.db` (AuditEventRepository uses the adaptive `Base`), not a separate
  file.
- ADR-11's "the engine swap is mostly a connection-string change, not a rewrite"
  holds **only for the adaptive/SQLAlchemy side**. The betb2b store is raw
  `sqlite3` with hand-written SQL; its schema needed a real port to ORM models
  (3-c) before it can host on Postgres, and its **persist path is still raw
  sqlite3** (F2 — the largest remaining piece, backlogged).

**Still open (operator-side, needs Railway access this sandbox lacks):**
provision the Postgres plugin → set `DATABASE_URL` → `alembic upgrade head` →
run the copy script → swap the betb2b persist path to ORM (F2) → retire ADR-1
point 5's Volume mount + `ADAPTIVE_DB_PATH` (ADR-11 point 5; `ADAPTIVE_DB_PATH`
stays for local/CI SQLite only). Until F2 ships, the betb2b data still lands in
`odds.db` — the Postgres path exists at the model/migration level but the
scraper doesn't write through it yet.

---

## ADR-12: The scraper gets a remote-control API on the existing FastAPI service — single-flight background jobs, API-key auth (2026-07-27)

- **Status:** accepted (deliberately deviates from ADR-1 point 4 for the control-plane MVP — see below)
- **Context:** The betb2b scraper was CLI-only. The operator wants to drive it remotely (trigger scrapes, monitor, read odds) from apps/other services. Three forks were decided with the operator: (1) **deployment model** — Railway hosts the control plane (API + DB); scrapes execute against whatever proxy is configured, failing cleanly if none, because the Railway egress IP is WAF-blocked (203) and cannot scrape betb2b directly (backlog: "IP is WAF-blocked"); (2) **execution** — scrapes run as background jobs inside the API web service (not a separate worker); (3) **surface** — API-only (no website yet), secured by an API key.
- **Decision:**
  1. **Add `/api/scraper/*` to the existing `src/api/main.py` FastAPI app** (already the Railway-deployed service, ADR-1): `POST /runs` (queue), `GET /runs[/{id}]` (monitor), `GET /skins|sports|counts`, `GET /odds/{event_id}`.
  2. **Auth: `x-api-key` vs `SCRAPER_API_KEY` env, fail-closed** — unset ⇒ 503 (feature disabled), wrong/missing ⇒ 401. No key handling beyond a constant-time compare; the operator sets the secret in Railway.
  3. **Execution: single-flight background jobs in-process.** A `scraper_jobs` table is the queue/status; `ScraperService` (started in the app lifespan) drains it via `store.claim_next_job` — **one scrape at a time** (one Chromium bootstrap; ADR-1's memory concern). Jobs go queued→running→succeeded/failed; orphaned `running` rows are reset on startup. **Deploy with `GUNICORN_WORKERS=1`** so single-flight is global (the DB claim guards regardless, but one worker keeps it deterministic).
  4. **Proxy from `BETB2B_PROXY_*` env.** No proxy / WAF block ⇒ the job is marked `failed` with the reason, never a hang — the caller polls a clear status.
  5. **Store stays SQLite** (`BETB2B_DB_PATH`, on the Railway Volume). Apps read betb2b data **through this API**, which is exactly ADR-11's "apps reach the data via the Python API, not direct-to-DB" — so the Postgres cutover (ADR-11) is orthogonal and not required for remote control.
- **Consequences:**
  - **Deviation from ADR-1 point 4** ("do NOT run scrape jobs inside the API service"). Accepted deliberately for the control-plane MVP: the hybrid scraper only bootstraps a browser briefly, single-flight caps it at one Chromium, and a separate worker service (ADR-1's preference) is more infra/cost than this stage warrants. If scrape volume grows or API latency suffers, promote the runner to a separate Railway worker consuming the same `scraper_jobs` table — the queue/claim seam is already there, so it's an additive change, not a rewrite. Revisit then.
  - The deployed scraper is only as reliable as its proxy. The bore.pub tunnel (operator's laptop, rotating port) is fine for validation but not production; a stable residential/KE proxy is the real dependency for always-on cloud scraping (backlogged).
  - `GUNICORN_WORKERS=1` trades API concurrency for deterministic single-flight. The control plane is low-traffic, so this is fine; if the API needs more workers later, move the runner to its own service (above) rather than raising workers.
  - Future agents: keep scrape execution behind the `scraper_jobs` queue. Do NOT add a second endpoint that scrapes inline in the request path (it would blow the request timeout and bypass single-flight).

---

## ADR-13: Supabase is the shared data + realtime + auth layer; Railway stays the compute — supersedes ADR-11's access model (2026-07-27)

- **Status:** accepted (supersedes **ADR-11 point 2**'s "apps reach the data through the Python API, not direct-to-DB"; keeps ADR-11's Postgres-relational engine choice; refines ADR-1)
- **Context:** ADR-11 chose Railway Postgres behind the Python API because the then-stated access model was "apps go through FastAPI." Since then the project gained a concrete **real-time, multi-client** direction: a live-progress UI (scrape `phase`, ADR-12) and planned **client apps + admin apps** consuming live odds. That is precisely the access model ADR-11 said would flip the decision toward Supabase. The operator chose the topology **scraper → Supabase → apps**.
- **Decision:**
  1. **Supabase (managed Postgres) is the shared store.** Its differentiators are now used, not wasted: **Realtime** (apps subscribe to odds/`phase` changes — no polling), **Auth** (app users), **RLS** (per-client read policies), and **client SDKs** (web/mobile/desktop).
  2. **Railway remains the compute tier** — the scraper (Playwright/Chromium + proxy egress) and the control API (ADR-12). **Supabase cannot run the scraper** (Edge Functions are Deno; no Chromium, no long jobs), so this is a hard split, not a migration off Railway.
  3. **Data flow:** the Railway scraper **writes to Supabase Postgres** via SQLAlchemy (`DATABASE_URL` = Supabase **pooler** URL). Apps **read Supabase directly** (Realtime + REST + RLS). The `scraper_jobs` table lives in the same store so apps read live job status/progress over Realtime alongside odds.
  4. **Control (trigger) stays on the Railway API** for now (admin apps call `POST /api/scraper/runs`, then watch progress via Supabase Realtime). A later option (noted, not committed): admin apps insert a job row into Supabase and the Railway runner consumes it from there — fully Supabase-mediated control.
- **Consequences:**
  - **Enabling work (ADR-11 F2, now the active task):** the betb2b store's write path is still raw `sqlite3` (`store.persist_result` + job helpers). It must be ported to **SQLAlchemy** (one code path: SQLite locally/CI, Supabase Postgres deployed) so the scraper writes to Supabase. The ORM models (now incl. `ScraperJob`) + `core/db.py` + `scripts/migrate_sqlite_to_postgres.py` already exist; the port + a `DATABASE_URL`-driven persist is what remains.
  - **Two providers.** More surface than Railway-alone, but each does what it's best at (Railway = browser compute; Supabase = data/realtime/auth). Accepted deliberately for the realtime-UI payoff.
  - **Operator prerequisites (only the operator can do):** create the Supabase project; take the **pooler** (pgBouncer, port 6543) connection string; set `DATABASE_URL` on the Railway service (never shared with the agent — the code reads it from env); run `create_all`/the migration to build the schema + copy existing `odds.db`; enable **Realtime** on the read tables; author **RLS** policies (client apps: read-only on odds/events; admin apps: broader). Use the **pooler** URL for the scraper's many short writes, not a direct connection.
  - **High-write caution:** `odds_snapshots` is time-series; apps should subscribe to **filtered** Realtime changes (a specific event/match), not the whole table. The change-only dedup already caps write volume.
  - Future agents: do NOT try to run the scraper on Supabase. Keep compute on Railway; Supabase is data/realtime/auth. Do NOT point the scraper at a **direct** Supabase connection under load — use the pooler.

---
## ADR-14: The scraper↔engine link is the shared Supabase DB, not direct HTTP — supersedes ADR-7's ingest export (2026-07-27)
- **Status:** accepted (supersedes ADR-7/ADR-8/ADR-10's direct HTTP `/api/ingest` link to scorewise-engine; refines ADR-13)
- **Context:** ADR-7/8/10 built a point-to-point chain: the scraper's `export/scorewise.py` builds scoped `PredictRequest`s (match_total = the totals rung whose over-odds is nearest 1.85; H2H per scope) and POSTs them to the engine's `/api/ingest`; the engine holds predictions in an in-memory `_store` + `predictions.json` on disk and pushes them to the website by webhook. That chain is fragile (the engine store is ephemeral on Railway; the webhook died silently once — see the website's `engine-auto-sync`) and couples three services over a hand-kept HTTP contract. With betb2b now writing structured odds/events/teams/markets/h2h/scores to a shared **Supabase** (ADR-13), the operator's decision is: **integrate via the DATABASE, not direct communication — the scraper and the engine both read/write Supabase.**
- **Decision:**
  1. **The scraper's job ends at Supabase.** It writes the betb2b tables (ADR-13) and does **not** POST to the engine. The direct-ingest exporter (`export/scorewise.py`, the `/api/ingest` client) and the `--ingest` flag are **retired**.
  2. **The engine reads its inputs from Supabase.** The scope-selection logic that lived in the scraper's exporter (ADR-7/8: pick the match_total line by over-odds ≈ 1.85; derive H2H per scope incl. team-total zeroing) **moves into the engine** (its own ADR-1), which reads the betb2b tables directly. The scraper no longer knows the engine's contract.
  3. **The engine writes predictions to Supabase**, keyed by `(event_id/match_id, scope)` (ADR-10's keying, now as durable DB rows); the website reads them from Supabase. No engine→website webhook.
- **Consequences:**
  - Supabase is the integration bus; the three services decouple — no point-to-point HTTP, no shared HTTP contract to keep in sync, and the ADR-10 fragility class (ephemeral engine store, silent webhook death) is resolved by a durable single source.
  - Retires on the scraper side: `export/scorewise.py` + `--ingest`. The engine side (its `/api/ingest`, disk `_store`, webhook_sender) is retired in **scorewise-engine ADR-1**.
  - The ADR-7/8 scope logic is **re-homed in the engine**, not lost. The scrapamoja market-mapping (the `(G,T)` taxonomy, sub-games) stays — it's what populates the betb2b tables the engine reads.
  - Follow-up: define the Supabase `predictions` table shape jointly with the engine (event_id FK + scope + recommendation/confidence/lines).

---
## ADR-15: The full odds pipeline is proxy-free — GetSportsZip discovery works from any IP (2026-07-27)
- **Status:** accepted (finding + direction; resolves the proxy dependency flagged in ADR-12/13 and the geo-curated-top-leagues coverage limit)
- **Context:** The scraper needed an allowed-country **residential** proxy (the operator's bore.pub tunnel) because the SPA/browser cookie-harvest bootstrap **and** the landing-page league discovery are WAF-blocked (HTTP 203 → `/block`) from datacenter IPs — the block is **datacenter-IP fingerprinting, not geo** (backlog 2026-07-17). ADR-5 already found the per-match `GetGameZip` returns 200 from a blocked datacenter IP. The one open question was **proxy-free DISCOVERY** (which leagues/games exist) without the browser.
- **Discovery (verified live — NO proxy, NO cookies, NO browser, from a WAF-blocked datacenter IP):**
  - `GET /service-api/LineFeed/GetSportsZip` returns the **full sports→leagues tree**: `Value[]` per sport; each sport's `L[]` lists every league with `LI` (champ id), `GC` (game count), name, country. Basketball (`I=3`): 14 leagues / 37 games. **200 OK, 190 KB.**
  - Chained proxy-free end-to-end: `GetSportsZip` (leagues) → `GetChampZip(LI)` (events) → `GetGameZip(id)` (odds — WNBA game, **436 markets**). The **entire pipeline runs proxy-free.**
  - The SW-gated aggregate feeds (`GetSportsShortZip` / `Get1x2_VZip` / `WebGetTopChampsZip` / `GetChampsZip`) stay **406** regardless of IP/cookies — but `GetSportsZip` is **not** gated and makes them unnecessary.
  - **Confirmed across the family:** 7/8 skins return identical 200 (22bet, 888starz, betwinner, helabet, linebet, megapari, melbet — all 93 sports / 14 basketball leagues / 37 games). **paripesa = 203** (a domain-config outlier, not a backend gate).
- **Decision:** The scraper's discovery + fetch no longer need the browser or the proxy. Build a browser-less **"direct mode"**: `GetSportsZip` → `GetChampZip` → `GetGameZip` → persist to Supabase, with **no Playwright bootstrap, no session cookies, no proxy.** The existing browser/session/landing-HTML path becomes a fallback (or is retired).
- **Consequences:**
  - The Railway scraper **drops the proxy for the odds pipeline entirely** — no bore.pub tunnel, no residential-proxy dependency, no Railway region change needed. The backlog "stable production proxy" item is largely moot for odds.
  - **Bonus coverage:** `GetSportsZip` lists **all** leagues (incl. WNBA), not the landing page's ~6–8 geo-curated *minor* leagues — this also resolves the "full-card discovery" limitation.
  - Still to verify (not blockers): **H2H** (statisticfeed) — does it work cookie-less like the odds feeds? If not, H2H runs on an occasional proxy pass; odds stay proxy-free. **paripesa** needs a domain fix (separate).
  - `GetSportsZip`'s `GC` counts let discovery prioritise leagues that actually have games. Direct mode is the immediate build.

---
## ADR-16: Finished-match results + prediction validation — state-driven, cross-repo (2026-07-28)
- **Status:** accepted (direction; the results-capture endpoint is open research)
- **Context:** The state-aware scheduler (ADR-15 follow-up, `66f9d30`) has **scheduled + live** passes but no **results** pass. The Line/Live feeds **drop a match once it ends**, so a finished match's final score is not reachable via `GetGameZip`. Final scores are what **grade predictions** (did OVER/UNDER hit? did the team win?) — the whole research/validation loop needs them, and nothing in the new pipeline captures them yet.
- **Decision:**
  1. **A results pass (scrapamoja scheduler) captures each finished match's final score once** — matches with `start_time + ~2.5h < now` and no result yet — and writes it to Supabase (`event_states` final score / a result field on `events`). **State-driven** (ADR-14): it queries the DB for finished-without-result matches; no cross-scraper trigger.
  2. **Grading is the engine's job** (its ADR-1 domain, not the scraper's): the engine reads *finished-with-result matches + ungraded predictions* from Supabase → marks **HIT/MISS** → writes back to `predictions`. DB-mediated; optionally Supabase-Realtime-accelerated. Track in the engine's own session.
  3. **Open research (blocks the scraper side):** *which endpoint returns a finished match's final score once it's off the Line/Live feed* — candidates: a results/history `statisticfeed` endpoint, the game `SC` via a different feed, or the H2H feed (which lists the just-finished game with its score). Find it live from a datacenter IP, proxy-free — same method as the `GetSportsZip` discovery win (ADR-15).
- **Consequences:** results are a research + build item, not shipped. Once the endpoint is found, the results pass slots in as the scheduler's third pass. Until then predictions are *made but not graded* → the website can't show ✓/✗ and there's no accuracy feedback. This is the highest-value open item for the product loop.

---
## ADR-17: Fetch concurrency + persist batching — the scaling model, with datacenter-IP rate discipline (2026-07-28)
- **Status:** accepted (direction)
- **Context:** With the browser gone (ADR-15), fetch is independent `httpx` calls but still **sequential** behind a rate limiter (120/min in direct mode). Persist batched the odds (`0053ff5`), but `h2h_games` (one `.returning()` insert each — ~586/run), the per-event dedup queries, and team lookups are still **one-round-trip-per-row** → the ~5.5-min persist on the live 102-event / 10,686-odds Railway run. The scheduler's tight live cadence (ADR-15/18) needs both faster.
- **Decision:**
  1. **Fetch: bounded concurrency, not a slow sequential rate.** Replace the sequential rate-limiter with a semaphore-bounded `asyncio.gather` over `GetGameZip`/`GetChampZip`/H2H (default ~8, `BETB2B_CONCURRENCY`). The un-gated feeds tolerate it (single-request proven; ramp under monitoring).
  2. **Persist: batch the remaining per-row work.** `h2h_games` via `insert().returning()` executemany (then batch `h2h_period_scores`), **one** dedup query across all event ids, an in-memory **team cache** — target ~5.5 min → ~30 s.
  3. **Datacenter-IP rate discipline (recorded constraint):** high-*volume* proxy-free access is **UNPROVEN** — only single requests are. Start conservative (concurrency ~8, live cadence ~10–15 s), watch for `429`/`403`/`203`, ramp deliberately. If the IP gets blocked, the proxy returns as a **fallback** — ADR-15 direct is opt-in, not exclusive.
- **Consequences:** 5–10× faster fetch + persist → 5–15 s live polling becomes viable. Change-only dedup keeps DB writes sane regardless of cadence. Risk: abuse-limit blocking under aggressive settings — mitigated by the conservative defaults + the proxy fallback path. Do NOT remove the rate cap entirely; bound concurrency instead.

---
## ADR-18: The scheduler runs as a dedicated always-on worker, separate from the API job runner (2026-07-28)
- **Status:** accepted (direction)
- **Context:** The state-aware scheduler (ADR-15/16) is a **continuously looping** process (scheduled ~3h + live ~15s + results). The remote-control API (ADR-12) runs **single-flight, request-triggered** background jobs inside the web service — right for on-demand scrapes, but a wrong shape for an always-on loop (it would tie up the single worker indefinitely).
- **Decision:** Run the scheduler as a **dedicated Railway worker service** (`python -m src.sites.betb2b.cli schedule …`), **separate** from the API web service — one always-on process, single-flight internally, restart-safe (each pass is idempotent + change-only, so a restart re-runs harmlessly). Do NOT run it inside the ADR-12 job runner. Both processes write to the **same Supabase**: the API stays for manual/ad-hoc triggers, the worker for continuous cadence.
- **Consequences:** a second Railway service (cost) for clean separation — the always-on scheduler can't starve the API, and the API's `GUNICORN_WORKERS=1` is unaffected. Env for the worker: `DATABASE_URL` (Supabase pooler) + `BETB2B_DIRECT=1` (proxy-free) + the cadence vars (ADR-15). Single-flight is **per-process**, so running the same skin's scheduler *and* a manual API job at once isn't coordinated — harmless thanks to change-only dedup, but avoid it deliberately. Alternative rejected: a cron-style external trigger — the live 15s cadence is too tight for cron and a persistent process is simpler.

---
## ADR-19: Market naming — adopt the SPA's new-builder GetGameZip feed (MEC categories + SG sub-games); defer exotic per-group labels (2026-07-28)
- **Status:** accepted (direction)
- **Context:** `markets.name` persists as `"G=27"` for group ids not in `markets.py` (~15 of ~64 named). Traced the SPA's naming end-to-end (proxy + Playwright — see `reviews/2026-07-28-market-naming-mechanism.md`): the feed carries only numeric `G`/`T`; the SPA composes names **client-side** (`name = groupNames[GS] ?? getMarketGroupTemplatesByGroupId(G).name`, feed `G` = a "foreignId" resolved against **per-sport bet-model templates**). The `bets_model_short` files the CDN serves are a **different id-space** (verified: they can't reproduce a single basketball market — feed `G=17` Total → "Match Result Including Overtime"), and the odds grid is **canvas-rendered** (no DOM text). So there is **no static feed-`G`→name file** to import. BUT the SPA fetches a **new-builder** `GetGameZip` variant our scraper doesn't use, whose response includes real names: `MEC[]` (filter categories) and `SG[].TG` (sub-game names).
- **Decision:**
  1. **Switch the scraper's `GetGameZip` to the new-builder params** — `isNewBuilder=true&GroupEvents=true&marketType=1&countevents=250` (id via the event's `CI`). Parse `MEC` (category names: Total/Handicap/Points/Result+Total/Special/…) and `SG.TG` (sub-game names: Rebounds/Assists/3-pt FG/…) straight from the feed.
  2. **Name markets by category + verified `(G,T)`** — keep the ADR-7 verified `(G,T)` map for core markets (1x2/totals/handicap/individual totals/moneyline); use the `MEC` category as the group label where `(G,T)` is unknown, replacing the bare `"G=<n>"`. Capture sub-game names as a new dimension.
  3. **DEFER exact exotic per-group labels.** They require replicating the client's sport-aware template resolution (deep, uncertain) or ADR-7 render-and-read cross-map. Not worth it for a cosmetic field while odds + `(G,T)` ids are already correct. Keep the honest `"G=<n>"` fallback for the unmapped remainder. **Never guess names.**
- **Consequences:** meaningfully-named markets across the board + a new sub-game dimension, from a contained feed-param change. Must validate the new-builder response parses cleanly for **prematch AND live**, and that `CI`-vs-`I` addressing works for our discovery ids. Rejected alternatives: (a) import `bets_model_short` — wrong id-space, would mislabel; (b) full client-logic replication now — disproportionate effort for a cosmetic label.
- **ADDENDUM (2026-08-05, Session 39) — SOLVED. The naming table is `bets_model` indexed by `GS` (groupShortId), NOT feed `G`.** The 2026-07-28 recon's "wrong id-space" verdict was an *indexing* error: it keyed the bet-model files by feed `G` (or the internal group id) and got garbage. The SPA's own composition is `name = groupNames[GS]` — and `groupNames` is the **union of every template file's `GN` sub-map, which is keyed by `GS`**. Files (gzipped JSON, globally reachable — **no proxy/browser needed**): `https://v3.traincdn.com/genfiles/cms/betstemplates/bets_model_short_en_<0..77>.json`, structure `{templateId: {G: {"N": groupName, "GN": {GS: name}, "M": {...}}}}`. Unioning all 78 files' `GN` gives **5,419 `GS`→name entries with ZERO conflicts** — a static, authoritative table that names EVERY group the feed can carry (verified against the real fixture: every `(G,GS)` — core AND exotic `G=91/92/2766/2768/…` — resolves correctly). Our feed already extracts `gs_id` on every selection, so it drops straight in.
  - **Shipped:** `data/market_group_names_en.json` (committed) + `scripts/fetch_market_names.py` (regenerator) + `markets.py::DEFAULT_MARKET_GROUP_NAMES` and a rewritten `lookup_market` — name order is verified `(G,GS,T)` → verified `(G,T)` → **GS table** → T-only → G-only → `G=<n>`; the selection SIDE still comes from the verified maps / T-table (the GS table names the group only). Exotic `G=<n>` labels are GONE.
  - **Bug the GS table caught:** the hand-verified ADR-7 map had `(14,22,182/183)` → "To Win Match". WRONG — the SPA names `GS=22` "Total Even", and the fixture confirms it (odds 1.84/1.82, **no line**, symmetric → an Even/Odd market, not a moneyline). Those rows were removed from `DEFAULT_MARKET_GST`/`DEFAULT_MARKET_GT` so it resolves to "Total Even" via the GS table.
  - **What earlier failed (for the record, so no one re-treads it):** render-and-read via DOM/Vue/plain-network IS impossible on this SPA (labels are canvas; feed + betting-app JS + dictionaries are all service-worker-mediated/cached → invisible to page-network; prod Vue exposes no devtools hook). The win came NOT from the browser but from fetching the static CDN dictionary directly and indexing it by the RIGHT key (`GS`). **Selection-side labels for exotic groups** (Over/Under/Even/Odd/etc.) are the only remaining gap — resolvable from the same files' `M` sub-map if ever needed; currently honest `T=<n>`.

---
## ADR-20: The results endpoint is statisticfeed `v1/Game` (`entity.status==3`) — resolves ADR-16's open research (2026-07-28)
- **Status:** accepted (closes the open research in ADR-16 §3; the results pass is now a build)
- **Context:** ADR-16 deferred *which endpoint returns a finished match's final score once it's off the Line/Live feed*. Found it live, proxy-free from a datacenter IP (recon: `reviews/2026-07-28-results-endpoint.md`).
- **Decision:** the results source is **`GET /service-api/statisticfeed/api/v1/Game?id=<id>&lng=en&ref=<partner>&fcountry=<country>&gr=<gr>`** — same host/grammar as our H2H/stats calls, un-gated. Its **`entity`** object carries `status` (**3 = finished**, 2 = live), final **`score1`/`score2`**, **`winner`** (1/2), and **`periods[]`** (Q1–Q4 finals). Verified: it **retains finished games for weeks** (games 6–18 days old still return full results), so the LineFeed/LiveFeed dropping the match does not lose the score. `v1/Game` is a **superset of `/Game/h2h`** (also returns teams + gameShorts).
- **Results-pass design:**
  1. Capture `entity.id` (statisticfeed game id) + status during live/scheduled scraping — fold it into enrichment by using `v1/Game` in place of the separate `/Game/h2h` call (one request, both).
  2. Results pass: for `start_time + ~2.5h < now` and no result yet → `v1/Game?id=<entity.id>` (retained); on `status==3` write final `score1/score2` + `winner` + `periods` to Supabase. Map team1/team2 → home/away by LineFeed O1/O2 order (same as the H2H `score1/score2` convention already stored). Try `id=<LineFeedEventId>` as a shortcut; keep the `entity.id` path as the guarantee.
  3. Engine grades HIT/MISS from the stored result (engine ADR-1/2, DB-mediated).
- **Consequences:** the scheduler's third pass (ADR-16 §1) is now implementable — the whole predict→grade→accuracy loop unblocks. Schema touch: a final-result store target (result fields on `events`, or a terminal `event_states` row) + a `stat_game_id` on `events` to hold `entity.id`. Rate discipline (ADR-17) still applies to the results polling. Optional follow-up: consolidate the H2H enrichment onto `v1/Game`.
