---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/product-brief-scrapamoja-2026-03-14.md
  - _bmad-output/project-context.md
workflowType: 'architecture'
project_name: 'scrapamoja'
user_name: 'Tisone'
date: '2026-03-14'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
- Network Interception Core: FR1-FR4 - pattern registration, handler callback, response metadata capture, raw bytes delivery
- Pattern Matching: FR5-FR8 - string prefix/substring matching, optional regex, validation at construction
- Lifecycle Management: FR9-FR12 - attach/detach, timing validation, late detach handling
- Error Handling: FR13-FR17 - bodyless responses, handler isolation, dev logging, pattern mismatch warnings
- Response Capture: FR18-FR21 - status, headers, raw bytes, race condition handling
- Developer Experience: FR22-FR24 - zero Playwright knowledge required, clear errors

**Non-Functional Requirements:**
- Integration: Playwright compatibility, downstream module contract (CapturedResponse usable by SCR-004/005)
- Reliability: Failure isolation (no crashes), resource cleanup, deterministic behavior
- Maintainability: Interface stability (public API locked), debuggability, documented failure modes
- Testability: Mockable page interface, isolated failure mode testing, 100% failure mode coverage

### Scale & Complexity

- Primary domain: Developer Tool (SDK/library/framework)
- Complexity level: Medium
- Estimated architectural components: 2-3 (NetworkInterceptor class, CapturedResponse dataclass, handler callback system)

### Technical Constraints & Dependencies

- Playwright >=1.40.0 for network event API
- Integration with existing module boundary model: receives page from src/browser/, delivers to src/encodings/
- Python 3.11+ with async architecture requirement
- 45 AI agent rules from project-context.md define implementation patterns

### Cross-Cutting Concerns Identified

- Error propagation: interceptor errors must not propagate to calling site module
- Resource lifecycle: proper cleanup in interrupt handling scenarios
- Interface stability: public API (NetworkInterceptor, CapturedResponse) must remain stable for future site modules

## Starter Template Evaluation

### Project Type Context

**Brownfield Project:** Feature addition to existing Scrapamoja framework
- Project exists with established structure and patterns
- Adding SCR-002 Network Response Interception module to existing codebase
- Not a new project requiring starter template - foundation already established

### Technology Foundation (Already Defined)

**Language & Runtime:**
- Python 3.11+ with asyncio-first architecture
- All I/O operations must use `async def`
- Implement `__aenter__`/`__aexit__` for resource managers

**Browser Automation:**
- Playwright >=1.40.0 (browser automation)
- Use BrowserSession for all browser operations - NEVER create raw Playwright instances
- Integration with existing stealth configuration patterns

**Key Dependencies:**
- Structured logging: Structlog >=23.2.0
- Data validation: Pydantic >=2.5.0
- Testing: pytest >=7.4.0 with asyncio_mode=auto

### Module Architecture Context

**Existing Module Boundary Model:**
- Receives page from `src/browser/`
- Delivers raw bytes to `src/encodings/`
- Site modules consume without knowing Playwright exists

**Established Patterns to Follow:**
- Dependency injection via module interfaces (`src/*/interfaces.py`)
- Custom exceptions per module (NetworkError, etc.)
- Structured logging with correlation IDs
- Resource monitoring from browser management system

### Architectural Decisions Context

Since this is a brownfield project adding a new module, the "starter" decisions are already made by:
1. The existing project structure in `src/`
2. The 45 AI agent rules in project-context.md
3. The established patterns from existing modules (FlashScore, Wikipedia)

**Next Architectural Decisions Will Focus On:**
- Where SCR-002 fits in the module structure (`src/network/`)
- Interface design for site module developers
- Integration points with existing browser and encoding modules
- Error handling patterns matching the framework

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Module location: `src/network/` (replaces existing interception.py)
- Interface design: NetworkInterceptor class with locked API
- Storage pattern: callback-only (no in-memory list storage)
- Pattern matching: string prefix/substring default, regex optional

**Important Decisions (Shape Architecture):**
- Error handling: reuse NetworkError, add TimingError and PatternError
- Response dataclass: CapturedResponse with raw_bytes field (not body)
- Constructor args: patterns, handler, dev_logging (not config object)

**Deferred Decisions (Post-MVP):**
- WebSocket frame interception
- Multiple interceptors on same page
- Auto-deduplication

### Module Architecture

**Location:** `src/network/` - replaces existing `interception.py`

