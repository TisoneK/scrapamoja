---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7]
status: complete
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/product-brief-scrapamoja-2026-03-17.md"
  - "_bmad-output/project-context.md"
  - "_bmad-output/brainstorming/brainstorming-session-2026-03-17-16-46-13.md"
  - "docs/proposals/browser_api_hybrid/FEATURE_03_CLOUDFLARE_SUPPORT.md"
documentCounts:
  prd: 1
  productBrief: 1
  projectContext: 1
  brainstorming: 1
  uxDesign: 0
  research: 1
  featureProposals: 1
workflowType: architecture
---

# Architecture Document - scrapamoja

**Author:** Tisone
**Date:** 2026-03-18

## Document Status

This architecture document is being created through a collaborative architectural decision-making process.

---

## Section 1: Project Context Analysis

### Requirements Overview

**Functional Requirements:**
The PRD contains 19 functional requirements organized into key categories:
- **Configuration Management (FR1-FR3):** YAML-based site configuration with `cloudflare_protected: true` flag
- **Stealth/Browser Fingerprinting (FR4-FR8):** Browser fingerprint management, automation signal suppression, user agent rotation
- **Challenge Detection (FR9-FR12):** Cloudflare challenge page detection via HTML pattern matching, multi-signal detection
- **Resilience & Retry (FR13-FR15):** Automatic challenge waiting, exponential backoff retry logic
- **Observability (FR16-FR17):** Structured logging for challenge events, metrics exposure
- **Browser Modes (FR18-FR19):** Headless and headed browser support

**Non-Functional Requirements:**
- **Performance:** >95% bypass success rate, <30s average challenge wait time, <1% false positive rate, >90% headless/headed parity
- **Security:** Secure credential handling, automation signal protection, session cookie security
- **Scalability:** Multiple concurrent browser sessions, proper resource management

### Scale & Complexity

- **Primary domain:** Web Scraping / Browser Automation / Anti-Detection
- **Complexity level:** High (deals with sophisticated bot detection systems, browser fingerprinting)
- **Estimated architectural components:** 6-8 core modules (browser management, stealth, detection, resilience, config, observability)

### Technical Constraints & Dependencies

- Python 3.11+ with asyncio-first architecture
- Playwright >=1.40.0 for browser automation
- Must integrate with existing Scrapamoja framework patterns
- Modular sub-module structure required (SCR-003 pattern)

### Cross-Cutting Concerns Identified

- **Async/Await patterns:** All I/O operations must use async def
- **Resource Management:** Browser sessions require proper cleanup
- **Error Handling:** Structured logging with correlation IDs
- **Dependency Injection:** Module interfaces for loose coupling

---

## Section 2: Technical Stack & Foundation

## Starter Template Evaluation

### Project Type

**Brownfield Project** - This is an existing Scrapamoja framework, not a greenfield project. The focus is on adding a new Cloudflare support module.

### Existing Technology Stack

The project already has established technologies:
- **Language:** Python 3.11+ (asyncio-first architecture)
- **Browser Automation:** Playwright >=1.40.0
- **Web Framework:** FastAPI >=0.104.0
- **ORM:** SQLAlchemy >=2.0.0
- **Data Validation:** Pydantic >=2.5.0

### Module Integration Approach

For brownfield projects, we leverage existing patterns rather than using a starter template:

**SCR-003 Sub-Module Pattern** (from project-context.md):
```
src/stealth/cloudflare/
├── __init__.py
├── core/           # profile lifecycle, apply to context
├── detection/     # challenge page detection, multi-signal
├── config/        # cloudflare-specific config, flag wiring
├── models/        # data structures
└── exceptions/    # custom exceptions
```

### Technical Decisions Provided by Existing Framework

- **Async/Await:** All I/O operations use async def (inherited)
- **Module Integration:** Use dependency injection via module interfaces
- **Resource Management:** Async context managers for browser sessions
- **Error Handling:** Structured logging with correlation IDs
- **Type Safety:** MyPy strict mode with Pydantic models

### Implementation Approach

Since this is brownfield, the "starter" is the existing Scrapamoja framework itself. The Cloudflare module will:
1. Follow SCR-003 sub-module pattern
2. Integrate with existing stealth module
3. Use existing resilience engine for retry logic
4. Leverage observability stack for logging

