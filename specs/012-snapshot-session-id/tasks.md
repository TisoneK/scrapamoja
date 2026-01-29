# Implementation Tasks: Fix Snapshot Filenames to Use Session ID for Proper Uniqueness

**Feature**: 012-snapshot-session-id  
**Branch**: `012-snapshot-session-id`  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Created**: January 29, 2026  
**Total Tasks**: 16

---

## Phase 1: Setup & Discovery

**Goal**: Understand current snapshot implementation and session ID availability  
**Independent Test**: Code inspection confirms session_id is available in snapshot capture context  

### Setup Tasks

- [ ] T001 Inspect current snapshot capture implementation in [src/browser/snapshot.py](../../src/browser/snapshot.py#L80-L100)
- [ ] T002 Locate all snapshot filename generation points (search for `{page_id}_{` and `{page_name}_{timestamp}`)
- [ ] T003 [P] Verify session_id is available in browser lifecycle example at capture time
- [ ] T004 [P] Review DOMSnapshot class in [src/models/selector_models.py](../../src/models/selector_models.py#L268) for session_id field
- [ ] T005 Review screenshot metadata structure in [src/browser/snapshot.py](../../src/browser/snapshot.py#L200-L280)
- [ ] T006 Verify data/snapshots/screenshots/ directory is created properly
- [ ] T007 Document current filename format limitations and collision risk

---

## Phase 2: Foundational Changes (Blocking Prerequisites)

**Goal**: Create helper functions for session ID-aware filename generation  
**Independent Test**: Helper functions correctly format filenames with session ID and pass unit inspection  

### Foundational Implementation

- [ ] T008 [P] Create filename generation helper function in [src/browser/snapshot.py](../../src/browser/snapshot.py) that accepts `page_name`, `session_id`, `timestamp` parameters
- [ ] T009 [P] Create screenshot path helper function in [src/browser/snapshot.py](../../src/browser/snapshot.py) that returns `screenshots/{page_name}_{session_id}_{timestamp}.png`
- [ ] T010 Add sanitization for session_id if it contains special characters (alphanumeric + underscore only)
- [ ] T011 Update `_capture_screenshot()` method signature to accept `session_id` parameter
- [ ] T012 Update `_save_snapshot()` method signature to accept `session_id` parameter

---

## Phase 3: User Story 1 - Unique Snapshot Storage Per Session (P1)

**Goal**: Snapshot JSON filenames include session_id for uniqueness  
**Independent Test**: Running example twice with different session IDs produces two non-conflicting JSON files with session IDs in filenames  
**Test Criterion**: Both `wikipedia_search_{session_id_1}_{timestamp1}.json` and `wikipedia_search_{session_id_2}_{timestamp2}.json` exist after two runs  

### Implementation for User Story 1

- [ ] T013 [US1] Update `_save_snapshot()` method to use session_id in filename format at [src/browser/snapshot.py](../../src/browser/snapshot.py#L280-L295)
- [ ] T014 [US1] Modify `capture_snapshot()` method to pass session_id to `_save_snapshot()` at [src/browser/snapshot.py](../../src/browser/snapshot.py#L80-L100)
- [ ] T015 [US1] Extract session_id from browser context or page session data at [src/browser/snapshot.py](../../src/browser/snapshot.py#L80-L100)
- [ ] T016 [US1] Update snapshot.to_dict() to include session_id field for JSON serialization at [src/browser/snapshot.py](../../src/browser/snapshot.py#L50-L65)
- [ ] T017 [US1] Verify filename format: `{page_id}_{session_id}_{int(timestamp)}.json`

**Checkpoint**: User Story 1 complete and independently testable

---

## Phase 4: User Story 2 - Session-Traceable Screenshot Filenames (P1)

**Goal**: Screenshot PNG filenames include session_id and are referenced in JSON metadata  
**Independent Test**: Screenshot files are saved with session_id in filename; JSON metadata screenshot_filepath includes session_id  
**Test Criterion**: JSON contains `"screenshot_filepath": "screenshots/wikipedia_search_{session_id}_{timestamp}.png"` and file exists at that path  

### Implementation for User Story 2

- [ ] T018 [P] [US2] Update `_capture_screenshot()` to use session_id in filename at [src/browser/snapshot.py](../../src/browser/snapshot.py#L200-L230)
- [ ] T019 [US2] Ensure screenshots directory exists before saving at [src/browser/snapshot.py](../../src/browser/snapshot.py#L230)
- [ ] T020 [US2] Update screenshot metadata to include full filename with session_id at [src/browser/snapshot.py](../../src/browser/snapshot.py#L240-L260)
- [ ] T021 [US2] Update JSON metadata field `screenshot_filepath` to reference complete filename including session_id
- [ ] T022 [US2] Verify screenshot filename format: `{page_id}_{session_id}_{int(timestamp)}.png`
- [ ] T023 [US2] Add verification that screenshot_filepath in JSON matches actual saved file path

**Checkpoint**: User Story 2 complete and independently testable

---

## Phase 5: User Story 3 - No False "Existing File" Warnings (P1)

**Goal**: Eliminate false "existing file" warnings when different sessions capture at similar times  
**Independent Test**: Run example twice rapidly; verify no warnings about existing files appear in logs  
**Test Criterion**: Log output contains zero warnings matching pattern "existing.*file" or "File already exists" when session IDs are different  

### Implementation for User Story 3

- [ ] T024 [US3] Review current warning logic for file existence checks in [src/browser/snapshot.py](../../src/browser/snapshot.py)
- [ ] T025 [US3] Update file existence checks to only apply within same session (not across sessions)
- [ ] T026 [US3] Remove or update timestamp-based collision detection if present at [src/browser/snapshot.py](../../src/browser/snapshot.py)
- [ ] T027 [US3] Add logging to record session_id when snapshot is saved (for debugging)
- [ ] T028 [US3] Verify that different session_ids never trigger "existing file" warnings

**Checkpoint**: User Story 3 complete - no false warnings for different sessions

---

## Phase 6: Edge Cases & Error Handling

**Goal**: Handle edge cases identified in specification  
**Independent Test**: System handles special characters, missing directories, concurrent operations gracefully  

### Edge Case Implementation

- [ ] T029 [P] Handle session_id with special characters - sanitize to alphanumeric + underscore only
- [ ] T030 Ensure screenshots directory is created if missing before saving first screenshot
- [ ] T031 [P] Handle case where session_id is unavailable - use fallback (e.g., UUID or timestamp-based)
- [ ] T032 Test concurrent snapshot captures don't produce filename collisions
- [ ] T033 Verify timestamp format consistency: `YYYYMMDD_HHMMSS`

---

## Phase 7: Backward Compatibility & Migration

**Goal**: Ensure existing snapshots can still be loaded; new format doesn't break anything  
**Independent Test**: Old snapshots without session_id can still be loaded; JSON schema change is backward-compatible  

### Backward Compatibility Tasks

- [ ] T034 [P] Update `load_snapshot()` method to handle both old and new filename formats at [src/browser/snapshot.py](../../src/browser/snapshot.py#L305-L325)
- [ ] T035 Verify snapshot.to_dict() includes all required fields for JSON serialization
- [ ] T036 Add migration note in docstring if manual action needed for old snapshots
- [ ] T037 Test that old snapshot files (without session_id) can still be queried

---

## Phase 8: Verification & Testing

**Goal**: Verify all acceptance criteria are met through manual testing  
**Independent Test**: Run example twice with TEST_MODE=1; verify both snapshots exist with unique filenames and no warnings  

### Verification Tasks

- [ ] T038 [P] Run browser_lifecycle_example.py with TEST_MODE=1 first time
- [ ] T039 [P] Run browser_lifecycle_example.py with TEST_MODE=1 second time (immediately after first)
- [ ] T040 Verify data/snapshots/ contains both sets of snapshots with different session IDs
- [ ] T041 Check that no "existing file" warnings appear in logs from either run
- [ ] T042 Verify screenshot files exist in data/snapshots/screenshots/ with session IDs
- [ ] T043 Parse JSON metadata and confirm screenshot_filepath includes session_id
- [ ] T044 Verify session_id extraction from filenames works correctly (string parsing)
- [ ] T045 Check all SC (Success Criteria) are met: SC-001 through SC-005

---

## Phase 9: Documentation & Code Review

**Goal**: Document changes and prepare for code review  
**Independent Test**: Code is clean, documented, and ready for review  

### Documentation Tasks

- [ ] T046 Add docstring updates to modified methods explaining session_id parameter
- [ ] T047 Update code comments to explain new filename format with session_id
- [ ] T048 Document the session_id field in DOMSnapshot class if added
- [ ] T049 Add inline comments for filename generation logic
- [ ] T050 Create quick reference showing old vs new filename format

---

## Implementation Strategy

### MVP Scope (Phase 3-5)
Focus on core requirement: session_id in filenames for JSON and PNG

**Minimum Tasks to Complete Feature**:
1. T013-T017: Snapshot JSON filename with session_id (US1)
2. T018-T023: Screenshot filename with session_id (US2)  
3. T024-T028: Remove false warnings (US3)
4. T038-T045: Verification testing

**Estimated Effort**: 2-3 hours for core implementation

### Full Scope (All Phases)
Add comprehensive error handling, backward compatibility, documentation

**Additional Tasks**: T001-T012, T029-T037, T046-T050  
**Estimated Effort**: +1-2 hours for completeness

### Parallel Execution Opportunities

**Parallelizable Task Sets**:
- T001-T007: Discovery can happen in parallel
- T008-T012: Helper functions are independent
- T013, T018: Filename generation can be done in parallel
- T038-T039: Two example runs are sequential (intentional)
- T046-T050: Documentation tasks are independent

---

## Dependencies & Ordering

```
Phase 1 (Discovery)
    ↓
Phase 2 (Foundational: T008-T012)
    ↓
Phase 3 (US1) + Phase 4 (US2) [can be parallel]
    ↓
Phase 5 (US3)
    ↓
Phase 6 (Edge Cases)
    ↓
Phase 7 (Backward Compatibility)
    ↓
Phase 8 (Verification)
    ↓
Phase 9 (Documentation)
```

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|--------------|
| Filename Uniqueness | 100% unique for different session_ids | T040 |
| False Warnings | 0 warnings for different sessions | T041 |
| Backward Compatibility | Old snapshots still loadable | T037 |
| Test Coverage | All SC (SC-001 through SC-005) met | T045 |
| Code Quality | Clean, documented, ready for review | T049-T050 |

---

## Files Modified

| File | Change | Phases |
|------|--------|--------|
| [src/browser/snapshot.py](../../src/browser/snapshot.py) | Add session_id parameter; update filename generation; modify save/load methods | 2-7 |
| [src/models/selector_models.py](../../src/models/selector_models.py) | Add session_id field to DOMSnapshot if needed | 2 |
| [examples/browser_lifecycle_example.py](../../examples/browser_lifecycle_example.py) | Review to verify session_id is accessible | 1 |
| [data/snapshots/](../../data/snapshots/) | Directory structure - verify screenshots/ exists | 1,6 |

---

## Notes

- Session ID is already available in browser lifecycle context (verified in Phase 1 discovery)
- No new dependencies required - uses existing pathlib and datetime
- Changes are localized to snapshot module - minimal side effects
- Manual testing via example is sufficient (no automated tests required per constitution)
- All tasks are independently verifiable through code inspection or file system checks
