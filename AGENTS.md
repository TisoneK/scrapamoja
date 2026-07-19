# Agent Instructions — Scrapamoja (scorewise-scraper)

<!-- Initialized 2026-07-18 from .context/core/templates/AGENTS.md.
This is the live agent instruction file — read this FIRST. -->

This repo uses the `.context/` protocol: persistent agent memory plus a
vendored copy of the full workflow, committed to git. **Before doing any
work, read `.context/kickoff.md` and follow it.** It routes you — local
IDE agent or cloud/sandbox agent — to the right instruction set in
`.context/core/rules/`.

## Project Overview

**Scrapamoja** (package name: `scorewise-scraper`) is a production-grade,
Python 3.12+ web scraping framework with a semantic selector engine,
adaptive failure recovery, and multi-site support. It is designed to
scrape sports-betting sites for odds data, handling anti-bot measures,
geo-blocking, and selector drift.

### Core Architecture

```
src/
├── api/                    # FastAPI control plane (feature flags, failures, audit)
├── browser/                # Browser lifecycle, stealth, fingerprinting, sessions
├── config/                 # Global settings (settings.py)
├── core/
│   ├── shutdown/           # Graceful shutdown coordinator
│   └── snapshot/           # Browser-state capture system (screenshots, HTML, artifacts)
├── extraction/             # Data extraction mode router
├── extractor/              # Field-level extractors (text, numeric, date, list, attribute)
├── interrupt_handling/     # SIGINT/SIGTERM handling, checkpointing, resource cleanup
├── navigation/             # Page navigation, route discovery, path planning, proxy management
├── network/                # HTTP client (httpx), HAR export/replay, proxy management, session harvesting
├── observability/          # Events, logger, metrics
├── resilience/             # Retry, circuit breaking, failure classification, abort management
├── selectors/              # Semantic selector engine (CSS, XPath, text-anchor, adaptive, fallback chains)
│   ├── adaptive/           # Adaptive engine: confidence scoring, failure detection, DOM analysis, snapshot capture
│   │   ├── api/            # FastAPI sub-app (health, audit, failures, triage, confidence, feature flags)
│   │   ├── db/             # SQLAlchemy models + repositories (SQLite)
│   │   └── services/       # Business logic (failure detection, stability scoring, DOM analysis)
│   └── websocket/          # WebSocket health client
├── sites/                  # Per-site scraper implementations
│   ├── _template/          # Template scaffolding for new sites
│   ├── base/               # Base classes (BaseSiteScraper, plugin system, config management)
│   ├── betb2b/             # ★ BetB2B family base scraper (parameterised by skin YAML)
│   ├── flashscore/         # Flashscore scraper
│   ├── github/             # GitHub scraper (example)
│   ├── linebet/            # Linebet-specific scraper (legacy; being absorbed into betb2b/)
│   └── ...                 # quotes, wikipedia, direct
├── stealth/                # Anti-detection (fingerprinting, behavior simulation, consent handling)
├── storage/                # Storage adapter
├── telemetry/              # Telemetry system (collectors, processors, reporting, alerting, storage)
└── utils/                  # Shared exceptions
```

### Key Design Decisions (ADRs in `.context/memory/plans/decisions.md`)

| ADR | Topic | Summary |
|-----|-------|---------|
| ADR-1 | Railway deployment | Deploy FastAPI control plane via Dockerfile; no scrape jobs in the API service |
| ADR-2 | AccessProfile axis | Separate transport/access concerns (geo-gating, proxy, SW) from extraction mode |
| ADR-3 | Linebet hybrid mode | Cookie-harvest → direct httpx polling of `/service-api/LiveFeed/` endpoints |
| ADR-4 | DOM-primary extraction | BetB2B direct-API auth-header contract rotates (406); DOM extraction is the reliable primary path |

### The BetB2B Family Scraper

The most important active work. `src/sites/betb2b/` is a **parameterised base scraper** for all BetB2B/1xbet-white-label bookmakers. Each brand is a thin YAML "skin" in `src/sites/betb2b/skins/<name>.yaml` — no Python changes needed to add a new bookmaker.

