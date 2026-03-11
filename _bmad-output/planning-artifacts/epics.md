---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
---

# scrapamoja - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for scrapamoja, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

**Extraction Mode Management (FR1-FR5):**
- FR1: The system routes to the extraction mode declared in the site module configuration
- FR2: The system supports Direct API Mode for HTTP-based extraction
- FR3: The system supports Intercepted API Mode for network capture (Phase 2)
- FR4: The system supports Hybrid Mode for session-harvested extraction (Phase 2)
- FR5: Developers can explicitly specify which extraction mode to use for a site module

**HTTP Transport / SCR-001 (FR6-FR10):**
- FR6: The system can make HTTP requests without launching a browser
- FR7: The system supports GET, POST, PUT, DELETE methods
- FR8: The system supports chainable request builder interface
- FR9: The system enforces per-domain rate limiting at transport layer (not configurable to global)
- FR10: The system supports concurrent requests without blocking

**Authentication & Credentials (FR11-FR15):**
- FR11: The system supports Bearer token authentication
- FR12: The system supports Basic authentication
- FR13: The system supports Cookie-based authentication
- FR14: The system never logs credentials or auth values
- FR15: Credentials are sourced from environment variables or secrets files, never hardcoded

**Site Module Management (FR16-FR20):**
- FR16: Developers can create new site modules via YAML configuration
- FR17: Site modules declare target endpoint, auth method, and extraction mode
- FR18: Site modules implement enforced output contract interface verified by static type checking
- FR19: Adding a new site module touches only src/sites/ directory
- FR20: Each site module declares the API version of the target site it was built against, enabling staleness detection when the target site changes

**Output & Data Delivery (FR21-FR24):**
- FR21: The system delivers JSON for all structured data to consuming systems
- FR22: The system returns raw bytes as-is for consuming layer to decode
- FR23: The output schema is consistent regardless of extraction mode used
- FR24: Every site module implements documented output contract interface

**Error Handling (FR25-FR28):**
- FR25: The system fails fast and loud when extraction fails
- FR26: The system provides structured errors with context for debugging
- FR27: The system degrades gracefully on schema changes (partial data returned where possible)
- FR28: The system surfaces data timestamp in every response so consuming systems can make freshness decisions

**CLI Interface (FR34-FR35):**
- FR34: The system provides consistent CLI interface across all extraction modes
- FR35: All capabilities available via CLI are also available via Python API

### NonFunctional Requirements

**Performance Requirements:**
- NFR1: Target <1 second latency for direct API calls (vs 5-30 seconds for browser)
- NFR2: Target 90% reduction in memory/CPU per extraction
- NFR3: Target 10-100x faster than browser-based approach
- NFR4: SCR-001 must support concurrent requests without blocking

**Security Requirements:**
- NFR5: Cookies, bearer tokens, and harvested session data must never appear in logs
- NFR6: Request URL, status code, and headers with auth values redacted - not raw tokens
- NFR7: Credentials via environment variables or gitignored secrets file - not hardcoded in YAML
- NFR8: API keys configured in site module config files must not be committed to version control
- NFR9: Redact anything in auth headers and cookie values by default
- NFR10: Opt-in verbose logging for debugging must explicitly warn developer that credentials may appear

**Availability Requirements:**
- NFR11: Target 99%+ successful extractions for supported sites
- NFR12: When extraction fails, fail fast and loud
- NFR13: Structured error with enough context for consuming system to decide: retry, fallback, or alert
- NFR14: Silent failures and empty results are worse than explicit errors

**Maintainability Requirements:**
- NFR15: Adding a new site module must not require changes outside src/sites/ - verified by CI
- NFR16: SCR-001 must contain zero retry logic - retry responsibility belongs exclusively to src/resilience/
- NFR17: Each module independently testable in isolation
- NFR18: Silent failures are prohibited - the system must never return an empty result that is indistinguishable from "no data found"
- NFR19: Protobuf decoder must return partial data and a structured error on schema mismatch - never a naked exception to the consuming system
- NFR20: The stealth module must be replaceable without touching any other module - it is a volatile dependency by design

