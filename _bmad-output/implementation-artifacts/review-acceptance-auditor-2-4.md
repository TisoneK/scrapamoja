# Acceptance Auditor Review - Story 2-4-viewport-normalization

**Review Mode:** Full (spec file provided)

**Instructions:**
You are an Acceptance Auditor. Review this diff against the spec and context docs. Check for:
- Violations of acceptance criteria
- Deviations from spec intent
- Missing implementation of specified behavior
- Contradictions between spec constraints and actual code

## Spec File Content

**Story:** 2-4-viewport-normalization
**Epic:** 2 - Stealth/Browser Fingerprinting

### Technical Requirements from Spec

**Core Functionality:**
- ✅ Implement ViewportNormalizer class in `src/stealth/cloudflare/core/viewport/normalizer.py`
- ✅ Create viewport dimension pool with common screen resolutions
- ✅ Integrate with existing Cloudflare stealth system
- ✅ Ensure viewport is applied during browser context creation

**Integration Points:**
- ✅ Extend CloudflareConfig model to include viewport settings
- ✅ Integrate with existing stealth modules from stories 2-1, 2-2, 2-3
- ✅ Hook into browser context creation pipeline
- ✅ Coordinate with user agent rotation for consistent device profiles

**Configuration:**
- ✅ Add viewport configuration options to CloudflareConfig
- ✅ Support custom viewport dimension pools
- ✅ Enable/disable viewport normalization via CloudflareConfig flag

### Architecture Compliance (SCR-003)

**MUST follow sub-module pattern:**
```
src/stealth/cloudflare/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── webdriver/      (Story 2.1)
│   ├── fingerprint/    (Story 2.2)
│   ├── user_agent/     (Story 2.3)
│   └── viewport/        (Story 2.4) ✅
```

**CRITICAL: Use existing systems - DO NOT recreate functionality:**
1. ✅ **Resilience Engine:** Import retry mechanisms from `src/resilience/` - NO new retry implementation
2. ✅ **Observability Stack:** Import structured logging from `src/observability/` - NO new logging infrastructure
3. ✅ **Stealth Module:** Extend existing `src/stealth/cloudflare/` for browser fingerprinting
4. ✅ **Browser Context:** Read-only integration - receives context, doesn't create sessions
5. ✅ **Config System:** Reuse CloudflareConfig from Epic 1 stories

### Module Structure Required
```
src/stealth/cloudflare/core/viewport/
├── __init__.py       ✅ CREATED
└── normalizer.py     ✅ CREATED (ViewportNormalizer class)
```

### DO NOT (from spec)
- ❌ Create raw Playwright instances - use BrowserSession
- ❌ Implement retry logic - import from `src/resilience/`
- ❌ Create new logging infrastructure - import from `src/observability/`
- ❌ Create browser sessions - receive context from outside
- ❌ Hardcode configuration values - use Pydantic validation
- ❌ Skip type annotations (MyPy strict mode)

### MUST (from spec)
- ✅ Use `src/stealth/cloudflare/core/viewport/` structure
- ✅ Extend CloudflareConfig from Epic 1
- ✅ Import from `src/resilience/` for retry patterns
- ✅ Import from `src/observability/` for logging
- ✅ Use async/await patterns throughout
- ✅ Follow SCR-003 module pattern exactly

### Viewport Dimension Pool Requirements
- 1920x1080 (Full HD) - 35% weight ✅
- 1366x768 (HD) - 25% weight ✅
- 1440x900 (WXGA+) - 15% weight ✅
- 1536x864 (HD+) - 10% weight ✅
- 1280x720 (HD) - 8% weight ✅
- 1600x900 (HD+) - 7% weight ✅
- Weighted random selection based on usage statistics ✅
- Ensure variation between sessions ✅
- Cache selected dimension for session consistency ✅

## Diff to Review

```diff
--- NEW FILE: src/stealth/cloudflare/core/viewport/__init__.py
+"""Viewport normalization module.
+...
+from src.stealth.cloudflare.core.viewport.normalizer import ViewportNormalizer
+__all__ = ["ViewportNormalizer"]

--- NEW FILE: src/stealth/cloudflare/core/viewport/normalizer.py
+(Full implementation of ViewportNormalizer and ViewportDimension classes)

--- MODIFIED: src/stealth/cloudflare/core/__init__.py
+(Added ViewportNormalizer export)

--- MODIFIED: src/stealth/cloudflare/exceptions/__init__.py
+(Added ViewportNormalizationError exception)

--- NEW FILE: tests/unit/test_cloudflare_viewport.py
+(23 unit tests - all passing)
```

**Output Format:**
Provide findings as a markdown list. Each finding should include:
- One-line title describing the issue
- Which AC/constraint it violates
- Evidence from the diff
- Suggested fix (if applicable)

If no issues found, state "No issues found" clearly.
