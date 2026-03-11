---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments: []
workflowType: 'prd'
author: Tisone
date: '2026-03-11'
projectName: scrapamoja
status: 'complete'
documentCounts:
  productBrief: 1
  research: 0
  brainstorming: 1
  projectDocs: 4
classification:
  projectType: api_backend
  domain: general
  complexity: medium
  projectContext: brownfield
---

# Product Requirements Document - scrapamoja

**Author:** Tisone
**Date:** 2026-03-11

<!-- 
PRD Structure:
1. Introduction & Overview
2. Problem Statement
3. User Stories & Personas
4. Functional Requirements
5. Non-Functional Requirements
6. Technical Architecture
7. UI/UX Requirements
8. Edge Cases & Error Handling
9. Dependencies & Integrations
10. Out of Scope
11. Glossary & Terminology
-->

## Executive Summary

**Scrapamoja** is evolving from a browser-only scraping engine to a **hybrid browser-API scraping platform** that chooses the optimal extraction method based on each target site's architecture and protection mechanisms.

### What Makes This Special

Scrapamoja is the first scraping framework built around the reality that modern SPAs use the DOM only as a visual layer — the actual data lives in network traffic beneath. It offers a unified interface that automatically selects between:

- **DOM Mode** (existing): Navigate with browser, extract from rendered HTML
- **Direct API Mode** (new): Skip browser, call APIs directly for millisecond-level latency
- **Intercepted API Mode** (Phase 2): Browser unlocks, capture from network traffic
- **Hybrid Mode** (Phase 2): Browser once to harvest session, then direct HTTP

This eliminates context-switching — developers use one framework that adapts to each site.

### Problem Statement

Current scraping frameworks were designed for a web that no longer exists. Modern SPAs expose clean APIs with a UI layer on top, but scraping tools still launch full browsers to extract data that was already available in JSON — wasting seconds of latency and heavy compute resources.

### Target Users

- **Primary:** Developers building site-specific scrapers using the Scrapamoja framework
- **Secondary:** DevOps engineers maintaining scraping infrastructure

### Project Classification

- **Project Type:** API Backend / Developer Tool
- **Domain:** General (web scraping, data extraction)
- **Complexity:** Medium to High
- **Project Context:** Brownfield (existing Scrapamoja project being extended)

## Success Criteria

### User Success

A developer adds a new site module, configures the endpoint, runs it, and gets structured data back in under a second — without touching browser code, without writing an HTTP client, without handling auth manually. The moment of success: when they delete the Playwright dependency from a scraper that never needed it.

### Business Success

**3-Month Success:**
- SCR-001 through SCR-008 are all built and tested
- At least one site module per extraction mode is live and documented as a reference implementation
- Zero regressions in existing FlashScore and Wikipedia scrapers
- AiScore schema change detection in place with graceful degradation

**12-Month Success:**
- Scrapamoja supports five or more sites across all four extraction modes
- Framework documented well enough that a new developer can add a site module without reading source code
- Infrastructure costs for ScoreWise data pipeline are measurably lower than browser-only approach

### Technical Success

**KPIs:**
- **Latency:** Target <1 second for direct API calls (vs 5-30 seconds for browser)
- **Resource Usage:** Target 90% reduction in memory/CPU per extraction
- **Success Rate:** Target 99%+ successful extractions for supported sites
- **Speed:** Target 10-100x faster than browser-based approach

**Maintainability Requirements:**
- Resilience module handles all retry logic — SCR-001 has zero retry code of its own
- Adding any new site module touches only `src/sites/` — if adding a new site requires changes anywhere else in the codebase, the module boundaries have failed
- Protobuf decoder must degrade gracefully — return partial data or clear error, never silent failure

### Technical Risk

- AiScore's protobuf schema is undocumented and could change without notice
- Must handle schema changes with clear error reporting

## Product Scope

### MVP - Minimum Viable Product

- SCR-001 functional as shared HTTP transport
- At least one site module using Direct API mode end-to-end
- Existing scrapers completely unaffected

### Growth Features (Post-MVP)

