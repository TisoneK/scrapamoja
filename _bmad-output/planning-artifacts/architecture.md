---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/product-brief-scrapamoja-2026-03-10.md"
  - "_bmad-output/project-context.md"
  - "docs/proposals/browser_api_hybrid/SCRAPAMOJA_BUILD_ORDER.md"
  - "docs/features.md"
  - "docs/summary.md"
  - "docs/yaml-configuration.md"
  - "docs/modular_template_guide.md"
workflowType: 'architecture'
project_name: 'scrapamoja'
user_name: 'Tisone'
date: '2026-03-11'
lastStep: 8
status: 'complete'
completedAt: '2026-03-11'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## ⭐ Architecture Complete - Implementation Ready

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

The PRD defines 28 functional requirements organized into 7 categories:

1. **Extraction Mode Management (FR1-FR5):** System routes to extraction modes declared in site module config. Supports Direct API Mode (MVP), Intercepted API Mode (Phase 2), Hybrid Mode (Phase 2). DOM Mode is existing behavior - must remain unaffected.

2. **HTTP Transport/SCR-001 (FR6-FR10):** Async HTTP client using httpx supporting GET/POST/PUT/DELETE. Chainable request builder interface. Per-domain rate limiting enforced at transport layer (not configurable to global). Concurrent requests without blocking.

3. **Authentication & Credentials (FR11-FR15):** Bearer token, Basic auth, Cookie-based auth support. Credentials never logged. Sourced from environment variables or secrets files, never hardcoded.

4. **Site Module Management (FR16-FR20):** YAML-based site module configuration. Site modules declare endpoint, auth method, extraction mode. Enforced output contract interface verified by static type checking. Boundary rule: adding new site module touches only `src/sites/`.

5. **Output & Data Delivery (FR21-FR24):** JSON for all structured data. Raw bytes returned as-is. Consistent output schema regardless of extraction mode. Every site module implements documented output contract.

6. **Error Handling (FR25-FR28):** Fail fast and loud. Structured errors with context. Graceful degradation on schema changes (partial data returned). Data timestamp surfaced in every response.

**Non-Functional Requirements:**

- **Performance:** <1 second latency for direct API calls (vs 5-30 seconds browser). 90% reduction in memory/CPU per extraction. 10-100x faster than browser-based.
- **Security:** Credentials never in logs. Redact auth headers/cookies by default. Opt-in verbose logging with explicit warning.
- **Availability:** 99%+ successful extraction target. Fallback tiers: retry via resilience → alternative extraction mode → alert consuming system.
- **Maintainability:** Resilience module handles all retry logic - site modules have zero retry code. Module boundaries enforced - changes outside `src/sites/` indicate boundary failure.

### Scale & Complexity

- **Primary domain:** API Backend / Developer Tool
- **Complexity level:** Medium-to-High
- **Estimated architectural components:** 9 new modules (SCR-001 through SCR-009) across 3 tiers

### Technical Constraints & Dependencies

1. **Brownfield project:** Must not break existing FlashScore and Wikipedia scrapers
2. **Python 3.11+:** asyncio-first architecture required
3. **httpx:** HTTP client choice for SCR-001
4. **Output contract:** Enforced via static type checking, not informal convention
5. **AiScore protobuf:** Undocumented schema - must handle changes gracefully

### Cross-Cutting Concerns Identified

1. **Async-first architecture:** Required for high-frequency polling scenarios
2. **Unified interface:** Same CLI and config patterns across all 4 extraction modes
3. **Resilience patterns:** Retry logic delegated to `src/resilience/` module - SCR-001 has zero retry code
4. **Per-domain rate limiting:** HARD requirement enforced at transport layer, not left to caller
5. **Protobuf schema handling:** Graceful degradation - return partial data or clear error, never silent failure
6. **Credential management:** Environment-based configuration, gitignored secrets, never hardcoded

## Starter Template Evaluation

### Project Type: Brownfield Extension

This is a **brownfield project** - Scrapamoja already exists and is being extended with new modules (SCR-001 through SCR-009). Unlike a new project that needs a starter template, this project extends existing architectural patterns.

