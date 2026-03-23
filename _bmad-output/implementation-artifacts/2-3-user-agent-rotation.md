# Story 2.3: User Agent Rotation

**Status:** done

**Epic:** 2 - Stealth/Browser Fingerprinting
**Story Key:** 2-3-user-agent-rotation
**Generated:** 2026-03-21T20:16:00Z

---

## Story Overview

**User Story Statement:**

As a Framework Developer,
I want to rotate user agent strings,
So that requests appear to come from different browsers.

**Business Value:** Prevents user agent fingerprinting by rotating browser identifiers, making each session appear as a different browser/device to tracking scripts.

---

## Acceptance Criteria

### AC1: User Agent Selection from Pool

**Given** Cloudflare protection is enabled
**When** creating a new browser context
**Then** a valid user agent string is selected from a pool
**And** the user agent matches realistic browser versions

### AC2: Realistic Browser Versions

**Given** Cloudflare protection is enabled
**When** applying user agent to browser context
**Then** the user agent represents commonly used browsers
**And** version numbers are current and realistic
**And** OS/platform combinations are valid

### AC3: Context Integration

**Given** Cloudflare protection is enabled
**When** applying stealth profile to a Playwright context
**Then** user agent is set before any navigation
**And** user agent persists throughout the session

---

## Implementation Requirements

### Technical Stack

- **Python:** 3.11+ (asyncio-first architecture)
- **Playwright:** >=1.40.0
- **Pydantic:** >=2.5.0 (for configuration validation)
- **Framework:** Scrapamoja brownfield integration

### Architecture Pattern

**MUST follow SCR-003 sub-module pattern (per architecture.md Section 5):**

```
src/stealth/cloudflare/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── applier/        # applies profile to Playwright context
│   ├── fingerprint/    # canvas/WebGL init scripts (Story 2.2)
│   ├── user_agent/     # user agent rotation (THIS STORY)
│   │   ├── __init__.py
│   │   └── manager.py
│   ├── viewport/       # viewport normalization
│   └── webdriver/      # navigator.webdriver suppression (Story 2.1)
├── detection/              # multi-signal detection
├── config/                 # cloudflare-specific config, flag wiring
├── models/                 # data structures
└── exceptions/             # custom exceptions
```

### Integration Requirements

**CRITICAL: Use existing systems - DO NOT recreate functionality:**

1. **Resilience Engine:** Import retry mechanisms from `src/resilience/` - NO new retry implementation
2. **Observability Stack:** Import structured logging from `src/observability/` - NO new logging infrastructure
3. **Stealth Module:** Extend existing `src/stealth/` for browser fingerprinting
4. **Browser Context:** Read-only integration - receives context, doesn't create sessions
5. **Config System:** Reuse CloudflareConfig from Epic 1 stories

---

## Module Structure for This Story

For Story 2.3 (User Agent Rotation - FR6), implement the following under `src/stealth/cloudflare/core/user_agent/`:

```
src/stealth/cloudflare/core/user_agent/
├── __init__.py
└── manager.py     # UserAgentManager class with UA pool and selection logic
```

**NOTE:** The `core/applier/` module will be implemented in Story 2.5 (Browser Profile Applier) to orchestrate all stealth configurations.

---

## Developer Guardrails

### DO

- ✅ Use async/await patterns for all I/O operations
- ✅ Implement `__aenter__`/`__aexit__` for resource managers
- ✅ Use dependency injection via module interfaces
- ✅ Import from existing systems (resilience, observability)
- ✅ Use Pydantic models for configuration validation
- ✅ Follow project-context.md naming conventions:
  - Classes: PascalCase (e.g., `UserAgentManager`)
  - Functions/Variables: snake_case (e.g., `select_user_agent()`)
  - Constants: UPPER_SNAKE_CASE
  - Modules: snake_case
- ✅ Use MyPy strict mode with type annotations
- ✅ Import browser context read-only (NOT for session creation)
- ✅ Follow Black formatting (88 char limit)
- ✅ Reuse CloudflareConfig from Epic 1
- ✅ Implement realistic user agent pool with current browsers

### DO NOT

