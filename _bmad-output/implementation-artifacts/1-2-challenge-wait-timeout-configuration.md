# Story 1.2: Challenge Wait Timeout Configuration

**Status:** ready-for-dev

**Epic:** 1 - Configuration Management
**Story Key:** 1-2-challenge-wait-timeout-configuration
**Generated:** 2026-03-18T21:37:00Z

---

## Story Overview

**User Story Statement:**

As a Site Module Developer,
I want to customize the challenge wait timeout per site,
So that I can handle sites with longer challenge times.

**Business Value:** Allows site-specific timeout tuning for sites that require longer challenge solve times.

---

## Acceptance Criteria

### AC1: Custom Timeout Configuration

**Given** a site module with `cloudflare_protected: true`
**When** I configure `challenge_timeout: 60` (seconds)
**Then** the framework waits up to 60 seconds for challenge completion
**And** returns timeout error after 60 seconds if challenge not resolved

### AC2: Default Timeout

**Given** no timeout configuration
**Then** the default timeout of 30 seconds is applied

### AC3: Timeout Range Validation

**Given** a timeout value outside valid range (< 5 or > 300 seconds)
**Then** validation error is raised with acceptable range message

### AC4: Timeout Integration

**Given** a valid timeout configuration
**Then** the timeout is passed to challenge detection module for wait logic
**And** timeout events are logged via observability system

---

## Implementation Requirements

### Technical Stack

- **Python:** 3.11+ (asyncio-first architecture)
- **Playwright:** >=1.40.0
- **Pydantic:** >=2.5.0 (for configuration validation)
- **Framework:** Scrapamoja brownfield integration

### Architecture Pattern

**MUST follow SCR-003 sub-module pattern:**

```
src/stealth/cloudflare/
├── __init__.py
├── core/                    # profile lifecycle, apply to context
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

---

## Module Structure for This Story

For Story 1.2, extend the existing config structure from Story 1.1:

```
src/stealth/cloudflare/
├── __init__.py                    # Already exists (Story 1.1)
├── config/
│   ├── __init__.py                # Already exists (Story 1.1)
│   ├── loader.py                  # Already exists (Story 1.1) - Add timeout field
│   ├── flags.py                   # Already exists (Story 1.1) - Add timeout handling
│   └── schema.py                  # Already exists (Story 1.1) - Add timeout validation
├── models/
│   ├── __init__.py                # Already exists (Story 1.1)
│   └── config.py                  # Already exists (Story 1.1) - Add challenge_timeout field
├── core/                          # NEW: Add core module for challenge handling
│   ├── __init__.py
│   └── waiter.py                  # NEW: Challenge wait logic with timeout
└── exceptions/
    └── __init__.py                # Already exists (Story 1.1) - Add TimeoutException