### Additional Requirements

**From Architecture Document:**
- Brownfield project: Must not break existing FlashScore and Wikipedia scrapers
- Python 3.11+ with asyncio-first architecture required
- httpx as HTTP client for SCR-001
- Output contract enforced via Protocol (duck typing), NOT Pydantic inheritance
- Module structure: src/{module_name}/ with __init__.py and interfaces.py
- Custom token bucket rate limiting, per-domain, enforced at transport layer
- Build Order: Tier 1 (Foundation: SCR-001, SCR-002, SCR-003, SCR-004, SCR-006, SCR-009), Tier 2 (Composite: SCR-005, SCR-007), Tier 3 (Assembly: SCR-008)
- CI boundary check: GitHub Actions validates site modules touch only src/sites/
- Shared error model in src/network/ - the single deliberate cross-boundary import
- Retry logic boundary: SCR-001 raises errors, resilience module handles retries
- Testing: pytest-asyncio
- Data Formats: JSON for structured data, raw bytes for consuming layer decoding

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 7 (Phase 2) | Route to extraction mode declared in config |
| FR2 | Epic 1 | Support Direct API Mode |
| FR3 | Epic 7 (Phase 2) | Support Intercepted API Mode (Phase 2) |
| FR4 | Epic 7 (Phase 2) | Support Hybrid Mode (Phase 2) |
| FR5 | Epic 7 (Phase 2) | Explicit mode specification |
| FR6 | Epic 1 | Make HTTP requests without browser |
| FR7 | Epic 1 | Support GET, POST, PUT, DELETE methods |
| FR8 | Epic 1 | Chainable request builder interface |
| FR9 | Epic 1 | Per-domain rate limiting at transport layer |
| FR10 | Epic 1 | Concurrent requests without blocking |
| FR11 | Epic 2 | Bearer token authentication |
| FR12 | Epic 2 | Basic authentication |
| FR13 | Epic 2 | Cookie-based authentication |
| FR14 | Epic 2 | Never log credentials or auth values |
| FR15 | Epic 2 | Credentials from env vars or secrets files |
| FR16 | Epic 3 | Create site modules via YAML config |
| FR17 | Epic 3 | Declare endpoint, auth method, extraction mode |
| FR18 | Epic 3 (Phase 2) | Output contract interface (SCR-008) |
| FR19 | Epic 3 (Phase 2) | Boundary rule - touch only src/sites/ (SCR-008) |
| FR20 | Epic 3 (Phase 2) | API version declaration (SCR-008) |
| FR21 | Epic 4 | Deliver JSON for structured data |
| FR22 | Epic 4 | Return raw bytes as-is |
| FR23 | Epic 4 | Consistent output schema regardless of mode |
| FR24 | Epic 4 | Implement output contract interface |
| FR25 | Epic 5 | Fail fast and loud on extraction failure |
| FR26 | Epic 5 | Structured errors with context |
| FR27 | Epic 5 | Graceful degradation on schema changes |
| FR28 | Epic 5 | Surface data timestamp in response |
| FR34 | Epic 6 | Consistent CLI across extraction modes |
| FR35 | Epic 6 | CLI and Python API parity |

## Epic List

### Epic 1: HTTP Transport Foundation
The SCR-001 module provides async HTTP transport with chainable request builder, enabling developers to make HTTP requests without launching a browser.
**FRs covered:** FR6, FR7, FR8, FR9, FR10

#### Stories

### Story 1.1: Async HTTP Client Base
As a developer, I want an async HTTP client that can make requests without launching a browser, so that I can achieve millisecond-level latency compared to browser-based extraction.
**Acceptance Criteria:**
- Given a target URL
- When I make a request using the async client
- Then the request completes without launching a browser
- And latency is under 1 second for typical API responses

### Story 1.2: HTTP Method Support
As a developer, I want to use GET, POST, PUT, DELETE methods through a consistent interface, so that I can interact with any API endpoint.
**Acceptance Criteria:**
- Given a target endpoint
- When I specify GET, POST, PUT, or DELETE
- Then the corresponding HTTP method is used
- And the response is returned to the caller

