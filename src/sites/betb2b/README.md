# BetB2B Family Scraper

A **single parameterized scraper** for the entire BetB2B / 1xbet platform
family — linebet, melbet, betwinner, 22bet, megapari, 888starz, helabet,
paripesa, … — with per-skin config in YAML.

> This is the flagship example of Scrapamoja's "one framework, many sites"
> thesis. linebet was reverse-engineered first (`src/sites/linebet/RECON.md`);
> the findings generalize across 8+ family members (verified 2026-07-18 via
> the Kenya proxy). ADR-3 in `.context/memory/plans/decisions.md` records
> the extraction-mode decision (`hybrid`).

## Why a family scraper?

The BetB2B platform is shared infrastructure — every skin hits the same
backend, the same `/service-api/{LiveFeed,LineFeed}/…` endpoints, the same
terse-key `Value[]` schema, the same base betting headers
(`is-srv`, `x-app-n`, `x-svc-source`, `x-requested-with`). What differs
per skin is small:

| Per-skin field   | linebet example | Meaning                                     |
|------------------|-----------------|---------------------------------------------|
| `domain`         | `linebet.com`   | bare hostname                               |
| `partner` / `ref`| `189`           | affiliate / brand id (`partner=` query)     |
| `gr`             | `650`           | project-group id (`gr=` query)              |
| `country`        | `87`            | internal BetB2B country id (`country=`)     |
| `geo`            | `KE`            | ISO country for proxy routing               |

Everything else is family-shared.

## Architecture

```
              ┌──────────────────────────────────────────────────┐
              │                BetB2BScraper                     │
              │         (parameterised by BetB2BSkinConfig)      │
              │                                                  │
              │  ┌──────────────────┐   ┌──────────────────┐    │
              │  │ BetB2BSession    │   │ BetB2BFeedClient │    │
              │  │ Manager          │   │ (httpx)          │    │
              │  │                  │   │                  │    │
              │  │ 1. Playwright    │   │ polls            │    │
              │  │    bootstrap     │──▶│ /service-api/    │    │
              │  │    via proxy     │   │  {LiveFeed,      │    │
              │  │ 2. SessionHarvest│   │   LineFeed}/…    │    │
              │  │    ~21 cookies   │   │  through proxy   │    │
              │  └──────────────────┘   └─────────┬────────┘    │
              │                                   │             │
              │                                   ▼             │
              │                         ┌──────────────────┐    │
              │                         │ BetB2BExtraction │    │
              │                         │ Rules            │    │
              │                         │ (terse → Event)  │    │
              │                         └──────────────────┘    │
              └──────────────────────────────────────────────────┘
```

| Component             | File                          | Responsibility                                                       |
|-----------------------|-------------------------------|----------------------------------------------------------------------|
| `BetB2BScraper`       | `scraper.py`                  | Public entry point. Wires session + client + extractor.             |
| `BetB2BSkinConfig`    | `config.py`                   | Per-skin config (every URL/header/param/id-map).                    |
| `BetB2BSessionManager`| `session.py`                  | Browser bootstrap → cookie harvest (caches + TTL refresh).          |
| `BetB2BFeedClient`    | `client.py`                   | httpx poller for the `LiveFeed`/`LineFeed` endpoints.               |
| `BetB2BExtractionRules`| `extraction/rules.py`        | Defensive 1xbet terse `Value[]` JSON → `Event`/`Market`/`Selection`.|
| Market/sport maps     | `markets.py`, `sports.py`     | `G`/`T`/`SI` id tables. Overridable per skin.                       |
| Per-skin YAML         | `skins/<name>.yaml`           | Identity + per-skin overrides.                                       |
| CLI                   | `cli/main.py`                 | `scrape` / `info` / `skins` / `probe` subcommands.                  |
| Live test script      | `scripts/validate_live.py`    | End-to-end probe → harvest → poll → extract → persist.              |
| Family probe script   | `scripts/probe_family.py`     | Verify the family-generalization signal across skins.               |

## Extraction mode: `hybrid` (ADR-3)

The recipe is browser bootstrap once → httpx polling:

1. **Browser bootstrap** (one Playwright Chromium launch through the
   allowed-country proxy): navigate to `https://<domain>/en`, dismiss
   the consent banner, wait for the SPA's API burst to settle, harvest
   ~21 session cookies via the framework's
   `SessionHarvester` (`src/network/session.py`).
2. **httpx polling** (sub-second, no browser per poll): the
   `BetB2BFeedClient` reuses the harvested cookies + base betting
   headers (`is-srv:false`, `x-app-n:__BETTING_APP__`,
   `x-svc-source:__BETTING_APP__`, `x-requested-with:XMLHttpRequest`)
   to GET `/service-api/{LiveFeed,LineFeed}/Get1x2_VZip?…`.
