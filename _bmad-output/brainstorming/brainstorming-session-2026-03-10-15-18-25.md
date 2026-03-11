---
stepsCompleted: [1, 2]
inputDocuments: ["docs/proposals/browser_api_hybrid/FEATURE_01_DIRECT_API_MODE.md", "docs/proposals/browser_api_hybrid"]
session_topic: 'Direct API Mode implementation for Scrapamoja'
session_goals: 'Generate implementation ideas, architectural approaches, and creative solutions for building the Direct API Mode feature'
selected_approach: 'User-Selected Techniques'
techniques_used: ['SCAMPER Method']
ideas_generated: []
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Tisone
**Date:** 2026-03-10

## Session Overview

**Topic:** Direct API Mode implementation for Scrapamoja
**Goals:** Generate implementation ideas, architectural approaches, and creative solutions for building the Direct API Mode feature

### Context Guidance

Based on the provided context, the user is working on the Scrapamoja project and wants to brainstorm about building the Direct API Mode feature. This feature allows Scrapamoja to make direct HTTP calls to known API endpoints without launching a browser.

Key context from the documents:
- Direct API Mode should bypass browser entirely for open APIs
- Should support configuring target API URLs, query parameters, headers, and authentication tokens
- Must handle JSON and plain text response formats
- Needs rate limiting and retry logic consistent with existing resilience standards
- CLI support required to invoke direct API calls

### Session Setup

The user selected **User-Selected Techniques** and chose the **SCAMPER Method** for this session.

---

## SCAMPER Method - Direct API Mode

**SCAMPER** is a systematic creativity technique using seven lenses:
- **S**ubstitute
- **C**ombine
- **A**dapt
- **M**odify
- **P**ut to other uses
- **E**liminate
- **R**everse

---

### S - SUBSTITUTE

*What could you substitute in the Direct API Mode feature?*

**Ideas Generated:**
1. Use httpx with async support for better performance (enables concurrent API calls)

---

### C - COMBINE

*What could you combine with Direct API Mode?*

**Ideas Generated:**
1. Built-in response caching with TTL for polling scenarios

---

### A - ADAPT

*How could you adapt Direct API Mode for different uses?*

**Ideas Generated:**
1. GraphQL as a named request type (thin wrapper, not full client)
2. **HTTP transport role for other Scrapamoja modules** — design the public interface for this from day one (CRITICAL ARCHITECTURAL DECISION)
3. Response type flexibility — handle raw bytes cleanly, delegate parsing to the encodings layer
4. Defer SSE streaming — different execution model, belongs in its own future module

---

### M - MODIFY

*What could you modify or magnify in Direct API Mode?*

**Ideas Generated:**
1. Request builder with chainable API for complex queries (fluent interface)

---

### P - PUT TO OTHER USES

*What else could Direct API Mode be used for?*

**Ideas Generated:**
1. Use as health check endpoint for monitored APIs

---

### E - ELIMINATE

*What could you eliminate from Direct API Mode?*

**Ideas Generated:**
1. Eliminate built-in parsing - return raw Response object to caller (keep transport layer simple)

---

### R - REVERSE

*What if you did the opposite of conventional Direct API thinking?*

**Ideas Generated:**
1. Default to async from day one (httpx async)

---

## Session Summary

### Ideas Generated During SCAMPER Session:

| # | SCAMPER | Idea |
|---|---------|------|
| 1 | S - Substitute | Use httpx with async support for better performance |
| 2 | C - Combine | Built-in response caching with TTL for polling scenarios |
| 3 | A - Adapt | GraphQL as a named request type (thin wrapper) |
| 4 | A - Adapt | **HTTP transport role for other Scrapamoja modules** - design public interface from day one |
| 5 | A - Adapt | Handle raw bytes cleanly, delegate parsing to encodings layer |
| 6 | A - Adapt | Defer SSE streaming to future module |
| 7 | M - Modify | Request builder with chainable API (fluent interface) |
| 8 | P - Put to Other Uses | Use as health check endpoint for monitored APIs |
| 9 | E - Eliminate | Return raw Response object to caller (no built-in parsing) |
| 10 | R - Reverse | Default to async from day one (httpx async) |

### Key Architectural Decisions:

1. **CRITICAL**: Design public interface for reuse as shared HTTP transport from day one
2. Use httpx with async support as the HTTP client
3. Keep transport layer simple - return raw Response, delegate parsing
4. Build chainable/fluent API for request building
5. Integrate with encodings layer for response handling
6. **.auth() accepts bearer, basic, and cookie** - cookie form is non-negotiable for SCR-007 compatibility (harvested session cookies)

---

*Session completed. Total ideas generated: 10*

---

## Deep Dive: HTTP Transport Interface Design

Since this is the **most critical architectural decision** for SCR-001, let's explore it further.

### Key Questions:

1. **What should the public interface look like?**
   - Function-based (e.g., `client.get(url, **kwargs)`)?
   - Class-based (e.g., `HttpTransport().get(url)`)?
   - Protocol-based (define interface for dependency injection)?

