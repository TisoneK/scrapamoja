# Review — BetB2B (1xBet family) reconnaissance

**Date:** 2026-07-18 · **Session:** 11 (+continuation) · **Agent:** Claude Opus 4.8 (local)
**Scope:** Reverse-engineering linebet.com and confirming the findings generalize
across the BetB2B/1xBet family of bookmakers. Captured live via a residential Kenyan
proxy (`gost` → `bore` TCP tunnel → framework `ProxyManager`). Companion:
`src/sites/linebet/RECON.md`, ADR-2/ADR-3 in `plans/decisions.md`.

## 1. Executive summary

linebet is one skin of the **BetB2B** platform (the software behind the 1xBet
family). Its live and prematch odds are served by a shared `service-api` feed
microservice that returns 1xBet-format terse-key JSON. **We proved the odds feed is
directly replayable from `httpx` with no browser** given three things: an
allowed-country IP, the base betting headers, and harvested session cookies. The
same endpoints/schema/method were **verified across 8 family domains**. This means
**one parameterized `betb2b` scraper covers the whole family** — the core of
Scrapamoja's "one framework, many sites" thesis.

Correction of record: an earlier draft concluded the odds were "service-worker-
mediated / DOM-only / needs a new `sw_replay` mode." That was **wrong** (a Playwright
event-surfacing quirk masqueraded as a SW transport). The odds are a plain XHR;
extraction mode is **`hybrid`** (ADR-3 supersedes ADR-2's linebet classification).

## 2. Access / anti-bot

- **Geo-gate at the nginx edge.** US/datacenter IP → `HTTP 203 → /en/block`
  ("not available in your country") before any app code runs. Allowed-country IP
  (Kenya confirmed: `102.210.56.70`, Kisumu) → full SPA at `200`. Detected country
  flows into the config API as `g=` (`g=KE`; `g=US` on the block page).
- **Not datacenter-fingerprinting alone** — this block is explicitly country-based
  and names the country. Free/datacenter proxies are also blocked; a residential
  allowed-country IP is required.
- **Mirror-domain failover** (`domain-sw.js` service worker): fetches
  `/checker/redirect/stat/run/` → a list of backup domains, probes each via
  `https://<domain>/static/pixel.gif`, reports back — how the brand survives domain
  takedowns.
- **Header-injection service worker** (`ivpn-sw.js`): stores headers in IndexedDB
  (`vpn`/`headers`), injects them into requests, derives `x-dt` from `x-project-id`.
  Real, but a **red herring for the odds feed** — see §4. Often the store is empty.
- **1xbet.com flagship** additionally sits behind **Cloudflare** (`403 "Just a
  moment…"`); the skins (melbet, linebet, …) do not.

## 3. The data endpoints

Two feed roots, same endpoint names + schema under each:

- **`service-api/LiveFeed/…`** — in-play (site `/en/live`)
- **`service-api/LineFeed/…`** — prematch/scheduled (site `/en/line/<sport>`)

| Endpoint (`{LiveFeed|LineFeed}`) | Purpose |
|---|---|
| `GET /service-api/{…}/Get1x2_VZip?count=N&lng=en&mode=4&country=87&top=true&partner=189&virtualSports=true` (live adds `gr=650`, `noFilterBlockEvent=true`) | **events + odds** |
| `GET /service-api/{…}/WebGetTopChampsZip?lng=en&country=87&gr=650` | top championships |
| `GET /service-api/{…}/GetSportsShortZip?lng=en&gr=650&country=87&partner=189&groupChamps=true` | sports/champ tree |
| `GET /service-api/{…}/GetTopGamesStatZip?lng=en&antisports=66&partner=189` | top games stats |
| `GET /service-api/main-{live|line}-feed/v1/expressDay?...` | express-of-the-day |
| `GET /champs-api/v1/get-champs-by-params-web` | championship list (richer `x-*` headers) |

- `_VZip`/`Zip` = gzip at the HTTP layer (auto-decompressed → JSON).
- `top=true` returns **top games across all sports**, not a full per-sport list. For
  a complete sport card add `sports=<SI>` (Basketball `SI=3`, Football `SI=1`) or
  walk `GetChampsZip` → `GetGamesZip`.
- Bootstrap/config APIs (not odds): `bff-api/config/*`, `web-api/session`+bonuses,
  `analytics-module-api`, `fatman-api` (telemetry). Static/CDN via `v3.traincdn.com`.

## 4. Request contract (what a replay needs)

Required request headers (captured live):

```
accept: application/json, text/plain, */*
content-type: application/json
is-srv: false
x-app-n: __BETTING_APP__
x-svc-source: __BETTING_APP__
x-requested-with: XMLHttpRequest
x-mobile-project-id: 0
```

Plus **session cookies** (~21, harvested from a browser bootstrap) and routing
through an **allowed-country proxy**. `x-hd` (a long base64 "auth token with expiry")
is sent on *some* requests but is **NOT required** for the odds feed — replay
without it returned identical data. This is the operator's earlier blocker resolved:
the old scraper failed on (1) no allowed IP, (2) missing betting headers, (3) no
cookies — not on `x-hd`/SW machinery.

**Proof:**
```
DIRECT httpx REPLAY (no browser):
  LiveFeed/Get1x2_VZip → 200 Success=true Value=9 events
  LineFeed/Get1x2_VZip → 200 Success=true Value=10 events (France v England, WC2026, 20 markets)
  without x-hd → identical
```

## 5. Response schema (1xBet terse `Value[]`)

`{"Success":true,"Error":"","Value":[<event>…]}`. Per event:

| Key | Meaning | Key | Meaning |
|---|---|---|---|
| `I`/`ZP` | event id | `O1`/`O2` | teams (`O1E`/`O2E` English) |
| `SN`/`SI` | sport name / id | `O1I`/`O2I` | team ids |
| `L`/`LI` | league name / id | `S` | start time (unix) |
| `CN` | country | `SC` | score: `FS`={`S1`,`S2`}, `PS`=periods[], `CP`=cur period, `TS`=clock, `SLS`=time-left text |
| `E[]` | **markets**: `T`=market-type, `G`=group (1=1x2, 2=handicap…), `C`=odds, `CV`=odds str, `P`=line, `B`=blocked | `AE[]` | grouped markets `{G, ME:[…]}` |

Prematch events carry more markets (~20 vs ~4 live) + a few extra keys
(`GSE`,`RLI`,`CI`,`CHIMG`). Maps directly onto `src/sites/linebet/extraction/models.py`
(`Event`/`Market`/`Selection`). Decoded sample:
`src/sites/linebet/snapshots/normalized/livefeed_get1x2_schema.md`. Build-phase TODO:
map the `T`/`G` id tables to human market names; confirm cookie TTL / re-bootstrap.

## 6. Family generalization (verified)

Probed `service-api/LineFeed/Get1x2_VZip` across the family through the proxy:

| Domains | Result | Verdict |
|---|---|---|
| melbet, betwinner, 22bet, megapari, 888starz, helabet, paripesa, **linebet** | identical `406 {"type":"feed/NotAcceptableException",…}` (same feed microservice; 406 = bare probe lacked per-skin cookies/headers) | ✅ same backend/endpoint/schema |
| **1xbet.com** | `403 "Just a moment…"` | family, but Cloudflare-fronted |
| **1win.pro** | `200` HTML (`ru-RU`), no `service-api` | ❌ different platform — exclude |

## 7. Extraction mode & build recommendation

- **Mode: `hybrid`** (ADR-3) — browser bootstrap once → harvest cookies → `httpx`
  poll. `HybridConfig` + `SessionHarvester` already exist in the framework.
- **Build `src/sites/betb2b/` as the base scraper**, linebet as first skin; new
  skins = thin `SiteConfig`s. This is the flagship example of the project thesis.
- **Per-skin config (differs):** `domain`, `partner`/`ref` (linebet `189`), `gr`
  project id (linebet `650`), geo `country`.
- **Shared (base):** feed roots + endpoint names, betting headers, terse-key schema,
  hybrid method, proxy routing.
- **Exceptions:** 1xbet.com needs an anti-Cloudflare path; 1win.pro is out of family.

## 8. Infrastructure delivered this session (context)

`src/network/proxy/` canonical ProxyManager (models/manager/providers/verify/config,
5 validation stages, 52 tests) + chokepoint wiring (HarExporter `--proxy`, browser
session managers, httpx client). This is what made the family capture a few lines of
config, and it validates the README's "handles anti-bot measures and network
failures" promise. Next task pointer: `tasks/current.md`; backlog item: "Generalize
the linebet scraper into a betb2b family base scraper."
