# Story 1.3: Detection Sensitivity Configuration

**Status:** ready-for-dev

**Epic:** 1 - Configuration Management
**Story Key:** 1-3-detection-sensitivity-configuration
**Generated:** 2026-03-19T10:31:07Z

---

## Story Overview

**User Story Statement:**

As a Site Module Developer,
I want to adjust detection sensitivity levels,
So that I can balance between false positives and false negatives.

**Business Value:** Allows fine-tuning of challenge detection to match site-specific behavior, reducing false positives on legitimate sites and improving detection rate on challenging Cloudflare-protected sites.

---

## Acceptance Criteria

### AC1: String-Based Sensitivity Configuration

**Given** a site module with `cloudflare_protected: true`
**When** I configure `detection_sensitivity: high|medium|low`
**Then** the configuration accepts string values (case-insensitive)
**And** high = 5, medium = 3, low = 1 internally

### AC2: Numeric Sensitivity Configuration (Backward Compatibility)

**Given** a site module with `cloudflare_protected: true`
**When** I configure `detection_sensitivity: 1-5` (numeric)
**Then** the configuration accepts integer values 1-5
**And** maintains backward compatibility with existing configs

### AC3: Sensitivity Mapping Logic

**Given** a detection_sensitivity value
**When** the value is parsed
**Then** the mapping is:
  - `high` (or 4-5): Maximum detection, more challenges detected, higher false positive risk
  - `medium` (or 3): Balanced detection, default recommendation
  - `low` (or 1-2): Conservative detection, fewer false positives, may miss edge cases

### AC4: Default Sensitivity

**Given** no detection_sensitivity configuration
**Then** the default sensitivity of "medium" (3) is applied
**And** documented as the recommended setting

### AC5: Sensitivity Integration with Detection

**Given** a valid detection_sensitivity configuration
**Then** the sensitivity value is passed to detection modules
**And** detection thresholds are adjusted based on sensitivity level

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

For Story 1.3, extend the existing config structure from Stories 1.1 and 1.2:

```
src/stealth/cloudflare/
├── __init__.py                    # Already exists (Story 1.1)
├── config/
│   ├── __init__.py                # Already exists (Story 1.1)
│   ├── loader.py                  # Already exists (Story 1.1) - Add sensitivity parsing
│   ├── flags.py                   # Already exists (Story 1.1) - Update for string support
│   └── schema.py                 # Already exists (Story 1.1) - Add string validation
├── models/
│   ├── __init__.py                # Already exists (Story 1.1)
│   ├── config.py                  # Already exists (Story 1.1) - Add string support
│   └── sensitivity.py              # NEW: Sensitivity level enum and mapping
├── core/                          # Already exists (Story 1.2)
│   ├── __init__.py                # Already exists (Story 1.2)
│   └── waiter.py                  # Already exists (Story 1.2)
└── exceptions/
    └── __init__.py                # Already exists (Story 1.1) - Add SensitivityError
```

### New Files to Create

1. `src/stealth/cloudflare/models/sensitivity.py` - Sensitivity level enum and mapping logic
2. `src/stealth/cloudflare/exceptions/__init__.py` - Add `SensitivityConfigurationError` (if not exists)

### Files to Modify

1. `src/stealth/cloudflare/models/config.py` - Add string value support for detection_sensitivity
2. `src/stealth/cloudflare/config/schema.py` - Add string validation for "high", "medium", "low"
3. `src/stealth/cloudflare/config/flags.py` - Add string-to-integer mapping logic
4. `src/stealth/cloudflare/config/loader.py` - Add string sensitivity parsing (if applicable)

---

## Developer Guardrails

### DO

- ✅ Use async/await patterns for all I/O operations
- ✅ Implement `__aenter__`/`__aexit__` for resource managers
- ✅ Use dependency injection via module interfaces
- ✅ Import from existing systems (resilience, observability)
- ✅ Use Pydantic models for configuration validation
- ✅ Follow project-context.md naming conventions:
  - Classes: PascalCase (e.g., `SensitivityLevel`, `SensitivityMapper`)
  - Functions/Variables: snake_case (e.g., `map_sensitivity_level()`)
  - Constants: UPPER_SNAKE_CASE
  - Modules: snake_case
- ✅ Use MyPy strict mode with type annotations
- ✅ Import browser context read-only (NOT for session creation)
- ✅ Follow Black formatting (88 char limit)
- ✅ Re-use Stories 1.1 and 1.2 patterns for config extension
- ✅ Handle both string ("high"|"medium"|"low") and numeric (1-5) values

### DO NOT

- ❌ Create raw Playwright instances - use BrowserSession
- ❌ Implement retry logic - import from `src/resilience/`
- ❌ Create new logging infrastructure - import from `src/observability/`
- ❌ Create browser sessions - receive context from outside
- ❌ Hardcode sensitivity values - use Pydantic validation
- ❌ Skip type annotations (MyPy strict mode)
- ❌ Duplicate config loading - extend existing loader
- ❌ Implement actual detection logic in this story - just the configuration

---

## File Implementation Order

1. **`src/stealth/cloudflare/models/sensitivity.py`** - Create sensitivity enum and mapping
2. **`src/stealth/cloudflare/models/config.py`** - Add string value support
3. **`src/stealth/cloudflare/config/schema.py`** - Add string validation ("high", "medium", "low")
4. **`src/stealth/cloudflare/config/flags.py`** - Add string-to-integer mapping
5. **`src/stealth/cloudflare/config/loader.py`** - Add string sensitivity parsing (if needed)
6. **`tests/unit/test_cloudflare_config.py`** - Add sensitivity tests

---

## Testing Requirements

