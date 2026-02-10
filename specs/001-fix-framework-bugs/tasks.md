---

description: "Task list for fixing critical framework bugs"
---

# Tasks: Fix Framework Bugs

**Input**: Design documents from `/specs/001-fix-framework-bugs/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Manual validation only - no automated tests included in implementation approach.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Verify existing project structure and identify files to be modified
- [ ] T002 Create backup of current state before making changes
- [ ] T003 [P] Review FRAMEWORK_BUGS.md to understand current error conditions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Constitution-Compliant Foundation Tasks

- [ ] T004 Review existing code structure in src/browser/ and src/storage/ modules
- [ ] T005 [P] Identify all import statements needed for bug fixes (uuid, asyncio, pathlib, typing)
- [ ] T006 [P] Verify current async/await patterns in resilience.py
- [ ] T007 [P] Review existing error handling patterns across affected modules
- [ ] T008 Document current session creation flow in BrowserManager
- [ ] T009 [P] Verify storage adapter interface requirements

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Fix Critical BrowserManager Bugs (Priority: P1) 🎯 MVP

**Goal**: Fix RetryConfig missing execute_with_retry method and BrowserSession session_id None handling

**Independent Validation**: Run `python -m examples.browser_lifecycle_example` and verify it initializes BrowserManager without AttributeError and creates sessions without TypeError

### Implementation for User Story 1

- [ ] T010 [US1] Implement execute_with_retry method in RetryConfig class in src/browser/resilience.py
- [ ] T011 [US1] Add proper imports (asyncio, Callable, Any) to src/browser/resilience.py
- [ ] T012 [US1] Fix BrowserSession.__post_init__ method to handle None session_id in src/browser/session.py
- [ ] T013 [US1] Add uuid import to src/browser/session.py for session ID generation
- [ ] T014 [US1] Test RetryConfig.execute_with_retry with successful operation
- [ ] T015 [US1] Test RetryConfig.execute_with_retry with retry scenarios
- [ ] T016 [US1] Test BrowserSession creation with None session_id
- [ ] T017 [US1] Test BrowserSession creation with explicit session_id
- [ ] T018 [US1] Verify BrowserManager initialization works without AttributeError
- [ ] T019 [US1] Verify session creation works without TypeError
- [ ] T020 [US1] Run browser lifecycle example to validate both fixes work together

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Fix Storage Adapter Integration (Priority: P2)

**Goal**: Implement missing list_files method in FileSystemStorageAdapter

**Independent Validation**: Verify BrowserManager initialization completes without warnings about missing list_files method

### Implementation for User Story 2

- [ ] T021 [US2] Implement list_files method in FileSystemStorageAdapter class in src/storage/adapter.py
- [ ] T022 [US2] Add proper imports (pathlib.Path, List) to src/storage/adapter.py
- [ ] T023 [US2] Test FileSystemStorageAdapter.list_files with default pattern
- [ ] T024 [US2] Test FileSystemStorageAdapter.list_files with specific patterns
- [ ] T025 [US2] Test FileSystemStorageAdapter.list_files with non-existent directory
- [ ] T026 [US2] Verify BrowserManager initialization no longer shows missing method warning
- [ ] T027 [US2] Test session persistence functionality if available

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Fix CircuitBreaker Async Issues (Priority: P3)

**Goal**: Ensure all CircuitBreaker.call() usages are properly awaited

**Independent Validation**: Monitor for RuntimeWarning about unawaited coroutines during resilience operations

### Implementation for User Story 3

- [ ] T028 [US3] Search for all CircuitBreaker.call() usage in codebase
- [ ] T029 [US3] Fix CircuitBreaker.call() usage in src/browser/resilience.py
- [ ] T030 [US3] Fix CircuitBreaker.call() usage in any other affected files
- [ ] T031 [US3] Test CircuitBreaker operations for proper async behavior
- [ ] T032 [US3] Verify no RuntimeWarning messages appear during execution
- [ ] T033 [US3] Test circuit breaker state transitions with proper awaiting

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T034 [P] Run complete browser lifecycle example to validate all fixes
- [ ] T035 [P] Verify all timing information displays correctly
- [ ] T036 [P] Check for any remaining RuntimeWarning messages
- [ ] T037 [P] Verify session cleanup completes without resource leaks
- [ ] T038 [P] Update any relevant documentation if needed
- [ ] T039 [P] Review error messages for descriptiveness and actionability
- [ ] T040 [P] Validate backward compatibility is maintained
- [ ] T041 [P] Constitution compliance audit (verify all principles followed)
- [ ] T042 [P] Performance validation (BrowserManager initialization under 5 seconds)

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

- Core bug fixes must be implemented first
- Individual component testing before integration testing
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch core fixes for User Story 1 together:
Task: "Implement execute_with_retry method in RetryConfig class in src/browser/resilience.py"
Task: "Fix BrowserSession.__post_init__ method to handle None session_id in src/browser/session.py"
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
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and verifiable
- **Bug fix approach**: Minimal changes to maintain backward compatibility
- **Defensive programming**: Handle edge cases gracefully
- **Proper async patterns**: Ensure all async operations are properly awaited
- **Error handling**: Maintain existing error handling patterns
- **Manual validation**: Use browser lifecycle example for testing
- **Constitution compliance**: Follow all constitutional principles
- **Neutral naming**: Use structural, descriptive language only
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: breaking changes, vague tasks, same file conflicts
- Constitution compliance mandatory for all implementation decisions
