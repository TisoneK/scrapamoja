# Sites

This directory contains all site implementations built on the Scrapamoja framework. Each site is a self-contained scraper that follows a shared contract — making it possible to add new sites without touching any core framework code.

---

## Available Sites

| Site | Description | Docs |
|------|-------------|------|
| [flashscore/](flashscore/) | Sports scores and match data (Basketball, Football) | [README](flashscore/README.md) |
| [wikipedia/](wikipedia/) | Article content, infoboxes, tables, and search results | [README](wikipedia/README.md) |

---

## Adding a New Site

The `_template/` directory is a full-featured starting point — not a stub. It includes flows, processors, validators, components, and multi-environment config wiring already in place.

```bash
cp -r src/sites/_template src/sites/your_site_name
```

See the [template README](_template/README.md) for the full guide, including how to choose the right architectural pattern for your site's complexity.

---

## How Sites Are Structured

Every site implementation follows the same contract defined by `base/`:

- `config.py` — site ID, name, base URL, and metadata
- `scraper.py` — inherits from `BaseSiteScraper`, implements `navigate()`, `scrape()`, and `normalize()`
- `flow.py` — navigation-only logic (no data extraction)
- `selectors/` — YAML selector definitions

Registration in `src/main.py` wires a site into the unified CLI:

```python
SITE_CLIS = {
    'flashscore': ('src.sites.flashscore.cli.main', 'FlashscoreCLI'),
    'wikipedia':  ('src.sites.wikipedia.cli.main',  'WikipediaCLI'),
    'your_site':  ('src.sites.your_site.cli.main',  'YourSiteCLI'),
}
```

---

## Base Framework (`base/`)

The `base/` directory provides the shared foundation all sites build on:

- `BaseSiteScraper` / `ModularSiteScraper` — abstract base classes defining the scraper contract
- `ScraperRegistry` — central registry for discovery, validation, and metadata
- `ComponentManager` — lifecycle management for flows, processors, and validators
- `ConfigurationManager` — multi-environment config with feature flag support
- `DIContainer` — dependency injection for component wiring
- Validation utilities with actionable error messages
