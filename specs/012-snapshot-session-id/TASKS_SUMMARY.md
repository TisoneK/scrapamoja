# 📋 Task Breakdown Complete: Snapshot Session ID Feature (#012)

**Date**: January 29, 2026  
**Status**: ✅ Complete and Committed  
**Branch**: `012-snapshot-session-id`

---

## 📊 Deliverables Summary

| Artifact | File | Status | Purpose |
|----------|------|--------|---------|
| **Specification** | [spec.md](spec.md) | ✅ Complete | Feature requirements & user stories |
| **Plan** | [plan.md](plan.md) | ✅ Complete | Technical context & architecture |
| **Tasks** | [tasks.md](tasks.md) | ✅ Complete | 50 actionable tasks across 9 phases |
| **Quality Check** | [checklists/requirements.md](checklists/requirements.md) | ✅ Complete | Specification validation |
| **Summary** | [PLAN_SUMMARY.md](PLAN_SUMMARY.md) | ✅ Complete | Planning overview |

---

## 🎯 Task Breakdown Overview

### Total Tasks: 50

**Organized in 9 Phases**:

| Phase | Name | Tasks | Duration | Parallelizable |
|-------|------|-------|----------|---|
| 1 | Setup & Discovery | T001-T007 | 1 hour | ✅ Yes (T001-T007) |
| 2 | Foundational Changes | T008-T012 | 1 hour | ✅ Yes (T008-T012) |
| 3 | **User Story 1** - Unique Snapshots | T013-T017 | 1 hour | ⚠️ Sequential |
| 4 | **User Story 2** - Screenshot Traceability | T018-T023 | 1 hour | ⚠️ Sequential |
| 5 | **User Story 3** - No False Warnings | T024-T028 | 0.5 hour | ⚠️ Sequential |
| 6 | Edge Cases & Error Handling | T029-T033 | 0.5 hour | ✅ Partially |
| 7 | Backward Compatibility | T034-T037 | 0.5 hour | ⚠️ Sequential |
| 8 | Verification & Testing | T038-T045 | 1 hour | ⚠️ Sequential |
| 9 | Documentation & Review | T046-T050 | 0.5 hour | ✅ Yes (T046-T050) |

---

## 🚀 Implementation Scope Options

### MVP (Minimum Viable Product) - ~2-3 hours
**Focus**: Core requirement delivered quickly

**Tasks to Complete**:
- Phase 1: Discovery (T001-T007)
- Phase 2: Foundational helpers (T008-T012)  
- Phase 3: US1 Implementation (T013-T017) ← Session ID in JSON
- Phase 4: US2 Implementation (T018-T023) ← Session ID in screenshots
- Phase 5: US3 Implementation (T024-T028) ← Remove false warnings
- Phase 8: Verification (T038-T045) ← Manual testing

**Delivers**: ✅ All 3 user stories + verification

**Recommended**: Start with MVP for quick validation

### Full Scope - ~3-5 hours total
**Additional Phases**:
- Phase 6: Edge cases (T029-T033) ← Special chars, missing dirs, concurrency
- Phase 7: Backward compatibility (T034-T037) ← Old snapshot support
- Phase 9: Documentation (T046-T050) ← Code review ready

**Delivers**: MVP + robustness + maintainability

---

## 📋 Phase Details

### Phase 1: Setup & Discovery (T001-T007)
**Goal**: Understand current implementation

- T001: Inspect snapshot capture in src/browser/snapshot.py
- T002: Locate all filename generation points
- T003: Verify session_id availability [P]
- T004: Review DOMSnapshot model [P]
- T005: Review screenshot metadata structure
- T006: Verify screenshots directory creation
- T007: Document collision risks

**Checkpoint**: Understanding complete

---

### Phase 2: Foundational Changes (T008-T012)
**Goal**: Create reusable helpers

