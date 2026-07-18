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