### Story 1.3: Chainable Request Builder
As a developer, I want a chainable request builder interface, so that I can construct complex requests with a fluent, readable syntax.
**Acceptance Criteria:**
- Given I need to build a request with headers, params, body
- When I use chainable methods like .header(), .param(), .body()
- Then each method returns the builder for chaining
- And the final .execute() executes the request

### Story 1.4: Per-Domain Rate Limiting
As a developer, I want per-domain rate limiting enforced at the transport layer, so that my requests don't get blocked due to hitting rate limits.
**Acceptance Criteria:**
- Given multiple requests to the same domain
- When requests exceed the rate limit
- Then requests are queued and executed within the limit
- And different domains don't share rate limits

### Story 1.5: Concurrent Request Support
As a developer, I want to make multiple concurrent requests without blocking, so that I can efficiently poll multiple endpoints.
**Acceptance Criteria:**
- Given I need to make 10 requests to different endpoints
- When I use async gather or similar concurrency
- Then all requests run concurrently
- And no request blocks another

### Epic 2: Authentication & Credentials
Secure handling of various authentication methods for target APIs, with credentials sourced from environment variables and never logged.
**FRs covered:** FR11, FR12, FR13, FR14, FR15

#### Stories

### Story 2.1: Unified .auth() Method
As a developer, I want a single .auth() builder method that accepts bearer token, basic credentials, or cookie jar, so that I can authenticate with any API type using a consistent interface.
**FRs covered:** FR11, FR12, FR13
**Acceptance Criteria:**
- Given I need to authenticate to an API
- When I use .auth(bearer='token'), .auth(basic=('user','pass')), or .auth(cookie=...)
- Then the appropriate auth header is sent
- And the cookie form is tested explicitly for SCR-007 compatibility

### Story 2.2: Credential Security
As a developer, I want credentials sourced from environment variables and automatically redacted from all logs, so that secrets are never hardcoded or accidentally leaked through debug output.
**FRs covered:** FR14, FR15
**Acceptance Criteria:**
- Given credentials configured in environment variables
- When requests are made
- Then credentials are read from env vars
- And auth values never appear in logs

### Epic 3: Site Module Configuration
YAML-based configuration for declaring target endpoints and authentication methods. Site module creation via config files.
**FRs covered:** FR16, FR17
*Note: FR18-FR20 (output contract, boundary rule, API versioning) moved to Phase 2 for SCR-008*

#### Stories

### Story 3.1: YAML Site Configuration
As a developer, I want to configure a site's target endpoint, authentication method, and extraction mode using a YAML file, so that connection details are declared separately from implementation code.
**FRs covered:** FR16, FR17
**Acceptance Criteria:**
- Given a YAML config file
- When the site module loads
- Then endpoint, auth method, and extraction mode are read
- And the transport uses these configurations

### Epic 4: Data Output & Delivery
Consistent JSON delivery regardless of extraction mode, with raw bytes returned as-is for consuming layer decoding.
**FRs covered:** FR21, FR22
*Note: FR23 and FR24 move to Phase 2 when SCR-008 is built*

#### Stories

### Story 4.1: Raw Response Delivery
As a developer, I want SCR-001 to return the raw httpx.Response object without decoding or wrapping, so that the calling layer decides how to handle the content — whether as JSON, bytes, or any other format.
**FRs covered:** FR21, FR22
**Acceptance Criteria:**
- Given an HTTP response
- When SCR-001 returns
- Then the raw httpx.Response is returned
- And the caller decides parsing strategy

### Epic 5: Error Handling & Resilience
Fail-fast error handling with structured errors, graceful degradation on schema changes, and data timestamps for freshness decisions.
**FRs covered:** FR25, FR26, FR28
*Note: FR27 moves to Phase 2 with SCR-005*

#### Stories

