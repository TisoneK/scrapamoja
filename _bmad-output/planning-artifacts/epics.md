---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
---

# scrapamoja - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for scrapamoja, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

**Network Interception Core:**

FR1: Site module developer can register URL patterns to match against network responses
FR2: Site module developer can provide a callback handler to process captured responses
FR3: System captures response metadata including URL, status code, and headers
FR4: System delivers raw response body as bytes to the handler callback

**Pattern Matching:**

FR5: System supports string prefix matching for URL patterns (default behavior)
FR6: System supports substring matching for URL patterns (default behavior)
FR7: System optionally supports regex-based pattern matching per interceptor instance
FR8: System validates pattern inputs at construction time and produces clear errors for invalid patterns

**Lifecycle Management:**

FR9: Site module developer can attach the interceptor to a Playwright page before navigation
FR10: System produces a clear, actionable error if attach() is called after page.goto()
FR11: Site module developer can detach the interceptor from the page when interception is complete
FR12: System handles late detach gracefully without leaking resources

**Error Handling:**

FR13: System handles bodyless responses (204 No Content, 301 Moved Permanently, 304 Not Modified) without crashing the listener
FR14: System isolates handler callback exceptions - a crashing handler logs an error but does not stop the listener
FR15: System provides optional dev logging mode that logs every captured response (disabled by default)
FR16: System produces a warning in dev logging mode when the handler has never fired after navigation completes — catches silent pattern mismatches
FR17: System handles redirect chains (301/302) where the same logical request produces multiple response events — behaviour is documented and predictable

**Response Capture:**

FR18: System captures HTTP status code for each matched response
FR19: System captures response headers for each matched response
FR20: System captures raw response body bytes for each matched response
FR21: System handles race conditions between response.body() await and page navigation gracefully

**Developer Experience:**

FR22: Site module developer can use network interception without reading Playwright documentation
FR23: Interface requires zero Playwright-specific code outside the interceptor itself
FR24: System provides clear error messages for developer mistakes (timing violations, invalid patterns)

### NonFunctional Requirements

**Integration:**

- Playwright Compatibility: NetworkInterceptor must work with the current stable version of Playwright. Changes to Playwright's network event API should be detected early through version pinning in tests.
- Downstream Module Contract: CapturedResponse dataclass must provide data in a format usable by downstream encoding modules (SCR-004/005) without requiring site module developers to understand the raw response structure.
- Error Propagation: Errors in the interceptor should not propagate to the calling site module - they should be handled internally with clear logging.

**Reliability:**

- Failure Isolation: The interceptor must not crash the calling site module. All failure modes (bodyless responses, handler exceptions, timing violations, race conditions) must be handled gracefully.
- Resource Cleanup: detach() must properly clean up all resources. Late detach (after page closure) should not leak resources.
- Deterministic Behavior: The interceptor's behavior must be predictable and deterministic - the same inputs should produce the same outputs.

**Maintainability:**

- Interface Stability: The public API (NetworkInterceptor class, CapturedResponse dataclass) must remain stable. Breaking changes to the interface would require all existing site modules to be updated.
- Debuggability: Dev logging mode must provide sufficient information for debugging pattern matching issues without requiring site module developers to add their own logging.
- Documented Failure Modes: All known failure modes must be documented so that future maintainers understand the expected behavior.

**Testability:**

- Mockable Interface: The module must be designed so that Playwright's page object can be mocked in tests. The attach() method should accept a mockable page interface.
- Isolated Failure Mode Testing: Each failure mode (bodyless responses, handler exceptions, timing violations, race conditions) must be testable in isolation without a real browser.
- Test Coverage Requirement: All identified failure modes from brainstorming must be covered by passing tests - 100% coverage of failure modes.

### Additional Requirements

**Architecture-Derived Requirements:**

- Module Location: `src/network/interception/` - replaces existing `interception.py`
- Interface Design: NetworkInterceptor class with locked API
- Storage Pattern: callback-only (no in-memory list storage)
- Pattern Matching: string prefix/substring default, regex optional
- Error Handling: reuse NetworkError, add TimingError and PatternError
- Response Dataclass: CapturedResponse with raw_bytes field (not body)
- Constructor Args: patterns, handler, dev_logging (not config object)
- Testing Approach: Mock Playwright page interface, 100% failure mode coverage
- Module Structure: `__init__.py`, `interceptor.py`, `models.py`, `exceptions.py`, `patterns.py`
- Existing Files Affected: `src/network/interception.py` - TO BE REMOVED (replaced by directory)

### FR Coverage Map

