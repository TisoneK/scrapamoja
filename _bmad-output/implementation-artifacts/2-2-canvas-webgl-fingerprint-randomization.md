# Story 2.2: Canvas/WebGL Fingerprint Randomization

**Status:** review

**Epic:** 2 - Stealth/Browser Fingerprinting
**Story Key:** 2-2-canvas-webgl-fingerprint-randomization
**Generated:** 2026-03-19T17:02:00Z

---

## Story Overview

**User Story Statement:**

As a Framework Developer,
I want to randomize canvas and WebGL fingerprints,
So that the browser has unique fingerprints for each session.

**Business Value:** Prevents Canvas and WebGL fingerprinting by returning randomized values, making each browser session appear unique to tracking scripts.

---

## Acceptance Criteria

### AC1: Canvas Fingerprint Randomization

**Given** a Playwright browser context
**When** Cloudflare protection is enabled
**Then** JavaScript initialization scripts are injected
**And** canvas fingerprint returns randomized values
**And** each session produces a different canvas hash

### AC2: WebGL Renderer Spoofing

**Given** a Playwright browser context
**When** Cloudflare protection is enabled
**Then** WebGL renderer info is spoofed
**And** the reported renderer appears as a common GPU
**And** vendor information is masked

### AC3: Context Integration

**Given** Cloudflare protection is enabled
**When** applying stealth profile to a Playwright context
**Then** canvas/WebGL randomization scripts are injected before any navigation
**And** fingerprint randomization persists throughout the session

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
│   ├── fingerprint/    # canvas/WebGL init scripts (THIS STORY)
│   │   ├── __init__.py
│   │   └── scripts.py
│   ├── user_agent/     # user agent rotation
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

For Story 2.2 (Canvas/WebGL Fingerprint Randomization - FR8), implement the following under `src/stealth/cloudflare/core/fingerprint/`:

```
src/stealth/cloudflare/core/fingerprint/
├── __init__.py
└── scripts.py       # CanvasFingerprintRandomizer and WebGLSpoofer classes
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
  - Classes: PascalCase (e.g., `CanvasFingerprintRandomizer`)
  - Functions/Variables: snake_case (e.g., `randomize_canvas()`)
  - Constants: UPPER_SNAKE_CASE
  - Modules: snake_case
- ✅ Use MyPy strict mode with type annotations
- ✅ Import browser context read-only (NOT for session creation)
- ✅ Follow Black formatting (88 char limit)
- ✅ Reuse CloudflareConfig from Epic 1
- ✅ Implement JavaScript injection for fingerprint randomization

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

1. **`src/stealth/cloudflare/core/fingerprint/__init__.py`** - Fingerprint module exports
2. **`src/stealth/cloudflare/core/fingerprint/scripts.py`** - CanvasFingerprintRandomizer and WebGLSpoofer classes with JavaScript injection

---

## Testing Requirements

- **Unit Tests:** For fingerprint randomization logic in `tests/`
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

### From Epic 2 (Prior Stories)

- **Story 2.1 (completed):** Automation Signal Suppression - establishes webdriver masking
- **Story 2.2 (THIS):** Canvas/WebGL Fingerprint Randomization
- **Story 2.3:** User Agent Rotation
- **Story 2.4:** Viewport Normalization
- **Story 2.5:** Browser Profile Applier - orchestrates all stealth configs

---

## Success Criteria

1. Canvas fingerprint returns randomized values for each session
2. WebGL renderer info is spoofed to appear as common GPU
3. JavaScript injection occurs before page navigation
4. Integration with CloudflareConfig from Epic 1 works
5. All tests pass with async support
6. Code follows Black formatting and MyPy strict mode

---

## Dev Notes

### Priority

This is the **second story** in Epic 2 (Stealth/Browser Fingerprinting). It builds upon:
- Story 2.1: Automation Signal Suppression (completed)
- Sets foundation for:
  - Story 2.3: User Agent Rotation
  - Story 2.4: Viewport Normalization
  - Story 2.5: Browser Profile Applier

### Technical Approach

1. **Canvas Randomization:** Use Playwright's `add_init_script()` to inject JavaScript that:
   - Overrides `HTMLCanvasElement.prototype.toDataURL`
   - Overrides `HTMLCanvasElement.prototype.toBlob`
   - Adds noise to canvas image data before rendering
   - Returns different values each call

2. **WebGL Spoofing:** Override WebGL properties to report:
   - Common GPU renderer (e.g., "ANGLE (NVIDIA GeForce RTX 3080)")
   - Common GPU vendor (e.g., "NVIDIA Corporation")
   - Standard WebGL version

3. **Interface:** Create `CanvasFingerprintRandomizer` and `WebGLSpoofer` classes that can be called by `core/applier/` (Story 2.5)

### Dependencies

- Reuses CloudflareConfig from Epic 1 story 1-1
- Builds on Story 2.1's JavaScript injection patterns
- Integrates with existing `src/stealth/` module patterns
- Uses observability stack for logging

### Next Stories Context

- **Story 2.3:** User Agent Rotation - adds UA string selection
- **Story 2.4:** Viewport Normalization - adds viewport configuration
- **Story 2.5:** Browser Profile Applier - orchestrates all stealth configs

---

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Section-6]
- [Source: _bmad-output/planning-artifacts/prd.md#FR8]
- [Source: _bmad-output/project-context.md]
- [Source: _bmad-output/implementation-artifacts/1-1-yaml-cloudflare-flag-configuration.md]
- [Source: _bmad-output/implementation-artifacts/2-1-automation-signal-suppression.md]

---

## Dev Agent Record

### Agent Model Used

(minimax/minimax-m2.5:free)

### Debug Log References

N/A - Story file creation

### Completion Notes List

- [x] Create fingerprint module structure
- [x] Implement CanvasFingerprintRandomizer class
- [x] Implement WebGLSpoofer class
- [x] Add FingerprintRandomizerError exception
- [x] Add unit tests
- [x] Validate Black formatting
- [x] Run all tests (no regressions)

### Implementation Notes

- Created `CanvasFingerprintRandomizer` class that randomizes canvas fingerprint by:
  - Overriding `HTMLCanvasElement.prototype.toDataURL`
  - Overriding `HTMLCanvasElement.prototype.toBlob`
  - Adding noise to canvas pixel data via `getImageData`/`putImageData`
- Created `WebGLSpoofer` class that spoofs WebGL information by:
  - Overriding `WebGLRenderingContext.prototype.getParameter`
  - Spoofing GPU_VENDOR (37445) and GPU_RENDERER (37446)
  - Supporting both WebGL1 and WebGL2
  - Using configurable GPU values (defaults to NVIDIA GeForce RTX 3080)
- Added `FingerprintRandomizerError` exception to exceptions module
- Uses Playwright's `add_init_script()` to inject JavaScript before page loads
- Follows async/await patterns with proper type annotations
- All 33 new unit tests pass
- No regressions in existing 105 tests

### File List

```
src/stealth/cloudflare/core/fingerprint/__init__.py
src/stealth/cloudflare/core/fingerprint/scripts.py
tests/unit/test_cloudflare_fingerprint.py
```

**Note:** The `core/applier/` sub-module (Story 2.5) will orchestrate all stealth configurations including canvas/WebGL fingerprint randomization.
