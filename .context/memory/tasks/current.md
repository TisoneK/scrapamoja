# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now. Set it at
session start (protocol Step 3), clear it at session end (Step 15). If
you find a stale in-progress entry here, a prior session died mid-task —
check its session entry and backlog before starting.

**BLOCKED ON USER (Session 11, 2026-07-17, local agent / Claude Opus 4.8
on Baos-Mac-mini):** Building the proxy abstraction, then capturing
linebet through a Kenyan proxy. Stages 1–3 + 5 DONE and pushed; Stage 4
(the actual linebet capture) is blocked waiting for the user's ngrok
connection details (host:port + basic-auth user/pass for a `gost` HTTP
proxy on their Kenyan Windows box).

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

**NEXT STEP (Stage 4 — resume here when the user sends ngrok details):**
1. Build a manager: `build_proxy_manager({"endpoints": [{"id":"direct",
   "scheme":"direct"}, {"id":"kenya","url":"http://USER:PASS@HOST:PORT",
   "country":"KE","source":"ngrok"}], "routing":[{"pattern":"*linebet.com",
   "target":"kenya"}], "default_target":"direct"})`.
2. `verify_proxy(manager.get("kenya"))` → assert egress countryCode == "KE".
3. `HarExporter(HarExporterConfig(url="https://linebet.com/en",
   live_url="https://linebet.com/en/live", proxy=manager.get("kenya"),
   output=Path("linebet_kenya.har")))` → expect 200 (not 203/block),
   record HAR.
4. Replay: `HarReplayer` + `src/core/snapshot/normalize.py` → catalog the
   REAL sports/odds endpoints + request headers (the original recon goal).
   Commit the normalized snapshot under `src/sites/linebet/snapshots/`.
5. Follow-up backlog item: migrate `stealth/coordinator` + `navigation`
   onto the canonical ProxyManager and deprecate the duplicate
   ProxySettings classes (see backlog).

**Standing reframe (Session 10):** linebet is the validation CASE for a
future site scraping-mode classifier (`src/extraction/classifier/`), not
the deliverable. The proxy layer is prerequisite infra for capturing the
linebet HAR that feeds the classifier.
