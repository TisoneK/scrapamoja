# Story 1.1: YAML Cloudflare Flag Configuration

**Status:** review

**Epic:** 1 - Configuration Management
**Story Key:** 1-1-yaml-cloudflare-flag-configuration
**Generated:** 2026-03-18T20:11:47Z

---

## Story Overview

**User Story Statement:**

As a Site Module Developer,
I want to enable Cloudflare protection with a simple YAML flag,
So that I can quickly configure sites without writing custom code.

**Business Value:** Simple configuration-driven approach to enable Cloudflare bypass without code changes.

---

## Acceptance Criteria

### AC1: Flag Activation

**Given** a site module YAML configuration file
**When** I set `cloudflare_protected: true`
**Then** the framework activates all Cloudflare bypass mechanisms
**And** the site is processed with stealth configuration, challenge detection, and retry logic

### AC2: Flag Deactivation

**Given** a site module YAML configuration file
**When** I set `cloudflare_protected: false` or omit the flag
**Then** no Cloudflare-specific processing is applied
**And** existing non-Cloudflare site modules remain completely unaffected

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

For Story 1.1, implement the following structure under `src/stealth/cloudflare/`:

```
src/stealth/cloudflare/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── loader.py       # YAML config loading
│   ├── flags.py        # cloudflare_protected flag handling
│   └── schema.py       # Pydantic validation
├── models/
│   ├── __init__.py
│   └── config.py       # CloudflareConfig model
└── exceptions/
    └── __init__.py
```

---

## Developer Guardrails

### DO

- ✅ Use async/await patterns for all I/O operations
- ✅ Implement `__aenter__`/`__aexit__` for resource managers
- ✅ Use dependency injection via module interfaces
- ✅ Import from existing systems (resilience, observability)
- ✅ Use Pydantic models for configuration validation
- ✅ Follow project-context.md naming conventions:
  - Classes: PascalCase (e.g., `CloudflareConfig`)
  - Functions/Variables: snake_case (e.g., `load_config()`)
  - Constants: UPPER_SNAKE_CASE
  - Modules: snake_case
- ✅ Use MyPy strict mode with type annotations
- ✅ Import browser context read-only (NOT for session creation)
- ✅ Follow Black formatting (88 char limit)

### DO NOT

- ❌ Create raw Playwright instances - use BrowserSession
- ❌ Implement retry logic - import from `src/resilience/`
- ❌ Create new logging infrastructure - import from `src/observability/`
- ❌ Create browser sessions - receive context from outside
- ❌ Hardcode configuration values - use Pydantic validation
- ❌ Skip type annotations (MyPy strict mode)

---

## File Implementation Order

1. **`src/stealth/cloudflare/__init__.py`** - Module exports
2. **`src/stealth/cloudflare/exceptions/__init__.py`** - Exception classes
3. **`src/stealth/cloudflare/models/__init__.py`** - Data models
4. **`src/stealth/cloudflare/models/config.py`** - CloudflareConfig Pydantic model
5. **`src/stealth/cloudflare/config/__init__.py`** - Config module exports
6. **`src/stealth/cloudflare/config/schema.py`** - Pydantic validation schema
7. **`src/stealth/cloudflare/config/flags.py`** - Flag handling logic
8. **`src/stealth/cloudflare/config/loader.py`** - YAML config loading

---

## Testing Requirements

- **Unit Tests:** For config loading and validation in `tests/`
- **Test Fixtures:** Sample YAML configs for testing
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

### From architecture.md

- SCR-003 sub-module pattern required
- Integration with existing resilience/observability systems
- Read-only browser context integration
- Multi-signal detection approach (future stories)

---

## Success Criteria

1. Site modules can enable Cloudflare protection with `cloudflare_protected: true` in YAML
2. Configuration is validated via Pydantic models
3. Non-Cloudflare sites remain unaffected
4. Module integrates with existing Scrapamoja framework patterns
5. All tests pass with async support
6. Code follows Black formatting and MyPy strict mode

---

## Dev Notes

### Priority

This is the **first story** in Epic 1. Establish the foundation for all subsequent stories:
- Story 1.2 will extend with timeout configuration
- Story 1.3 will add sensitivity configuration
- Later epics depend on this config system

### Next Stories Context

- **Story 1.2:** Challenge Wait Timeout Configuration - extends config with `challenge_timeout` field
- **Story 1.3:** Detection Sensitivity Configuration - extends config with `detection_sensitivity` field
- **Epic 2:** Uses config to enable stealth profiles
- **Epic 3:** Uses config for challenge detection settings

---

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Section-5]
- [Source: _bmad-output/planning-artifacts/prd.md#FR1]
- [Source: _bmad-output/project-context.md]

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

N/A - First story

### Completion Notes List

- [x] Implement config module structure
- [x] Create Pydantic validation schema
- [x] Implement YAML flag loading
- [x] Add unit tests
- [x] Validate Black formatting
- [x] Run MyPy type check

### File List

```
src/stealth/cloudflare/__init__.py
src/stealth/cloudflare/config/__init__.py
src/stealth/cloudflare/config/loader.py
src/stealth/cloudflare/config/flags.py
src/stealth/cloudflare/config/schema.py
src/stealth/cloudflare/models/__init__.py
src/stealth/cloudflare/models/config.py
src/stealth/cloudflare/exceptions/__init__.py
tests/unit/test_cloudflare_config.py
```
