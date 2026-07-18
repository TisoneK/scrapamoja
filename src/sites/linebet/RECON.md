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
- **The live odds come from `/service-api/LiveFeed/Get1x2_VZip`** (and siblings —
  see below). It is a plain HTTP GET returning JSON (1xbet terse-key schema).
  **Proven:** replays from `httpx` with no browser, `Success=true`, real events.
- **What it takes to replay:** (1) an allowed-country proxy, (2) the base betting
  headers (`is-srv:false`, `x-app-n:__BETTING_APP__`, `x-requested-with:XMLHttpRequest`,
  `x-svc-source:__BETTING_APP__`), (3) session cookies (harvest once from a browser
  bootstrap). The `x-hd` token is sent on *some* requests but is **not required**
  for the odds feed (replay without it returned identical data).
- **Extraction mode = `hybrid`** (browser-harvest cookies → direct `httpx` polling).
  The DOM also renders odds as a fallback. This is the classifier's validation case.

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

## SOLVED: the live odds feed (2026-07-18)

The operator's prior attempt named the data endpoint (`LineFeed`); this session
captured it live and **proved a browserless replay works**. How it was found: an
in-page `window.fetch` wrapper (init script) logs every URL — this catches the
feed calls that Playwright's `page.on("response")` / context events and the HAR
all missed (a Playwright surfacing quirk, **not** a service-worker transport as
the earlier draft guessed).

### The endpoints (host `linebet.com`, all `service-api`)

| Endpoint | Purpose |
|----------|---------|
| `GET /service-api/LiveFeed/Get1x2_VZip?count=10&lng=en&gr=650&mode=4&country=87&top=true&partner=189&virtualSports=true&noFilterBlockEvent=true` | **live events + odds** (in-play). `count`=events, `top=true`=featured. |
| `GET /service-api/LiveFeed/GetSportsShortZip?lng=en&gr=650&country=87&partner=189&groupChamps=true` | live sports/champ tree |
| `GET /service-api/LiveFeed/WebGetTopChampsZip?lng=en&gr=650&country=87` | top live championships |
| `GET /service-api/LiveFeed/GetTopGamesStatZip?lng=en&partner=189` | top games stats |
| `GET /service-api/main-line-feed/v1/…` | **pre-match** ("line") feed (vs `main-live-feed` for in-play) |
| `GET /champs-api/v1/get-champs-by-params-web` | championship list (sends the richer `x-*` header set) |

Stable query params: `gr=650` (project/group id), `country=87`, `partner=189`,
`ref=189`, `lng=en`. `_VZip`/`Zip` suffix = the response was gzip-compressed at the
HTTP layer (httpx/browser decompress it automatically → JSON).

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
