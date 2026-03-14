---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/brainstorming/brainstorming-session-2026-03-14-0500.md
  - _bmad-output/project-context.md
date: 2026-03-14
author: Tisone
status: complete
---

# Product Brief: SCR-002 Network Response Interception

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

SCR-002 Network Response Interception enables Scrapamoja to extract data from modern SPAs by capturing API responses at the network layer before they reach the DOM. This transforms Scrapamoja from a DOM-only scraper into a hybrid extraction platform capable of targeting any web architecture.

---

## Core Vision

### Problem Statement

Modern web applications are SPAs that load data dynamically via internal API calls. The data never appears in the HTML DOM in a usable form. Scrapamoja's current DOM scraping approach cannot extract this data reliably. Developers building site modules for these targets have no extraction path today.

### Problem Impact

- Developers attempt DOM scraping on SPAs and get empty or incomplete data because content renders after JavaScript execution
- wait_for_selector workarounds are fragile, timing-dependent, and break when sites change rendering logic
- Direct API calls are blocked immediately by Cloudflare or bot detection
- No supported path exists in Scrapamoja for intercepting network responses
- **Hard blocker:** SCR-008 (AiScore) and any future SPA site modules cannot be built without this capability

### Why Existing Solutions Fall Short

- **Raw Playwright is DIY:** page.on("response") exists but requires handling all failure modes (bodyless responses, handler isolation, lifecycle management, pattern matching, version changes) — every developer re-implements incompletely
- **Scrapy:** Pure HTTP, no browser integration
- **Selenium:** No equivalent network event system
- **No framework integration:** No existing solution provides this as a reusable, tested, framework-integrated module

### Proposed Solution

A generic, reusable network interception module in `src/network/` that:
- Attaches to a Playwright page before navigation
- Listens for responses matching registered URL patterns
- Delivers raw bytes via callback to the calling site module
- No storage, no decoding, no site-specific logic — pure capture and notification
- All failure handling (bodyless responses, handler exceptions, cleanup) is built in

### Key Differentiators

- **Architectural fit:** Slots directly into Scrapamoja's existing module boundary model — receives page from `src/browser/`, delivers raw bytes to `src/encodings/`, site modules consume it without knowing Playwright exists
- **Composability moat:** SCR-002 + SCR-003 + SCR-004 + SCR-005 + SCR-007 compose into a complete hybrid extraction pipeline — competitors reimplementing just interception get a fraction of the value
- **Timing:** SPAs are now dominant for high-value data sources (sports, finance, betting); Playwright is mature and stable
- **Separation of concerns:** SCR-002 stops at raw bytes, hands off to SCR-004/005 for decoding — this design choice makes the module reusable across every future site regardless of encoding format

---

## Target Users

### Primary Users

**Scrapamoja Site Module Developers**

The primary user is a Python developer building a Scrapamoja site module for a SPA-based target. They are not Playwright experts — they know enough to navigate pages and extract data, but they have not thought deeply about network event systems.

**Context & Motivation:**
- Building new site modules for data sources (sports, finance, betting)
- Want to focus on data extraction logic, not browser internals
- Motivated by being able to target ANY web architecture, not just DOM-scrapeable sites

**Problem Experience:**
- Navigate to target page, run selectors, get nothing
- Inspect page, realize data loads dynamically via JavaScript
- Try wait_for_selector — fragile, timing-dependent, breaks on site changes
- Look at DevTools network tab, see API call, try direct HTTP — 403 blocked
- **Stuck with no clear path forward inside Scrapamoja framework**

**Success Vision:**
- Find NetworkInterceptor in src/network/
- Read interface: three methods, pattern list, handler — immediately understood
- Attach before page.goto(), navigate, handler fires with exactly the data from DevTools
- **"The framework solved the hard part. I just registered a pattern."**

**Usage Pattern (Four Steps):**
1. Instantiate NetworkInterceptor with target URL pattern and handler function
2. Call attach(page) before navigation
3. Navigate, handle captured responses in callback
4. Call detach() when done

### Secondary Users

**Future External Contributors**
- Inherit a working interception layer without needing to understand Playwright's network event system
- Interface is the same regardless of familiarity with codebase
- Documentation determines ease of adoption, not interface design

### User Journey

