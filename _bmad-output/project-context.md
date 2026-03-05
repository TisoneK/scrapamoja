---
project_name: scrapamoja
user_name: Tisone
date: '2026-03-04'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'workflow_rules', 'critical_rules', 'existing_frameworks']
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## ⚠️ CRITICAL: Existing Frameworks (EXTEND, DON'T RECREATE)

**Before implementing ANY new functionality, check if it already exists!** This project has robust, production-ready frameworks that should be extended, not recreated.

### 1. Browser Management Framework (`src/browser/`)

**ALWAYS use existing browser components - this is an INTEGRATED SYSTEM:**

| Component | File | Purpose |
|-----------|------|---------|
| **BrowserSessionManager** | `browser/session_manager.py` | ⭐ **MAIN ENTRY POINT** - Coordinates all browser components |
| BrowserAuthority | `browser/authority.py` | Central authority for lifecycle control |
| BrowserManager | `browser/manager.py` | Multi-session management, concurrent access |
| BrowserSession | `browser/session.py` | Individual browser instance management |
| StateManager | `browser/state.py` | State persistence with encryption |
| ResourceMonitor | `browser/monitoring.py` | Resource usage monitoring |
| ResilienceManager | `browser/resilience.py` | Retry + circuit breaker patterns |
| ConfigurationManager | `browser/configuration.py` | Config loading, validation |
| Encryption | `browser/encryption.py` | State data encryption |
| CorruptionDetector | `browser/corruption_detector.py` | State corruption detection |
| LifecycleManager | `browser/lifecycle.py` | Module lifecycle phases |

**🔑 Session Manager is the INTEGRATION HUB** - It combines:
- Browser lifecycle (launch/close)
- State persistence (cookies, storage)
- Resource monitoring (memory, CPU)
- Error handling & recovery
- Configuration management

**Usage:**
```python
from src.browser.session_manager import BrowserSessionManager

# Don't create raw Playwright instances - use SessionManager!
session_manager = BrowserSessionManager()
browser_context = await session_manager.create_session(config)
```

### 2. Telemetry System (`src/telemetry/`)

**ALWAYS use existing telemetry components:**

| Component | File | Purpose |
|-----------|------|---------|
| Lifecycle | `telemetry/lifecycle.py` | System lifecycle management |
| Alerting | `telemetry/alerting/` | Alert engine, threshold monitoring |
| Collector | `telemetry/collector/` | Event, metrics, performance collection |
| Storage | `telemetry/storage/` | InfluxDB, backup, archival |
| Processing | `telemetry/processor/` | Batch processing, aggregation |
| Reporting | `telemetry/reporting/` | Analytics, health reports |
| Error Handling | `telemetry/error_handling.py` | Error classification, recovery |
| Configuration | `telemetry/configuration/` | Config schemas, validation |
| Security | `telemetry/security/` | Data protection, anonymization |

**Usage:**
```python
from src.telemetry.lifecycle import TelemetryLifecycleManager
from src.telemetry.collector.metrics_collector import MetricsCollector

# Don't create new logging/metrics systems - extend existing
collector = MetricsCollector()
```

### 3. Selector Engine (`src/selectors/`)

**Core selector resolution system:**

| Component | File | Purpose |
|-----------|------|---------|
| Engine | `selectors/engine.py` | Main selector resolution |
| Confidence | `selectors/confidence.py` | Confidence scoring |
| Registry | `selectors/registry.py` | Selector registration |
| Validation | `selectors/validation.py` | Selector validation |
| Context | `selectors/context_manager.py` | Context management |
| **Selector Strategies** | `selectors/strategies/` | 7 strategy implementations |
| Adaptive | `selectors/adaptive/` | Adaptive selector system |
| Drift | `selectors/interfaces.py` | IDriftDetector interface |
| Evolution | `selectors/evolution/` | Selector evolution |

**Selector Strategy Types:**
```python
from src.selectors.strategies import (
    AttributeMatchStrategy,    # CSS attribute matching
    CSSStrategy,                # CSS selector
    DOMRelationshipStrategy,    # DOM tree relationships
    RoleBasedStrategy,         # ARIA role-based
    TextAnchorStrategy,         # Text anchor positioning
    XPathStrategy,              # XPath expressions
    BaseStrategy,               # Abstract base for all strategies
)
```

### 4. Storage System (`src/storage/`)

**Unified storage adapter:**

