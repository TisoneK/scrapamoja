# Feature Specification: Stealth & Anti-Detection System

**Feature Branch**: `002-stealth-system`  
**Created**: 2026-01-27  
**Status**: Draft  
**Input**: User description: "Stealth & Anti-Detection System"

## User Scenarios & Testing

### User Story 1 - Prevent Detection as Automated Bot (Priority: P1)

A security-conscious scraper needs to operate without triggering bot detection mechanisms on protected websites. The system must mask all indicators that would identify it as an automated tool, ensuring requests appear indistinguishable from legitimate user browsers.

**Why this priority**: Detection triggers blocking, rate limiting, or IP bans, which completely breaks the scraper's functionality. This is the foundational requirement for all other stealth capabilities.

**Independent Test**: Configure stealth system, navigate to target website, verify no bot detection signals are triggered and scraper can access pages that block standard automation tools.

**Acceptance Scenarios**:

1. **Given** a Playwright browser instance, **When** the stealth system initializes, **Then** the `navigator.webdriver` property is undefined and `navigator.plugins` are populated
2. **Given** a configured stealth system, **When** making requests to a target website, **Then** HTTP headers do not contain automation indicators (no `Playwright` user-agent strings)
3. **Given** a stealth-enabled browser, **When** JavaScript probes for `window.chrome` object, **Then** the object responds like a real Chrome browser
4. **Given** stealth configuration enabled, **When** the scraper navigates to a page, **Then** no bot detection signals are logged or reported

---

### User Story 2 - Rotate IP Addresses with Session Persistence (Priority: P1)

A large-scale scraper needs to distribute requests across multiple residential IPs to avoid detection by frequency analysis, while maintaining sticky sessions so that user context and authentication state persist within individual proxy sessions.

**Why this priority**: Frequency-based detection (many requests from same IP) is a primary blocking mechanism. Session persistence is critical to maintain authentication state across multiple requests.

**Independent Test**: Configure proxy rotation, navigate multiple pages per match, verify requests use different IPs while maintaining session cookies and authentication state within each IP's session.

**Acceptance Scenarios**:

1. **Given** a residential proxy pool configured, **When** starting a new match, **Then** a sticky session is established with one residential IP
2. **Given** an active sticky session, **When** navigating between match pages, **Then** all requests in that session use the same residential IP
3. **Given** multiple matches being scraped, **When** starting each new match, **Then** a new IP from the proxy pool is selected for the session
4. **Given** a proxy rotation strategy configured, **When** a session completes, **Then** that IP is available for reuse according to rotation cooldown rules

---

### User Story 3 - Emulate Human Interaction Patterns (Priority: P1)

The scraper must behave like a human user navigating the website, including realistic mouse movements, scroll patterns, and timing between interactions, to avoid triggering behavioral analysis systems that detect unnatural interaction sequences.

**Why this priority**: Modern detection systems analyze interaction patterns (speed, precision, sequences) to identify bots. Realistic human behavior is essential for avoiding detection.

**Independent Test**: Execute a series of page interactions with stealth enabled, capture browser telemetry, verify mouse movements are gradual, scroll timing has natural variation, and click-to-navigation timing matches human reflexes.

**Acceptance Scenarios**:

1. **Given** a stealth-enabled browser, **When** clicking an element, **Then** there is a random delay between 100-500ms before the click is executed
2. **Given** mouse movement simulation enabled, **When** moving from one element to another, **Then** the movement follows a curved path with natural acceleration/deceleration
3. **Given** page interaction required, **When** scrolling content, **Then** scroll speed varies naturally and includes occasional pauses
4. **Given** rapid sequential interactions configured, **When** executing multiple actions, **Then** random micro-delays are injected to prevent machine-like precision

---

### User Story 4 - Normalize Browser Fingerprint (Priority: P2)

The scraper must report realistic device characteristics (screen resolution, timezone, language, plugins) that match legitimate user browsers, preventing fingerprinting services from detecting inconsistent or impossible device configurations.

**Why this priority**: Fingerprinting systems collect dozens of attributes to build a device profile; inconsistent attributes (impossible screen size, mismatched timezone) are red flags for automation.

**Independent Test**: Configure fingerprint normalization, navigate to fingerprinting service, verify reported device characteristics are coherent and match expected patterns for the user-agent string.

**Acceptance Scenarios**:

1. **Given** fingerprint normalization enabled, **When** the browser reports `navigator.userAgent`, **Then** the user-agent, timezone, and language are internally consistent
2. **Given** a Chrome user-agent configured, **When** requesting device properties, **Then** reported screen resolution is a valid modern display size matching Chrome distribution
3. **Given** fingerprint profile configuration, **When** multiple pages load in the same session, **Then** all fingerprint attributes remain consistent across the session
4. **Given** no explicit fingerprint configuration, **Then** fingerprint normalization uses realistic defaults for common modern devices

---

### User Story 5 - Handle Cookie and Consent Flows (Priority: P2)

The scraper must automatically process GDPR and cookie consent workflows that block content until accepted, allowing seamless navigation through pages that require consent management before data access.

**Why this priority**: Many target websites have consent dialogs that block content; automating this workflow enables broader site coverage without manual intervention.

**Independent Test**: Navigate to a website with cookie/GDPR consent requirements, verify consent workflow is automatically processed, and content becomes accessible without manual action.

**Acceptance Scenarios**:

1. **Given** a website with cookie consent dialog, **When** the page loads, **Then** the consent handler detects the dialog and accepts required cookies
2. **Given** GDPR consent requirements present, **When** the page displays privacy options, **Then** the system accepts functional cookies and remembers the choice
3. **Given** consent accepted, **When** navigating to subsequent pages, **Then** no additional consent dialogs are displayed for the session
4. **Given** consent handler failure, **When** timeout occurs, **Then** the system logs the failure and attempts content extraction anyway with available data

---

### User Story 6 - Mask Automation Indicators (Priority: P2)

The scraper must remove all traces that might identify it as Playwright-driven automation, including console messages, global objects, and execution context flags, ensuring compatibility with detection services that look for automation markers.

**Why this priority**: Sophisticated detection systems check for Playwright, Selenium, or other automation framework indicators; masking these prevents trivial detection.

**Independent Test**: Execute scraper, run JavaScript checks from webpage that probe for automation frameworks, verify no automation indicators are detected.

**Acceptance Scenarios**:

1. **Given** anti-detection enabled, **When** JavaScript code checks for `navigator.webdriver`, **Then** the property is either undefined or false
2. **Given** automation masking active, **When** a page injects code to detect Playwright, **Then** no Playwright-specific objects or methods are accessible
3. **Given** stealth mode configured, **When** reading `process.version` from browser context, **Then** the value is undefined or reports legitimate browser version
4. **Given** anti-detection active, **When** JavaScript analyzes global object properties, **Then** no Playwright-internal properties are exposed

---

### Edge Cases

- What happens when a proxy IP is blocked or returns HTTP 403? System should fall back to next available IP or abort with clear error
- What happens when fingerprint normalization creates impossible combinations? System should validate and use safe defaults instead
- How does system handle consent dialogs that differ significantly from standard patterns? System should attempt extraction with partial data rather than failing completely
- What happens when multiple competing anti-detection measures conflict (e.g., User-Agent says Chrome but fingerprint says Firefox)? System should maintain internal consistency and use primary user-agent as source of truth

## Requirements

### Functional Requirements

- **FR-001**: System MUST normalize browser fingerprint by providing coherent `navigator` properties (userAgent, platform, language, timezone) that are internally consistent
- **FR-002**: System MUST implement residential proxy rotation with sticky sessions that maintain the same IP for all requests within a single match scrape
- **FR-003**: System MUST emulate human behavior patterns including: random mouse movements with curves, variable scroll speeds, click hesitation delays (100-500ms), and micro-pauses between sequential actions
- **FR-004**: System MUST mask all Playwright automation indicators including `navigator.webdriver`, Playwright-specific console messages, and global automation objects
- **FR-005**: System MUST automatically detect and process GDPR/cookie consent dialogs without manual intervention before allowing content access
- **FR-006**: System MUST provide user-agent string rotation across configurable browser types (Chrome, Firefox, Safari) with realistic version combinations
- **FR-007**: System MUST handle proxy rotation failures gracefully by attempting fallback IPs or aborting with traceable error logging
- **FR-008**: System MUST persist proxy session state (cookies, authentication) across multiple page navigations within a single IP session
- **FR-009**: System MUST validate fingerprint coherence before initialization and fall back to safe defaults for impossible combinations
- **FR-010**: System MUST provide configuration control for all stealth measures independently (enable/disable each component without affecting others)
- **FR-011**: System MUST log all anti-detection measures applied during initialization for auditability and debugging
- **FR-012**: System MUST be compatible with Playwright async API exclusively - no blocking or synchronous operations
- **FR-013**: System MUST provide structured JSON logging with correlation IDs for stealth-related events for traceability