**Rationale:** The existing `src/network/interception.py` was created prematurely during SCR-001 implementation (scope creep) before SCR-002's design was finalized. It conflicts with locked PRD decisions:
- Storage: list-based vs callback-only
- Patterns: regex default vs string prefix default
- Field naming: body vs raw_bytes

SCR-002 will supersede this file entirely.

### Interface Design

**NetworkInterceptor Class:**
```python
class NetworkInterceptor:
    def __init__(
        self,
        patterns: list[str],
        handler: Callable[[CapturedResponse], Awaitable[None]],
        dev_logging: bool = False
    ): ...
    
    async def attach(self, page: Any) -> None: ...
    async def detach(self) -> None: ...
```

**Constructor Args (Locked):**
- `patterns: list[str]` - URL patterns to match
- `handler: Callable` - async callback for captured responses
- `dev_logging: bool` - optional debug logging flag

**Not a config object** - args are direct constructor parameters as specified in PRD.

### Response Data Structure

**CapturedResponse Dataclass:**
```python
@dataclass
class CapturedResponse:
    url: str                          # Request URL
    status: int                      # HTTP status code
    headers: dict[str, str]           # Response headers
    raw_bytes: bytes | None          # Raw response body (NOT "body")
```

**Field naming:** `raw_bytes` specifically signals raw bytes, not decoded content. This differentiates from the existing implementation's `body` field.

### Storage Pattern

**Callback-Only (Locked):**
- No `get_captured_responses()` list storage
- Handler callback invoked for each matched response
- Caller manages response storage/processing

**Rationale:** PRD explicitly rejected in-memory list storage. The callback pattern ensures:
- No memory accumulation during long-running scrapes
- Caller controls response processing and storage
- Simpler interceptor implementation

### Pattern Matching

**Default: String Prefix/Substring (Locked):**
- String prefix matching by default
- Substring matching available
- One optional regex per interceptor instance

**Validation:** Pattern validation at construction time with clear errors for invalid input

### Error Handling

**Reuse:** `NetworkError` from `src/network/errors.py` (module="interception")

**New Exceptions:**
- `TimingError` - raised when attach() is called after page.goto()
- `PatternError` - raised for invalid pattern input at construction time

### Testing Approach

- Mock Playwright page interface
- Isolated failure mode testing (bodyless responses, handler exceptions, timing violations, race conditions)
- 100% failure mode coverage target

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points:** 5 areas where AI agents could make different choices

### Naming Patterns (from Project Context)

**Code Naming (Follow existing):**
- Classes: PascalCase (`NetworkInterceptor`, `CapturedResponse`)
- Functions/variables: snake_case (`attach`, `dev_logging`, `raw_bytes`)
- Constants: UPPER_SNAKE_CASE
- Modules: snake_case

**Field Naming (SCR-002 Specific):**
- Response body field: `raw_bytes` (NOT "body") - signals raw bytes, not decoded content
- URL field: `url` (lowercase)
- Status field: `status` (not "status_code" for the response object)

### Module Structure

**Directory:** `src/network/interception/` (replaces existing `interception.py`)

**Internal Structure:**
```
src/network/interception/
├── __init__.py        # Public API exports
├── interceptor.py     # NetworkInterceptor class
├── models.py          # CapturedResponse, config models
├── exceptions.py      # TimingError, PatternError
└── patterns.py        # Pattern matching logic (isolated for testing)
```

**Rationale:**
- Follows `direct_api/` module pattern
- `patterns.py` isolated for independent unit testing (not tied to interceptor instantiation)
- `__init__.py` provides clean public API

### Data Class Patterns

**CapturedResponse:**
```python
@dataclass
class CapturedResponse:
    url: str                          # Request URL
    status: int                      # HTTP status code
    headers: dict[str, str]           # Response headers
    raw_bytes: bytes | None           # Raw response body (NOT "body")
```

**Naming rationale:** `raw_bytes` specifically signals raw bytes vs decoded content, differentiating from the deprecated implementation's `body` field.

### Exception Patterns

**Reuse existing:**
- `NetworkError` from `src/network/errors.py` (module="interception")

**New exceptions:**
```python
# src/network/interception/exceptions.py
class TimingError(Exception):
    """Raised when attach() is called after page.goto()."""
    pass

class PatternError(Exception):
    """Raised for invalid pattern input at construction time."""
    pass
```

**Pattern:** Custom exceptions per module (follows project-context rule)

### Testing Patterns

