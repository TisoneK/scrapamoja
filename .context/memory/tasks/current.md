# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
check its session entry and backlog before starting.

**SESSION 11 COMPLETE (2026-07-17, local agent / Claude Opus 4.8 on
Baos-Mac-mini):** Built the proxy abstraction (Stages 1–3+5), then plugged
in the user's Kenyan proxy (Stage 4) and did the FIRST live linebet capture.
All 5 stages done + pushed. Recon findings written up in
`src/sites/linebet/RECON.md` + `snapshots/normalized/linebet_api_catalog.json`
(commit `9878dcf`). Proxy transport used: `gost` HTTP proxy (Kisumu, KE)
→ `bore` TCP tunnel (`bore.pub:<port>`) → framework `ProxyManager`. ngrok
was NOT usable (TCP needs card); `bore` (no account) worked.

**How the session evolved:** started as linebet recon ("learn the headers
+ endpoints, use a proxy if you can't connect"). Confirmed BOTH browser
surfaces available to a local agent egress from a **US datacenter IP**
(`135.180.70.225`) — the in-app Browser (`mcp__Claude_Browser__*`) AND
"Claude in Chrome" (`mcp__claude-in-chrome__*`) both hit linebet's geo-block
(HTTP 203 → `/en/block`, "not available in your country • US"). So a local
agent CANNOT reach linebet from here without a proxy. The user then asked
to build a **robust ProxyManager abstraction FIRST** (validated in 5 stages)
before plugging in their Kenyan Windows proxy via ngrok.

**What got built (all committed + pushed to main):**
- `src/network/proxy/` — canonical proxy layer (the single chokepoint):
  `models.py` (ProxyScheme incl. DIRECT, ProxyEndpoint with
  to_playwright_proxy/to_httpx_proxy/to_url/from_url + legacy adapters +
  credential-safe repr, ProxyHealth), `manager.py` (ProxyManager: rotation
  round-robin/random/sticky/health-weighted, health, failover, per-site
  RoutingRule, with_failover), `providers.py` (Direct/Static/ManualEndpoint
  incl. `.ngrok()`), `verify.py` (verify_proxy egress-IP+geo via httpx 0.28
  `proxy=`, + Playwright variant), `config.py` (build_proxy_manager(dict) —
  declarative pool + routing).  Commit `44a4bce`, `467acb1`.
- Chokepoint wiring: `HarExporterConfig.proxy` + `--proxy` CLI
  (`src/network/har/export.py`), injected ProxyManager w/ flat-field
  fallback in `browser/session_manager.py`, `set_proxy_manager()` +
  create_context apply in `browser/session.py`, `proxy=` in
  `network/direct_api/client.py`.  Commit `8bc8a29`.
- Tests: 47 proxy unit tests + 3 Stage-2 local-proxy routing integration
  tests (in-process recording CONNECT proxy proves httpx AND Playwright
  route through the manager's endpoint).  Commits `8fb284f`, `467acb1`.
  har + direct_api suites still green (no regressions).

**KEY RECON FINDINGS (Stage 4 — DONE):**
- Kenya proxy → linebet `/en` + `/en/live` load `200` (not 203). Egress
  confirmed KE (102.210.56.70, Kisumu). Live sportsbook DOM renders real
  matches + odds (screenshot verified).
- **Live odds feed is invisible to interception.** Odds render in the DOM,
  but ZERO odds requests appear at Playwright page/context level, in the
  HAR, or as page WebSocket/SSE. Transport is service-worker-mediated:
  `ivpn-sw.js` injects headers from IndexedDB (`vpn/headers`; derives
  `x-dt` from `x-project-id`), `domain-sw.js` does mirror-domain failover
  (`/checker/redirect/stat/run/`). So linebet is NOT clean `intercepted`
  mode — DOM/hybrid extraction (or CDP-level SW capture) is required.
- Bootstrap API surface documented: `bff-api` (config/licenses/event-logo,
  params `lang/d/g=KE/p=650`), `web-api` (session 204, bonuses KES, banners),
  `service-api/gamespreview/*`, `fatman-api` (telemetry), `analytics-module-api`.
  Full writeup: `src/sites/linebet/RECON.md` + `snapshots/normalized/
  linebet_api_catalog.json`.

**NEXT STEPS (future sessions):**
1. Find the actual live-odds endpoint: attach CDP `Target.setAutoAttach`
   to the service-worker target + enable `Network` there, OR read
   IndexedDB `vpn/headers` at runtime and locate the sportsbook fetch.
   (SPA `entry-*.js` only exposed casino `service-api` endpoints, not the
   sportsbook feed — that chunk loads separately.)
2. Build a DOM extractor for the live grid (`c-events`/champ rows) as the
   reliable path — odds render fine.
3. Feed a real capture to the scraping-mode classifier (the deliverable).
4. Migrate `stealth/coordinator` + `navigation` onto the canonical
   ProxyManager; deprecate duplicate ProxySettings (backlog item).

**Standing reframe (Session 10):** linebet is the validation CASE for a
future site scraping-mode classifier (`src/extraction/classifier/`), not
the deliverable. The proxy layer is prerequisite infra for capturing the
linebet HAR that feeds the classifier.