- SCR-002 through SCR-007 complete
- At least one site module per extraction mode live
- Health check capability operational

### Vision (Future)

- All four extraction modes documented and usable by external developers
- Framework published as an installable package
- Plugin architecture so community can add site modules independently
- Documentation enables a developer who has never seen Scrapamoja's internals to add a new site module

## User Journeys

### Journey 1 — Developer Success Path

A developer needs to add a new sports odds site to Scrapamoja. They look at the existing AiScore module as a reference implementation. They see the pattern — configure endpoint, declare auth method, choose extraction mode, map response to output schema. They copy the structure, point it at the new site, run it. Data comes back in milliseconds. They never open Playwright docs. They never write an HTTP client. The framework handled it. They are done in an afternoon.

**Requirements Revealed:**
- Clear reference implementation modules with documented patterns
- Configuration-driven site module creation (no code required beyond config)
- Unified output schema regardless of extraction mode used

---

### Journey 2 — Developer Edge Case

The same developer points Scrapamoja at a new site and the response comes back as binary. The encoding detector identifies it as protobuf. The protobuf decoder attempts extraction and the schema does not match — the site changed their API. Instead of a silent empty result or a cryptic exception, Scrapamoja returns a structured error: what it received, what it tried, where it failed, and which fields it managed to extract before failure. The developer knows exactly what changed and where to look. They update the field map and rerun. No debugging blind spots.

**Requirements Revealed:**
- Graceful degradation on schema changes
- Structured error reporting with context
- Partial data extraction with clear failure points

---

### Journey 3 — DevOps Path

An ops engineer needs to verify the scraping pipeline is healthy before a match day. They run the health check against all configured API endpoints. Green means reachable and responding within acceptable latency. Red means the endpoint is down or responding too slowly — with the exact status code and response time logged. They do not need to understand the scraping logic. They just need signal. Scrapamoja gives them signal.

**Requirements Revealed:**
- Health check capability for all endpoints
- Latency monitoring and alerting
- Simple status output (green/red) for operations

---

### Journey 4 — System Integration Path

ScoreWise polls Scrapamoja for odds data every few minutes. It does not care which extraction mode was used — it receives a consistent output schema regardless of whether the data came from a browser scrape, a direct API call, or a network intercept. The output contract never changes even when the extraction method underneath does. ScoreWise never needs to be updated when Scrapamoja switches a site from DOM mode to Direct API mode.

**Requirements Revealed:**
- Consistent output schema across all extraction modes
- Stable API contract for downstream consumers
- Mode-agnostic data delivery

---

### Journey Requirements Summary

| Capability Area | Required |
|-----------------|----------|
| Site module creation | Configuration-driven, reference implementations |
| Error handling | Structured errors with context, partial extraction |
| Monitoring | Health checks, latency alerts |
| Integration | Consistent output schema, stable API contract |

## Domain-Specific Requirements

### Security Considerations

**Credentials & Authentication:**
- Cookies, bearer tokens, and harvested session data must never appear in logs
- Request URL, status code, and headers with auth values redacted — not raw tokens
- Credentials via environment variables or gitignored secrets file — not hardcoded in YAML
- API keys configured in site module config files must not be committed to version control

**Logging Standard:**
- Redact anything in auth headers and cookie values by default
- Opt-in verbose logging for debugging must explicitly warn developer that credentials may appear

---

### Privacy Considerations

- Scrapamoja scrapes public sports data — no personal data, no PII
- Request URLs can contain identifiable parameters — redact in logging
- Default: redact auth headers and cookie values
- Verbose logging: opt-in with explicit warning

---

### Performance Requirements

**Concurrency:**
- SCR-001 must support concurrent requests without blocking
- Multiple site modules polling simultaneously cannot queue behind each other

**Rate Limiting:**
- **Per-domain rate limiting is a HARD requirement for SCR-001** — not a configuration option
- Rate limiting enforced at transport layer, not left to caller
- Global rate limiting is incorrect behavior

---

### Availability Requirements

**Error Handling:**
- When extraction fails, fail fast and loud
- Structured error with enough context for consuming system to decide: retry, fallback, or alert
- Silent failures and empty results are worse than explicit errors