**Note:** This architectural approach should be the foundation for the first implementation story.

---

## Core Architectural Decisions

### Decision Summary

| Decision | Status | Details |
|----------|--------|---------|
| Challenge Detection | ✅ Locked | Multi-signal detection (HTML + Cookie + URL) in separate sub-modules |
| Existing Systems | ✅ Locked | Integrate with src/resilience/ and src/observability/ |
| Browser Context | ✅ Locked | Read-only - receives context, doesn't create sessions |
| Stealth Profile | ✅ Locked | Full stealth (navigator.webdriver, canvas/WebGL, UA, viewport) |
| Site Config | ✅ Locked | YAML flag with site-configurable overrides |
| Testing | ✅ Locked | Follows project-context.md rules |

### 1. Challenge Detection Approach

**Decision:** Multi-signal Detection

Each detection signal lives in its own sub-module under `detection/`:
- `detection/html_pattern/` - HTML pattern matching
- `detection/cookie_clearance/` - Cookie-based clearance detection
- `detection/url_redirect/` - URL redirect pattern detection

This follows the SCR-003 recursive sub-module pattern from project-context.md.

### 2. Integration with Existing Systems

**Decision:** SCR-003 consumes existing systems

- **Resilience Engine:** Import retry mechanisms from `src/resilience/` - NO new retry implementation
- **Observability Stack:** Import structured logging from `src/observability/` - NO new logging infrastructure
- **Stealth Module:** Extend existing `src/stealth/` for browser fingerprinting

This follows project-context.md rule: "ALWAYS use existing systems instead of recreating functionality."

### 3. Browser Context Integration

**Decision:** Read-only integration

SCR-003 does NOT create or manage browser sessions. It receives a Playwright browser context passed in from outside and applies configuration to it.

The import from `src/browser/` is:
- **Read-only** - for type hints and interface contracts only
- **NOT for session creation** - SCR-003 is a configuration concern, not session management

### 4. Stealth/Browser Fingerprint Configuration

**Decision:** Full Stealth Profile with site-configurable overrides

Per PRD (FR4-FR8):
- navigator.webdriver suppression
- Canvas/WebGL fingerprint randomization via init scripts
- User agent rotation
- Viewport normalization

Per PRD (FR1-FR3):
- Site-configurable YAML flag: `cloudflare_protected: true`
- Per-site sensitivity levels
- Timeout configuration

### 5. Module Structure

```
src/stealth/cloudflare/
├── __init__.py
├── core/                    # profile lifecycle, apply to context
├── detection/              # multi-signal detection
│   ├── html_pattern/       # HTML pattern matching
│   ├── cookie_clearance/   # Cookie-based clearance
│   └── url_redirect/       # URL redirect patterns
├── config/                 # cloudflare-specific config, flag wiring
├── models/                 # data structures
└── exceptions/             # custom exceptions
```

### 6. Testing Strategy

**Decision:** Follows project-context.md rules

- Unit tests in `tests/`
- Integration tests for browser session workflows
- pytest markers: `@pytest.mark.integration`, `@pytest.mark.unit`
- asyncio_mode=auto for async test support
- Mock patterns using pytest-mock

---

## Section 3: Architectural Decisions

*See Core Architectural Decisions above*

---

## Section 4: Module Design

### Implementation Patterns & Consistency Rules

**Pattern Source:** project-context.md + SCR-003 specific rules

#### Code Naming Conventions (from project-context.md)

- **Classes:** PascalCase (e.g., `CloudflareDetector`, `StealthProfile`)
- **Functions/Variables:** snake_case (e.g., `detect_challenge()`, `browser_context`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `MAX_RETRY_ATTEMPTS`)
- **Modules:** snake_case (e.g., `cloudflare_stealth`)

#### Async/Await Patterns (from project-context.md)

- All I/O operations use `async def`
- Use `asyncio.gather()` for concurrent browser sessions
- Implement `__aenter__`/`__aexit__` for resource managers

#### SCR-003 Specific Patterns

**Detection Sub-Module Pattern:**
```
detection/
├── html_pattern/
│   ├── __init__.py
│   └── detector.py
├── cookie_clearance/
│   ├── __init__.py
│   └── detector.py
└── url_redirect/
    ├── __init__.py
    └── detector.py
```

