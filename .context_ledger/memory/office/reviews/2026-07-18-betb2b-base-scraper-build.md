# Review — BetB2B family base scraper (build)

**Date:** 2026-07-18 · **Session:** 12 · **Agent:** Super Z / GLM (cloud sandbox)
**Scope:** Build the `src/sites/betb2b/` family base scraper per ADR-3 + the Session-11
betb2b family recon. Live validation deferred to next session.

## 1. Executive summary

Built a single parameterized scraper for the BetB2B/1xbet family — linebet, melbet,
betwinner, 22bet, megapari, 888starz, helabet, paripesa — with per-skin config in YAML.
Extraction mode is `hybrid` (ADR-3): browser bootstrap through an allowed-country proxy
harvests ~21 session cookies, then `httpx` polls `/service-api/{LiveFeed,LineFeed}/…`
directly. 24 unit tests pass; live end-to-end validation is pending (blocked by a
recurring Bash-tool 403 outage, not code or proxy).

This is the flagship example of Scrapamoja's "one framework, many sites" thesis: linebet
was reverse-engineered first (see `src/sites/linebet/RECON.md`), and the findings
generalize across 8+ family members (verified 2026-07-18 via the Kenya proxy). One
`BetB2BSkinConfig` YAML per bookmaker, no Python changes needed to add a new skin.

## 2. What shipped

See `src/sites/betb2b/README.md` for the full operator guide. Highlights:

- `BetB2BSkinConfig` (`config.py`) is the customization surface — every URL, header,
  query param, market-id, sport-id is a field on the dataclass, overridable per skin
  via YAML. The `from_yaml()` loader does strict-key checking so typos fail fast.
- `markets.py` (15 market groups, 23 market types) and `sports.py` (37 sports) carry
  the family-shared `G` / `T` / `SI` lookup tables. `lookup_market()` degrades
  gracefully to `G=<g>` / `T=<t>` labels for unknown ids.
- `extraction/rules.py` is defensive — handles both `E[]` (flat, grouped by `G`) and
  `AE[]` (grouped, with `ME[]` sub-arrays) market layouts, prefers `AE[]` and uses
  `E[]` to enrich. Coerces the `SC` block to (status, minute, period, time_remaining),
  pulls English team names from `O1E`/`O2E`, appends the `P` line to selection labels
  for handicap/totals markets. Never raises on schema drift.
- `session.py` — `BetB2BSessionManager` re-uses the framework `SessionHarvester` +
  `SessionValidator`; pre-bootstrap proxy-country verification fails fast on
  misconfigured egress; TTL-based + auth-error-based re-bootstrap.
- `client.py` — `BetB2BFeedClient` uses httpx 0.28 `proxy=` and the canonical
  `ProxyEndpoint.to_httpx_proxy()`; rate-limited; long-lived `AsyncClient` for
  connection pooling.
- `scraper.py` — `BetB2BScraper` orchestrator wires into the framework
  `ProxyManager.acquire(site=domain, endpoint_id=…)`; de-dupes events by `event_id`
  (merges markets, prefers the live version).
- `cli/main.py` — `scrape` / `info` / `skins` / `probe` subcommands; proxy config
  from env vars (`BETB2B_PROXY_URL`/`USER`/`PASS`/`COUNTRY`/`ID`) — no secrets in
  CLI args.
- `scripts/validate_live.py` — end-to-end probe → harvest → poll → extract → persist;
  `scripts/probe_family.py` — reproduces the Session-11 8-domain family probe.
- `skins/*.yaml` — 8 shipped skins. linebet uses verified-true values (`partner=189`,
  `gr=650`, `country=87`, `geo=KE`); the other 7 ship with `partner=1` / `gr=1`
  placeholders (per-skin `partner`/`gr` ids NOT captured yet — see `tasks/current.md`).

## 3. Test results

`pytest src/sites/betb2b/tests/ -v` → **24 passed, 0 failed** (3.46s). No network, no
browser. Covers: decode (valid/empty/invalid JSON, Success=false), extraction (live
feed, prematch feed, AE-grouped markets, E-flat markets, non-event dict filtering,
unknown market ids degrade gracefully), market/sport lookups, skin YAML loading
(defaults filled, unknown keys rejected), `feed_url` rendering (both roots + extra
params), `merged_headers` with cookies, `with_overrides`, dedup (market merge +
live-version preference), `get_info`.

The repo's broader pytest baseline is still broken (per the Session-4 backlog items —
`pytest.ini` header bug, ~24% of tests hang, 15 collection errors); this session did
NOT touch any of that.

## 4. Live validation — pending

The Kenya proxy was verified live mid-session (`102.210.56.70 (KE)` via `verify_proxy`).
The CLI `skins` and `info --skin linebet` subcommands both ran successfully. Four
attempts to execute `python -m src.sites.betb2b.scripts.validate_live --skin linebet`
were each blocked by the Bash tool returning `broken session: 403 Forbidden` on every
invocation (including `echo retry`). The outage is a session-level tool-surface issue,
not a code or proxy issue — two of the four hit AFTER `verify_proxy` had just succeeded.

Resume command + triage steps are in `.context/memory/tasks/current.md` under
"Live validation pending". A next-session agent should run it as the first action.

## 5. Open items

- **HIGH:** live-validate `validate_live --skin linebet` end-to-end. Next agent runs
  it; if 0 events / 0 captures, the task file has the triage steps (check
  `verify_proxy` egress country, check `session_harvested` flag, check for geo/WAF
  block in `summary.json` → `steps[]`).
- **MEDIUM:** confirm per-skin `partner`/`gr` ids for the 7 non-linebet skins
  (bootstrap each, dump `bff-api/config/group/get?...&p=<gr>` from the SPA, patch the
  YAMLs).
- **MEDIUM:** run `probe_family.py` through the proxy to re-confirm the
  family-generalization signal against the current set of domains.
- The "Generalize the linebet scraper into a betb2b family base scraper" backlog item
  is DONE this session — marked `[x]` in `tasks/backlog.md`.

## 6. Architectural notes

- **Extraction mode = `hybrid`** (ADR-3, refines ADR-2). The earlier `sw_replay` mode
  reserved by ADR-2 is no longer motivated — the linebet odds feed is a plain XHR
  that replays from httpx with base betting headers + cookies + an allowed-country
  proxy.
- **One framework, many sites.** The betb2b package is the first scraper in the repo
  that is parameterised by skin rather than by site. It does NOT subclass
  `BaseSiteScraper` (the registry's one-class-per-site model doesn't fit); per-skin
  `LinebetScraper`-style adapters can wrap `BetB2BScraper` if registry integration
  becomes a requirement.
- **Customizability surface.** Every BetB2B family difference is a YAML field:
  identity (`domain`/`partner`/`gr`/`country`/`geo`), feed paths, query params,
  headers, stealth profile, session TTL, market-id table, sport-id table, proxy
  endpoint id, allowed countries, feature flags. Operators add a new bookmaker by
  dropping a YAML in `src/sites/betb2b/skins/` — no Python changes needed.
- **Re-uses the framework.** `ProxyManager` (`src/network/proxy/`),
  `SessionHarvester` + `SessionValidator` (`src/network/session.py`), and
  `ExtractionMode.HYBRID` (`src/sites/base/site_config.py`) are all wired in — no
  re-implementation.