- **Unit Tests:** For sensitivity mapping, string validation, and config loading
- **Test Fixtures:** Sample YAML configs with various sensitivity values ("high", "medium", "low", 1, 3, 5)
- **pytest markers:** `@pytest.mark.unit`, `@pytest.mark.integration`
- **asyncio_mode=auto** for async test support
- **Mock Patterns:** Use pytest-mock for external dependencies
- **Edge Cases:** Test invalid string values, boundary numeric values, case insensitivity
- **Error Cases:** Test invalid sensitivity values (< 1, > 5, invalid strings)

---

## Previous Story Intelligence

### From Story 1.2 (Challenge Wait Timeout Configuration)

- Established the base config system with Pydantic models
- Created `ChallengeWaiter` in `src/stealth/cloudflare/core/waiter.py`
- Extended `CloudflareConfig` model with `challenge_timeout` field
- Created validation in schema.py for timeout values (5-300 seconds)
- Pattern: Add field → Add validation → Add to config model → Add to flags → Add tests

### Key Learnings from Story 1.2

1. The config extension pattern is: field in model → validation in schema → parsing in flags
2. Story 1.3 should follow the same pattern but add string value support
3. The sensitivity mapper should be a separate module for clarity

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
- Multi-signal detection approach (future stories - Epic 3)
- Detection sensitivity thresholds will be used by detection modules

### From Story 1.1 (YAML Flag Configuration)

- Established base config with `cloudflare_protected` flag
- Created `CloudflareConfig` model in `src/stealth/cloudflare/models/config.py`
- Created flag handling in `src/stealth/cloudflare/config/flags.py`

---

## Success Criteria

1. Site modules can configure `detection_sensitivity: high|medium|low` in YAML
2. Site modules can configure `detection_sensitivity: 1-5` (backward compatibility)
3. Default sensitivity of "medium" (3) is applied when not specified
4. Invalid values ("invalid", 0, 6) raise validation errors
5. String values are case-insensitive ("HIGH", "High", "high" all valid)
6. Sensitivity mapping logic correctly converts string to numeric
7. All tests pass with async support
8. Code follows Black formatting and MyPy strict mode

---

## Dev Notes

### Priority

This is the **third story** in Epic 1 (Configuration Management):
- Story 1.1 established the base config with `cloudflare_protected` flag
- Story 1.2 added `challenge_timeout` configuration
- Story 1.3 adds `detection_sensitivity` configuration
- Epic 3 (Challenge Detection) will use these sensitivity settings

### Technical Gap Analysis

**Current Implementation State:**
- `detection_sensitivity` field exists in config model (1-5 numeric only)
- Schema validation for numeric range (1-5) already exists
- **MISSING:** String value support ("high", "medium", "low")
- **MISSING:** Sensitivity mapper/converter logic
- **MISSING:** Integration with detection modules (future Epic 3)

### What This Story Must Implement

1. **String value support** - Allow YAML config like `detection_sensitivity: high`
2. **Mapping logic** - Convert string to numeric (high=5, medium=3, low=1)
3. **Validation** - Accept both string and numeric values
4. **Backward compatibility** - Numeric values still work

### What This Story Must NOT Implement

1. Actual challenge detection logic - that's Epic 3
2. Detection threshold adjustments - that's Epic 3
3. Integration with detection modules - that's Epic 3

### Integration Points

- **With Story 1.1:** Re-use config model, flags, schema patterns
- **With Story 1.2:** Re-use config extension pattern
- **With Epic 3 (Challenge Detection):** Provide sensitivity configuration for detection thresholds

### Technical Considerations

1. Sensitivity should be configurable per-site to handle varying Cloudflare configurations
2. Default "medium" (3) aligns with balanced detection approach
3. String values improve UX - developers don't need to know numeric thresholds
4. Use enum for type safety: `SensitivityLevel.HIGH`, `SensitivityLevel.MEDIUM`, `SensitivityLevel.LOW`

---

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Section-5]
- [Source: _bmad-output/planning-artifacts/prd.md#FR3]
- [Source: _bmad-output/planning-artifacts/prd.md#NFR3]
- [Source: _bmad-output/implementation-artifacts/1-1-yaml-cloudflare-flag-configuration.md]
- [Source: _bmad-output/implementation-artifacts/1-2-challenge-wait-timeout-configuration.md]
- [Source: _bmad-output/project-context.md]

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

N/A - Story implementation pending

### Completion Notes List

- [ ] Add SensitivityLevel enum to models/sensitivity.py
- [ ] Add sensitivity mapper function (string to numeric)
- [ ] Update CloudflareConfig model for string value support
- [ ] Update schema.py for string validation ("high", "medium", "low")
- [ ] Update flags.py for string-to-integer mapping
- [ ] Add unit tests for sensitivity configuration
- [ ] Add unit tests for sensitivity mapping
- [ ] Validate Black formatting
- [ ] Run MyPy type check

### File List

```
src/stealth/cloudflare/__init__.py                           # Already exists
src/stealth/cloudflare/config/__init__.py                     # Already exists
src/stealth/cloudflare/config/loader.py                       # Modify - add string parsing
src/stealth/cloudflare/config/flags.py                        # Modify - add string mapping
src/stealth/cloudflare/config/schema.py                       # Modify - add string validation
src/stealth/cloudflare/models/__init__.py                     # Already exists
src/stealth/cloudflare/models/config.py                       # Modify - add string support
src/stealth/cloudflare/models/sensitivity.py                   # NEW - sensitivity enum/mapper
src/stealth/cloudflare/exceptions/__init__.py                  # Modify - add error (if needed)
src/stealth/cloudflare/core/__init__.py                        # Already exists
src/stealth/cloudflare/core/waiter.py                          # Already exists
tests/unit/test_cloudflare_config.py                           # Modify - add tests
```