**Interface Pattern:**
- Import interfaces from `src/*/interfaces.py`
- Use dependency injection for loose coupling

**Exception Pattern:**
- Custom exceptions in `exceptions/` sub-module
- Follow naming: `CloudflareError`, `ChallengeDetectionError`, etc.

#### Enforcement Guidelines

**All AI Agents MUST:**
- Follow project-context.md rules exactly
- Use existing systems (resilience, observability) instead of recreating
- Import browser context read-only (not for session creation)
- Implement each detection signal in its own sub-module

---

## Section 5: Integration Patterns

### Complete Module Structure (SCR-003)

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
│   └── webdriver/      # navigator.webdriver suppression
│       ├── __init__.py
│       └── mask.py
├── detection/
│   ├── __init__.py
│   ├── html_pattern/
│   │   ├── __init__.py
│   │   ├── matcher.py      # pattern matching logic
│   │   ├── signatures.py   # Cloudflare HTML signatures
│   │   └── models.py       # data structures
│   ├── cookie_clearance/
│   │   ├── __init__.py
│   │   ├── checker.py      # cookie checking logic
│   │   └── signals.py      # clearance signals
│   └── url_redirect/
│       ├── __init__.py
│       ├── detector.py     # redirect detection
│       └── patterns.py     # URL patterns
├── config/
│   ├── __init__.py
│   ├── loader.py       # YAML config loading
│   ├── flags.py       # cloudflare_protected flag
│   └── schema.py      # Pydantic validation
├── models/
│   ├── __init__.py
│   └── challenge.py   # Challenge data structures
└── exceptions/
    ├── __init__.py
    └── errors.py      # Custom exceptions
```

### Requirements to Structure Mapping

| FR | Module | Files |
|----|--------|-------|
| FR1-FR3 | config/ | loader.py, flags.py, schema.py |
| FR4 | core/webdriver/ | mask.py |
| FR5 | core/fingerprint/ | scripts.py |
| FR6 | core/user_agent/ | manager.py |
| FR7 | core/viewport/ | config.py |
| FR8 | core/applier/ | apply.py |
| FR9-FR12 | detection/ | html_pattern/, cookie_clearance/, url_redirect/ |
| FR13-FR15 | Uses src/resilience/ | (external) |
| FR16-FR17 | Uses src/observability/ | (external) |

### Integration Boundaries

- **SCR-003 → src/resilience/:** Import retry mechanisms (read-only)
- **SCR-003 → src/observability/:** Import structured logging (read-only)
- **SCR-003 → src/stealth/:** Extend existing stealth module
- **SCR-003 → src/browser/:** Import types/interfaces only (read-only)

---

## Section 6: Validation & Compliance

### Architecture Validation Results

#### Coherence Validation ✅

- All architectural decisions work together
- Python 3.11+ + Playwright + async/await patterns are compatible
- SCR-003 sub-module pattern aligns with project-context.md rules
- Integration with existing systems (resilience, observability) is coherent

#### Requirements Coverage Validation ✅

| Requirement | Architecture Support |
|-------------|---------------------|
| FR1-FR3 (Config) | config/ module |
| FR4 (Webdriver) | core/webdriver/ |
| FR5 (Fingerprint) | core/fingerprint/ |
| FR6 (User Agent) | core/user_agent/ |
| FR7 (Viewport) | core/viewport/ |
| FR8 (Profile) | core/applier/ |
| FR9-FR12 (Detection) | detection/ sub-modules |
| FR13-FR15 (Resilience) | Uses src/resilience/ |
| FR16-FR17 (Observability) | Uses src/observability/ |

All 19 functional requirements are architecturally supported.

#### Implementation Readiness ✅

- Module structure follows SCR-003 recursive pattern
- Integration points clearly defined (read-only for external systems)
- Naming conventions established
- Error handling patterns defined

#### Gap Analysis

- No critical gaps identified
- Architecture is READY FOR IMPLEMENTATION

---

## Architecture Completeness Checklist

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

---

## Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- Refer to this document for all architectural questions
- Import external systems (resilience, observability) - do not recreate

**First Implementation Priority:**
Create `src/stealth/cloudflare/` directory structure with `__init__.py` files in all subdirectories, then implement core/applier/ module first.

---

*Architecture document completed: 2026-03-18*