FR1: Epic 1 - Register URL patterns to match against network responses
FR2: Epic 1 - Provide callback handler to process captured responses
FR3: Epic 2 - Capture response metadata including URL, status code, and headers
FR4: Epic 2 - Deliver raw response body as bytes to the handler callback
FR5: Epic 1 - String prefix matching for URL patterns (default behavior)
FR6: Epic 1 - Substring matching for URL patterns (default behavior)
FR7: Epic 1 - Optional regex-based pattern matching per interceptor instance
FR8: Epic 1 - Validate pattern inputs at construction time and produce clear errors for invalid patterns
FR9: Epic 2 - Attach the interceptor to a Playwright page before navigation
FR10: Epic 2 - Produce a clear, actionable error if attach() is called after page.goto()
FR11: Epic 2 - Detach the interceptor from the page when interception is complete
FR12: Epic 2 - Handle late detach gracefully without leaking resources
FR13: Epic 3 - Handle bodyless responses (204, 301, 304) without crashing the listener
FR14: Epic 3 - Isolate handler callback exceptions - crashing handler logs error but does not stop listener
FR15: Epic 3 - Provide optional dev logging mode that logs every captured response (disabled by default)
FR16: Epic 3 - Produce warning in dev logging mode when handler has never fired after navigation completes
FR17: Epic 3 - Handle redirect chains (301/302) where same logical request produces multiple response events
FR18: Epic 2 - Capture HTTP status code for each matched response
FR19: Epic 2 - Capture response headers for each matched response
FR20: Epic 2 - Capture raw response body bytes for each matched response
FR21: Epic 2 - Handle race conditions between response.body() await and page navigation gracefully
FR22: Epic 3 - Use network interception without reading Playwright documentation
FR23: Epic 3 - Interface requires zero Playwright-specific code outside the interceptor itself
FR24: Epic 3 - Provide clear error messages for developer mistakes (timing violations, invalid patterns)

## Epic List

### Epic 1: Core Module Setup & Pattern Matching

**Goal:** Module structure exists, patterns can be registered and matched

Site module developers can set up the network interception module with proper structure and register URL patterns that the system can match against network responses using flexible matching options.

**FRs covered:** FR1, FR2, FR5, FR6, FR7, FR8

---

#### Story 1.1: Create Module Structure and CapturedResponse Dataclass

As a **site module developer**,  
I want **the network interception module to have proper structure with a CapturedResponse dataclass**,  
So that **I can receive structured response data from captured network requests**.

**Acceptance Criteria:**

**Given** a new Scrapamoja project, **When** importing the NetworkInterceptor module, **Then** the module structure exists at `src/network/interception/` with all five files: `__init__.py`, `interceptor.py`, `models.py`, `exceptions.py`, `patterns.py`

**And** the old `src/network/interception.py` file has been removed

**And** the CapturedResponse dataclass is available with url, status, headers, and raw_bytes fields

**And** the dataclass fields are properly typed (url: str, status: int, headers: dict[str, str], raw_bytes: bytes | None)

---

#### Story 1.2: Implement NetworkInterceptor Constructor with Pattern Validation

As a **site module developer**,  
I want **to create a NetworkInterceptor with URL patterns and a handler callback**,  
So that **the interceptor can match network responses against my specified patterns**.

**Acceptance Criteria:**

**Given** a NetworkInterceptor constructor with patterns and handler parameters, **When** valid patterns are provided, **Then** the interceptor is created successfully

**And** **When** invalid patterns (empty list, invalid regex if provided) are provided, **Then** a clear PatternError is raised with descriptive message

**And** the constructor accepts patterns: list[str], handler: Callable, dev_logging: bool = False

---

#### Story 1.3: Implement Pattern Matching System

As a **site module developer**,  
I want **to use flexible URL pattern matching (prefix, substring, regex)**,  
So that **I can capture exactly the network responses I need**.

**Acceptance Criteria:**

**Given** registered patterns in the interceptor, **When** a network response URL is evaluated, **Then** the pattern matching follows this order:

1. **First**, string prefix matching (URL starts with pattern) - this is the default fast path
2. **If no prefix match**, string substring matching (URL contains pattern) - this is the fallback
3. **If regex is specified** for a pattern, regex matching is used instead of string matching

**And** all pattern matching logic is isolated in patterns.py for independent unit testing

**And** the pattern matching can be tested without instantiating the full NetworkInterceptor

---

### Epic 2: Interceptor Lifecycle & Response Capture

**Goal:** Interceptor can attach, capture responses, and detach cleanly

Site module developers can attach the interceptor to a Playwright page before navigation, capture response data (URL, status, headers, raw bytes) via the handler callback, and detach cleanly when done.

