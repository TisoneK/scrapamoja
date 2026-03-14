---
stepsCompleted: ["step-01-init", "step-02-discovery", "step-02b-vision", "step-02c-executive-summary", "step-03-success", "step-04-journeys", "step-05-domain", "step-06-innovation", "step-07-project-type", "step-08-scoping", "step-09-functional", "step-10-nonfunctional", "step-11-polish"]
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-scrapamoja-2026-03-14.md
  - _bmad-output/brainstorming/brainstorming-session-2026-03-14-0500.md
  - _bmad-output/project-context.md
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: general
  complexity: medium
  projectContext: brownfield
---

# Product Requirements Document - scrapamoja

**Author:** Tisone
**Date:** 2026-03-14

## Executive Summary

SCR-002 Network Response Interception enables Scrapamoja to extract data from modern SPAs by capturing API responses at the network layer before they reach the DOM. This transforms Scrapamoja from a DOM-only scraper into a hybrid extraction platform capable of targeting any web architecture.

### What Makes This Special

- **Architectural Fit:** Slots directly into Scrapamoja's existing module boundary model — receives page from `src/browser/`, delivers raw bytes to `src/encodings/`, site modules consume it without knowing Playwright exists
- **Composability Moat:** SCR-002 + SCR-003 + SCR-004 + SCR-005 + SCR-007 compose into a complete hybrid extraction pipeline — competitors reimplementing just interception get a fraction of the value
- **Separation of Concerns:** SCR-002 stops at raw bytes, hands off to SCR-004/005 for decoding — this design choice makes the module reusable across every future site regardless of encoding format

### Problem Statement

Modern web applications are SPAs that load data dynamically via internal API calls. The data never appears in the HTML DOM in a usable form. Scrapamoja's current DOM scraping approach cannot extract this data reliably. Developers building site modules for these targets have no extraction path today.

### Target Users

**Primary:** Scrapamoja Site Module Developers — Python developers building Scrapamoja site modules for SPA-based targets who are not Playwright experts.

**Secondary:** Future External Contributors who inherit a working interception layer without needing to understand Playwright's network event system.

### Project Classification

- **Project Type:** Developer Tool (SDK/library/framework)
- **Domain:** General (data extraction, API integration, developer utilities)
- **Complexity:** Medium
- **Context:** Brownfield (feature addition to existing Scrapamoja project)

## Success Criteria

### User Success

**Module Level:** SCR-002 is considered successful when a site module developer can integrate network interception in a new site module without reading Playwright documentation or handling any Playwright internals themselves. The interface is self-sufficient.

**Framework Level:** SCR-008 (AiScore) can be built using SCR-002 as its capture layer — the first real-world proof. If AiScore cannot be built on top of SCR-002 without modifications to SCR-002 itself, the module is not generic enough. SCR-008 serves as a validation gate for SCR-002's genericness — if SCR-008 requires modifications to SCR-002 to work, SCR-002 is not sufficiently generic. This is a quality signal, not a dependency or timeline commitment.

**Quality Level:** All failure modes identified in brainstorming are handled correctly:
- Bodyless responses do not crash the listener
- Handler exceptions do not propagate
- Late detach does not leak
- Silent pattern mismatches surface in dev mode
- A developer using SCR-002 incorrectly gets a clear error, not silent failure

**User Quote:** "I found the endpoint in DevTools, registered the pattern, and it worked. I never had to think about Playwright."

### Business Success

**3 Months:**
- SCR-002 is merged, fully tested, and the interception pattern is proven against a real SPA target
- The hybrid pipeline has its first real proof point
- ScoreWise has a working data feed

**12 Months:**
- Multiple site modules exist that use SCR-002 as their capture layer
- New SPA targets are unblocked by default
- Remaining hybrid pipeline features (SCR-003 through SCR-007) are built on the foundation SCR-002 provides

**Strategic Contribution:**
- SCR-002 is the second pillar of the hybrid extraction platform, after SCR-001
- Defines Scrapamoja as "a framework that can extract structured data from any web architecture"

