# scraper Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-27

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
- 001-fix-framework-bugs: Added Python 3.11+ + Playwright (async API), asyncio
- 007-selector-telemetry: Added Python 3.11+ with asyncio + Playwright (async API), asyncio, JSON schema, time series storage (NEEDS CLARIFICATION)
- 007-yaml-selector-config: Added Python 3.11+ + PyYAML, watchdog (file monitoring), existing Selector Engine


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
