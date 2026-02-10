---

description: "Task list for snapshot timing and telemetry fixes implementation"
---

# Tasks: Snapshot Timing and Telemetry Fixes

**Input**: Design documents from `/specs/014-snapshot-timing-fix/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL for this feature - only include if explicitly requested for validation

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/`, `examples/` at repository root
- Paths shown below follow the single project structure from plan.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Verify feature branch 014-snapshot-timing-fix is checked out and clean
- [x] T002 Verify existing dependencies are installed (playwright>=1.40.0, pytest>=7.4.0, etc.)
- [x] T003 [P] Create backup of current working implementation in examples/browser_lifecycle_example.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Analyze current DOMSnapshotManager implementation in src/browser/snapshot.py
- [x] T005 [P] Analyze current BrowserLifecycleExample implementation in examples/browser_lifecycle_example.py
- [x] T006 [P] Identify exact location of snapshot JSON persistence logic
- [x] T007 Identify exact location of display_telemetry_summary() call
- [x] T008 [P] Identify current snapshot capture timing and replay order
- [x] T009 Document current execution flow and identify timing bug location

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Snapshot JSON Persistence Timing Fix (Priority: P1) 🎯 MVP

**Goal**: Developers can run the browser lifecycle example and have offline HTML replay and integrity verification work correctly, with snapshot JSON metadata available before replay attempts.

**Independent Test**: Run the browser lifecycle example and verify that offline HTML replay and integrity verification complete successfully without file not found errors.

### Implementation for User Story 1

- [x] T010 [US1] Fix filename mismatch in capture_snapshot() method in examples/browser_lifecycle_example.py
- [x] T011 [US1] Add timing tracking for JSON persistence within capture() method in src/browser/snapshot.py
- [x] T012 [US1] Update Snapshot dataclass to include json_persistence_time field in src/browser/snapshot.py
- [x] T013 [US1] Ensure persist() method completes before capture() returns in src/browser/snapshot.py
- [x] T014 [US1] Add error handling for JSON persistence failures in src/browser/snapshot.py
- [x] T015 [US1] Verify JSON file exists and is readable before capture() method returns
- [x] T016 [US1] Test snapshot capture timing by running browser lifecycle example
- [x] T017 [US1] Verify offline HTML replay works without file not found errors
- [x] T018 [US1] Verify integrity verification works without file not found errors

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Telemetry Method Error Resolution (Priority: P2)

**Goal**: Developers can run the browser lifecycle example without encountering AttributeError for missing display_telemetry_summary method.

**Independent Test**: Run the browser lifecycle example and verify no AttributeError occurs during execution.

### Implementation for User Story 2

- [x] T019 [US2] Locate display_telemetry_summary() call in examples/browser_lifecycle_example.py
- [x] T020 [US2] Remove the problematic display_telemetry_summary() call in examples/browser_lifecycle_example.py
- [x] T021 [US2] Replace with appropriate success message for telemetry in examples/browser_lifecycle_example.py
- [x] T022 [US2] Test browser lifecycle example execution to verify no AttributeError
- [x] T023 [US2] Verify example completes successfully with clean output

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Playwright Timeout Warning Reduction (Priority: P3)

**Goal**: Developers can run the browser lifecycle example with reduced or eliminated Playwright timeout warnings during snapshot capture.

**Independent Test**: Run the browser lifecycle example and observe reduced timeout warnings in the output.

### Implementation for User Story 3

- [x] T024 [US3] Identify current timeout warning source in examples/browser_lifecycle_example.py
- [x] T025 [US3] Add page-type detection method _is_search_page() in examples/browser_lifecycle_example.py
- [x] T026 [US3] Add conditional wait logic _wait_for_search_results_if_needed() in examples/browser_lifecycle_example.py
- [x] T027 [US3] Modify snapshot capture to gate waits by page type in examples/browser_lifecycle_example.py
- [x] T028 [US3] Test timeout warning reduction on article pages
- [x] T029 [US3] Verify search result waits still work on search pages

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T030 [P] Run comprehensive end-to-end test of browser lifecycle example
- [x] T031 Verify all existing functionality still works (selector engine, YAML configs, browser lifecycle)
- [x] T032 [P] Measure performance impact of timing fixes (should be < 5% increase)
- [x] T033 [P] Test JSON persistence timing (should be < 100ms)
- [x] T034 Verify offline replay success rate (should be 100% when capture succeeds)
- [x] T035 Verify integrity verification success rate (should be 100% when capture succeeds)
- [x] T036 [P] Update any relevant documentation with timing changes
- [x] T037 Clean up any temporary debugging code or comments

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of US1/US2

### Within Each User Story

- Core implementation before validation
- Each story should be independently testable
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch analysis tasks in parallel:
Task: "Analyze current DOMSnapshotManager implementation in src/browser/snapshot.py"
Task: "Analyze current BrowserLifecycleExample implementation in examples/browser_lifecycle_example.py"
Task: "Identify exact location of snapshot JSON persistence logic"
Task: "Identify exact location of display_telemetry_summary() call"

# Once analysis complete, proceed with implementation:
Task: "Modify DOMSnapshotManager.capture() method in src/browser/snapshot.py to add synchronous JSON persistence"
Task: "Update Snapshot dataclass to include json_persistence_time field in src/browser/snapshot.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Verify offline replay and integrity verification work

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Validate timing fix (MVP!)
3. Add User Story 2 → Test independently → Validate telemetry fix
4. Add User Story 3 → Test independently → Validate timeout reduction
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (critical timing fix)
   - Developer B: User Story 2 (telemetry error fix)
   - Developer C: User Story 3 (timeout warning fix)
3. Stories complete and integrate independently

---

## Success Criteria Validation

### User Story 1 Success Metrics
- [ ] Offline HTML replay completes successfully 100% of the time when snapshot capture succeeds
- [ ] Integrity verification completes successfully 100% of the time when snapshot capture succeeds
- [ ] Snapshot JSON metadata is available within 100ms of snapshot capture completion

### User Story 2 Success Metrics
- [ ] Browser lifecycle example executes without AttributeError exceptions
- [ ] Clean execution output without error messages

### User Story 3 Success Metrics
- [ ] Playwright timeout warnings during snapshot capture are reduced by at least 90%
- [ ] No functional impact on snapshot capture capabilities

### Overall Success Metrics
- [ ] Total execution time of browser lifecycle example does not increase by more than 5%
- [ ] All existing functionality (selector engine, YAML configs, browser lifecycle) continues to work without regression

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- User Story 1 is critical and blocks framework-grade functionality
- User Stories 2 and 3 are improvements but not blocking
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