| Component | File | Purpose |
|-----------|------|---------|
| StorageAdapter | `storage/adapter.py` | Abstract storage interface |
| FileSystemAdapter | `storage/adapter.py` | File system implementation |
| MemoryAdapter | `storage/adapter.py` | In-memory for testing |

**Usage:**
```python
from src.storage.adapter import get_storage_adapter, FileSystemStorageAdapter

# Don't create new storage - use existing adapter
storage = get_storage_adapter()
```

### 5. Site Scrapers (`src/sites/`)

**Site-specific implementations:**

| Site | Path | Implementation |
|------|------|-----------------|
| Template | `sites/_template/` | Base scraper template |
| Wikipedia | `sites/wikipedia/` | Full implementation |
| Flashscore | `sites/flashscore/` | Full implementation |
| GitHub | `sites/github/` | Full implementation |
| Shared | `sites/shared_components/` | Reusable components |

### 6. Stealth System (`src/stealth/`)

**Anti-detection framework:**

| Component | File | Purpose |
|-----------|------|---------|
| AntiDetection | `stealth/anti_detection.py` | Main anti-detection |
| Behavior | `stealth/behavior.py` | Human behavior emulation |
| Fingerprint | `stealth/fingerprint.py` | Browser fingerprinting |
| ProxyManager | `stealth/proxy_manager.py` | Proxy rotation |
| ConsentHandler | `stealth/consent_handler.py` | Consent dialog handling |
| Coordinator | `stealth/coordinator.py` | Orchestration |

### 7. Other Core Modules

| Module | Purpose |
|--------|---------|
| `src/models/` | Pydantic data models (selector_models.py) |
| `src/core/` | Core utilities (logging, shutdown) |
| `src/core/snapshot/` | **CRITICAL - DOM Snapshot System** - 18 files for capture, storage, triggers |
| `src/navigation/` | **CRITICAL - Navigation System** - 25+ files for route planning, adaptation |
| `src/resilience/` | **CRITICAL - Resilience System** - 30+ files for recovery, retry, checkpoints |
| `src/observability/` | Observability utilities (logging, metrics) |
| `src/interrupt_handling/` | Interrupt and signal handling |
| `src/config/` | Configuration management (settings.py with 22KB, YAML configs) |

### 8. Core Snapshot System (`src/core/snapshot/`)

**CRITICAL - This is the MAIN snapshot system:**

| Component | File | Purpose |
|-----------|------|---------|
| SnapshotManager | `core/snapshot/manager.py` | Main entry point for snapshot operations |
| SnapshotCapture | `core/snapshot/capture.py` | DOM capture logic |
| SnapshotStorage | `core/snapshot/storage.py` | Storage backend |
| SnapshotConfig | `core/snapshot/config.py` | Configuration |
| SnapshotTriggers | `core/snapshot/triggers.py` | Automatic capture triggers |
| SnapshotMetrics | `core/snapshot/metrics.py` | Performance metrics |
| SnapshotModels | `core/snapshot/models.py` | Data models |
| SnapshotCircuitBreaker | `core/snapshot/circuit_breaker.py` | Failure prevention |
| SnapshotIntegration | `core/snapshot/integration.py` | System integration |
| Handlers | `core/snapshot/handlers/` | Specialized handlers (browser, selector, error, retry, session, scraper, coordinator, monitoring) |

**Usage:**
```python
from src.core.snapshot import SnapshotManager, get_snapshot_manager

# Get global snapshot manager
snapshot_mgr = get_snapshot_manager()

# Capture snapshot
bundle = await snapshot_mgr.capture_snapshot(page, context, config)
```

### 9. Navigation System (`src/navigation/`)

**CRITICAL - Complex navigation handling:**

| Component | File | Purpose |
|-----------|------|---------|
| NavigationService | `navigation/navigation_service.py` | Main navigation orchestration |
| RouteDiscovery | `navigation/route_discovery.py` | Discover navigation routes |
| RouteOptimizer | `navigation/route_optimizer.py` | Optimize route selection |
| RouteAdaptation | `navigation/route_adaptation.py` | Adapt routes dynamically |
| PathPlanning | `navigation/path_planning.py` | Plan navigation paths |
| NavigationContext | `navigation/context_manager.py` | Context management |
| NavigationEventPublisher | `navigation/event_publisher.py` | Event publishing |
| PerformanceMonitor | `navigation/performance_monitor.py` | Performance tracking |
| CheckpointManager | `navigation/checkpoint_manager.py` | Navigation checkpoints |
| ProxyManager | `navigation/proxy_manager.py` | Proxy handling |
| HealthChecker | `navigation/health_checker.py` | Navigation health |
| Integrations | `navigation/integrations/` | External integrations |

