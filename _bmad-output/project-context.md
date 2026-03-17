---
project_name: 'scrapamoja'
user_name: 'Tisone'
date: '2026-03-15'
sections_completed: ['technology_stack', 'language_specific', 'framework_specific', 'testing_rules', 'code_quality', 'development_workflow', 'critical_dont_miss_rules']
status: 'complete'
rule_count: 46
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

**Core Technologies:**
- Python 3.11+ (asyncio-first architecture)
- Playwright >=1.40.0 (browser automation)
- FastAPI >=0.104.0 (REST API framework)
- SQLAlchemy >=2.0.0 (async ORM)
- Pydantic >=2.5.0 (data validation)

**Key Dependencies:**
- BeautifulSoup4 >=4.12.0 (HTML parsing)
- lxml >=4.9.0 (XML/HTML processing)
- pytest >=7.4.0 (testing with async support)
- Black >=23.11.0 (code formatting, 88 char limit)
- Ruff >=0.1.6 (linting)
- MyPy >=1.7.0 (strict type checking)

**Critical Infrastructure:**
- Structlog >=23.2.0 (structured logging)
- Rich >=13.7.0 (console output)
- InfluxDB-client >=1.38.0 (metrics storage)

## Critical Implementation Rules

### Language-Specific Rules

- **Async/Await Requirements**: ALL I/O operations must use `async def` (browser, storage, network). Use `asyncio.gather()` for concurrent browser sessions. Implement `__aenter__`/`__aexit__` for resource managers (BrowserSession, etc.)
- **Module Integration Patterns**: Use dependency injection via module interfaces (`src/*/interfaces.py`). Leverage existing systems: don't recreate browser/session/storage handlers. Import from core systems: `from src.core.snapshot import SnapshotManager`
- **Type Safety Requirements**: MyPy strict mode - all functions need type annotations. Use Pydantic models for all data transfer objects. SQLAlchemy models must extend proper base classes
- **Error Handling Architecture**: Use structured logging with correlation IDs from observability stack. Custom exceptions per module (BrowserError, SelectorError, etc.). Implement resilience patterns from `src/resilience/`
- **Resource Management**: Use async context managers for browser sessions. Implement proper cleanup in interrupt handling scenarios. Follow snapshot system patterns for state persistence
- **Critical Integration Rules**: Always use existing selector engine for DOM operations. Leverage telemetry system for metrics collection. Use storage adapter instead of direct file operations

### Framework-Specific Rules

- **Browser Management Framework**: Use BrowserSession for all browser operations - never create raw Playwright instances. Implement authority pattern for concurrent session management. Use resource monitoring from browser management system. Follow stealth configuration patterns for anti-detection
- **Selector Engine Framework**: Use semantic selector strategies instead of raw CSS/XPath selectors. Implement confidence scoring for all selector operations. Use adaptive failure recovery from selector engine. Leverage DOM context for element validation
- **Snapshot System Framework**: Use SnapshotManager for all snapshot orchestration. Use SnapshotStorage for hierarchical storage with deduplication. Implement BrowserSnapshot and SelectorSnapshot handlers. Use SnapshotBundle for unified data model. Follow atomic operations and metrics tracking patterns
- **Storage & Persistence Framework**: Use storage adapter for all backend operations. Implement compression and metadata management. Use core snapshot system integration. Follow hierarchical storage patterns
- **Resilience Framework**: Use retry mechanisms from resilience engine for all external operations. Implement checkpointing for long-running operations. Use abort controller for intelligent failure detection. Follow resource lifecycle control patterns
- **Observability Framework**: Use structured logging with correlation IDs. Implement telemetry collection for all operations. Use event bus for system communication. Follow performance monitoring patterns
- **FastAPI Web Framework**: Use middleware patterns: CORS, rate limiting, audit logging. Implement structured responses with Pydantic models. Use dependency injection for framework services. Follow async route patterns
- **Interrupt Handling Framework**: Use signal capture for graceful shutdowns. Implement resource cleanup patterns. Use atomic operations for data integrity. Follow user feedback integration patterns
- **Navigation Intelligence Framework**: Use RouteDiscovery for automatic path finding. Implement ContextManager for navigation state. Use stealth-aware design for route planning. Follow human behavior emulation patterns
- **Multi-Site Framework**: Use ScraperRegistry for site discovery and registration. Follow BaseSiteScraper contract: navigate(), scrape(), normalize(). Implement site-specific configs with SITE_CONFIG dictionary. Use standardized directory structure: src/sites/{site_name}/{config.py,scraper.py,flow.py,selectors/,cli/}

