---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
---

# scrapamoja - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for scrapamoja, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

**Configuration Management (FR1-FR3):**

FR1: Site Module Developers can configure Cloudflare protection via YAML flag (`cloudflare_protected: true`)

FR2: Site Module Developers can customize challenge wait timeout per site

FR3: Site Module Developers can adjust detection sensitivity levels

**Stealth/Browser Fingerprinting (FR4-FR8):**

FR4: The framework can apply browser fingerprint configurations to Playwright context

FR5: The framework can suppress automation detection signals (`navigator.webdriver`)

FR6: The framework can rotate user agent strings

FR7: The framework can normalize viewport dimensions

FR8: The framework can inject JavaScript initialization scripts for browser API exposure including canvas and WebGL fingerprint randomization

**Challenge Detection (FR9-FR12):**

FR9: The framework can detect Cloudflare challenge pages via HTML pattern matching

FR10: The framework can detect challenge completion via cookie-based clearance

FR11: The framework can detect URL redirect patterns

FR12: The framework can implement multi-signal detection with confidence scoring

**Resilience & Retry (FR13-FR15):**

FR13: The framework can automatically wait for challenge completion

FR14: The framework can implement retry logic with exponential backoff

FR15: The framework can handle timeout scenarios gracefully

**Observability (FR16-FR17):**

FR16: The framework can provide structured logging for challenge events

FR17: The framework can expose metrics for monitoring bypass success rates

**Browser Modes (FR18-FR19):**

FR18: The framework can work in headless browser mode

FR19: The framework can work in headed browser mode

### NonFunctional Requirements

**Performance:**

NFR1: Challenge Wait Time - Average time from request to content availability must be <30 seconds (includes challenge wait time)

NFR2: Bypass Success Rate - >95% success rate on known Cloudflare-protected sites

NFR3: False Positive Rate - <1% - legitimate non-protected sites should not be incorrectly flagged

NFR4: Headless/Headed Parity - >90% - headless success rate should be within 10% of headed mode

**Security:**

NFR5: Credential Handling - Secure storage and handling of proxy authentication credentials

NFR6: Automation Signal Protection - No exposure of browser automation signals in logs that could aid detection

NFR7: Session Cookie Security - Secure handling of any session cookies obtained during challenge resolution

**Scalability:**

NFR8: Concurrent Sessions - Support for multiple concurrent browser sessions

NFR9: Resource Management - Proper cleanup of browser instances, memory management

NFR10: Configurable Limits - User-configurable concurrency limits to prevent resource exhaustion

### Additional Requirements

**Architecture Requirements:**

- Brownfield project - integrate with existing Scrapamoja framework
- Use SCR-003 sub-module pattern: `src/stealth/cloudflare/` with core/, detection/, config/, models/, exceptions/
- Integration with existing systems:
  - Import retry mechanisms from `src/resilience/` - NO new retry implementation
  - Import structured logging from `src/observability/` - NO new logging infrastructure
  - Extend existing `src/stealth/` for browser fingerprinting
- Browser context: Read-only integration - receives context, doesn't create sessions
- Follow async/await patterns (async def for all I/O)
- Use dependency injection for loose coupling
- Implement __aenter__/__aexit__ for resource managers
- Type safety: MyPy strict mode with Pydantic models

**Implementation Priority:**
- Create `src/stealth/cloudflare/` directory structure with `__init__.py` files in all subdirectories
- Implement core/applier/ module first

### UX Design Requirements

(No UX Design document was provided for this project)

### FR Coverage Map

| FR Category | FRs | Epic Assignment |
|-------------|-----|-----------------|
| Configuration Management | FR1-FR3 | Epic 1 |
| Stealth/Browser Fingerprinting | FR4-FR8 | Epic 2 |
| Challenge Detection | FR9-FR12 | Epic 3 |
| Resilience & Retry | FR13-FR15 | Epic 4 |
| Observability | FR16-FR17 | Epic 5 |
| Browser Modes | FR18-FR19 | Epic 2 (integrated) |

## Epic List

### Epic 1: Configuration Management
**User Outcome:** Site module developers can configure Cloudflare protection via simple YAML flags
**FRs covered:** FR1, FR2, FR3
**Stories:** 3

### Epic 2: Stealth/Browser Fingerprinting
**User Outcome:** Browsers appear as regular user browsers to avoid detection
**FRs covered:** FR4, FR5, FR6, FR7, FR8, FR18, FR19
**Stories:** 6

### Epic 3: Challenge Detection
**User Outcome:** Framework can detect Cloudflare challenges using multiple signals
**FRs covered:** FR9, FR10, FR11, FR12
**Stories:** 4

### Epic 4: Resilience & Retry
**User Outcome:** Failed attempts are automatically retried with proper timeout handling
**FRs covered:** FR13, FR14, FR15
**Stories:** 3