### Story 5.1: Structured Fail-Fast Errors
As a developer, I want the system to fail immediately with a structured error containing module, operation, URL, status code, and detail — so that failures are visible and debuggable without guessing what went wrong.
**FRs covered:** FR25, FR26
**Acceptance Criteria:**
- Given an error condition
- When the request fails
- Then a structured error is raised with module, operation, URL, status_code, detail
- And the error can be parsed programmatically

### Story 5.2: Data Timestamps
As a consuming system, I want the HTTP response date header surfaced in every response, so that I can make data freshness decisions without parsing the response body.
**FRs covered:** FR28
**Acceptance Criteria:**
- Given an HTTP response
- When the response is returned
- Then response.headers.get('date') is surfaced
- And the caller can make freshness decisions

### Epic 6: CLI for Direct API Mode
Command-line interface for SCR-001's Direct API mode, with consistent patterns that will extend to other modes in Phase 2.
**FRs covered:** FR34, FR35
*Note: Cross-mode consistency validated in Phase 2*

#### Stories

### Story 6.1: CLI Interface
As a developer, I want a consistent CLI interface for Direct API mode, so that I can interact with the scraper from the command line.
**FRs covered:** FR34
**Acceptance Criteria:**
- Given the CLI is installed
- When I run scrape commands
- Then the command works consistently for Direct API mode

### Story 6.2: CLI and Python API Parity
As a developer, I want all CLI capabilities available via Python API, so that I can use the library programmatically with feature parity.
**FRs covered:** FR35
**Acceptance Criteria:**
- Given a capability available via CLI
- When I use the Python API
- Then the same functionality is accessible
- And both interfaces are consistent

### Epic 7: Extraction Mode Support (Phase 2)
Routing between extraction modes (Direct API, Intercepted, Hybrid). Moved to Phase 2 since only Direct API mode exists initially.
**FRs covered:** FR1, FR2, FR3, FR4, FR5
*Note: FR1-FR2 implicitly satisfied by SCR-001 existing; FR3-FR5 are Phase 2*

#### Stories

### Story 7.1: Mode Declaration and Routing
As a developer, I want to declare the extraction mode in the site module config and have the framework route to it automatically, so that mode selection is explicit and predictable.
**FRs covered:** FR1, FR2, FR5
**Note:** Direct API Mode already built in Epic 1

### Story 7.2: Intercepted API Mode (Phase 2)
As a developer, I want to use Intercepted API Mode for network capture, so that I can extract data from sites that require browser initialization.
**FRs covered:** FR3 - SCR-002

### Story 7.3: Hybrid Mode (Phase 2)
As a developer, I want to use Hybrid Mode for session-harvested extraction, so that I can combine browser session with direct HTTP.
**FRs covered:** FR4 - SCR-007

---

## Phase 1 Stories Summary (SCR-001 Scope)

### Epic 1: HTTP Transport Foundation
- Story 1.1: Async HTTP Client Base
- Story 1.2: HTTP Method Support
- Story 1.3: Chainable Request Builder
- Story 1.4: Per-Domain Rate Limiting
- Story 1.5: Concurrent Request Support

### Epic 2: Authentication & Credentials
- Story 2.1: Unified .auth() Method (Bearer, Basic, Cookie)
- Story 2.2: Credential Security (Env vars + log redaction)

### Epic 3: Site Module Configuration
- Story 3.1: YAML Site Configuration

### Epic 4: Data Output & Delivery
- Story 4.1: Raw Response Delivery

### Epic 5: Error Handling & Resilience
- Story 5.1: Structured Fail-Fast Errors
- Story 5.2: Data Timestamps (HTTP date header)

### Epic 6: CLI for Direct API Mode
- Story 6.1: CLI Interface
- Story 6.2: CLI and Python API Parity

---

## Implementation Notes for BMAD Agent

1. **Epic 1 - Story 1.1 and 1.3** are tightly coupled — the async client base and chainable builder are the same object. Build together in same PR.

2. **Epic 2 - Story 2.1** cookie form is most critical — SCR-007 uses it to inject harvested session credentials. Test explicitly.

3. **Epic 7 (Phase 2)** stories should be implemented when SCR-002, SCR-007 are in scope.

<!-- Epic breakdown to be completed in Step 02 -->

