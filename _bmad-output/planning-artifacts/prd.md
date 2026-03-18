---
stepsCompleted: ["step-01-init", "step-02-discovery", "step-02b-vision", "step-02c-executive-summary", "step-03-success", "step-04-journeys", "step-05-domain", "step-06-innovation", "step-07-project-type", "step-08-scoping", "step-09-functional", "step-10-nonfunctional", "step-11-polish", "step-12-complete"]
status: complete
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-scrapamoja-2026-03-17.md"
  - "_bmad-output/brainstorming/brainstorming-session-2026-03-17-16-46-13.md"
  - "_bmad-output/project-context.md"
  - "docs/proposals/browser_api_hybrid/FEATURE_03_CLOUDFLARE_SUPPORT.md"
documentCounts:
  productBriefs: 1
  research: 1
  brainstorming: 1
  projectDocs: 1
workflowType: 'prd'
classification:
  projectType: 'Developer Tool / Framework'
  domain: 'Web Scraping / Browser Automation'
  complexity: 'High'
  projectContext: 'brownfield'
---

# Product Requirements Document - scrapamoja

**Author:** Tisone
**Date:** 2026-03-18

## Executive Summary

Scrapamoja is a general-purpose, production-grade web scraping framework designed to reliably extract data from anti-bot protected websites. Unlike one-off scraping scripts, Scrapamoja provides a modular architecture with reusable components that handle the universal challenges of modern web scraping: anti-bot detection (Cloudflare, etc.), selector drift, network failures, and browser resource management. The framework enables developers to build site-specific scrapers quickly by leveraging pre-built systems for browser automation, stealth configuration, resilience, and data extraction.

### What Makes This Special

1. **Framework, not a scraper**: Built for developers to build site-specific scrapers on top
2. **Modular architecture**: Each concern (selectors, stealth, resilience) is a separate, reusable module
3. **Production-ready**: Built for long-running jobs with proper resource management and observability
4. **Config-driven**: Site modules configure capabilities via YAML, not code changes
5. **Cloudflare as a feature**: One flag (`cloudflare_protected: true`) enables anti-bot protection for any site

## Project Classification

- **Project Type:** Developer Tool / Framework (Python library)
- **Domain:** Web Scraping / Browser Automation / Anti-Detection
- **Complexity:** High (deals with sophisticated bot detection systems, browser fingerprinting)
- **Project Context:** Brownfield (existing framework with active development)

## Success Criteria

### User Success

- Scraper successfully loads Cloudflare-protected pages without receiving 403 errors or challenge pages
- No manual intervention required to solve challenges
- Works in both headless and headed browser modes
- Existing non-Cloudflare site modules remain completely unaffected

### Business Success

- Number of site modules successfully using `cloudflare_protected: true` config
- Number of Cloudflare-protected target sites supported
- Mean time to integration for new Cloudflare-protected sites
- Zero manual intervention required for challenge solving

### Technical Success

- Bypass Success Rate: >95% success rate on known Cloudflare-protected sites
- Average Time to Clear Challenge: <30 seconds average (includes challenge wait time)
- False Positive Detection Rate: <1% (legitimate sites incorrectly flagged as protected)
- Headless vs Headed Parity: >90% (headless success rate within 10% of headed)

### Measurable Outcomes

| Metric | Target | Measurement |
|--------|--------|--------------|
| Cloudflare bypass success rate | >95% | Pages loaded without 403/challenge |
| Average challenge wait time | <30 seconds | Time from request to content |
| False positive rate | <1% | Non-protected sites flagged |
| Headless/headed parity | >90% | Success rate comparison |
| Site modules using feature | Growing | Config count in codebase |

## Product Scope

### MVP - Minimum Viable Product

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

### Growth Features (Post-MVP)

- Support for other CDN/WAF providers (Akamai, Imperva)
- Advanced fingerprinting techniques
- CAPTCHA solving capability (separate feature)
- Authenticated login wall handling

### Vision (Future)

- Universal anti-bot framework that handles any protection system
- Self-learning detection that adapts to new challenges
- One-click site module generation for protected sites

## User Journeys

### Primary User: Alex (Site Module Developer)

**Persona:** Python developer with experience in web scraping, new to Scrapamoja

**Situation:** Alex needs to build a scraper for a Cloudflare-protected sports data site. Previously, they had to write custom bypass logic that broke frequently every time the target site changed their protection.

**Goal:** Quickly build a scraper without worrying about anti-bot mechanics

**Obstacle:** Cloudflare blocks automated access, previous solutions were fragile one-off scripts

**Solution:** Set `cloudflare_protected: true` in YAML config and let Scrapamoja handle the rest

#### Journey Narrative

