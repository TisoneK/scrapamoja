# Story 5.1: Learn from Approvals

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **System**,
I want to learn from human approvals
So that future selector proposals improve in accuracy.

## Acceptance Criteria

1. **Given** a human approves a proposed selector
   **When** the approval is recorded
   **Then** the weight of the selector strategy should increase
   **And** similar selector strategies should get a slight weight boost

2. **Given** approvals accumulate over time
   **When** proposing new selectors
   **Then** strategies that have been approved before should receive higher confidence scores

## Tasks / Subtasks

- [x] Task 1: Extend ConfidenceScorer with Approval Learning (AC: #1)
  - [x] Subtask 1.1: Add approval weight tracking per strategy type
  - [x] Subtask 1.2: Implement weight boost for similar selector strategies
  - [x] Subtask 1.3: Persist learned weights to database

- [x] Task 2: Integrate with Approval Workflow (AC: #1, #2)
  - [x] Subtask 2.1: Connect approval endpoint to learning system
  - [x] Subtask 2.2: Ensure _record_positive_feedback() is fully implemented
  - [x] Subtask 2.3: Test weight propagation on approval

- [x] Task 3: Implement Similar Strategy Boost (AC: #1)
  - [x] Subtask 3.1: Identify similar strategies (CSS→XPath, etc.)
  - [x] Subtask 3.2: Apply slight boost to related strategies
  - [x] Subtask 3.3: Document strategy relationship matrix

- [x] Task 4: Weight Persistence (AC: #2)
  - [x] Subtask 4.1: Create or use weights table
  - [x] Subtask 4.2: Save learned weights on each approval
  - [x] Subtask 4.3: Load weights on service initialization
  - [x] Subtask 4.4: Test weight persistence across restarts

---

## Critical Architecture Requirements

### ⚠️ MANDATORY: Integration Requirements (DO NOT REINVENT)

Per Sprint Change Proposal (_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-03.md):

1. **MUST EXTEND existing `ConfidenceScorer`** from `src/selectors/adaptive/services/confidence_scorer.py`
   - DO NOT create a new scoring service
   - DO NOT duplicate the scoring logic

2. **Existing Systems to Extend:**
   | Need | Use This | Location |
   |------|----------|----------|
   | Confidence scoring | `ConfidenceScorer` | `src/selectors/adaptive/services/confidence_scorer.py` |
   | Confidence weights | `_historical_data` dict | Same as above |
   | Positive feedback | `record_positive_feedback()` | Same as above (TODOs exist) |

3. **Pattern for Extension:**
   ```python
   # CORRECT: Extend existing
   class LearningConfidenceScorer(ConfidenceScorer):
       def __init__(self):
           super().__init__()
           self._approval_weights = {}  # Add new weights storage
       
       def record_positive_feedback(self, selector, strategy):
           # Call parent method
           super().record_positive_feedback(selector, strategy)
           # Add learning-specific logic
   
   # WRONG: Create parallel system
   class NewScoringService:  # DON'T DO THIS
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
```

### Database Tables
- `weights` - Learning algorithm weights (per Sprint Change Proposal - MUST use)

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
def record_positive_feedback(
    self,
    selector: str,
    strategy: StrategyType,
    approved: bool,
    confidence_at_approval: Optional[float] = None,
):
    """
    Record feedback from custom selector approval/rejection for learning.
    """
    # TODO: Implement full approval learning logic
    # This is where Story 5.1 picks up
    
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

**From Story 4-2 Integration:**
```python
# failure_service.py calls this on approval:
self._record_positive_feedback(
    selector=selector,
    strategy=strategy,
)
# But this method has TODOs - needs full implementation
```

---

## Technical Implementation Notes

### Learning System Architecture

The learning from approvals should work as follows:

1. **On Approval Event:**
   - User approves a selector in the escalation UI
   - `failure_service.approve_alternative()` is called
   - `_record_positive_feedback()` is invoked
   - **Story 5.1**: Full implementation of `_record_positive_feedback()`

2. **Weight Adjustment Logic:**
   ```
   For each approval:
   1. Record the exact selector + strategy in _historical_data
   2. Boost the base confidence for that strategy type
   3. Apply slight boost (5-10%) to related strategies:
      - CSS → related to XPath (both structural)
      - TEXT_ANCHOR → related to DOM_RELATIONSHIP (both context-based)
   4. Persist weights to database
   ```

3. **Weight Persistence:**
   - Save to `weights` table on each approval
   - Load on `ConfidenceScorer` initialization
   - Use JSON or structured storage for weight history

4. **Future Proposals:**
   - When proposing new selectors, look up learned weights
   - Apply learned boost to confidence calculation
   - Show "learned from X approvals" indicator

### Strategy Relationship Matrix

For the "similar selector strategies" boost:

| Strategy | Related Strategies | Boost Factor |
|----------|-------------------|--------------|
| CSS | XPath, ATTRIBUTE_MATCH | +5% |
| XPath | CSS, DOM_RELATIONSHIP | +5% |
| TEXT_ANCHOR | DOM_RELATIONSHIP, ROLE_BASED | +5% |
| ATTRIBUTE_MATCH | CSS, XPath | +5% |
| DOM_RELATIONSHIP | XPath, TEXT_ANCHOR | +5% |
| ROLE_BASED | TEXT_ANCHOR | +3% |

---

## Previous Story Intelligence

### From Story 4-2 Implementation
- **Approval workflow exists**: `POST /failures/{id}/approve` endpoint implemented
- **Learning integration exists**: `_record_positive_feedback()` method exists but has TODOs
- **ConfidenceScorer exists**: Already has `_historical_data` storage and `record_positive_feedback()` stub
- **Key Issue**: Learning is NOT fully implemented - this is what Story 5.1 completes!

### Files to Modify
**Backend (Python):**
- `src/selectors/adaptive/services/confidence_scorer.py` - Implement `record_positive_feedback()` fully
- `src/selectors/adaptive/services/failure_service.py` - May need to ensure proper call to learning system

**Database (if needed):**
- Create/use `weights` table for persistence

**Tests:**
- `tests/selectors/adaptive/test_confidence_scorer.py` - Add tests for learning functionality

### Key Learnings from Previous Stories
- Story 4-2 marked approval as working but learning is incomplete
- Sprint Change Proposal explicitly states: "MUST extend existing ConfidenceScorer"
- Do NOT create new services - extend what exists

---

## Web Research Notes

### Latest Technical Considerations

For implementing the learning system, consider:

1. **Weight Decay**: Consider if older approvals should have less influence over time
2. **Confidence Bounds**: Ensure learned weights don't push confidence above 1.0
3. **Strategy vs Specific**: Distinguish between learning from specific selectors vs strategy types
4. **Cold Start**: Handle case where no approvals have been recorded yet

### Potential Enhancements (Post-MVP)
- Weighted average of historical confidence scores
- Exponential moving average for recent approvals
- Per-sport/per-site weight specialization

---

## References

- [Source: _bmad-output/planning-artifacts/epics.md#408-424] - Story 5.1 requirements with BDD acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#146-161] - Data Architecture and Tables
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-03.md] - **CRITICAL**: Sprint Change Proposal mandating ConfidenceScorer extension
- [Source: _bmad-output/planning-artifacts/architecture.md#218-257] - Code Organization and Module Structure

### Previous Epic Dependencies
- [Source: _bmad-output/implementation-artifacts/3-2-generate-confidence-scores.md] - Confidence scoring (Story 3.2)
- [Source: _bmad-output/implementation-artifacts/4-2-approve-or-reject-proposed-selectors.md] - Approval workflow (Story 4.2)

### Existing Implementation (Build Upon)
- [Source: src/selectors/adaptive/services/confidence_scorer.py#507-555] - Existing `record_positive_feedback()` stub with TODOs
- [Source: src/selectors/adaptive/services/confidence_scorer.py#404-427] - Existing `add_historical_data()` method
- [Source: src/selectors/adaptive/services/failure_service.py#344-386] - Approval flow calling learning system

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Backend (Python) - Modify existing:**
- `src/selectors/adaptive/services/confidence_scorer.py` - Implement full `record_positive_feedback()` with learning logic

**Database (if needed):**
- `src/selectors/adaptive/db/models/weights.py` - Create if weights table doesn't exist

**Tests:**
- `tests/selectors/adaptive/test_confidence_scorer.py` - Add tests for approval learning

**Frontend (if needed):**
- May need to display learned weights in UI (future Epic 5.3)
