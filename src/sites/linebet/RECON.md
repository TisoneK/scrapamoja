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

## Open questions for the next session

1. **Find the live-odds endpoint.** It's behind the service-worker transport.
   Next step: attach a **CDP** session with `Target.setAutoAttach` to the service
   worker target and enable `Network` there, OR read the IndexedDB `vpn/headers`
   at runtime and look for the odds fetch the app issues. (The SPA `entry-*.js`
   only revealed the casino `service-api` endpoints, not the sportsbook feed —
   the sportsbook chunk is loaded separately.)
2. **DOM extraction fallback.** Odds render fully in the DOM; a Playwright DOM
   extractor is the reliable path today. Selectors live in the live betting grid
   (`c-events` / champ rows).
3. Feed a real capture to the scraping-mode classifier — this is the validation
   case (expected: hybrid/playwright with a SW transport, not clean intercept).
