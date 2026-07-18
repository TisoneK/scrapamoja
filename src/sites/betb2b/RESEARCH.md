# BetB2B / 1xbet Family — Infrastructure Deep Research

> **Research window:** 2026-07-17 → 2026-07-19
> **Live-confirmed skins:** linebet (KE), with family-wide probe across
> melbet, betwinner, 22bet, megapari, 888starz, helabet, paripesa, 1xbet, 1win.
> **Method:** Playwright bootstrap through a residential Kenyan proxy
> (`gost` HTTP proxy on a Windows host in Kisumu → `bore.pub` TCP tunnel →
> the framework's `ProxyManager`), then `httpx` replay of captured feed
> calls, plus in-page `fetch` probes from inside the bootstrapped SPA.

This document is the canonical reference for how the BetB2B / 1xbet
platform family is built, how it differs from skin to skin, and how the
`scrapamoja` betb2b scraper is shaped around those findings. Companion
implementation: [`src/sites/betb2b/`](.) — see
[`RECON.md` in the linebet folder](../linebet/RECON.md) for the original
per-skin recon notes; this file generalizes them.

---

## 1. The BetB2B platform — one backend, many brands

**BetB2B** is a white-label sportsbook platform provider (Curaçao-licensed)
that powers 18+ betting brands. The operator (the brand owner) gets:

- A branded frontend (logo, color theme, domain, payment methods)
- A unique `partner` / `ref` affiliate id and a unique `gr` project-group id
- Per-skin risk margins, market depth, and bonus/odds-margin policies

The operator does **not** get a separate backend. All skins share:

- The same `/service-api/{LiveFeed,LineFeed}/…` REST endpoints
- The same 1xbet terse-key `Value[]` JSON schema
- The same championship tree, event ids (`I` / `ZP`), team ids (`O1I` / `O2I`)
- The same sport-id (`SI`), league-id (`LI`), market-group (`G`), market-type (`T`) tables
- The same Cloudflare WAF rules and service-worker header-injection pipeline

Empirically verified 2026-07-18 by probing
`/service-api/LineFeed/Get1x2_VZip` across 8 family domains through the
Kenya proxy — all returned the *identical*
`{"type":"feed/NotAcceptableException",...}` 406 envelope from the same
shared feed microservice. The 406 means the endpoint exists and behaves
the same; the bare probe just lacked the per-skin cookies/headers.

### The confirmed family (8 skins, shared backend)

| Skin | Domain | `partner` | `gr` | `country` (KE) | Geo | Notes |
|------|--------|----------|------|----------------|-----|-------|
| linebet | `linebet.com` | 189 | 650 | 87 | KE | Reverse-engineered against this. Kenya-confirmed. |
| melbet | `melbet.com` | 82 | 650 | 87 | KE | Same backend, different branding. |
| betwinner | `betwinner.com` | 119 | 650 | 87 | KE | |
| 22bet | `22bet.com` | 1 | 650 | 87 | KE | |
| megapari | `megapari.com` | 35608 | 650 | 87 | KE | |
| 888starz | `888starz.bet` | 1653463 | 650 | 87 | KE | |
| helabet | `helabet.com` | 6 | 650 | 87 | KE | |
| paripesa | `paripesa.bet` | 356 | 650 | 87 | KE | |

### The non-family lookalikes (negative tests)

| Site | Why it's NOT BetB2B |
|------|---------------------|
| `1xbet.com` | **Same family** but fronted by Cloudflare (`403 "Just a moment…"`) — the flagship. Needs anti-Cloudflare handling the skins don't. |
| `1win.pro` | Different platform entirely. Returns `200` HTML in `ru-RU`; no `service-api` feed. Handle separately. |

### Implication for the scraper

One parameterized scraper covers the family. Per-skin config is small —
`domain`, `partner`/`ref`, `gr`, `country`, `geo` — and lives in a YAML
file at [`skins/<name>.yaml`](skins/). No Python changes needed to add a
bookmaker.

---

## 2. Frontend architecture — Nuxt SSR + Vue grid + 3 service workers

The frontend is a **Nuxt.js (Vue.js SSR)** application. Identifying signals:

- `window.__NUXT__` payload on the homepage
- `/_nuxt/` chunked asset paths
- `data-v-*` scoped style attributes on every element
- `data-mbc-__betting_app__="DashboardGameDesktop"` Vue component markers

The betting SPA itself is a micro-frontend loaded from
`linebet.com/sys-static/sys-betting-app-static/…` (dozens of chunked CSS/JS
bundles). `window.serverData` carries the micro-frontend config
(`__V3_HOST_APP__`, feature-flag variants).

### The Vue grid markup (the DOM extractor target)

The odds grid is rendered as a championship-grouped list. The class
hierarchy (verified against live linebet HTML, 2026-07-19):

```
<div class="betting-main-dashboard">
  <div class="dashboard">
    <div class="dashboard__champs">
      <div class="dashboard-champ">                       <!-- one per competition -->
        <div class="dashboard-champ__name">
          <span class="dashboard-champ-name__label">NBA</span>   <!-- competition name -->
        </div>
        <div class="dashboard-champ-body">
          <div class="dashboard-champ-body__games">
            <li class="dashboard-champ__game dashboard-game">     <!-- one per fixture -->
              <div class="dashboard-game-block">
                <span class="dashboard-game-block__row">
                  <div class="dashboard-game-block__teams">
                    <span class="dashboard-game-block__team">Lakers</span>
                    <span class="dashboard-game-block__team">Celtics</span>
                  </div>
                  <div class="c-bets">                              <!-- odds cells -->
                    <button class="c-bets__bet">1.85</button>
                    <button class="c-bets__bet">1.95</button>
                  </div>
                </span>
              </div>
            </li>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

The `dashboard-champ` container is the **competition scope** — every game
inside it inherits the championship name from the parent header. The
`dashboard-game-block__team` cells (exactly 2 per row) are the team names.
The `c-bets__bet` buttons are the odds cells (typically 3 for 1x2 sports,
2 for h2h sports).

> **Selector drift caveat.** These class names are stable across the
> family but **do** churn over time as the SPA ships new chunks. The DOM
> extractor in [`extraction/dom.py`](extraction/dom.py) uses
> `class*=` (contains) matches wherever possible and the per-sport
> [`DOMSelectors`](sports/base.py) bundle lets us ship overrides per
> sport without touching the shared extractor.

### The three service workers

The site installs three service workers that together defeat naive scraping:

| SW | Role | Impact on scraping |
|----|------|---------------------|
| `ivpn-sw.js` | **Header injection.** Keeps a set of headers in IndexedDB (`vpn` DB → `headers` store), loads them into memory, and on every request clones it and sets all stored headers. Derives `x-dt` from `x-project-id` and forces `mode:"same-origin"`. | API requests carry SW-injected headers a plain HTTP replay won't have. **This is what causes the 406.** |
| `domain-sw.js` | **Mirror-domain failover.** Fetches `/checker/redirect/stat/run/` → a list of backup `domains`, probes each via `https://<domain>/static/pixel.gif?<ts>`, and reports LOADED/ERROR back to `/checker/redirect/stat/`. This is how the site survives domain takedowns. | None for scraping — but useful intel for finding alternate domains. |
| `check-rum.worker.js` | RUM / performance monitoring (not data). | None. |
| `pwa-module-sw.js` | PWA cache (`networkFirst` + TTL cache cleanup). | None. |

#### The `ivpn-sw` auth-header rotation (the 406 story)

**2026-07-18:** The `Get1x2_VZip` feed replayed cleanly from `httpx` with
just the base betting headers + harvested cookies. The `ivpn-sw` header
injection was real but did **not** gate the odds feed — `x-hd` was sent
on some requests but not required.

**2026-07-19:** The platform rotated the contract. The same httpx replay
now returns **`406 feed/NotAcceptableException`**. An in-page `fetch`
from inside the bootstrapped SPA also returns 406 — the feed request has
moved into a worker context where `ivpn-sw` injects a required `x-dt`
header (derived from `x-project-id`) from a store the app fills via
`postMessage`. The IndexedDB `vpn/headers` store is gone; the SW only
activates when registered with an `?i=` param.

**Consequence (ADR-4):** DOM extraction is the drift-proof primary path.
The direct-API is best-effort: capture genuine headers per-session via
CDP `Target.setAutoAttach` to the service-worker target + `Network`,
replay those, and treat 406 as a DOM-fallback trigger.

---

## 3. Backend API surface — `service-api`, `bff-api`, `champs-api`

Hosts (linebet example, family-shared):

| Host | Role |
|------|------|
| `linebet.com` | App + all APIs |
| `v3.traincdn.com` | Static CDN: dictionaries, CMS media, chunked SPA bundles |
| `widget.suphelper.top` | Support widget |
| `mc.yandex.ru` | Yandex Metrica analytics |

### Common query-param grammar

```
lang=en & d=<domain> & g=<GEO> & p=<gr>
```

- `p` / `projectId` = `gr` (linebet = 650) — the project-group id
- `g` = detected country (ISO code) — flows through the config API
- `d` = bare domain (for the bff-api)

### The feed endpoints (the data we want)

**Two feed roots — this is the key split:**

| Root | Path | Means |
|------|------|-------|
| LiveFeed | `/service-api/LiveFeed/…` | In-play events (the `/en/live` pages) |
| LineFeed | `/service-api/LineFeed/…` | Prematch / scheduled events (the `/en/line/<sport>` pages) |

Same endpoint names + schema under each root:

| Endpoint (swap `LiveFeed`↔`LineFeed` for in-play↔prematch) | Purpose |
|----------|---------|
| `GET /Get1x2_VZip?count=10&lng=en&mode=4&country=87&top=true&partner=189&virtualSports=true` | **Events + odds** (`top=true` = top games across sports; add `sports=<SI>` for per-sport) |
| `GET /WebGetTopChampsZip?lng=en&country=87&gr=650` | Top championships |
| `GET /GetSportsShortZip?lng=en&gr=650&country=87&partner=189&groupChamps=true` | Sports / championship tree |
| `GET /GetTopGamesStatZip?lng=en&antisports=66&partner=189` | Top games stats |
| `GET /service-api/main-{live,line}-feed/v1/expressDay?cfView=3&country=87&gr=650&lng=en&ref=189` | Express-of-the-day |
| `GET /champs-api/v1/get-champs-by-params-web` | Championship list (sends the richer `x-*` header set) |

Stable query params: `gr=<project-group>`, `country=<internal-id>`, `partner=<affiliate>`,
`lng=<lang>`. The `_VZip` / `Zip` suffix means the response is
gzip-compressed at the HTTP layer (httpx / browser decompress
automatically → JSON).

### The bootstrap / config API surface

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/bff-api/config/group/get?groups=…&g=KE&p=650` | SPA feature / config groups (`b.core`, `d.*`) |
| GET | `/bff-api/config/licenses.json?…` | Licence / footer config |
| GET | `/bff-api/event-logo/v2/suitable.json?…` | Country / league logos |
| GET | `/web-api/session` (204) | Anonymous session bootstrap |
| GET | `/web-api/api/v3/bonuses/welcome-bonuses` | Welcome offers (currency = KES for KE) |
| GET | `/web-api/api/third-party/banner-for-header` | Header promo |
| GET | `/service-api/gamespreview/getbanner?whence=55&ref=189&gr=650&lng=en&fCountry=87` | Casino preview |
| GET | `/service-api/gamespreview/GetGamesPreviewLight` / `GetGamesPreviewByGameIds` / `GetGamesActions` | Casino games (found in `entry-*.js`) |
| GET | `/analytics-module-api/v1/analytics?projectId=650&domain=linebet.com` | Analytics counter config (Yandex `22934032` + GA `G-P0W7C55K23`) |
| GET | `/checker/redirect/stat/run/` | **Mirror-domain list** (failover) |
| POST | `/checker/redirect/stat/` | Mirror-domain reachability report |
| GET/POST | `/fatman-api/<40-hex>/…` (`event.json`, `ab.json`, `metadata.json`, `fc`) | First-party telemetry/AB. The `<40-hex>` is a rotating id. Responses are tiny `{"ts":…}` — analytics, **not** data. |
| GET | `/sys-welcome-app-front/en`, `/sys-office-app-front/en` | Nuxt micro-frontend shells |
| GET | `/sys-static/sys-betting-app-static/…` | Betting SPA bundles (dozens of chunked CSS/JS) |

---

## 4. The 1xbet terse-key `Value[]` schema

The feed endpoints all return the same envelope:

```json
{
  "Success": true,
  "Error": "",
  "Value": [ <event>, <event>, … ]
}
```

Per event (single-letter keys — terse for wire size):

| Key | Meaning | Key | Meaning |
|-----|---------|-----|---------|
| `I` / `ZP` | event id | `O1` / `O2` | team names (`O1E` / `O2E` = English) |
| `SN` / `SI` | sport name / id | `O1I` / `O2I` | team ids |
| `L` / `LI` | league name / id | `S` | start time (Unix epoch seconds) |
| `CN` | country | `SC` | score block (see below) |
| `E[]` | markets (flat): `T`=type, `G`=group, `C`=coefficient, `CV`=odds str, `P`=param (handicap/total line), `B`=blocked | `AE[]` | grouped markets: `{G, ME:[…same as E]}` (preferred when present) |

### The `SC` (score) block

```json
"SC": {
  "FS": {"S1": 2, "S2": 1},        // full score: home, away
  "PS": [...],                       // period scores
  "CP": 2,                           // current period (1=1st half, 2=2nd half, …)
  "CPS": "2nd half",                 // current period name (text)
  "TS": 1342,                        // clock seconds (within period)
  "SLS": "12:34"                     // time-left text
}
```

The extractor uses `FS.S1` / `FS.S2` for `score_home` / `score_away`,
`CPS` for `period`, `TS // 60` for a coarse `minute` (within-period),
and `SLS` for `time_remaining`. See
[`extraction/rules.py`](extraction/rules.py) `_coerce_status()`.

### The `G` (market group) and `T` (market type) id tables

The `G` ids are **family-shared** but the display names differ per sport.
`G=1` is "1x2" on football (3-way: home/draw/away) but "To Win Match" on
basketball (2-way: home/away, no draw — overtime resolves ties). The
per-sport overrides live in [`sports/<sport>.py`](sports/).

| `G` | Football name | Basketball name | Tennis name | MarketType enum |
|-----|---------------|-----------------|-------------|-----------------|
| 1 | 1x2 | To Win Match | To Win Match | `MONEYLINE_12` (3-way) / `MONEYLINE_H2H` (2-way) |
| 2 | Handicap | Handicap | Game Handicap | `HANDICAP` |
| 3 | Total Goals | Total Points | Total Games | `TOTALS` |
| 4 | Team Total Goals | Team Total Points | — | `TOTALS` |
| 5 | Correct Score | Exact Score | Exact Score | `CORRECT_SCORE` |
| 6 | Double Chance | — | — | `DOUBLE_CHANCE` |
| 9 | Both Teams To Score | — | — | `BTTS` |
| 17 | Total Goals | Total Points | Total Games | `TOTALS` |

The full table is in [`markets.py`](markets.py). Per-sport overrides in
each `sports/<sport>.py` `market_group_overrides` list.

### The `SI` (sport id) table

Family-shared. Full table in [`sport_ids.py`](sport_ids.py). Headline values:

| `SI` | Sport | Slug | Has draw? | Period |
|------|-------|------|-----------|--------|
| 1 | Football | `football` | Yes (1X2) | 2 halves |
| 2 | Ice Hockey | `ice-hockey` | Yes (regulation 1X2) | 3 periods |
| 3 | Basketball | `basketball` | No (OT resolves) | 4 quarters |
| 4 | Tennis | `tennis` | No | best-of-N sets |
| 5 | Volleyball | (not shipped) | No | best-of-N sets |
| 6 | Handball | (not shipped) | Yes | 2 halves |
| 7 | Baseball | (not shipped) | No (innings) | 9 innings |
| 8 | Cricket | (not shipped) | Yes (draw possible) | innings |
| 11 | Boxing | (not shipped) | No | rounds |
| 12 | MMA | (not shipped) | No | rounds |
| 13 | Table Tennis | (not shipped) | No | best-of-N sets |
| 20 | Esports | `esports` | No | best-of-N maps |
| 32 | Horse Racing | (not shipped) | No | — |
| 75 | Politics | (not shipped) | — | — |
| 82 | Financials | (not shipped) | — | — |

The 6 shipped sports (all, football, basketball, ice-hockey, tennis,
esports) cover the bulk of the family's traffic. Adding a new sport =
drop a 50-line module in [`sports/`](sports/) and register it in
[`sports/registry.py`](sports/registry.py).

---

## 5. Anti-bot architecture

### Layer 1: Geo-gating at the nginx edge

From a US / datacenter IP you get `HTTP 203 → /en/block` before any app
code runs. From an allowed-country IP (Kenya confirmed) the full SPA
loads (`200`). The detected country flows through the config API as the
`g=` query param (`g=KE`; `g=US` on the block page).

**Mitigation:** route through an allowed-country proxy. The skin's
`allowed_countries` list drives the
[`BetB2BSessionManager._verify_proxy_country()`](session.py) check that
runs before any browser launch — saves an expensive Playwright launch if
the proxy is misconfigured.

### Layer 2: Cloudflare WAF (1xbet.com only)

The flagship `1xbet.com` domain is fronted by Cloudflare. Bare probes
return `403 "Just a moment…"` with a JS challenge. The 8 skin domains
are **not** fronted by Cloudflare and don't need anti-Cloudflare
handling.

### Layer 3: The `ivpn-sw` header injection

See §2. The feed request now (2026-07-19) requires an SW-injected `x-dt`
header derived from `x-project-id` via `postMessage`. Missing it ⇒ 406.

**Mitigation:** DOM extraction (ADR-4). The SPA renders the odds
correctly; we read them from the rendered DOM. The direct-API path is
best-effort and falls back to DOM on 406.

### Layer 4: Required base betting headers

The `service-api` rejects / ignores requests missing the betting-app
header set:

```
accept: application/json, text/plain, */*
content-type: application/json
is-srv: false
x-app-n: __BETTING_APP__
x-svc-source: __BETTING_APP__
x-requested-with: XMLHttpRequest
x-mobile-project-id: 0
```

Plus session cookies (harvested from a browser bootstrap — 21-22 cookies).

These are family-shared and live in
[`DEFAULT_BASE_BETTING_HEADERS`](config.py).

### Layer 5: TLS fingerprinting (suspected, unconfirmed)

The 406 error message is generic. The platform may also be checking TLS
JA3 fingerprints. The httpx client uses Python's default TLS stack which
differs from Chromium's. If confirmed, the fix is to use a TLS-impersonating
client (`curl_cffi` or `tls-client`).

---

## 6. The hybrid extraction mode (ADR-3 + ADR-4)

### The recipe

1. **Browser bootstrap** (one Playwright Chromium launch through the
   allowed-country proxy):
   - Navigate to `https://<domain>/en`, dismiss the consent banner,
     wait for the SPA's API burst to settle (12-18s).
   - Visit `https://<domain>/en/live` too — some cookies are only set on
     the live route.
   - Harvest ~21 session cookies via the framework's `SessionHarvester`
     (`src/network/session.py`).
2. **Direct-API poll** (best-effort, httpx): poll the
   `/service-api/{LiveFeed,LineFeed}/…` endpoints directly through the
   proxy with the base betting headers + harvested cookies. No browser
   per poll.
3. **DOM fallback** (drift-proof primary): on 406 (or any non-2xx /
   undecodable response), render the corresponding live/line page in
   Playwright and read the odds the SPA already rendered.

### Why the hybrid mode works

- The browser bootstrap solves geo-gating + cookie harvesting in one shot.
- The direct-API poll is fast (sub-second) when the auth-header contract
  is stable. The 21 harvested cookies are good for hours.
- The DOM fallback is the safety net. The SPA renders odds the same way
  a human sees them — no auth-header contract can break it.

### What each part costs

| Step | Cost | Frequency |
|------|------|-----------|
| Browser bootstrap | ~30-45s (one Playwright launch + 12-18s settle + cookie harvest) | Once per session TTL (default 2h) |
| Direct-API poll | ~200-500ms per endpoint | Every poll |
| DOM fallback | ~25-40s (one Playwright launch + settle + extract) | Only when the API 406s |

---

## 7. The per-sport scraper framework (ADR-5)

The betb2b scraper is parameterised by **skin** (which bookmaker) and by
**sport** (which sport). See [`sports/`](sports/) for the implementation.
Each sport customizes:

1. **URL slug** — `/en/line/basketball` vs `/en/line/football`. The
   browser bootstrap navigates here so the SPA loads the right
   championship tree.
2. **Feed query param** — `sports=<SI>` is added to feed requests
   automatically.
3. **DOM selectors** — the drift-tolerance extractor uses the
   `dashboard-champ` hierarchy by default; sports can override.
4. **Market-group name overrides** — `G=1` is "1x2" on football but
   "To Win Match" on basketball.
5. **Event enrichment hooks** — each sport maps period strings to
   numbers ("2nd quarter" → `minute=2`, "3rd set" → `minute=3`).

### Shipped sports

| Slug | SI | Has draw | Period | Market-group overrides |
|------|----|---------|--------|-----------------------|
| `all` | 0 (no filter) | — | — | none |
| `football` | 1 | Yes | half (2) | 1x2, Handicap, Total Goals, Double Chance, BTTS |
| `ice-hockey` | 2 | Yes (regulation) | period (3) | 1x2 (Regulation), Puck Line, Total Goals |
| `basketball` | 3 | No | quarter (4) | To Win Match, Handicap, Total Points, Team Total Points, Exact Score |
| `tennis` | 4 | No | set (best-of-N) | To Win Match, Game Handicap, Total Games, Exact Score |
| `esports` | 20 | No | map (best-of-N) | To Win Match, Map Handicap, Total Maps, Exact Score |

### Adding a new sport

```python
# src/sites/betb2b/sports/volleyball.py
from ..extraction.models import MarketType, Sport
from .base import MarketGroupOverride, SportScraper

class VolleyballScraper(SportScraper):
    sport_id = 5
    slug = "volleyball"
    live_slug = "volleyball"
    sport_enum = Sport.VOLLEYBALL
    display_name = "Volleyball"
    has_draw = False
    period_name = "set"
    market_group_overrides = [
        MarketGroupOverride(g_id=1, name="To Win Match",
                            market_type=MarketType.MONEYLINE_H2H),
        MarketGroupOverride(g_id=3, name="Total Points",
                            market_type=MarketType.TOTALS),
    ]
```

Then register it in `sports/registry.py`:

```python
from .volleyball import VolleyballScraper
register_sport_scraper(VolleyballScraper)
```

No changes to `scraper.py` or `session.py`.

---

## 8. The mirror-domain failover (`domain-sw.js`)

The site survives domain takedowns via a mirror-domain list fetched from
`/checker/redirect/stat/run/`. The SW probes each mirror via
`https://<domain>/static/pixel.gif?<ts>` and reports LOADED/ERROR back to
`/checker/redirect/stat/`.

Known linebet mirrors (probe 2026-07-18):

- `linebet.com` (primary)
- `linebet.co` (alternate TLD)
- `1xlbsb.com` (mirror — short code)
- `lb1xbet.com` (mirror — 1xbet-style)
- … plus a rotating set of 6-12 short-code mirrors

The mirror list rotates. To discover the current set, hit
`/checker/redirect/stat/run/` from inside the bootstrapped SPA. This is
useful when a skin's primary domain is seized; the scraper can failover
to a mirror by changing the skin's `domain` field.

---

## 9. Reproducing this research

### The proxy

Any allowed-country HTTP proxy works. The operator's setup:

- `gost` HTTP proxy on a Windows host in Kisumu, KE
- Exposed via `bore.pub` TCP tunnel on port 37582
- Auth: `TisoneK:Taalib01`

```bash
export BETB2B_PROXY_URL=http://bore.pub:37582
export BETB2B_PROXY_USER=TisoneK
export BETB2B_PROXY_PASS=Taalib01
export BETB2B_PROXY_COUNTRY=KE
export BETB2B_PROXY_ID=kenya
```

### The family probe

```bash
python -m src.sites.betb2b.scripts.probe_family
```

Probes `/service-api/LineFeed/Get1x2_VZip` across all 10 candidate
domains (8 family + 1xbet + 1win) and reports the shared-feed 406
signal. Use this to verify a new skin belongs to the family.

### The per-skin live validation

```bash
python -m src.sites.betb2b.scripts.validate_live --skin linebet --sport basketball
```

Runs the full hybrid pipeline: proxy verify → browser bootstrap → cookie
harvest → httpx feed poll → DOM fallback → event extraction → persist.
Writes a `summary.json` + per-action captures to
`/home/z/my-project/download/betb2b_validate_<skin>_<sport>/`.

### The CLI

```bash
python -m src.sites.betb2b.cli.main skins                    # list skins
python -m src.sites.betb2b.cli.main sports                   # list sports
python -m src.sites.betb2b.cli.main info --skin linebet --sport basketball
python -m src.sites.betb2b.cli.main scrape --skin linebet --sport basketball --action list_prematch
python -m src.sites.betb2b.cli.main probe --skin linebet --sport basketball
```

---

## 10. Open questions / next research

- **TLS fingerprinting.** Confirm whether the 406 is purely header-driven
  or also TLS-JA3-driven. If TLS, switch to `curl_cffi` for the direct-API
  path.
- **CDP `Target.setAutoAttach` to the SW target.** Capture the genuine
  per-session `x-dt` header from inside the service worker. This would
  restore the direct-API path until the next contract rotation.
- **Mirror-domain auto-failover.** Wire the `/checker/redirect/stat/run/`
  endpoint into the skin config so the scraper can failover to a mirror
  automatically when the primary domain is seized.
- **Per-sport DOM selector drift.** The current `DOMSelectors` defaults
  work for the 6 shipped sports on linebet. Verify they hold on the other
  7 skins and on the live (vs prematch) pages.
- **Market-group `T` id table.** The `T` (market-type) id table in
  `markets.py` is partially known from the 1xbet family. A live capture
  of a full `AE[]` payload would let us complete it.
- **Cookie TTL.** The default session TTL is 2h. Confirm how quickly
  cookies actually expire on each skin — the platform may rotate them
  faster.

---

## Appendix: ADRs

| ADR | Topic | Summary |
|-----|-------|---------|
| ADR-1 | Railway deployment | Deploy FastAPI control plane via Dockerfile; no scrape jobs in the API service |
| ADR-2 | AccessProfile axis | Separate transport/access concerns (geo-gating, proxy, SW) from extraction mode |
| ADR-3 | Linebet hybrid mode | Cookie-harvest → direct httpx polling of `/service-api/LiveFeed/` endpoints |
| ADR-4 | DOM-primary extraction | BetB2B direct-API auth-header contract rotates (406); DOM extraction is the reliable primary path |
| ADR-5 | Per-sport scraper framework | One `SportScraper` ABC + sport-specific subclasses; per-sport URL slug, feed param, DOM selectors, market-group overrides, enrichment hooks. Adding a sport = drop a 50-line module, no scraper changes. |
