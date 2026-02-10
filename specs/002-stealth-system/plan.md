# Implementation Plan: Stealth & Anti-Detection System

**Branch**: `002-stealth-system` | **Date**: 2026-01-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-stealth-system/spec.md`

## Summary

The Stealth & Anti-Detection System masks automated browser control indicators to prevent bot detection on protected websites. Primary requirements: (1) normalize browser fingerprints to realistic device characteristics, (2) implement residential proxy rotation with sticky sessions, (3) emulate human interaction patterns (timing, mouse movement, scrolling), (4) mask Playwright automation indicators, (5) automatically process GDPR/cookie consent workflows. Core approach: modular stealth subsystems (fingerprint normalizer, proxy manager, behavior emulator, consent handler) integrated with Playwright's CDP protocol, coordinated through central StealthConfig with per-component enable/disable controls. All operations must be async-compatible and production-ready for Flashscore target.

## Technical Context

**Language/Version**: Python 3.11+ with asyncio  
**Primary Dependencies**: Playwright (async API exclusively), CDP protocol for browser control  
**Storage**: Session state (cookies, proxy assignments) persisted to disk; runtime configuration in YAML  
**Testing**: Manual validation against real detection systems (not automated test suites per constitution)  
**Target Platform**: Linux/macOS/Windows servers, production Flashscore target  
**Project Type**: Core scraper subsystem (modular, single responsibility)  
**Performance Goals**: Stealth initialization <2 seconds; proxy rotation <100ms overhead per request  
**Constraints**: Non-blocking async operations only; no external dependencies beyond Playwright; graceful degradation on stealth component failures  
**Scale/Scope**: 5 independent stealth subsystems; 4 key entity types; integration with Navigator and Tab Controller modules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Compliance Against Core Principles

✅ **I. Semantic Selector-Centric Architecture**: Stealth system does not define selectors directly (selectors are Navigator's responsibility). Stealth system provides context support for selectors through fingerprint and behavior simulation, ensuring selectors work with realistic browser state. No selector-specific violations.

✅ **II. Deep Modularity with Single Responsibility**: Stealth system designed as 5 independent subsystems: (1) fingerprint normalizer - handles device property consistency, (2) proxy manager - residential IP rotation and sticky sessions, (3) behavior emulator - human-like interaction timing, (4) consent handler - GDPR workflow automation, (5) anti-detection masker - Playwright indicator removal. Each subsystem is independently testable and can be toggled on/off without affecting others.

✅ **III. Asynchronous-First Design with Playwright Real Browser Execution**: All stealth operations use Playwright's async API exclusively. No blocking operations. Browser fingerprint/anti-detection applied via CDP protocol (native Playwright integration). Behavior emulation (delays, mouse movements) managed through async timers. No synchronous calls.

✅ **IV. Stealth & Human Behavior Emulation (Production Essential)**: This feature IS the stealth system. All requirements directly address this principle: realistic fingerprints, proxy rotation, human behavior patterns, consent handling, anti-detection masking. Production-ready by definition.

✅ **V. Tab-Aware Context Scoping**: Stealth configuration respects tab context. Consent dialogs detected before tab navigation. Proxy session persists across tab interactions within same match. Fingerprint consistency maintained within session scope. No cross-tab contamination.

✅ **VI. Data Integrity & Schema Versioning**: StealthConfig and AntiDetectionEvent entities have clear structure. All logged stealth actions include timestamps, correlation IDs, event type. Session persistence includes schema version for forward compatibility.

✅ **VII. Production Fault Tolerance & Resilience**: Stealth failures degrade gracefully: (a) proxy IP block → fallback to next IP, (b) consent handler timeout → log failure, continue extraction, (c) fingerprint conflict → use safe defaults, (d) anti-detection mask failure → log warning, continue. No component failure crashes system.

✅ **VIII. Observability & Structured Logging**: All stealth operations logged with structured JSON: fingerprint initialization, proxy rotation, behavior emulation timing, consent acceptance, automation indicator masking. Run-ID/Match-ID correlation on all logs. DOM snapshots on failures.

### Technical Constraints Validation

✅ **TC-001**: Platform-agnostic design confirmed. No Windows-specific paths or OS APIs used. Configuration drives behavior.

✅ **TC-002**: Stealth measures transparent to caller. Navigator applies StealthConfig internally. No code changes needed at call sites.

✅ **TC-003**: Proxy manager designed for residential IP providers (Bright Data, Oxylabs) with pluggable rotation strategy.

✅ **TC-004**: Fingerprint data uses realistic distributions from actual Chrome/Firefox/Safari browser populations.

✅ **TC-005**: All operations designed as async functions compatible with asyncio event loop.

✅ **TC-006**: StealthConfig fully documented in YAML with production defaults (all stealth enabled).

✅ **TC-007**: Graceful degradation implemented at each subsystem level with fallback logic.

✅ **TC-008**: Only dependency beyond Playwright is standard library (json, asyncio, logging, etc.).

✅ **TC-009**: Deep modularity confirmed. Each subsystem independently testable.

✅ **TC-010**: Implementation-first approach: direct implementation with manual validation against real Flashscore detection systems.

### Gate Status

**STATUS**: ✅ **PASS** - All 8 core principles satisfied. All 10 technical constraints met. No violations. Ready for Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/002-stealth-system/
├── spec.md              # Feature specification (DONE)
├── plan.md              # This file - Phase 0-1 planning (IN PROGRESS)
├── research.md          # Phase 0 output - Research findings (TODO)
├── data-model.md        # Phase 1 output - Entity definitions (TODO)
├── quickstart.md        # Phase 1 output - Developer guide (TODO)
├── contracts/           # Phase 1 output - API interfaces (TODO)
│   └── stealth-system-api.md
└── checklists/
    └── requirements.md  # Specification quality validation (DONE)
```