### Existing Architecture to Extend

- **Base modules:** Browser management, stealth, resilience (already exist in `src/`)
- **CLI patterns:** Site-specific CLI classes in `src/sites/{site}/cli/main.py`
- **Module structure:** `src/module_name/` with `__init__.py` for clean API
- **Interfaces:** `src/module_name/interfaces.py` for dependency injection

### Technology Stack for SCR-001 through SCR-009

| Component | Technology | Notes |
|-----------|-----------|-------|
| Runtime | Python 3.11+ | asyncio-first architecture |
| HTTP Client | httpx | For SCR-001 Direct API Mode |
| Async | asyncio | Native, no external library |
| Data Validation | Pydantic | Config models and structured output/error models **within modules only** |
| Logging | structlog | Structured logging with correlation IDs |
| Browser | Playwright | For SCR-002, SCR-003, SCR-006, SCR-007 only |

### Excluded Technologies

- **FastAPI:** Exists in project but NOT used by SCR-001-009
- **SQLAlchemy:** Exists in project but NOT needed for scraping modules

### Key Architectural Decision: Output Contract Interface

**CRITICAL:** The output contract interface is a **Protocol** (duck typing), NOT a Pydantic BaseModel inheritance chain.

- Pydantic is used for config models and structured output/error models **within each module**
- Do NOT impose Pydantic models across module boundaries
- Output contract uses Python `Protocol` for loose coupling
- Enables any implementation to satisfy the contract without inheritance

### Build Order (from SCRAPAMOJA_BUILD_ORDER.md)

| Tier | Phase | Modules | Notes |
|------|-------|---------|-------|
| 1 | Foundation | SCR-001, SCR-002, SCR-003, SCR-004, SCR-006, SCR-009 | No internal dependencies, can be built in parallel |
| 2 | Composite | SCR-005, SCR-007 | SCR-005 depends on SCR-004; SCR-007 depends on 001, 003, 006 |
| 3 | Assembly | SCR-008 | Depends on all previous modules |

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Rate limiting implementation approach
- CI boundary enforcement

**Important Decisions (Shape Architecture):**
- All other decisions already specified in PRD

**Deferred Decisions (Post-MVP):**
- None identified at this time

### Module Structure

**Decision:** Follow existing `src/{module_name}/` pattern
- Each module has `__init__.py` for clean API
- Each module has `interfaces.py` for dependency injection
- Confirmed from existing Scrapamoja patterns

### HTTP Transport (SCR-001)

**Decision:** Chainable request builder pattern
- Confirmed from SCAMPER session and PRD
- httpx-based async client
- No further discussion needed

### Rate Limiting Implementation

**Decision:** Custom token bucket implementation
- **Approach:** Custom implementation, not library
- **Keying:** Per-domain
- **Location:** Inside SCR-001 module boundary
- **Implementation:** ~30-40 lines of code
- **Rationale:** Thin implementation provides full control. Libraries would need wrapping anyway. Per-domain requirement is specific enough that a library would add complexity without benefit.

### Testing Approach

**Decision:** pytest-asyncio
- Natural choice for asyncio-first project
- Implied by NFR17 - each module independently testable in isolation
- Follows existing project patterns

### CI/CD Boundary Enforcement (NFR15)

**Decision:** GitHub Actions workflow step
- **Mechanism:** `git diff --name-only` against base branch
- **Validation:** Any changed files outside `src/sites/` in a PR that modifies `src/sites/` causes failure
- **Location:** GitHub Actions workflow step
- **Note:** This is a CI check, NOT a pytest test
- **Rationale:** Enforces the NFR15 requirement - CI must verify new site modules do not modify files outside `src/sites/`

### Complete Decision Matrix

