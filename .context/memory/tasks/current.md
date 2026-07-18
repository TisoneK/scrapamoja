# Current Task (overwrite each session)

**NEXT: build `src/sites/betb2b/` base scraper** (Session 11 ended here, 2026-07-18).
linebet is fully reverse-engineered and is one skin of the BetB2B/1xbet family —
the recon generalizes to ~9 bookmakers. Full details: `src/sites/linebet/RECON.md`
(READ THIS FIRST) + ADR-2/ADR-3 in `plans/decisions.md`.

## What to build
A `betb2b` base scraper, `extraction_mode=hybrid` (ADR-3): browser bootstrap once
through an allowed-country proxy to harvest ~21 session cookies (framework
`HybridConfig` + `SessionHarvester` already exist), then `httpx`-poll the feeds.
linebet = first skin; melbet/betwinner/etc = thin per-skin SiteConfig.

- **Feeds** (host `<domain>`, all `service-api`):
  - in-play: `GET /service-api/LiveFeed/Get1x2_VZip?count=N&lng=en&gr=650&mode=4&country=87&top=true&partner=189&virtualSports=true`
  - prematch: `GET /service-api/LineFeed/Get1x2_VZip?...` (same names, `LineFeed` root)
  - siblings: `WebGetTopChampsZip`, `GetSportsShortZip`, `GetTopGamesStatZip`, `main-{live,line}-feed/v1`
  - `top=true` = top games across sports; for a full per-sport list add `sports=<SI>` (Basketball=3, Football=1) / walk `GetChampsZip`→`GetGamesZip`.
- **Required headers**: `is-srv:false`, `x-app-n:__BETTING_APP__`, `x-svc-source:__BETTING_APP__`, `x-requested-with:XMLHttpRequest` + cookies + allowed-country proxy. `x-hd`/IndexedDB/service-worker = NOT needed for odds (red herring).
- **Schema** (terse `Value[]`): `I`/`ZP`=id, `O1`/`O2`=teams, `SN`/`SI`=sport, `L`/`LI`=league, `S`=start ts, `SC`=score(`FS`{S1,S2},`PS`,`TS`), markets `E[]`/`AE[].ME[]`: `T`=type,`G`=group(1=1x2,2=handicap),`C`=odds,`P`=line,`B`=blocked. Sample: `snapshots/normalized/livefeed_get1x2_schema.md`. Maps to existing `extraction/models.py` Event/Market/Selection.
- **Per-skin config**: `domain`, `partner`/`ref` (linebet=189), `gr` (linebet=650), `country`. Shared: everything else.
- **Exclusions**: 1xbet.com = Cloudflare (needs anti-CF); 1win.pro = different platform.

## Proxy (must be live to test)
Operator runs `gost -L "http://USER:PASS@:8080"` (Kenya) + `bore.exe local 8080 --to bore.pub` → sends `bore.pub:<port>` + creds. Then:
`build_proxy_manager({"endpoints":[{"id":"kenya","url":"http://USER:PASS@bore.pub:<port>","country":"KE","source":"ngrok"}],"routing":[{"pattern":"*linebet.com","target":"kenya"}]})`. `verify_proxy` should show countryCode KE. bore port changes each run; ngrok/pinggy don't work (TCP gated).

## Done this session (all pushed to main)
Proxy abstraction `src/network/proxy/` (5 stages, 52 tests) + chokepoint wiring
(HarExporter/browser/httpx) + linebet full recon (live+prematch feeds, headers,
schema, httpx-replay PROVEN) + BetB2B family generalization verified. See
`agents/sessions.md` Session 11 (+ continuation) and the backlog "Generalize the
linebet scraper into a betb2b family base scraper" item.
