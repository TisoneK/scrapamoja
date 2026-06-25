# FlashScore Site Implementation 🏀⚽

> **The FlashScore scraper is a reference implementation built on the Scrapamoja framework.** It demonstrates how to build a production-grade site scraper with sport-aware extraction, status-based flows, and hierarchical YAML selectors.

---

## What It Scrapes

FlashScore is a live sports data aggregator. This implementation extracts:

- **Match lists** — scheduled, live, and finished matches per sport
- **Match summaries** — teams, scores, competition, and timing
- **Match stats** — in-game statistics per tab context (summary, stats, odds, H2H)
- **Match odds** — betting odds where available
- **Head-to-head history** — past results between two teams

**Supported sports:** Basketball, Football
**Supported statuses:** Live, Finished, Scheduled

---

## Structure

```
flashscore/
├── scraper.py              # FlashscoreScraper — main scraper class
├── flow.py                 # FlashscoreFlow — page navigation logic
├── orchestrator.py         # Orchestrates full scrape sessions
├── config.py               # Site config (ID, base URL, sport definitions)
├── selector_config.py      # Selector configuration loader
├── extractors/             # Status-specific data extractors
│   ├── base_extractor.py
│   ├── live_match_extractor.py
│   ├── finished_match_extractor.py
│   ├── scheduled_match_extractor.py
│   ├── basketball_match_detail_extractor.py
│   ├── basketball_tertiary_extractor.py
│   ├── match_detail_extractor.py
│   ├── primary_tab_extractor.py
│   └── tertiary_tab_extractor.py
├── selectors/              # YAML selector definitions
│   ├── authentication/     # Cookie consent handling
│   ├── extraction/         # Data extraction selectors
│   │   ├── match_list/     # Match listing page selectors
│   │   ├── match_summary/  # Summary tab (teams, score, time)
│   │   ├── match_stats/    # Stats tab
│   │   ├── match_odds/     # Odds tab
│   │   └── match_h2h/      # Head-to-head tab
│   ├── filtering/          # Competition and date filter controls
│   │   ├── competition_filter/
│   │   └── date_filter/
│   └── navigation/         # Page navigation elements
│       ├── primary_tabs/
│       ├── secondary_tabs/
│       ├── tertiary_tabs/
│       ├── sport_selection/
│       ├── match_navigation/
│       └── event_filter/
├── models/                 # Data models for extracted content
├── html_structure/         # Captured HTML snapshots (for selector dev)
└── cli/                    # Command-line interface
    └── commands/
        ├── scrape.py
        └── validate.py
```

---

## How It Works

### Navigation Flow

The `FlashscoreFlow` class handles all page navigation:

```
Homepage → Sport selection → Status filter (live/finished/scheduled)
         → Match list → Match detail page → Tab navigation (summary/stats/odds/h2h)
```

### Selector Hierarchy

Selectors are resolved from most specific to most generic:

```
sport → status → context → element

Example: basketball → live → match_summary → home_team
```

Each element can have multiple strategies (CSS, XPath) with weights — the engine picks the highest-confidence match and falls back automatically.

### Extractor Architecture

Each match status has a dedicated extractor class that knows what data is available for that state:

- `LiveMatchExtractor` — score, current period, elapsed time
- `FinishedMatchExtractor` — final score, period breakdown
- `ScheduledMatchExtractor` — kickoff time, competition, venue

Basketball has additional extractors for tertiary tab data (quarter-by-quarter breakdowns).

### Snapshot Integration

When a selector fails, the scraper automatically captures a full snapshot — HTML, screenshot, and selector trace — correlated by session ID. Snapshots are stored via `SnapshotManager` and can be used to update YAML selectors without re-running a live scrape.

---

## Usage

```bash
# From the project root using the unified CLI
python -m src.main flashscore scrape basketball live --limit 10
python -m src.main flashscore scrape football finished -o csv -f results.csv
python -m src.main flashscore scrape basketball scheduled --no-headless --verbose

# Or using the site CLI directly
python -m src.sites.flashscore.cli.main scrape basketball live --limit 5
```

**Output formats:** `json` (default), `csv`, `xml`

---

## Selector Configuration

Selectors live in `selectors/` as YAML files. Example:

```yaml
# selectors/extraction/match_summary/basketball/home_team.yaml
description: "Home team name"
confidence_threshold: 0.8
timeout: 3.0
retry_count: 2
strategies:
  - type: "css"
    selector: ".participant__home .participant__participantName"
    weight: 1.0
  - type: "css"
    selector: ".home-team-name"
    weight: 0.9
  - type: "xpath"
    selector: "//div[@class='participant__home']//div[@class='participant__participantName']"
    weight: 0.8
metadata:
  wait_for_element: true
  tab_context: "summary"
```

When FlashScore updates their HTML, update the selector YAML — no Python changes needed.

---

## Extending

**Add a new sport:**
1. Add sport definition to `config.py`
2. Create selector subdirectories under `selectors/extraction/match_summary/<sport>/`
3. Add a sport-specific extractor if the data shape differs significantly

**Add a new data type (e.g. lineups):**
1. Add selectors under `selectors/extraction/match_lineups/`
2. Create an extractor class inheriting from `BaseExtractor`
3. Wire it into the orchestrator

---

## Troubleshooting

**Selectors failing after a FlashScore update:**
Run with `--no-headless --verbose` to see the browser live, capture the new HTML structure, and update the relevant YAML file.

**No matches returned:**
Verify the sport/status combination has active data on FlashScore at the time of scraping. Scheduled matches only appear within a certain time window.

**Timeout errors:**
Increase `browser.timeout` in your config, or reduce `--limit` to scrape fewer matches per session.