**Opening Scene:**
Alex is frustrated. They've spent weeks writing custom Cloudflare bypass logic that keeps breaking. Each time the target site updates their protection, their scraper stops working. They're tired of playing cat-and-mouse with anti-bot systems.

**Rising Action:**
1. Alex discovers Scrapamoja and learns about its modular framework
2. Alex creates a new site module following framework patterns
3. Alex reads the docs and finds `cloudflare_protected: true` config option
4. Alex adds the flag to their site YAML configuration

**Climax:**
Alex runs the scraper. For the first time, it successfully loads the Cloudflare-protected page without any 403 errors or challenge pages. The Cloudflare protection is automatically handled by the framework.

**Resolution:**
Alex can now focus on writing extraction logic instead of fighting anti-bot systems. They add more Cloudflare-protected sites using the same pattern. They feel relieved and confident.

### Secondary User: Operations Engineer

**Persona:** DevOps engineer responsible for running scrapers in production

**Situation:** Needs to monitor scraper health, handle failures, and ensure reliable data collection

**Goal:** Zero-downtime scraping with proper monitoring and alerting

**Obstacle:** Cloudflare challenges can cause unpredictable delays and failures

**Solution:** Scrapamoja's built-in retry logic and observability provide visibility into Cloudflare-specific issues

#### Journey Narrative

**Opening Scene:**
Jordan is on-call. They need to ensure the scrapers are running smoothly. Previously, they had no visibility into why Cloudflare-protected pages failed.

**Rising Action:**
1. Jordan checks the observability dashboard
2. Notices increased challenge detection events for a specific site
3. Reviews structured logs showing challenge wait times
4. Adjusts configuration to increase timeout for that site

**Climax:**
Jordan identifies a pattern: certain pages trigger longer challenges. They optimize the configuration and reduce false alarms.

**Resolution:**
Jordan has confidence in the system's ability to handle Cloudflare challenges automatically. They can sleep at night.

### Journey Requirements Summary

| User Type | Key Capability | Emotional Need |
|-----------|----------------|----------------|
| Alex (Developer) | Simple config flag | Confidence, focus on extraction |
| Jordan (Ops) | Observability, logging | Control, peace of mind |

| Capability Area | Required Feature |
|----------------|------------------|
| Configuration | YAML-based site config with `cloudflare_protected: true` |
| Stealth | Browser fingerprint management |
| Detection | Challenge page detection |
| Retry | Exponential backoff on challenges |
| Observability | Structured logging for challenge events |
| Timeout | Configurable challenge wait time |

## Domain-Specific Requirements

### Technical Constraints

- **Browser Resource Management**: Efficient handling of browser instances, memory cleanup, concurrent session limits
- **Network Management**: Request throttling, bandwidth considerations, retry logic
- **Anti-Detection**: Browser fingerprint management, automation signal suppression, human behavior emulation
- **Scalability**: Support for multiple concurrent browser sessions, distributed scraping patterns

### Security Considerations

- **Credential Handling**: Secure storage and management of any authentication tokens
- **Proxy Rotation**: Support for proxy servers with secure credential management
- **Data Protection**: Secure handling of scraped data, especially if containing personal information

### Ethical Guidelines

- **Rate Limiting**: Built-in mechanisms to respect target server resources
- **User-Agent Management**: Proper user-agent strings that identify the scraper appropriately
- **robots.txt Support**: Optional compliance with target site crawling rules
- **Terms of Service**: Framework should allow users to configure compliance with ToS

### Risk Mitigations

- **Detection Evasion**: Multi-signal detection approach to minimize false positives
- **Graceful Degradation**: When anti-bot measures cannot be bypassed, clear error reporting
- **Failure Recovery**: Checkpoint mechanisms to resume from failures
- **Observability**: Structured logging to diagnose scraping issues

## Developer Tool Specific Requirements

### Framework Architecture

- **Modular Design**: Each concern (selectors, stealth, resilience, storage) is a separate, reusable module
- **Sub-module Structure**: Follows recursive subdirectory pattern per project-context.md:
  ```
  src/stealth/cloudflare/
  ├── __init__.py
  ├── core/           # profile lifecycle, apply to context
  ├── detection/     # challenge page detection, multi-signal
  ├── config/        # cloudflare-specific config, flag wiring
  ├── models/        # data structures
  └── exceptions/   # custom exceptions
  ```
- **Dependency Injection**: Use interfaces for loose coupling
- **Base Contracts**: Follow BaseSiteScraper pattern: navigate(), scrape(), normalize()

### Developer Experience

- **Python-First API**: Async/await patterns with proper type annotations
- **Configuration via YAML**: Site modules configure capabilities via YAML, not code changes
- **CLI Support**: Site-specific CLI classes in `src/sites/{site}/cli/main.py`
- **Error Messages**: Clear, actionable error messages with correlation IDs for debugging

### Documentation Requirements

