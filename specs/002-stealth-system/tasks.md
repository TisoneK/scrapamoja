# Implementation Tasks: Stealth & Anti-Detection System

**Branch**: `002-stealth-system` | **Created**: 2026-01-27  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Overview

This document breaks down implementation into actionable tasks organized by user story and development phase. Tasks follow strict checklist format with IDs, parallelization markers, story labels, and file paths for direct implementation.

**Total Tasks**: 67  
**Setup & Foundational**: 8  
**User Story 1 (Bot Detection)**: 12  
**User Story 2 (Proxy Rotation)**: 13  
**User Story 3 (Behavior Emulation)**: 12  
**User Story 4 (Fingerprint Normalization)**: 10  
**User Story 5 (Consent Handling)**: 8  
**User Story 6 (Automation Masking)**: 4  

---

## Phase 1: Setup & Project Foundation

### Infrastructure Setup

- [x] T001 Create stealth package directory structure with `src/stealth/__init__.py`
- [x] T002 Create `src/stealth/models.py` with type definitions (dataclasses, enums, type hints)
- [x] T003 Create `src/stealth/config.py` with `StealthConfig` class and defaults
- [x] T004 Create `src/stealth/events.py` with `AntiDetectionEvent` logging framework
- [x] T005 Create module docstrings and README in `src/stealth/README.md`
- [x] T006 Create `src/stealth/coordinator.py` skeleton with `StealthSystem` class interface
- [x] T007 Create test fixtures directory `tests/stealth/fixtures/` with mock browser configs
- [x] T008 Create logging configuration in `src/config/stealth-logging.yaml`

---

## Phase 2: User Story 1 - Prevent Detection as Automated Bot (Priority: P1)

**Goal**: Mask all automation indicators so Playwright-driven scraper appears as legitimate user browser

**Independent Test Criteria**: Configure stealth system, navigate to Flashscore homepage, verify `navigator.webdriver` is undefined and HTTP headers contain no Playwright indicators

### Subsystem: Anti-Detection Masking

- [x] T009 [P] [US1] Implement `src/stealth/anti_detection.py` module structure with class `AntiDetectionMasker`
- [x] T010 [P] [US1] Implement `AntiDetectionMasker.mask_webdriver_property()` - remove navigator.webdriver via init_script
- [x] T011 [P] [US1] Implement `AntiDetectionMasker.mask_playwright_indicators()` - remove console method patches
- [x] T012 [P] [US1] Implement `AntiDetectionMasker.mask_process_property()` - remove process.version
- [x] T013 [P] [US1] Implement `AntiDetectionMasker.add_realistic_plugins()` - populate navigator.plugins
- [x] T014 [P] [US1] Implement `AntiDetectionMasker.apply_masks()` - orchestrate all masks via CDP
- [x] T015 [US1] Create test: Launch browser with anti-detection enabled, verify navigator.webdriver returns undefined
- [x] T016 [US1] Create test: Verify no Playwright console methods leaked to page context
- [x] T017 [US1] Create test: Verify navigator.plugins populated with realistic extension list
- [x] T018 [US1] Add error handling in anti-detection masker for CDP failures with graceful degradation
- [x] T019 [US1] Add structured logging of mask application in `AntiDetectionEvent` publisher
- [x] T020 [US1] Integrate anti-detection masker into `StealthSystem.initialize()` workflow

---

## Phase 3: User Story 2 - Rotate IP Addresses with Session Persistence (Priority: P1)

**Goal**: Distribute requests across residential IPs while maintaining session cookies within sticky sessions

**Independent Test Criteria**: Create proxy sessions for 3 different matches, verify each gets different residential IP, verify cookies persist within session

### Subsystem: Proxy Management

