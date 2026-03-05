# Story 3.1: Analyze DOM Structure

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **System**,
I want to analyze the captured DOM snapshot
So that I can identify alternative selector strategies.

## Acceptance Criteria

1. **Given** a DOM snapshot from a failed selector
   **When** the analysis runs
   **Then** it should identify potential alternative selectors using multiple strategies: CSS, XPath, text anchor, attribute match, DOM relationships, role-based

2. **Given** the DOM analysis
   **When** it identifies alternatives
   **Then** each alternative should include: selector string, strategy type, confidence score

## Tasks / Subtasks

- [x] Task 1: Create DOM Analysis Service (AC: #1)
  - [x] Subtask 1.1: Create DOMAnalyzer class to parse HTML snapshots
  - [x] Subtask 1.2: Implement CSS selector strategy analyzer
  - [x] Subtask 1.3: Implement XPath selector strategy analyzer
  - [x] Subtask 1.4: Implement text anchor selector strategy analyzer
  - [x] Subtask 1.5: Implement attribute match selector strategy analyzer
  - [x] Subtask 1.6: Implement DOM relationship selector strategy analyzer
  - [x] Subtask 1.7: Implement role-based selector strategy analyzer

- [x] Task 2: Create Alternative Selector Generator (AC: #1)
  - [x] Subtask 2.1: Create AlternativeSelector class to hold selector data
  - [x] Subtask 2.2: Implement generate_alternatives method in DOMAnalyzer
  - [x] Subtask 2.3: Add scoring for each selector strategy

- [x] Task 3: Integrate with Snapshot System (AC: #2)
  - [x] Subtask 3.1: Load HTML from snapshot (Story 2.2)
  - [x] Subtask 3.2: Get failed selector context from FailureEvent (Story 2.3)
  - [x] Subtask 3.3: Return alternatives with strategy type and confidence

- [x] Task 4: Add Tests (AC: #1)
  - [x] Subtask 4.1: Unit tests for each strategy analyzer
  - [x] Subtask 4.2: Integration test for full analysis pipeline
  - [x] Subtask 4.3: Test edge cases (empty snapshot, malformed HTML)

## Dev Notes

### Project Structure Notes

- **Module Location**: `src/selectors/adaptive/` (per architecture)
- **New Service**: `src/selectors/adaptive/services/dom_analyzer.py` - DOM analysis service
- **Existing Dependencies**:
  - `src/selectors/adaptive/db/models/snapshot.py` - Snapshot model (Story 2.2)
  - `src/selectors/adaptive/db/models/failure_event.py` - FailureEvent model (Story 2.1)
  - `src/selectors/adaptive/services/failure_context.py` - Context from Story 2.3

**Naming Conventions:**
- Python: `snake_case` for variables/functions
- Service Classes: `PascalCase` (e.g., `DOMAnalyzer`, `AlternativeSelector`)
- Strategy Types: lowercase enum values (e.g., `css`, `xpath`, `text_anchor`)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#277-291] - Story requirements with BDD acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#218-227] - Code Organization: New module under `src/selectors/adaptive/`
- [Source: _bmad-output/implementation-artifacts/2-2-capture-dom-snapshot-at-failure.md] - Story 2.2 (snapshot capture)
- [Source: _bmad-output/implementation-artifacts/2-3-record-failure-context.md] - Story 2.3 (failure context)

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

**Implementation Date:** 2026-03-04

**Summary:**
- Created `DOMAnalyzer` service in `src/selectors/adaptive/services/dom_analyzer.py`
- Implements all 6 selector strategy types: CSS, XPath, text anchor, attribute match, DOM relationship, role-based
- Each alternative selector includes: selector_string, strategy_type, confidence_score, element_description
- Service returns alternatives sorted by confidence (highest first)
- Deduplicates selectors, keeping highest confidence
- Handles edge cases: empty HTML, malformed HTML, no target found

**Acceptance Criteria Met:**
- ✅ AC1: Identified potential alternative selectors using multiple strategies
- ✅ AC2: Each alternative includes selector string, strategy type, and confidence score

**Tests Added:**
- 36 unit tests covering all strategy types and edge cases
- All tests passing

### File List

- `src/selectors/adaptive/services/dom_analyzer.py` (NEW)
- `tests/unit/selectors/adaptive/services/test_dom_analyzer.py` (NEW)
- `src/selectors/adaptive/services/__init__.py` (MODIFIED - added exports)

---

# Comprehensive Story Context for Implementation

## 1. Story Foundation

### Epic Context (Epic 3: Alternative Selector Proposal)

Epic 3 builds on Epic 2's failure detection foundation to propose alternative selectors. This story (3.1) is the first story in Epic 3:

- **Story 3.1**: Analyze DOM Structure (THIS STORY - backlog)
- **Story 3.2**: Generate Confidence Scores (backlog)
- **Story 3.3**: Calculate Blast Radius (backlog)

**Epic 3 Goal**: Analyze DOM structure and propose multiple alternative selector strategies with confidence scores.

### Dependencies

- **Prerequisite**: Story 2.1 (Detect Selector Resolution Failures) - provides failure events
- **Prerequisite**: Story 2.2 (Capture DOM Snapshot) - provides HTML snapshots
- **Prerequisite**: Story 2.3 (Record Failure Context) - provides context data
- **Blocked by**: Epic 2 completion

### Business Value

DOM analysis enables:
- Proposing multiple alternative selectors when original fails
- Reducing manual intervention in selector fixes
- Supporting Epic 4 (Human Verification Workflow)
- Feeding data to learning system (Epic 5)

---

## 2. Technical Foundation

### Architecture Requirements (from architecture.md)

**Technology Stack:**
- Database: SQLite (MVP) with SQLAlchemy 2.0 async
- Backend: FastAPI
- Browser Automation: Playwright
- HTML Parsing: BeautifulSoup4 or lxml

**Code Structure (from architecture.md):**
```
src/
├── selectors/
│   ├── adaptive/
│   │   ├── services/
│   │   │   ├── dom_analyzer.py (NEW - THIS STORY)
│   │   │   ├── proposal_engine.py (Story 3.2)
│   │   │   ├── blast_radius.py (Story 3.3)
│   │   │   ├── failure_detector.py (Story 2.1)
│   │   │   ├── snapshot_capture.py (Story 2.2)
│   │   │   └── failure_context.py (Story 2.3)
│   │   └── db/
│   │       ├── models/
│   │       │   ├── snapshot.py (Story 2.2)
│   │       │   └── failure_event.py (Story 2.1)
```

### Existing Code to Reference

**Stories 2.1-2.3 (Complete):**
- `src/selectors/adaptive/db/models/failure_event.py` - FailureEvent with context
- `src/selectors/adaptive/db/models/snapshot.py` - Snapshot with HTML content
- `src/selectors/adaptive/services/failure_context.py` - Context capture service
- `src/selectors/adaptive/services/snapshot_capture.py` - Snapshot capture service

**Epic 1 (Complete):**
- `src/selectors/adaptive/db/models/recipe.py` - Recipe model pattern
- `src/selectors/adaptive/services/stability_scoring.py` - Service pattern

---

## 3. Developer Implementation Guardrails

### Critical Requirements

1. **EXISTING SNAPSHOT SYSTEM**: Story 2.2 already captures DOM snapshots
   - Use `Snapshot.html_content` to load HTML for analysis
   - Integrate with existing `SnapshotRepository`

2. **EXISTING FAILURE EVENT**: Story 2.1/2.3 provides failure context
   - Get `failed_selector` from FailureEvent
   - Get `snapshot_id` to load the HTML
   - Get sport/site context for scoring

3. **MULTIPLE STRATEGIES REQUIRED**: Must implement all 6 strategies
   - CSS selector strategies
   - XPath selector strategies
   - Text anchor strategies
   - Attribute match strategies
   - DOM relationship strategies
   - Role-based strategies

4. **CONFIDENCE SCORE STRUCTURE**: Each alternative needs:
   - `selector_string`: The actual selector
   - `strategy_type`: Which strategy generated it
   - `confidence_score`: 0.0 to 1.0 (will be refined in Story 3.2)

5. **ASYNC PATTERNS**:
   - All database operations must be async
   - Use repository pattern from existing code

### Testing Standards

- Unit tests in `tests/unit/selectors/adaptive/services/`
- Mock HTML samples for testing each strategy
- Test edge cases: empty HTML, malformed HTML, no alternatives found

### Naming Conventions

- Python: snake_case (functions, variables)
- Service Classes: PascalCase
- Files: snake_case.py
- Strategy Types: lowercase enum

---

## 4. Acceptance Criteria Deep Dive

### AC1: Identify Alternative Selectors

**Implementation Approach:**

1. **DOM Analyzer Service**:
   ```python
   from dataclasses import dataclass
   from enum import Enum
   
   class StrategyType(Enum):
       CSS = "css"
       XPATH = "xpath"
       TEXT_ANCHOR = "text_anchor"
       ATTRIBUTE_MATCH = "attribute_match"
       DOM_RELATIONSHIP = "dom_relationship"
       ROLE_BASED = "role_based"
   
   @dataclass
   class AlternativeSelector:
       selector_string: str
       strategy_type: StrategyType
       confidence_score: float
       element_description: str  # Human-readable description
   
   class DOMAnalyzer:
       """Service for analyzing DOM snapshots and generating alternative selectors."""
       
       async def analyze_snapshot(
           self,
           snapshot_id: int,
           failed_selector: str,
       ) -> List[AlternativeSelector]:
           """Analyze DOM and generate alternative selectors."""
           # Load snapshot HTML
           snapshot = await self.snapshot_repo.get_by_id(snapshot_id)
           html = snapshot.html_content
           
           # Parse HTML
           soup = BeautifulSoup(html, 'lxml')
           
           # Find target element (using failed selector)
           target = soup.select_one(failed_selector)
           if not target:
               return []
           
           # Generate alternatives using all strategies
           alternatives = []
           alternatives.extend(self._analyze_css(target, soup))
           alternatives.extend(self._analyze_xpath(target, soup))
           alternatives.extend(self._analyze_text_anchor(target, soup))
           alternatives.extend(self._analyze_attribute_match(target, soup))
           alternatives.extend(self._analyze_dom_relationship(target, soup))
           alternatives.extend(self._analyze_role_based(target, soup))
           
           return alternatives
   ```

2. **Strategy Implementations**:
   ```python
   def _analyze_css(self, target, soup) -> List[AlternativeSelector]:
       """Generate CSS selector alternatives."""
       alternatives = []
       
       # ID-based
       if target.get('id'):
           alternatives.append(AlternativeSelector(
               selector_string=f"#{target['id']}",
               strategy_type=StrategyType.CSS,
               confidence_score=0.9,
               element_description=f"ID selector: #{target['id']}"
           ))
       
       # Class-based
       if target.get('class'):
           classes = ' '.join(target.get('class', []))
           alternatives.append(AlternativeSelector(
               selector_string=f".{classes.replace(' ', '.')}",
               strategy_type=StrategyType.CSS,
               confidence_score=0.7,
               element_description=f"Class selector: .{classes}"
           ))
       
       # Tag + class combination
       alternatives.append(AlternativeSelector(
           selector_string=f"{target.name}.{' '.join(target.get('class', []))}",
           strategy_type=StrategyType.CSS,
           confidence_score=0.6,
           element_description=f"Tag-class combination"
       ))
       
       return alternatives
   
   def _analyze_xpath(self, target, soup) -> List[AlternativeSelector]:
       """Generate XPath alternatives."""
       # Use lxml to generate XPath
       from lxml import etree
       # ... implementation
       
   def _analyze_text_anchor(self, target, soup) -> List[AlternativeSelector]:
       """Generate text anchor alternatives."""
       # Find text content and generate text-based selectors
       
   def _analyze_attribute_match(self, target, soup) -> List[AlternativeSelector]:
       """Generate attribute-based alternatives."""
       
   def _analyze_dom_relationship(self, target, soup) -> List[AlternativeSelector]:
       """Generate DOM relationship alternatives."""
       # Find parent, sibling, child relationships
       
   def _analyze_role_based(self, target, soup) -> List[AlternativeSelector]:
       """Generate ARIA role-based alternatives."""
   ```

### AC2: Return Selector with Strategy and Confidence

**Response Structure**:
```python
@dataclass
class AlternativeSelector:
    selector_string: str      # ".match-result"
    strategy_type: StrategyType  # StrategyType.CSS
    confidence_score: float   # 0.85
    element_description: str  # "Class selector for match result"
```

---

## 5. Integration Points

### With Story 2.2 (Snapshot Capture)

- **Input**: `snapshot_id` from FailureEvent
- **Get**: `Snapshot.html_content` for parsing
- **Model**: `src/selectors/adaptive/db/models/snapshot.py`

### With Story 2.3 (Failure Context)

- **Input**: `failed_selector`, sport, site from FailureEvent
- **Use**: Failed selector to find target element
- **Use**: Sport/site context for scoring adjustments

### With Story 3.2 (Generate Confidence Scores)

- **Output**: Initial confidence scores (will be refined)
- **Hand-off**: Story 3.2 will recalculate based on historical data

### With Story 3.3 (Blast Radius)

- **Output**: Alternative selectors for blast radius calculation
- **Hand-off**: Story 3.3 will calculate impact of each alternative

---

## 6. Edge Cases to Handle

1. **Empty Snapshot**: What if snapshot has no HTML content?
2. **Malformed HTML**: Handle parsing errors gracefully
3. **Failed Selector Invalid**: What if failed selector is not valid CSS?
4. **No Alternatives Found**: Return empty list, don't fail
5. **Duplicate Selectors**: Deduplicate alternatives
6. **Very Complex DOM**: Limit analysis depth for performance

---

## 7. File Checklist

### New Files to Create

1. `src/selectors/adaptive/services/dom_analyzer.py` - Main DOM analysis service
2. `tests/unit/selectors/adaptive/services/test_dom_analyzer.py` - Service tests

### Files to Modify

1. `src/selectors/adaptive/services/__init__.py` - Export new service

---

## 8. Quick Start for Implementation

### Step 1: Create DOM Analyzer Service
Create `src/selectors/adaptive/services/dom_analyzer.py` with:
- StrategyType enum
- AlternativeSelector dataclass
- DOMAnalyzer class with analyze_snapshot method

### Step 2: Implement Each Strategy
Add methods for each of the 6 strategies:
- _analyze_css
- _analyze_xpath
- _analyze_text_anchor
- _analyze_attribute_match
- _analyze_dom_relationship
- _analyze_role_based

### Step 3: Integrate with Snapshot
Load HTML from snapshot using SnapshotRepository

### Step 4: Add Tests
Create unit tests for each strategy and integration test

---

# ARCHITECTURE COMPLIANCE

## From Architecture Document

**Technology Stack:**
- ✅ Uses BeautifulSoup4/lxml for HTML parsing (industry standard)
- ✅ Follows async patterns from existing code
- ✅ Uses repository pattern for data access

**Code Organization:**
- ✅ New service in `src/selectors/adaptive/services/`
- ✅ Follows naming conventions (snake_case, PascalCase)
- ✅ Uses dataclasses for data structures

**Integration Points:**
- ✅ Uses existing Snapshot model from Story 2.2
- ✅ Uses existing FailureEvent from Story 2.1/2.3
- ✅ Prepares for Story 3.2 and 3.3 handoff

## Previous Story Learnings

From Story 2.3 (most recent completed):
- Use async repository pattern consistently
- Include comprehensive docstrings
- Add type hints throughout
- Return empty collections rather than None
- Handle exceptions gracefully at service boundary