**FRs covered:** FR3, FR4, FR9, FR10, FR11, FR12, FR18, FR19, FR20, FR21

---

#### Story 2.1: Implement attach() Method with Timing Validation

As a **site module developer**,  
I want **to attach the interceptor to a Playwright page before navigation**,  
So that **the interceptor can capture network responses as they occur**.

**Acceptance Criteria:**

**Given** a NetworkInterceptor instance and a Playwright page object, **When** attach(page) is called before page.goto(), **Then** the interceptor is successfully attached to the page

**And** **When** attach(page) is called after page.goto() has already occurred, **Then** a clear TimingError is raised with message: "attach() must be called before page.goto(). Call attach() first, then navigate."

**And** the attach method is async def attach(self, page: Any) -> None

---

#### Story 2.2: Implement Playwright Network Event Listener

As a **site module developer**,  
I want **the interceptor to listen for network responses**,  
So that **matched responses can be captured and processed**.

**Acceptance Criteria:**

**Given** an attached interceptor, **When** the page navigates and network responses occur, **Then** the interceptor listens to Playwright's response events

**And** responses are matched against registered patterns using the pattern matching system

**And** matched responses trigger the handler callback with a CapturedResponse object

---

#### Story 2.3: Implement Response Capture

As a **site module developer**,  
I want **to receive complete response data (URL, status, headers, raw bytes) via the handler callback**,  
So that **I can process the captured data for my site's needs**.

**Acceptance Criteria:**

**Given** a matched network response, **When** the handler callback is invoked, **Then** the CapturedResponse contains:
- url: str - the request URL
- status: int - HTTP status code
- headers: dict[str, str] - response headers
- raw_bytes: bytes | None - raw response body

**And** the handler receives exactly one CapturedResponse per matched response

**And** **When** response.body() is awaited and the page navigates away before the await completes, **Then** the exception is caught, raw_bytes is set to None, and the handler is still called with the partial CapturedResponse — the listener does not crash and continues monitoring subsequent responses

---

#### Story 2.4: Implement detach() Method

As a **site module developer**,  
I want **to detach the interceptor when interception is complete**,  
So that **resources are properly cleaned up**.

**Acceptance Criteria:**

**Given** an attached interceptor, **When** detach() is called, **Then** the Playwright event listeners are removed

**And** all resources are cleaned up properly

**And** **When** detach() is called after the page has been closed (late detach), **Then** no exception is raised and no resources leak

---

### Epic 3: Error Handling & Developer Experience

**Goal:** All failure modes handled gracefully, developer experience is clean

Site module developers experience robust error handling that prevents crashes from edge cases and receives clear, actionable error messages that enable quick problem resolution without deep Playwright knowledge.

**FRs covered:** FR13, FR14, FR15, FR16, FR17, FR22, FR23, FR24

---

#### Story 3.1: Implement Error Handling

As a **site module developer**,  
I want **the interceptor to handle edge cases gracefully without crashing**,  
So that **my site module continues running even when unexpected responses occur**.

**Acceptance Criteria:**

**Given** an attached interceptor, **When** a bodyless response is received (204 No Content, 301 Moved Permanently, 304 Not Modified), **Then** the listener does not crash and continues monitoring

**And** **When** the handler callback raises an exception, **Then** the exception is caught, logged, and the listener continues without stopping

**And** **When** redirect chains occur (301/302), **Then** the behavior is documented and predictable (each response in the chain is processed separately)

---

#### Story 3.2: Implement Dev Logging Mode

As a **site module developer**,  
I want **optional debug logging to help troubleshoot pattern matching issues**,  
So that **I can see what's being captured and diagnose problems**.

**Acceptance Criteria:**

**Given** dev_logging=True in NetworkInterceptor constructor, **When** responses are captured, **Then** each captured response is logged at debug level

**And** **When** page navigation completes but the handler has never fired, **Then** a warning is logged to help identify silent pattern mismatches

**And** **When** dev_logging=False (default), **Then** no logging output is produced

---

#### Story 3.3: Implement Clear Error Messages

As a **site module developer**,  
I want **clear, actionable error messages when I make mistakes**,  
So that **I can quickly fix issues without deep debugging**.

**Acceptance Criteria:**

**Given** invalid input or incorrect usage, **When** the error occurs, **Then** the error message is specific and actionable

**And** for timing violations: "attach() must be called before page.goto(). Call attach() first, then navigate."

**And** for pattern errors: Clear description of what made the pattern invalid

**And** the errors do not expose internal Playwright concepts - site module developers never need to read Playwright documentation to understand error messages