**Location:** `tests/` (not co-located)

**Framework:** pytest with asyncio_mode=auto

**Mock Pattern:**
- Mock Playwright page interface (duck typing, not inheritance)
- Mock response objects for pattern matching tests

**Isolation:**
- `patterns.py` tested independently without full interceptor
- Failure modes tested in isolation:
  - Bodyless responses (204, 301, 304)
  - Handler exceptions
  - Timing violations
  - Race conditions

### Logging Patterns

**Library:** Structlog (as per project-context)

**Pattern:**
- Use correlation IDs from observability stack
- Log levels: debug for captured responses, warning for failures
- Dev logging mode: optional verbose logging (off by default)

### API Surface Pattern

**Constructor:**
```python
class NetworkInterceptor:
    def __init__(
        self,
        patterns: list[str],           # NOT a config object
        handler: Callable[[CapturedResponse], Awaitable[None]],
        dev_logging: bool = False
    ): ...
```

**Direct args** (not config object) - as locked in PRD

### Enforcement Guidelines

**All AI Agents MUST:**
- Use `src/network/interception/` directory structure
- Name response body field `raw_bytes` (NOT "body")
- Put pattern matching in `patterns.py` for isolation
- Use pytest with asyncio_mode=auto
- Follow existing naming conventions (PascalCase, snake_case, UPPER_SNAKE_CASE)
- Include type annotations (MyPy strict mode)
- Add docstrings to all public classes and functions

**Anti-Patterns to Avoid:**
- NOT `get_captured_responses()` list storage (callback-only)
- NOT regex-by-default patterns (string prefix default)
- NOT using "body" field name (use "raw_bytes")
- NOT creating separate interceptor files at `src/network/` level

## Project Structure & Boundaries

### Complete Project Directory Structure

**SCR-002 Module Location:**
```
src/network/interception/          # NEW - replaces src/network/interception.py
├── __init__.py                    # Exports: NetworkInterceptor, CapturedResponse
├── interceptor.py                 # NetworkInterceptor class
├── models.py                      # CapturedResponse dataclass, pattern validation
├── exceptions.py                 # TimingError, PatternError
└── patterns.py                   # Pattern matching logic (isolated for testing)
```

**Tests:**
```
tests/unit/network/interception/
├── test_patterns.py              # Isolated pattern matching tests
├── test_interceptor.py           # Full interceptor tests
├── test_exceptions.py            # Exception tests
└── test_models.py                # CapturedResponse dataclass tests

tests/integration/network/
└── test_interception_integration.py  # Real browser, real SPA target (NFR requirement)
```

**Existing Files Affected:**
- `src/network/interception.py` - TO BE REMOVED (replaced by directory)

### Architectural Boundaries

**Input Boundary:**
- Receives raw Playwright `page` object from caller (site module)
- Caller responsible for page lifecycle (BrowserSession management)
- Attaches via `attach(page)` BEFORE `page.goto()`

**Output Boundary:**
- Delivers `CapturedResponse` via handler callback to caller
- No storage - caller manages response storage/processing
- Callback-only pattern (no list accumulation)

**Error Boundary:**
- Uses `NetworkError` from `src/network/errors.py` (module="interception")
- New exceptions: `TimingError`, `PatternError`
- Errors do NOT propagate to caller (handled internally)

**Logging Boundary:**
- Uses structlog (project standard)
- Correlation IDs from observability stack
- Dev logging mode: optional verbose output

### Requirements to Structure Mapping

**Functional Requirements Mapping:**
- FR1-FR4 (Network Interception Core) → `interceptor.py`
- FR5-FR8 (Pattern Matching) → `patterns.py`, `models.py`
- FR9-FR12 (Lifecycle Management) → `interceptor.py` attach/detach
- FR13-FR17 (Error Handling) → `exceptions.py`, `interceptor.py`
- FR18-FR21 (Response Capture) → `models.py` CapturedResponse
- FR22-FR24 (Developer Experience) → `__init__.py` clean API

**Non-Functional Requirements:**
- Integration (Playwright) → `interceptor.py`
- Reliability (failure isolation) → `interceptor.py`, `exceptions.py`
- Maintainability (interface stability) → `__init__.py` locked API
- Testability (mockable) → `patterns.py` isolated, `test_*.py` files

### Integration Points

**Internal Communication:**
- Site module → NetworkInterceptor: page object, patterns, handler
- NetworkInterceptor → Site module: CapturedResponse via callback
- NetworkInterceptor → src/network/errors.py: NetworkError

