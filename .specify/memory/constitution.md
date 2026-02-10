<!-- 
SYNC IMPACT REPORT
==================

Version Change: 1.0.0 → 1.0.1 (PATCH - Operating constraint addition)

Rationale: Added System Command Bypass Policy for ps commands to enable automated 
resource monitoring without user approval barriers. This is a non-breaking addition 
that clarifies system command execution policy for monitoring operations.

Core Principles Established: 8 (unchanged)
- I. Semantic Selector-Centric Architecture (NON-NEGOTIABLE)
- II. Deep Modularity with Single Responsibility
- III. Asynchronous-First Design with Playwright Real Browser Execution
- IV. Stealth & Human Behavior Emulation (Production Essential)
- V. Tab-Aware Context Scoping
- VI. Data Integrity & Schema Versioning
- VII. Production Fault Tolerance & Resilience
- VIII. Observability & Structured Logging

Operating Constraints Sections: 6 (added Section F)
- A. Flashscore-Specific Technical Requirements
- B. Network & Proxy Strategy
- C. Legal & Ethical Boundaries
- D. Research vs Production Configuration Modes
- E. Match Failure & Auto-Abort Policies
- F. System Command Bypass Policy (NEW)

Governance Section: 
- Mandatory Code Review Checklist
- Breaking Changes & Version Bumping Policy
- Constitution Amendment Process
- Compliance Verification Requirements
- Runtime Guidance References

Template Synchronization Status:
✅ .specify/templates/spec-template.md - VERIFIED (no constitution-specific gates)
✅ .specify/templates/plan-template.md - REQUIRES UPDATE (add Constitution Check details)
✅ .specify/templates/tasks-template.md - VERIFIED (task categorization already flexible)
⚠️ .specify/templates/checklist-template.md - INFORMATION: Code review checklist formalized here
✅ .specify/templates/agent-file-template.md - No action required

Dependent Artifacts:
- No existing implementation code (greenfield project)
- No prior constitution versions to migrate
- Module READMEs will be created during implementation

Follow-Up TODOs:
1. Update plan-template.md "Constitution Check" section with specific Flashscore gates
2. Create developer onboarding guide linking to this constitution
3. Create selector engine specification (referenced as backbone)
4. Create stealth configuration reference guide

Implementation Ready: ✅ YES
- All placeholders replaced with concrete values
- Boundaries explicitly defined
- Governance processes specified
- Ready for initial PR/task creation
-->

****# Flashscore Scraper Constitution

## Core Principles

### I. Semantic Selector-Centric Architecture (NON-NEGOTIABLE)

The Selector Engine is the system backbone. All extraction logic must rely on semantic selector definitions resolved through a multi-strategy, confidence-scored selector engine with snapshot-backed failure analysis and drift detection. Direct, hardcoded selectors are forbidden outside the Selectors Engine. Selectors represent intent (e.g., "home_team_name"), not implementation. Multi-strategy resolution is mandatory for every selector: primary strategy → secondary fallback → tertiary structural fallback. Selector resolution returns confidence scores; confidence < 0.6 triggers automatic snapshot + warning; confidence 0.6–0.8 returns element + warning; confidence > 0.8 returns element accepted. No single-strategy selectors allowed.

### II. Deep Modularity with Single Responsibility

The scraper must be written in clean, production-ready, object-oriented Python with deep modularity: modules can be nested arbitrarily deep, each with a single responsibility. Core modules (navigator, tab_controller, extractor) must each have sub-modules (e.g., navigator.stealth, navigator.routing). Utility modules (retry, logging, validation, data_models), service modules (network, browser_management, data_storage), and helper modules (e.g., data_storage.json_handler) must all exist as distinct, independently testable units. Every module must include its own README.md documenting purpose, responsibilities, dependencies, public API, usage examples, configuration, error handling, testing notes, and integration points.

### III. Asynchronous-First Design with Playwright Real Browser Execution

The scraper MUST use Python asyncio and Playwright's async API exclusively. Real browser execution (Chromium) is mandatory — no HTTP-layer scraping. The browser MUST be fully rendered with JavaScript execution, DOM mutation handling, client-side routing awareness, and complete rendering pipeline. Headless mode is optional for debugging; non-headless mode enables human behavior simulation. All network operations MUST be non-blocking. No thread-based parallelism; async/await coordination only.

### IV. Stealth & Human Behavior Emulation (Production Essential)

Flashscore has aggressive anti-bot detection. Stealth configuration is mandatory: custom user-agent rotation, locale/timezone/language consistency, browser fingerprint normalization via playwright-stealth or custom patches. Human behavior emulation is non-negotiable: natural scrolling, randomized dwell times, mouse movement modeling, imperfect execution patterns, realistic click timing. Headless browser execution without stealth is unacceptable in production. All interactions must simulate realistic human pause/resume patterns.

### V. Tab-Aware Context Scoping