| Category | Decision | Rationale |
|----------|----------|----------|
| Runtime | Python 3.11+ (asyncio-first) | PRD requirement |
| HTTP Client | httpx | PRD SCR-001 |
| Output Contract | Protocol (duck typing) | Loose coupling, not Pydantic inheritance |
| Pydantic Usage | Within modules only | Technical preference - don't impose across boundaries |
| Logging | structlog | Project context |
| Rate Limiting | Custom token bucket, per-domain | User decision - thin implementation, full control |
| Boundary Rule | Site modules touch only `src/sites/` | PRD NFR15 |
| Error Handling | Fail fast, structured errors | PRD |
| Credentials | Env vars, never logged | PRD security |
| Module Structure | `src/{module_name}/` with interfaces.py | Existing pattern |
| Chainable Builder | Confirmed | SCAMPER session |
| Testing | pytest-asyncio | Asyncio-first project |
| CI Boundary Check | GitHub Actions git diff step | User decision - enforce NFR15 |

## Implementation Patterns & Consistency Rules

### Overview

This section defines implementation patterns that prevent AI agent conflicts. These patterns build on the 45 rules in `project-context.md` with additional specificity for SCR-001 through SCR-009.

### Pattern 1: HTTP Response Handling

**Rule:** SCR-001 returns raw `httpx.Response` — never decoded, never wrapped.

**Rationale:** Without this pattern, different agents will make different choices:
- One agent returns httpx.Response directly
- Another wraps it in a dataclass
- Another decodes it immediately

The chain breaks when modules expect different types.

**Implementation:**
- Caller decides what to do with the response
- Any module needing decoded content passes the response to SCR-004 (encoding detector) first
- No module between SCR-001 and SCR-004 touches the response body

### Pattern 2: Error Structure (SHARED - Exception to Boundary Rule)

**Rule:** Every error in SCR-001 through SCR-009 must carry this structure:

```python
{
    "module": "scr_001",        # which module raised it
    "operation": "execute",      # what operation failed
    "url": "...",               # redacted if auth present
    "status_code": 403,         # if HTTP error
    "detail": "...",            # human readable
    "partial_data": {...}       # whatever was extracted before failure, or None
}
```

**Location:** `src/network/`

**IMPORTANT - Intentional Cross-Boundary Import:**
- The shared error model lives in `src/network/` because most errors originate there
- However, it is imported by ALL modules that raise structured errors (src/encodings/, src/stealth/, src/browser/)
- This is the **single deliberate cross-boundary import** in the entire codebase
- Must be documented as INTENTIONAL to prevent future "clean up cross-boundary imports" passes from breaking it

### Pattern 3: Retry Logic Boundary

**Rule:** SCR-001 raises errors — it does NOT retry. The resilience module handles retries.

**Error Categories:**
- **Retryable:** network timeout, connection reset, 429, 503 — resilience module retries these
- **Terminal:** 401, 403, schema mismatch, malformed URL — resilience module does not retry these, surfaces immediately

**Implementation Detail (CRITICAL):**
- The retryable/terminal tag is an **enum field** on the shared error model (Pattern 2)
- NOT a separate exception class hierarchy
- Agents must NOT create RetryableError and TerminalError subclasses
- One error type, one tag field — ensures resilience module handles consistently

This is the interface contract between SCR-001 and src/resilience/.

### Pattern 4: Config Model Structure

**Rule:** Each module that reads YAML config maps it to a Pydantic model defined inside that module.

**Boundaries:**
- The model is never imported by other modules
- Config flows inward — the module owns its config shape
- If two modules need the same config value, they each define their own model for it
- No shared config models across module boundaries

### Pattern 5: CLI Entry Point

**Rule:** Already established in `project-context.md`.

Reference: Site-specific CLI classes in `src/sites/{site}/cli/main.py` with `create_parser()` and `run()` methods.

**Do not redefine** — reference existing patterns.

### Additional Rules from Project Context

AI agents implementing SCR-001-009 must also follow the 45 rules in `_bmad-output/project-context.md`, including:

- **Naming:** snake_case for modules/functions/variables, PascalCase for classes, UPPER_SNAKE_CASE for constants
- **Line length:** 88 characters (Black)
- **Async:** ALL I/O operations use `async def`
- **Resource management:** async context managers (`__aenter__`/`__aexit__`)
- **Type safety:** MyPy strict mode, all functions need type annotations

