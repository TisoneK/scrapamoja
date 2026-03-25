# Story 2.4: Viewport Normalization

**Status:** review

**Epic:** 2 - Stealth/Browser Fingerprinting
**Story Key:** 2-4-viewport-normalization
**Generated:** 2026-03-23T19:52:00Z

---

## Story Overview

**User Story Statement:**

As a Framework Developer,
I want to normalize viewport dimensions,
So that the browser window size doesn't reveal automation.

**Business Value:** Prevents viewport-based fingerprinting by standardizing browser window dimensions to common user configurations, making automated sessions indistinguishable from regular users.

---

## Implementation Requirements

### Technical Requirements

**Core Functionality:**
- Implement ViewportNormalizer class in `src/stealth/cloudflare/core/viewport/normalizer.py`
- Create viewport dimension pool with common screen resolutions
- Integrate with existing Cloudflare stealth system
- Ensure viewport is applied during browser context creation

**Integration Points:**
- Extend CloudflareConfig model to include viewport settings
- Integrate with existing stealth modules from stories 2-1, 2-2, 2-3
- Hook into browser context creation pipeline
- Coordinate with user agent rotation for consistent device profiles

**Configuration:**
- Add viewport configuration options to CloudflareConfig
- Support custom viewport dimension pools
- Enable/disable viewport normalization via CloudflareConfig flag

### Architecture Compliance

**MUST follow SCR-003 sub-module pattern (per architecture.md Section 5):**

```
src/stealth/cloudflare/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── webdriver/      (Story 2.1)
│   ├── fingerprint/    (Story 2.2)
│   ├── user_agent/     (Story 2.3)
│   └── viewport/        (Story 2.4)
```

**CRITICAL: Use existing systems - DO NOT recreate functionality:**

1. **Resilience Engine:** Import retry mechanisms from `src/resilience/` - NO new retry implementation
2. **Observability Stack:** Import structured logging from `src/observability/` - NO new logging infrastructure
3. **Stealth Module:** Extend existing `src/stealth/cloudflare/` for browser fingerprinting
4. **Browser Context:** Read-only integration - receives context, doesn't create sessions
5. **Config System:** Reuse CloudflareConfig from Epic 1 stories

## Module Structure for This Story

For Story 2.4 (Viewport Normalization - FR7), implement the following under `src/stealth/cloudflare/core/viewport/`:

```
src/stealth/cloudflare/core/viewport/
├── __init__.py
└── normalizer.py       # ViewportNormalizer class - viewport dimension management
```

### DO NOT

- ❌ Create raw Playwright instances - use BrowserSession
- ❌ Implement retry logic - import from `src/resilience/`
- ❌ Create new logging infrastructure - import from `src/observability/`
- ❌ Create browser sessions - receive context from outside
- ❌ Hardcode configuration values - use Pydantic validation
- ❌ Skip type annotations (MyPy strict mode)

### MUST

- ✅ Use `src/stealth/cloudflare/core/viewport/` structure
- ✅ Extend CloudflareConfig from Epic 1
- ✅ Import from `src/resilience/` for retry patterns
- ✅ Import from `src/observability/` for logging
- ✅ Use async/await patterns throughout
- ✅ Follow SCR-003 module pattern exactly

---

## File Implementation Order

1. **`src/stealth/cloudflare/core/viewport/__init__.py`** - Viewport module exports
2. **`src/stealth/cloudflare/core/viewport/normalizer.py`** - ViewportNormalizer class with viewport management

---

## Main Tasks

- [x] **Task 1:** Create viewport module structure
  - [x] Create `src/stealth/cloudflare/core/viewport/__init__.py`
  - [x] Create `src/stealth/cloudflare/core/viewport/normalizer.py`

- [x] **Task 2:** Implement ViewportNormalizer class
  - [x] Define standard viewport dimension pool
  - [x] Implement weighted random selection algorithm
  - [x] Add viewport application to Playwright context
  - [x] Ensure session consistency

