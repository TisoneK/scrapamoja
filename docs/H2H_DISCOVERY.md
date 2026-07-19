# H2H (Head-to-Head) Endpoint Discovery

**Date:** 2026-07-19
**Target:** Linebet.com (BetB2B platform) — NBA Summer League (scheduled match)
**Skin tested:** `linebet`
**Agent:** Local IDE (Playwright async_api, Python 3.12+)
**Status:** ✅ SOLVED — endpoint identified and captured

---

## Executive Summary

After multiple failed attempts using live/in-play matches (where H2H data is **not**
pre-loaded and appears to be SW-mediated), the head-to-head endpoint was finally
discovered by using a **scheduled pre-match event from a major league** (NBA Summer
League: Oklahoma City Thunder vs Brooklyn Nets).

**Key insight that unlocked the discovery:** Scheduled matches from major leagues
pre-load H2H data at bootstrap time as a standard XHR, visible to Playwright's
`page.on("response")`. Live matches may use a different (SW-mediated) path.

---

## The Endpoint

```
GET /service-api/statisticfeed/api/v1/Game/h2h?id={gameId}&lng=en&ref=189&fcountry=87&gr=650
```

**Full URL (example):**
```
https://linebet.com/service-api/statisticfeed/api/v1/Game/h2h?id=737455106&lng=en&ref=189&fcountry=87&gr=650
```

### Parameters

| Parameter | Example Value | Description | Source |
|-----------|---------------|-------------|--------|
| `id` | `737455106` | Internal game ID for H2H lookup | NOT the URL event ID (e.g. `352015844`). Found in `GetGameZip` response or `GetSubsOptionsForGame` |
| `lng` | `en` | Language | Fixed |
| `ref` | `189` | Partner/affiliate ID | Skin config |
| `fcountry` | `87` | Country filter | From location detection |
| `gr` | `650` | Project/group ID (linebet) | Skin config |

### Cross-skin parameter variations

The `ref`, `fcountry`, and `gr` query params are sourced from each skin's YAML config
(`partner`, `country`, `gr` fields respectively). Different bookmakers use different values:

| Skin | Domain | `ref` (partner) | `gr` | `fcountry` |
|------|--------|-----------------|------|------------|
| 22bet | 22bet.com | 1 | 1 | 87 |
| 888starz | 888starz.bet | 1 | 1 | 87 |
| betwinner | betwinner.com | 1 | 1 | 87 |
| helabet | helabet.com | 1 | 1 | 87 |
| **linebet** | linebet.com | **189** | **650** | 87 |
| megapari | megapari.com | 1 | 1 | 87 |
| **melbet** | melbet.com | **61** | **6** | 87 |
| paripesa | paripesa.bet | 1 | 1 | 87 |

All skins share country=87 (Kenya). The `fcountry` may differ for skins in other
jurisdictions. The endpoint path is universal across all BetB2B skins since they
share the same backend infrastructure.

### Headers (for httpx replay)

```python
headers = {
    "is-srv": "false",
    "x-app-n": "__BETTING_APP__",
    "x-svc-source": "__BETTING_APP__",
    "x-requested-with": "XMLHttpRequest",
    "x-mobile-project-id": "0",
    "Referer": "https://linebet.com/",
}
```

Same base betting headers as other `service-api` endpoints. **Session cookies are
required** (harvested from browser bootstrap).

---

## Full Response (NBA Summer League example)

```json
{
  "teams": [
    {
      "id": "5ab1265c494765f3ca240306",
      "countryId": "153",
      "title": "Brooklyn Nets",
      "subTeams": [{"title": "Brooklyn Nets", "image": "/sfiles/logo_teams/..."}],
      "teamType": 1,
      "clId": 6852,
      "image": "/sfiles/logo_teams/...",
      "country": {"id": 153, "title": "United States", "logoId": 12753, "image": "..."}
    },
    {
      "id": "5ab1265c494765f3ca240317",
      "title": "Oklahoma City Thunder",
      ...
    }
    // 12 teams total (all NBA teams referenced in gameShorts)
  ],
  "gameShorts": [
    {
      "id": "6865cd0d9930a40b3ceaeffb",
      "stageId": "68659e8b9930a40b3cb0bfd6",
      "team1": "5ab1265c494765f3ca240306",   // references teams[].id
      "team2": "5ab1265c494765f3ca240317",
      "dateStart": 1752183000,                // Unix timestamp (UTC)
      "score1": 81,
      "score2": 90,
      "subScore1": 0,
      "subScore2": 0,
      "countRedCards1": 0,
      "countRedCards2": 0,
      "winner": 2,                            // 1=team1, 2=team2, 0=draw/tie
      "status": 3,                             // 3=finished
      "subStatus": 0,
      "periods": [
        {"score1": 15, "score2": 22, "type": 18},
        {"score1": 22, "score2": 22, "type": 19},
        {"score1": 21, "score2": 23, "type": 20},
        {"score1": 23, "score2": 23, "type": 21}
      ]
    }
    // 19 gameShorts entries returned
  ],
  "sportId": 3,
  "subSportId": null,
  "entity": "68659e8b9930a40b3cb0bfd6"
}
```

### Period type mapping (basketball)

| `type` value | Meaning |
|--------------|---------|
| 18 | 1st Quarter |
| 19 | 2nd Quarter |
| 20 | 3rd Quarter |
| 21 | 4th Quarter |

