# Tasks: Page HTML Capture and Storage in Snapshots

**Input**: Design documents from `/specs/009-page-html-capture/`
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

- [x] T001 Create html subdirectory in data/snapshots/ for HTML file storage
- [x] T002 Add hashlib import to examples/browser_lifecycle_example.py for content hashing
- [x] T003 [P] Verify existing snapshot directory structure and permissions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Constitution-Compliant Foundation Tasks

- [x] T004 Setup HTML file naming convention utilities (timestamp, session_id, hash_prefix)
- [x] T005 [P] Implement content hash generation function using SHA-256
- [x] T006 [P] Configure graceful degradation error handling for HTML capture failures
- [x] T007 [P] Setup structured logging for HTML capture operations
- [x] T008 Create HTML file path resolution utilities
- [x] T009 [P] Implement file size monitoring and validation
- [x] T010 Configure UTF-8 encoding handling for HTML content
- [x] T011 Setup HTML file existence verification utilities

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - HTML Content Capture (Priority: P1) 🎯 MVP

**Goal**: Capture complete page HTML content during snapshot creation and store as separate file with JSON reference

**Independent Validation**: Run browser_lifecycle_example.py and verify both JSON snapshot and HTML file are created with correct content and hash

### Implementation for User Story 1

- [x] T012 [US1] Implement HTML content capture in capture_snapshot() method in examples/browser_lifecycle_example.py
- [x] T013 [US1] Add content hash generation and storage in snapshot JSON
- [x] T014 [US1] Implement HTML file creation with timestamp-based naming convention
- [x] T015 [US1] Add html_file field to snapshot JSON schema (version 1.1)
- [x] T016 [US1] Implement graceful degradation for HTML capture failures
- [x] T017 [US1] Add structured logging for HTML capture operations
- [x] T018 [US1] Implement file size validation and monitoring
- [x] T019 [US1] Add UTF-8 encoding handling for HTML content
- [x] T020 [US1] Update schema version to 1.1 in snapshot generation
- [x] T021 [US1] Test HTML file creation and JSON reference functionality

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Offline HTML Replay (Priority: P2)

**Goal**: Load previously captured HTML content into browser for offline testing and verification

**Independent Validation**: Load captured HTML file directly in browser and verify page renders correctly without network access

### Implementation for User Story 2

- [x] T022 [P] [US2] Create HTML file loading utility functions in examples/browser_lifecycle_example.py
- [x] T023 [US2] Implement browser loading of captured HTML files via file:// protocol
- [x] T024 [US2] Add HTML file verification and validation functions
- [x] T025 [US2] Create offline testing helper functions
- [x] T026 [US2] Add HTML content integrity verification before loading
- [x] T027 [US2] Implement error handling for missing/corrupted HTML files
- [x] T028 [US2] Add structured logging for HTML replay operations
- [x] T029 [US2] Test offline HTML replay functionality

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Content Integrity Verification (Priority: P3)

**Goal**: Verify captured HTML content has not been corrupted and ensure data reliability

**Independent Validation**: Modify captured HTML file and verify hash mismatch is detected and reported

### Implementation for User Story 3

- [x] T030 [P] [US3] Create content hash verification utility functions
- [x] T031 [US3] Implement HTML file integrity checking functions
- [x] T032 [US3] Add corruption detection and reporting mechanisms
- [x] T033 [US3] Create hash recalculation and comparison utilities
- [x] T034 [US3] Implement integrity verification for existing snapshots
- [x] T035 [US3] Add structured logging for integrity verification operations
- [x] T036 [US3] Test content integrity verification functionality

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T037 [P] Update quickstart.md with actual implementation examples
- [x] T038 Code cleanup and refactoring in examples/browser_lifecycle_example.py
- [x] T039 Performance optimization for large HTML file handling
- [x] T040 Add comprehensive error messages for troubleshooting
- [x] T041 Run manual validation of all user story scenarios
- [x] T042 Constitution compliance audit (verify all principles followed)
- [x] T043 Update documentation with new HTML capture capabilities
- [x] T044 Test backward compatibility with existing snapshot consumers

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
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 HTML file structure
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Depends on US1 hash storage

### Within Each User Story

- HTML content capture MUST be implemented first (US1)
- Hash generation and storage before integrity verification (US3)
- File creation before replay functionality (US2)
- Error handling throughout all operations
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, User Story 1 and 2 can start in parallel
- Utility functions within stories marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all HTML capture utilities for User Story 1 together:
Task: "Implement HTML content capture in capture_snapshot() method"
Task: "Add content hash generation and storage in snapshot JSON"
Task: "Implement HTML file creation with timestamp-based naming convention"
Task: "Add html_file field to snapshot JSON schema (version 1.1)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test HTML capture and file creation independently
5. Demo HTML file capture functionality

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Demo HTML capture (MVP!)
3. Add User Story 2 → Test independently → Demo offline replay
4. Add User Story 3 → Test independently → Demo integrity verification
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (HTML capture)
   - Developer B: User Story 2 (Offline replay)
   - Developer C: User Story 3 (Integrity verification)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and verifiable
- **Implementation-first approach**: Direct implementation with manual validation
- **Deep modularity**: HTML capture as separate concern from metadata capture
- **Production resilience**: Graceful degradation on HTML capture failures
- **Neutral naming convention**: Use structural, descriptive language only
- **Backward compatibility**: Existing snapshot consumers continue to work
- **File-based storage**: HTML files separate from JSON metadata
- **Schema versioning**: Update to 1.1 while maintaining 1.0 compatibility
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Constitution compliance mandatory for all implementation decisions