**Extraction mode:** Hybrid (ADR-3/ADR-4)
1. Browser bootstrap once through an allowed-country proxy → harvest ~21 session cookies
2. `httpx`-poll the `/service-api/{LiveFeed,LineFeed}/...` endpoints directly (best-effort; 406 → DOM fallback)
3. DOM extraction as the drift-proof primary path when the API auth-header contract rotates

**Current skins:** linebet, 22bet, betwinner, melbet, megapari, 888starz, helabet, paripesa

### Per-Sport Scrapers (`src/sites/betb2b/sports/`) — ✅ Initialized 2026-07-18

The BetB2B backend tags every event with an integer `SI` sport id (1=Football,
3=Basketball, 4=Tennis, …). The `sports/` subpackage lets each sport customize
its scraper behavior without touching the base scraper:

* **URL slug.** `/en/line/basketball` vs `/en/line/football` — the browser
  bootstrap navigates here so the SPA loads the right championship tree and
  the service worker injects the correct per-sport cookies.
* **Feed query param.** The `sports=<SI>` filter is automatically added to
  `/service-api/{Line,Live}Feed/Get1x2_VZip` requests.
* **DOM selectors.** The drift-tolerance fallback extractor uses
  `dashboard-champ` / `dashboard-champ__game` / `dashboard-game-block__team`
  by default; sports with unusual layouts can override.
* **Market-group name overrides.** `G=1` is "1x2" on football (3-way) but
  "To Win Match" on basketball (2-way, no draw). `G=17` is "Total Goals"
  on football but "Total Points" on basketball. Each sport ships its own
  overrides that merge on top of `DEFAULT_MARKET_GROUPS`.
* **Event enrichment hooks.** Each sport can map period strings to numbers
  (e.g. "2nd quarter" → `minute=2`, "3rd set" → `minute=3`).

**Shipped sports:** `all` (no filter), `football` (SI=1), `basketball` (SI=3),
`ice-hockey` (SI=2), `tennis` (SI=4), `esports` (SI=20).

**Adding a new sport** = drop a 50-line module in `sports/` and register it in
`sports/registry.py`. No changes to `scraper.py` or `session.py`.

```python
from src.sites.betb2b import BetB2BScraper, BetB2BSkinConfig

skin = BetB2BSkinConfig.from_yaml("src/sites/betb2b/skins/linebet.yaml")
async with BetB2BScraper(skin, sport="basketball") as scraper:
    result = await scraper.scrape(action="list_prematch")
    # → bootstraps against /en/line/basketball, filters feed with sports=3,
    #   tags events with Sport.BASKETBALL, applies "To Win Match" overrides.
```

CLI:

```bash
python -m src.sites.betb2b.cli.main scrape --skin linebet --sport basketball --action list_prematch
python -m src.sites.betb2b.cli.main sports                # list registered sports
python -m src.sites.betb2b.cli.main info --skin linebet --sport basketball
```

Live validation against linebet basketball:

```bash
export BETB2B_PROXY_URL=http://bore.pub:37582
export BETB2B_PROXY_USER=TisoneK
export BETB2B_PROXY_PASS=Taalib01
export BETB2B_PROXY_COUNTRY=KE
export BETB2B_PROXY_ID=kenya
python -m src.sites.betb2b.scripts.validate_live --skin linebet --sport basketball
```

**BetB2B platform infrastructure (researched 2026-07-18, H2H solved 2026-07-19):**
- White-label platform provider (Curaçao), powers 18+ betting brands
- Frontend: Microfrontend shell + betting app loaded via CDN (`v3.traincdn.com`). NOT Nuxt.js SSR (no `window.__NUXT__`)
- Backend: `/service-api/LiveFeed/` and `/service-api/LineFeed/` REST endpoints returning terse-key JSON
- All sister sites share the same odds feed, events, and markets; differences are branding + risk margins
- Anti-bot: Cloudflare WAF, JS challenges, rate limiting, TLS fingerprinting, geo-blocking per skin
- API endpoints: `Get1x2_VZip`, `GetSportsShortZip`, `WebGetTopChampsZip`, `GetTopGamesStatZip`
- Response format: `{"Success": true, "Value": [{I, O1, O2, SN, SI, L, LI, S, SC, E[], AE[]}]}`
- **H2H / statistics:** `/service-api/statisticfeed/api/v1/Game/h2h?id={gameId}&lng=en&ref={partner}&fcountry={country}&gr={gr}` — fires at bootstrap on scheduled match pages. The `id` param is **NOT** the URL event ID; it's found in `GetGameZip` or `GetSubsOptionsForGame` responses. Skins vary `partner`/`gr`/`country` values (see YAML). See `docs/H2H_DISCOVERY.md` for full spec.