### 10. Resilience System (`src/resilience/`)

**CRITICAL - Failure recovery and retry logic:**

| Component | File | Purpose |
|-----------|------|---------|
| ResilienceCoordinator | `resilience/coordinator.py` | Main orchestration (30KB) |
| BrowserRecovery | `resilience/browser_recovery.py` | Browser-specific recovery |
| FailureClassifier | `resilience/failure_classifier.py` | Classify failure types |
| FailureHandler | `resilience/failure_handler.py` | Handle failures |
| TabHandler | `resilience/tab_handler.py` | Tab-specific recovery |
| Correlation | `resilience/correlation.py` | Cross-component correlation |
| Events | `resilience/events.py` | Resilience events |
| Interfaces | `resilience/interfaces.py` | ABC interfaces |
| Retry | `resilience/retry/` | Retry logic modules |
| Checkpoint | `resilience/checkpoint/` | Checkpoint management |
| Resource | `resilience/resource/` | Resource management |
| Logging | `resilience/logging/` | Resilience logging |
| Config | `resilience/config/` | Resilience configuration |

---

## Technology Stack & Versions

### Core Technologies
- **Python 3.11+** - Required version (from `requires-python >=3.11`)
- **Playwright 1.40.0+** - Browser automation
- **Pydantic 2.5.0+** - Data validation with v2 API
- **pytest 7.4.0+** - Testing framework
- **pytest-asyncio 0.21.0+** - Async test support
- **SQLAlchemy 2.0.0+** - Database ORM
- **InfluxDB Client 1.38.0+** - Time-series data

### Development Tools
- **Black 23.11.0+** - Code formatter (88 char line length)
- **Ruff 0.1.6+** - Fast linter
- **Mypy 1.7.0+** - Type checker (strict mode)

### Key Dependencies
- **aiofiles 23.2.0+** - Async file I/O
- **asyncio-throttle 1.0.2+** - Rate limiting
- **lxml 4.9.0+** - XML/HTML parsing
- **beautifulsoup4 4.12.0+** - HTML parsing
- **structlog 23.2.0+** - Structured logging
- **rich 13.7.0+** - Terminal formatting
- **click 8.1.0+** - CLI framework
- **pyyaml 6.0.1+** - YAML config parsing

---

## Critical Implementation Rules

### Language-Specific Rules

#### Python Strict Mode Requirements
- **All functions must have type hints** - MyPy strict mode is enabled (`disallow_untyped_defs = true`)
- **No implicit optionals** - Use `Optional[X]` not `X | None` consistently, or vice versa but be consistent (`no_implicit_optional = true`)
- **No unused imports** - Enable `warn_unused_ignores = true`
- **Always use async/await for I/O** - Never use blocking calls in async context

#### Import Conventions
```python
# Standard library first
import asyncio
import json
from pathlib import Path

# Third-party imports
import pydantic
from playwright.async_api import async_playwright

# Local imports
from src.selectors.config import SelectorConfig
from src.utils.exceptions import SelectorEngineError
```

#### Exception Hierarchy Pattern
```python
class SelectorEngineError(Exception):
    """Base exception for selector engine - all custom exceptions inherit from this."""
    pass

class SelectorNotFoundError(SelectorEngineError):
    """Raised when selector is not found in DOM."""
    pass
```

### Framework-Specific Rules

#### Playwright Integration
- **Always use async_playwright()** - Never sync version in async code
- **Always release resources** - Use `async with` or proper cleanup:
  ```python
  async with async_playwright() as p:
      browser = await p.chromium.launch()
      # ... use browser
      await browser.close()  # Or use context manager
  ```
- **Context isolation** - Each scraping session gets own browser context

#### Selector Engine Patterns
- **Confidence scoring** - All selector strategies must return confidence 0.0-1.0
- **Strategy types** - Use Enum: `class StrategyType(str, Enum)`
- **Fallback chains** - Implement fallback selector chains with confidence thresholds

#### YAML Configuration
- **Hot-reload support** - Config files support live reload via file watcher
- **Inheritance** - Recipes support parent-child inheritance
- **Versioning** - Recipe versions tracked with stability scores

### Testing Rules

