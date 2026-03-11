# Feature Proposal: Session Bootstrap Mode
**Project:** Scrapamoja  
**Feature ID:** SCR-007  
**Status:** Proposed  
**Author:** TisoneK  
**Date:** March 2026  

---

## 1. Summary

Add a dedicated extraction mode — **Session Bootstrap** — that uses a Playwright browser once to unlock a protected site and harvest session credentials, then immediately switches to direct HTTP calls for all data extraction. The browser is a one-time bootstrap tool, not a continuous extraction mechanism.

---

## 2. Problem

Protected sites like AiScore require a real browser to pass bot detection. But extracting data repeatedly through a full browser session is slow, resource-intensive, and does not scale. At the same time, direct HTTP calls alone cannot access these sites because the session has not been established.

Neither pure browser scraping nor pure direct API calls solve this problem on their own. There is a gap between them that no current Scrapamoja mode addresses.

---

## 3. Opportunity

The insight is that bot detection and data extraction are two separate concerns. The browser is excellent at the first — passing Cloudflare, executing JavaScript, building a valid session. Direct HTTP is excellent at the second — fast, lightweight, scalable data retrieval.

By combining them in sequence — browser first to bootstrap the session, direct HTTP after to extract data — both concerns are addressed without compromise. The browser runs once. Everything after is fast.

This is the natural culmination of the Direct API, Cloudflare Support, and Session Harvesting features. Session Bootstrap mode is what happens when all three work together in a single orchestrated flow.

---

## 4. What This Feature Adds

- A **Session Bootstrap extraction mode** that orchestrates a two-phase flow:
  - **Phase 1 (Bootstrap):** Launch browser, navigate to site, pass bot detection, harvest session credentials, close browser
  - **Phase 2 (Extract):** Use harvested credentials to make direct HTTP calls to the target API endpoints
- Automatic re-bootstrap when a harvested session expires
- Configuration for how long a session is considered valid before re-bootstrapping
- CLI flag to force a fresh bootstrap regardless of existing session state
- Session persistence so a bootstrap is not required every time Scrapamoja starts
- Logging that clearly shows when the browser phase ends and the direct HTTP phase begins

---

## 5. Who Benefits

- **ScoreWise** — the primary motivating use case. Needs basketball odds updated regularly. Cannot afford a full browser launch on every poll, but cannot bypass Cloudflare without a browser.
- Any high-frequency data pipeline targeting a Cloudflare-protected API
- Production deployments where minimising browser runtime is a resource and cost concern

---

## 6. How This Differs from Other Modes

| Mode | Browser Used | When |
|---|---|---|
| DOM Extraction | Always | Every request |
| Direct API | Never | Every request |
| Network Intercept | Always | Every request |
| **Session Bootstrap** | **Once per session** | **Bootstrap only** |

Session Bootstrap is the performance-optimised mode for sites that need the browser to get in but not to stay in.

---

## 7. Discovery Context

This mode emerged from the AiScore investigation as the practical answer to a real operational question: ScoreWise needs odds data frequently. AiScore requires a browser to access. Running a full browser on every poll is not viable. The solution — bootstrap once, poll directly — became obvious once session harvesting was identified as a capability.

The flow was validated conceptually during the investigation:

1. Playwright navigated to `m.aiscore.com` ✅
2. Cloudflare passed ✅
3. API response intercepted ✅
4. Session cookies confirmed present in browser context ✅
5. The logical next step — harvest those cookies and use them in `httpx` — is what this feature formalises.

---

## 8. Success Criteria

- A complete Session Bootstrap flow executes end-to-end: browser launches, session established, browser closes, direct HTTP calls succeed
- The browser phase completes and closes before any data extraction begins
- Direct HTTP calls using harvested credentials return the same data as browser-intercepted calls
- Re-bootstrap triggers automatically when the session expires, without requiring a restart
- The entire mode is configurable and selectable via CLI and site configuration
- Memory usage after the bootstrap phase is consistent with direct HTTP only (no browser process remaining)

---

## 9. Out of Scope

- Managing multiple concurrent sessions (future consideration)
- Rotating sessions across different IP addresses (future consideration)
- Any site that requires continuous browser interaction beyond initial authentication

---

*Proposal prepared March 2026.*
