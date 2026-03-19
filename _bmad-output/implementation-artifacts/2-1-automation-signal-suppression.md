# Story 2.1: Automation Signal Suppression

**Status:** ready-for-dev

**Epic:** 2 - Stealth/Browser Fingerprinting
**Story Key:** 2-1-automation-signal-suppression
**Generated:** 2026-03-19T14:50:07Z

---

## Story Overview

**User Story Statement:**

As a Framework Developer,
I want to suppress navigator.webdriver flag,
So that the browser appears as a regular user browser.

**Business Value:** Prevents Cloudflare from detecting browser automation by masking the primary automation signal.

---

## Acceptance Criteria

### AC1: Navigator.webdriver Suppression

**Given** a Playwright browser context
**When** Cloudflare protection is enabled
**Then** the navigator.webdriver property is set to false/undefined
**And** the property appears as a normal browser property

### AC2: Additional Automation Signal Masking

**Given** a Playwright browser context
**When** Cloudflare protection is enabled
**Then** other automation signals are masked
**And** the browser appears as a regular user browser

### AC3: Context Integration

**Given** Cloudflare protection is enabled
**When** applying stealth profile to a Playwright context
**Then** automation signals are suppressed before any navigation
**And** signals remain suppressed throughout the session

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
│   │   ├── __init__.py
│   │   └── apply.py
│   ├── fingerprint/    # canvas/WebGL init scripts
│   │   ├── __init__.py
│   │   └── scripts.py
│   ├── user_agent/     # user agent rotation
│   │   ├── __init__.py
│   │   └── manager.py
│   ├── viewport/       # viewport normalization
│   │   ├── __init__.py
│   │   └── config.py
│   └── webdriver/      # navigator.webdriver suppression (THIS STORY)
│       ├── __init__.py
│       └── mask.py
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

For Story 2.1 (Automation Signal Suppression - FR5), implement the following under `src/stealth/cloudflare/core/webdriver/`:

```
src/stealth/cloudflare/core/webdriver/
├── __init__.py
└── mask.py       # WebdriverMasker class - navigator.webdriver suppression
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
  - Classes: PascalCase (e.g., `AutomationSignalSuppressor`)
  - Functions/Variables: snake_case (e.g., `suppress_signals()`)
  - Constants: UPPER_SNAKE_CASE
  - Modules: snake_case
- ✅ Use MyPy strict mode with type annotations
- ✅ Import browser context read-only (NOT for session creation)
- ✅ Follow Black formatting (88 char limit)
- ✅ Reuse CloudflareConfig from Epic 1
- ✅ Implement JavaScript injection for signal suppression

### DO NOT

- ❌ Create raw Playwright instances - use BrowserSession
- ❌ Implement retry logic - import from `src/resilience/`
- ❌ Create new logging infrastructure - import from `src/observability/`
- ❌ Create browser sessions - receive context from outside
- ❌ Hardcode configuration values - use Pydantic validation
- ❌ Skip type annotations (MyPy strict mode)
- ❌ Create new stealth subdirectories - use architecture.md Section 5 structure
- ❌ Duplicate existing stealth configurations

---

## File Implementation Order

1. **`src/stealth/cloudflare/core/webdriver/__init__.py`** - Webdriver module exports
2. **`src/stealth/cloudflare/core/webdriver/mask.py`** - WebdriverMasker class with JavaScript injection

---

## Testing Requirements

- **Unit Tests:** For signal suppression logic in `tests/`
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
- Stealth profile application via JavaScript injection

### From Epic 1 (Completed)

- CloudflareConfig model already implemented
- YAML flag configuration already working
- Config loading pipeline established

---

## Success Criteria

1. navigator.webdriver property is suppressed (set to false/undefined)
2. Additional automation signals are masked
3. Stealth profile applies to Playwright context correctly
4. Integration with CloudflareConfig from Epic 1 works
5. All tests pass with async support
6. Code follows Black formatting and MyPy strict mode

---

## Dev Notes

### Priority

This is the **first story** in Epic 2 (Stealth/Browser Fingerprinting). It establishes the foundation for:
- Story 2.2: Canvas/WebGL Fingerprint Randomization
- Story 2.3: User Agent Rotation
- Story 2.4: Viewport Normalization
- Story 2.5: Browser Profile Applier
- Story 2.6: Headless and Headed Mode Support

### Technical Approach

1. **JavaScript Injection:** Use Playwright's `add_init_script()` to inject JavaScript that modifies `navigator.webdriver`
2. **Property Override:** Override the `webdriver` property in the navigator object to return `undefined`
3. **Additional Automation Signals:** Also mask other common automation detection properties:
   - `$cdc_adoQpoasnfa76pfcZLmcfl_Array`
   - `$cdc_adoQpoasnfa76pfcZLmcfl_Object`
   - `$cdc_adoQpoasnfa76pfcZLmcfl_Promise`
   - `$cdc_adoQpoasnfa76pfcZLmcfl_Symbol`
4. **Interface:** Create `WebdriverMasker` class that can be called by `core/applier/` (Story 2.5)

### Dependencies

- Reuses CloudflareConfig from Epic 1 story 1-1
- Integrates with existing `src/stealth/` module patterns
- Uses observability stack for logging

### Next Stories Context

- **Story 2.2:** Canvas/WebGL Fingerprint Randomization - extends with canvas spoofing
- **Story 2.3:** User Agent Rotation - adds UA string selection
- **Story 2.4:** Viewport Normalization - adds viewport configuration
- **Story 2.5:** Browser Profile Applier - orchestrates all stealth configs

---

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Section-6]
- [Source: _bmad-output/planning-artifacts/prd.md#FR5]
- [Source: _bmad-output/project-context.md]
- [Source: _bmad-output/implementation-artifacts/1-1-yaml-cloudflare-flag-configuration.md]

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

N/A - First story of Epic 2

### Completion Notes List

- [ ] Create stealth module structure
- [ ] Implement JavaScript injection scripts
- [ ] Implement AutomationSignalSuppressor class
- [ ] Update core applier for signal suppression
- [ ] Add unit tests
- [ ] Validate Black formatting
- [ ] Run MyPy type check

### File List

```
src/stealth/cloudflare/core/webdriver/__init__.py
src/stealth/cloudflare/core/webdriver/mask.py
tests/unit/test_cloudflare_webdriver.py
```

**Note:** The `core/applier/` sub-module (Story 2.5) will orchestrate all stealth configurations including this webdriver mask.
