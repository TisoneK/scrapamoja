# Linebet — how it works (live recon, 2026-07-17)

First successful **live** capture of linebet.com, via a residential Kenyan proxy
(`gost` HTTP proxy on a Windows box in Kisumu → `bore` TCP tunnel → this machine's
`ProxyManager`). All prior sessions were WAF/geo-blocked from datacenter IPs. This
documents what the live site actually does. Companion data:
[`snapshots/normalized/linebet_api_catalog.json`](snapshots/normalized/linebet_api_catalog.json).

> **UPDATE 2026-07-18 — the odds feed is SOLVED and directly scrapable.** An
> earlier draft of this file concluded the live odds were "service-worker-mediated
> / DOM-only." That was **wrong**: the odds are a normal `service-api/LiveFeed/*`
> XHR that **replays directly from httpx (no browser)**. The correction and the
> proof are in "SOLVED: the live odds feed" below; the service-worker machinery is
> real but does **not** gate the odds feed. Extraction mode for linebet is
> **`hybrid`** (browser bootstrap once for cookies → direct HTTP polling), not a
> new mode — see ADR-3 in `.context/memory/plans/decisions.md`.

## TL;DR for a future scraper

- **Access is geo-gated at the nginx edge.** From a US/datacenter IP you get
  `HTTP 203 → /en/block` before any app code runs. From an allowed-country IP
  (Kenya confirmed) the full SPA loads (`200`). The detected country flows through
  the config API as the `g=` query param (`g=KE`; `g=US` on the block page).
- **Odds come from `/service-api/{LiveFeed,LineFeed}/Get1x2_VZip`** (+ siblings):
  `LiveFeed` = in-play (`/en/live`), `LineFeed` = prematch/scheduled
  (`/en/line/<sport>`). Plain HTTP GET → JSON (1xbet terse-key schema).
  **Proven:** both roots replay from `httpx` with no browser, `Success=true`.
- **What it takes to replay:** (1) an allowed-country proxy, (2) the base betting
  headers (`is-srv:false`, `x-app-n:__BETTING_APP__`, `x-requested-with:XMLHttpRequest`,
  `x-svc-source:__BETTING_APP__`), (3) session cookies (harvest once from a browser
  bootstrap). The `x-hd` token is sent on *some* requests but is **not required**
  for the odds feed (replay without it returned identical data).
- **Extraction mode = `hybrid`** (browser-harvest cookies → direct `httpx` polling).
  The DOM also renders odds as a fallback. This is the classifier's validation case.

## Generalizes to the whole 1xbet / BetB2B family (verified 2026-07-18)

linebet is one skin of the **BetB2B** platform. The findings here are **family-wide**,
confirmed empirically by probing `/service-api/LineFeed/Get1x2_VZip` across domains
through the Kenya proxy:

- **Same backend / same endpoint / same schema** (all returned the *identical*
  `{"type":"feed/NotAcceptableException",...}` 406 envelope from the shared feed
  microservice, i.e. the endpoint exists and behaves the same — 406 just means the
  bare probe lacked the per-skin cookies/headers): **melbet, betwinner, 22bet,
  megapari, 888starz, helabet, paripesa, linebet**.
- **1xbet.com** (flagship): same family but **fronted by Cloudflare** (`403 "Just a
  moment…"`) — needs anti-Cloudflare handling the skins don't.
- **1win.pro**: **NOT** this platform (`200` HTML, `ru-RU`; no `service-api` feed) —
  handle separately.

**Implication:** one parameterized BetB2B scraper covers the family. Per-skin config
is small — `domain`, `partner`/`ref` (linebet `189`), `gr` project id (linebet `650`),
geo `country`, and a per-skin cookie harvest. Everything else (the `LiveFeed`/
`LineFeed` roots, endpoint names, the `is-srv`/`x-app-n`/`x-svc-source`/
`x-requested-with` headers, the terse-key `Value[]` schema, hybrid cookie-harvest →
httpx polling) is shared. This fits the project's one-framework goal: a `betb2b`
base scraper + thin per-skin `SiteConfig`s.