### Source Code (repository root)

```text
src/
├── stealth/                          # STEALTH & ANTI-DETECTION SYSTEM
│   ├── __init__.py                  # Package initialization
│   ├── config.py                    # StealthConfig, fingerprint defaults, provider configs
│   ├── types.py                     # ProxySession, BrowserFingerprint, AntiDetectionEvent types
│   ├── fingerprint.py               # Browser fingerprint normalization (subsystem 1)
│   ├── proxy_manager.py             # Residential IP rotation (subsystem 2)
│   ├── behavior.py                  # Human behavior emulation (subsystem 3)
│   ├── consent_handler.py           # GDPR/cookie consent (subsystem 4)
│   ├── anti_detection.py            # Automation indicator masking (subsystem 5)
│   ├── events.py                    # AntiDetectionEvent logging and publishing
│   ├── coordinator.py               # StealthSystem main coordinator
│   └── README.md                    # Module documentation
```

## Phase 0: Research & Analysis

### Research Questions to Resolve

The spec is complete with no NEEDS CLARIFICATION items. However, research phase validates implementation approaches:

1. **Browser Fingerprint Data Sources**: Where to source realistic device characteristic distributions (screen resolutions, timezones, language patterns, plugins) for Chrome, Firefox, Safari? Options: use Playwright's built-in cdp data, use industry datasets (e.g., from w3c.org), manually curate realistic ranges. Decision needed: preferred source for statistical validity.

2. **Residential Proxy Integration Pattern**: How to integrate with residential proxy providers (Bright Data, Oxylabs) API? Options: (a) proxy rotation as context manager, (b) proxy pool abstraction with health monitoring, (c) simple URL-based proxy format. Decision needed: abstraction level and health monitoring requirements.

3. **Human Behavior Emulation Timing Distributions**: What timing distributions represent realistic human behavior? Options: uniform random, normal distribution centered on typical values, exponential distribution, empirical from behavioral studies. Decision needed: which distribution best balances realism with implementation simplicity.

4. **Consent Dialog Detection Strategy**: How to detect GDPR/consent dialogs reliably across sites? Options: (a) text-based pattern matching (e.g., "Accept All", "I Agree"), (b) DOM pattern matching (modal + button structure), (c) combination of both. Decision needed: which patterns cover common consent implementations.

5. **Playwright Anti-Detection Approach**: How to apply stealth measures with Playwright? Options: (a) use playwright-extra-plugin-stealth, (b) manual CDP protocol patches, (c) combination approach. Decision needed: dependencies vs control tradeoff.

### Research Output Format

Research findings will be documented in `research.md` with:
- **Decision**: What was chosen and implemented
- **Rationale**: Why this approach was selected
- **Alternatives Considered**: What other options were evaluated and why rejected
- **Implementation Notes**: Key technical details for implementation phase

---

## Phase 1: Design & Contracts

### 1. Data Model (`data-model.md`)

Core entities with relationships:

**ProxySession** (sticky session for one match scrape)
- ip_address: str (residential IP)
- port: int
- session_id: str (unique identifier)
- cookies: dict (session state)
- created_at: datetime
- last_activity: datetime
- ttl_seconds: int
- status: enum (active, exhausted, failed)

**BrowserFingerprint** (device properties)
- user_agent: str (e.g., "Mozilla/5.0 Chrome/120.0...")
- platform: str (e.g., "Linux", "macOS", "Windows")
- language: str (e.g., "en-US")
- timezone: str (e.g., "UTC", "America/New_York")
- screen_width: int
- screen_height: int
- color_depth: int
- timezone_offset: int
- plugins: list[str]
- media_devices: dict
- consistent: bool (internal coherence validation)

