---

description: "Task list for core module refactoring fix implementation"
---

# Tasks: Core Module Refactoring Fix

**Input**: Design documents from `/specs/011-fix-snapshot-refactor/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Manual validation only - no automated tests included in implementation approach.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Verify current project structure and dependencies in src/browser/snapshot.py
- [x] T002 Confirm all required imports are present (datetime, hashlib, pathlib, structlog)
- [x] T003 [P] Backup current snapshot.py file before making changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Constitution-Compliant Foundation Tasks

- [x] T004 Analyze current variable scope issues in capture_snapshot() method
- [x] T005 [P] Identify all undefined variable references in the module
- [x] T006 [P] Document current variable naming patterns and consistency requirements
- [x] T007 [P] Verify browser session integration points are working correctly
- [x] T008 Confirm file system operations and JSON serialization are functional
- [x] T009 Validate error handling and structured logging are properly configured

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Variable Reference Resolution (Priority: P1) 🎯 MVP

**Goal**: Fix undefined variable references in the core snapshot module so it can be imported and used without NameError exceptions.

**Independent Validation**: Import the snapshot module and call capture_snapshot() method, verifying no NameError or undefined variable exceptions occur.

### Implementation for User Story 1

- [x] T010 [US1] Fix undefined screenshot_path variable on line 149 in src/browser/snapshot.py
- [x] T011 [US1] Verify variable scope is properly defined for all metadata operations in src/browser/snapshot.py
- [x] T012 [US1] Test module import without NameError exceptions
- [x] T013 [US1] Validate capture_snapshot() method executes without undefined variable errors
- [x] T014 [US1] Confirm screenshot metadata processing completes without variable access errors
- [x] T015 [US1] Test timestamp operations work correctly with proper datetime object handling
- [x] T016 [US1] Verify logging statement works correctly with fixed variable reference
- [x] T017 [US1] Validate graceful handling when screenshot_metadata is None or missing

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Import Statement Completion (Priority: P1)

**Goal**: Ensure all required import statements are present so the module can function without ImportError exceptions.

**Independent Validation**: Import the module and verify all required modules (datetime, hashlib, pathlib) are available without import errors.

### Implementation for User Story 2

- [x] T018 [US2] Verify datetime and timezone imports are properly structured in src/browser/snapshot.py
- [x] T019 [US2] Confirm hashlib import is available for content hashing operations in src/browser/snapshot.py
- [x] T020 [US2] Validate pathlib import is present for file system operations in src/browser/snapshot.py
- [x] T021 [US2] Check structlog import is properly configured for structured logging in src/browser/snapshot.py
- [x] T022 [US2] Test module import without ImportError exceptions
- [x] T023 [US2] Verify all datetime operations work correctly with timezone-aware objects
- [x] T024 [US2] Confirm content hashing functions are available without import errors
- [x] T025 [US2] Validate file path operations work correctly with pathlib

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Variable Naming Consistency (Priority: P2)

**Goal**: Ensure consistent variable naming throughout the codebase for readability and maintainability.

**Independent Validation**: Review all variable references in the module and ensure consistent naming patterns are used throughout.

### Implementation for User Story 3

- [x] T026 [US3] Audit all screenshot_path references for consistent naming in src/browser/snapshot.py
- [x] T027 [US3] Verify screenshot_metadata access patterns are consistent throughout src/browser/snapshot.py
- [x] T028 [US3] Check timestamp variable handling follows consistent datetime object patterns in src/browser/snapshot.py
- [x] T029 [US3] Validate metadata field access uses the same pattern throughout src/browser/snapshot.py
- [x] T030 [US3] Ensure variable names follow neutral naming convention (structural, descriptive only)
- [x] T031 [US3] Document any remaining naming inconsistencies for future reference
- [x] T032 [US3] Verify all variable scopes are properly contained within method boundaries

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T033 [P] Test example code using refactored core module runs without blocking errors
- [x] T034 Verify backward compatibility with existing snapshot functionality
- [x] T035 Validate JSON schema compatibility is maintained (version 1.2)
- [x] T036 Test integration with browser lifecycle management system
- [x] T037 Run comprehensive validation of all snapshot capture methods
- [x] T038 Verify structured logging works correctly with correlation IDs
- [x] T039 Test error handling and graceful failure scenarios
- [x] T040 Constitution compliance audit (verify all principles followed)

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
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Should be independently testable

### Within Each User Story

- Variable reference fixes must be completed first (User Story 1)
- Import verification before functionality testing (User Story 2)
- Naming consistency audit after core fixes (User Story 3)
- Each story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, User Story 1 and User Story 2 can start in parallel (both P1)
- User Story 3 can proceed independently after P1 stories are complete

---

## Parallel Example: User Story 1

```bash
# Launch core variable reference fixes for User Story 1 together:
Task: "Fix undefined screenshot_path variable on line 149 in src/browser/snapshot.py"
Task: "Verify variable scope is properly defined for all metadata operations in src/browser/snapshot.py"
Task: "Test module import without NameError exceptions"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Variable Reference Resolution)
   - Developer B: User Story 2 (Import Statement Completion)
3. Stories complete and integrate independently
4. Developer C: User Story 3 (Variable Naming Consistency) after P1 stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and verifiable
- **Implementation-first development**: Direct fix with manual validation
- **Production resilience**: Graceful failure handling maintained
- **Neutral naming convention**: Use structural, descriptive language only
- **Minimal changes**: Single line fix for critical issue, no breaking changes
- **Backward compatibility**: Maintain existing API interfaces
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Constitution compliance mandatory for all implementation decisions