## Anti-blocking architecture (three service workers)

The site installs three service workers that together defeat naive scraping and
domain blocking:

| SW | Role |
|----|------|
| `ivpn-sw.js` | **Header injection.** Keeps a set of headers in IndexedDB (`vpn` DB → `headers` store), loads them into memory, and on every request clones it and sets all stored headers. Notably it derives `x-dt` from `x-project-id` (`c.set("x-dt", u["x-project-id"])`) and forces `mode:"same-origin"`. So API requests carry SW-injected headers a plain HTTP replay won't have. |
| `domain-sw.js` | **Mirror-domain failover.** Fetches `/checker/redirect/stat/run/` → a list of backup `domains`, probes each via `https://<domain>/static/pixel.gif?<ts>`, and reports LOADED/ERROR back to `/checker/redirect/stat/`. This is how the site survives domain takedowns. |
| `check-rum.worker.js` | RUM / performance monitoring (not data). |
| `pwa-module-sw.js` | PWA cache (`networkFirst` + TTL cache cleanup). |

Implication (revised 2026-07-18): this `ivpn-sw` header machinery is real and
gates *some* endpoints (e.g. `champs-api` sends `x-project-id`/`x-referral`/
`x-whence`, and the first `Get1x2` load carried an `x-hd` token), **but it does
NOT gate the live-odds feed** — `Get1x2_VZip` replays fine without `x-hd`/IndexedDB
headers (see "SOLVED" below). Treat the SW header injection as an anti-block /
telemetry layer, not a hard requirement for the odds data. In practice the
IndexedDB `vpn/headers` store was often empty at capture time anyway.

## Bootstrap / config API surface (observed live, `g=KE`)

Hosts: `linebet.com` (app + APIs), `v3.traincdn.com` (static CDN + dictionaries +
CMS media), `widget.suphelper.top` (support widget), `mc.yandex.ru` (analytics).

Common param grammar on `bff-api`: `lang=en & d=linebet.com & g=<GEO> & p=650`
(`p`/`projectId` = 650 = the linebet project id; `g` = detected country).

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `linebet.com/bff-api/config/group/get?groups=…&g=KE&p=650` | SPA feature/config groups (`b.core`, `d.*`) |
| GET | `linebet.com/bff-api/config/licenses.json?…` | licence/footer config |
| GET | `linebet.com/bff-api/event-logo/v2/suitable.json?…` | country/league logos |
| GET | `linebet.com/web-api/session` (204) | anonymous session bootstrap |
| GET | `linebet.com/web-api/api/v3/bonuses/welcome-bonuses` | offers (currency KES) |
| GET | `linebet.com/web-api/api/third-party/banner-for-header` | header promo |
| GET | `linebet.com/service-api/gamespreview/getbanner?whence=55&ref=189&gr=650&lng=en&fCountry=87` | casino preview |
| GET | `linebet.com/service-api/gamespreview/GetGamesPreviewLight` / `GetGamesPreviewByGameIds` / `GetGamesActions` | casino games (found in `entry-*.js`) |
| GET | `linebet.com/analytics-module-api/v1/analytics?projectId=650&domain=linebet.com` | analytics counter config (Yandex `22934032` + GA `G-P0W7C55K23`) |
| GET | `linebet.com/checker/redirect/stat/run/` | **mirror-domain list** (failover) |
| POST | `linebet.com/checker/redirect/stat/` | mirror-domain reachability report |
| GET/POST | `linebet.com/fatman-api/<40-hex>/…` (`event.json`, `ab.json`, `metadata.json`, `fc`) | first-party telemetry/AB. The `<40-hex>` path segment is a rotating id. Responses are tiny `{"ts":…}` — analytics, **not** data. |
| GET | `linebet.com/sys-welcome-app-front/en`, `sys-office-app-front/en` | nuxt micro-frontend shells |