- [x] T021 [P] [US2] Implement `src/stealth/proxy_manager.py` module with class `ProxyManager`
- [x] T022 [P] [US2] Implement `ProxyProvider` abstract base class with `get_proxy_url()`, `mark_exhausted()`, `health_check()`
- [x] T023 [P] [US2] Implement `BrightDataProvider` concrete provider with sticky session formatting
- [x] T024 [P] [US2] Implement `OxyLabsProvider` concrete provider for fallback option
- [x] T025 [P] [US2] Implement `MockProxyProvider` for development/testing without real proxies
- [x] T026 [US2] Implement `ProxyManager.initialize()` - connect to provider and verify credentials
- [x] T027 [US2] Implement `ProxyManager.get_next_session()` - create `ProxySession` with residential IP
- [x] T028 [US2] Implement `ProxyManager.retire_session()` - mark IP for rotation and apply cooldown
- [x] T029 [US2] Implement session state persistence to `data/storage/proxy-sessions/{run_id}.json`
- [x] T030 [US2] Implement cookie accumulation within `ProxySession` across multiple requests
- [x] T031 [US2] Create test: Verify proxy session IP remains constant across 10 page navigations
- [x] T032 [US2] Create test: Verify cookies persist within session, cleared on session close
- [x] T033 [US2] Add health monitoring and fallback logic for blocked proxy IPs in `ProxyManager`
- [x] T034 [US2] Integrate proxy manager into `StealthSystem.initialize()` and session lifecycle methods

---

## Phase 4: User Story 3 - Emulate Human Interaction Patterns (Priority: P1)

**Goal**: Simulate realistic human timing and movement patterns to avoid behavioral detection

**Independent Test Criteria**: Execute click, scroll, and micro-delay operations, measure timing distributions, verify they match human patterns (100-500ms click hesitation, natural scroll variance)

### Subsystem: Behavior Emulation

- [x] T035 [P] [US3] Implement `src/stealth/behavior.py` module with class `BehaviorEmulator`
- [x] T036 [P] [US3] Implement click hesitation timing with normal distribution in `BehaviorEmulator.click_with_delay()`
- [x] T037 [P] [US3] Implement mouse movement with Bézier curve (ease-in-out) in `BehaviorEmulator.move_mouse_naturally()`
- [x] T038 [P] [US3] Implement scroll timing with variable speed and natural pauses in `BehaviorEmulator.scroll_naturally()`
- [x] T039 [P] [US3] Implement micro-delay between rapid actions in `BehaviorEmulator.add_micro_delay()`
- [x] T040 [P] [US3] Implement behavior intensity profiles (conservative/moderate/aggressive) with configurable timing ranges
- [x] T041 [US3] Create test: Verify click hesitation follows normal distribution (mean ~150ms, variance ~75ms)
- [x] T042 [US3] Create test: Verify mouse movement uses Bézier curve (not linear path)
- [x] T043 [US3] Create test: Verify scroll includes natural pauses matching human reading patterns
- [x] T044 [US3] Create test: Verify micro-delay ranges respect configured intensity level
- [x] T045 [US3] Add timing telemetry logging to `AntiDetectionEvent` for all behavior operations
- [x] T046 [US3] Integrate behavior emulator into `StealthSystem.emulate_click()`, `emulate_scroll()`, `add_micro_delay()` methods

---

## Phase 5: User Story 4 - Normalize Browser Fingerprint (Priority: P2)

**Goal**: Report realistic device characteristics that are internally consistent and statistically valid

**Independent Test Criteria**: Generate fingerprints, verify user-agent matches browser/platform, verify timezone/language are plausible, run through coherence validation (0 conflicts)

### Subsystem: Fingerprint Normalization

- [x] T047 [P] [US4] Implement `src/stealth/fingerprint.py` module with class `FingerprintNormalizer`
- [x] T048 [P] [US4] Implement fingerprint data loading from industry distributions (Chrome, Firefox, Safari versions)
- [x] T049 [P] [US4] Implement `FingerprintNormalizer.generate_fingerprint()` with coherent property combinations
- [x] T050 [P] [US4] Implement screen resolution selection from realistic modern display distribution
- [x] T051 [P] [US4] Implement timezone/language combination validation and pairing logic
- [x] T052 [P] [US4] Implement plugin list curation matching browser type (Chrome plugins ≠ Firefox plugins)
- [x] T053 [US4] Implement `FingerprintNormalizer.validate_coherence()` with 8+ coherence checks
- [x] T054 [US4] Implement `FingerprintNormalizer.get_safe_defaults()` for fallback profiles
- [x] T055 [US4] Create test: Generate 100 fingerprints, verify 0 coherence violations
- [x] T056 [US4] Create test: Verify Chrome fingerprints always report Chrome user-agent and Chrome plugins
- [x] T057 [US4] Add fingerprint caching per session (consistency across page loads)
- [x] T058 [US4] Integrate fingerprint normalizer into `StealthSystem.apply_fingerprint_to_browser()` method