3. **Extraction**: the `BetB2BExtractionRules` project the terse-key
   `Value[]` JSON onto `Event`/`Market`/`Selection` dataclasses.

Re-bootstrap is automatic: the `SessionValidator` watches for the
session TTL (default 2h) and for auth-error HTTP statuses (401/403/419/
440); on either signal, the next `get_session()` call re-bootstraps.

## Quick start

```bash
# 1. Install deps (only needed once).
pip install -r requirements.txt
playwright install chromium

# 2. Configure the proxy via env vars (no secrets in CLI args).
export BETB2B_PROXY_URL=http://bore.pub:1074
export BETB2B_PROXY_USER=TisoneK
export BETB2B_PROXY_PASS=Taalib01
export BETB2B_PROXY_COUNTRY=KE
export BETB2B_PROXY_ID=kenya

# 3. List the shipped skins.
python -m src.sites.betb2b.cli skins

# 4. Inspect a skin's rendered feed URLs + config.
python -m src.sites.betb2b.cli info --skin linebet

# 5. Connectivity probe (bootstrap → harvest cookies; no feed polling).
python -m src.sites.betb2b.cli probe --skin linebet

# 6. Live scrape — in-play events.
python -m src.sites.betb2b.cli scrape --skin linebet --action list_live --pretty

# 7. Live scrape — prematch + live, filter to basketball (SI=3).
python -m src.sites.betb2b.cli scrape --skin linebet --action list_all \
    --sport-id 3 --pretty
```

## End-to-end validation script

The standalone `scripts/validate_live.py` runs the full pipeline and
persists every capture for offline replay:

```bash
export BETB2B_PROXY_URL=http://bore.pub:1074
export BETB2B_PROXY_USER=TisoneK
export BETB2B_PROXY_PASS=Taalib01
export BETB2B_PROXY_COUNTRY=KE
export BETB2B_PROXY_ID=kenya

python -m src.sites.betb2b.scripts.validate_live --skin linebet
# → /home/z/my-project/download/betb2b_validate_linebet/
#     ├── summary.json
#     └── captured/
#         ├── list_live_captures.json
#         ├── list_live_events.json
#         ├── list_prematch_captures.json
#         └── list_prematch_events.json
```

## Customizing — adding a new skin

Drop a YAML file in `src/sites/betb2b/skins/<name>.yaml`. Every field
is optional except `name` and `domain` — omitted fields fall back to
the family defaults (`DEFAULT_SKIN_CONFIG` in `config.py`).

```yaml
# skins/mybookmaker.yaml
name: mybookmaker
domain: mybookmaker.com
partner: 555
gr: 42
country: 87
geo: KE
language: en
enabled: true
proxy_endpoint_id: kenya
allowed_countries: ["KE"]
notes: |
  MyBookmaker skin — confirmed same-backend 2026-XX-XX.
```

Then:

```bash
python -m src.sites.betb2b.cli scrape --skin mybookmaker --action list_live
```

### Overriding the deep defaults

Beyond the identity fields, every feed URL / header / query param /
market-id / sport-id mapping is overridable. Example — a skin that
uses a different `partner` value AND a custom sport-id table:

```yaml
name: customskin
domain: custom.com
partner: 999
gr: 100
country: 87
geo: KE
sport_map:
  3:
    si_id: 3
    name: "Hoops"   # localised sport name
market_groups:
  999:
    g_id: 999
    name: "custom_market"
```

## Actions

| Action           | What it does                                                          |
|------------------|-----------------------------------------------------------------------|
| `list_live`      | Poll `LiveFeed/Get1x2_VZip` — in-play events + odds.                  |
| `list_prematch`  | Poll `LineFeed/Get1x2_VZip` — prematch/scheduled events + odds.       |
| `list_all`       | Poll both roots in one scrape. De-duplicates by `event_id`.           |
| `raw_capture`    | Capture only — no extraction. Useful for debugging feed drift.        |
| `sports_short`   | Poll `GetSportsShortZip` — the sport/championship tree.               |
| `top_champs`     | Poll `WebGetTopChampsZip` — the top-championships list.               |

## Output shape

`scrape()` returns a dict (see `BetB2BScrapeResult.to_dict()`):