The betting SPA bundles load from `linebet.com/sys-static/sys-betting-app-static/…`
(dozens of chunked CSS/JS). `window.serverData` carries the micro-frontend config
(`__V3_HOST_APP__`, feature-flag variants).

## How this was captured (reproducible)

```python
from src.network.proxy import build_proxy_manager
from src.network.har.export import HarExporter, HarExporterConfig
from pathlib import Path

kenya = build_proxy_manager({"endpoints": [
    {"id": "kenya", "url": "http://USER:PASS@<tunnel-host>:<port>",
     "country": "KE", "source": "ngrok"}]}).get("kenya")

await HarExporter(HarExporterConfig(
    url="https://linebet.com/en", live_url="https://linebet.com/en/live",
    proxy=kenya, output=Path("linebet_kenya.har"))).run()
```

The proxy endpoint is any allowed-country HTTP proxy (a `gost` proxy exposed via a
TCP tunnel works). The raw HAR is **not committed** — it contains session cookies;
only this writeup + the redacted endpoint catalog are.

> **⚠️ MOVING TARGET — re-verified 2026-07-19 (Session 13).** The direct-API
> replay below is **NOT a stable static-header recipe**. As of 2026-07-19 the exact
> base-header httpx replay that worked on 2026-07-18 returns **`406`
> `feed/NotAcceptableException`** — *and so does a bare in-browser `fetch`*. Two
> changes on the platform side:
> 1. The feed request **moved into a worker context** — invisible to page
>    `fetch`/XHR wrappers AND page-target CDP `Network` (both see 0 feed requests).
>    Do NOT rely on `page.on("request"/"response")`, an init-script `fetch` hook, or
>    a page-target CDP session to capture it — they will show nothing.
> 2. `ivpn-sw.js` now injects a required header (`x-dt`, derived from
>    `x-project-id`) from a store the app fills via `postMessage`; it only activates
>    when the SW is registered with an `?i=` param, and the old IndexedDB
>    `vpn/headers` store is gone. Missing that injected header ⇒ `406`.
>
> **Consequence for the scraper (see ADR-4):** treat **DOM extraction as the
> primary path** (drift-proof — odds render fine) and **direct-API as best-effort**:
> capture the genuine headers per-session via CDP `Target.setAutoAttach` to the
> service-worker/worker target + `Network`, replay those, and treat `406` as a
> re-harvest/DOM-fallback trigger — never a hard failure. The endpoints, params, and
> schema documented below are still correct; only the *auth-header contract* rotates.

## SOLVED: the live odds feed (2026-07-18) — endpoints/schema still valid; see the moving-target warning above

The operator's prior attempt named the data endpoint (`LineFeed`); this session
captured it live and **proved a browserless replay works**. How it was found: an
in-page `window.fetch` wrapper (init script) logs every URL — this catches the
feed calls that Playwright's `page.on("response")` / context events and the HAR
all missed (a Playwright surfacing quirk, **not** a service-worker transport as
the earlier draft guessed).

### The endpoints (host `linebet.com`, all `service-api`)

