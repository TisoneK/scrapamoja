# Story 3.3: Calculate Blast Radius

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **System**,
I want to calculate the blast radius for each proposed fix
So that users understand the impact of approving a selector change.

## Acceptance Criteria

1. **Given** a proposed selector fix
   **When** blast radius is calculated
   **Then** it should identify all selectors that share ancestor containers with the proposed selector
   **And** the blast radius should indicate: how many selectors might be affected, which sports might be impacted

2. **Given** blast radius information
   **When** displayed in the UI
   **Then** it should clearly show: affected selector count, affected sports, severity level

## Tasks / Subtasks

- [x] Task 1: Create BlastRadius Calculator Service (AC: #1)
  - [x] Subtask 1.1: Design BlastRadius dataclass with all impact metrics
  - [x] Subtask 1.2: Implement ancestor container detection algorithm
  - [x] Subtask 1.3: Implement selector impact analysis
  - [x] Subtask 1.4: Implement sport/impact correlation
  - [x] Subtask 1.5: Implement severity level calculation

- [x] Task 2: Integrate with Selector Analysis (AC: #1)
  - [x] Subtask 2.1: Connect to AlternativeSelector from Story 3.1/3.2
  - [x] Subtask 2.2: Use DOM snapshot for container analysis
  - [x] Subtask 2.3: Query recipe configurations for affected selectors

- [x] Task 3: Add UI Data Structures (AC: #2)
  - [x] Subtask 3.1: Implement BlastRadiusResult with UI-friendly fields
  - [x] Subtask 3.2: Add severity categorization (low/medium/high/critical)
  - [x] Subtask 3.3: Add sorting by severity

- [x] Task 4: Add Tests (AC: #1, #2)
  - [x] Subtask 4.1: Unit tests for blast radius calculation
  - [x] Subtask 4.2: Integration test with DOM analyzer
  - [x] Subtask 4.3: Test edge cases (no shared ancestors, all selectors affected)

## Dev Notes

### Project Structure Notes

- **Module Location**: `src/selectors/adaptive/` (per architecture)
- **New Service**: `src/selectors/adaptive/services/blast_radius.py` - Blast radius calculation service
- **Extend**: `src/selectors/adaptive/services/dom_analyzer.py` from Story 3.1
- **Existing Dependencies**:
  - `src/selectors/adaptive/services/dom_analyzer.py` - AlternativeSelector (Story 3.1)
  - `src/selectors/adaptive/services/confidence_scorer.py` - ConfidenceScorer (Story 3.2)
  - `src/selectors/adaptive/db/models/snapshot.py` - Snapshot model (Story 2.2)
  - `src/selectors/adaptive/db/models/recipe.py` - Recipe model (Epic 1)

**Naming Conventions:**
- Python: `snake_case` for variables/functions
- Service Classes: `PascalCase` (e.g., `BlastRadiusCalculator`)
- Severity Levels: lowercase enum values (e.g., `low`, `medium`, `high`, `critical`)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#310-326] - Story requirements with BDD acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#218-227] - Code Organization: New module under `src/selectors/adaptive/`
- [Source: _bmad-output/implementation-artifacts/3-1-analyze-dom-structure.md] - Story 3.1 (DOM Analysis)
- [Source: _bmad-output/implementation-artifacts/3-2-generate-confidence-scores.md] - Story 3.2 (Confidence Scoring)

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

- **Implemented BlastRadiusCalculator Service** in `src/selectors/adaptive/services/blast_radius.py`
- **Implemented severity levels**: LOW, MEDIUM, HIGH, CRITICAL based on affected selector count and sports
- **Implemented ancestor container detection algorithm** using BeautifulSoup for DOM analysis
- **Implemented selector impact analysis** to find affected selectors sharing ancestor containers
- **Implemented UI-friendly BlastRadiusUI** for display purposes with severity badges
- **Added comprehensive unit tests** in `tests/unit/selectors/adaptive/services/test_blast_radius.py`
- **All 92+ tests pass** including the 26 new blast radius tests

### Code Review Fixes (2026-03-04)

- **Extended AlternativeSelector** with `blast_radius_result` and `blast_radius_severity` fields
- **Added `to_dict()` methods** to `BlastRadiusResult` and `BlastRadiusUI` for serialization
- **Updated `to_dict()` in AlternativeSelector** to include blast radius fields in serialization

### File List

- `src/selectors/adaptive/services/blast_radius.py` (NEW)
- `src/selectors/adaptive/services/__init__.py` (MODIFIED - added exports)
- `tests/unit/selectors/adaptive/services/test_blast_radius.py` (NEW)

## Change Log

- 2026-03-04: Implemented Story 3.3 - Calculate Blast Radius
- 2026-03-04: Code review fixes - Extended AlternativeSelector with blast radius integration

---

# Comprehensive Story Context for Implementation

## 1. Story Foundation

### Epic Context (Epic 3: Alternative Selector Proposal)

Epic 3 builds on Epic 2's failure detection foundation to propose alternative selectors with confidence scores and blast radius:

- **Story 3.1**: Analyze DOM Structure (ready-for-dev)
- **Story 3.2**: Generate Confidence Scores (ready-for-dev)
- **Story 3.3**: Calculate Blast Radius (THIS STORY - backlog)

**Epic 3 Goal**: Analyze DOM structure and propose multiple alternative selector strategies with confidence scores and blast radius impact analysis.

### Dependencies

- **Prerequisite**: Story 3.1 (Analyze DOM Structure) - provides AlternativeSelector with selector strings
- **Prerequisite**: Story 3.2 (Generate Confidence Scores) - provides refined confidence scores
- **Prerequisite**: Story 2.2 (Capture DOM Snapshot) - provides HTML snapshots for DOM analysis
- **Prerequisite**: Epic 1 (Recipe Models) - provides Recipe model for querying configurations
- **Blocked by**: None - all prerequisites complete

### Business Value

Blast radius calculation enables:
- Users to understand the broader impact of selector changes
- Risk assessment before approving selector changes
- Prioritization of fixes based on impact scope
- Prevention of cascading failures from premature selector approvals

---

## 2. Technical Foundation

### Architecture Requirements (from architecture.md)

**Technology Stack:**
- Database: SQLite (MVP) with SQLAlchemy 2.0 async
- Backend: FastAPI
- HTML Parsing: BeautifulSoup4 or lxml
- Existing: DOMAnalyzer from Story 3.1, ConfidenceScorer from Story 3.2

**Code Structure (from architecture.md):**
```
src/
├── selectors/
│   ├── adaptive/
│   │   ├── services/
│   │   │   ├── blast_radius.py (NEW - THIS STORY)
│   │   │   ├── dom_analyzer.py (Story 3.1)
│   │   │   ├── confidence_scorer.py (Story 3.2)
│   │   │   ├── proposal_engine.py (Story 3.2 - combines analyzer + scorer)
```

### Previous Story Learnings

From Story 3.1 (Analyze DOM Structure):
- AlternativeSelector structure with selector_string, strategy_type, confidence_score
- Strategy types: CSS, XPATH, TEXT_ANCHOR, ATTRIBUTE_MATCH, DOM_RELATIONSHIP, ROLE_BASED
- DOMAnalyzer uses BeautifulSoup4/lxml for parsing

From Story 3.2 (Generate Confidence Scores):
- ConfidenceScorer with weighted scoring algorithm
- ConfidenceTier enum: HIGH (0.7-1.0), MEDIUM (0.4-0.69), LOW (0.0-0.39)
- Integration pattern: extend AlternativeSelector rather than replace

### Existing Code to Reference

**Story 3.1 (Ready for Dev):**
- `src/selectors/adaptive/services/dom_analyzer.py` - DOMAnalyzer with AlternativeSelector
- Strategy types: CSS, XPATH, TEXT_ANCHOR, ATTRIBUTE_MATCH, DOM_RELATIONSHIP, ROLE_BASED

**Story 3.2 (Ready for Dev):**
- `src/selectors/adaptive/services/confidence_scorer.py` - ConfidenceScorer with detailed scoring

**Epic 1 (Complete):**
- `src/selectors/adaptive/db/models/recipe.py` - Recipe model with version tracking
- `src/selectors/adaptive/services/stability_scoring.py` - StabilityScoring service pattern

---

## 3. Developer Implementation Guardrails

### Critical Requirements

1. **ANCESTOR CONTAINER DETECTION**: Must identify shared DOM ancestors
   - Parse DOM to find container elements
   - Compare proposed selector's ancestors with other selectors
   - Identify selectors sharing same parent/grandparent containers

2. **AFFECTED SELECTOR COUNT**: Per AC1
   - Count all selectors that might be impacted
   - Consider both same-sport and cross-sport selectors
   - Factor in recipe inheritance (parent/child recipes)

3. **SPORT IMPACT ANALYSIS**: Per AC1
   - Map affected selectors to their sports
   - Provide breakdown by sport
   - Consider multi-sport selectors

4. **SEVERITY LEVELS**: Per AC2
   - LOW: 1-2 affected selectors, 1 sport
   - MEDIUM: 3-5 affected selectors, 2-3 sports
   - HIGH: 6-10 affected selectors, 4+ sports
   - CRITICAL: 10+ affected selectors or critical selectors affected

5. **BACKWARD COMPATIBILITY**:
   - Stories 3.1 and 3.2 code must work unchanged
   - Extend AlternativeSelector with blast_radius field
   - Handle missing historical data gracefully

### Testing Standards

- Unit tests in `tests/unit/selectors/adaptive/services/`
- Mock DOM snapshots for testing ancestor detection
- Test edge cases: no ancestors, all selectors shared, cross-recipe impacts

### Naming Conventions

- Python: snake_case (functions, variables)
- Service Classes: PascalCase
- Files: snake_case.py
- Severity Levels: lowercase enum

---

## 4. Acceptance Criteria Deep Dive

### AC1: Calculate Blast Radius (Affected Selectors + Sports)

**Implementation Approach:**

1. **BlastRadiusCalculator Service**:
   ```python
   from dataclasses import dataclass
   from enum import Enum
   from typing import Optional
   
   class SeverityLevel(Enum):
       LOW = "low"        # 1-2 affected, 1 sport
       MEDIUM = "medium"  # 3-5 affected, 2-3 sports
       HIGH = "high"      # 6-10 affected, 4+ sports
       CRITICAL = "critical"  # 10+ affected or critical
   
   @dataclass
   class AffectedSelector:
       selector_string: str
       recipe_id: int
       sport: str
       confidence_score: float
   
   @dataclass
   class BlastRadiusResult:
       proposed_selector: str
       affected_count: int
       affected_selectors: list[AffectedSelector]
       affected_sports: list[str]
       severity: SeverityLevel
       container_path: str  # Common ancestor path
   
   class BlastRadiusCalculator:
       """Service for calculating blast radius of proposed selector changes."""
       
       async def calculate_blast_radius(
           self,
           proposed_selector: AlternativeSelector,
           snapshot_id: int,
           sport: str,
       ) -> BlastRadiusResult:
           """Calculate the blast radius for a proposed selector change."""
           
           # 1. Load DOM snapshot
           snapshot = await self.snapshot_repo.get_by_id(snapshot_id)
           html = snapshot.html_content
           
           # 2. Find proposed selector's ancestors
           ancestors = self._find_ancestor_containers(html, proposed_selector.selector_string)
           
           # 3. Query all selectors in recipes
           all_selectors = await self.recipe_repo.get_all_selectors()
           
           # 4. Find affected selectors (share ancestors)
           affected = []
           for selector in all_selectors:
               if self._shares_ancestor(selector, ancestors):
                   affected.append(AffectedSelector(
                       selector_string=selector.selector_string,
                       recipe_id=selector.recipe_id,
                       sport=selector.sport,
                       confidence_score=selector.confidence_score,
                   ))
           
           # 5. Extract affected sports
           affected_sports = list(set(s.sport for s in affected))
           
           # 6. Calculate severity
           severity = self._calculate_severity(len(affected), len(affected_sports))
           
           return BlastRadiusResult(
               proposed_selector=proposed_selector.selector_string,
               affected_count=len(affected),
               affected_selectors=affected,
               affected_sports=affected_sports,
               severity=severity,
               container_path=ancestors[0] if ancestors else "",
           )
   ```

2. **Ancestor Container Detection**:
   ```python
   def _find_ancestor_containers(
       self,
       html: str,
       selector: str,
   ) -> list[str]:
       """Find ancestor containers of the target element."""
       soup = BeautifulSoup(html, 'lxml')
       target = soup.select_one(selector)
       
       if not target:
           return []
       
       ancestors = []
       current = target.parent
       
       # Go up to 5 levels (configurable)
       for _ in range(5):
           if current is None:
               break
           if current.name in ('div', 'section', 'article', 'main', 'nav', 'header', 'footer'):
               # Add identifiable attributes
               container_id = current.get('id', '')
               container_class = ' '.join(current.get('class', [])[:2])
               if container_id:
                   ancestors.append(f"#{container_id}")
               elif container_class:
                   ancestors.append(f".{container_class.replace(' ', '.')}")
           current = current.parent
       
       return ancestors
   ```

3. **Severity Calculation**:
   ```python
   def _calculate_severity(
       self,
       affected_count: int,
       sport_count: int,
   ) -> SeverityLevel:
       """Calculate severity based on affected count and sports."""
       
       # Critical: 10+ affected OR critical selectors
       if affected_count >= 10:
           return SeverityLevel.CRITICAL
       
       # High: 6-10 affected OR 4+ sports
       if affected_count >= 6 or sport_count >= 4:
           return SeverityLevel.HIGH
       
       # Medium: 3-5 affected OR 2-3 sports
       if affected_count >= 3 or sport_count >= 2:
           return SeverityLevel.MEDIUM
       
       # Low: 1-2 affected, 1 sport
       return SeverityLevel.LOW
   ```

### AC2: Display Blast Radius Information

**UI Data Structure**:
```python
@dataclass
class BlastRadiusUI:
    """UI-friendly blast radius representation."""
    
    proposed_selector: str
    severity_badge: str  # Color-coded: green/yellow/orange/red
    severity_label: str  # "Low", "Medium", "High", "Critical"
    affected_count: int
    affected_sports: list[str]
    affected_selectors_preview: list[str]  # Top 5 for display
    container_description: str  # Human-readable
```

---

## 5. Integration Points

### With Story 3.1 (DOM Analysis)

- **Input**: AlternativeSelector with selector_string from DOM analysis
- **Use**: DOM snapshot for ancestor detection
- **Output**: Enhanced AlternativeSelector with blast_radius field

### With Story 3.2 (Confidence Scoring)

- **Input**: AlternativeSelector with refined confidence scores
- **Use**: Confidence scores affected selectors
- for prioritizing **Output**: Combined analysis with both confidence and blast radius

### With Story 2.2 (Snapshot Capture)

- **Input**: snapshot_id for DOM analysis
- **Get**: HTML content for ancestor detection

### With Epic 1 (Recipe Models)

- **Input**: Recipe configurations for querying all selectors
- **Query**: All selectors to find affected ones

### With Epic 4 (Human Verification - Future)

- **Output**: Blast radius data for UI display
- **Hand-off**: UI will show severity badges and affected counts

---

## 6. Edge Cases to Handle

1. **No DOM Snapshot Available**: Return empty blast radius with LOW severity
2. **Invalid Selector Syntax**: Return error or skip with warning
3. **No Shared Ancestors**: Return 0 affected, LOW severity
4. **All Selectors Affected**: Return CRITICAL severity with full list
5. **Cross-Recipe Impact**: Consider parent/child recipe relationships
6. **Multi-Page Selectors**: Handle selectors used across multiple pages
7. **Very Deep DOM**: Limit ancestor traversal depth for performance

---

## 7. File Checklist

### New Files to Create

1. `src/selectors/adaptive/services/blast_radius.py` - Main blast radius calculation service
2. `tests/unit/selectors/adaptive/services/test_blast_radius.py` - Service tests

### Files to Modify

1. `src/selectors/adaptive/services/__init__.py` - Export new service
2. `src/selectors/adaptive/services/dom_analyzer.py` - Optionally integrate blast radius
3. `src/selectors/adaptive/services/confidence_scorer.py` - Optionally integrate blast radius

### Optional Integration

- Create `proposal_engine.py` to combine DOMAnalyzer + ConfidenceScorer + BlastRadiusCalculator (cleaner architecture for Epic 3)

---

## 8. Quick Start for Implementation

### Step 1: Create BlastRadiusCalculator Service
Create `src/selectors/adaptive/services/blast_radius.py` with:
- SeverityLevel enum
- AffectedSelector dataclass
- BlastRadiusResult dataclass
- BlastRadiusCalculator class with calculate_blast_radius method

### Step 2: Implement Ancestor Detection
Add methods:
- _find_ancestor_containers
- _shares_ancestor

### Step 3: Implement Severity Calculation
Add method:
- _calculate_severity

### Step 4: Add Tests
Create unit tests for blast radius calculation

---

# ARCHITECTURE COMPLIANCE

## From Architecture Document

**Technology Stack:**
- ✅ Uses BeautifulSoup4/lxml for HTML parsing (industry standard)
- ✅ Follows async patterns from existing code
- ✅ Uses repository pattern for data access
- ✅ Integrates with FastAPI (future Epic 4/7)

**Code Organization:**
- ✅ New service in `src/selectors/adaptive/services/`
- ✅ Follows naming conventions (snake_case, PascalCase)
- ✅ Uses dataclasses for data structures

**Integration Points:**
- ✅ Uses existing AlternativeSelector from Story 3.1
- ✅ Uses existing ConfidenceScorer from Story 3.2
- ✅ Uses existing Recipe model from Epic 1
- ✅ Prepares for Epic 4 (Human Verification) UI display

## Previous Story Learnings

From Story 3.2 (most recent completed):
- Use async repository pattern consistently
- Include comprehensive docstrings
- Add type hints throughout
- Return empty collections rather than None
- Handle exceptions gracefully at service boundary
- Extend data structures rather than replace

From Story 3.1:
- Use StrategyType enum for consistent strategy identification
- Include element_description for human readability
- Support multiple strategy types simultaneously

---

# PROJECT CONTEXT REFERENCE

## Critical Project Rules (from project-context.md)

1. **🔴 NEVER recreate existing frameworks**:
   - ❌ Don't create new HTML parsing → USE BeautifulSoup4/lxml
   - ❌ Don't create new async patterns → USE existing repository pattern
   - ❌ Don't bypass existing services

2. **Python Strict Mode**:
   - All functions must have type hints (mypy strict enabled)
   - No implicit optionals - use Optional[X] consistently
   - Always use async/await for I/O

3. **Naming Conventions**:
   - Classes: PascalCase
   - Functions/methods: snake_case
   - Files: snake_case.py

4. **Import Order**:
   - Standard library first
   - Third-party imports
   - Local imports

---

# LATEST TECHNICAL SPECIFICS

## Library Versions (from project-context.md)

- Python: 3.11+
- Playwright: 1.40.0+
- Pydantic: 2.5.0+
- SQLAlchemy: 2.0.0+
- BeautifulSoup4: 4.12.0+
- lxml: 4.9.0+

## Best Practices

- Use `async with` for resource management
- Always close browser contexts
- Set reasonable timeouts (default 30s)
- Use structlog for logging

---

# STORY COMPLETION STATUS

**Story**: 3.3 Calculate Blast Radius
**Epic**: 3 (Alternative Selector Proposal)
**Status**: ready-for-dev
**Created**: 2026-03-04

**Dependencies Status**:
- ✅ Story 3.1 (Analyze DOM Structure) - ready-for-dev
- ✅ Story 3.2 (Generate Confidence Scores) - ready-for-dev
- ✅ Story 2.2 (Capture DOM Snapshot) - done
- ✅ Epic 1 (Foundation) - done

**Next Stories**:
- Epic 3 is complete after this story
- Epic 4 (Human Verification Workflow) next