### Telemetry System (`src/telemetry/`) — ✅ Wired into betb2b

The framework has a comprehensive telemetry subsystem (`src/telemetry/`) with collectors,
processors, reporting, alerting, and storage (InfluxDB, JSON file, tiered).

**BetB2B integration:** `src/sites/betb2b/telemetry_integration.py` provides a
lightweight, self-contained `BetB2BTelemetry` class that emits structured JSON events
for every phase of the scrape lifecycle (bootstrap, feed poll, extraction, DOM fallback,
scrape-complete, error snapshots). It is wired into `BetB2BScraper.__init__` and called
at each lifecycle point in `scraper.py`. Fully customizable via constructor params:
`output_dir`, `enabled`, `snapshot_on_error`, `max_events_per_file`,
`include_captured_bodies`. Auto-flushes to rotating JSON files.

### Snapshot System (`src/core/snapshot/`) — ✅ Wired into betb2b

Browser state capture for debugging and drift detection:
- Context-aware organization: site/module/component/timestamp hierarchy
- Dual HTML capture: full page + element-specific
- Event-driven triggers: failure, timeout, extraction mismatch
- Normalization + diff for captured network responses
- Handlers: browser, session, scraper, selector, error, retry, monitoring, coordinator

**BetB2B integration (fully wired via `telemetry_integration.py`):**

1. **Success-path page snapshots** — `capture_page_snapshot()` is called during
   DOM fallback renders (live + prematch). The `render_dom_events()` method in
   `session.py` accepts an `_on_page_ready` callback that the scraper uses to
   capture a full-page HTML + screenshot snapshot via the framework's
   `SnapshotManager`, with a direct-HTML fallback if the manager is unavailable.

2. **Success-path result snapshots** — `capture_result_snapshot()` serializes
   every completed scrape result (events, markets, captures) into a timestamped
   JSON file under `data/telemetry/betb2b/result_snapshots/`. This enables
   diff-based drift detection across sessions without needing a browser.

3. **Error-path snapshots** — `capture_error_snapshot()` triggers on failures
   (DOM fallback errors, timeouts). Uses the framework's `SnapshotManager` with
   a JSON fallback when no browser page is available.

All snapshot paths are controlled by `snapshot_on_error` (default True) and
`snapshot_on_success` (default True) flags on `BetB2BTelemetry`.

## Rules (beyond the .context protocol)

1. **Start at `.context/kickoff.md`.** Do not grep the codebase for "context" — the protocol lives in `.context/`.
2. **Never write under `.context/core/`** — it is read-only. All project memory goes under `.context/memory/`.
3. **Pick your instruction set by YOUR agent type:** local IDE → `.context/core/rules/ai-engineering-protocol-local.md`; cloud/sandbox → `.context/core/rules/ai-engineering-protocol.md`.
4. **Read memory before working:** `.context/memory/workflows/active.md`, `.context/memory/agents/sessions.md` (last entries), `.context/memory/tasks/current.md`, `.context/memory/inefficiencies/log.md`.
5. **One task at a time.** Check `.context/memory/tasks/current.md` first.
6. **Append-only files:** `agents/sessions.md`, `tasks/backlog.md`, `plans/decisions.md`, `flaws/log.md`, `inefficiencies/log.md`.
7. **No secrets in tracked files.** Values go only in `.context/memory/secrets/` (self-gitignored).
8. **Two surfaces, two prefixes:** product code = normal commit prefixes; `.context/` = `chore(context):`.
9. **Session is done when committed AND pushed**, session logged, and `tasks/current.md` cleared.
10. **Don't ask permission for the default next step.** Do it and report. Ask only on genuine ambiguity.

### BetB2B-Specific Rules

11. **Never chase the BetB2B auth-header contract in code.** The `x-dt`/`x-project-id` header rotates per session. DOM extraction is the stable path (ADR-4).
12. **Skins are YAML-only.** To add a bookmaker, create `skins/<name>.yaml` — no Python changes.
13. **Proxy is optional.** BetB2B sites geo-block per skin, but if your
    egress is already in an allowed country, the scraper runs fine in
    direct mode (no proxy). Set `BETB2B_PROXY_URL` / related env vars
    only when needed.