**StealthConfig** (feature toggle and configuration)
- enabled: bool
- fingerprint: BrowserFingerprint
- proxy_rotation: dict (rotation_strategy, cooldown_seconds, provider_config)
- behavior_emulation: dict (click_delay_min_ms, click_delay_max_ms, mouse_curve, scroll_variation)
- consent_handling: dict (enabled, pattern_matchers, accept_buttons)
- anti_detection: dict (mask_webdriver, mask_playwright, mask_process, remove_console_patches)
- graceful_degradation: bool (continue on component failure)

**AntiDetectionEvent** (audit log entry)
- timestamp: datetime
- event_type: str (fingerprint_initialized, proxy_rotated, behavior_simulated, consent_accepted, mask_applied)
- match_id: str
- run_id: str
- details: dict (event-specific context)
- subsystem: str (fingerprint, proxy_manager, behavior, consent_handler, anti_detection)

### 2. API Contracts (`contracts/stealth-system-api.md`)

Main coordinator interface (integration point for Navigator):

```python
class StealthSystem:
    async def initialize(self, config: StealthConfig) -> None
    async def create_proxy_session(self, match_id: str) -> ProxySession
    async def close_proxy_session(self, session_id: str) -> None
    async def get_active_fingerprint(self) -> BrowserFingerprint
    async def emulate_click(self, page: Page, selector: str) -> None
    async def emulate_scroll(self, page: Page, direction: str, amount: int) -> None
    async def process_consent_dialog(self, page: Page) -> bool
    async def validate_stealth_measures(self) -> list[str]  # warnings
```

Per-subsystem interfaces for testing:

```python
# fingerprint.py
class FingerprintNormalizer:
    def generate_fingerprint(self, user_agent: str) -> BrowserFingerprint
    def validate_coherence(self, fp: BrowserFingerprint) -> tuple[bool, list[str]]
    def get_safe_defaults(self) -> BrowserFingerprint

# proxy_manager.py
class ProxyManager:
    async def init_provider(self, provider_config: dict) -> None
    async def get_next_session(self, match_id: str) -> ProxySession
    async def retire_session(self, session_id: str) -> None
    async def health_check(self) -> dict

# behavior.py
class BehaviorEmulator:
    async def click_with_delay(self, page: Page, selector: str) -> None
    async def scroll_naturally(self, page: Page, direction: str, amount: int) -> None
    async def add_micro_delay(self, min_ms: int, max_ms: int) -> None

# consent_handler.py
class ConsentHandler:
    async def detect_and_accept(self, page: Page) -> bool
    def register_pattern(self, pattern_name: str, detectors: list) -> None

# anti_detection.py
class AntiDetectionMasker:
    async def mask_webdriver_property(self, page: Page) -> None
    async def mask_playwright_indicators(self, page: Page) -> None
    async def remove_process_property(self, page: Page) -> None
```

### 3. Quick Start (`quickstart.md`)

Developer onboarding guide covering:
- Installation and Python version requirements
- Basic StealthConfig usage with production defaults
- Integration with Navigator (how to instantiate and use)
- Testing locally with mock proxy (for development without residential proxy)
- Configuration YAML structure and options
- Logging and debugging with structured JSON output
- Common troubleshooting (proxy failures, consent detection misses, fingerprint conflicts)
- Performance characteristics and optimization tips

---

## Phase 2: Implementation & Validation

*(This section describes work scope; implementation happens in next phase)*

### Implementation Sequence

1. **Foundation** (subsystem by subsystem)
   - types.py: Define ProxySession, BrowserFingerprint, StealthConfig, AntiDetectionEvent
   - config.py: Default configurations, realistic fingerprint distributions, provider configs

2. **Subsystem Development** (in parallel, each independently testable)
   - fingerprint.py: Fingerprint generation and validation
   - proxy_manager.py: Proxy rotation and session management
   - behavior.py: Timing and interaction emulation
   - consent_handler.py: Dialog detection and acceptance
   - anti_detection.py: Automation indicator masking

3. **Coordination & Integration**
   - events.py: Event logging and publishing
   - coordinator.py: StealthSystem main class orchestrating all subsystems
   - Integration tests with Navigator and Tab Controller

4. **Documentation**
   - Module README with API, usage examples, error handling
   - YAML configuration reference
   - Troubleshooting guide

### Validation Approach

Per constitution principle, validation is manual against real detection systems:
- Navigate to Flashscore with stealth enabled/disabled
- Verify 95% success rate (SC-001)
- Verify proxy rotation distributes across IPs (SC-002)
- Verify fingerprint coherence (SC-003)
- Verify consent handling (SC-004)
- Run browser automation detection tools and verify 0 detections (SC-005)
- Multi-page navigation within session (SC-006)
- Measure timing distributions (SC-007)
- Verify error handling clarity (SC-008)
- Benchmark initialization time (SC-009)
- Test IP rotation failure recovery (SC-010)
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