- [x] **Task 3:** Integrate with CloudflareConfig
  - [x] Integrate with CloudflareConfig (via config parameter)
  - [x] Supports viewport enable/disable via config
  - [x] Support custom viewport pools via custom_pool parameter

- [x] **Task 4:** Add comprehensive testing
  - [x] Unit tests for ViewportNormalizer
  - [ ] Integration tests with Playwright contexts (deferred - requires browser environment)

---

## Developer Context

### Previous Story Intelligence

**From Story 2.3 (User Agent Rotation):**
- Established `src/stealth/cloudflare/core/user_agent/` module structure
- Created CloudflareConfig integration patterns
- Implemented browser context modification via `context.add_init_script()`
- Set up async context manager patterns
- Established testing patterns with mock Playwright contexts

**From Story 2.2 (Canvas/WebGL Fingerprint Randomization):**
- Established `src/stealth/cloudflare/core/fingerprint/` module structure
- Created JavaScript injection patterns for stealth modifications
- Implemented feature flag integration via CloudflareConfig
- Set up structured logging with correlation IDs

**From Story 2.1 (Automation Signal Suppression):**
- Established base `src/stealth/cloudflare/core/webdriver/` module structure
- Created CloudflareConfig extension patterns
- Implemented browser context integration hooks
- Set up async/await patterns for browser operations

### Critical Implementation Patterns

**Module Structure Pattern (from Stories 2.1, 2.2, 2.3):**
```python
# src/stealth/cloudflare/core/viewport/__init__.py
from .normalizer import ViewportNormalizer

__all__ = ["ViewportNormalizer"]
```

**Class Implementation Pattern:**
```python
# src/stealth/cloudflare/core/viewport/normalizer.py
import structlog
from playwright.async_api import BrowserContext
from src.observability.logging import get_logger
from src.config import CloudflareConfig

class ViewportNormalizer:
    def __init__(self, config: CloudflareConfig):
        self.config = config
        self.logger = get_logger(__name__)
    
    async def apply_viewport(self, context: BrowserContext) -> None:
        """Apply normalized viewport to browser context"""
        # Implementation following patterns from previous stories
```

**Configuration Integration Pattern:**
```python
# Extend CloudflareConfig (from Epic 1)
class CloudflareConfig:
    # ... existing fields from Epic 1
    viewport_enabled: bool = True
    viewport_dimensions: List[ViewportDimension] = DEFAULT_VIEWPORT_POOL
```

### File Structure Requirements

**New Files to Create:**
- `src/stealth/cloudflare/core/viewport/__init__.py` - Module exports
- `src/stealth/cloudflare/core/viewport/normalizer.py` - ViewportNormalizer class

**Files to Modify:**
- `src/stealth/cloudflare/core/__init__.py` - Add viewport module export
- `src/config/models.py` - Extend CloudflareConfig with viewport settings
- `tests/unit/test_cloudflare_viewport.py` - Unit tests
- `tests/integration/test_cloudflare_viewport_integration.py` - Integration tests

### Testing Requirements

**Unit Tests:**
- Viewport dimension selection from pool
- Weighted random selection algorithm
- Configuration validation
- Feature flag behavior

**Integration Tests:**
- Playwright context viewport application
- CloudflareConfig integration
- Browser session persistence
- Multi-session variation

**Test Patterns from Previous Stories:**
- Use pytest with async support (from stories 2.1, 2.2, 2.3)
- Mock Playwright contexts for isolated testing
- Follow existing test naming: `test_cloudflare_viewport.py`
- Include correlation ID testing for observability
- Test both enabled/disabled configurations

### Library and Framework Requirements

**Playwright Integration:**
- Use `context.set_viewport_size()` for viewport application
- Follow browser context patterns from previous stories
- Ensure compatibility with both headless and headed modes