**External Integrations:**
- Playwright page object (raw, not BrowserSession)
- No external APIs (internal module)

**Data Flow:**
```
Site Module
    │
    ├──patterns + handler
    ▼
NetworkInterceptor.attach(page)
    │
    ├──page.goto()
    ▼
Playwright Response Events
    │
    ▼
Pattern Matching (patterns.py)
    │
    ▼
Handler Callback → Site Module
    (CapturedResponse)
```

### File Organization Patterns

**Source Organization:**
- Follows `src/module_name/` pattern (project-context rule)
- `__init__.py` provides clean public API
- Separate files for models, exceptions, core logic

**Test Organization:**
- Unit tests in `tests/unit/network/interception/`
- Integration tests in `tests/integration/network/`
- pytest with asyncio_mode=auto (project standard)

**Removed Files:**
- `src/network/interception.py` - deprecated, supersceded by directory

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- Python 3.11+ + Playwright >=1.40.0: Compatible
- Async patterns: Consistent throughout
- Error handling: NetworkError reuse confirmed
- No contradictory decisions found

**Pattern Consistency:**
- Naming: PascalCase/snake_case/UPPER_SNAKE_CASE (project standard)
- Structure: `src/module_name/` pattern (project standard)
- Communication: Callback-only pattern (PRD-locked)

**Structure Alignment:**
- Directory structure supports all decisions
- Boundaries properly defined (input: page object, output: CapturedResponse)
- Integration points clear (src/network/errors.py, structlog)

### Requirements Coverage Validation ✅

**Functional Requirements Coverage (24 FRs):**
- Network Interception Core (FR1-FR4): `interceptor.py`
- Pattern Matching (FR5-FR8): `patterns.py`, `models.py`
- Lifecycle Management (FR9-FR12): `interceptor.py`
- Error Handling (FR13-FR17): `exceptions.py`, `interceptor.py`
- Response Capture (FR18-FR21): `models.py` CapturedResponse
- Developer Experience (FR22-FR24): `__init__.py` clean API

**Non-Functional Requirements Coverage:**
- Integration: Playwright compatibility
- Reliability: Failure isolation, resource cleanup
- Maintainability: Interface stability (locked API)
- Testability: Mockable interface, isolated pattern testing

### Implementation Readiness Validation ✅

**Decision Completeness:**
- All critical decisions documented with versions
- Implementation patterns comprehensive
- Consistency rules clear and enforceable

**Structure Completeness:**
- All files/directories defined
- Integration points specified
- Boundaries well-defined

**Pattern Completeness:**
- All conflict points addressed
- Naming conventions comprehensive
- Process patterns (error handling, logging) complete

### Gap Analysis Results

**Critical Gaps:** None
**Important Gaps:** None
**Nice-to-Have:** WebSocket interception, multiple interceptors (post-MVP)

### Implementation Detail: attach() Timing Detection (FR10)

**Detection Logic (Defense in Depth - Option D):**

```python
async def attach(self, page: Any) -> None:
    # Fast path: check URL first
    url = page.url
    if url not in ("about:blank", "about:blank#blocked"):
        raise TimingError(
            "attach() must be called before page.goto(). "
            f"Page URL is already: {url}"
        )
    
    # Confirmation: check document.readyState
    ready_state = await page.evaluate("document.readyState")
    if ready_state not in ("loading",):
        raise TimingError(
            "attach() must be called before page.goto(). "
            f"Document readyState is: {ready_state}"
        )
    
    # Proceed with attachment...
```

**Rationale:**
- Fast path (URL check): O(1), catches most cases
- Confirmation (readyState): Handles about:blank edge case
- Two checks together are more reliable than either alone
- attach() is called once per session, so overhead is negligible

**Error Message Guidance:**
- Include both URL and readyState in error message for debugging
- Suggest correct order: "Call attach() first, then navigate with page.goto()"

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**✅ Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** HIGH

**Key Strengths:**
- PRD-locked decisions precisely followed
- Existing implementation conflicts identified and resolved
- attach() timing detection explicitly documented (FR10)
- Test structure supports isolated failure mode testing
- Clean API surface with `__init__.py` exports

**Areas for Future Enhancement:**
- WebSocket interception (post-MVP)
- Multiple interceptors on same page (post-MVP)

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- Refer to this document for all architectural questions
- Use attach() timing detection logic documented above for FR10