### Technical Success

All failure modes identified in brainstorming are handled correctly.

### Measurable Outcomes

| Metric | Target |
|--------|--------|
| New site module using SCR-002 requires zero Playwright-specific code outside the interceptor | 100% |
| All brainstorming failure modes covered by tests | 100% |
| Existing FlashScore and Wikipedia modules unaffected — zero regression | 100% |
| attach() called after page.goto() produces clear, actionable error | Yes |
| Number of site modules buildable for SPA targets | > 0 (currently 0) |

## Product Scope

### MVP - Minimum Viable Product

The MVP is exactly the four-step usage pattern — nothing more.

**Must have for MVP:**
1. **NetworkInterceptor class** with attach(page) and detach() methods
2. **URL pattern matching** — string prefix/substring default, one optional regex per interceptor
3. **Pattern validation at construction time** — clear error on invalid input
4. **CapturedResponse dataclass** — url, status, headers, raw_bytes as named fields
5. **Handler callback invocation** — isolated exception handling, crashing handler logs error, does not stop the listener
6. **Graceful bodyless response handling** — 204, 301, 304 do not crash the listener
7. **Dev logging mode** — off by default, flag to enable, logs every captured response
8. **attach() timing validation** — called after page.goto() produces clear actionable error

**The MVP is complete when:** a site module developer can use the four-step pattern against a real SPA target and receive raw bytes in their handler without writing any Playwright-specific code themselves.

### Growth Features (Post-MVP)

- **WebSocket frame interception** — same listener pattern, different event type, natural extension
- **Streaming response support** — partial body capture for chunked responses
- **Multiple interceptors** on same page with non-overlapping pattern sets
- **Auto-deduplication** as opt-in flag

### Vision (Future)

Long-term (2-3 years): If Scrapamoja becomes a platform with external contributors, SCR-002 becomes the standard capture layer that every SPA module uses. The interface stays stable — new site modules added years later use the same four-step pattern.

## User Journeys

### Primary User: Scrapamoja Site Module Developer

**Persona:** Alex - Python developer building Scrapamoja site modules for data sources (sports, finance, betting). Not a Playwright expert - knows enough to navigate pages and extract data, but hasn't thought deeply about network event systems.

#### Journey 1: Success Path - Building an SPA Site Module

**Opening Scene:**
Alex is tasked with building a new site module for a sports data website that turns out to be a SPA. They've successfully built DOM-based scrapers before, but when they navigate to the target page and run selectors, they get nothing. Inspecting the page, they realize the data loads dynamically via JavaScript.

**Rising Action:**
- Tries wait_for_selector — fragile, timing-dependent, breaks on site changes
- Looks at DevTools network tab, sees API call, tries direct HTTP — 403 blocked
- Stuck with no clear path forward inside Scrapamoja framework

**Climax:**
- Discovers SCR-002 NetworkInterceptor in src/network/
- Reads interface: three methods, pattern list, handler — immediately understood
- Attaches before page.goto(), navigates, handler fires with exactly the data from DevTools

**Resolution:**
"The framework solved the hard part. I just registered a pattern."

#### Journey 2: Edge Case - Handling Bodyless Responses

**Opening Scene:**
Alex is building a module for a site that returns 204 No Content for certain requests. They need to handle this gracefully without crashing the listener.

**Rising Action:**
- Registers pattern for API endpoint
- Navigates, receives 204 response
- NetworkInterceptor gracefully handles bodyless response, logs in dev mode, doesn't crash

**Resolution:**
Alex continues working without having to add special handling for edge cases. The framework has their back.

#### Journey 3: Error Recovery - Wrong attach() Timing

**Opening Scene:**
Alex accidentally calls attach() after page.goto() - a common mistake for developers new to network interception.

**Rising Action:**
- Calls attach() on an already-navigated page
- NetworkInterceptor detects the timing violation
- Clear, actionable error produced: "attach() must be called before page.goto(). Call attach() first, then navigate."