#### Test Markers (from pytest.ini)
```python
@pytest.mark.unit          # Fast, isolated unit tests
@pytest.mark.integration   # Tests requiring external services
@pytest.mark.slow          # Tests taking >5 seconds
@pytest.mark.selector_engine  # Selector engine specific
@pytest.mark.confidence_scoring  # Confidence scoring tests
@pytest.mark.drift_detection   # Drift detection tests
@pytest.mark.snapshots   # DOM snapshot tests
```

#### Test Structure
- **Location**: `tests/` directory (configured in `pyproject.toml`)
- **Async tests**: Use `@pytest.mark.asyncio` decorator
- **Fixtures**: Use `pytest-asyncio` fixtures for async setup
- **Mock external calls**: Use `pytest-mock` for Playwright/API mocking

#### Coverage Requirements
- Run with: `pytest --cov=src --cov-report=term-missing`
- Minimum coverage: Not explicitly set, but target >80% for core modules

### Code Quality & Style Rules

#### Formatting (Black)
- **Line length**: 88 characters (Black default)
- **Target Python**: 3.11 (from `target-version`)

#### Linting (Ruff)
- **Select rules**: E, W, F, I, B, C4, UP
- **Ignore**: E501 (line too long - handled by Black)
- **Per-file ignores**: `__init__.py` can skip F401

#### Type Checking (Mypy) - STRICT
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
```

#### Naming Conventions
- **Classes**: PascalCase (`class SelectorEngine`)
- **Functions/methods**: snake_case (`def get_selector()`)
- **Constants**: UPPER_SNAKE_CASE
- **Private methods**: `_leading_underscore()`
- **Files**: snake_case.py

#### Dataclass/Pydantic Usage
```python
from dataclasses import dataclass
from pydantic import BaseModel, Field

@dataclass
class SimpleData:
    name: str
    value: int

class ComplexModel(BaseModel):
    name: str
    value: int = Field(default=0, ge=0)
```

### Development Workflow Rules

#### Git Branch Naming
- Feature: `feature/description`
- Bugfix: `bugfix/description`
- Hotfix: `hotfix/description`

#### Testing Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific markers
pytest -m "not slow"
pytest -m "unit"

# Parallel execution
pytest -n auto
```

#### Code Quality Checks
```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

### Critical Don't-Miss Rules

#### Anti-Patterns to Avoid

1. **🔴 NEVER recreate existing frameworks** - This is the MOST IMPORTANT rule!
   - ❌ Don't create new Playwright instances → USE `BrowserSessionManager`
   - ❌ Don't create new logging systems → EXTEND `TelemetryLifecycleManager`
   - ❌ Don't create new storage → USE `StorageAdapter`
   - ❌ Don't create new metrics → USE `MetricsCollector`
   - ❌ Don't create new alerts → EXTEND `AlertEngine`
   - ❌ Never bypass SessionManager - it's the INTEGRATION HUB

2. **Never use sync Playwright in async code**
   ```python
   # WRONG
   from playwright.sync_api import sync_playwright
   
   # CORRECT
   from playwright.async_api import async_playwright
   ```

2. **Never block event loop**
   ```python
   # WRONG - blocks event loop
   time.sleep(5)
   
   # CORRECT - async sleep
   await asyncio.sleep(5)
   ```

3. **Never forget to close resources**
   ```python
   # WRONG - resource leak
   browser = await p.chromium.launch()
   # ... do work
   
   # CORRECT - always cleanup
   async with async_playwright() as p:
       browser = await p.chromium.launch()
       # ... work done, browser auto-closed
   ```

4. **Never ignore type hints**
   ```python
   # WRONG - no type hints
   def process(data):
       return data
   
   # CORRECT - full type hints
   def process(data: dict[str, Any]) -> list[str]:
       return list(data.keys())
   ```

5. **Never use bare exceptions**
   ```python
   # WRONG
   except:
       pass
   
   # CORRECT
   except SelectorEngineError as e:
       logger.error(f"Selector failed: {e}")
       raise
   ```

#### Security Rules
- **Never log sensitive data** - Redact PII, credentials
- **Environment variables** - Use `.env` for secrets, never commit
- **Proxy credentials** - Handle securely, never log

#### Performance Gotchas
- **Selector timeout** - Set reasonable timeouts (default 30s)
- **Memory leaks** - Always cleanup browser contexts
- **Rate limiting** - Respect site limits, use throttle
- **DOM snapshots** - Don't store full page HTML - extract needed data

---

_Last updated: 2026-03-04_