- T008: Create filename generation helper [P]
- T009: Create screenshot path helper [P]
- T010: Add session_id sanitization
- T011: Update _capture_screenshot() signature
- T012: Update _save_snapshot() signature

**Checkpoint**: Helpers ready for implementation

---

### Phase 3: User Story 1 - Unique Snapshots (T013-T017)
**Goal**: Session ID in snapshot JSON filenames

**Format Change**:
- Old: `wikipedia_search_{timestamp}.json`
- New: `wikipedia_search_{session_id}_{timestamp}.json`

**Tasks**:
- T013: Update _save_snapshot() method [US1]
- T014: Pass session_id from capture_snapshot() [US1]
- T015: Extract session_id from browser context [US1]
- T016: Update DOMSnapshot.to_dict() [US1]
- T017: Verify filename format [US1]

**Test**: Run example twice → both JSON files exist with different session IDs

---

### Phase 4: User Story 2 - Screenshot Traceability (T018-T023)
**Goal**: Session ID in screenshots + JSON metadata

**Format Change**:
- Old: `data/snapshots/screenshots/wikipedia_search_{timestamp}.png`
- New: `data/snapshots/screenshots/wikipedia_search_{session_id}_{timestamp}.png`

**Metadata Update**:
- Old: `"screenshot_filepath": "screenshots/wikipedia_search_{timestamp}.png"`
- New: `"screenshot_filepath": "screenshots/wikipedia_search_{session_id}_{timestamp}.png"`

**Tasks**:
- T018: Update _capture_screenshot() [P] [US2]
- T019: Ensure screenshots/ directory exists [US2]
- T020: Update screenshot metadata [US2]
- T021: Update JSON screenshot_filepath field [US2]
- T022: Verify screenshot filename format [US2]
- T023: Add filepath verification [US2]

**Test**: JSON contains correct screenshot_filepath; file exists

---

### Phase 5: User Story 3 - No False Warnings (T024-T028)
**Goal**: Different sessions never trigger warnings

**Tasks**:
- T024: Review current warning logic [US3]
- T025: Update file checks to be session-aware [US3]
- T026: Remove or update collision detection [US3]
- T027: Add session_id logging [US3]
- T028: Verify no warnings for different session_ids [US3]

**Test**: Run twice rapidly → zero warnings in logs

---

### Phase 6: Edge Cases & Error Handling (T029-T033)
**Goal**: Robust error handling

**Cases**:
- Special characters in session_id
- Missing screenshots directory
- Unavailable session_id (fallback)
- Concurrent snapshot operations
- Timestamp precision

**Tasks**:
- T029: Sanitize session_id [P]
- T030: Auto-create screenshots dir
- T031: Handle missing session_id [P]
- T032: Test concurrent captures [P]
- T033: Verify timestamp format

---

### Phase 7: Backward Compatibility (T034-T037)
**Goal**: Old snapshots still work

**Tasks**:
- T034: Update load_snapshot() for old format [P]
- T035: Verify to_dict() includes all fields
- T036: Add migration notes
- T037: Test old snapshot loading

**Test**: Old snapshots without session_id can still be loaded

---

### Phase 8: Verification & Testing (T038-T045)
**Goal**: All success criteria met

**Test Protocol**:
```powershell
# Run 1
$env:TEST_MODE=1; python -m examples.browser_lifecycle_example

# Run 2 (immediately after Run 1)
$env:TEST_MODE=1; python -m examples.browser_lifecycle_example

# Verify
# - Both snapshot sets exist
# - Different session IDs in filenames
# - No "existing file" warnings
# - Screenshots saved with session IDs
# - JSON metadata references correct paths
```

**Tasks**:
- T038: First example run [P]
- T039: Second example run [P]
- T040: Verify dual snapshot sets [P]
- T041: Check for warnings [P]
- T042: Verify screenshot files [P]
- T043: Parse JSON metadata [P]
- T044: Test session_id extraction [P]
- T045: Verify all SC (SC-001 through SC-005) [P]

