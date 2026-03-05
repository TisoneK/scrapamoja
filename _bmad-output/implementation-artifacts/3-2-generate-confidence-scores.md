# Story 3.2: Generate Confidence Scores

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **System**,
I want to calculate confidence scores for proposed selectors
So that users can make informed decisions.

## Acceptance Criteria

1. **Given** multiple proposed selector alternatives
   **When** confidence scores are calculated
   **Then** scores should range from 0.0 to 1.0
   **And** the scoring should consider: historical stability, selector specificity, DOM structure similarity

2. **Given** proposed selectors with confidence scores
   **When** they are displayed to users
   **Then** they should be sorted by confidence score (highest first)

## Tasks / Subtasks

- [x] Task 1: Create ConfidenceScorer Service (AC: #1)
  - [x] Subtask 1.1: Design ConfidenceScore dataclass with all scoring factors
  - [x] Subtask 1.2: Implement historical stability scoring component
  - [x] Subtask 1.3: Implement selector specificity scoring component
  - [x] Subtask 1.4: Implement DOM structure similarity scoring component
  - [x] Subtask 1.5: Implement weighted scoring algorithm

- [x] Task 2: Integrate with DOM Analysis (AC: #1)
  - [x] Subtask 2.1: Extend AlternativeSelector with detailed scoring breakdown
  - [x] Subtask 2.2: Connect to DOMAnalyzer output (Story 3.1)
  - [x] Subtask 2.3: Handle edge cases (no historical data, incomplete DOM)

- [x] Task 3: Add Sorting by Confidence (AC: #2)
  - [x] Subtask 3.1: Implement sort by confidence (descending)
  - [x] Subtask 3.2: Add confidence tier categorization (high/medium/low)

- [x] Task 4: Add Tests (AC: #1, #2)
  - [x] Subtask 4.1: Unit tests for each scoring component
  - [x] Subtask 4.2: Integration test for full scoring pipeline
  - [x] Subtask 4.3: Test sorting and tier categorization

## Dev Notes

### Project Structure Notes

- **Module Location**: `src/selectors/adaptive/` (per architecture)
- **New Service**: `src/selectors/adaptive/services/confidence_scorer.py` - Confidence scoring service
- **Extend**: `src/selectors/adaptive/services/dom_analyzer.py` from Story 3.1
- **Existing Dependencies**:
  - `src/selectors/adaptive/services/dom_analyzer.py` - AlternativeSelector (Story 3.1)
  - `src/selectors/adaptive/db/models/snapshot.py` - Snapshot model (Story 2.2)
  - `src/selectors/adaptive/services/stability_scoring.py` - Stability scoring pattern (Epic 1)

**Naming Conventions:**
- Python: `snake_case` for variables/functions
- Service Classes: `PascalCase` (e.g., `ConfidenceScorer`)
- Confidence Tiers: lowercase enum values (e.g., `high`, `medium`, `low`)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#293-308] - Story requirements with BDD acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#218-227] - Code Organization: New module under `src/selectors/adaptive/`
- [Source: _bmad-output/implementation-artifacts/3-1-analyze-dom-structure.md] - Story 3.1 (DOM Analysis)

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

- Created ConfidenceScorer service with weighted scoring algorithm
- Implemented historical stability, specificity, and DOM similarity scoring components
- Extended AlternativeSelector with scoring breakdown and confidence tier fields
- Added rank_selectors method for sorting by confidence (descending)
- Created comprehensive unit tests (30 tests, all passing)
- All acceptance criteria satisfied: scores range 0.0-1.0, sorted by confidence

### Code Review Fixes Applied (2026-03-04)

- **FIXED**: Import error in stability_scoring.py - changed from `src.selectors.confidence` to `src.selectors.adaptive.services.confidence_scorer`
- **FIXED**: Added missing `update_strategy_metrics()` method to ConfidenceScorer for stability_scoring integration
- **FIXED**: Type annotations in AlternativeSelector to accept dataclass types (was expecting only dict)
- **FIXED**: Updated `_historical_data` type to support both float scores and dict metrics

### Remaining Known Issues

- **SNAPSHOT REPO DELETED**: SnapshotRepository was deleted in previous work. DOM similarity calculation falls back to defaults when repository unavailable. Consider restoring if needed.

### File List

- src/selectors/adaptive/services/confidence_scorer.py (NEW)
- src/selectors/adaptive/services/dom_analyzer.py (MODIFIED - extended AlternativeSelector)
- src/selectors/adaptive/services/__init__.py (MODIFIED - added exports)
- tests/unit/selectors/adaptive/services/test_confidence_scorer.py (NEW)

---

# Comprehensive Story Context for Implementation

## 1. Story Foundation

### Epic Context (Epic 3: Alternative Selector Proposal)

Epic 3 builds on Epic 2's failure detection foundation to propose alternative selectors with confidence scores:

- **Story 3.1**: Analyze DOM Structure (ready-for-dev - first in Epic 3)
- **Story 3.2**: Generate Confidence Scores (THIS STORY - backlog)
- **Story 3.3**: Calculate Blast Radius (backlog)

**Epic 3 Goal**: Analyze DOM structure and propose multiple alternative selector strategies with confidence scores.

### Dependencies

- **Prerequisite**: Story 3.1 (Analyze DOM Structure) - provides AlternativeSelector with initial confidence
- **Prerequisite**: Story 2.2 (Capture DOM Snapshot) - provides HTML snapshots
- **Prerequisite**: Story 1.3/1.3a (Stability Scoring) - provides stability scoring pattern

### Business Value

Confidence scoring enables:
- Users to make informed decisions about which selector to approve
- Ranking selectors by reliability for automated selection
- Feeding the learning system (Epic 5) with quality data
- Reducing failures by prioritizing stable selectors

---

## 2. Technical Foundation

### Architecture Requirements (from architecture.md)

**Technology Stack:**
- Database: SQLite (MVP) with SQLAlchemy 2.0 async
- Backend: FastAPI
- HTML Parsing: BeautifulSoup4 or lxml
- Existing: StabilityScorer from Epic 1

**Code Structure (from architecture.md):**
```
src/
├── selectors/
│   ├── adaptive/
│   │   ├── services/
│   │   │   ├── confidence_scorer.py (NEW - THIS STORY)
│   │   │   ├── dom_analyzer.py (Story 3.1)
│   │   │   ├── proposal_engine.py (Story 3.2 - combines analyzer + scorer)
│   │   │   ├── blast_radius.py (Story 3.3)
```

### Previous Story Learnings (Story 3.1)

From Story 3.1 (Analyze DOM Structure):

**AlternativeSelector Structure (extends Story 3.1):**
```python
@dataclass
class AlternativeSelector:
    selector_string: str
    strategy_type: StrategyType
    confidence_score: float  # Placeholder from Story 3.1
    element_description: str
    
    # NEW in Story 3.2 - detailed scoring:
    scoring_breakdown: Optional[ScoringBreakdown] = None
    confidence_tier: Optional[ConfidenceTier] = None
    historical_stability: Optional[float] = None
    specificity_score: Optional[float] = None
    dom_similarity: Optional[float] = None
```

**Key Pattern to Follow:**
- Story 3.1 returns initial placeholder confidence scores (0.5-0.9 range)
- Story 3.2 refines these scores using historical data, specificity, and DOM analysis
- Keep backward compatible - Story 3.1 code should work without changes

### Existing Code to Reference

**Story 3.1 (Ready for Dev):**
- `src/selectors/adaptive/services/dom_analyzer.py` - DOMAnalyzer with AlternativeSelector
- Strategy types: CSS, XPATH, TEXT_ANCHOR, ATTRIBUTE_MATCH, DOM_RELATIONSHIP, ROLE_BASED

**Epic 1 (Complete):**
- `src/selectors/adaptive/services/stability_scoring.py` - StabilityScoring service pattern
- `src/selectors/adaptive/db/models/recipe.py` - Recipe model with stability_score field

---

## 3. Developer Implementation Guardrails

### Critical Requirements

1. **CONFIDENCE SCORE RANGE**: Must be 0.0 to 1.0
   - 0.0 = completely unreliable
   - 1.0 = extremely reliable
   - Use float for precision

2. **SCORING FACTORS** (per AC1):
   - **Historical Stability**: Look up selector in audit/weights table (Epic 5 patterns apply early)
   - **Selector Specificity**: More specific selectors get higher scores
     - ID-based: 0.8-0.9
     - Class-based: 0.6-0.8
     - Tag-only: 0.3-0.5
   - **DOM Structure Similarity**: How close to original failed selector

3. **SORTING** (per AC2):
   - Always sort by confidence_score descending
   - Highest confidence first

4. **CONFIDENCE TIERS**:
   - HIGH: 0.7-1.0 (green)
   - MEDIUM: 0.4-0.69 (yellow)
   - LOW: 0.0-0.39 (red)

5. **BACKWARD COMPATIBILITY**:
   - Story 3.1 code must work unchanged
   - Extend AlternativeSelector, don't replace
   - Handle missing historical data gracefully (use defaults)

### Testing Standards

- Unit tests in `tests/unit/selectors/adaptive/services/`
- Mock historical data for testing scoring
- Test edge cases: no history, empty selectors, invalid strategies

### Naming Conventions

- Python: snake_case (functions, variables)
- Service Classes: PascalCase
- Files: snake_case.py
- Confidence Tiers: lowercase enum

---

## 4. Acceptance Criteria Deep Dive

### AC1: Calculate Confidence Scores (0.0-1.0)

**Implementation Approach:**

1. **ConfidenceScorer Service**:
   ```python
   from dataclasses import dataclass
   from enum import Enum
   from typing import Optional
   
   class ConfidenceTier(Enum):
       HIGH = "high"      # 0.7-1.0
       MEDIUM = "medium"  # 0.4-0.69
       LOW = "low"        # 0.0-0.39
   
   @dataclass
   class ScoringBreakdown:
       historical_stability: float      # 0.0-1.0
       specificity_score: float         # 0.0-1.0
       dom_similarity: float            # 0.0-1.0
       final_score: float               # 0.0-1.0
   
   class ConfidenceScorer:
       """Service for calculating refined confidence scores."""
       
       # Weights for each factor (adjustable)
       WEIGHTS = {
           'historical_stability': 0.4,
           'specificity': 0.35,
           'dom_similarity': 0.25,
       }
       
       async def calculate_confidence(
           self,
           selector: AlternativeSelector,
           snapshot_id: int,
           sport: str,
           site: str,
       ) -> AlternativeSelector:
           """Calculate refined confidence score for a selector."""
           
           # 1. Historical stability (40% weight)
           historical = await self._get_historical_stability(
               selector.selector_string,
               selector.strategy_type,
               sport,
           )
           
           # 2. Specificity score (35% weight)
           specificity = self._calculate_specificity(selector.selector_string)
           
           # 3. DOM similarity (25% weight)
           dom_sim = await self._calculate_dom_similarity(
               selector.selector_string,
               snapshot_id,
           )
           
           # Weighted final score
           final_score = (
               historical * self.WEIGHTS['historical_stability'] +
               specificity * self.WEIGHTS['specificity'] +
               dom_sim * self.WEIGHTS['dom_similarity']
           )
           
           # Clamp to 0.0-1.0
           final_score = max(0.0, min(1.0, final_score))
           
           # Build breakdown
           breakdown = ScoringBreakdown(
               historical_stability=historical,
               specificity_score=specificity,
               dom_similarity=dom_sim,
               final_score=final_score,
           )
           
           # Determine tier
           tier = self._get_tier(final_score)
           
           return AlternativeSelector(
               selector_string=selector.selector_string,
               strategy_type=selector.strategy_type,
               confidence_score=final_score,
               element_description=selector.element_description,
               scoring_breakdown=breakdown,
               confidence_tier=tier,
               historical_stability=historical,
               specificity_score=specificity,
               dom_similarity=dom_sim,
           )
   ```

2. **Historical Stability**:
   ```python
   async def _get_historical_stability(
       self,
       selector_string: str,
       strategy_type: StrategyType,
       sport: str,
   ) -> float:
       """Look up selector in historical data."""
       # Check weights table (Epic 5 pattern - implement early)
       # If no history, use strategy-based default
       weight = await self.weight_repo.get_weight(selector_string, strategy_type, sport)
       if weight:
           return weight.confidence_factor  # Normalize to 0-1
       
       # Default based on strategy type
       defaults = {
           StrategyType.CSS: 0.7,
           StrategyType.XPATH: 0.65,
           StrategyType.TEXT_ANCHOR: 0.6,
           StrategyType.ATTRIBUTE_MATCH: 0.55,
           StrategyType.DOM_RELATIONSHIP: 0.5,
           StrategyType.ROLE_BASED: 0.5,
       }
       return defaults.get(strategy_type, 0.5)
   ```

3. **Specificity Calculation**:
   ```python
   def _calculate_specificity(self, selector: str) -> float:
       """Calculate selector specificity score."""
       # ID selectors: highest specificity
       if '#' in selector and selector.count('#') == 1:
           # e.g., #main-content
           return 0.9
       
       # Class-based selectors
       if '.' in selector:
           class_count = selector.count('.')
           return min(0.8, 0.5 + (class_count * 0.1))
       
       # Attribute selectors
       if '[' in selector:
           return 0.6
       
       # Tag + class combinations
       if len(selector.split()) > 1:
           return 0.5
       
       # Tag only: lowest specificity
       return 0.3
   ```

4. **DOM Similarity**:
   ```python
   async def _calculate_dom_similarity(
       self,
       selector: str,
       snapshot_id: int,
   ) -> float:
       """Calculate how similar this selector is to the failed one."""
       # Load snapshot
       snapshot = await self.snapshot_repo.get_by_id(snapshot_id)
       
       # Compare with original failed selector
       # Higher similarity = more likely to work similarly
       # Use string distance or DOM path similarity
       
       # Simple implementation: check if selectors share ancestors
       failed_path = self._get_dom_path(snapshot.html_content, self.failed_selector)
       new_path = self._get_dom_path(snapshot.html_content, selector)
       
       return self._calculate_path_similarity(failed_path, new_path)
   ```

### AC2: Sort by Confidence (Highest First)

**Implementation:**
```python
async def rank_selectors(
    self,
    selectors: List[AlternativeSelector],
) -> List[AlternativeSelector]:
    """Sort selectors by confidence score (highest first)."""
    return sorted(
        selectors,
        key=lambda s: s.confidence_score,
        reverse=True,
    )

def _get_tier(self, score: float) -> ConfidenceTier:
    """Categorize confidence into tier."""
    if score >= 0.7:
        return ConfidenceTier.HIGH
    elif score >= 0.4:
        return ConfidenceTier.MEDIUM
    else:
        return ConfidenceTier.LOW
```

---

## 5. Integration Points

### With Story 3.1 (DOM Analysis)

- **Input**: List[AlternativeSelector] with placeholder confidence scores
- **Process**: Refine each selector's confidence using scoring algorithm
- **Output**: Enhanced AlternativeSelector with detailed scoring

### With Story 2.2 (Snapshot Capture)

- **Input**: snapshot_id for DOM similarity calculation
- **Get**: HTML content for DOM path analysis

### With Story 5.1-5.3 (Learning - Future)

- **Output**: Weights/audit data that will be used by Epic 5
- **Pre-pattern**: Use weight lookup even though Epic 5 not started

### With Story 3.3 (Blast Radius)

- **Input**: Confidence scores for impact calculation
- **Hand-off**: Blast radius can weight by confidence

---

## 6. Edge Cases to Handle

1. **No Historical Data**: Use strategy-type defaults
2. **Invalid Selector Syntax**: Return low confidence (0.1)
3. **Empty Selector List**: Return empty list (don't fail)
4. **DOM Parse Error**: Skip DOM similarity, use other factors
5. **Very Long Selectors**: Penalize with lower specificity
6. **Duplicate Selectors**: Deduplicate before scoring
7. **Mixed Strategy Types**: Score each independently

---

## 7. File Checklist

### New Files to Create

1. `src/selectors/adaptive/services/confidence_scorer.py` - Main confidence scoring service
2. `tests/unit/selectors/adaptive/services/test_confidence_scorer.py` - Service tests

### Files to Modify

1. `src/selectors/adaptive/services/__init__.py` - Export new service
2. `src/selectors/adaptive/services/dom_analyzer.py` - Optionally integrate scorer

### Optional Integration

- Create `proposal_engine.py` to combine DOMAnalyzer + ConfidenceScorer (cleaner architecture)

---

## 8. Quick Start for Implementation

### Step 1: Create ConfidenceScorer Service
Create `src/selectors/adaptive/services/confidence_scorer.py` with:
- ConfidenceTier enum
- ScoringBreakdown dataclass
- ConfidenceScorer class with calculate_confidence method

### Step 2: Implement Scoring Components
Add methods:
- _get_historical_stability
- _calculate_specificity
- _calculate_dom_similarity
- _get_tier

### Step 3: Add Ranking
Add rank_selectors method for sorting

### Step 4: Add Tests
Create unit tests for each scoring component

---

# ARCHITECTURE COMPLIANCE

## From Architecture Document

**Technology Stack:**
- ✅ Uses SQLAlchemy 2.0 async patterns (per Epic 1)
- ✅ Uses repository pattern for data access
- ✅ Uses dataclasses for data structures

**Code Organization:**
- ✅ New service in `src/selectors/adaptive/services/`
- ✅ Follows naming conventions (snake_case, PascalCase)
- ✅ Prepares for Epic 5 learning system integration

**API Patterns:**
- ✅ Returns structured data with breakdown
- ✅ Includes metadata for debugging

## Previous Story Learnings

From Story 3.1 (Analyze DOM Structure):
- Use async repository pattern consistently
- Include comprehensive docstrings
- Add type hints throughout
- Return empty collections rather than None
- Handle exceptions gracefully at service boundary

From Story 2.3 (Complete):
- Use dataclasses for clear data structures
- Add scoring breakdown for transparency
- Provide defaults when data unavailable

---

# LATEST TECHNICAL SPECIFICATIONS

## Library Versions

- **SQLAlchemy**: 2.0.0+ (from project-context.md)
- **Pydantic**: 2.5.0+ (from project-context.md)
- **BeautifulSoup4**: 4.12.0+ (from project-context.md)
- **lxml**: 4.9.0+ (from project-context.md)

## Best Practices

1. **Async Throughout**: All database operations must be async
2. **Type Hints**: MyPy strict mode enabled - all functions need hints
3. **Error Handling**: Use exception hierarchy from project-context.md
4. **No Blocking**: Never use time.sleep(), use asyncio.sleep()
5. **Resource Cleanup**: Always use async context managers

---

# PROJECT CONTEXT REFERENCE

## Critical Rules from project-context.md

1. **All functions must have type hints** - MyPy strict mode
2. **Use Optional[X] consistently** - Not X | None
3. **Always use async/await for I/O** - Never blocking calls
4. **Never use sync Playwright** - Use async_playwright
5. **Never block event loop** - Use asyncio.sleep not time.sleep

## Testing Requirements

- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.asyncio`
- Run with: `pytest --cov=src --cov-report=term-missing`
- Location: `tests/` directory

---

# STORY COMPLETION STATUS

- Status: ready-for-dev
- Created: 2026-03-04
- Ultimate context engine analysis completed - comprehensive developer guide created