2. **What should the return type be?**
   - Raw httpx Response object?
   - Wrapped custom Response class?
   - Typed dataclass with parsed data?

3. **How should configuration be passed?**
   - Constructor injection?
   - Per-request parameters?
   - Configuration file + overrides?

4. **How should it integrate with other modules?**
   - Site modules import directly?
   - Injected via protocol?
   - Registry pattern?

### Proposed Interface Concepts:

```python
# Option A: Simple function-based
def request(method: str, url: str, **kwargs) -> HttpResponse: ...

# Option B: Class-based with chainable builder
class HttpClient:
    def get(self, url: str) -> RequestBuilder
    def post(self, url: str) -> RequestBuilder

# Option C: Protocol-based for DI
class IHttpClient:
    async def request(self, method: str, url: str) -> HttpResponse: ...
```

### DECISION: Class-based with chainable builder ✓

This matches the fluent request builder idea generated earlier. Let's explore what this looks like:

```python
# Example usage - chainable fluent interface
client = HttpClient(base_url="https://api.example.com")

response = (client
    .get("/matches")
    .header("Authorization", "Bearer token")
    .param("sport_id", 2)
    .param("date", "20260310")
    .timeout(30)
    .execute())
```

### FINAL DESIGN DECISIONS:

1. **Async by Default, Sync Wrapper** ✓
   - Scrapamoja is async throughout. SCR-001 must be async-first.
   - If sync-only, it becomes a bottleneck when SCR-007 and SCR-008 use it in async contexts.
   - Sync wrapper exists purely for convenience in scripts/tests — not the primary interface.

2. **Base URL - Optional but Always Valid on Execute** ✓
   - Make base_url optional on the client constructor.
   - But always valid on execute() — must be provided either at client or request level.
   - **Why?** If fully optional, SCR-007 and SCR-008 will repeat `https://api.aiscore.com` in every single call.
   - One URL change would break everything — maintenance nightmare.
   - Base URL enables composability: set once, use many times.

3. **Auth via builder method** (.auth() for convenience)

---

### Follow-up Questions:

1. Should this be sync-only, async-only, or support both?
2. Should base_url be required or optional?
3. Should auth be handled via methods or headers?

### Design Refinement Based on Decisions:

```python
# Final proposed interface
class HttpClient:
    def __init__(self, base_url: str | None = None, **kwargs): ...
    
    def get(self, path: str) -> RequestBuilder: ...
    def post(self, path: str) -> RequestBuilder: ...
    # ... other methods

class RequestBuilder:
    def header(self, key: str, value: str) -> RequestBuilder: ...
    def param(self, key: str, value: Any) -> RequestBuilder: ...
    def auth(
        self,
        bearer: str | None = None,
        basic: tuple[str, str] | None = None,
        cookie: dict[str, str] | None = None
    ) -> RequestBuilder: ...
    def timeout(self, seconds: float) -> RequestBuilder: ...
    
    async def execute(self) -> RawHttpResponse: ...
    def execute_sync(self) -> RawHttpResponse: ...
```

---

## Additional Context from Feature Documents

### From SCRAPAMOJA_BUILD_ORDER.md:

**SCR-001 — Direct API Mode**
- **Depends on:** Nothing internal
- **Reason:** Makes raw HTTP calls. No browser. No other Scrapamoja module needed. It is a standalone transport layer.
- **Build Order:** #2 in Phase 1 (after SCR-004)
- **Needed by:** SCR-007 (Session Bootstrap)

### From SCRAPAMOJA_ARCHITECTURE_GUIDE.md:

**Placement:** `src/network/` *(new directory)*
- Direct API mode is about making HTTP calls without a browser.
- This is a transport concern — it lives at the network layer, not the browser layer.
- All future features that deal with how data moves over the wire — without a browser — will live alongside it.

### From hybrid-scraping-proposal.md:

**Four Extraction Modes:**
1. **DOM Mode** *(existing)* - Navigate with browser, extract from HTML
2. **Direct API Mode** *(new)* - Skip browser, call API directly
3. **Intercepted API Mode** *(new)* - Browser unlocks, capture from network
4. **Hybrid Mode** *(new)* - Browser once, harvest session, then direct HTTP

### From FEATURE_01_DIRECT_API_MODE.md:

**Success Criteria:**
- Site module can use Direct API mode without browser dependency
- Data returned from open API in under 1 second
- Mode selectable via CLI flag and config file
- Rate limiting and retry logic work correctly
- Existing browser-based modules unaffected

**Out of Scope:**
- Cloudflare/bot detection (SCR-003)
- Protobuf decoding (SCR-005)
- Session management (SCR-006)

---

## Extended Brainstorming: Implementation Details

Based on the context, let's explore more specific implementation questions:

*(Session ended by user - no further exploration requested)*

---

## Session Complete ✓
```
