# Story 5.3: Track Selector Survival Across Generations

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **System**,
I want to track selector survival across layout generations
So that stability scores can be calculated accurately.

## Acceptance Criteria

1. **Given** a recipe version
   **When** selectors survive a layout generation change on the target site
   **Then** the `generation_survived` count should increment
   **And** the stability score should reflect the survival rate

2. **Given** a selector that fails
   **When** the failure is detected
   **Then** it should be recorded as a generation failure
   **And** the recipe should be marked for review

## Tasks / Subtasks

- [x] Task 1: Implement Generation Tracking (AC: #1)
  - [x] Subtask 1.1: Add generation metadata to recipe versions
  - [x] Subtask 1.2: Implement generation detection mechanism
  - [x] Subtask 1.3: Track selector survival count per recipe

- [x] Task 2: Implement Stability Score Calculation (AC: #1)
  - [x] Subtask 2.1: Extend stability scoring with generation survival
  - [x] Subtask 2.2: Update confidence calculation to factor in generations
  - [x] Subtask 2.3: Test stability score updates on generation changes

- [x] Task 3: Implement Generation Failure Detection (AC: #2)
  - [x] Subtask 3.1: Detect selector failures as generation failures
  - [x] Subtask 3.2: Record generation failure events
  - [x] Subtask 3.3: Mark recipes for review on failure

- [x] Task 4: Integrate with Learning System (AC: #1, #2)
  - [x] Subtask 4.1: Connect generation tracking to approval learning
  - [x] Subtask 4.2: Connect generation tracking to rejection learning
  - [x] Subtask 4.3: Ensure generation data persists with weights

---

## Critical Architecture Requirements

### ⚠️ MANDATORY: Integration Requirements (DO NOT REINVENT)

Per Sprint Change Proposal (_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-03.md) and Epic 5 pattern:

1. **MUST EXTEND existing `ConfidenceScorer`** from `src/selectors/adaptive/services/confidence_scorer.py`
   - DO NOT create a new scoring service
   - DO NOT duplicate the scoring logic
   - This story extends the learning system from Stories 5.1 and 5.2

2. **Existing Systems to Extend:**
   | Need | Use This | Location |
   |------|----------|----------|
   | Confidence scoring | `ConfidenceScorer` | `src/selectors/adaptive/services/confidence_scorer.py` |
   | Historical data | `_historical_data` dict | Same as above |
   | Approval learning | `record_positive_feedback()` | Same as above (Story 5.1 implemented) |
   | Rejection learning | `record_negative_feedback()` | Same as above (Story 5.2 implemented) |
   | Weights persistence | `weights` table | `src/selectors/adaptive/db/models/weights.py` |

3. **Pattern for Extension:**
   ```python
   # CORRECT: Extend existing - Stories 5.1 and 5.2 established the pattern
   class GenerationTrackingScorer(ConfidenceScorer):
       def __init__(self):
           super().__init__()
           self._generation_data = {}  # Add generation tracking
   
       def record_generation_survival(self, recipe_id, generation):
           # Track survival across generations
   
       def calculate_generation_stability(self, recipe_id):
           # Calculate stability based on generation survival
   
   # WRONG: Create parallel system
   class NewStabilityService:  # DON'T DO THIS
       def calculate(self):
           # own implementation - DUPLICATES ConfidenceScorer
   ```

### Module Structure
Per architecture, all new code goes in:
- **Python Backend**: `src/selectors/adaptive/`
- **Frontend**: `ui/escalation/` (existing React app)

### Database Tables
- `recipes` - Already has generation field (per Epic 1)
- `weights` - Extend from Stories 5.1 and 5.2 for generation data

### Technology Stack
- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Pydantic
- **Frontend**: React + TypeScript (existing)
- **Authentication**: API Keys (per architecture)

---

## Developer Guardrails

### DO NOT REINVENT
- ✅ Use existing `ConfidenceScorer` from `src/selectors/adaptive/services/confidence_scorer.py`
- ✅ Use existing `_historical_data` dictionary for data storage
- ✅ Use existing weights table pattern from Epic 5 (Stories 5.1 and 5.2)
- ✅ Follow the same extension pattern as Stories 5.1 and 5.2
- ❌ DO NOT create new scoring logic
- ❌ DO NOT duplicate existing confidence calculation
- ❌ DO NOT create separate stability service

### MUST USE
- FastAPI for all API endpoints (already implemented)
- SQLAlchemy 2.0 async patterns (already established)
- Pydantic for request/response validation
- React Query for server state management
- Tailwind CSS for styling

### Naming Conventions
- Python: `snake_case` for functions/variables
- TypeScript: `camelCase` variables, `PascalCase` components
- API Response: `{"data": {...}` format per architecture
- Errors: RFC 7807 format `{"type": "...", "title": "...", "detail": "..."}`

### Critical Implementation Details

**Existing Code to Build Upon:**

```python
# From src/selectors/adaptive/services/confidence_scorer.py

# 1. Existing method - NEEDS EXTENSION for generation tracking:
# The ConfidenceScorer class already has:
self._historical_data: Dict[str, float | Dict[str, Any]] = {}

# Stories 5.1 and 5.2 added:
self._approval_weights: Dict[StrategyType, float] = {}
self._rejection_weights: Dict[StrategyType, float] = {}

# Story 5.3 needs to add:
self._generation_data: Dict[str, Dict[str, Any]] = {}  # {recipe_id: {generation: int, survived: int, failures: int}}

# 2. Existing weights:
WEIGHTS = {
    'historical_stability': 0.4,
    'specificity': 0.35,
    'dom_similarity': 0.25,
}

# Story 5.3 should consider adding:
GENERATION_WEIGHT = 0.15  # Weight for generation survival in confidence calculation
```

**From Stories 5-1 and 5-2 Implementation:**
```python
# Stories 5.1 and 5.2 established the learning pattern - follow same for generation:
# 1. Add tracking dictionary to __init__
# 2. Implement record method (record_generation_survival, record_generation_failure)
# 3. Add to confidence calculation
# 4. Add persistence methods
# 5. Connect to existing failure detection system
```

---

## Technical Implementation Notes

### Generation Tracking Architecture

The tracking of selector survival across generations should work as follows:

1. **On Site Layout Change Detection:**
   - System detects when target site has a layout change (generation increment)
   - This can be detected via:
     - Periodic DOM structure analysis
     - Selector failure patterns (multiple failures in short time)
     - Explicit generation markers in recipes
   
2. **Generation Survival Tracking:**
   ```
   For each recipe:
   1. Track current generation number
   2. Track number of generations survived
   3. Track number of generation failures
   4. Calculate survival rate: survived / total_generations
   5. Factor into stability score
   ```

3. **Stability Score Integration:**
   - Generation survival should contribute to stability score
   - Higher survival = higher stability = higher confidence
   - Formula: `stability = base_stability * (1 + generation_weight * survival_rate)`

4. **Generation Failure Recording:**
   - When selector fails, check if it's a generation failure
   - Generation failure = failure after site layout change
   - Record failure count per generation
   - Mark recipe for review after X consecutive failures

### Generation Detection Strategies

| Strategy | Detection Method | Reliability |
|----------|-----------------|-------------|
| DOM Hash | Compare DOM structure hashes | High |
| Failure Pattern | Multiple failures in short window | Medium |
| Explicit Marker | Version bump in recipe | High |
| Time-based | Assume change after X days | Low |

### Database Schema Considerations

```python
# Extend existing weights table or create generation table
class GenerationData:
    recipe_id: str
    current_generation: int
    generations_survived: int
    generation_failures: int
    last_generation_change: datetime
    stability_score: float
```

---

## Previous Story Intelligence

### From Story 5-1 Implementation (Learn from Approvals)
- **Approval learning implemented**: `record_positive_feedback()` is fully implemented
- **Weight persistence exists**: Weights table with approval data
- **Strategy relationship matrix**: Boost factors for related strategies
- **Key Insight**: Follow same pattern for generation tracking

### From Story 5-2 Implementation (Learn from Rejections)
- **Rejection learning implemented**: `record_negative_feedback()` is fully implemented
- **Rejection weights persist**: Rejection data saved to database
- **Penalty system**: Strategy penalties capped at 25%
- **Key Insight**: Generation tracking should mirror this pattern

### What Stories 5.1 and 5.2 Did (Follow Same Pattern):
1. Extended `ConfidenceScorer` with tracking dictionaries
2. Implemented record methods (positive/negative feedback)
3. Added to confidence calculation
4. Created persistence methods
5. Connected to workflow endpoints

### Files to Modify
**Backend (Python):**
- `src/selectors/adaptive/services/confidence_scorer.py` - Add generation tracking methods
- `src/selectors/adaptive/services/failure_service.py` - Connect to generation tracking

**Database (if needed):**
- Extend `weights` table or create generation tracking table

**Tests:**
- Add tests for generation tracking (extend existing test files)

### Key Learnings from Epic 5 Stories
- Always extend `ConfidenceScorer` - never create parallel systems
- Mirror the pattern from Stories 5.1 and 5.2 for new tracking
- Persistence is critical - data must survive restarts
- Generation tracking should integrate with existing learning system

---

## Web Research Notes

### Latest Technical Considerations

For implementing generation tracking, consider:

1. **Generation vs Version**: Distinguish between recipe version (selector changes) and generation (site layout changes)
2. **Detection Sensitivity**: Balance between detecting real changes and false positives
3. **Storage Efficiency**: Don't store full DOM for every generation - just hashes/markers
4. **Recovery**: Consider if/how failed generations can recover

### Potential Enhancements (Post-MVP)
- Automatic generation detection using ML
- Per-generation selector performance tracking
- Predictive generation survival modeling
- Cross-site generation correlation

---

## References

- [Source: _bmad-output/planning-artifacts/epics.md#442-459] - Story 5.3 requirements with BDD acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#146-161] - Data Architecture and Tables
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-03.md] - **CRITICAL**: Sprint Change Proposal mandating ConfidenceScorer extension
- [Source: _bmad-output/planning-artifacts/architecture.md#218-257] - Code Organization and Module Structure

### Previous Epic Dependencies
- [Source: _bmad-output/implementation-artifacts/1-1-extend-yaml-schema-with-recipe-metadata.md] - Recipe metadata (Story 1.1)
- [Source: _bmad-output/implementation-artifacts/1-2-create-recipe-version-storage.md] - Recipe versioning (Story 1.2)
- [Source: _bmad-output/implementation-artifacts/3-2-generate-confidence-scores.md] - Confidence scoring (Story 3.2)
- [Source: _bmad-output/implementation-artifacts/5-1-learn-from-approvals.md] - **MUST READ**: Learn from approvals (Story 5.1) - follow pattern
- [Source: _bmad-output/implementation-artifacts/5-2-learn-from-rejections.md] - **MUST READ**: Learn from rejections (Story 5.2) - follow pattern

### Existing Implementation (Build Upon)
- [Source: src/selectors/adaptive/services/confidence_scorer.py] - ConfidenceScorer with Stories 5.1 and 5.2 extensions
- [Source: src/selectors/adaptive/db/models/weights.py] - Weights models (extended by Stories 5.1 and 5.2)
- [Source: src/selectors/adaptive/db/repositories/weight_repository.py] - Weight persistence (extended by Stories 5.1 and 5.2)
- [Source: src/selectors/adaptive/services/failure_service.py] - Failure detection (connects to learning system)

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

Implementation of Story 5.3 Track Selector Survival Across Generations completed:

**Summary:**
- Extended ConfidenceScorer with generation tracking capabilities
- Added database model and repository methods for persistence
- Updated confidence calculation to factor in generation stability

**Key Changes:**
1. Added `_generation_data` dict to track per-recipe generation info
2. Implemented `record_generation_survival()` - tracks successful generations
3. Implemented `record_generation_failure()` - tracks failures, triggers review after 3 consecutive
4. Implemented `calculate_generation_stability()` - calculates stability based on survival rate
5. Updated `calculate_confidence()` - applies generation stability factor to final score
6. Added GenerationData SQLAlchemy model for persistence
7. Added repository methods for generation data CRUD operations

**Tests Added:**
- 19 unit tests covering all generation tracking functionality
- All existing 30 confidence scorer tests still pass

### File List

**Backend (Python) - Modify existing:**
- `src/selectors/adaptive/services/confidence_scorer.py` - Added generation tracking methods: `_generation_data`, `record_generation_survival()`, `record_generation_failure()`, `calculate_generation_stability()`, `get_generation_data()`, `load_generation_data()`, `save_generation_data()`, `detect_generation_change()`, `get_generation_boost()`, `should_mark_recipe_for_review()`, `reset_generation_failures()`, `export_generation_data()`, `load_generation_data()`
- Updated `calculate_confidence()` to accept `recipe_id` parameter and apply generation stability

**Database - Extend existing:**
- `src/selectors/adaptive/db/models/weights.py` - Added GenerationData model
- `src/selectors/adaptive/db/repositories/weight_repository.py` - Added generation data persistence methods: `upsert_generation_data()`, `get_generation_data()`, `get_all_generation_data()`, `load_generation_data_for_scorer()`, `delete_generation_data()`

**Tests - Add:**
- `tests/unit/selectors/adaptive/services/test_generation_tracking.py` - 19 tests for generation tracking
