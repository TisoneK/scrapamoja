---
stepsCompleted: [1, 2, 3, 4, 5, 6]
status: complete
inputDocuments:
  - "_bmad-output/brainstorming/brainstorming-session-2026-03-17-16-46-13.md"
  - "docs/summary.md"
  - "_bmad-output/project-context.md"
  - "docs/proposals/browser_api_hybrid/FEATURE_03_CLOUDFLARE_SUPPORT.md"
date: 2026-03-17
author: Tisone
---

# Product Brief: scrapamoja

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

Scrapamoja is a general-purpose, production-grade web scraping framework designed to reliably extract data from anti-bot protected websites. Unlike one-off scraping scripts, Scrapamoja provides a modular architecture with reusable components that handle the universal challenges of modern web scraping: anti-bot detection (Cloudflare, etc.), selector drift, network failures, and browser resource management. The framework enables developers to build site-specific scrapers quickly by leveraging pre-built systems for browser automation, stealth configuration, resilience, and data extraction.

---

## Core Vision

### Problem Statement

Modern websites increasingly deploy sophisticated anti-bot protection systems (Cloudflare, Akamai, PerimeterX, etc.) that block automated access. Building a reliable scraper requires solving multiple complex problems: bypassing bot detection, handling volatile DOM structures that change without notice, managing network failures gracefully, and optimizing browser resource usage. Most existing solutions are one-off scripts that don't scale, lack proper error handling, and can't be reused across different target sites.

### Problem Impact

- Developers waste time reinventing the wheel for each new target site
- Anti-bot detection causes scrapers to fail silently or return empty data
- Selector changes break scrapers frequently, requiring constant maintenance
- Browser resource exhaustion crashes long-running scraping jobs
- Lack of observability makes debugging production issues difficult

### Why Existing Solutions Fall Short

1. **Single-purpose scripts**: Most scraping tools are written for one specific site and can't be adapted
2. **No abstraction layers**: Hardcoded selectors, site-specific logic, and brittle dependencies
3. **Missing stealth capabilities**: Poor browser fingerprint configuration triggers bot detection
4. **No resilience patterns**: Scripts fail on network errors without retry logic or checkpoints
5. **Limited observability**: No structured logging, metrics, or failure correlation

### Proposed Solution

Scrapamoja is a modular framework with well-defined abstraction layers:

- **Selector Engine**: Multi-strategy, confidence-scored selector resolution with drift detection
- **Stealth System**: Browser fingerprint management for bypassing bot detection
- **Resilience Engine**: Retry mechanisms, checkpoints, and graceful degradation
- **Snapshot System**: DOM state capture for failure analysis and recovery
- **Observability Stack**: Structured logging, metrics, and performance monitoring

For SCR-003 (Cloudflare Support): A reusable framework module activated by a single config flag (`cloudflare_protected: true`), not hardcoded hacks per site. Any site module gets Cloudflare support automatically.

### Key Differentiators

1. **Framework, not a scraper**: Built for developers to build site-specific scrapers on top
2. **Modular architecture**: Each concern (selectors, stealth, resilience) is a separate, reusable module
3. **Production-ready**: Built for long-running jobs with proper resource management and observability
4. **Config-driven**: Site modules configure capabilities via YAML, not code changes
5. **Cloudflare as a feature**: One flag enables anti-bot protection for any site

## Target Users

### Primary Users

**Scrapamoja Site Module Developers** — Python developers building site scrapers inside `src/sites/`. These are the developers who will:
- Set `cloudflare_protected: true` in their site YAML configuration
- Benefit from automatic Cloudflare bypass without writing custom bypass logic
- Focus on site-specific extraction logic rather than anti-bot mechanics

**Persona: Alex, Site Module Developer**
- Background: Python developer with experience in web scraping, new to Scrapamoja
- Goals: Quickly build a scraper for a Cloudflare-protected sports data site
- Problem Experience: Previously had to write custom bypass logic that broke frequently
- Success Vision: Set one config flag and have Cloudflare protection handled automatically

### Secondary Users

**N/A** — End users of the scraped data are out of scope for this feature. The Cloudflare support module is a developer-facing capability, not a user-facing product.

### User Journey

1. **Discovery**: Developer learns about Scrapamoja framework and its capabilities
2. **Onboarding**: Developer creates new site module following framework patterns
3. **Core Usage**: Developer adds `cloudflare_protected: true` to site config YAML
4. **Success Moment**: Developer runs scraper and it successfully loads Cloudflare-protected pages without 403 errors
5. **Long-term**: Developer leverages the same pattern for additional Cloudflare-protected sites

## Success Metrics

### User Success Metrics

**Primary Success Criterion:**
- Scraper successfully loads Cloudflare-protected pages without receiving 403 errors or challenge pages

**Key Metrics:**

1. **Bypass Success Rate**: Percentage of Cloudflare-protected page loads that succeed without challenge
   - Target: >95% success rate on known Cloudflare-protected sites
   
2. **Average Time to Clear Challenge**: Time from page request to content availability
   - Target: <30 seconds average (includes challenge wait time)
   
3. **False Positive Detection Rate**: Percentage of legitimate (non-Cloudflare) sites incorrectly flagged as protected
   - Target: <1% false positive rate
   
4. **Headless vs Headed Parity**: Success rate comparison between headless and headed browser modes
   - Target: >90% parity (headless success rate within 10% of headed)

### Business Objectives

**N/A** — This is an internal framework capability, not a revenue-generating product. Business objectives are measured through framework adoption and site module success.

### Key Performance Indicators

- Number of site modules successfully using `cloudflare_protected: true` config
- Number of Cloudflare-protected target sites supported
- Mean time to integration for new Cloudflare-protected sites
- Zero manual intervention required for challenge solving

## MVP Scope

### Core Features (MVP)

1. **Config Flag**: `cloudflare_protected: true` YAML configuration that activates Cloudflare bypass
2. **Stealth Browser Profile**: Browser fingerprint configuration applied to Playwright context
   - User agent rotation
   - Viewport normalization  
   - Browser API exposure (canvas, WebGL, fonts)
   - Automation signal suppression (`navigator.webdriver` flag)
3. **Challenge Detection & Wait Logic**: 
   - Detection of Cloudflare challenge pages
   - Automatic waiting for challenge completion
   - Retry logic with exponential backoff

### Out of Scope for MVP

- CAPTCHA solving (requires human visual input)
- Authenticated login wall handling
- Other CDN/WAF providers (Akamai, Imperva) — future consideration

### MVP Success Criteria

- Scrapemoja successfully loads Cloudflare-protected pages with `cloudflare_protected: true` config
- Works in both headless and headed browser modes
- No manual intervention required to solve challenges
- Existing non-Cloudflare site modules unaffected

### Future Vision

- Support for other CDN/WAF providers (Akamai, Imperva)
- Advanced fingerprinting techniques
- CAPTCHA solving capability (separate feature)
