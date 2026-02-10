# Tasks: Screenshot Capture with Organized File Structure

**Input**: Design documents from `/specs/010-screenshot-capture/`
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

- [x] T001 Create screenshots subdirectory in data/snapshots/ for PNG file storage
- [x] T002 Add PIL/Pillow import to examples/browser_lifecycle_example.py for image processing
- [x] T003 [P] Verify existing snapshot directory structure and permissions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Constitution-Compliant Foundation Tasks

- [x] T004 Setup screenshot file naming convention utilities (timestamp-based matching JSON)
- [x] T005 [P] Implement screenshot capture configuration utilities (mode, quality settings)
- [x] T006 [P] Configure graceful degradation error handling for screenshot capture failures
- [x] T007 [P] Setup structured logging for screenshot capture operations
- [x] T008 Create screenshot file path resolution utilities
- [x] T009 [P] Implement file size monitoring and validation for screenshots
- [x] T010 Configure PNG format handling and quality settings
- [x] T011 Setup screenshot file existence verification utilities

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Screenshot Capture with File Organization (Priority: P1) 🎯 MVP

**Goal**: Capture page screenshots during snapshot creation and store as separate PNG files with JSON references

**Independent Validation**: Run browser_lifecycle_example.py and verify both JSON snapshot and PNG screenshot files are created with correct naming and metadata

### Implementation for User Story 1

- [x] T012 [US1] Implement screenshot capture in capture_snapshot() method in examples/browser_lifecycle_example.py
- [x] T013 [US1] Add screenshot metadata collection (dimensions, file size, timestamp)
- [x] T014 [US1] Implement PNG file creation with timestamp-based naming convention
- [x] T015 [US1] Add screenshot field to snapshot JSON schema (version 1.2)
- [x] T016 [US1] Implement graceful degradation for screenshot capture failures
- [x] T017 [US1] Add structured logging for screenshot capture operations
- [x] T018 [US1] Implement file size validation and monitoring for screenshots
- [x] T019 [US1] Add PNG format handling and quality settings
- [x] T020 [US1] Update schema version to 1.2 in snapshot generation
- [x] T021 [US1] Test screenshot file creation and JSON reference functionality

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Screenshot Mode Selection (Priority: P2)

**Goal**: Support both fullpage and viewport screenshot modes with configurable settings

**Independent Validation**: Configure different screenshot modes and verify the resulting image dimensions match the expected capture type

### Implementation for User Story 2

- [x] T022 [P] [US2] Create screenshot mode configuration utilities in examples/browser_lifecycle_example.py
- [x] T023 [US2] Implement fullpage screenshot capture mode with Playwright API
- [x] T024 [US2] Implement viewport screenshot capture mode with Playwright API
- [x] T025 [US2] Add screenshot mode parameter to capture_snapshot() method signature
- [x] T026 [US2] Implement quality settings configuration for PNG compression
- [x] T027 [US2] Add capture_mode field to screenshot metadata in JSON
- [x] T028 [US2] Implement mode validation and error handling
- [x] T029 [US2] Test both fullpage and viewport screenshot modes
- [x] T030 [US2] Test screenshot quality settings and file size impact

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T031 [P] Update quickstart.md with actual implementation examples
- [x] T032 Code cleanup and refactoring in examples/browser_lifecycle_example.py
- [x] T033 Performance optimization for large screenshot file handling
- [x] T034 Add comprehensive error messages for troubleshooting
- [x] T035 Run manual validation of all user story scenarios
- [x] T036 Constitution compliance audit (verify all principles followed)
- [x] T037 Update documentation with new screenshot capture capabilities
- [x] T038 Test backward compatibility with existing snapshot consumers

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 screenshot capture foundation
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Screenshot capture utilities MUST be defined first (US1)
- Mode selection implementation before quality settings (US2)
- Error handling throughout all operations
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, User Story 1 and 2 can start in parallel (if team capacity allows)
- Utility functions within stories marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all screenshot capture utilities for User Story 1 together:
Task: "Implement screenshot capture in capture_snapshot() method"
Task: "Add screenshot metadata collection (dimensions, file size, timestamp)"
Task: "Implement PNG file creation with timestamp-based naming convention"
Task: "Add screenshot field to snapshot JSON schema (version 1.2)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test screenshot capture and file creation independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Screenshot capture)
   - Developer B: User Story 2 (Mode selection)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and verifiable
- **Implementation-first approach**: Direct implementation with manual validation
- **Deep modularity**: Screenshot capture as separate concern from metadata capture
- **Production resilience**: Graceful degradation on screenshot capture failures
- **Neutral naming convention**: Use structural, descriptive language only
- **Backward compatibility**: Existing snapshot consumers continue to work
- **File-based storage**: Screenshot files separate from JSON metadata
- **Schema versioning**: Update to 1.2 while maintaining 1.1 compatibility
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Constitution compliance mandatory for all implementation decisions