Flashscore's multi-layer UI (primary, secondary, tertiary tabs) requires explicit tab management. The TabController MUST determine tab availability dynamically (some tabs are match-dependent). Selectors MUST be tab-aware and context-scoped: `Selector("odds_row").within("odds_tab_container")` with explicit parent container and required active tab state. DOM nodes from inactive tabs MUST NOT pollute extraction. Tab success MUST be verified via element-based readiness checks and semantic DOM pattern presence, not just visual confirmation.

### VI. Data Integrity & Schema Versioning

All output MUST include a schema_version field. Backward compatibility MUST be maintained for previous schema versions. Deprecated fields MUST have a clear phase-out timeline. Partial data (missing tabs/sections) MUST be handled gracefully with explicit null markers. Timestamps MUST be normalized to UTC. All domain-specific data (odds, scores, time formats) MUST be parsed with locale awareness. No raw strings in output; all values MUST be typed and schema-safe.

### VII. Production Fault Tolerance & Resilience

The scraper MUST survive long-running operations with graceful degradation. Session persistence across runs is mandatory: cookies, credentials, consent state saved to disk. Checkpointing MUST enable resume after failure. Automatic retry logic with exponential backoff MUST be built-in for transient failures. Network failures MUST not crash the system. Graceful shutdown handlers MUST ensure partial results are saved. Failed match extraction MUST not block subsequent matches.

### VIII. Observability & Structured Logging

All operations MUST be logged with structured, machine-parseable JSON output. Run-ID and Match-ID MUST correlate all log entries. Performance timers MUST track extraction speed. DOM snapshots MUST be captured on selector failures and low-confidence resolutions. Network events MUST be monitored (read-only) to validate content load completion. Logs MUST enable post-mortem debugging without re-running scrapers.

## Operating Constraints & Boundaries

### A. Flashscore-Specific Technical Requirements

**SPA Architecture Awareness:**
- Page transitions do NOT trigger full reloads; content is injected dynamically via XHR/fetch
- URL changes ≠ DOM readiness; explicit readiness validation required
- Secondary/tertiary tabs do NOT preload data; each tab click triggers new async requests
- Skeleton loaders and placeholder nodes MUST be detected; selectors must encode readiness logic

**Anti-Bot Defenses:**
- Missing browser fingerprints → instant detection
- Unrealistic click timing → silent content failure
- No mouse movement/scrolling → flagged as bot
- Headless-only execution → immediately detected
- Concurrency (parallel requests) → rapid IP blocking

**DOM Volatility:**
- CSS class names rotate frequently and are intentionally obfuscated
- Stable selectors use semantic attributes, text anchors, DOM position patterns
- Brittle static selectors are forbidden; semantic strategies required
- Class name changes must NOT break extraction

### B. Network & Proxy Strategy

**Residential Proxies (Mandatory for Production):**
- Datacenter IPs are fragile; residential proxies reduce detection risk
- Sticky sessions MUST be maintained during entire match extraction
- IP rotation occurs between matches, NEVER within a match
- Proxy health MUST be continuously monitored; failed proxies auto-retired
- Proxy country targeting MUST align with content locale

**Rate Limiting & Session Safety:**
- Conservative aggression: stealth settings adapt based on risk tolerance
- Configurable caps on hourly/daily requests to avoid blocking
- Session longevity protection: do NOT exhaust IP reputation with excessive requests
- Kill-switch logic triggers automatic shutdown on detection escalation

### C. Legal & Ethical Boundaries

**Compliance Acknowledgment:**
- Flashscore robots.txt explicitly disallows scraping
- This project is designed for personal research and educational purposes only
- NOT intended for commercial exploitation or terms-of-service violation
- NOT intended for competitive intelligence or unfair trading advantages

**Responsibility:**
- Implementation MUST respect Terms of Service intent, not just letter
- Automatic shutdown on detection escalation is mandatory
- Rate limiting is a contractual commitment, not optional
- Commercial use is strictly prohibited

### D. Research vs Production Configuration Modes

**Research Mode (Data Collection & Prototyping):**
- DOM snapshots: Aggressive (primary + secondary tiers)
- Retry limits: High (5-10 attempts per selector)
- Confidence thresholds: Lenient (accept > 0.5)
- Rate limiting: Conservative (slow but thorough)
- Logging: DEBUG level with full execution traces

**Production Mode (Long-Running Operations):**
- DOM snapshots: Minimal (failure-only)
- Retry limits: Low (2-3 attempts)
- Confidence thresholds: Strict (require > 0.8)
- Rate limiting: Optimized for speed
- Logging: INFO level with errors only

**Mode Enforcement:**
- Runtime configuration via CLI flags
- Environment-based defaults
- Safety locks to prevent accidental production mode in development

### E. Match Failure & Auto-Abort Policies

**Failed Run Definitions:**