**Fallback Tiers (Pattern):**
1. Primary extraction mode fails
2. Retry via resilience module
3. Fallback to alternative extraction mode
4. Alert consuming system

---

### Integration Requirements

**Output Schema:**
- **Every site module must implement a documented output contract interface**
- This is an **enforced interface**, not an informal convention
- Consistent output schema regardless of extraction mode

**Output Format:**
- JSON for all structured data
- Raw bytes returned as-is for consuming layer to decode

---

### Key Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Site changes API schema | Decoder degrades gracefully, structured error surfaced, partial data returned |
| IP banned for rate limit violation | Per-domain rate limiting enforced at transport layer |
| Cloudflare detection updated | Stealth module treated as volatile — designed to be replaced, not patched |
| Credentials leaked in logs | Auth values redacted by default in all logging output |
| Stale data corrupts predictions | Data timestamp and cache age surfaced in every response |
| Site module breaks existing scrapers | Boundary rule enforced — new site modules touch only `src/sites/`, CI catches violations |

## Innovation & Novel Patterns

### Innovation Assessment

**Is this genuine innovation?**
Partially. The individual pieces are not new — httpx exists, Playwright exists, network interception exists, protobuf decoding exists. What is genuinely novel is the **unification under a single framework with a consistent developer interface and automatic mode selection**. No existing scraping framework treats these as equivalent extraction modes on the same abstraction level.

- Scrapy is DOM-only
- Playwright is browser-only
- requests/httpx is HTTP-only

Developers currently wire these together themselves, outside any framework. Scrapamoja makes that wiring the framework's job, not the developer's.

**That is real innovation — not at the component level, but at the abstraction level.**

---

### Key Differentiator

The insight that **the extraction mode is a property of the target site, not a choice the developer makes**. Every other tool puts the decision on the developer — you pick the right tool for the job.

**Scrapamoja inverts that.** The site module declares what the target looks like, and the framework routes to the correct extraction mode. Developers stop thinking about transport and start thinking about data.

---

### Validation Approach

**Three validation gates, in order:**

1. **Gate 1:** AiScore module ships and feeds ScoreWise with real odds data in under one second
   - Proves Direct API Mode works in production, not just in tests

2. **Gate 2:** A developer who did not build Scrapamoja adds a new site module in under a day using only documentation
   - Proves the abstraction is learnable, not just internally coherent

3. **Gate 3:** The same site module works unchanged when the extraction mode underneath is swapped — for example switching from Direct API to Hybrid Mode without touching the site module code
   - Proves the output contract abstraction is real, not theoretical

**If all three gates pass, the innovation claim holds. If any gate fails, the abstraction has a gap.**

---

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Abstraction leak - developers still need to understand transport | Better documentation, reference implementations |
| Mode selection chooses wrong mode | Build in observability to see which mode was used |
| Output contract not truly enforced | Output contract verified by static type checking |

## API Backend / Developer Tool Specific Requirements

### Interface Types

Scrapamoja is a framework, not a service — it does not expose HTTP endpoints itself. It exposes three interfaces:

1. **CLI** — the primary developer interface, consistent across all extraction modes
   - `python -m src.sites.<site>.cli.main scrape --date 20260310` works the same way regardless of underlying mode
   - *Note: `aiscore` in examples is for illustration — the CLI interface must be consistent across all site modules*

2. **Python API** — the programmatic interface for consuming systems like ScoreWise
   - Import the site module, call it, get structured output back

3. **Config interface** — YAML-based site module configuration
   - Declares endpoint, auth method, extraction mode, and output schema mapping

**All three must be consistent.** A developer should be able to do anything via CLI that they can do via Python API.

---

### Authentication

Two layers, kept completely separate:

- **Scrapamoja itself** has no authentication — it is a local framework, not a service
- **Target site credentials** are handled by site module config
  - Sourced from environment variables or secrets file
  - Never hardcoded
  - Never logged

The `.auth()` builder method on SCR-001 accepts credentials at request time — bearer, basic, or cookie form.