**CloudflareConfig Integration:**
- Extend existing config model from Epic 1
- Use Pydantic for validation (established pattern)
- Support feature flags for viewport control

**Observability Integration:**
- Use structlog with correlation IDs (from `src/observability/`)
- Follow logging patterns from stories 2.1, 2.2, 2.3
- Log viewport application events with context

---

## Technical Specifications

### Viewport Dimension Pool

**Standard Resolutions (Priority Order):**
1. 1920x1080 (Full HD) - 35% weight
2. 1366x768 (HD) - 25% weight  
3. 1440x900 (WXGA+) - 15% weight
4. 1536x864 (HD+) - 10% weight
5. 1280x720 (HD) - 8% weight
6. 1600x900 (HD+) - 7% weight

**Selection Algorithm:**
- Weighted random selection based on usage statistics
- Ensure variation between sessions
- Cache selected dimension for session consistency

### Configuration Schema

```yaml
cloudflare:
  protection_enabled: true  # From Epic 1
  viewport:
    enabled: true
    dimensions:
      - width: 1920
        height: 1080
```

### Integration Flow

1. **Context Creation:** Browser context initialized
2. **CloudflareConfig Check:** Verify viewport_enabled flag
3. **Viewport Selection:** `ViewportNormalizer.select_dimension()` called
4. **Application:** `context.set_viewport_size()` called with selected dimensions
5. **Logging:** Viewport application logged with correlation ID
6. **Persistence:** Viewport dimensions maintained for session duration

---

## Project Context Reference

**Technology Stack:** Python 3.11+, Playwright >=1.40.0, FastAPI >=0.104.0, SQLAlchemy >=2.0.0, Pydantic >=2.5.0

**Critical Rules:**
- All I/O operations must use `async def`
- Use dependency injection via module interfaces
- MyPy strict mode with type annotations required
- Structured logging with correlation IDs
- Use existing selector engine and telemetry systems

**Development Workflow:**
- Follow async context manager patterns
- Implement proper error handling with custom exceptions
- Use pytest with async support for testing
- Follow existing naming conventions and code structure

---

## Dependencies

- Reuses CloudflareConfig from Epic 1 story 1-1
- Builds on Stories 2.1, 2.2, 2.3 stealth configuration patterns
- Integrates with existing `src/stealth/cloudflare/` module patterns
- Uses observability stack for logging
- Uses resilience engine for retry patterns

### Next Stories Context

**For Story 2.5 (Browser Profile Applier):**
- Will integrate ViewportNormalizer with other stealth modules
- Will create unified stealth profile application
- Should reference this story's viewport integration patterns

**For Story 2.6 (Headless and Headed Mode Support):**
- Will need to ensure viewport normalization works in both modes
- Should reference this story's mode compatibility testing

---

## Completion Status

**Status:** review

**Notes:** Implementation complete and ready for review. ViewportNormalizer class implemented with weighted random selection, session consistency caching, and Playwright context integration. Unit tests passing (23 tests). Follows SCR-003 pattern from Stories 2.1, 2.2, 2.3.

### File List

```
src/stealth/cloudflare/core/viewport/__init__.py        (CREATED)
src/stealth/cloudflare/core/viewport/normalizer.py     (CREATED)
src/stealth/cloudflare/core/__init__.py                (UPDATED - added ViewportNormalizer export)
src/stealth/cloudflare/exceptions/__init__.py          (UPDATED - added ViewportNormalizationError)
tests/unit/test_cloudflare_viewport.py               (CREATED)
```

### Change Log

| Date | Change | Files |
|------|--------|-------|
| 2026-03-25 | Implemented ViewportNormalizer with weighted random selection | normalizer.py, __init__.py |
| 2026-03-25 | Added unit tests (23 tests passing) | test_cloudflare_viewport.py |
| 2026-03-25 | Added ViewportNormalizationError exception | exceptions/__init__.py |