**League-Level Failure (Auto-Blacklist):**
- > 50% matches fail selector confidence thresholds
- > 30% matches have missing critical tabs (Odds or H2H)
- Consistent soft-block detection across all proxies

**Competition-Level Failure (Extended Blacklist):**
- > 70% matches fail extraction completely
- Persistent DOM structure changes (selector engine unable to adapt)
- All proxy IPs flagged simultaneously

**Auto-Abort Triggers (Immediate):**
- Detection escalation detected across all active proxies
- League blacklist: 3 consecutive failed runs → 24-hour blacklist
- Competition blacklist: 5 consecutive failed runs → 72-hour blacklist
- Soft abort: success rate drops below 20% → finish current match, stop

### F. System Command Bypass Policy

**Process Monitoring Commands (ps):**
- System process monitoring commands (ps, tasklist, etc.) MUST use bypass policy
- Bypass policy allows execution without user approval for monitoring operations
- This applies to resource monitoring, health checks, and system introspection
- Bypass policy is limited to read-only system queries
- No destructive operations allowed under bypass policy
- All bypassed commands must be logged for audit purposes

**Recovery & Override:**
- Automatic retry after blacklist period expires
- Manual override for emergency situations (requires explicit flag)
- Progressive backoff for repeated failures

## Development Workflow & Review Gates

### Mandatory Code Review Checklist

All PRs MUST verify:

1. **Architecture Compliance:**
   - [ ] Selector Engine used for all DOM queries (no hardcoded selectors outside engine)
   - [ ] Multi-strategy resolution present for new selectors
   - [ ] Confidence scoring implemented and validated
   - [ ] Tab-scoping applied (where applicable)

2. **Modularity Standards:**
   - [ ] New modules have README.md with full documentation
   - [ ] Single responsibility verified
   - [ ] No circular dependencies
   - [ ] Public API clearly defined

3. **Async Safety:**
   - [ ] No blocking I/O in async context
   - [ ] No thread-based parallelism; asyncio only
   - [ ] Proper task cleanup on cancellation
   - [ ] Timeouts applied to all network operations

4. **Stealth & Detection:**
   - [ ] Human behavior patterns verified
   - [ ] Fingerprint consistency checked
   - [ ] Rate limiting respected
   - [ ] No parallelization of match extraction

5. **Data Integrity:**
   - [ ] Schema version incremented (if breaking changes)
   - [ ] Backward compatibility maintained
   - [ ] Null handling explicit for optional fields
   - [ ] Domain normalization (UTC times, typed values)

6. **Resilience & Logging:**
   - [ ] Structured JSON logging in place
   - [ ] Snapshot capture on failures
   - [ ] Retry logic with exponential backoff
   - [ ] Graceful degradation tested

7. **System Command Policy:**
   - [ ] ps commands use bypass policy for monitoring operations
   - [ ] Read-only system queries properly identified
   - [ ] No destructive operations under bypass policy
   - [ ] Bypassed commands logged for audit

### Breaking Changes & Version Bumping

**MAJOR version bump (X.0.0):**
- Selector Engine API changes (e.g., confidence threshold definition changes)
- Core module interface changes (navigator, extractor, tab_controller)
- Data schema incompatibilities (fields removed, types changed)
- Backward compatibility cannot be maintained

**MINOR version bump (0.X.0):**
- New selectors added
- New tabs supported
- New domain (e.g., cricket, basketball)
- Backward-compatible API extensions

**PATCH version bump (0.0.X):**
- Selector improvements (strategy re-ranking, new fallback discovery)
- Bug fixes in extraction logic
- Stealth improvements
- Retry strategy optimizations
- Documentation updates

## Governance

**Constitution as the Law:**
This constitution supersedes all other practices, coding standards, and conventions. Any conflict between a pull request's approach and this document MUST be resolved in favor of the constitution. PRs that violate core principles (I-VIII) or operating constraints (A-E) MUST be rejected.

**Amendment Process:**
1. Propose amendment with rationale (in GitHub issue or PR comment)
2. Document old vs new requirements
3. Identify affected templates/artifacts (`.specify/templates/**`)
4. Specify version bump type (MAJOR/MINOR/PATCH)
5. Obtain approval (maintainer consensus)
6. Update constitution with rationale comment
7. Propagate all dependent template changes
8. Update version and LAST_AMENDED_DATE

**Compliance Verification:**
- All new tasks MUST reference compliance gates
- Code reviews MUST use the mandatory checklist
- Failed runs MUST log constitution compliance issues
- Template updates MUST be synchronized with constitution changes

**Runtime Guidance:**
For day-to-day development decisions, refer to implementation guidance docs in `.specify/` and module-specific READMEs. Those documents provide concrete how-to guidance; this constitution provides the why and what boundaries must never be crossed.

---

**Version**: 1.0.1 | **Ratified**: 2026-01-27 | **Last Amended**: 2026-01-30