**Two feed roots — this is the key split:**
- **`LiveFeed/…`** = **in-play** (the site's `/en/live` pages). Confirmed replayable.
- **`LineFeed/…`** = **pre-match / scheduled** (the site's `/en/line/<sport>` pages,
  e.g. `https://linebet.com/en/line/basketball`). Confirmed replayable.

They are the same endpoint names + schema under different roots:

| Endpoint (swap `LiveFeed`↔`LineFeed` for in-play↔prematch) | Purpose |
|----------|---------|
| `GET /service-api/{LiveFeed,LineFeed}/Get1x2_VZip?count=10&lng=en&mode=4&country=87&top=true&partner=189&virtualSports=true` | **events + odds** (`top=true` = top games across sports; add a sport/champ filter for a full per-sport list — see note). Live adds `gr=650`, `mode=4`, `noFilterBlockEvent=true`. |
| `GET /service-api/{LiveFeed,LineFeed}/WebGetTopChampsZip?lng=en&country=87&gr=650` | top championships |
| `GET /service-api/{LiveFeed,LineFeed}/GetSportsShortZip?lng=en&gr=650&country=87&partner=189&groupChamps=true` | sports/champ tree |
| `GET /service-api/{LiveFeed,LineFeed}/GetTopGamesStatZip?lng=en&antisports=66&partner=189` | top games stats |
| `GET /service-api/main-{live,line}-feed/v1/expressDay?cfView=3&country=87&gr=650&lng=en&ref=189` | express-of-the-day |
| `GET /champs-api/v1/get-champs-by-params-web` | championship list (sends the richer `x-*` header set) |

Stable query params: `gr=650` (project/group id), `country=87`, `partner=189`
(`ref=189`), `lng=en`. `_VZip`/`Zip` suffix = the response is gzip-compressed at the
HTTP layer (httpx/browser decompress automatically → JSON).

> **Note — `top=true` returns only "top games," not a full sport list.** On
> `/en/line/basketball` the captured `LineFeed/Get1x2_VZip?top=true` returned 10 top
> games *across all sports* (e.g. a football match), not the full basketball card.
> For a complete per-sport prematch list the scraper must add a sport filter
> (`sports=<SI>`, e.g. Basketball `SI=3`, Football `SI=1`) and/or walk champs via
> `GetChampsZip` → `GetGamesZip`. Map the sport-id table during the build.

### Required request headers (values captured live)

```
accept: application/json, text/plain, */*
content-type: application/json
is-srv: false
x-app-n: __BETTING_APP__
x-svc-source: __BETTING_APP__
x-requested-with: XMLHttpRequest
x-mobile-project-id: 0
# x-hd: <long base64 blob>   <- sent on SOME requests; NOT required for the odds
#                              feed (replay without it returned identical data).
#                              This is the operator's "auth token with expiry".
```

Plus **session cookies** (harvested from a browser bootstrap — 21–22 cookies).

### Proof — direct httpx replay (no browser)

Replaying `Get1x2_VZip` from `httpx` through the Kenya proxy, with the base betting
headers + harvested cookies:

```
DIRECT httpx REPLAY: status 200  Success=True  Value=9 events  (29 KB JSON)
   without x-hd  -> status 200  (identical bytes)
```

→ **linebet is scrapable in `hybrid` mode**: bootstrap a browser once to harvest
cookies (the framework's `HybridConfig` + `SessionHarvester` already model this),
then poll the `LiveFeed`/`main-line-feed` endpoints directly with `httpx`. No
browser per poll, no DOM scraping, no `x-hd`/service-worker replay needed.

### Response schema (1xbet terse-key `Value[]`)

Top: `{"Success":true,"Error":"","Value":[ <event>, … ]}`. Per event (key → meaning):

| Key | Meaning | Key | Meaning |
|-----|---------|-----|---------|
| `I` / `ZP` | event id | `O1` / `O2` | team names (`O1E`/`O2E` = English) |
| `SN` / `SI` | sport name / id | `O1I` / `O2I` | team ids |
| `L` / `LI` | league name / id | `S` | start time (unix) |
| `CN` | country | `SC` | score: `FS`={`S1`,`S2`}, `PS`=periods[], `CP`=cur period, `TS`=clock secs, `SLS`=time-left text |
| `E[]` | **markets**: `T`=market-type id, `G`=group (1=1x2, 2=handicap, …), `C`=coefficient (odds), `CV`=odds str, `P`=param (handicap/total line), `B`=blocked | `AE[]` | grouped markets: `{G, ME:[…same as E]}` |

The linebet `extraction/models.py` `Event`/`Market`/`Selection` dataclasses map
onto this directly. A sample decoded event is in
[`snapshots/normalized/livefeed_get1x2_schema.md`](snapshots/normalized/livefeed_get1x2_schema.md).

### Why the operator's earlier scraper failed (all three needed together)

1. **No allowed-country IP** → `203`/block before any feed call.
2. **Missing the `x-app-n` / `x-svc-source` / `is-srv` betting headers** → the
   `service-api` rejects/ignores the request.
3. **No harvested cookies** → unauthenticated. (The `x-hd`/service-worker/IndexedDB
   rabbit hole was a red herring for the odds feed.)

### Remaining unknowns / next build steps

- Map the `T` (market-type) and `G` (group) id tables to human market names
  (1=1x2 W1/X/W2, 2=handicap, 17=totals, …) — partially known from the 1xbet family.
- Confirm cookie TTL / whether re-bootstrap is needed periodically (hybrid session
  refresh).
- Build the `hybrid` scraper: `SessionHarvester` bootstrap → `httpx` poll loop over
  the `LiveFeed` endpoints → map terse JSON to `Event`/`Market`/`Selection`.

## SOLVED (2026-07-18): odds via per-match `GetGameZip` (the markets=0 fix)

The list/live grids render only event *stubs* (teams, league) — **odds do NOT
render in the DOM in headless** (0 coefficient elements on both list and match
pages), and the `top=true` list feed 406s (SW-gated, ADR-4). The odds live in the
**per-match** feed, which is NOT SW-gated and replays from httpx:

```
GET /service-api/{LineFeed|LiveFeed}/GetGameZip?id=<eventId>&lng=en&country=87&partner=189&gr=650&isSubGames=true&grMode=4
  headers: is-srv:false, x-app-n:__BETTING_APP__, x-svc-source:__BETTING_APP__,
           x-requested-with:XMLHttpRequest, x-mobile-project-id:0  + session cookies
```

- `LineFeed/GetGameZip` = prematch, `LiveFeed/GetGameZip` = in-play (the other
  returns `Success:false` for the wrong state). Confirmed live 2026-07-18:
  id=351745496 → `Success:true`, `Value[0].E[]` = **238 markets** (terse
  `T`/`P`/`C`/`G` — maps onto `BetB2BExtractionRules`).
- **`<eventId>`** comes from the match URL the SPA builds on click, e.g.
  `/en/line/basketball/75093-nba-summer-league/351745496-orlando-magic-boston-celtics`
  → id = `351745496`. Extract IDs from the rendered list (game row anchors / click
  target) or from a working list endpoint.

**Scraper model (fixes markets=0):** list → event IDs → `GetGameZip?id=` per event →
parse `E[]`/`AE[]`. This is the odds path; DOM-odds and the `top=true` list feed are
not viable headless.

## SOLVED (2026-07-19): H2H / head-to-head endpoint (`statisticfeed`)

Head-to-head appears on **hover over a team name** (match page only for
scheduled/pre-match events; team el class `scoreboard-team-name`). The H2H popup
shows two tabs: **"Recent Games"** and **"Previous meetings"**.

**Contrary to earlier investigation, the H2H endpoint is NOT ServiceWorker-mediated.
It fires during INITIAL PAGE LOAD and is fully visible to Playwright
`page.on("response")`.** The earlier operator DevTools session (2026-07-18) may have
missed it because it loaded a live/in-play match page where H2H data may not be
pre-fetched, or the SW-cached response didn't trigger a new network request.

Discovered 2026-07-19 via headless Playwright against a **scheduled** (pre-match)
NBA Summer League match:

```
GET https://linebet.com/service-api/statisticfeed/api/v1/Game/h2h?id=737455106&lng=en&ref=189&fcountry=87&gr=650
```

**Key properties:**

| Property | Value |
|----------|-------|
| Path | `/service-api/statisticfeed/api/v1/Game/h2h` |
| Method | GET |
| Media | JSON (~17KB for 19 games) |
| SW-gated? | **NO** — captured via `page.on("response")`, not SW |
| Trigger | Fires on **initial page load**, NOT on hover |
| Hover role | Hover over team name **shows the pre-loaded data** in a popup |
| Game ID source | NOT the URL event ID — comes from `GetGameZip` response |
| httpx-replayable? | **Likely yes** — standard service-api endpoint, base betting headers + cookies |

### Query parameters

| Param | Example | Source |
|-------|---------|--------|
| `id` | `737455106` | Game ID from `GetGameZip` response (not URL event ID `352015844`) |
| `lng` | `en` | Language |
| `ref` | `189` | Partner/affiliate ID |
| `fcountry` | `87` | Country filter |
| `gr` | `650` | Project/group ID |

### Response structure

```json
{
  "teams": [
    {
      "id": "5ab1265c494765f3ca240306",
      "countryId": "153",
      "title": "Brooklyn Nets",
      "subTeams": [{"title": "Brooklyn Nets", "image": "/sfiles/logo_teams/..."}],
      "teamType": 1,
      "clId": 6852,
      "image": "/sfiles/logo_teams/...",
      "country": {"id": 153, "title": "United States", "logoId": 12753, "image": "..."}
    },
    ...  (12 teams total — all NBA teams with games in the returned set)
  ],
  "gameShorts": [
    {
      "id": "6865cd0d9930a40b3ceaeffb",
      "stageId": "68659e8b9930a40b3cb0bfd6",
      "team1": "5ab1265c494765f3ca240306",   // references teams[].id
      "team2": "5ab1265c494765f3ca240317",
      "dateStart": 1752183000,                // Unix timestamp
      "score1": 81,
      "score2": 90,
      "subScore1": 0,
      "subScore2": 0,
      "countRedCards1": 0,
      "countRedCards2": 0,
      "winner": 2,                            // 1=team1, 2=team2, 0=draw
      "status": 3,                             // 3=finished
      "subStatus": 0,
      "periods": [
        {"score1": 15, "score2": 22, "type": 18},
        {"score1": 22, "score2": 22, "type": 19},
        {"score1": 21, "score2": 23, "type": 20},
        {"score1": 23, "score2": 23, "type": 21}
      ]
    },
    ...  (19 gameShorts entries)
  ],
  "sportId": 3,
  "subSportId": null,
  "entity": "..."
}
```

### Period types (basketball)

| `type` | Meaning |
|--------|---------|
| 18 | 1st quarter |
| 19 | 2nd quarter |
| 20 | 3rd quarter |
| 21 | 4th quarter |

### How to find the Game ID (`id` param)

The `id` parameter (`737455106` in the example) is **NOT the event ID in the URL**
(`352015844`). It comes from somewhere in the `GetGameZip` response or the page
state. Possible sources:
- `GetGameZip` response may contain a `constId` field
- The `SubscriptionServiceV3/api/v3/games/GetSubsOptionsForGame?constId=737455106`
  endpoint uses the same ID — confirmed during discovery
- The ID may be embedded in the page HTML or the service worker state

### Full endpoint catalog (linebet.com match page bootstrap)

| # | Endpoint | Size | Purpose |
|---|----------|------|---------|
| 1 | `GET /bff-api/config/group/get?groups=b.core,...` | 92KB | App config/bootstrap |
| 2 | `POST /analytics-module-api/v1/analytics` | 152b | Analytics ping |
| 3 | `GET /fatman-api/.../fc` | 7b | Fatman ping |
| 4 | `GET /fatman-api/.../ab.json` | 2b | A/B test assignment |
| 5 | `GET /fatman-api/.../event.json` | 23b | Analytics event |
| 6 | `GET /fatman-api/.../metadata.json` | 42b | Analytics metadata |
| 7 | `GET /bff-api/config/group/get?groups=b.rum` | 128b | RUM config |
| 8 | `GET /bff-api/event-logo/v2/suitable.json` | 1KB | Event logos |
| 9 | `GET /sys-*-app-front/.../match-page` | 3-4KB | Microfrontend shells |
| 10 | `GET /service-api/gamespreview/getbanner` | 219b | Banner |
| 11 | `POST /web-api/api/v3/bonuses/welcome-bonuses` | 837b | Welcome bonuses |
| 12 | `GET /web-api/api/third-party/banner-for-header` | 232b | Header banner |
| 13 | `GET /bff-api/config/licenses.json` | 2KB | Licenses |
| 14 | `GET /web-api/session` | 7b | Session check |
| 15 | `POST /hd-api/external/verify` | 737b | Human verification |
| 16 | `GET /bff-api/config/group/get?groups=d.bringfriend` | 146b | Referral config |
| 17 | `POST /web-api/api/v3/bonuses/first-deposit` | 436b | Deposit bonus |
| 18 | **`GET /service-api/statisticfeed/api/v1/Game/h2h`** | **18KB** | **★ H2H data** |
| 19 | `GET /service-api/LineFeed/GetGameZip` | 15KB | Match markets/odds |
| 20 | `GET /service-api/LineFeed/GetSportsShortZip` | 15KB | Sports tree |
| 21 | `GET /service-api/main-line-feed/v1/expressDay` | 24KB | Line feed |
| 22 | `GET /service-api/main-live-feed/v1/expressDay` | 10KB | Live feed |
| 23 | `GET /service-api/LineFeed/WebGetTopChampsZip` | 506b | Top champs |
| 24 | `GET /service-api/LineFeed/GetTopGamesStatZip` | 9KB | Top games stats |
| 25 | `GET /service-api/SubscriptionServiceV3/api/v3/games/GetSubsOptionsViews` | 194b | Subs views |
| 26 | `GET /service-api/SubscriptionServiceV3/api/v3/games/GetSubsOptionsForGame` | 49b | Subs for game |
| 27 | `GET /bff-api/config/video.json` | 2KB | Video config |
| 28 | `POST /account-api/user/v1/phone-data` | 31KB | Phone data |
| 29 | `POST /flexreg-api/v1/registration/form/widget` | 56KB | Registration form |
| 30 | `GET /platform-apps-legacy-api/mobile` | 311b | Mobile platform |

### How H2H discovery was done (methodology)

1. Use a **scheduled** (not live) match from a **major league** (NBA Summer League)
2. Navigate to match page with `wait_until="load"` + 25s SPA hydration wait
3. Capture all responses via `page.on("response")` (NOT ServiceWorker-mediated!)
4. Filter for `/service-api/` paths
5. Hover over team names (`.scoreboard-team-name`) using Playwright `.hover()`
   + JS `MouseEvent` dispatch for redundancy
6. The H2H popup appears with "Recent Games" / "Previous meetings" tabs
7. The actual API call happened at **bootstrap time** (index 130/153), hover just
   reveals the pre-loaded UI

### Previous incorrect assumptions (corrected)

| Assumption | Correction |
|------------|------------|
| H2H is SW-mediated, invisible to Playwright | **False** — visible via `page.on("response")` for scheduled matches |
| H2H fires only on hover | **False** — data is pre-loaded at bootstrap, hover only shows UI |
| `GetSportsShortZip` might carry H2H data | **False** — it's the sports sidebar tree |
| H2H endpoint is a separate SW request | **False** — it's `statisticfeed/api/v1/Game/h2h` |

<!-- SECTION REPLACED 2026-07-19 — H2H endpoint discovered and documented in SOLVED section above -->

<!-- SECTION REPLACED 2026-07-19 — H2H endpoint discovered. All candidate endpoints tested negative. The real endpoint is /service-api/statisticfeed/api/v1/Game/h2h -->

<!-- SECTION REPLACED 2026-07-19 — Conclusion was correct (separate endpoint needed), but SW-mediated assumption was wrong. The actual endpoint /service-api/statisticfeed/api/v1/Game/h2h IS visible to Playwright and fires at bootstrap, NOT on hover. -->