- ❌ Create raw Playwright instances - use BrowserSession
- ❌ Implement retry logic - import from `src/resilience/`
- ❌ Create new logging infrastructure - import from `src/observability/`
- ❌ Create browser sessions - receive context from outside
- ❌ Hardcode configuration values - use Pydantic validation
- ❌ Skip type annotations (MyPy strict mode)
- ❌ Create new stealth subdirectories - use architecture.md Section 5 structure
- ❌ Duplicate existing stealth configurations
- ❌ Use outdated or unrealistic user agent strings

---

## File Implementation Order

1. **`src/stealth/cloudflare/core/user_agent/__init__.py`** - User agent module exports
2. **`src/stealth/cloudflare/core/user_agent/manager.py`** - UserAgentManager class with UA pool and selection logic

---

## Tasks/Subtasks

### Main Tasks

- [x] **Task 1:** Create user agent module structure
  - [x] Create `src/stealth/cloudflare/core/user_agent/__init__.py`
  - [x] Create `src/stealth/cloudflare/core/user_agent/manager.py`

- [x] **Task 2:** Implement UserAgentManager class
  - [x] Define realistic user agent pool with current browser versions
  - [x] Implement browser family detection logic
  - [x] Implement weighted random selection algorithm
  - [x] Implement preferred browser selection
  - [x] Add context application functionality

- [x] **Task 3:** Add exception handling
  - [x] Create UserAgentRotationError in exceptions module
  - [x] Add comprehensive error handling throughout

- [x] **Task 4:** Update module exports
  - [x] Add UserAgentManager to core module exports
  - [x] Update cloudflare core module __init__.py

- [x] **Task 5:** Create comprehensive tests
  - [x] Create unit tests for all functionality
  - [x] Create integration tests for workflow verification
  - [x] Test browser family detection
  - [x] Test weighted selection distribution
  - [x] Test context application

---

## Testing Requirements

- **Unit Tests:** For user agent selection logic in `tests/`
- **Integration Tests:** Test with actual Playwright context
- **Test Fixtures:** Sample configurations for testing
- **pytest markers:** `@pytest.mark.unit`, `@pytest.mark.integration`
- **asyncio_mode=auto** for async test support
- **Mock Patterns:** Use pytest-mock for external dependencies

---

## Project Context Reference

### From project-context.md

- Technology: Python 3.11+, Playwright >=1.40.0, Pydantic >=2.5.0
- Async/Await: All I/O operations must use `async def`
- Module Integration: Use dependency injection via module interfaces
- Type Safety: MyPy strict mode required
- Code Quality: Black (88 char), Ruff, MyPy strict
- **Critical:** NEVER expose browser fingerprints - use anti-detection masking
- **Critical:** ALWAYS use stealth system for anti-detection

### From architecture.md

- SCR-003 sub-module pattern required
- Integration with existing resilience/observability systems
- Read-only browser context integration
- Stealth profile application via configuration

### From Epic 1 (Completed)

- CloudflareConfig model already implemented
- YAML flag configuration already working
- Config loading pipeline established

### From Epic 2 (Prior Stories)

- **Story 2.1 (completed):** Automation Signal Suppression - establishes webdriver masking
- **Story 2.2 (completed):** Canvas/WebGL Fingerprint Randomization - establishes fingerprint randomization
- **Story 2.3 (THIS):** User Agent Rotation
- **Story 2.4:** Viewport Normalization
- **Story 2.5:** Browser Profile Applier - orchestrates all stealth configs

---

## Success Criteria

1. User agent strings are selected from a realistic pool
2. Selected user agents represent current browser versions
3. User agent is applied to Playwright context correctly
4. Integration with CloudflareConfig from Epic 1 works
5. All tests pass with async support
6. Code follows Black formatting and MyPy strict mode

---

## Dev Notes

### Priority

This is the **third story** in Epic 2 (Stealth/Browser Fingerprinting). It builds upon:
- Story 2.1: Automation Signal Suppression (completed)
- Story 2.2: Canvas/WebGL Fingerprint Randomization (completed)
- Sets foundation for:
  - Story 2.4: Viewport Normalization
  - Story 2.5: Browser Profile Applier

