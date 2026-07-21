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
