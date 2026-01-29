---

description: "Task list for Fix Framework Issues feature implementation"
---

# Tasks: Fix Framework Issues

**Input**: Design documents from `/specs/002-framework-issues/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Manual validation through browser lifecycle example

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `examples/` at repository root
- Paths shown below assume single project structure from plan.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create test pages directory structure in examples/test_pages/
- [ ] T002 Verify existing project structure and identify files to be modified
- [ ] T003 Create backup of current state before making changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Foundation Tasks

- [ ] T004 Review existing storage adapter patterns in src/storage/adapter.py
- [ ] T005 Review existing browser session cleanup patterns in src/browser/session.py
- [ ] T006 Review existing browser lifecycle example structure in examples/browser_lifecycle_example.py
- [ ] T007 Verify current error handling patterns across affected modules

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Complete Storage Interface Implementation (Priority: P1) 🎯 MVP

**Goal**: Implement missing store() and delete() methods in FileSystemStorageAdapter to enable session persistence and cleanup

**Independent Validation**: Run browser lifecycle example and verify session persistence and cleanup complete without storage adapter errors

### Implementation for User Story 1

- [ ] T008 [US1] Implement store() method in FileSystemStorageAdapter class in src/storage/adapter.py
- [ ] T009 [US1] Implement delete() method in FileSystemStorageAdapter class in src/storage/adapter.py
- [ ] T010 [US1] Add proper error handling and structured logging to storage methods in src/storage/adapter.py
- [ ] T011 [US1] Test storage operations with various data types and error scenarios
- [ ] T012 [US1] Verify storage adapter follows existing adapter patterns in src/storage/adapter.py
- [ ] T013 [US1] Test session persistence functionality with browser lifecycle example
- [ ] T014 [US1] Test session cleanup functionality with browser lifecycle example

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Robust Navigation with Test Mode Support (Priority: P2)

**Goal**: Add TEST_MODE environment variable support with local HTML pages for reliable CI/CD testing

**Independent Validation**: Run browser lifecycle example in TEST_MODE and verify navigation completes successfully using local test pages

### Implementation for User Story 2

- [ ] T015 [US2] Create test pages directory and Google stub page in examples/test_pages/google_stub.html
- [ ] T016 [US2] Add environment variable detection to browser lifecycle example in examples/browser_lifecycle_example.py
- [ ] T017 [US2] Implement _get_navigation_url() method in examples/browser_lifecycle_example.py
- [ ] T018 [US2] Enhance navigate_to_google() method with retry/backoff logic in examples/browser_lifecycle_example.py
- [ ] T019 [US2] Add configurable navigation timeouts for test vs production modes in examples/browser_lifecycle_example.py
- [ ] T020 [US2] Test navigation functionality in normal mode with examples/browser_lifecycle_example.py
- [ ] T021 [US2] Test navigation functionality in TEST_MODE with examples/browser_lifecycle_example.py
- [ ] T022 [US2] Verify TEST_MODE works without external network access

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Clean Subprocess Shutdown on Windows (Priority: P3)

**Goal**: Enhance session cleanup to ensure subprocess handles are properly closed before asyncio loop shutdown

**Independent Validation**: Run browser lifecycle example and verify session cleanup completes without subprocess deallocator warnings on Windows

### Implementation for User Story 3

- [ ] T023 [US3] Add subprocess handle tracking to BrowserSession.__post_init__ in src/browser/session.py
- [ ] T024 [US3] Implement _cleanup_subprocess_handles() method in src/browser/session.py
- [ ] T025 [US3] Enhance close() method with subprocess cleanup in src/browser/session.py
- [ ] T026 [US3] Add Windows-specific closed pipe access guards in src/browser/session.py
- [ ] T027 [US3] Add structured logging for subprocess cleanup operations in src/browser/session.py
- [ ] T028 [US3] Test subprocess cleanup with single browser session in examples/browser_lifecycle_example.py
- [ ] T029 [US3] Test subprocess cleanup with multiple browser sessions in examples/browser_lifecycle_example.py
- [ ] T030 [US3] Verify no subprocess deallocator warnings appear on Windows

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T031 [P] Run complete browser lifecycle example to validate all fixes work together
- [ ] T032 [P] Verify all timing information displays correctly after fixes
- [ ] T033 [P] Check for any remaining RuntimeWarning messages during execution
- [ ] T034 [P] Verify session cleanup completes without resource leaks
- [ ] T035 [P] Update any relevant documentation if needed
- [ ] T036 [P] Review error messages for descriptiveness and actionability
- [ ] T037 [P] Validate backward compatibility is maintained
- [ ] T038 [P] Constitution compliance audit (verify all principles followed)
- [ ] T039 [P] Performance validation (BrowserManager initialization under 5 seconds)

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
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Should be independently testable from US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Should be independently testable from US1/US2

### Within Each User Story

- Storage interface methods must be implemented first (US1)
- Test page creation must precede navigation enhancements (US2)
- Subprocess tracking must precede cleanup enhancements (US3)
- Core implementation before integration testing
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Different user stories can be worked on in parallel by different team members
- Polish tasks can run in parallel once all stories are complete

---

## Parallel Example: User Story 1

```bash
# Launch storage interface implementation tasks together:
Task: "Implement store() method in FileSystemStorageAdapter class in src/storage/adapter.py"
Task: "Implement delete() method in FileSystemStorageAdapter class in src/storage/adapter.py"
Task: "Add proper error handling and structured logging to storage methods in src/storage/adapter.py"
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
   - Developer A: User Story 1 (Storage Interface)
   - Developer B: User Story 2 (Test Mode)
   - Developer C: User Story 3 (Subprocess Cleanup)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and verifiable
- **Implementation-first development**: Direct implementation with manual validation
- **Module lifecycle management**: Explicit phases, state ownership, clear contracts, contained failures
- **Production resilience**: Graceful failure handling with retry and recovery
- **Neutral naming convention**: Use structural, descriptive language only
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Constitution compliance mandatory for all implementation decisions
