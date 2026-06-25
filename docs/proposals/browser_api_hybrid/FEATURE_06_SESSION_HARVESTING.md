# Feature Proposal: Session Harvesting
**Project:** Scrapamoja  
**Feature ID:** SCR-006  
**Status:** Proposed  
**Author:** TisoneK  
**Date:** March 2026  

---

## 1. Summary

Add the ability for Scrapamoja to extract authentication credentials — cookies, tokens, and session headers — from an active Playwright browser session, and package them for reuse in subsequent direct HTTP calls. This means the browser only needs to run once to establish a valid session, after which lighter-weight HTTP requests can be made directly without re-launching the browser.

---

## 2. Problem

Launching a Playwright browser is expensive. It consumes significant memory, takes several seconds to start, and must render a full page before any data can be captured. For many data collection tasks — particularly those that need to poll for updates frequently — this overhead is prohibitive.

However, the browser is often only needed once: to satisfy bot detection and establish a valid session. Once Cloudflare or similar protection has been passed, the resulting session cookies and tokens are what the server actually validates on subsequent requests. If those credentials could be extracted and reused directly, the browser would only need to run once per session — and all subsequent calls could be made via fast, lightweight HTTP.

Currently, Scrapamoja has no mechanism to extract or reuse browser session credentials. Every extraction requires a full browser session from start to finish.

---

## 3. Opportunity

After a Playwright browser successfully loads a protected page, the browser context holds a complete, validated session state — including:

- **Cookies** set by the server (including Cloudflare's `cf_clearance` cookie)
- **Local storage** values set by the site's JavaScript
- **Request headers** used by the site's internal API calls (user agent, origin, referer)

These values represent everything the server needs to consider a request legitimate. By extracting them from the browser context and packaging them into a reusable HTTP client configuration, Scrapamoja can make all subsequent API calls directly — without any browser involvement — until the session expires.

---

## 4. What This Feature Adds

- A **session harvester** that extracts cookies, tokens, and headers from an active Playwright browser context
- A **session package** — a portable, serialisable object containing everything needed to authenticate direct HTTP calls
- Conversion of a harvested session into a pre-configured HTTP client ready for immediate use
- Session validity checking — detecting when a harvested session has expired and triggering browser re-authentication
- Optional session persistence — saving a harvested session to disk so it can be reused across Scrapamoja restarts without relaunching the browser
- Per-site configuration for session lifetime expectations and re-authentication triggers

---

## 5. Who Benefits

- Any use case that needs to poll a protected API frequently — such as ScoreWise checking for odds updates every few minutes
- Developers building high-frequency data pipelines where browser launch overhead is unacceptable
- Any site module where the browser is only needed for initial authentication, not for ongoing data extraction

---

## 6. Discovery Context

This need was identified as a direct consequence of the AiScore investigation. The Playwright browser successfully accessed `m.aiscore.com` and triggered the target API calls — but every new data request required a full browser session. For ScoreWise, which needs odds data updated regularly before games, re-launching a browser for each poll is impractical.

The insight was that once Cloudflare grants access, the resulting `cf_clearance` cookie and session state are what matters. If those can be harvested from the browser and reused in direct `httpx` calls, the expensive browser launch becomes a one-time cost.

---

## 7. Success Criteria

- A harvested session successfully authenticates direct HTTP calls to a previously Cloudflare-protected endpoint
- Session harvesting adds no more than 500ms overhead to an existing browser session
- A harvested session can be serialised and reused across process restarts
- Session expiry is detected and triggers automatic browser re-authentication
- The harvested session works correctly with the Direct API mode feature
- No browser is launched for any request made after the initial session harvest

---

## 8. Out of Scope

- Managing login credentials (username/password authentication is separate from session token reuse)
- Cloudflare bypass itself (covered by a separate feature)
- Proxy rotation or IP management (future consideration)

---

*Proposal prepared March 2026.*