**Checkpoint**: Feature complete and verified

---

### Phase 9: Documentation & Review (T046-T050)
**Goal**: Code review ready

**Tasks**:
- T046: Update method docstrings
- T047: Add inline comments
- T048: Document DOMSnapshot changes
- T049: Add filename format reference
- T050: Create old vs new format guide

---

## 🎯 Success Criteria Mapping

| Success Criteria | Verification Task | Expected Result |
|------------------|-------------------|-----------------|
| SC-001: Two runs produce unique files | T040 | Both snapshot sets exist, zero conflicts |
| SC-002: JSON references correct paths | T043 | `screenshot_filepath` includes session_id |
| SC-003: No false warnings | T041 | Zero "existing file" warnings |
| SC-004: Session ID extractable | T044 | String parsing of filename works |
| SC-005: Consistent format | T022 + T017 | Both JSON and PNG use same pattern |

---

## 🔄 Parallel Execution Plan

### Can Execute in Parallel:
- **Discovery Phase**: All T001-T007 tasks (code inspection)
- **Helper Phase**: T008-T012 (independent helper functions)
- **Documentation Phase**: T046-T050 (independent docs)
- **Verification Phase**: Tasks 40-45 can be partially parallel (reading files vs running example)

### Must Execute Sequentially:
- Phase 3 → Phase 4 → Phase 5 (user stories build on each other)
- T038 → T039 (two runs must be sequential)
- Core implementation (must complete before verification)

---

## 📈 Estimated Effort

| Phase | MVP | Full Scope | Notes |
|-------|-----|-----------|-------|
| 1 | 1h | 1h | Discovery |
| 2 | 1h | 1h | Helpers |
| 3 | 1h | 1h | Core implementation |
| 4 | 1h | 1h | Core implementation |
| 5 | 0.5h | 0.5h | Core implementation |
| 6 | — | 0.5h | Extra: Edge cases |
| 7 | — | 0.5h | Extra: Backward compat |
| 8 | 1h | 1h | Testing & verification |
| 9 | — | 0.5h | Extra: Documentation |
| **Total** | **~2-3h** | **~3-5h** | |

---

## 🎓 Files Modified

| File | Impact | Phases |
|------|--------|--------|
| `src/browser/snapshot.py` | High - Core changes | 2-7 |
| `src/models/selector_models.py` | Low - Review only | 1 |
| `examples/browser_lifecycle_example.py` | None - Validation only | 1 |
| `data/snapshots/` | Low - Directory structure | 1,6 |

---

## ✅ Task Statuses

**All 50 tasks are**:
- ✅ Specifically scoped (not vague)
- ✅ Independently verifiable
- ✅ Marked with file paths and line numbers
- ✅ Organized by user story
- ✅ Sequenced for dependency order
- ✅ Mapped to success criteria
- ✅ Ready for implementation

---

## 🚀 Next Steps

1. **Start Phase 1**: Discovery tasks (T001-T007)
   - Inspect current code
   - Understand session_id availability
   - Plan helper functions

2. **Complete Phase 2**: Foundational helpers (T008-T012)
   - Create filename generation function
   - Create screenshot path function
   - Add sanitization logic

3. **Implement User Stories**: Phases 3-5 (T013-T028)
   - Session ID in snapshots
   - Session ID in screenshots
   - Remove false warnings

4. **Verify**: Phase 8 (T038-T045)
   - Run tests twice
   - Check all files and metadata
   - Verify all success criteria

5. **Document**: Phase 9 (T046-T050)
   - Add docstrings and comments
   - Prepare for code review

---

## 📚 Related Documentation

- **Specification**: [spec.md](spec.md) - Feature requirements
- **Plan**: [plan.md](plan.md) - Technical approach
- **Quality Check**: [checklists/requirements.md](checklists/requirements.md) - Spec validation
- **Overview**: [PLAN_SUMMARY.md](PLAN_SUMMARY.md) - Planning summary