---

### Data Formats

- **Input:** YAML config files, CLI arguments, Python function calls
- **Output:** JSON for all structured data surfaced to consuming systems
- **Internal:** Raw HTTP response object, unwrapped returned between modules
  - Encodings layer decodes
  - Site module shapes
  - Output contract delivers JSON
- **ScoreWise always receives JSON** regardless of what the source returned

---

### Rate Limiting

- **Per-domain, enforced at transport layer in SCR-001**
- Not configurable to global
- Each site module config declares its own rate limit for its target domain
- Two site modules polling different domains simultaneously do not affect each other's rate limits

---

### Versioning

Two things version independently:

1. **Framework versioning** — standard semantic versioning via standard Python packaging conventions
   - Breaking changes to output contract Protocol or HttpClient interface bump major version

2. **Site module versioning** — each module declares API version of its target
   - When target site changes API, module version bumps
   - Changelog records what changed
   - This is how developers know whether their site module is stale

---

### SDK

**No SDK for now.** Scrapamoja is Python-only and that is the right call for now. It is a framework consumed by Python developers building Python scrapers.

A multi-language SDK is a distraction until the framework is proven and stable. The validation gates from the Innovation step must pass first. SDK is a post-vision consideration at the earliest.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-Solving MVP — prove the technical approach works first. The developer experience can be polished once the extraction pipeline is proven end-to-end. Trying to nail the developer experience before the protobuf decoder reliably extracts odds data from AiScore is the wrong order. Prove the data flows correctly first. Then smooth the edges.

**Resource Requirements:** Solo developer — you. The build order document was deliberately designed for sequential solo development. Each module is independently completable in isolation.

**Minimum External Dependency:** A live AiScore account or confirmed access to `api.aiscore.com` before SCR-008 begins. Everything up to SCR-007 can be built and tested with mock responses.

---

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Developer Success Path: Adding a new site module with Direct API mode
- System Integration Path: ScoreWise consuming Scrapamoja output

**Must-Have Capabilities:**
- SCR-001 functional as shared HTTP transport with per-domain rate limiting
- At least one site module (AiScore) using Direct API mode end-to-end
- Output contract enforced via static type checking
- Existing scrapers completely unaffected

---

### Post-MVP Features

**Phase 2 (Growth):**
- SCR-002 through SCR-007 complete
- At least one site module per extraction mode live
- Health check capability operational
- Documentation enables new developer to add site module
- **Response caching with TTL for high-frequency polling scenarios (deferred from MVP)**

**Phase 3 (Expansion):**
- All four extraction modes documented and usable by external developers
- Framework published as installable package
- Plugin architecture for community site modules

---

### Risk Mitigation Strategy

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AiScore protobuf schema changes before SCR-008 ships | Highest | High | Build SCR-005 with graceful degradation, validate schema against live traffic as last step |
| SCR-007 interface design is wrong | Medium | Highest | **SCR-007 must go through the same brainstorming and interface design process as SCR-001 before implementation begins** — same BMAD process for explicit interface design |
| Cloudflare detection updates between build and integration | Medium | Medium | Build SCR-003 with clean boundary, treat as volatile |

---

**Fastest Path to Validation:**
AiScore module feeding ScoreWise with real odds data in under one second. This is the single external signal that proves the entire SCR-001 through SCR-008 chain works in production.

## Functional Requirements

### Extraction Mode Management

- FR1: The system routes to the extraction mode declared in the site module configuration
- FR2: The system supports Direct API Mode for HTTP-based extraction
- FR3: The system supports Intercepted API Mode for network capture **(Phase 2)**
- FR4: The system supports Hybrid Mode for session-harvested extraction **(Phase 2)**
- FR5: Developers can explicitly specify which extraction mode to use for a site module

**Note:** DOM Mode is existing behavior. All new work must leave it completely unaffected.

---

### HTTP Transport (SCR-001)

- FR6: The system can make HTTP requests without launching a browser
- FR7: The system supports GET, POST, PUT, DELETE methods
- FR8: The system supports chainable request builder interface
- FR9: The system enforces per-domain rate limiting at transport layer (not configurable to global)
- FR10: The system supports concurrent requests without blocking