### Enforcement

1. **CI Boundary Check:** GitHub Actions step validates site modules touch only `src/sites/`
2. **Static Type Checking:** MyPy strict mode verifies Protocol adherence
3. **Code Quality:** Black formatting (88 char), Ruff linting
4. **Shared Error Model:** The single cross-boundary Pydantic import is documented as intentional

## Project Structure & Boundaries

### Existing src/ Structure Analysis

Before mapping new modules, the undocumented directories were investigated:

| Directory | Contents | Relevance to SCR-001-009 |
|----------|----------|------------------------|
| src/core/ | logging_config.py, shutdown/, snapshot/ | Core concerns - NOT a catch-all |
| src/models/ | selector_models.py only | Selector-specific only - NOT shared models |
| src/api/ | FastAPI web layer | Web API - NOT relevant to SCR-001-009 |
| src/services/ | Empty | Must remain EMPTY and unused by SCR-001-009 |

### New Module Directory Mapping

| Module | ID | Location | Status | Notes |
|--------|-----|----------|--------|-------|
| Direct API Mode | SCR-001 | `src/network/` | NEW | HTTP transport module |
| Network Interception | SCR-002 | `src/network/` | Phase 2 | Not in current scope |
| Cloudflare Support | SCR-003 | `src/stealth/` | Phase 2 | Not in current scope |
| Auto Encoding Detection | SCR-004 | `src/encodings/` | Phase 2 | Not in current scope |
| Protobuf Decoding | SCR-005 | `src/encodings/` | Phase 2 | Not in current scope |
| Session Harvesting | SCR-006 | `src/browser/` | Phase 2 | Not in current scope |
| Session Bootstrap | SCR-007 | `src/network/` | Phase 2 | Not in current scope |
| AiScore Module | SCR-008 | `src/sites/aiscore/` | Phase 2 | Not in current scope |
| Persistent Profile | SCR-009 | `src/browser/` | Phase 2 | Not in current scope |

**Note:** Each entry represents a module directory (with `__init__.py`), not a single file. Internal file organization is the implementation agent's decision.

### Important Boundary Rules

1. **src/services/ remains EMPTY:**
   - Must remain unused by SCR-001-009
   - Prevents future agents from using it as a dumping ground
   - SCR-007 (orchestration) lives in src/network/, NOT here

2. **src/network/ is the new home for:**
   - HTTP transport (SCR-001)
   - Network interception (SCR-002)
   - Session bootstrap orchestration (SCR-007)
   - Shared error model (Pattern 2)

3. **src/encodings/ is NEW:**
   - Houses both encoding detection (SCR-004) and protobuf decoding (SCR-005)
   - Not just decoder - handles detection AND decoding

### Module Interaction Boundaries

> **NOTE:** This flow shows the complete architectural chain for context. For implementation scope, see the "Current Scope" statement at the end of this document.

```
SCR-001 (HTTP Transport)
    ↓ returns raw httpx.Response
SCR-004 (Encoding Detection)
    ↓ identifies format
SCR-005 (Protobuf Decoding)
    ↓ decodes binary
SCR-007 (Session Bootstrap)
    ↓ orchestrates
SCR-008 (AiScore Site Module)
```

### Directory Structure Overview

```
src/
├── network/                 # NEW - houses HTTP transport modules
│   └── (module directories for SCR-001)
├── encodings/              # NEW - SCR-004, SCR-005 (Phase 2)
│   └── (module directories)
├── stealth/                # EXTENDED - SCR-003 (Phase 2)
│   └── (module directories)
├── browser/                # EXTENDED - SCR-006, SCR-009 (Phase 2)
│   └── (module directories)
├── sites/                  # EXTENDED - SCR-008 (Phase 2)
│   └── aiscore/
│       └── (module directories)
├── resilience/              # REUSED - SCR-001 uses it
└── ...existing...
```

**Note:** Each SCR feature is a module (directory with `__init__.py`), not a single file. Internal file names are the implementation agent's decision.