### Testing Rules

- **Test Organization**: Use pytest markers: `@pytest.mark.integration`, `@pytest.mark.unit`, `@pytest.mark.slow`. Integration tests in `tests/integration/`, unit tests in `tests/`. Module-specific markers: `selector_engine`, `confidence_scoring`, `drift_detection`, `snapshots`, `performance`. Use `asyncio_mode=auto` for async test support
- **Mock Usage**: Use pytest-mock for mocking external dependencies. Mock Playwright browser instances in unit tests. Mock storage and snapshot systems for isolated testing. Use fixtures for common test setup (browser configs, DOM samples)
- **Integration Testing Patterns**: Test end-to-end browser session workflows. Validate selector engine integration with DOM context. Test snapshot system integration across modules. Validate resilience engine retry mechanisms. Test interrupt handling with shutdown coordinator
- **Module Integration Rules**: Test browser management with selector engine integration. Validate storage adapter with snapshot system. Test telemetry collection across all modules. Validate observability stack integration. Test FastAPI middleware integration
- **Coverage Requirements**: Coverage reporting enabled with HTML and XML output. Target coverage for core modules (browser, selectors, snapshot). Integration tests for cross-module workflows. Performance tests for critical integration paths
- **Cleanup & Integration Testing**: Test shutdown coordinator for graceful resource cleanup. Validate interrupt handling in integration scenarios. Test atomic operations across module boundaries. Use proper async context manager cleanup in integration tests
- **Browser Integration Testing**: Test stealth system integration with browser management. Validate navigation intelligence with route discovery. Test authority pattern for concurrent sessions. Validate resource monitoring integration

### Code Quality & Style Rules

- **Black Formatting Rules**: Line length: 88 characters (strictly enforced). Target Python version: 3.11+. Use double quotes for strings. Proper trailing comma handling for multi-line constructs
- **Ruff Linting Rules**: Enabled rules: pycodestyle errors/warnings, pyflakes, isort, flake8-bugbear, flake8-comprehensions, pyupgrade. Ignore E501 (line length - handled by Black). Ignore B008 (function calls in argument defaults). Per-file ignores: F401 for `__init__.py`, B011 for tests
- **MyPy Type Checking**: Strict mode enabled with comprehensive checks. All functions must have type annotations. Disallow untyped definitions and incomplete definitions. No implicit optional types. Warn on redundant casts and unused ignores
- **Code Organization**: Module structure: `src/module_name/` with `__init__.py` for clean API. Interfaces in `src/module_name/interfaces.py` for dependency injection. Models in `src/module_name/models/` for data structures. Use absolute imports from project root
- **Sub-Module Structure (SCR-003+)**: Each concern gets its own subdirectory (module), NOT just separate files. The main class file orchestrates — it does NOT implement. Logic lives in dedicated sub-modules. Example correct structure:
  ```
  src/network/interception/
  ├── __init__.py
  ├── core/          # lifecycle, attach/detach
  │   └── __init__.py
  ├── matching/      # pattern logic
  │   └── __init__.py
  ├── capture/       # response capture
  │   └── __init__.py
  ├── models/        # data structures
  │   └── __init__.py
  └── exceptions/   # custom exceptions
      └── __init__.py
  ```
  The anti-pattern: a single orchestrator file (e.g., `interceptor.py`) absorbing all logic, OR flat files like `models.py` and `exceptions.py`. This violates the principle that `src/module_name/` must be applied recursively inside each feature module.
