# Feature Proposal: Cloudflare-Protected SPA Support
**Project:** Scrapamoja  
**Feature ID:** SCR-003  
**Status:** Proposed  
**Author:** TisoneK  
**Date:** March 2026  

---

## 1. Summary

Enable Scrapamoja to successfully access and extract data from websites protected by Cloudflare bot detection. By configuring the Playwright browser to present as a legitimate user, Cloudflare challenges are passed automatically — unlocking access to sites that currently return a 403 error on every attempt.

---

## 2. Problem

Cloudflare is the world's most widely deployed bot protection system. It sits in front of a vast number of high-value data sources — sports platforms, betting sites, financial services, news platforms, and more. When a request does not originate from a legitimate browser environment, Cloudflare returns a 403 error and serves a challenge page instead of the actual site content.

Any direct HTTP request — whether from `httpx`, `requests`, or even a poorly configured Playwright instance — will be blocked. The challenge page contains no useful data and cannot be bypassed by simply copying headers or cookies from a real browser session.

Currently, Scrapamoja has no specific capability to handle Cloudflare-protected sites. Attempts to access them fail silently or with a 403 error, with no clear path forward.

---

## 3. Opportunity

Cloudflare's bot detection evaluates a combination of signals to determine whether a request is human:

- Browser fingerprint (user agent, TLS fingerprint, HTTP/2 settings)
- JavaScript execution capability
- Browser API availability (canvas, WebGL, fonts)
- Behaviour patterns (mouse movement, timing)

A properly configured Playwright browser satisfies all of these signals because it is a real Chromium instance. The key is ensuring that Scrapamoja's browser configuration does not expose automation signals — such as the `navigator.webdriver` flag or headless browser markers — that Cloudflare uses to identify bots.

---

## 4. What This Feature Adds

- A **Cloudflare-aware browser profile** for Playwright that suppresses automation detection signals
- Correct user agent strings, viewport dimensions, and browser API exposure consistent with a real desktop browser
- Automatic waiting behaviour that allows Cloudflare's JavaScript challenge to complete before navigation proceeds
- Detection logic that identifies when a Cloudflare challenge page has been served, triggering appropriate wait and retry behaviour
- Integration with Scrapamoja's existing stealth module, extending it with Cloudflare-specific configuration
- A site configuration flag — `cloudflare_protected: true` — that activates this profile for any site module

---

## 5. Who Benefits

- Any developer building a Scrapamoja module for a modern sports, betting, financial, or media platform
- The AiScore module specifically, which is fully Cloudflare-protected
- Any future site module targeting a Cloudflare-protected domain

---

## 6. Discovery Context

This need was discovered directly during the AiScore integration sprint. Every attempt to access `api.aiscore.com` or `m.aiscore.com` via direct HTTP returned:

```
Status code: 403
Raw response: <!DOCTYPE html><html><title>Just a moment...</title>...
```

The "Just a moment..." page is Cloudflare's standard challenge page. It confirmed that bot detection was active and that a real browser environment was required. Switching to a Playwright browser with appropriate configuration resolved the 403 completely — confirming that the bypass approach is viable.

---

## 7. Success Criteria

- Scrapamoja successfully loads a Cloudflare-protected page without receiving a 403 or challenge page
- The solution works on headless and headed browser configurations
- No manual intervention is required to solve the challenge
- The browser profile passes Cloudflare's detection for all target sites tested
- The configuration is reusable across any site module via a single flag
- Existing non-Cloudflare site modules are completely unaffected

---

## 8. Out of Scope

- Solving CAPTCHA challenges that require human visual input (a separate, harder problem)
- Bypassing authenticated login walls (separate from bot detection)
- Handling other CDN/WAF providers such as Akamai or Imperva (future consideration)

---

*Proposal prepared March 2026.*