1. **Discovery:** Encounter SPA blocker in existing scraping approach → Search codebase → Find SCR-002 in src/network/
2. **Onboarding:** Read simple interface (3 methods) → Understand pattern + handler concept → Integrate in minutes
3. **Core Usage:** Attach before navigation → Navigate → Receive raw bytes in callback → Pass to downstream decoders
4. **Success Moment:** Handler fires with exact data from DevTools → "This just works"
5. **Long-term:** SPA targets no longer blockers → New decision branch: DOM fails → Try network interception

---

## Success Metrics

### User Success Criteria

**Module Level:** SCR-002 is considered successful when a site module developer can integrate network interception in a new site module without reading Playwright documentation or handling any Playwright internals themselves. The interface is self-sufficient.

**Framework Level:** SCR-008 (AiScore) can be built using SCR-002 as its capture layer — the first real-world proof. If AiScore cannot be built on top of SCR-002 without modifications to SCR-002 itself, the module is not generic enough.

**Quality Level:** All failure modes identified in brainstorming are handled correctly:
- Bodyless responses do not crash the listener
- Handler exceptions do not propagate
- Late detach does not leak
- Silent pattern mismatches surface in dev mode
- A developer using SCR-002 incorrectly gets a clear error, not silent failure

**User Quote:** "I found the endpoint in DevTools, registered the pattern, and it worked. I never had to think about Playwright."

### Business Objectives

**3 Months:**
- SCR-002 is merged, tested, and SCR-008 (AiScore) is buildable on top of it
- The hybrid pipeline has its first real proof point
- ScoreWise has a working data feed

**12 Months:**
- Multiple site modules exist that use SCR-002 as their capture layer
- New SPA targets are unblocked by default
- Remaining hybrid pipeline features (SCR-003 through SCR-007) are built on the foundation SCR-002 provides

**Strategic Contribution:**
- SCR-002 is the second pillar of the hybrid extraction platform, after SCR-001
- Defines Scrapamoja as "a framework that can extract structured data from any web architecture"
- This positioning is the long-term moat

### Key Performance Indicators

| Metric | Target |
|--------|--------|
| New site module using SCR-002 requires zero Playwright-specific code outside the interceptor | 100% |
| All brainstorming failure modes covered by tests | 100% |
| Existing FlashScore and Wikipedia modules unaffected — zero regression | 100% |
| attach() called after page.goto() produces clear, actionable error | Yes |
| Number of site modules buildable for SPA targets | > 0 (currently 0) |

---

## MVP Scope

### Core Features

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

### Out of Scope for MVP

- **Response storage** — caller's responsibility
- **Decoding** — SCR-004/005's responsibility
- **Session management** — SCR-006/007's responsibility
- **WebSocket interception** — future roadmap
- **Multiple concurrent interceptors** on the same page — caller's responsibility to manage
- **Retry logic** — SCR-002 captures once, resilience is handled elsewhere

### MVP Success Criteria

Three gates, all must pass:

1. **SCR-008 (AiScore) can be built** on top of SCR-002 without modifying SCR-002 — **SCR-008 is a future validator, not a requirement. It proves SCR-002 is generic enough.**
2. **All failure modes from brainstorming** are covered by passing tests
3. **Existing FlashScore and Wikipedia modules** pass their existing tests unchanged — zero regression

**Decision point for beyond MVP:** SCR-008 is the trigger. If SCR-008 implementation reveals gaps in SCR-002, those gaps are fixed in SCR-002 before SCR-008 is merged. SCR-002 is not considered done until SCR-008 proves it.

> ⚠️ **Important Note for PRD:** SCR-008 is a validation gate, not a SCR-002 requirement. The PRD should NOT include SCR-008-specific requirements. SCR-002 must be generic enough to support SCR-008, but its scope is limited to the eight core features listed above.

### Future Vision

**Priority order for future development:**

1. **WebSocket frame interception** — same listener pattern, different event type, natural extension
2. **Streaming response support** — partial body capture for chunked responses
3. **Multiple interceptors** on same page with non-overlapping pattern sets
4. **Auto-deduplication** as opt-in flag — not default, not MVP

**Long-term (2-3 years):** If Scrapamoja becomes a platform with external contributors, SCR-002 becomes the standard capture layer that every SPA module uses. The interface stays stable — new site modules added years later use the same four-step pattern. That stability is the long-term goal, not feature expansion.
