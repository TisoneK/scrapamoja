# Feature Proposal: Direct API Mode
**Project:** Scrapamoja  
**Feature ID:** SCR-001  
**Status:** Completed  
**Author:** TisoneK  
**Date:** March 2026  

---

## 1. Summary

Add the ability for Scrapamoja to make direct HTTP calls to known API endpoints without launching a browser at all. When a target site exposes a clean, accessible API with no bot protection, Scrapamoja should be able to call it directly and return structured data — fast, lightweight, and with no browser overhead.

---

## 2. Problem

Scrapamoja currently requires a Playwright browser for every data extraction task. This is appropriate for sites that require a rendered page, but it is wasteful and slow when the target is a known, open API endpoint that can be called directly with a simple HTTP request.

There are many data sources that expose clean APIs — sports data services, public statistics endpoints, open government data, and more — that do not require a browser at all. Forcing a full browser launch for these cases adds unnecessary latency, resource consumption, and complexity.

---

## 3. Opportunity

By supporting direct API calls as a first-class extraction mode, Scrapamoja can:

- Return data in milliseconds instead of seconds
- Consume a fraction of the memory and CPU of a browser session
- Handle high-frequency polling use cases that a browser-based approach cannot scale to
- Serve as the foundation for more advanced modes that build on top of direct HTTP

---

## 4. What This Feature Adds

- A dedicated **Direct API extraction mode** that bypasses the browser entirely
- Support for configuring target API URLs, query parameters, request headers, and authentication tokens per site module
- Automatic handling of standard response formats (JSON, plain text)
- Rate limiting and retry logic consistent with Scrapamoja's existing resilience standards
- CLI support so developers can invoke direct API calls with the same commands used for browser-based scraping

---

## 5. Who Benefits

- Developers building site modules for open or semi-open APIs
- Use cases requiring frequent data refresh (polling every few seconds or minutes)
- Lightweight deployments where browser infrastructure is not available or desired

---

## 6. Discovery Context

This need was identified during the AiScore integration sprint. An attempt was made to call `api.aiscore.com` directly using `httpx` before trying any browser approach. While that specific call was blocked by Cloudflare, the investigation confirmed the value of direct API calling as a capability — it is always worth attempting before escalating to a full browser session.

---

## 7. Success Criteria

- A site module can be configured to use Direct API mode without any browser dependency
- Data is returned correctly from a real open API endpoint in under one second
- The mode is selectable via CLI flag and site configuration file
- Rate limiting and retry logic function correctly under this mode
- Existing browser-based modules are completely unaffected

---

## 8. Out of Scope

- Handling Cloudflare or other bot detection (that is covered by a separate feature)
- Binary or protobuf response decoding (covered by a separate feature)
- Session management or credential harvesting (covered by a separate feature)

## 9. Completion Notes

**Completed:** March 2026  
**Implementation:** Epic 6 (CLI for Direct API Mode)

### Stories Delivered:
- 6-1: CLI Interface
- 6-2: CLI and Python API Parity

### Code Locations:
- `src/network/direct_api/` - Core HTTP client implementation
- `src/sites/direct/cli/main.py` - CLI interface

### Success Criteria Verification:
- ✅ Site module can use Direct API mode without browser dependency
- ✅ CLI support (`python -m src.main direct --help`)
- ✅ HTTP methods (GET, POST, PUT, DELETE) supported
- ✅ Rate limiting enforced at transport layer
- ✅ Authentication from environment variables
- ✅ Existing browser-based modules unaffected

---

*Proposal prepared March 2026.*