### Epic 5: Observability
**User Outcome:** Operations teams can monitor and debug challenge handling
**FRs covered:** FR16, FR17
**Stories:** 2

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 1 | YAML flag configuration for Cloudflare protection |
| FR2 | Epic 1 | Challenge wait timeout configuration |
| FR3 | Epic 1 | Detection sensitivity configuration |
| FR4 | Epic 2 | Apply browser fingerprint to Playwright context |
| FR5 | Epic 2 | Suppress navigator.webdriver |
| FR6 | Epic 2 | User agent rotation |
| FR7 | Epic 2 | Viewport normalization |
| FR8 | Epic 2 | Canvas/WebGL fingerprint randomization |
| FR9 | Epic 3 | HTML pattern detection |
| FR10 | Epic 3 | Cookie clearance detection |
| FR11 | Epic 3 | URL redirect detection |
| FR12 | Epic 3 | Multi-signal detection with confidence scoring |
| FR13 | Epic 4 | Automatic challenge wait |
| FR14 | Epic 4 | Retry logic with exponential backoff |
| FR15 | Epic 4 | Timeout handling |
| FR16 | Epic 5 | Structured logging |
| FR17 | Epic 5 | Metrics exposure |
| FR18 | Epic 2 | Headless browser mode |
| FR19 | Epic 2 | Headed browser mode |

<!-- Repeat for each epic in epics_list (N = 1, 2, 3...) -->

## Epic 1: Configuration Management

**Epic Goal:** Enable site module developers to configure Cloudflare protection via YAML configuration

<!-- Repeat for each story (M = 1, 2, 3...) within epic 1 -->

### Story 1.1: YAML Cloudflare Flag Configuration

As a Site Module Developer,
I want to enable Cloudflare protection with a simple YAML flag,
So that I can quickly configure sites without writing custom code.

**Acceptance Criteria:**

**Given** a site module YAML configuration file
**When** I set `cloudflare_protected: true`
**Then** the framework activates all Cloudflare bypass mechanisms
**And** the site is processed with stealth configuration, challenge detection, and retry logic

**Given** a site module YAML configuration file
**When** I set `cloudflare_protected: false` or omit the flag
**Then** no Cloudflare-specific processing is applied
**And** existing non-Cloudflare site modules remain completely unaffected

### Story 1.2: Challenge Wait Timeout Configuration

As a Site Module Developer,
I want to customize the challenge wait timeout per site,
So that I can handle sites with longer challenge times.

**Acceptance Criteria:**

**Given** a site module with `cloudflare_protected: true`
**When** I configure `challenge_timeout: 60` (seconds)
**Then** the framework waits up to 60 seconds for challenge completion
**And** returns timeout error after 60 seconds if challenge not resolved

**Given** no timeout configuration
**Then** the default timeout of 30 seconds is applied

### Story 1.3: Detection Sensitivity Configuration

As a Site Module Developer,
I want to adjust detection sensitivity levels,
So that I can balance between false positives and false negatives.

**Acceptance Criteria:**

**Given** a site module with `cloudflare_protected: true`
**When** I configure `detection_sensitivity: high|medium|low`
**Then** the detection logic uses appropriate thresholds
**And** high sensitivity detects more challenges but may have higher false positives
**And** low sensitivity is more conservative

---

## Epic 2: Stealth/Browser Fingerprinting

**Epic Goal:** Apply browser fingerprint configurations to avoid detection as automation

### Story 2.1: Automation Signal Suppression

As a Framework Developer,
I want to suppress navigator.webdriver flag,
So that the browser appears as a regular user browser.

**Acceptance Criteria:**

**Given** a Playwright browser context
**When** Cloudflare protection is enabled
**Then** the navigator.webdriver property is set to false/undefined
**And** other automation signals are masked

### Story 2.2: Canvas/WebGL Fingerprint Randomization

As a Framework Developer,
I want to randomize canvas and WebGL fingerprints,
So that the browser has unique fingerprints for each session.

**Acceptance Criteria:**

**Given** a Playwright browser context
**When** Cloudflare protection is enabled
**Then** JavaScript initialization scripts are injected
**And** canvas fingerprint returns randomized values
**And** WebGL renderer info is spoofed

### Story 2.3: User Agent Rotation

As a Framework Developer,
I want to rotate user agent strings,
So that requests appear to come from different browsers.

**Acceptance Criteria:**

**Given** Cloudflare protection is enabled
**When** creating a new browser context
**Then** a valid user agent string is selected from a pool
**And** the user agent matches realistic browser versions

### Story 2.4: Viewport Normalization

As a Framework Developer,
I want to normalize viewport dimensions,
So that the browser window size doesn't reveal automation.

**Acceptance Criteria:**

**Given** Cloudflare protection is enabled
**When** creating a new browser context
**Then** viewport is set to standard dimensions (e.g., 1920x1080, 1366x768)
**And** viewport matches common user configurations

### Story 2.5: Browser Profile Applier

As a Framework Developer,
I want to apply all stealth configurations to Playwright context,
So that the full stealth profile is applied consistently.

**Acceptance Criteria:**

**Given** Cloudflare protection is enabled
**When** applying stealth profile to a Playwright context
**Then** all stealth configurations are applied (webdriver, canvas, UA, viewport)
**And** the context appears as a regular user browser

