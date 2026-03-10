# Scrapamoja: Hybrid Browser-API Scraping Engine
## Feature Proposal

**Author:** TisoneK  
**Status:** Proposed  
**Version:** 1.0  
**Target Release:** v1.2 (Q2 2026)

---

## 1. Overview

This proposal introduces a **Hybrid Browser-API Scraping Engine** for Scrapamoja — a new capability that combines browser automation with real-time network interception to extract data from modern, heavily protected web applications that neither pure browser scraping nor direct API calls can handle alone.

The need for this feature was discovered and validated during a real-world integration project: extracting live basketball odds and match data from AiScore (m.aiscore.com) for the ScoreWise prediction algorithm. The challenges encountered there represent a broader class of modern websites that Scrapamoja currently cannot handle.

---

## 2. The Problem

### 2.1 The Modern Web Has Changed

Most high-value data sources today are no longer simple web pages. They are **Single Page Applications (SPAs)** — sophisticated web apps that load blank pages first, then fetch all data dynamically in the background. Sports platforms, financial dashboards, betting sites, and e-commerce platforms all follow this pattern.

This creates a fundamental scraping challenge:

- **Direct API calls fail** — these sites use enterprise bot detection (like Cloudflare) that blocks any request not coming from a real browser. You get a 403 error before you ever see any data.
- **Pure browser scraping struggles** — even when Playwright renders the page, the data arrives as raw binary, not readable HTML or JSON. Standard DOM selectors find nothing useful.
- **Copied headers don't work** — taking the headers and cookies from a browser session and replaying them in a script often fails because session tokens are dynamic and tied to the browser's fingerprint.

### 2.2 The AiScore Discovery

When investigating AiScore for basketball match and odds data, we encountered all three of these problems at once:

- Direct HTTP requests returned a **403 Cloudflare block** immediately
- The API response was not JSON — it was **Protocol Buffer (protobuf) binary data**, a compact binary format used by Google and many large platforms instead of human-readable JSON
- The data could only be accessed when a **real Chromium browser** made the request — because Cloudflare validates the full browser environment, not just the headers

However, we discovered something important: when Playwright navigates to the page as a real browser, Cloudflare is satisfied, the internal API is called, and the binary response travels through the browser's network layer — where it can be **captured in-flight**, before it ever reaches the DOM. This moment of interception is the key insight behind this proposal.

### 2.3 What Scrapamoja Cannot Do Today

Scrapamoja currently excels at **DOM scraping** — navigating to a page with Playwright and extracting data from rendered HTML using CSS and XPath selectors. This works well for sites like FlashScore.

It does not currently support:

- Intercepting network responses during browser navigation
- Decoding binary or protobuf-encoded API responses
- Harvesting browser session credentials for reuse in lighter-weight direct API calls
- Intelligently choosing between DOM scraping and API interception based on the target site

---

## 3. The Proposed Solution

### 3.1 Core Idea: Use the Browser as a Key, Not Just a Reader

The fundamental shift this feature proposes is changing **how we think about the browser** in a scraping workflow.

Today, Scrapamoja uses the browser to *read the page* — navigate, render, extract.

With the Hybrid Engine, the browser also serves as a *key to unlock the API* — it satisfies bot detection, establishes a valid session, and triggers the underlying data calls. The actual data is then captured from the network layer, not the DOM.

This means:

- We get the **security bypass** that only a real browser can provide
- We get **clean, structured data** directly from the API, not fragile DOM scraping
- We can optionally **harvest the session** and make subsequent calls directly — without browser overhead

### 3.2 The Three-Phase Pipeline

The Hybrid Engine operates in three distinct phases:

**Phase 1 — Unlock**  
The browser navigates to the target site exactly as a real user would. Bot detection challenges are solved automatically. A valid session is established with all the necessary cookies, tokens, and fingerprints.

**Phase 2 — Intercept**  
While the browser navigates, a network listener monitors all outgoing requests and incoming responses. When a response matches the target API endpoint — identified by URL pattern — the raw response is captured immediately, before the browser processes it.

**Phase 3 — Decode**  
The captured response is passed through an encoding detector that identifies whether it is JSON, gzip-compressed, protobuf binary, or another format, and decodes it accordingly into clean, structured Python data ready for use.

### 3.3 Four Extraction Modes

The engine will support four distinct modes, selectable per site configuration:

**DOM Mode** *(existing)*  
The current Scrapamoja approach. Navigate with browser, extract from rendered HTML. Best for traditional sites and server-rendered pages.

**Direct API Mode** *(new)*  
Skip the browser entirely. Make HTTP calls directly to a known API endpoint. Best for open APIs with no bot detection.

**Intercepted API Mode** *(new)*  
Use the browser to unlock access, but capture data from the network layer rather than the DOM. Best for Cloudflare-protected SPAs like AiScore.

**Hybrid Mode** *(new)*  
Use the browser once to establish a session and harvest credentials, then switch to lightweight direct HTTP calls for all subsequent requests. Best for high-frequency data collection where browser overhead is too slow.

---

## 4. What This Unlocks for Scrapamoja

### 4.1 A Much Larger Target Universe

Today, Scrapamoja can scrape sites where the data is in the HTML. With this feature, it can also scrape:

- **Cloudflare-protected SPAs** — the vast majority of modern sports, betting, and financial platforms
- **Protobuf API sites** — platforms that use binary data formats instead of JSON (common among large tech-backed products)
- **Session-gated data** — content that requires an active, browser-verified session to access
- **Any site that uses XHR/fetch** — which is essentially every modern web application

### 4.2 Better Data Quality

API-intercepted data is inherently cleaner than DOM-scraped data:

- No parsing fragile HTML selectors that break when the site redesigns
- No dealing with partial renders, lazy-loaded content, or animation delays
- Structured data from the source — exactly what the site's own app uses
- Less post-processing required before the data is usable

### 4.3 Performance Gains in Hybrid Mode

For use cases like ScoreWise that need to poll data frequently, Hybrid Mode offers a significant performance improvement. The browser is launched once to establish a session, credentials are harvested, and all subsequent calls are made directly via lightweight HTTP — orders of magnitude faster than launching a browser for every request.

### 4.4 Foundation for Plugin Ecosystem

The encoding detection and decoding layer becomes a reusable foundation. Any new site module added to Scrapamoja automatically benefits from it — contributors adding new sites don't need to handle binary formats themselves.

---

## 5. New Site Module: AiScore

As the first implementation of the Hybrid Engine, a new **AiScore site module** will be built alongside the engine itself. This module will:

- Navigate to `m.aiscore.com` and pass Cloudflare verification automatically
- Intercept the basketball matches API response mid-flight
- Decode the protobuf binary response into structured match data
- Extract upcoming fixtures with team names, match IDs, leagues, and odds markets — including **Total Points (Over/Under)** lines, the primary data need for ScoreWise
- Support configurable date, timezone, and sport parameters
- Follow the same CLI pattern as the existing FlashScore module for consistency

This module serves dual purpose: it delivers the basketball data needed for ScoreWise, and it proves out the Hybrid Engine against a real, production-grade, Cloudflare-protected target.

---

## 6. New Capabilities Summary

| Capability | Current State | After This Feature |
|---|---|---|
| DOM scraping | ✅ Supported | ✅ Unchanged |
| Direct API calls | ❌ Not supported | ✅ New |
| Network response interception | ❌ Not supported | ✅ New |
| Protobuf binary decoding | ❌ Not supported | ✅ New |
| Auto encoding detection | ❌ Not supported | ✅ New |
| Session harvesting | ❌ Not supported | ✅ New |
| Cloudflare-protected SPAs | ❌ Blocked | ✅ Supported |
| Hybrid mode (browser → direct HTTP) | ❌ Not supported | ✅ New |
| AiScore module | ❌ Does not exist | ✅ New |

---

## 7. Alignment with Scrapamoja Roadmap

This feature directly advances several items already on the Scrapamoja roadmap:

**v1.2 — GraphQL API Integration**  
The network interception infrastructure needed for this feature is the same infrastructure needed for GraphQL. Adding GraphQL support afterward becomes a decoder extension, not a new architectural effort.

**v1.2 — Real-time WebSocket Updates**  
WebSocket frames can be intercepted using the same listener pattern proposed here. The groundwork laid by this feature makes WebSocket support a natural next step.

**v2.0 — SaaS API Offering**  
Clean, structured data captured from API interception is far more suitable for a productised data output than fragile DOM-scraped HTML. This feature is a prerequisite for a credible SaaS offering.

**v2.0 — Advanced Analytics Dashboard**  
Reliable, structured data from the interception layer is a prerequisite for any analytics layer built on top of Scrapamoja.

---

## 8. Risks & Considerations

**Session Expiry**  
Harvested browser sessions expire. The engine must handle re-authentication gracefully and know when to relaunch the browser to refresh credentials without manual intervention.

**Binary Schema Changes**  
Sites can update their protobuf schemas without notice, which would break the binary decoder. The string extraction fallback provides a safety net, but schema changes should be monitored as part of site module maintenance.

**Cloudflare Evolution**  
Cloudflare continuously improves its bot detection. Playwright-based bypass works today but may require ongoing updates as detection improves. Scrapamoja's existing stealth module is the right place to maintain this arms race.

**Ethical Use**  
This feature significantly increases Scrapamoja's capability to access data that sites may not intend to be accessed programmatically. Users should always review the target site's Terms of Service and consider legitimate API access where available before using these capabilities.

---

## 9. Success Criteria

This feature will be considered complete when:

1. The AiScore module successfully returns structured basketball match data including Total Points odds for upcoming games
2. The Hybrid Engine is documented and extensible — a new site can be added using the hybrid pattern without modifying core engine code
3. The encoding detector correctly and automatically identifies JSON, gzip, and protobuf responses
4. The session harvester can extract credentials from a browser session for use in direct HTTP calls
5. All four extraction modes are selectable via site configuration and CLI flags
6. Existing FlashScore and Wikipedia modules are completely unaffected

---

## 10. Conclusion

The Hybrid Browser-API Scraping Engine is a natural and necessary evolution of Scrapamoja. The modern web demands it. The AiScore investigation proved it is both feasible and valuable. Rather than being stopped by Cloudflare, binary encodings, or dynamic SPAs, Scrapamoja will treat them as solved problems — and in doing so, will be capable of extracting structured data from virtually any website, regardless of how it is built or protected.

---

*Proposal prepared March 2026. Feedback welcome via GitHub Discussions.*
