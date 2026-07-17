# Linebet Scraper

Hybrid **browser + API interception** scraper for [linebet.com](https://linebet.com/en),
built on the Site Template Integration Framework (`BaseSiteTemplate`).

> **Why hybrid?** Linebet is a sportsbook SPA behind Cloudflare. Direct
> HTTP calls to its `/api/...` endpoints return 403 without the cookies,
> headers and TLS fingerprint a real browser carries. But parsing the
> rendered DOM is fragile — the SPA reshuffles its markup every release.
> The hybrid approach gets the best of both worlds: a real Playwright
> browser passes the anti-bot checks, and a `NetworkInterceptor`
> captures the JSON the SPA fetches from its own backend. We then
> project that JSON onto typed dataclasses — no DOM scraping required.

## Architecture

```
                ┌──────────────────────────────────────────────┐
                │              LinebetScraper                  │
                │  (extends BaseSiteTemplate)                  │
                │                                              │
                │  ┌────────────────┐    ┌─────────────────┐   │
                │  │  LinebetFlow   │    │ LinebetExtrac-  │   │
                │  │ (navigation +  │    │ tionRules       │   │
                │  │  scroll + wait)│    │ (JSON→Event)    │   │
                │  └───────┬────────┘    └────────▲────────┘   │
                │          │                      │            │
                │          ▼                      │            │
                │  ┌──────────────────────────────────────┐    │
                │  │     Playwright Page (real browser)   │    │
                │  │  ┌──────────────────────────────┐    │    │
                │  │  │  NetworkInterceptor          │    │    │
                │  │  │  patterns = API_URL_PATTERNS │    │    │
                │  │  │  handler = _on_captured_resp │    │    │
                │  │  └──────────────┬───────────────┘    │    │
                │  └─────────────────┼────────────────────┘    │
                │                    │                         │
                │                    ▼  captured JSON          │
                │  ┌──────────────────────────────────────┐    │
                │  │  List[CapturedResponse]              │────┘
                │  └──────────────────────────────────────┘
                └──────────────────────────────────────────────┘
```

| Component                          | File                              | Responsibility                                                       |
|------------------------------------|-----------------------------------|----------------------------------------------------------------------|
| `LinebetScraper`                   | `scraper.py`                      | Public entry point. Wires template + interceptor + flow + extractor. |
| `LinebetFlow`                      | `flow.py`                         | Navigation only — `goto`, scroll, consent-dismiss, settle-wait.     |
| `LinebetExtractionRules`           | `extraction/rules.py`             | Defensive JSON → `Event`/`Market`/`Selection` projection.           |
| `LinebetScrapeResult` & data models| `extraction/models.py`            | Typed output dataclasses.                                            |
| Config                             | `config.py`                       | URLs, API patterns, rate limits, stealth, feature flags.            |
| Integration bridge                 | `integration_bridge.py`           | Framework-compliance shim for registry + compliance validator.      |
| YAML selectors                     | `selectors/*.yaml`                | Minimal — hybrid mode doesn't rely on them, kept for compliance.    |

## Installation

The scraper lives inside the `scrapamoja` repo; no separate install is
needed. From the repo root:

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

### As a Python module

```python
import asyncio
from playwright.async_api import async_playwright
from src.sites.linebet import LinebetScraper
from src.selectors.engine import SelectorEngine  # framework's engine

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        engine = SelectorEngine()
        scraper = LinebetScraper(page, engine)
        await scraper.initialize(page, engine)

        # Capture prematch fixtures only
        result = await scraper.scrape(action="list_prematch")
        print(result["event_count"], "events")

        # Capture live in-play only
        live = await scraper.scrape(action="list_live")
        print(live["event_count"], "live events")

        # Raw capture — skip extractor, keep JSON for offline analysis
        raw = await scraper.scrape(action="raw_capture")
        for cap in raw["captured_responses"]:
            print(cap["url"], cap["body_bytes"], "bytes")

        await browser.close()

asyncio.run(main())
```

### Actions

| Action           | What it does                                                                  |
|------------------|-------------------------------------------------------------------------------|
| `list_prematch`  | Navigate to `/en`, scroll the fixtures list, harvest every `/api/list/...`.   |
| `list_live`      | Navigate to `/en/live`, harvest every `/api/live/...`.                        |
| `list_all`       | Do both in one scrape. De-duplicates events that appear in both endpoints.    |
| `raw_capture`    | Capture only — no extractor. Useful for debugging API drift.                  |

### Output shape

`scrape()` returns a dict (see `LinebetScrapeResult.to_dict()`):

```json
{
  "action": "list_prematch",
  "url": "https://linebet.com/en",
  "events": [
    {
      "event_id": "ev-1001",
      "sport": "Football",
      "competition": "Premier League",
      "home": "Arsenal",
      "away": "Chelsea",
      "start_time": "2025-01-01T00:00:00+00:00",
      "status": "not_started",
      "is_live": false,
      "markets": [
        {
          "name": "Match Result",
          "market_type": "1x2",
          "selections": [
            {"name": "1", "price": 1.85, "line": null, "is_suspended": false},
            {"name": "X", "price": 3.40, "line": null, "is_suspended": false},
            {"name": "2", "price": 4.20, "line": null, "is_suspended": false}
          ]
        }
      ]
    }
  ],
  "captured_responses": [...],
  "scrape_duration_seconds": 14.32,
  "extracted_at": "2026-07-17T12:34:56+00:00",
  "extraction_source": "linebet_scraper",
  "template_version": "1.0.0",
  "error": null,
  "success": true,
  "event_count": 1,
  "captured_response_count": 7
}
```

## Configuration knobs

All in `config.py`:

| Constant                          | Default                                 | Effect                                                |
|-----------------------------------|-----------------------------------------|-------------------------------------------------------|
| `API_URL_PATTERNS`                | `["https://linebet.com/api/", …]`       | URLs the interceptor matches. Broad by design.        |
| `DEFAULT_API_SETTLE_SECONDS`      | `12.0`                                  | How long to wait for the SPA's API burst after DCL.   |
| `DEFAULT_SCRAPE_TIMEOUT_SECONDS`  | `60.0`                                  | Hard cap on a single `scrape()` call.                 |
| `MAX_CAPTURED_RESPONSES`          | `200`                                   | In-memory cap; further matches are dropped + logged.  |
| `RATE_LIMIT_REQUESTS_PER_MINUTE`  | `6`                                     | Politeness cap on scrape invocations.                 |
| `STEALTH_USER_AGENT` / `VIEWPORT` | Chrome 124 / 1536×864                    | Matches a real desktop profile.                       |

## Testing

```bash
pytest src/sites/linebet/tests/ -v
```

Tests run without a browser or network — they exercise the extractor
against synthetic JSON payloads that mimic Linebet's API shapes, plus
the scraper's plumbing with a mocked `NetworkInterceptor`.

## Limitations & known issues

- **Schema drift.** Linebet ships backend changes without notice. The
  extractor is defensive (`_get_first` over multiple key aliases,
  best-effort shape heuristics) so it degrades to "fewer events" rather
  than crashing, but if extraction ever returns 0 events for a scrape
  that captured N responses, run `action="raw_capture"` and inspect the
  JSON to find the new field names.
- **Live long-poll.** Linebet keeps an open long-poll for live odds,
  so `wait_until="networkidle"` would hang. We use `domcontentloaded`
  + a fixed settle window instead.
- **No replay mode yet.** `ENABLE_REPLAY_MODE` is plumbed but the
  httpx-based replay path (re-issue captured requests with forwarded
  cookies/headers) is not yet implemented. Build it when there's a
  concrete need for sub-second polling.
- **Cloudflare challenges.** If Linebet's challenge mode escalates
  (e.g. interactive CAPTCHA), the headless browser will fail. The
  fix is to swap `BROWSER_HEADLESS = False` and let a human solve it
  once, then reuse the persisted session — see
  `docs/proposals/browser_api_hybrid/FEATURE_09_PERSISTENT_BROWSER_PROFILE.md`.
