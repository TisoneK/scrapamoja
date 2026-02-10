# Feature Specification: Snapshot Timing and Telemetry Fixes

**Feature Branch**: `014-snapshot-timing-fix`  
**Created**: 2025-01-29  
**Status**: Draft  
**Input**: User description: "Feature: 012-selector-engine-integration - Critical Issues Requiring Immediate Fix

CRITICAL ISSUES (REAL PROBLEMS)

Issue 1: Snapshot JSON Timing Bug - HIGH SEVERITY

Problem: Snapshot JSON metadata is written AFTER replay attempts, causing offline HTML replay and integrity verification to fail.

Evidence:

Replay tries to load: data\snapshots\wikipedia_search_1769691064_1769691068.json
But "Snapshot saved to:" message appears AFTER replay attempt
This confirms execution order bug
Root Cause: capture_snapshot() -> replay_snapshot() // JSON doesn't exist yet -> verify_integrity() // JSON doesn't exist yet
-> snapshot_metadata_write() // TOO LATE

Required Fix: Move snapshot JSON persistence to happen synchronously INSIDE capture_snapshot(), before any replay/verification:

snapshot = await snapshot_manager.capture(page)

MUST happen here - persist JSON metadata immediately
snapshot_manager.persist(snapshot)

Only after this:
await replay(snapshot.path) await verify(snapshot.path)

Rule: If a feature consumes snapshot metadata, the metadata must exist before the feature runs.

Issue 2: Missing Telemetry Method - MEDIUM SEVERITY

Problem: 'BrowserLifecycleExample' object has no attribute 'display_telemetry_summary'

Evidence: Error occurs during execution, but later shows "Selector engine telemetry: All operations completed successfully"

Fix Options:

Option A (Cleaner): Remove the call entirely: # self.display_telemetry_summary()
Option B: Stub the method: def display_telemetry_summary(self): pass
Recommendation: Option A unless telemetry is part of public API.

NON-BLOCKING ISSUES

Issue 3: Playwright Timeout Warnings - LOW SEVERITY

Problem: Still seeing "Timeout 1500ms exceeded waiting for .mw-search-result-heading a"

Cause: Snapshot module runs search-page waits after navigation landed on article page

Optional Fix: Gate waits by page type: if "Special:Search" in page.url: await wait_for_search_results()

Issue 4: Windows Asyncio Pipe Exception - IGNORE

Problem: "ValueError: I/O operation on closed pipe" during cleanup

Cause: Python 3.14 + Windows Proactor + Playwright subprocess teardown

Action: Safe to ignore - never affects production correctness.

CURRENT STATUS

Component | Status Browser lifecycle | Complete Selector engine | Complete YAML selectors | Complete Snapshot capture | Complete Snapshot JSON timing | BROKEN Offline replay | Blocked by timing Integrity verification | Blocked by timing Telemetry summary | Stale call Windows pipe warning | Ignore

EXACT NEXT STEPS (MINIMAL & REQUIRED)

CRITICAL: Move snapshot JSON persistence earlier in capture_snapshot()
Impact: Immediately fixes offline HTML replay AND integrity verification
Result: System crosses from "demo working" to "framework-grade"
Remove display_telemetry_summary() call
(Optional): Scope snapshot waits to page context to eliminate timeout warnings
Priority: Step #1 is non-negotiable for framework-grade functionality."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Snapshot JSON Persistence Timing Fix (Priority: P1)

Developers can run the browser lifecycle example and have offline HTML replay and integrity verification work correctly, with snapshot JSON metadata available before replay attempts.

**Why this priority**: This is a critical framework-grade issue that breaks core functionality. Without this fix, the system cannot reliably demonstrate offline capabilities or data integrity verification.

**Independent Test**: Can be fully tested by running the browser lifecycle example and verifying that offline HTML replay and integrity verification complete successfully without file not found errors.

**Acceptance Scenarios**:

1. **Given** a browser lifecycle example is executed, **When** snapshot capture completes, **Then** the JSON metadata file exists before any replay attempts
2. **Given** offline HTML replay is initiated, **When** the replay process runs, **Then** it successfully loads the snapshot JSON without file not found errors
3. **Given** integrity verification is performed, **When** verification runs, **Then** it successfully accesses the snapshot JSON metadata

---

### User Story 2 - Telemetry Method Error Resolution (Priority: P2)

Developers can run the browser lifecycle example without encountering AttributeError for missing display_telemetry_summary method.

**Why this priority**: This prevents runtime errors and provides a cleaner execution experience, though it doesn't break core functionality.

**Independent Test**: Can be fully tested by running the browser lifecycle example and verifying no AttributeError occurs during execution.

**Acceptance Scenarios**:

1. **Given** the browser lifecycle example is executed, **When** the execution reaches the telemetry summary section, **Then** no AttributeError is raised
2. **Given** the example completes execution, **When** reviewing the output, **Then** appropriate telemetry information is displayed or gracefully omitted

---

### User Story 3 - Playwright Timeout Warning Reduction (Priority: P3)

Developers can run the browser lifecycle example with reduced or eliminated Playwright timeout warnings during snapshot capture.

**Why this priority**: This improves the developer experience by reducing noise in logs, though it doesn't affect functionality.

**Independent Test**: Can be fully tested by running the browser lifecycle example and observing reduced timeout warnings in the output.

**Acceptance Scenarios**:

1. **Given** the browser lifecycle example navigates to an article page, **When** snapshot capture runs, **Then** no search-result-specific timeout warnings occur
2. **Given** the browser lifecycle example navigates to a search results page, **When** snapshot capture runs, **Then** appropriate waits are only executed when relevant

---

### Edge Cases

- What happens when snapshot capture fails completely?
- How does system handle partial snapshot data during replay?
- What happens when JSON persistence fails but HTML/screenshot succeed?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST persist snapshot JSON metadata synchronously within the capture_snapshot() method before any replay or verification attempts
- **FR-002**: System MUST ensure snapshot JSON file exists on disk before offline HTML replay is initiated
- **FR-003**: System MUST ensure snapshot JSON file exists before integrity verification is initiated
- **FR-004**: System MUST resolve the missing display_telemetry_summary method error in BrowserLifecycleExample
- **FR-005**: System MUST eliminate or appropriately scope Playwright timeout warnings during snapshot capture
- **FR-006**: System MUST maintain backward compatibility with existing browser lifecycle functionality
- **FR-007**: System MUST preserve all existing snapshot capture capabilities (HTML, screenshots, metadata)

### Key Entities *(include if feature involves data)*

- **Snapshot Metadata**: JSON file containing snapshot information including file paths, timestamps, and integrity data
- **BrowserLifecycleExample**: Main example class demonstrating browser lifecycle and selector engine integration
- **DOMSnapshotManager**: Component responsible for capturing and persisting snapshot data
- **Offline Replay System**: Component responsible for replaying captured HTML content
- **Integrity Verification System**: Component responsible for verifying snapshot data integrity

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Offline HTML replay completes successfully 100% of the time when snapshot capture succeeds
- **SC-002**: Integrity verification completes successfully 100% of the time when snapshot capture succeeds
- **SC-003**: Browser lifecycle example executes without AttributeError exceptions
- **SC-004**: Playwright timeout warnings during snapshot capture are reduced by at least 90%
- **SC-005**: Total execution time of browser lifecycle example does not increase by more than 5%
- **SC-006**: All existing functionality (selector engine, YAML configs, browser lifecycle) continues to work without regression
- **SC-007**: Snapshot JSON metadata is available within 100ms of snapshot capture completion