**Resolution:**
Alex fixes the code quickly because the error message is clear and actionable. No hours of debugging.

### Secondary User: Future External Contributor

**Persona:** Jordan - External developer who discovers Scrapamoja and wants to contribute a new site module for an SPA target. They're familiar with Python but not with the Scrapamoja internals.

**Opening Scene:**
Jordan finds Scrapamoja through a blog post or GitHub search. They're excited about the idea of a hybrid extraction platform.

**Rising Action:**
- Explores the codebase, finds SCR-002 in src/network/
- Interface is the same regardless of familiarity with codebase
- Documentation provides everything needed to get started

**Resolution:**
"Inherited a working interception layer without needing to understand Playwright's network event system. The interface just works."

### Journey Requirements Summary

From these journeys, the following capabilities are revealed:

1. **Simple Interface Design:** Three methods (attach, detach, handler) - immediately understood without reading Playwright docs
2. **Pattern Matching:** URL pattern registration with clear matching behavior
3. **Error Handling:** Clear, actionable errors for developer mistakes (timing violations, invalid patterns)
4. **Graceful Edge Case Handling:** Bodyless responses (204, 301, 304) handled without crashing
5. **Dev Mode Logging:** Optional logging to help with debugging
6. **Exception Isolation:** Handler exceptions don't crash the listener

## Developer Tool Specific Requirements

### Project-Type Overview

SCR-002 is an internal module within Scrapamoja, not a standalone package. It's a Python library that enables network response interception for site module developers building SPA scrapers.

### Technical Architecture Considerations

**Integration Model:**
- Internal module in `src/network/` directory
- Receives Playwright page object from `src/browser/`
- Delivers raw bytes to `src/encodings/` for downstream processing
- Site modules consume the interceptor without knowing Playwright exists

**API Surface (Locked):**
- `NetworkInterceptor` class with:
  - `__init__(patterns: list[str], handler: Callable, dev_logging: bool = False)`
  - `attach(page)` - must be called before page.goto()
  - `detach()` - cleanup when done
- `CapturedResponse` dataclass with:
  - `url` - the request URL
  - `status` - HTTP status code
  - `headers` - response headers
  - `raw_bytes` - the raw response body

### Documentation Requirements

1. **API Reference:** Complete documentation of NetworkInterceptor class and CapturedResponse dataclass
2. **Usage Examples:** Four-step pattern demonstration showing typical integration
3. **Integration Guide:** Short guide showing how to use SCR-002 within a site module

### What We Skip

- Visual design (not applicable to developer tool)
- Store compliance (not a standalone package)
- Language matrix (Python only)
- Installation guide (internal module, part of Scrapamoja)
- Migration guide (new module, nothing to migrate)

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-Solving MVP - solve the core problem of SPA data extraction with minimum viable functionality
**Resource Requirements:** Single Python developer with Playwright familiarity

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Primary user (Alex) successfully integrates network interception in a new site module
- Edge case handling (bodyless responses, timing violations)

**Must-Have Capabilities (8 Core Features):**
1. NetworkInterceptor class with attach(page) and detach() methods
2. URL pattern matching — string prefix/substring default, one optional regex per interceptor
3. Pattern validation at construction time — clear error on invalid input
4. CapturedResponse dataclass — url, status, headers, raw_bytes as named fields
5. Handler callback invocation — isolated exception handling, crashing handler logs error, does not stop the listener
6. Graceful bodyless response handling — 204, 301, 304 do not crash the listener
7. Dev logging mode — off by default, flag to enable, logs every captured response
8. attach() timing validation — called after page.goto() produces clear actionable error

### Post-MVP Features

**Phase 2 (Growth):**
- WebSocket frame interception
- Streaming response support
- Multiple interceptors on same page with non-overlapping pattern sets
- Auto-deduplication as opt-in flag

**Phase 3 (Expansion):**
- Long-term interface stability for external contributors
- SCR-002 becomes the standard capture layer for every SPA module

### Risk Mitigation Strategy