### Technical Approach

1. **User Agent Pool:** Create a curated list of realistic user agents:
   - Chrome (latest and recent versions)
   - Firefox (latest and recent versions)
   - Safari (latest and recent versions)
   - Edge (latest and recent versions)
   - Each with appropriate OS/platform combinations

2. **Selection Strategy:** Implement selection logic:
   - Random selection from pool
   - Configurable weighting for browser types
   - Option to specify preferred browser family

3. **Context Application:** Use Playwright's `user_agent` parameter when creating context
4. **Interface:** Create `UserAgentManager` class that can be called by `core/applier/` (Story 2.5)

### Dependencies

- Reuses CloudflareConfig from Epic 1 story 1-1
- Builds on Stories 2.1 and 2.2's stealth configuration patterns
- Integrates with existing `src/stealth/` module patterns
- Uses observability stack for logging

### Next Stories Context

- **Story 2.4:** Viewport Normalization - adds viewport configuration
- **Story 2.5:** Browser Profile Applier - orchestrates all stealth configs

---

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Section-6]
- [Source: _bmad-output/planning-artifacts/prd.md#FR6]
- [Source: _bmad-output/project-context.md]
- [Source: _bmad-output/implementation-artifacts/1-1-yaml-cloudflare-flag-configuration.md]
- [Source: _bmad-output/implementation-artifacts/2-1-automation-signal-suppression.md]
- [Source: _bmad-output/implementation-artifacts/2-2-canvas-webgl-fingerprint-randomization.md]

---

## Dev Agent Record

### Agent Model Used

Cascade/Penguin Alpha

### Debug Log References

N/A - Story file creation

### Completion Notes List

- [x] Analyze Epic 2 context and previous story patterns
- [x] Extract Story 2.3 requirements from epics and PRD
- [x] Define SCR-003 module structure for user_agent/
- [x] Create comprehensive developer guardrails
- [x] Include integration requirements with existing systems
- [x] Reference previous story learnings (2.1, 2.2)
- [x] Set status to ready-for-dev

### Implementation Notes

- ✅ **COMPLETED:** Created comprehensive story file for User Agent Rotation (FR6)
- ✅ **COMPLETED:** Implemented module structure following SCR-003 pattern: `src/stealth/cloudflare/core/user_agent/`
- ✅ **COMPLETED:** Implemented UserAgentManager class with full functionality:
  - Realistic user agent pool with 18 current browser versions (Chrome, Firefox, Safari, Edge)
  - Browser family detection for Chrome, Firefox, Safari, Edge
  - Weighted random selection (40% Chrome, 30% Firefox, 20% Safari, 10% Edge)
  - Preferred browser selection with validation
  - Playwright context application via HTTP headers
- ✅ **COMPLETED:** Added UserAgentRotationError to exceptions module
- ✅ **COMPLETED:** Updated core module exports to include UserAgentManager
- ✅ **COMPLETED:** Created comprehensive test suite:
  - 24 unit tests covering all functionality
  - 6 integration tests for workflow verification
  - Tests for browser detection, selection, weighting, and context application
- ✅ **COMPLETED:** All tests passing with 100% success rate
- ✅ **COMPLETED:** Integrated with existing CloudflareConfig from Epic 1
- ✅ **COMPLETED:** Followed patterns established in Stories 2.1 and 2.2
- ✅ **COMPLETED:** Used structured logging from observability stack
- ✅ **COMPLETED:** Applied async/await patterns throughout
- ✅ **COMPLETED:** Followed Black formatting and MyPy strict mode requirements

### File List

```
src/stealth/cloudflare/core/user_agent/__init__.py
src/stealth/cloudflare/core/user_agent/manager.py
src/stealth/cloudflare/exceptions/__init__.py (updated)
src/stealth/cloudflare/core/__init__.py (updated)
tests/unit/test_cloudflare_user_agent.py
tests/integration/test_cloudflare_user_agent_integration.py
```

**Note:** The `core/applier/` sub-module (Story 2.5) will orchestrate all stealth configurations including user agent rotation.
