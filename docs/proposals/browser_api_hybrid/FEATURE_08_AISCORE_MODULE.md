# Feature Proposal: AiScore Site Module
**Project:** Scrapamoja  
**Feature ID:** SCR-008  
**Status:** Proposed  
**Author:** TisoneK  
**Date:** March 2026  

---

## 1. Summary

Build a fully working Scrapamoja site module for `m.aiscore.com` — a Cloudflare-protected sports SPA powered by TheSports data — that extracts upcoming basketball fixtures, league information, team names, match IDs, and betting odds markets including **Total Points (Over/Under) lines**. This module is the primary data source for the **ScoreWise** basketball prediction algorithm.

---

## 2. Problem

ScoreWise needs structured basketball data — specifically upcoming game fixtures paired with their Total Points odds — to generate predictions. AiScore displays exactly this data for hundreds of leagues worldwide, sourced from TheSports, one of the leading sports data providers.

However, AiScore presents three technical barriers that prevent standard data access:

1. **Cloudflare bot protection** blocks all direct HTTP requests with a 403 error
2. **SPA architecture** means the page HTML contains no data — everything is fetched dynamically
3. **Protobuf binary encoding** means the API responses are not JSON — they are binary data requiring specialised decoding

No existing Scrapamoja module addresses any of these challenges. A new, purpose-built AiScore module is required.

---

## 3. What AiScore Offers

AiScore (`m.aiscore.com`) provides:

- **Upcoming fixtures** across 1,300+ basketball leagues worldwide
- **Live scores** for in-progress games
- **Odds markets** per match including:
  - Moneyline (To Win)
  - Spread (ATS)
  - **Total Points (Over/Under)** — the primary market for ScoreWise
- **League and team metadata** including names, countries, and identifiers
- **Historical match data** accessible via date parameters

All data is sourced from TheSports — the same provider powering major sports media and betting platforms globally.

---

## 4. What This Module Adds

- A complete `src/sites/aiscore/` module following Scrapamoja's existing site module architecture
- **Fixture extraction** — upcoming basketball games with home team, away team, league, and match ID
- **Odds extraction** — Total Points line and Over/Under odds for each fixture
- **League filtering** — ability to filter by specific leagues (NBA, EuroLeague, KBL, etc.)
- **Date and timezone configuration** — extract fixtures for any date in any timezone
- **CLI support** — consistent with the FlashScore module interface:
  ```
  python -m src.sites.aiscore.cli.main scrape basketball scheduled --date 20260310
  ```
- **JSON and CSV output** — structured data ready for ScoreWise ingestion
- A **protobuf field map** documenting the discovered AiScore binary schema for maintainability

---

## 5. Target Data Output

For each upcoming basketball fixture, the module will return:

| Field | Example |
|---|---|
| match_id | `ndkzysn0wrgfx73` |
| league | National Basketball Association |
| home_team | Cleveland Cavaliers |
| away_team | Philadelphia 76ers |
| date | 2026-03-10 |
| tip_off_time | 19:00 |
| total_line | 225.5 |
| over_odds | 0.91 |
| under_odds | 0.91 |
| spread_line | 10.5 |
| moneyline_home | 1.20 |
| moneyline_away | 4.75 |

---

## 6. Technical Approach

The module will use the **Network Intercept** extraction mode:

1. Playwright navigates to `m.aiscore.com/basketball`
2. Cloudflare challenge passes automatically
3. Network listener captures the matches API response:
   ```
   GET api.aiscore.com/v1/m/api/matches?lang=2&sport_id=2&date=YYYYMMDD&tz=TZ
   ```
4. Protobuf binary response is decoded using string extraction and numeric pattern matching
5. Structured match and odds data is returned

For high-frequency use (ScoreWise polling), the module will support **Session Bootstrap mode** — bootstrapping a session once and reusing credentials for subsequent direct API calls.

---

## 7. Why This Module Matters Beyond ScoreWise

This module is the **first real-world proof of Scrapamoja's new capabilities**. It validates:

- Cloudflare bypass works in production
- Network interception captures live API responses reliably
- Protobuf decoding produces usable structured data
- The full extraction pipeline functions end-to-end on a major, production-grade protected site

Every new capability built for this module becomes immediately reusable for any future Scrapamoja site module targeting similar infrastructure.

---

## 8. Discovery Context

The entire AiScore investigation was conducted in a single session:

- Identified AiScore as the consumer-facing product of TheSports data
- Discovered `m.aiscore.com` as the mobile-only SPA
- Reverse-engineered the internal API endpoint from browser DevTools network tab
- Confirmed Cloudflare protection via 403 response to direct HTTP
- Confirmed protobuf encoding via hex dump analysis
- Confirmed data accessibility via Playwright network interception
- Extracted team names, league names, match IDs, and odds numeric sequences from binary

The data is confirmed to be present and accessible. This module formalises that extraction into a production-grade, maintainable implementation.

---

## 9. Success Criteria

- The module returns upcoming basketball fixtures for a specified date without manual intervention
- Total Points (Over/Under) line and odds are present for each fixture that has odds available
- NBA fixtures are correctly identified and separated from other leagues
- Output is valid JSON and CSV, correctly structured for ScoreWise ingestion
- The module runs reliably on repeated executions without session or bot detection failures
- CLI interface matches the pattern established by the FlashScore module
- A protobuf field map document is included in the module for future maintainers

---

## 10. Out of Scope

- Live score updates during games (future extension)
- Player-level statistics (future extension)
- Historical odds data retrieval (future extension)
- Other sports beyond basketball (future extension following the same module pattern)

---

*Proposal prepared March 2026.*