**Technical Risks:**
- Playwright version changes could break network events → mitigate by version pinning in tests
- Race condition between response.body() await and page navigation → mitigate by wrapping every response.body() call in try/except with graceful skip on failure

**Market Risks:**
- No direct competitors with this specific approach → validate by testing against a real SPA target during implementation

**Resource Risks:**
- Minimal team needed - single developer can implement core MVP

## Functional Requirements

### Network Interception Core

- FR1: Site module developer can register URL patterns to match against network responses
- FR2: Site module developer can provide a callback handler to process captured responses
- FR3: System captures response metadata including URL, status code, and headers
- FR4: System delivers raw response body as bytes to the handler callback

### Pattern Matching

- FR5: System supports string prefix matching for URL patterns (default behavior)
- FR6: System supports substring matching for URL patterns (default behavior)
- FR7: System optionally supports regex-based pattern matching per interceptor instance
- FR8: System validates pattern inputs at construction time and produces clear errors for invalid patterns

### Lifecycle Management

- FR9: Site module developer can attach the interceptor to a Playwright page before navigation
- FR10: System produces a clear, actionable error if attach() is called after page.goto()
- FR11: Site module developer can detach the interceptor from the page when interception is complete
- FR12: System handles late detach gracefully without leaking resources

### Error Handling

- FR13: System handles bodyless responses (204 No Content, 301 Moved Permanently, 304 Not Modified) without crashing the listener
- FR14: System isolates handler callback exceptions - a crashing handler logs an error but does not stop the listener
- FR15: System provides optional dev logging mode that logs every captured response (disabled by default)
- FR16: System produces a warning in dev logging mode when the handler has never fired after navigation completes — catches silent pattern mismatches
- FR17: System handles redirect chains (301/302) where the same logical request produces multiple response events — behaviour is documented and predictable

### Response Capture

- FR18: System captures HTTP status code for each matched response
- FR19: System captures response headers for each matched response
- FR20: System captures raw response body bytes for each matched response
- FR21: System handles race conditions between response.body() await and page navigation gracefully

### Developer Experience

- FR22: Site module developer can use network interception without reading Playwright documentation
- FR23: Interface requires zero Playwright-specific code outside the interceptor itself
- FR24: System provides clear error messages for developer mistakes (timing violations, invalid patterns)

## Non-Functional Requirements

### Integration

- **Playwright Compatibility:** NetworkInterceptor must work with the current stable version of Playwright. Changes to Playwright's network event API should be detected early through version pinning in tests.
- **Downstream Module Contract:** CapturedResponse dataclass must provide data in a format usable by downstream encoding modules (SCR-004/005) without requiring site module developers to understand the raw response structure.
- **Error Propagation:** Errors in the interceptor should not propagate to the calling site module - they should be handled internally with clear logging.

### Reliability

- **Failure Isolation:** The interceptor must not crash the calling site module. All failure modes (bodyless responses, handler exceptions, timing violations, race conditions) must be handled gracefully.
- **Resource Cleanup:** detach() must properly clean up all resources. Late detach (after page closure) should not leak resources.
- **Deterministic Behavior:** The interceptor's behavior must be predictable and deterministic - the same inputs should produce the same outputs.

### Maintainability

- **Interface Stability:** The public API (NetworkInterceptor class, CapturedResponse dataclass) must remain stable. Breaking changes to the interface would require all existing site modules to be updated.
- **Debuggability:** Dev logging mode must provide sufficient information for debugging pattern matching issues without requiring site module developers to add their own logging.
- **Documented Failure Modes:** All known failure modes must be documented so that future maintainers understand the expected behavior.

### Testability

- **Mockable Interface:** The module must be designed so that Playwright's page object can be mocked in tests. The attach() method should accept a mockable page interface.
- **Isolated Failure Mode Testing:** Each failure mode (bodyless responses, handler exceptions, timing violations, race conditions) must be testable in isolation without a real browser.
- **Test Coverage Requirement:** All identified failure modes from brainstorming must be covered by passing tests - 100% coverage of failure modes.