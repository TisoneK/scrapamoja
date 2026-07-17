# Linebet — how it works (live recon, 2026-07-17)

First successful **live** capture of linebet.com, via a residential Kenyan proxy
(`gost` HTTP proxy on a Windows box in Kisumu → `bore` TCP tunnel → this machine's
`ProxyManager`). All prior sessions were WAF/geo-blocked from datacenter IPs. This
documents what the live site actually does. Companion data:
[`snapshots/normalized/linebet_api_catalog.json`](snapshots/normalized/linebet_api_catalog.json).

## TL;DR for a future scraper

- **Access is geo-gated at the nginx edge.** From a US/datacenter IP you get
  `HTTP 203 → /en/block` before any app code runs. From an allowed-country IP
  (Kenya confirmed) the full SPA loads (`200`). The detected country flows through
  every API call as the `g=` query param (`g=KE` here; `g=US` on the block page).
- **The live odds feed is NOT a normal XHR/WebSocket you can intercept.** The
  sportsbook renders real live matches + odds in the DOM, yet *zero* odds requests
  appear at Playwright's page **or** context level, in the HAR, or as a page
  WebSocket/SSE. The transport is mediated by a **service worker** (see below), so
  standard network interception and HAR replay will **not** capture live odds.
- **Practical extraction path is the rendered DOM** (Playwright/`hybrid`), or
  reverse-engineering the service-worker header injection + the odds endpoint.
  This is a strong signal for the scraping-mode classifier: linebet is **not**
  cleanly `intercepted` mode.

## Anti-blocking architecture (three service workers)

The site installs three service workers that together defeat naive scraping and
domain blocking:

| SW | Role |
|----|------|
| `ivpn-sw.js` | **Header injection.** Keeps a set of headers in IndexedDB (`vpn` DB → `headers` store), loads them into memory, and on every request clones it and sets all stored headers. Notably it derives `x-dt` from `x-project-id` (`c.set("x-dt", u["x-project-id"])`) and forces `mode:"same-origin"`. So API requests carry SW-injected headers a plain HTTP replay won't have. |
| `domain-sw.js` | **Mirror-domain failover.** Fetches `/checker/redirect/stat/run/` → a list of backup `domains`, probes each via `https://<domain>/static/pixel.gif?<ts>`, and reports LOADED/ERROR back to `/checker/redirect/stat/`. This is how the site survives domain takedowns. |
| `check-rum.worker.js` | RUM / performance monitoring (not data). |
| `pwa-module-sw.js` | PWA cache (`networkFirst` + TTL cache cleanup). |

Implication: any direct-API replay must reproduce the `ivpn-sw` header set
(`x-project-id`, `x-dt`, and whatever else the app writes into the `vpn/headers`
store at runtime) — read them out of IndexedDB after the app initializes.

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

## Prior operator investigation (the header mystery — now explained)

An earlier abandoned attempt (operator's own notes, folded in 2026-07-17) got
further on the *data* endpoint than this session's automated capture, and the two
halves now fit together:

- **The odds data comes from a `LineFeed` endpoint** — the classic
  1xbet/melbet-family `/LineFeed/...` feed. This confirms linebet runs that
  platform. (This session didn't see it because it's issued behind the service
  worker; see below.)
- **The response is heavily compressed**; once decompressed it is JSON with
  **terse single-letter keys** (`T`, `E`, `C`, `G`, …) — the standard 1xbet
  LineFeed schema (e.g. `Value[].O1/O2` = teams, `E[]` = markets with `T`=type,
  `C`=coefficient). The exact key map must be re-derived from a live capture.
- **The request carried auth headers the scraper could never reproduce** — an
  auth token **with an expiry time**, plus a header carrying the **URL of the
  previous page** (a referer-like navigation-context header). In a real browser
  they were all present; in a plain HTTP scraper they were **completely absent**.

**Why the headers were invisible — solved.** This is exactly what `ivpn-sw.js`
does (see the SW table above): it keeps those headers in IndexedDB (`vpn`/
`headers`), and the **service worker injects them into every outgoing request**
*after* the page hands the request off. So they never appear in the page's own
JS, in network interception, or in the HAR — the browser "has" them only because
the SW adds them. That is the mechanism behind the operator's observation and
behind this session's "odds feed invisible to interception" finding. Same wall,
two sides.

## Concrete plan for next session (the unblock)

The proxy must be live again (gost + a TCP tunnel, e.g. `bore`; see capture recipe
above). Then:

1. **Dump the injected headers.** Load linebet live, let the SPA initialize, then
   read IndexedDB `vpn` → `headers` (via `page.evaluate` opening the DB, or CDP
   `IndexedDB.requestData`). This yields the auth token, its expiry, `x-project-id`
   / `x-dt`, and the referer-like navigation header — the set `ivpn-sw.js` injects.
2. **Capture a real `LineFeed` request.** Either attach a **CDP** session with
   `Target.setAutoAttach {autoAttach:true, flatten:true}` to the **service-worker**
   target and enable its `Network` domain (page-level Playwright can't see SW
   traffic), or find the `LineFeed` URL + query params in the sportsbook JS chunk
   (loaded separately from the `entry-*.js` that only exposed casino `service-api`).
3. **Replay `LineFeed` directly** with the IndexedDB-sourced headers, then
   **decompress** (try gzip/deflate/brotli; the platform sometimes wraps a custom
   scheme) → parse the terse JSON. Map the single-letter keys to `Event`/`Market`/
   `Selection` (the linebet `extraction/models.py` dataclasses already exist).
4. **Watch the token expiry.** Because the auth header expires, a long-running
   scraper must re-harvest it from IndexedDB (or re-bootstrap the browser) on a
   timer — this is a `hybrid`/`sw_replay` concern, not simple `intercepted`.

**DOM fallback (works today):** odds render fully in the DOM; a Playwright DOM
extractor over the live betting grid (`c-events` / champ rows) is the reliable
path if the LineFeed replay proves too brittle.

**Classifier note:** feed a real capture to the scraping-mode classifier — linebet
is the validation case. Expected output: `playwright` (or the future `sw_replay`)
extraction mode **plus** an AccessProfile of `geo_gated + requires_proxy +
transport: service_worker + interceptable: false + header_source: indexeddb`
(see ADR-2 in `.context/memory/plans/decisions.md`).
