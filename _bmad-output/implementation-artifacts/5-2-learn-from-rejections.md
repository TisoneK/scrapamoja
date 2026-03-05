# Story 5.2: Learn from Rejections

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **System**,
I want to learn from human rejections
So that similar selector strategies are avoided in the future.

## Acceptance Criteria

1. **Given** a human rejects a proposed selector
   **When** the rejection is recorded
   **Then** the weight of that selector strategy should decrease
   **And** the rejection reason should be analyzed to identify patterns to avoid

2. **Given** rejections accumulate over time
   **When** proposing new selectors
   **Then** strategies that have been rejected before should receive lower confidence scores

## Tasks / Subtasks

- [x] Task 1: Extend ConfidenceScorer with Rejection Learning (AC: #1)
  - [x] Subtask 1.1: Add rejection weight tracking per strategy type
  - [x] Subtask 1.2: Implement weight decrease for rejected selector strategies
  - [x] Subtask 1.3: Persist rejection data to database

- [x] Task 2: Integrate with Rejection Workflow (AC: #1, #2)
  - [x] Subtask 2.1: Connect rejection endpoint to learning system
  - [x] Subtask 2.2: Ensure record_negative_feedback() is fully implemented
  - [x] Subtask 2.3: Test weight propagation on rejection

- [x] Task 3: Analyze Rejection Patterns (AC: #1)
  - [x] Subtask 3.1: Parse rejection reasons for pattern extraction
  - [x] Subtask 3.2: Identify strategy-specific rejection patterns
  - [x] Subtask 3.3: Apply pattern-based weight adjustments

- [x] Task 4: Rejection Weight Persistence (AC: #2)
  - [x] Subtask 4.1: Store rejection data in weights table
  - [x] Subtask 4.2: Save learned rejection weights on each rejection
  - [x] Subtask 4.3: Load rejection weights on service initialization
  - [x] Subtask 4.4: Test rejection weight persistence across restarts

---

## Critical Architecture Requirements

### ⚠️ MANDATORY: Integration Requirements (DO NOT REINVENT)

Per Sprint Change Proposal (_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-03.md):

1. **MUST EXTEND existing `ConfidenceScorer`** from `src/selectors/adaptive/services/confidence_scorer.py`
   - DO NOT create a new scoring service
   - DO NOT duplicate the scoring logic
   - This story mirrors Story 5.1 but for NEGATIVE feedback

2. **Existing Systems to Extend:**
   | Need | Use This | Location |
   |------|----------|----------|
   | Confidence scoring | `ConfidenceScorer` | `src/selectors/adaptive/services/confidence_scorer.py` |
   | Confidence weights | `_historical_data` dict | Same as above |
   | Positive feedback | `record_positive_feedback()` | Same as above (Story 5.1 implemented this) |
   | Negative feedback | `record_negative_feedback()` | Same as above (TODOs exist - needs implementation) |

3. **Pattern for Extension:**
   ```python
   # CORRECT: Extend existing - Story 5.1 did this for positive feedback
   class LearningConfidenceScorer(ConfidenceScorer):
       def __init__(self):
           super().__init__()
           self._rejection_weights = {}  # Add rejection weights storage
   
       def record_negative_feedback(self, selector, strategy, reason=None):
           # Call parent method
           super().record_negative_feedback(selector, strategy, reason)
           # Add rejection learning-specific logic
   
   # WRONG: Create parallel system
   class NewRejectionService:  # DON'T DO THIS
       def calculate(self):
           # own implementation - DUPLICATES ConfidenceScorer
   ```

### Module Structure
Per architecture, all new code goes in:
- **Python Backend**: `src/selectors/adaptive/`
- **Frontend**: `ui/escalation/` (existing React app)

### API Requirements (from Architecture)
```
GET /weights - View learning weights (EXISTING endpoint)
PATCH /weights/{selector} - Adjust weights (EXISTING endpoint)
POST /failures/{id}/reject - Reject proposed selector (EXISTING endpoint - needs learning integration)
```

### Database Tables
- `weights` - Learning algorithm weights (per Sprint Change Proposal - MUST use)
- Should extend existing weights table from Story 5.1

### Technology Stack
- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Pydantic
- **Frontend**: React + TypeScript (existing)
- **Authentication**: API Keys (per architecture)

---

## Developer Guardrails

### DO NOT REINVENT
- ✅ Use existing `ConfidenceScorer` from `src/selectors/adaptive/services/confidence_scorer.py`
- ✅ Use existing `_historical_data` dictionary for weight storage
- ✅ Use existing weights table pattern from Epic 5
- ✅ Follow same pattern as Story 5.1 (learn-from-approvals) but for rejections
- ❌ DO NOT create new scoring logic
- ❌ DO NOT duplicate existing confidence calculation

### MUST USE
- FastAPI for all API endpoints (already implemented)
- SQLAlchemy 2.0 async patterns (already established)
- Pydantic for request/response validation
- React Query for server state management
- Tailwind CSS for styling

### Naming Conventions
- Python: `snake_case` for functions/variables
- TypeScript: `camelCase` variables, `PascalCase` components
- API Response: `{"data": {...}}` format per architecture
- Errors: RFC 7807 format `{"type": "...", "title": "...", "detail": "..."}`

### Critical Implementation Details

**Existing Code to Build Upon:**

```python
# From src/selectors/adaptive/services/confidence_scorer.py

# 1. Existing method - NEEDS FULL IMPLEMENTATION (currently has TODOs):
def record_negative_feedback(
    self,
    selector: str,
    strategy: StrategyType,
    rejection_reason: Optional[str] = None,
):
    """
    Record feedback from custom selector rejection for learning.
    """
    # TODO: Implement full rejection learning logic
    # This is where Story 5.2 picks up - mirror record_positive_feedback() logic
    # but for negative feedback

# 2. Existing historical data storage:
self._historical_data: Dict[str, float | Dict[str, Any]] = {}

# 3. Existing weights:
WEIGHTS = {
    'historical_stability': 0.4,
    'specificity': 0.35,
    'dom_similarity': 0.25,
}

# 4. Existing strategy defaults:
STRATEGY_DEFAULTS = {
    StrategyType.CSS: 0.7,
    StrategyType.XPATH: 0.65,
    StrategyType.TEXT_ANCHOR: 0.6,
    StrategyType.ATTRIBUTE_MATCH: 0.55,
    StrategyType.DOM_RELATIONSHIP: 0.5,
    StrategyType.ROLE_BASED: 0.5,
}
```

**From Story 5-1 Implementation (Learned Patterns to Follow):**
```python
# Story 5.1 implemented record_positive_feedback() - follow same pattern for negative:
def record_negative_feedback(
    self,
    selector: str,
    strategy: StrategyType,
    rejection_reason: Optional[str] = None,
):
    # 1. Record the exact selector + strategy in _historical_data
    # 2. Decrease the base confidence for that strategy type
    # 3. Apply slight decrease to related strategies (mirror the boost from approvals)
    # 4. Parse rejection_reason for pattern extraction if provided
    # 5. Persist weights to database
```

---

## Technical Implementation Notes

### Learning System Architecture (Mirrors Story 5.1)

The learning from rejections should work as follows:

1. **On Rejection Event:**
   - User rejects a selector in the escalation UI
   - `failure_service.reject_alternative()` is called (check if exists)
   - `record_negative_feedback()` is invoked
   - **Story 5.2**: Full implementation of `record_negative_feedback()`

2. **Weight Adjustment Logic (Mirror of approvals but negative):**
   ```
   For each rejection:
   1. Record the exact selector + strategy in _historical_data
   2. Decrease the base confidence for that strategy type
   3. Apply slight decrease (3-5%) to related strategies:
      - CSS → related to XPath (both structural)
      - TEXT_ANCHOR → related to DOM_RELATIONSHIP (both context-based)
   4. Parse rejection reason for pattern extraction:
      - "too specific" → decrease specificity weight
      - "too generic" → increase specificity requirement
      - "wrong element" → decrease confidence for that DOM path
   5. Persist rejection weights to database
   ```

3. **Rejection Weight Persistence:**
   - Save to `weights` table on each rejection
   - Load on `ConfidenceScorer` initialization
   - Use JSON or structured storage for rejection history

4. **Future Proposals:**
   - When proposing new selectors, look up rejection weights
   - Apply learned penalty to confidence calculation
   - Show "rejected X times" indicator

### Strategy Relationship Matrix (For Rejection - Inverse of Approval)

For the "similar selector strategies" penalty:

| Strategy | Related Strategies | Penalty Factor |
|----------|-------------------|----------------|
| CSS | XPath, ATTRIBUTE_MATCH | -3% |
| XPath | CSS, DOM_RELATIONSHIP | -3% |
| TEXT_ANCHOR | DOM_RELATIONSHIP, ROLE_BASED | -3% |
| ATTRIBUTE_MATCH | CSS, XPath | -3% |
| DOM_RELATIONSHIP | XPath, TEXT_ANCHOR | -3% |
| ROLE_BASED | TEXT_ANCHOR | -2% |

### Rejection Reason Patterns

Parse rejection reasons to extract learning:

| Reason Pattern | Learning Action |
|-----------------|-----------------|
| "too specific" | Decrease specificity weight, favor more general selectors |
| "too generic" | Increase specificity requirements |
| "wrong element" | Decrease confidence for that DOM path pattern |
| "fragile" | Decrease stability weight |
| "not stable" | Decrease historical stability weight |
| Custom reason | Store as text for manual review |

---

## Previous Story Intelligence

### From Story 5-1 Implementation
- **Approval learning implemented**: `record_positive_feedback()` is now fully implemented
- **Weight persistence exists**: Weights table with approval data
- **Strategy relationship matrix**: Boost factors for related strategies
- **Learning integration**: Already connected to approval workflow
- **Key Insight**: Story 5.2 should mirror 5.1's implementation but for negative feedback

### What Story 5.1 Did (Follow Same Pattern):
1. Extended `ConfidenceScorer` with `_approval_weights`
2. Implemented `record_positive_feedback()` method
3. Connected to approval endpoint
4. Created weight persistence
5. Applied strategy relationship boost

### Files to Modify
**Backend (Python):**
- `src/selectors/adaptive/services/confidence_scorer.py` - Implement `record_negative_feedback()` fully
- `src/selectors/adaptive/services/failure_service.py` - May need to ensure proper call to rejection learning system

**Database (if needed):**
- Extend `weights` table for rejection data (may already exist from Story 5.1)

**Tests:**
- `tests/selectors/adaptive/test_rejection_learning.py` - Add tests for rejection learning (create new)
- May extend existing test files

### Key Learnings from Story 5-1
- Mirror the positive feedback implementation for negative
- Same weight persistence pattern
- Same strategy relationship logic (but inverted)
- Do NOT create new services - extend what exists

---

## Web Research Notes

### Latest Technical Considerations

For implementing the rejection learning system, consider:

1. **Weight Bounds**: Ensure rejection weights don't push confidence below minimum (e.g., 0.1)
2. **Recovery**: Consider if/how rejected strategies can recover (e.g., after X approvals without rejection)
3. **Cold Start**: Handle case where no rejections have been recorded yet
4. **Rejection Fatigue**: Don't overly penalize - balance with approval history

### Potential Enhancements (Post-MVP)
- Weighted average of historical rejection confidence scores
- Per-sport/per-site rejection specialization
- Rejection reason clustering with NLP (future)
- Auto-recovery mechanism for wrongly rejected strategies

---

## References

- [Source: _bmad-output/planning-artifacts/epics.md#425-441] - Story 5.2 requirements with BDD acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#146-161] - Data Architecture and Tables
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-03.md] - **CRITICAL**: Sprint Change Proposal mandating ConfidenceScorer extension
- [Source: _bmad-output/planning-artifacts/architecture.md#218-257] - Code Organization and Module Structure

### Previous Epic Dependencies
- [Source: _bmad-output/implementation-artifacts/3-2-generate-confidence-scores.md] - Confidence scoring (Story 3.2)
- [Source: _bmad-output/implementation-artifacts/4-2-approve-or-reject-proposed-selectors.md] - Rejection workflow (Story 4.2)
- [Source: _bmad-output/implementation-artifacts/5-1-learn-from-approvals.md] - **MUST READ**: Learn from approvals (Story 5.1) - mirror this implementation

### Existing Implementation (Build Upon)
- [Source: src/selectors/adaptive/services/confidence_scorer.py#507-555] - Existing `record_negative_feedback()` stub with TODOs
- [Source: src/selectors/adaptive/services/confidence_scorer.py#404-427] - Existing `add_historical_data()` method
- [Source: src/selectors/adaptive/services/confidence_scorer.py] - Story 5.1's implementation of `record_positive_feedback()` - READ THIS for pattern
- [Source: src/selectors/adaptive/services/failure_service.py#344-386] - Rejection flow (check if calls learning system)

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

- All rejection learning tests pass (26 tests)
- 203 tests pass in the adaptive services module
- 2 pre-existing test failures in test_custom_selector.py (unrelated to this implementation)

### Completion Notes List

- ✅ Implemented full rejection learning system mirroring Story 5.1 (learn-from-approvals)
- ✅ Extended ConfidenceScorer with `_rejection_weights` dictionary for tracking
- ✅ Implemented `record_negative_feedback()` method with:
  - Rejection count tracking per strategy type
  - Penalty calculation (5% per rejection, capped at 25%)
  - Related strategy penalty propagation (3% per related strategy)
  - Rejection reason pattern parsing (too_specific, too_generic, wrong_element, fragile, not_stable, custom)
  - Minimum confidence floor (0.1) to prevent over-penalization
- ✅ Added database persistence for rejection weights
- ✅ Updated FailureService to integrate with rejection learning
- ✅ Updated historical stability lookup to apply rejection penalties
- ✅ Created comprehensive test suite (26 tests, all passing)

### File List

**Backend (Python) - Modify existing:**
- `src/selectors/adaptive/services/confidence_scorer.py` - Added rejection learning: `_rejection_weights`, `record_negative_feedback()`, `get_rejection_weights()`, `get_strategy_penalty()`, `load_rejection_weights()`, `export_rejection_weights()`, `_load_persisted_rejection_weights()`, `_persist_rejection_weights()`, `_parse_rejection_reason()`, updated `_get_historical_stability()`
- `src/selectors/adaptive/services/failure_service.py` - Updated `_record_negative_feedback()` to integrate with learning system, added `_parse_rejection_reason()`

**Database - New models:**
- `src/selectors/adaptive/db/models/weights.py` - Added `RejectionWeight` and `SelectorRejectionHistory` models
- `src/selectors/adaptive/db/models/__init__.py` - Added exports for new models

**Repository - New methods:**
- `src/selectors/adaptive/db/repositories/weight_repository.py` - Added: `upsert_rejection_weight()`, `get_all_rejection_weights()`, `get_rejection_weight_by_strategy()`, `load_rejection_weights_for_scorer()`, `save_rejection_history()`, `get_rejection_history()`

**Tests - New file:**
- `tests/unit/selectors/adaptive/services/test_rejection_learning.py` - 26 comprehensive tests for rejection learning

**Frontend (if needed):**
- May need to display rejection counts in UI (future Epic 5.3)