---

## Phase 6: User Story 5 - Handle Cookie and Consent Flows (Priority: P2)

**Goal**: Automatically detect and accept GDPR/cookie consent dialogs without manual intervention

**Independent Test Criteria**: Navigate to 5 websites with consent dialogs, verify all dialogs detected and accepted, verify no consent dialogs on subsequent pages in same session

### Subsystem: Consent Handling

- [x] T059 [P] [US5] Implement `src/stealth/consent_handler.py` module with class `ConsentHandler`
- [x] T060 [P] [US5] Implement consent dialog detection with DOM pattern matching (modal + button structure)
- [x] T061 [P] [US5] Implement text-based consent detection heuristics for generic modals
- [x] T062 [P] [US5] Implement accept button finding with fallback strategies
- [x] T063 [US5] Implement `ConsentHandler.detect_dialog()` with support for cookie_banner, gdpr_modal, generic_modal patterns
- [x] T064 [US5] Implement `ConsentHandler.accept_consent()` with click and verification
- [x] T065 [US5] Create test: Detect and accept consent dialog on 5 different test websites
- [x] T066 [US5] Create test: Verify dialog is fully dismissed before continuing extraction
- [x] T067 [US5] Add timeout handling (5 second default) with graceful degradation if dialog not found
- [x] T068 [US5] Add structured logging of consent acceptance in `AntiDetectionEvent`
- [x] T069 [US5] Integrate consent handler into `StealthSystem.process_consent_dialog()` method
- [x] T070 [US5] Implement custom pattern registration for site-specific consent dialogs

---

## Phase 7: User Story 6 - Mask Automation Indicators (Priority: P2)

**Goal**: Remove all Playwright-specific traces from browser context

**Independent Test Criteria**: Run automation detection tools, verify 0 detections of Playwright framework indicators

### Integration with Anti-Detection

- [x] T071 [P] [US6] Create test: Run JavaScript automation detection probes, verify navigator.webdriver is undefined
- [x] T072 [P] [US6] Create test: Verify no Playwright-specific console methods accessible from page
- [x] T073 [US6] Create test: Verify process.version is undefined or returns legitimate version
- [x] T074 [US6] Add verification step in `StealthSystem.validate_stealth_measures()` to detect remaining indicators

---

## Phase 8: Integration & Coordination

### StealthSystem Coordinator

- [x] T075 [P] Implement `StealthSystem.__init__()` with subsystem initialization
- [x] T076 [P] Implement `StealthSystem.initialize(config)` - orchestrate all subsystems
- [x] T077 [P] Implement `StealthSystem.shutdown()` - graceful cleanup of resources
- [x] T078 [P] Implement `StealthSystem.apply_fingerprint_to_browser(context)` - apply fingerprint via CDP
- [x] T079 [P] Implement `StealthSystem.create_proxy_session(match_id)` - create sticky proxy session
- [x] T080 [P] Implement `StealthSystem.close_proxy_session(session_id)` - retire session
- [x] T081 [P] Implement `StealthSystem.emulate_click(page, selector, match_id)` - coordinated behavior
- [x] T082 [P] Implement `StealthSystem.emulate_scroll(page, direction, amount, match_id)` - coordinated behavior
- [x] T083 [P] Implement `StealthSystem.add_micro_delay(match_id)` - coordinated timing
- [x] T084 [P] Implement `StealthSystem.process_consent_dialog(page, match_id)` - consent workflow
- [x] T085 [P] Implement `StealthSystem.validate_stealth_measures(page, match_id)` - detection testing
- [x] T086 [P] Implement event publishing and logging coordination across all subsystems

### Configuration & YAML Support

- [x] T087 Create `config/stealth.yaml` template with production defaults
- [x] T088 Implement YAML config loading in `src/config/settings.py`
- [x] T089 Implement config validation (all required fields, valid enum values)
- [x] T090 Create configuration reference documentation

### Documentation

- [x] T091 Create module docstrings in all `src/stealth/*.py` files
- [x] T092 Create docstrings for all public methods and classes
- [x] T093 Create inline comments for complex algorithms (Bézier curves, coherence checks, pattern matching)
- [x] T094 Create usage examples in module README files

---

## Phase 9: Validation & Testing

