---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments: ["_bmad-output/brainstorming/brainstorming-session-2026-03-10-15-18-25.md", "_bmad-output/project-context.md"]
date: 2026-03-10
author: Tisone
---

# Product Brief: scrapamoja

## Executive Summary

**Scrapamoja** is evolving from a browser-only scraping engine to a **hybrid browser-API scraping platform** that can choose the optimal extraction method based on the target site's architecture and protection mechanisms.

The core problem: Current browser-based scraping is too slow (seconds vs milliseconds) and resource-heavy (high memory/CPU) for high-frequency polling use cases like ScoreWise odds updates.

The solution: Add direct API calling capability that bypasses the browser entirely when the target site exposes accessible API endpoints — delivering data in milliseconds with minimal resources.

---

## Core Vision

### Problem Statement

Scrapamoja currently requires a Playwright browser for every data extraction task. While appropriate for sites requiring rendered pages, this approach is wasteful when the target is a known open API that can be called directly with simple HTTP requests.

### Problem Impact

- **Latency**: Browser launches take seconds; direct API calls return in milliseconds
- **Resource consumption**: Each browser session consumes significant memory and CPU
- **Scalability**: Cannot support high-frequency polling (e.g., odds updates every few minutes)
- **Cost**: Higher infrastructure costs for browser-based infrastructure

### Proposed Solution

Add a **Direct API extraction mode** that bypasses the browser entirely for accessible API endpoints. This is the first of four planned extraction modes:

1. **DOM Mode** (existing) - Navigate with browser, extract from HTML
2. **Direct API Mode** (new) - Skip browser, call API directly  
3. **Intercepted API Mode** (new) - Browser unlocks, capture from network
4. **Hybrid Mode** (new) - Browser once, harvest session, then direct HTTP

### Key Differentiators

- **Adaptive extraction**: Choose the right tool for each site
- **Async-first architecture**: Built for high-frequency polling from day one
- **Unified interface**: Same CLI and config patterns across all modes
- **Internal reuse**: HTTP transport designed for other Scrapamoja modules

---

## Target Users

### Primary Users

**1. Scrapamoja Developers** (Primary)
- **Role**: Backend developers who build and extend site-specific scrapers using the Scrapamoja framework
- **Pain Points**: 
  - Current browser-based scraping is too slow (seconds vs milliseconds)
  - High memory/CPU usage limits scalability
  - Difficulty with modern SPAs and Cloudflare-protected sites
  - High maintenance burden when sites change their structure
- **Success Vision**: Faster data extraction, less resource consumption, easier handling of protected sites, reduced maintenance

**2. DevOps Engineers** (Secondary)
- **Role**: Team members who maintain scraping infrastructure and ensure reliable data pipelines
- **Pain Points**: 
  - Browser-based scrapers consume too many resources
  - High infrastructure costs
  - Difficulty scaling for high-frequency polling
- **Success Vision**: Lightweight scrapers that scale easily, lower infrastructure costs, reliable automated pipelines

### Secondary Users

**3. Data Analysts/Consumers**
- **Role**: Team members who consume the scraped data for analysis, predictions, or business insights
- **Pain Points**:
  - Data delays due to slow scraping
  - Missing data during browser failures
- **Success Vision**: Fast, reliable data delivery for downstream applications

---

## Success Metrics

### User Success Criteria
- **Data extraction in under 1 second** (vs current seconds with browser)
- **Reduced resource consumption** - significantly lower memory and CPU usage
- **High-frequency polling capability** - ability to poll every few minutes without performance degradation
- **Reliability** - successful data extraction consistently

### Business Objectives
- **Lower infrastructure costs** - reduce compute/resources needed for scraping
- **Scalability** - ability to handle more scraping jobs with same infrastructure
- **Maintainability** - easier to maintain scrapers with unified interface

### Key Performance Indicators (KPIs)
1. **Latency**: Target <1 second for direct API calls (vs 5-30 seconds for browser)
2. **Resource Usage**: Target 90% reduction in memory/CPU per extraction
3. **Success Rate**: Target 99%+ successful extractions for supported sites
4. **Extraction Speed**: Target 10-100x faster than browser-based approach

---

## MVP Scope

### Core Features (MVP)

**Direct API Mode (SCR-001)** - The MVP focuses on this single feature:

1. **HTTP Client**
   - Async-first HTTP client using httpx
   - Support for GET, POST, PUT, DELETE methods
   - Request/response handling
   - **Chainable Request Builder Interface** (from brainstorming session):
     ```python
     client = HttpClient(base_url="https://api.example.com")
     response = (client
         .get("/matches")
         .header("Authorization", "Bearer token")
         .param("sport_id", 2)
         .timeout(30)
         .execute())
     ```

2. **Authentication**
   - Bearer token support
   - Basic auth support  
   - Cookie-based authentication (for session compatibility with SCR-007)

3. **Resilience**
   - Rate limiting support
   - **Retry logic delegated to src/resilience/ module** - SCR-001 does not implement retries internally
   - Timeout handling

4. **CLI Integration**
   - Unified CLI interface consistent with existing Scrapamoja patterns
   - Configuration via site config files

5. **Response Caching**
   - Built-in response caching with TTL for polling scenarios

### Out of Scope for MVP (Phase 2)

The following features are deferred to Phase 2:

- **Network Interception** (SCR-002) - Capturing API responses during browser sessions
- **Cloudflare Support** (SCR-003) - Bypassing bot detection
- **Auto Encoding Detection** (SCR-004) - Automatic format detection
- **Protobuf Decoding** (SCR-005) - Binary response handling
- **Session Harvesting** (SCR-006) - Extracting browser session credentials
- **Session Bootstrap Mode** (SCR-007) - Browser + direct HTTP hybrid

### MVP Success Criteria

1. **Functional**: Site module can use Direct API mode without browser dependency
2. **Performance**: Data returned from open API in under 1 second
3. **Usability**: Mode selectable via CLI flag and config file
4. **Reliability**: Rate limiting and retry logic work correctly
5. **Isolation**: Existing browser-based modules completely unaffected

### Future Vision

If successful, Scrapamoja will evolve into a **full Hybrid Browser-API Scraping Engine** with four extraction modes:

1. **DOM Mode** (existing) - Navigate with browser, extract from HTML
2. **Direct API Mode** (MVP) - Skip browser, call API directly  
3. **Intercepted API Mode** (Phase 2) - Browser unlocks, capture from network
4. **Hybrid Mode** (Phase 2) - Browser once, harvest session, then direct HTTP

This creates a flexible scraping platform that can choose the optimal extraction method based on each target site's architecture and protection mechanisms.