14. **The validate_live script is the e2e test.** Run `python -m src.sites.betb2b.scripts.validate_live --skin linebet`. Proxy env vars are optional — omit them if your egress is in an allowed country.

15. **H2H endpoint uses skin config params.** The `/statisticfeed/api/v1/Game/h2h` endpoint takes `ref={partner}`, `fcountry={country}`, `gr={gr}` from the skin YAML. Linebet uses `ref=189&fcountry=87&gr=650`; most other skins default to `ref=1&fcountry=87&gr=1`. See `docs/H2H_DISCOVERY.md`.

16. **H2H discovery requires a scheduled (pre-match) major league event.** Live/in-play matches do NOT pre-fetch H2H data. Use `/en/line/` (pre-match) not `/en/live/`. The endpoint fires at bootstrap, not on hover. See `src/sites/betb2b/scripts/discover_h2h.py`.

17. **The H2H `id` param is NOT the URL event ID.** It must be extracted from `GetGameZip` or `GetSubsOptionsForGame` response bodies. They are different numbers with no obvious relationship.

### Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

### Running Tests

```bash
# Unit tests (fast, no network)
pytest tests/unit/ -m "not integration"

# All tests
pytest tests/ -x

# BetB2B-specific tests
pytest tests/ -k "betb2b" -v

# BetB2B live validation (proxy optional — omit if egress is in allowed country)
# With proxy:
BETB2B_PROXY_URL=http://bore.pub:55068 \
BETB2B_PROXY_USER=TisoneK \
BETB2B_PROXY_PASS=Taalib01 \
BETB2B_PROXY_COUNTRY=KE \
BETB2B_PROXY_ID=kenya \
python -m src.sites.betb2b.scripts.validate_live --skin linebet
# Without proxy (direct mode):
python -m src.sites.betb2b.scripts.validate_live --skin linebet
```

### BetB2B CLI

```bash
# List available skins
python -m src.sites.betb2b.cli.main skins

# Print skin info + feed URLs
python -m src.sites.betb2b.cli.main info --skin linebet

# Scrape live events
python -m src.sites.betb2b.cli.main scrape --skin linebet --action list_live -v

# Probe connectivity (bootstrap only, no feed poll)
python -m src.sites.betb2b.cli.main probe --skin linebet
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/sites/betb2b/config.py` | `BetB2BSkinConfig` dataclass — all per-skin customization |
| `src/sites/betb2b/scraper.py` | `BetB2BScraper` — the main scraper class |
| `src/sites/betb2b/client.py` | `BetB2BFeedClient` — httpx feed poller |
| `src/sites/betb2b/session.py` | `BetB2BSessionManager` — browser cookie-harvest bootstrap |
| `src/sites/betb2b/extraction/rules.py` | `BetB2BExtractionRules` — terse-key JSON → Event/Market/Selection |
| `src/sites/betb2b/extraction/dom.py` | DOM extraction fallback — reads rendered odds from page |
| `src/sites/betb2b/extraction/models.py` | `Event`, `Market`, `Selection`, `CapturedFeedResponse`, `BetB2BScrapeResult` |
| `src/sites/betb2b/markets.py` | Market group/type lookup tables |
| `src/sites/betb2b/sports.py` | Sport ID → name mapping |
| `src/sites/betb2b/skins/` | Per-bookmaker YAML skin configs |
| `src/sites/betb2b/scripts/validate_live.py` | E2E validation script |
| `src/sites/betb2b/scripts/discover_h2h.py` | H2H endpoint discovery script |
| `src/sites/betb2b/cli/main.py` | CLI entry point |
| `docs/H2H_DISCOVERY.md` | H2H endpoint full specification + integration guide |
| `src/network/proxy/` | ProxyManager, ProxyEndpoint, proxy verification |
| `src/network/session.py` | SessionHarvester, SessionPackage, SessionValidator |
| `src/telemetry/` | Full telemetry system (collectors, processors, storage, reporting) |
| `src/core/snapshot/` | Snapshot capture system (browser state, HTML, screenshots) |