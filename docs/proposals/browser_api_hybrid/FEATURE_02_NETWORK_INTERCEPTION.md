# Feature Proposal: Network Response Interception
**Project:** Scrapamoja  
**Feature ID:** SCR-002  
**Status:** Proposed  
**Author:** TisoneK  
**Date:** March 2026  

---

## 1. Summary

Add the ability for Scrapamoja to listen to network traffic during a Playwright browser session and capture API responses mid-flight — before they are processed by the page. This allows structured data to be extracted directly from the network layer, completely bypassing the need to parse the DOM.

---

## 2. Problem

Scrapamoja currently extracts data by navigating to a page and reading content from the rendered HTML using CSS and XPath selectors. This works well for traditional websites but fails for modern Single Page Applications (SPAs).

In an SPA, the page HTML is essentially empty. All meaningful data is fetched asynchronously from internal API endpoints after the page loads. By the time the browser has rendered anything useful, the data has already travelled from the server, through the network layer, into JavaScript memory — and then been painted onto the screen as HTML. Scraping the resulting HTML means working with a copy of a copy, filtered through the site's own rendering logic.

The original data — clean, structured, often in JSON — passed through the browser's network layer and was never captured.

---

## 3. Opportunity

Playwright exposes a network event system that fires on every request and response during a browser session. By attaching a listener before navigation begins, Scrapamoja can intercept API responses at the moment they arrive — capturing the raw, structured data directly, without any DOM involvement.

This produces:

- Cleaner data (no HTML parsing, no rendering artifacts)
- More reliable extraction (API responses are structured by design, HTML is not)
- Resilience to site redesigns (the API often remains stable even when the visual layout changes)
- Access to data that never appears in the DOM at all

---

## 4. What This Feature Adds

- A **network response listener** that can be attached to any Playwright browser session
- URL pattern matching so only relevant API responses are captured (not images, fonts, analytics, etc.)
- Captured responses stored and returned alongside or instead of DOM-extracted data
- Configuration per site module specifying which URL patterns to intercept
- CLI and logging support to inspect intercepted responses during development

---

## 5. Who Benefits

- Developers building modules for any modern SPA — sports platforms, financial dashboards, e-commerce, social platforms
- Any use case where the DOM does not reliably contain the target data
- Developers who want cleaner, more stable data extraction without maintaining fragile CSS selectors

---

## 6. Discovery Context

This capability was discovered during the AiScore investigation. After navigating to `m.aiscore.com/basketball` with Playwright and logging all network responses, the following was observed:

```
[200] https://api.aiscore.com/v1/m/api/matches?lang=2&sport_id=2&date=20260310&tz=03:00
```

This single line confirmed that all basketball match data — including odds — was available directly from the network layer. The DOM contained no useful data. Network interception was the only viable extraction path.

---

## 7. Success Criteria

- A site module can configure URL patterns to intercept during browser navigation
- Matching responses are captured and returned as structured data
- Non-matching responses (images, CSS, analytics) are ignored without affecting performance
- The listener attaches before navigation begins and captures responses reliably
- Works correctly alongside existing DOM extraction in the same browser session
- Intercepted response content is accessible for further processing by decoders

---

## 8. Out of Scope

- Decoding binary or protobuf responses (covered by a separate feature)
- Cloudflare bypass (covered by a separate feature)
- WebSocket interception (future roadmap item)

---

*Proposal prepared March 2026.*