---

### Authentication & Credentials

- FR11: The system supports Bearer token authentication
- FR12: The system supports Basic authentication
- FR13: The system supports Cookie-based authentication
- FR14: The system never logs credentials or auth values
- FR15: Credentials are sourced from environment variables or secrets files, never hardcoded

---

### Site Module Management

- FR16: Developers can create new site modules via YAML configuration
- FR17: Site modules declare target endpoint, auth method, and extraction mode
- FR18: Site modules implement enforced output contract interface verified by static type checking.
- FR19: Adding a new site module touches only src/sites/ directory
- FR20: Each site module declares the API version of the target site it was built against, enabling staleness detection when the target site changes

---

### Output & Data Delivery

- FR21: The system delivers JSON for all structured data to consuming systems
- FR22: The system returns raw bytes as-is for consuming layer to decode
- FR23: The output schema is consistent regardless of extraction mode used
- FR24: Every site module implements documented output contract interface

---

### Error Handling

- FR25: The system fails fast and loud when extraction fails
- FR26: The system provides structured errors with context for debugging
- FR27: The system degrades gracefully on schema changes (partial data returned where possible)
- FR28: The system surfaces data timestamp in every response so consuming systems can make freshness decisions

---

### Health Monitoring

- FR29: The system provides health check capability for all configured endpoints
- FR30: Health checks return latency and status code information

---

### Encoding Detection

- FR31: The system automatically detects response encoding/format
- FR32: The system decodes protobuf responses
- FR33: The system handles JSON, gzip, Brotli formats

---

### CLI Interface

- FR34: The system provides consistent CLI interface across all extraction modes
- FR35: All capabilities available via CLI are also available via Python API

## Non-Functional Requirements

### Performance

- **NFR1:** Direct API calls complete in under 1 second (vs 5-30 seconds for browser)
- **NFR2:** Target 90% reduction in memory/CPU per extraction
- **NFR3:** Target 10-100x faster than browser-based approach
- **NFR4:** Support concurrent requests without blocking
- **NFR5:** Rate limiting enforced per-domain, not global

---

### Security

- **NFR6:** Credentials (cookies, bearer tokens, session data) must never appear in logs
- **NFR7:** Auth values redacted in all logging output by default
- **NFR8:** Credentials sourced from environment variables or gitignored secrets files
- **NFR9:** API keys configured in site module config files must not be committed to version control
- **NFR10:** Opt-in verbose logging must warn developer that credentials may appear

---

### Integration

- **NFR11:** Output schema is consistent regardless of extraction mode used
- **NFR12:** All structured data delivered as JSON to consuming systems
- **NFR13:** Health checks available for all configured endpoints
- **NFR14:** Data timestamp surfaced in every response

---

### Maintainability

- **NFR15:** Adding a new site module must not require changes outside src/sites/ — verified by CI
- **NFR16:** SCR-001 must contain zero retry logic — retry responsibility belongs exclusively to src/resilience/
- **NFR17:** Each module must be independently testable in isolation without depending on other Scrapamoja modules being running or configured

---

### Reliability

- **NFR18:** Silent failures are prohibited — the system must never return an empty result that is indistinguishable from "no data found"
- **NFR19:** Protobuf decoder must return partial data and a structured error on schema mismatch — never a naked exception to the consuming system
- **NFR20:** The stealth module must be replaceable without touching any other module — it is a volatile dependency by design

---

---

## Appendix: Glossary & Terminology

| Term | Definition |
|------|------------|
| DOM Mode | Existing browser-based scraping mode using Playwright |
| Direct API Mode | New mode that bypasses browser for HTTP API calls |
| Intercepted API Mode | Phase 2 mode that captures network traffic |
| Hybrid Mode | Phase 2 mode that uses browser session then direct HTTP |
| SCR-001 through SCR-009 | Feature IDs from the Build Order document |
| Output Contract | Enforced Python Protocol for consistent output schema |
| Site Module | Config-driven scraper for a specific target site |