### Manual Validation Against Flashscore

- [x] T095 Navigate Flashscore with stealth disabled, observe detection blocking
- [x] T096 Navigate Flashscore with stealth enabled, verify 95%+ success rate (SC-001)
- [x] T097 Scrape 50 consecutive matches, verify IP rotation distributes across 5+ IPs (SC-002)
- [x] T098 Generate 100 fingerprints, verify 0 coherence violations (SC-003)
- [x] T099 Navigate 5 websites with consent dialogs, verify 100% auto-acceptance (SC-004)
- [x] T100 Run browser automation detection tools, verify 0 Playwright detections (SC-005)
- [x] T101 Navigate 10 pages within single proxy session, verify cookies persist (SC-006)
- [x] T102 Measure timing distributions, verify they match human patterns (SC-007)
- [x] T103 Test error scenarios, verify all errors include actionable remediation (SC-008)
- [x] T104 Benchmark stealth initialization time, verify <2 seconds (SC-009)
- [x] T105 Test proxy IP rotation failure, verify fallback to next IP <1 retry (SC-010)

### Error Handling & Resilience

- [x] T106 Test graceful degradation: proxy failure → continue with next IP
- [x] T107 Test graceful degradation: consent timeout → continue extraction
- [x] T108 Test graceful degradation: fingerprint conflict → use safe defaults
- [x] T109 Test graceful degradation: anti-detection mask failure → log warning, continue

### Performance Validation

- [x] T110 Profile initialization time (target: <2 seconds)
- [x] T111 Profile per-click overhead (target: ~150-400ms from emulation)
- [x] T112 Profile memory usage (target: ~5-10MB)
- [x] T113 Profile CPU usage during timing delays (should be minimal)

---

## Implementation Strategy

### Recommended Execution Order

**Phase 1** (Day 1): Setup foundation - T001-T008
- Creates project structure and infrastructure
- Enables parallel work on subsystems

**Phase 2-3** (Days 2-3): Anti-detection + Proxy - T009-T034
- Two largest subsystems, can be developed in parallel (T009-T025 parallelizable)
- Anti-detection masks are prerequisites for credible testing

**Phase 4-5** (Days 4-5): Behavior + Fingerprint - T035-T058
- Can be developed in parallel (T035-T052 parallelizable)
- Moderate complexity, independent of other subsystems

**Phase 6-7** (Days 6): Consent + Masking verification - T059-T074
- Consent handling depends only on Playwright Page API
- Masking verification uses existing anti-detection subsystem

**Phase 8** (Days 7-8): Integration & coordination - T075-T094
- Tie all subsystems together through StealthSystem coordinator
- Create documentation and configuration

**Phase 9** (Days 9-10): Validation & testing - T095-T113
- Manual validation against real Flashscore website
- Performance profiling and optimization

### Parallelization Opportunities

Tasks marked `[P]` are parallelizable:

**Day 2-3 Parallel Tracks**:
- Track A: Anti-detection (T009-T020)
- Track B: Proxy manager (T021-T034)
- Track C: Type definitions (T001-T002, dependency for all)

**Day 4-5 Parallel Tracks**:
- Track A: Behavior emulation (T035-T046)
- Track B: Fingerprint normalization (T047-T058)

**Day 5-6 Parallel Tracks**:
- Track A: Consent handling (T059-T070)
- Track B: Manual tests for subsystems (T041-T057, T065-T066)

### Dependency Graph

```
T001-T008 (Setup)
    ↓
T009-T020 (Anti-detection) ──┐
T021-T034 (Proxy manager) ────┼─→ T075-T086 (Integration)
T035-T046 (Behavior) ─────────┼─→ T087-T094 (Config & Docs)
T047-T058 (Fingerprint) ──────┤    ↓
T059-T070 (Consent) ──────────┘    T095-T113 (Validation)
T071-T074 (Masking verify)
```

---

## Success Criteria

All tasks completed when:
1. ✅ All 113 tasks marked complete
2. ✅ All subsystems independently testable (manual tests pass)
3. ✅ StealthSystem coordinator fully integrated
4. ✅ All 10 success criteria (SC-001 through SC-010) validated against real Flashscore
5. ✅ All error scenarios tested and handled gracefully
6. ✅ All documentation complete and accurate
7. ✅ Zero breaking changes to existing Navigator API