- **Naming Conventions**: Classes: PascalCase (BrowserSession, SnapshotManager). Functions/variables: snake_case (capture_snapshot, browser_config). Constants: UPPER_SNAKE_CASE (MAX_RETRIES, DEFAULT_TIMEOUT). Modules: snake_case (browser_management, selector_engine)
- **Documentation Requirements**: Use docstrings for all public functions and classes. Structlog for logging with correlation IDs. Rich for console output and progress bars. Comprehensive README for each module

### Development Workflow Rules

- **CLI Entry Point Patterns**: Use `src/main.py` as unified CLI entry point. Site-specific CLI classes in `src/sites/{site}/cli/main.py`. Implement `create_parser()` and `run()` methods for each site CLI. Use argparse for command-line argument parsing. Support verbose flag for enhanced logging
- **Module Development Patterns**: Follow modular architecture with clear separation of concerns. Use dependency injection via interfaces. Implement proper async context managers. Use existing systems instead of recreating functionality. Follow established patterns for browser, selector, and storage integration
- **Configuration Management**: Use environment-based configuration via `src/config/`. Implement Pydantic models for configuration validation. Support feature flags for conditional functionality. Use JSON Schema for configuration validation. Centralize all configuration loading
- **Error Handling & Logging**: Use structured logging with correlation IDs. Implement custom exceptions per module. Use resilience engine for retry mechanisms. Follow interrupt handling patterns for graceful shutdowns. Use telemetry for monitoring and alerting
- **Integration with Existing Systems**: Always leverage existing selector engine for DOM operations. Use snapshot system for state persistence. Integrate with observability stack for monitoring. Use storage adapter for all persistence operations. Follow established patterns for browser management
- **Site-Specific Development**: Use base contracts from `src/sites/` framework. Implement registry patterns for site scrapers. Follow validation guardrails for data extraction. Use shared components for common functionality. Implement proper error handling for site-specific issues. Follow BaseSiteScraper contract: navigate(), scrape(), normalize(). Register new sites in ScraperRegistry and src/main.py SITE_CLIS dictionary

### Critical Don't-Miss Rules

- **Anti-Patterns to Avoid**: NEVER create raw Playwright instances - always use BrowserSession. NEVER bypass selector engine - use semantic selectors with confidence scoring. NEVER implement direct file operations - use storage adapter and snapshot system. NEVER ignore async context managers - proper resource cleanup is mandatory. NEVER create duplicate functionality - leverage existing modular systems
- **Critical Integration Gotchas**: ALWAYS use existing browser management instead of creating new session handlers. ALWAYS integrate with observability stack for logging and metrics. ALWAYS use resilience engine for external operations (retries, checkpoints). ALWAYS follow interrupt handling patterns for graceful shutdowns. ALWAYS use snapshot system for state persistence and recovery
- **Performance Anti-Patterns**: NEVER block event loops - use async patterns throughout. NEVER ignore resource monitoring - browser sessions have limits. NEVER skip deduplication in snapshot storage. NEVER disable telemetry collection - performance monitoring is critical. NEVER ignore memory optimization in navigation intelligence
- **Security & Stealth Rules**: ALWAYS use stealth system for anti-detection. NEVER expose browser fingerprints - use anti-detection masking. ALWAYS rotate proxies via proxy manager. NEVER ignore consent handling - use behavior emulator. ALWAYS follow human behavior emulation patterns
- **Edge Cases to Handle**: Browser session corruption - use authority pattern for recovery. Selector confidence failures - use adaptive failure recovery. Storage backend failures - use storage adapter fallbacks. Network interruptions - use resilience engine retry mechanisms. Resource exhaustion - use abort controller and lifecycle management
- **Critical System Dependencies**: ALWAYS import from core systems instead of duplicating functionality. NEVER break dependency injection patterns via interfaces. ALWAYS maintain correlation IDs across async operations. NEVER bypass shutdown coordinator in cleanup scenarios

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-03-15