```

### New Files to Create

1. `src/stealth/cloudflare/core/__init__.py` - Core module exports
2. `src/stealth/cloudflare/core/waiter.py` - Challenge wait logic with configurable timeout
3. `src/stealth/cloudflare/exceptions/__init__.py` - Add `ChallengeTimeoutError`

### Files to Modify

1. `src/stealth/cloudflare/models/config.py` - Add `challenge_timeout` field with default 30
2. `src/stealth/cloudflare/config/schema.py` - Add timeout field validation (5-300 seconds)
3. `src/stealth/cloudflare/config/loader.py` - Add timeout field loading
4. `src/stealth/cloudflare/config/flags.py` - Add timeout flag handling

---

## Developer Guardrails

### DO

- ✅ Use async/await patterns for all I/O operations
- ✅ Implement `__aenter__`/`__aexit__` for resource managers
- ✅ Use dependency injection via module interfaces
- ✅ Import from existing systems (resilience, observability)
- ✅ Use Pydantic models for configuration validation
- ✅ Follow project-context.md naming conventions:
  - Classes: PascalCase (e.g., `ChallengeWaiter`)
  - Functions/Variables: snake_case (e.g., `wait_for_challenge()`)
  - Constants: UPPER_SNAKE_CASE
  - Modules: snake_case
- ✅ Use MyPy strict mode with type annotations
- ✅ Import browser context read-only (NOT for session creation)
- ✅ Follow Black formatting (88 char limit)
- ✅ Re-use Story 1.1 patterns for config extension

### DO NOT

- ❌ Create raw Playwright instances - use BrowserSession
- ❌ Implement retry logic - import from `src/resilience/`
- ❌ Create new logging infrastructure - import from `src/observability/`
- ❌ Create browser sessions - receive context from outside
- ❌ Hardcode timeout values - use Pydantic validation
- ❌ Skip type annotations (MyPy strict mode)
- ❌ Duplicate config loading - extend Story 1.1 loader

---

## File Implementation Order

1. **`src/stealth/cloudflare/exceptions/__init__.py`** - Add `ChallengeTimeoutError`
2. **`src/stealth/cloudflare/models/config.py`** - Add `challenge_timeout` field (default=30)
3. **`src/stealth/cloudflare/config/schema.py`** - Add timeout validation (5-300 seconds)
4. **`src/stealth/cloudflare/config/flags.py`** - Add timeout flag handling
5. **`src/stealth/cloudflare/config/loader.py`** - Add timeout field loading
6. **`src/stealth/cloudflare/core/__init__.py`** - Core module exports
7. **`src/stealth/cloudflare/core/waiter.py`** - Challenge wait logic with timeout

---

## Testing Requirements

- **Unit Tests:** For config loading, validation, and timeout logic
- **Test Fixtures:** Sample YAML configs with various timeout values
- **pytest markers:** `@pytest.mark.unit`, `@pytest.mark.integration`
- **asyncio_mode=auto** for async test support
- **Mock Patterns:** Use pytest-mock for external dependencies
- **Edge Cases:** Test timeout boundary values (5, 30, 300 seconds)
- **Error Cases:** Test invalid timeout values

---

## Project Context Reference

### From project-context.md

- Technology: Python 3.11+, Playwright >=1.40.0, Pydantic >=2.5.0
- Async/Await: All I/O operations must use `async def`
- Module Integration: Use dependency injection via module interfaces
- Type Safety: MyPy strict mode required
- Code Quality: Black (88 char), Ruff, MyPy strict

### From architecture.md

- SCR-003 sub-module pattern required
- Integration with existing resilience/observability systems
- Read-only browser context integration
- Multi-signal detection approach (future stories)

### From Story 1.1 (Prerequisite)

This story extends the config system from Story 1.1:
- Re-use `CloudflareConfig` model - add `challenge_timeout` field
- Re-use config loader - add timeout field parsing
- Re-use Pydantic schema - add timeout validation

---

## Success Criteria

1. Site modules can configure `challenge_timeout: <seconds>` in YAML
2. Default timeout of 30 seconds is applied when not specified
3. Invalid timeout values (< 5 or > 300) raise validation errors
4. Challenge wait logic respects configured timeout
5. Timeout events are logged via observability system
6. All tests pass with async support
7. Code follows Black formatting and MyPy strict mode

---

## Dev Notes

### Priority

This is the **second story** in Epic 1. It extends the config system from Story 1.1:
- Story 1.1 established the base config with `cloudflare_protected` flag
- Story 1.2 adds `challenge_timeout` configuration
- Story 1.3 will add detection sensitivity configuration
- Epic 4 (Resilience) will use these timeout settings for wait logic

### Integration Points

- **With Story 1.1:** Extend existing config models and loaders
- **With Epic 4 (Story 4.1):** Provide timeout configuration for automatic challenge wait
- **With Epic 3 (Challenge Detection):** Timeout applies to challenge detection wait

### Technical Considerations

1. Timeout should be configurable per-site to handle varying Cloudflare challenge times
2. Default 30 seconds aligns with NFR1 (Challenge Wait Time < 30 seconds)
3. Range 5-300 seconds prevents misconfiguration while allowing flexibility
4. Use existing observability for timeout event logging

---

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Section-5]
- [Source: _bmad-output/planning-artifacts/prd.md#FR2]
- [Source: _bmad-output/planning-artifacts/prd.md#NFR1]
- [Source: _bmad-output/implementation-artifacts/1-1-yaml-cloudflare-flag-configuration.md]
- [Source: _bmad-output/project-context.md]

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

N/A - Story implementation pending

### Completion Notes List

- [ ] Add challenge_timeout field to CloudflareConfig model
- [ ] Add timeout validation to Pydantic schema
- [ ] Update config loader to parse timeout field
- [ ] Implement ChallengeWaiter with timeout logic
- [ ] Add ChallengeTimeoutError exception
- [ ] Write unit tests for timeout configuration
- [ ] Write unit tests for wait logic
- [ ] Validate Black formatting
- [ ] Run MyPy type check

### File List

```
src/stealth/cloudflare/__init__.py                           # Already exists
src/stealth/cloudflare/config/__init__.py                     # Already exists
src/stealth/cloudflare/config/loader.py                       # Modify - add timeout
src/stealth/cloudflare/config/flags.py                        # Modify - add timeout handling
src/stealth/cloudflare/config/schema.py                       # Modify - add validation
src/stealth/cloudflare/models/__init__.py                     # Already exists
src/stealth/cloudflare/models/config.py                       # Modify - add field
src/stealth/cloudflare/exceptions/__init__.py                  # Modify - add TimeoutError
src/stealth/cloudflare/core/__init__.py                        # NEW
src/stealth/cloudflare/core/waiter.py                          # NEW
tests/unit/test_cloudflare_config.py                           # Modify - add tests
```
