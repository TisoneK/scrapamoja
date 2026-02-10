# scraper Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-01-29

## Active Technologies
- Python 3.11+ with asyncio + Playwright (async API), NetworkX for graph algorithms, JSON schema validation (004-navigation-routing)
- JSON files with schema versioning for route graphs and navigation history (004-navigation-routing)
- Python 3.11+ with asyncio + Playwright (async API), psutil for resource monitoring, JSON for checkpoint storage (005-production-resilience)
- JSON-based checkpoint files with schema versioning, structured logging files (005-production-resilience)
- Python 3.11+ + PyYAML, watchdog (file monitoring), existing Selector Engine (007-yaml-selector-config)
- YAML files in `src/selectors/config/` hierarchy (007-yaml-selector-config)
- Python 3.11+ with asyncio + Playwright (async API), asyncio, JSON schema, time series storage (NEEDS CLARIFICATION) (007-selector-telemetry)
- Time series database for metrics (NEEDS CLARIFICATION - InfluxDB, Prometheus, or custom JSON files) (007-selector-telemetry)
- Python 3.11+ + Playwright (async API), asyncio (001-fix-framework-bugs)
- File system (JSON) for session persistence (001-fix-framework-bugs)
- Python 3.11+ + Playwright (async API), existing browser lifecycle components (009-page-html-capture)
- File system (JSON snapshots + separate HTML files) (009-page-html-capture)
- Python 3.11+ + Playwright (async API), existing browser lifecycle components, PIL/Pillow for image processing (010-screenshot-capture)
- File system (JSON snapshots + separate PNG screenshot files) (010-screenshot-capture)
- [if applicable, e.g., PostgreSQL, CoreData, files or N/A] (009-page-html-capture)
- Python 3.11+ + Playwright (async API), existing selector engine implementation (012-selector-engine-integration)
- JSON files for snapshots and telemetry data in data/ directory (012-selector-engine-integration)
- Python 3.11+ + playwright>=1.40.0, pytest>=7.4.0, pytest-asyncio>=0.21.0, pydantic>=2.5.0, structlog>=23.2.0 (014-snapshot-timing-fix)
- JSON files (session data, snapshots), InfluxDB (telemetry metrics) (014-snapshot-timing-fix)
- Python 3.11+ with asyncio + Playwright (async API), PyYAML for configuration, existing selector engine and browser lifecycle components (013-site-scraper-template)
- File system (template folders, YAML configs) for site scraper framework (013-site-scraper-template)
- Python 3.11+ with BeautifulSoup4, lxml, python-dateutil, pydantic, regex for data extraction (014-extractor-module)
- In-memory processing with optional JSON serialization for extraction rules and results (014-extractor-module)
- Python 3.11+ + Playwright (async API), PyYAML for configuration, existing selector engine and browser lifecycle components (015-enhance-site-template-modular)
- File system (template folders, YAML configs), JSON for metadata (015-enhance-site-template-modular)
- Python 3.11+ + Playwright (async API), existing extractor module, Wikipedia-specific extraction rules, data validation frameworks (016-wikipedia-extractor-integration)
- JSON for extraction results, Wikipedia API data structures, caching for extraction rules (016-wikipedia-extractor-integration)
- Python 3.11+ + Playwright, PyYAML, existing selector engine (016-wikipedia-extractor-fix)
- File-based YAML selectors in `src/sites/wikipedia/selectors/` (016-wikipedia-extractor-fix)
- Python 3.11+ + Playwright, PyYAML, existing framework components (BaseSiteScraper, BaseFlow, DOMContext, ExtractionRule, SemanticSelector) (017-site-template-integration)
- File-based YAML configuration, JSON schema for validation (017-site-template-integration)

- Python 3.11+ with asyncio + Playwright (async API), psutil for resource monitoring (003-browser-lifecycle)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11+ with asyncio: Follow standard conventions

## Recent Changes
- 017-site-template-integration: Added Python 3.11+ + Playwright, PyYAML, existing framework components (BaseSiteScraper, BaseFlow, DOMContext, ExtractionRule, SemanticSelector)
- 016-wikipedia-extractor-fix: Added Python 3.11+ + Playwright, PyYAML, existing selector engine
- 015-enhance-site-template-modular: Added Python 3.11+ + Playwright (async API), PyYAML for configuration, existing selector engine and browser lifecycle components


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
