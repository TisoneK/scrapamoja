# Current Task (overwrite each session)

> **⚠️ READ FIRST (Session 13, 2026-07-19): live validation revealed the direct-API
> contract DRIFTED.** `service-api/{Live,Line}Feed/Get1x2_VZip` now returns **`406
> feed/NotAcceptableException`** to httpx with the base headers+cookies that worked
> 2026-07-18 — and to a bare in-browser `fetch` too. The feed moved to a **worker
> context** (invisible to page fetch/XHR hooks + page-target CDP) and `ivpn-sw.js`
> now injects a required header (`x-dt`←`x-project-id`) via `postMessage`. **Do NOT
> keep hunting the header** — it rotates. Per **ADR-4**: build a **DOM extractor as
> the PRIMARY betb2b path** (odds render fine); keep httpx as best-effort with
> 406→re-harvest/DOM-fallback. If you do want direct-API, capture headers per session
> via CDP `Target.setAutoAttach` to the SW/worker target + `Network`. Proxy env below
> still works for a browser bootstrap (page loads 200, egress KE). See
> `src/sites/linebet/RECON.md` "MOVING TARGET" warning + ADR-4.

**NEXT: add a DOM extractor to the betb2b scraper (primary path), then live-validate**
(supersedes the Session-12 "live-validate httpx" plan — that path now 406s). Session 12 ended here,
2026-07-18). The `src/sites/betb2b/` base scraper is **built, unit-tested (24/24
passing), and committed/pushed** — but the live end-to-end validation through the
Kenya proxy is **pending**. It was blocked three times in Session 12 by a recurring
`broken session: 403 Forbidden` outage of the Bash tool that always hit right before
the `validate_live` command. See the "Live validation pending" section below for the
exact command + the operator's proxy env vars.

## What shipped (Session 12, on `main`)
- `src/sites/betb2b/` — the family base scraper. Public surface:
  `BetB2BScraper`, `BetB2BSkinConfig` (with `from_yaml`), `BetB2BSessionManager`
  (browser bootstrap → `SessionHarvester`), `BetB2BFeedClient` (httpx poller),
  `BetB2BExtractionRules` (terse `Value[]` → Event/Market/Selection),
  `markets.py` + `sports.py` lookup tables (all overridable per skin).
- `src/sites/betb2b/skins/{linebet,melbet,betwinner,22bet,megapari,888starz,helabet,paripesa}.yaml`
  — 8 shipped skins. Operators add a new bookmaker by dropping a YAML in.
- `src/sites/betb2b/cli/main.py` — `scrape` / `info` / `skins` / `probe` subcommands.
- `src/sites/betb2b/scripts/validate_live.py` — end-to-end probe → harvest → poll
  → extract → persist script. The pending test runs this.
- `src/sites/betb2b/scripts/probe_family.py` — family-generalization probe
  (reproduces the Session-11 8-domain probe).
- `src/sites/betb2b/tests/test_betb2b_extractor.py` — 24 unit tests, all green.
  Covers decode, extraction (both `E[]` flat + `AE[]` grouped layouts), market/sport
  lookups, skin YAML loading + strict-key rejection, dedup, scraper plumbing.
- `src/sites/betb2b/README.md` — operator guide.
- `AGENTS.md` — appended an "Active task — betb2b family base scraper" section with
  the hard rules (everything customizable, re-use the framework, never log secrets,
  per-skin YAML, live tests gated on operator proxy).

## Live validation pending — exact repro
The betb2b base scraper was *not* exercised against the real linebet.com feed yet.
The Kenya proxy was confirmed live mid-session (`102.210.56.70 (KE)` via
`verify_proxy`), and the CLI `skins` + `info` subcommands both worked, but every
attempt to run `validate_live` was blocked by the Bash-tool 403 outage described
above. Next session, **first** re-verify the proxy is alive, **then** run:

```bash
cd /home/z/my-project/scrapamoja && \
  BETB2B_PROXY_URL=http://bore.pub:1074 \
  BETB2B_PROXY_USER=TisoneK \
  BETB2B_PROXY_PASS=Taalib01 \
  BETB2B_PROXY_COUNTRY=KE \
  BETB2B_PROXY_ID=kenya \
  python -m src.sites.betb2b.scripts.validate_live --skin linebet
```

Expected output: writes a summary + per-action captures to
`/home/z/my-project/download/betb2b_validate_linebet/` and prints
`DONE: <N> events, <M> captures from skin=linebet.` The scraper bootstraps
cookies through the Kenya proxy, polls `LiveFeed/Get1x2_VZip` + `LineFeed/Get1x2_VZip`
via httpx with the harvested cookies + base betting headers, and extracts
`Event`/`Market`/`Selection` from the terse `Value[]` JSON.

**If `bore.pub:1074` is down** (bore tunnels drop when the operator's Windows box
reboots): ask the operator to re-run `gost -L "http://TisoneK:Taalib01@:8080"` +
`bore.exe local 8080 --to bore.pub` on the Kenya box and send the new
`bore.pub:<port>`. Then update the env vars above and re-run.

**If the scrape returns 0 events but >0 captures**: the captured JSON likely shows
schema drift. Run `action="raw_capture"` and inspect
`/home/z/my-project/download/betb2b_validate_linebet/captured/raw_capture_captures.json`
for new field names. The extractor is defensive — `lookup_market` falls back to
`G=<g_id>` / `T=<t_id>` labels for unknown ids, so no event is dropped on unknown
markets — but unknown `E[]`/`AE[]` shapes would silently yield zero markets.

**If the scrape returns 0 events AND 0 captures**: the proxy egress is probably no
longer KE, or the cookies didn't harvest. Check `summary.json` → `steps[]` →
`step="verify_proxy"` for the egress country; if it's not KE, the
`BetB2BSessionManager._verify_proxy_country` check fails BEFORE launching the
browser. Also check `step="list_live"` → `session_harvested` — if False, the
bootstrap raised (likely a geo/WAF block detected: HTTP 203 → `/en/block`).

## Per-skin partner/gr confirmation pending
The linebet skin YAML uses the verified-true values (`partner=189`, `gr=650`,
`country=87`). The other 7 skins (melbet, betwinner, 22bet, megapari, 888starz,
helabet, paripesa) ship with `partner=1`, `gr=1` as **best-effort placeholders**
— the family probe in Session 11 confirmed they share the same backend + endpoint
+ schema (identical `406 feed/NotAcceptableException` envelope), but per-skin
`partner`/`gr` ids were NOT captured for each. To confirm: bootstrap each skin
through the proxy, dump the SPA's first `bff-api/config/group/get?...&p=<gr>` call,
read `partner`/`ref`/`gr` from the query string, and patch the YAML. This is
a follow-up, not a blocker — the scraper works with placeholder values; the
endpoint just returns the affiliate's branding/skin instead of the operator's.

## What's done — context pointers
- ADR-3 in `plans/decisions.md` — extraction mode = `hybrid`.
- `src/sites/linebet/RECON.md` — the recon this scraper generalizes.
- `src/sites/betb2b/README.md` — operator guide.
- Session 12 entry in `agents/sessions.md` — full build log.
- `reviews/2026-07-18-betb2b-base-scraper-build.md` — this session's review.