- **API Reference**: Auto-generated from docstrings
- **Quickstart Guide**: Step-by-step for adding new site modules
- **Example Modules**: Reference implementations in `src/sites/`
- **Architecture Guide**: How to add new sub-modules

### Testing Requirements

- **Unit Tests**: For framework components in `tests/`
- **Integration Tests**: For browser session workflows
- **Test Fixtures**: DOM samples for selector testing
- **Mock Patterns**: pytest-mock for external dependencies

### Distribution

- **Package**: PyPI distribution ready
- **Versioning**: Semantic versioning
- **Dependencies**: Defined in pyproject.toml/requirements.txt
- **Type Hints**: MyPy strict mode compatible

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-Solving MVP - Focus on proving the core technical solution works (Cloudflare bypass via config flag)

**Resource Requirements:** 
- Python developer with Playwright experience
- Knowledge of browser fingerprinting techniques
- Understanding of async/await patterns in Python

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Alex (Site Module Developer) adding `cloudflare_protected: true` to site config
- Basic challenge detection and wait logic

**Must-Have Capabilities:**
1. `cloudflare_protected: true` YAML configuration flag
2. Stealth browser profile with:
   - User agent rotation
   - Viewport normalization
   - Browser API exposure (canvas, WebGL, fonts)
   - Automation signal suppression (`navigator.webdriver`)
3. Challenge detection (HTML pattern matching)
4. Automatic wait for challenge completion
5. Retry logic with exponential backoff
6. Works in both headless and headed modes

### Post-MVP Features

**Phase 2 (Growth):**
- Support for other CDN/WAF providers (Akamai, Imperva)
- Advanced fingerprinting techniques
- Proxy rotation support
- Enhanced logging and observability

**Phase 3 (Expansion):**
- Self-learning detection that adapts to new challenges
- One-click site module generation for protected sites
- CAPTCHA solving capability (separate feature)
- Authenticated login wall handling

### Risk Mitigation Strategy

**Technical Risks:**
- Cloudflare updating detection methods → Mitigation: Configurable patterns, confidence scoring
- False positives/negatives → Mitigation: Multi-signal detection approach
- Headless mode differences → Mitigation: Mode-specific configurations

**Market Risks:**
- Need to validate bypass works on real Cloudflare-protected sites → Mitigation: Test with known sites first
- Competition from existing solutions → Mitigation: Focus on config-driven approach and framework architecture

**Resource Risks:**
- Can launch with smaller feature set → MVP focuses only on core bypass capability

## Functional Requirements

### Configuration Management

- FR1: Site Module Developers can configure Cloudflare protection via YAML flag (`cloudflare_protected: true`)
- FR2: Site Module Developers can customize challenge wait timeout per site
- FR3: Site Module Developers can adjust detection sensitivity levels

### Stealth/Browser Fingerprinting

- FR4: The framework can apply browser fingerprint configurations to Playwright context
- FR5: The framework can suppress automation detection signals (`navigator.webdriver`)
- FR6: The framework can rotate user agent strings
- FR7: The framework can normalize viewport dimensions
- FR8: The framework can inject JavaScript initialization scripts for browser API exposure including canvas and WebGL fingerprint randomization

### Challenge Detection

- FR9: The framework can detect Cloudflare challenge pages via HTML pattern matching
- FR10: The framework can detect challenge completion via cookie-based clearance
- FR11: The framework can detect URL redirect patterns
- FR12: The framework can implement multi-signal detection with confidence scoring

### Resilience & Retry

- FR13: The framework can automatically wait for challenge completion
- FR14: The framework can implement retry logic with exponential backoff
- FR15: The framework can handle timeout scenarios gracefully

### Observability

- FR16: The framework can provide structured logging for challenge events
- FR17: The framework can expose metrics for monitoring bypass success rates

### Browser Modes

- FR18: The framework can work in headless browser mode
- FR19: The framework can work in headed browser mode

## Non-Functional Requirements

### Performance

- **Challenge Wait Time**: Average time from request to content availability must be <30 seconds (includes challenge wait time)
- **Bypass Success Rate**: >95% success rate on known Cloudflare-protected sites
- **False Positive Rate**: <1% - legitimate non-protected sites should not be incorrectly flagged
- **Headless/Headed Parity**: >90% - headless success rate should be within 10% of headed mode

### Security

- **Credential Handling**: Secure storage and handling of proxy authentication credentials
- **Automation Signal Protection**: No exposure of browser automation signals in logs that could aid detection
- **Session Cookie Security**: Secure handling of any session cookies obtained during challenge resolution

### Scalability

- **Concurrent Sessions**: Support for multiple concurrent browser sessions
- **Resource Management**: Proper cleanup of browser instances, memory management
- **Configurable Limits**: User-configurable concurrency limits to prevent resource exhaustion