```json
{
  "skin": "linebet",
  "action": "list_live",
  "url": "https://linebet.com/service-api/LiveFeed/Get1x2_VZip?...",
  "events": [
    {
      "event_id": "737248980",
      "sport": "Basketball",
      "competition": "NBA. Summer League",
      "home": "Minnesota Timberwolves",
      "away": "Los Angeles Clippers",
      "start_time": "2026-07-14T20:45:00+00:00",
      "status": "live",
      "score_home": 118,
      "score_away": 126,
      "period": "1 Overtime",
      "time_remaining": "2 min remaining",
      "is_live": true,
      "country": "United States",
      "markets": [
        {
          "name": "Asian Handicap",
          "market_type": "handicap",
          "selections": [
            {"name": "W2 (-7.5)", "price": 1.98, "line": -7.5, "is_suspended": true},
            {"name": "W1 (+7.5)", "price": 1.825, "line": 7.5, "is_suspended": true}
          ],
          "is_live": true,
          "is_suspended": true,
          "raw_g": 2
        }
      ],
      "source_url": "https://linebet.com/service-api/LiveFeed/Get1x2_VZip?...",
      "raw_endpoint": "https://linebet.com/service-api/LiveFeed/Get1x2_VZip?...",
      "sport_id": 3,
      "league_id": 75093
    }
  ],
  "captured_responses": [...],
  "scrape_duration_seconds": 14.32,
  "session_harvested": true,
  "extracted_at": "2026-07-18T12:34:56+00:00",
  "extraction_source": "betb2b_scraper",
  "template_version": "1.0.0",
  "error": null,
  "success": true,
  "event_count": 1,
  "captured_response_count": 1
}
```

## Schema map (1xbet terse `Value[]`)

| Key          | Meaning                                  | Maps to                      |
|--------------|------------------------------------------|------------------------------|
| `I` / `ZP`   | event id                                 | `Event.event_id`             |
| `O1` / `O2`  | team names (`O1E`/`O2E` = English)       | `Event.home` / `Event.away`  |
| `SN` / `SI`  | sport name / id                          | `Event.sport` / `sport_id`   |
| `L` / `LI`   | league name / id                         | `Event.competition` / `league_id` |
| `S`          | start time (unix)                        | `Event.start_time`           |
| `CN`         | country                                  | `Event.country`              |
| `SC.FS.S1/S2`| full score                               | `Event.score_home/away`      |
| `SC.CP/CPS`  | current period (int/name)                | `Event.period`               |
| `SC.SLS`     | time-remaining text                      | `Event.time_remaining`       |
| `E[]`        | flat markets: `T`=type, `G`=group, `C`=odds, `P`=line, `B`=blocked | `Event.markets` |
| `AE[]`       | grouped markets: `{G, ME:[…same as E]}`  | `Event.markets` (preferred)  |

Market-id tables (`G` → group, `T` → type within group) live in
`markets.py`. Sport-id table (`SI` → name) in `sports.py`. Both are
family-shared defaults; per-skin YAML can extend/override.

## Testing

```bash
# Unit tests (no browser, no network).
pytest src/sites/betb2b/tests/ -v

# Live end-to-end (needs the proxy env vars above).
python -m src.sites.betb2b.scripts.validate_live --skin linebet

# Family generalization probe (hit every candidate domain through the proxy).
python -m src.sites.betb2b.scripts.probe_family
```

## Limitations & known issues

- **Schema drift.** The BetB2B backend ships changes without notice.
  The extractor is defensive (multi-key lookups + shape heuristics) so
  it degrades to "fewer events / fewer markets" rather than crashing.
  If extraction returns 0 events for a scrape that captured N
  responses, run `action="raw_capture"` and inspect the JSON to find
  the new field names.
- **Geo-block.** All BetB2B skins geo-block at the nginx edge
  (`HTTP 203 → /en/block` from disallowed countries). A proxy is
  **optional** — if your egress IP is already in an allowed country
  (e.g. running from Kenya for a KE skin), the scraper works fine
  in direct mode (`proxy_manager=None`). Set `BETB2B_PROXY_URL` and
  related env vars only when your egress country is blocked.
- **1xbet.com is Cloudflare-fronted.** The flagship domain sits
  behind a `403 "Just a moment…"` challenge the skins don't. A
  1xbet.com skin is shipped disabled by default — needs anti-CF
  handling (out of scope for this build).
- **1win.pro is a different platform.** Not in the BetB2B family
  (200 HTML, no `service-api` feed). Excluded from the shipped skins.
- **Cookie TTL.** Default re-bootstrap cadence is 2 hours. If you see
  a run of `406 feed/NotAcceptableException` from a previously-working
  session, the cookies likely expired — `BetB2BSessionManager` will
  auto-re-bootstrap on the next auth-error status, but you can force
  it with `session_manager.clear()`.

## See also

- `src/sites/linebet/RECON.md` — the full reverse-engineering writeup.
- `.context/memory/plans/decisions.md` ADR-2 + ADR-3 — extraction-mode
  decision + the linebet-specific classification.
- `src/network/proxy/` — the canonical ProxyManager / ProxyEndpoint
  layer this scraper wires into.
- `src/network/session.py` — the `SessionHarvester` /
  `SessionValidator` used by `BetB2BSessionManager`.