### Story 2.6: Headless and Headed Mode Support

As a Framework Developer,
I want the stealth configuration to work in both headless and headed modes,
So that users can choose their preferred browser mode.

**Acceptance Criteria:**

**Given** Cloudflare protection is enabled
**When** running in headless mode
**Then** stealth configuration is applied correctly
**And** headless success rate is within 10% of headed mode (>90% parity)

**Given** Cloudflare protection is enabled
**When** running in headed mode
**Then** stealth configuration is applied correctly
**And** challenges are handled without manual intervention

---

## Epic 3: Challenge Detection

**Epic Goal:** Detect Cloudflare challenge pages using multiple signals

### Story 3.1: HTML Pattern Detection

As a Framework Developer,
I want to detect Cloudflare challenge pages via HTML pattern matching,
So that I can identify when a challenge is presented.

**Acceptance Criteria:**

**Given** a page response
**When** Cloudflare presents a challenge page
**Then** the framework detects known Cloudflare challenge HTML patterns
**And** returns a challenge detected signal

**Given** a regular page
**When** no challenge patterns are matched
**Then** the page is treated as normal content

### Story 3.2: Cookie Clearance Detection

As a Framework Developer,
I want to detect challenge completion via cookie clearance,
So that I know when the challenge has been solved.

**Acceptance Criteria:**

**Given** a browser context with Cloudflare challenge
**When** Cloudflare clears the challenge (sets clearance cookies)
**Then** the framework detects the clearance cookies
**And** returns a challenge cleared signal

**Given** no clearance cookies
**Then** the challenge is still pending

### Story 3.3: URL Redirect Detection

As a Framework Developer,
I want to detect challenge completion via URL redirect patterns,
So that I know when the challenge has been solved.

**Acceptance Criteria:**

**Given** a navigation during challenge processing
**When** the URL changes from challenge URL to original target URL
**Then** the framework detects the redirect pattern
**And** returns a challenge cleared signal

### Story 3.4: Multi-Signal Detection with Confidence Scoring

As a Framework Developer,
I want to implement multi-signal detection with confidence scoring,
So that I can make more accurate challenge detection decisions.

**Acceptance Criteria:**

**Given** a page response during navigation
**When** multiple detection signals are available
**Then** each signal is evaluated independently
**And** confidence score is calculated based on signals
**And** high confidence (>0.8) triggers challenge handling
**And** low confidence (<0.3) is treated as no challenge

---

## Epic 4: Resilience & Retry

**Epic Goal:** Automatically handle challenge waiting and retry failed attempts

### Story 4.1: Automatic Challenge Wait

As a Framework Developer,
I want to automatically wait for challenge completion,
So that challenges are handled without manual intervention.

**Acceptance Criteria:**

**Given** a challenge is detected
**When** challenge is in progress
**Then** the framework waits for challenge completion
**And** checks for clearance every 1 second
**And** continues waiting up to configured timeout

**Given** challenge is completed within timeout
**Then** navigation proceeds with cleared session

**Given** challenge is not completed within timeout
**Then** a timeout error is raised

### Story 4.2: Retry Logic with Exponential Backoff

As a Framework Developer,
I want to implement retry logic with exponential backoff,
So that failed attempts are retried with increasing delays.

**Acceptance Criteria:**

**Given** a navigation attempt fails due to challenge
**When** retry is enabled
**Then** the framework delegates retry logic to the src/resilience/ engine
**And** uses its configured backoff parameters
**And** does not hardcode retry values in SCR-003

**Given** all retries are exhausted
**Then** a retry exhausted error is raised with details

### Story 4.3: Timeout Handling

As a Framework Developer,
I want to handle timeout scenarios gracefully,
So that the system doesn't hang indefinitely.

**Acceptance Criteria:**

**Given** challenge wait timeout is reached
**Then** a clear timeout error is raised
**And** error includes timeout value and challenge status
**And** resources are properly cleaned up

---

## Epic 5: Observability

**Epic Goal:** Provide structured logging and metrics for monitoring and debugging

### Story 5.1: Structured Logging for Challenge Events

As an Operations Engineer,
I want structured logging for challenge events,
So that I can diagnose issues in production.

**Acceptance Criteria:**

**Given** Cloudflare protection is enabled
**When** challenge events occur
**Then** structured logs are emitted with event type, timestamp, correlation ID
**And** log levels are appropriate (DEBUG for details, INFO for milestones, ERROR for failures)
**And** logs include context: URL, challenge type, wait time, retry count

### Story 5.2: Metrics Exposure for Monitoring

As an Operations Engineer,
I want metrics for monitoring bypass success rates,
So that I can track system performance.

**Acceptance Criteria:**

**Given** Cloudflare protection is enabled
**When** navigation completes (success or failure)
**Then** metrics are exposed using the existing src/observability/ metrics system
**And** includes: total attempts, successful bypasses, failed attempts, average wait time
**And** does not build new metrics infrastructure

---

<!-- End story repeat -->