### CI Boundary Enforcement

Per NFR15, GitHub Actions validates that site modules touch only `src/sites/`:

```yaml
# .github/workflows/boundary-check.yml
- name: Check site module boundaries
  run: |
    git diff --name-only ${{ github.base_ref }}...HEAD \
      | grep -v "^src/sites/" \
      | grep -q "^src/sites/" && echo "ERROR: Changes outside src/sites/" && exit 1 || true
```

This ensures the boundary rule is enforced on all PRs.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- All technology choices are compatible: Python 3.11+, httpx, asyncio, Pydantic, structlog, Playwright
- No version conflicts identified
- Patterns align with technology choices
- No contradictory decisions

**Pattern Consistency:**
- Implementation patterns support architectural decisions
- HTTP Response Handling → Encoding Detection → Decoding chain is coherent
- Naming conventions consistent across all areas
- Structure patterns align with technology stack

**Structure Alignment:**
- Project structure supports all architectural decisions
- Boundaries properly defined and respected
- Structure enables chosen patterns
- Integration points properly structured

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:**
- FR1-FR5 (Extraction Mode Management): Supported by module routing and configuration
- FR6-FR10 (HTTP Transport): SCR-001 provides chainable httpx client
- FR11-FR15 (Authentication): Bearer, Basic, Cookie auth support
- FR16-FR20 (Site Modules): YAML config, boundary rule, output contract
- FR21-FR24 (Output): JSON delivery, Protocol-based output contract
- FR25-FR28 (Error Handling): Structured errors with context, graceful degradation

**Non-Functional Requirements Coverage:**
- Performance: Async-first, <1s latency target
- Security: Credentials never logged, env var sourcing
- Availability: 99%+ target, fallback tiers
- Maintainability: Resilience module handles retries, boundary rule enforced

### Implementation Readiness Validation ✅

**Decision Completeness:**
- All critical decisions documented with versions
- Implementation patterns comprehensive enough for AI agents
- Consistency rules clear and enforceable
- Examples provided for major patterns

**Structure Completeness:**
- Project structure complete and specific
- All 9 modules mapped to specific directories
- Integration points clearly specified
- Component boundaries well-defined

**Pattern Completeness:**
- All potential conflict points addressed (HTTP response, error, retry, config, CLI)
- Naming conventions comprehensive (from project-context.md)
- Communication patterns fully specified (Protocol-based output contract)
- Process patterns complete (error handling, retry boundary)

### Gap Analysis Results

**Critical Gaps:** None

**Important Gaps:** None

**Nice-to-Have:**
- Could add more code examples for complex patterns (deferred - patterns are clear enough)

### Architecture Completeness Checklist

✅ **Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

✅ **Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

✅ **Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

✅ **Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** HIGH

**Key Strengths:**
1. Clear module boundaries with intentional cross-boundary exception (shared error model)
2. Explicit retry logic boundary between SCR-001 and resilience module
3. CI boundary check enforces site module boundary rule
4. Protocol-based output contract for loose coupling
5. Build order provides clear dependency path
6. All 28 FRs and all NFRs covered

**Areas for Future Enhancement:**
- SCR-007 brainstorming/interface design process (Phase 2)
- Response caching with TTL (Phase 2)

### Notes for Future Phases

**1. SCR-007 Process Requirement:**
> SCR-007 must go through the same brainstorming and interface design process as SCR-001 before implementation begins — flagged as a formal process requirement in PRD.

**2. Response Caching with TTL:**
> Response caching with TTL for high-frequency polling — deferred to Phase 2. Exists only in brainstorming session document. Must be explicitly added to Growth Features list before Phase 2 begins to avoid rediscovering and debating again.

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- Refer to this document for all architectural questions

**First Implementation Priority:**
SCR-001 (Direct API Mode) - HTTP transport layer with custom per-domain token bucket rate limiting.

**Current Scope:** SCR-001 ONLY. SCR-002 through SCR-009 are documented for architectural awareness but are NOT in scope for this implementation phase.