> **Note for other sports:** Football (soccer) likely uses different period type
> values (e.g., 1 = 1st Half, 2 = 2nd Half). These need to be mapped per-sport.

---

## How the H2H Data Appears in the UI

1. User navigates to a **scheduled** match page (e.g., `/en/line/basketball/...`)
2. At bootstrap, the SPA fires the `/statisticfeed/api/v1/Game/h2h` XHR
3. The H2H data is stored in Vue component state (invisible in DOM)
4. When user **hovers over a team name** (`.scoreboard-team-name`), a popup appears
5. The popup has two tabs: **"Recent Games"** and **"Previous meetings"**
6. The popup shows 5-10 recent games for that specific team (filtered from the full response)
7. Each game shows: date, opponent, final score, and per-period breakdown

**UI selectors:**
- Team name: `.scoreboard-team-name` or `.scoreboard-team-name__text`
- H2H popup container: `.scoreboard-team-info__content`
- Popup tab: contains text "Recent Games" / "Previous meetings"

---

## Discovery Methodology (step-by-step)

### Prerequisites
- Python 3.12+ with `playwright` installed
- Access to linebet.com from an allowed country (Kenya works without proxy)

### Script approach

```python
# Pseudo-code for the discovery approach

async def discover_h2h():
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()

    responses = []
    page.on("response", lambda r: asyncio.create_task(capture(r)))

    # STEP 1: Navigate to a scheduled (pre-match) major league match
    #         CRITICAL: Use /en/line/ NOT /en/live/
    await page.goto(
        "https://linebet.com/en/line/basketball/75093-nba-summer-league/"
        "352015844-oklahoma-city-thunder-brooklyn-nets",
        wait_until="load"
    )

    # STEP 2: Wait for SPA hydration (20-25 seconds)
    await asyncio.sleep(25)

    # STEP 3: Hover over team names to reveal H2H popup
    team_elements = await page.query_selector_all(".scoreboard-team-name")
    for el in team_elements:
        await el.hover(force=True)
        await asyncio.sleep(2)

    # STEP 4: Find the H2H endpoint in captured responses
    h2h_responses = [r for r in responses if "/h2h" in r.url]
```

### Critical success factors
1. **Scheduled match** — Must use `/en/line/` (pre-match), NOT `/en/live/` (in-play)
2. **Major league** — NBA, EPL, La Liga, etc. Minor leagues return empty `gameShorts[]`
3. **Long wait** — 20-25 seconds for the microfrontend SPA to hydrate
4. **`wait_until="load"`** — NOT `domcontentloaded`. The betting app scripts load asynchronously
5. **Response capture set up BEFORE navigation** — Missing the bootstrap requests is irreversible

---

## Previous Incorrect Assumptions (Corrected)

| Old Assumption | Correction |
|---------------|------------|
| H2H is SW-mediated and invisible to Playwright | **FALSE** — visible via `page.on("response")` for scheduled matches |
| H2H fires only on hover | **FALSE** — data is pre-loaded at bootstrap, hover only shows UI popup |
| `GetSportsShortZip` might carry H2H data | **FALSE** — it's the sports sidebar tree menu |
| Need CDP `Target.setAutoAttach` to capture H2H | **FALSE** — standard XHR, no CDP needed |
| Live matches have H2H data | **PARTIALLY FALSE** — live matches may use different (SW) transport or skip H2H entirely |

---

## Integration into Scraper

The H2H endpoint should be integrated as an **optional parallel fetch** during
match page scraping:

1. **When:** During `GetGameZip` call (same bootstrap phase)
2. **How:** Extract the `id` parameter from `GetGameZip` response or
   `GetSubsOptionsForGame` response, then call `/statisticfeed/api/v1/Game/h2h`
3. **Parsing:** Map `teams[]` by ID, then parse `gameShorts[]` into historical
   match records with opponent names, scores, periods, and winner
4. **Storage:** Attach H2H data to the `Event` or `BetB2BScrapeResult` model
5. **Scope:** Per-match detail endpoint (not list-level). Call when scraping a
   single match page with `include_h2h=True`

### Example httpx implementation

```python
async def fetch_h2h(
    client: httpx.AsyncClient,
    base_url: str,
    game_id: str,
    skin: BetB2BSkinConfig,
) -> dict | None:
    """Fetch H2H historical match data."""
    params = {
        "id": game_id,
        "lng": "en",
        "ref": skin.partner_id,      # e.g., 189
        "fcountry": skin.country_id,  # e.g., 87
        "gr": skin.group_id,          # e.g., 650
    }
    headers = {
        "is-srv": "false",
        "x-app-n": "__BETTING_APP__",
        "x-svc-source": "__BETTING_APP__",
        "x-requested-with": "XMLHttpRequest",
        "Referer": f"{base_url}/",
    }
    url = f"{base_url}/service-api/statisticfeed/api/v1/Game/h2h"
    resp = await client.get(url, params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()
```

---

## References

- **RECON.md:** `src/sites/linebet/RECON.md` (updated 2026-07-19 with SOLVED section)
- **Discovery script:** `src/sites/betb2b/scripts/discover_h2h.py`
- **Captured data:** `betb2b_h2h_discovery/h2h_discovery.json`
- **Match page HTML:** `betb2b_h2h_discovery/match_page_full.html`
- **Screenshots:** `betb2b_h2h_discovery/01_match_page.png`, `02_after_hover.png`