### Technical Constraints

- **TC-001**: Stealth system must be platform-agnostic (Windows, macOS, Linux) with no OS-specific implementation details
- **TC-002**: All stealth measures must be transparent to caller - stealth system initialization must not require changes to caller code
- **TC-003**: Proxy management must support residential IP providers (e.g., Bright Data, Oxylabs) with proxy rotation strategy configuration
- **TC-004**: Fingerprint normalization must use realistic device data from actual browser distributions to avoid statistical anomalies
- **TC-005**: All stealth operations must be non-blocking and compatible with asyncio event loop
- **TC-006**: Stealth configuration must be documented in YAML config file with sensible production defaults
- **TC-007**: System must implement graceful degradation - if stealth component fails, scraper continues with reduced stealth levels
- **TC-008**: No external dependencies for anti-detection beyond Playwright's built-in CDP protocol support
- **TC-009**: Deep modularity required - stealth subsystems (fingerprint, proxy, behavior, consent) must be independently testable components
- **TC-010**: Implementation-first development - direct implementation with manual validation against actual detection systems

### Key Entities

- **ProxySession**: Represents a sticky session with a single residential IP, includes session cookies, IP address, rotation state, and lifecycle management (start time, last activity, TTL)
- **BrowserFingerprint**: Encapsulates all reported browser properties (userAgent, platform, language, timezone, screen resolution, plugins, media devices) that must be internally consistent
- **StealthConfig**: Configuration object controlling which anti-detection measures are enabled, proxy rotation strategy, behavior emulation intensity, consent handling rules
- **AntiDetectionEvent**: Logged event tracking stealth measures applied (fingerprint initialization, proxy rotation, bot signal masking, consent acceptance)

## Success Criteria

### Measurable Outcomes

- **SC-001**: Stealth-enabled scraper successfully navigates to 95% of target websites that block standard Playwright instances without triggering bot detection or rate limiting
- **SC-002**: Proxy rotation distributes requests across at least 5 different residential IPs when scraping 50 consecutive matches, with no more than 3 consecutive matches from the same IP
- **SC-003**: Browser fingerprint reports internally consistent values across all navigator properties (no impossible combinations like Chrome browser reporting Firefox plugins)
- **SC-004**: Cookie consent dialogs are automatically processed on 100% of tested websites that display them, without requiring manual intervention or custom per-site logic
- **SC-005**: JavaScript executed on target pages cannot detect Playwright automation framework (0 detections of `navigator.webdriver`, Playwright-specific console methods, or automation context)
- **SC-006**: Session persistence maintains authentication state across minimum 10 page navigations within a single sticky proxy session
- **SC-007**: Human behavior emulation produces click-to-navigation delays of 100-500ms and mouse movement curves that statistically match human interaction patterns
- **SC-008**: All stealth-related errors include actionable information (IP rotation failure, fingerprint conflict detected, consent handler timeout) with clear remediation steps
- **SC-009**: Stealth system initialization completes in under 2 seconds without blocking the main navigation flow
- **SC-010**: System gracefully handles proxy IP blocks by rotating to alternative IP within 1 retry attempt

## Assumptions

- Target websites use standard bot detection patterns (fingerprinting, navigation timing, interaction analysis) rather than specialized Playwright-specific detection
- Residential proxy provider (Bright Data, Oxylabs, or equivalent) with API authentication will be configured externally
- GDPR/cookie consent dialogs follow common patterns (accept button, close icon, reject option); site-specific dialogs may require custom handling
- Human behavior emulation target is "suspicious but not impossible" rather than pixel-perfect human matching
- Detection escalation is gradual (warnings → rate limiting → IP block) rather than immediate permanent bans
- Scraper target (Flashscore) does not employ specialized anti-Playwright detection or advanced behavioral analysis
- Browser fingerprint attributes (screen resolution, timezone, language) can be safely randomized within realistic ranges per user-agent

## Out of Scope

- Integration with specific proxy providers (external configuration)
- Site-specific consent handling beyond common GDPR patterns
- Detection circumvention for JavaScript-based content rendering timing analysis
- Legal/compliance evaluation of scraping practices
- Browser update handling (user-agent, fingerprint updates for new Chrome versions)
- Machine learning-based behavior analysis evasion
