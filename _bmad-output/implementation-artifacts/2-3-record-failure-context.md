# Story 2.3: Record Failure Context

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **System**,
I want to record comprehensive failure context
So that failures can be analyzed and proposed fixes can be evaluated.

## Acceptance Criteria

1. **Given** a selector failure
   **When** the failure is recorded
   **Then** it should capture: sport, page state, tab type, previous selector strategy used, confidence score at time of failure

2. **Given** failure context is recorded
   **When** querying failures
   **Then** the context should be filterable by sport, date range, selector type

3. **Given** failure events from Story 2.1
   **When** this story integrates
   **Then** the failure should include comprehensive context data

4. **Given** stored failure context
   **When** analyzed for patterns
   **Then** it should support aggregation by sport/site/error_type

## Tasks / Subtasks

- [x] Task 1: Extend FailureEvent model with context fields (AC: #1)
  - [x] Subtask 1.1: Add sport, page_state, tab_type fields to FailureEvent
  - [x] Subtask 1.2: Add previous_strategy_used, confidence_score_at_failure fields
  - [x] Subtask 1.3: Create database migration for new fields

- [x] Task 2: Create failure context capture service (AC: #1)
  - [x] Subtask 2.1: Create FailureContextService class
  - [x] Subtask 2.2: Implement context extraction from page state
  - [x] Subtask 2.3: Integrate with Story 2.1's failure detection

- [x] Task 3: Add filtering and query capabilities (AC: #2)
  - [x] Subtask 3.1: Add query filters to FailureEventRepository
  - [x] Subtask 3.2: Support filtering by sport, date range, selector type
  - [x] Subtask 3.3: Add aggregation queries for pattern analysis

- [x] Task 4: Add context to API endpoints (AC: #2)
  - [x] Subtask 4.1: Update GET /failures endpoint with context filters
  - [x] Subtask 4.2: Add context fields to failure detail response

- [x] Task 5: Add tests for failure context (AC: #4)
  - [x] Subtask 5.1: Unit tests for context extraction
  - [x] Subtask 5.2: Integration tests for filtering
  - [x] Subtask 5.3: Test aggregation queries

## Dev Notes

### Project Structure Notes

The failure context system extends the adaptive module from Epic 1 and builds on Epic 2 stories:
- **Module Location**: `src/selectors/adaptive/` (per architecture)
- **Existing Model**: `src/selectors/adaptive/db/models/recipe.py` - Recipe SQLAlchemy model
- **Existing Service**: `src/selectors/adaptive/services/stability_scoring.py` - StabilityScoringService
- **Event System**: Uses existing `src/observability/events.py` - `publish_selector_failed()`

**Key Files to Create/Modify:**
- `src/selectors/adaptive/db/models/failure_event.py` - Extend with context fields (or create new if 2.1 created it)
- `src/selectors/adaptive/db/repositories/failure_event_repository.py` - Add query filters
- `src/selectors/adaptive/services/failure_context.py` - NEW: Context capture service

**Naming Conventions:**
- Python: `snake_case` for variables/functions
- SQLAlchemy Models: `PascalCase` for class names
- Database Tables: `snake_case` plural (e.g., `failure_events`)
- Service Classes: `PascalCase` (e.g., `FailureContextService`)

### References

- [Source: _bmad-output/planning-artifacts/epics.md#255-270] - Story requirements with BDD acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#155-160] - Tables Required: snapshots, recipes
- [Source: _bmad-output/planning-artifacts/architecture.md#218-227] - Code Organization: New module under `src/selectors/adaptive/`
- [Source: _bmad-output/implementation-artifacts/2-1-detect-selector-resolution-failures.md] - Story 2.1 (failure detection)
- [Source: _bmad-output/implementation-artifacts/2-2-capture-dom-snapshot-at-failure.md] - Story 2.2 (snapshot capture)

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

- Extended FailureEvent model with new context fields
- Created FailureContextService for capturing page context
- Added filtering and aggregation methods to repository

### Completion Notes List

- ✅ Implemented context fields in FailureEvent model (sport, page_state, tab_type, previous_strategy_used, confidence_score_at_failure)
- ✅ Created FailureContextService with page context capture capabilities
- ✅ Added find_with_filters() method with support for sport, date range, selector type, error type, tab_type, site
- ✅ Added aggregation methods: aggregate_by_sport(), aggregate_by_error_type(), aggregate_by_site()
- ✅ Added get_failure_trend() for time-based analysis
- ✅ Added comprehensive tests for new functionality
- ✅ All 35 tests pass

### File List

**Modified:**
- src/selectors/adaptive/db/models/failure_event.py
- src/selectors/adaptive/db/repositories/failure_event_repository.py
- src/selectors/adaptive/services/__init__.py

**Created:**
- src/selectors/adaptive/services/failure_context.py

**Tests Modified:**
- tests/unit/selectors/adaptive/db/test_failure_event_model.py
- tests/unit/selectors/adaptive/db/test_failure_event_repository.py

## Change Log

- 2026-03-03: Implemented story 2-3-record-failure-context - Added context fields to FailureEvent, created FailureContextService, added filtering/aggregation methods (Tisone)

---

# Comprehensive Story Context for Implementation

## 1. Story Foundation

### Epic Context (Epic 2: Failure Detection & Capture)

Epic 2 builds on Epic 1's foundation (recipe versioning, stability scoring) to detect selector failures and capture diagnostic data. This story (2.3) is the third and final story in Epic 2:

- **Story 2.1**: Detect Selector Resolution Failures (status: ready-for-dev)
- **Story 2.2**: Capture DOM Snapshot at Failure (status: ready-for-dev)
- **Story 2.3**: Record Failure Context (THIS STORY - backlog)

**Epic 2 Goal**: Detect when selectors fail during extraction, capture DOM snapshots, and record failure context.

### Dependencies

- **Prerequisite**: Story 2.1 (Detect Selector Resolution Failures) - provides failure event structure
- **Prerequisite**: Story 2.2 (Capture DOM Snapshot) - provides snapshot data to enrich context
- **Blocked by**: Story 1.3 (Recipe Stability Scoring) - provides the adaptive module structure

### Business Value

Comprehensive failure context enables:
- Pattern analysis across failures (by sport, site, selector type)
- Better proposal engine inputs (Epic 3)
- Learning system data (Epic 5)
- Audit trail for debugging

---

## 2. Technical Foundation

### Architecture Requirements (from architecture.md)

**Technology Stack:**
- Database: SQLite (MVP) with SQLAlchemy 2.0 async
- Backend: FastAPI
- Browser Automation: Playwright
- Storage: File system for HTML content + database for metadata

**Tables Required (from architecture.md):**
- failure```
_events - Already created in Story 2.1, extend with context fields
- snapshots - Created in Story 2.2
```

**API Endpoints Required:**
- `GET /failures` - List failures with filters
- `GET /failures/{id}` - Get failure details with context

### Code Structure (from architecture.md)

```
src/
├── selectors/
│   ├── adaptive/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   ├── schemas/
│   │   │   └── dependencies/
│   │   ├── db/
│   │   │   ├── models/
│   │   │   │   ├── recipe.py (exists)
│   │   │   │   ├── failure_event.py (Story 2.1)
│   │   │   │   └── snapshot.py (Story 2.2)
│   │   │   └── repositories/
│   │   │       ├── recipe_repository.py (exists)
│   │   │       ├── failure_event_repository.py (Story 2.1)
│   │   │       └── snapshot_repository.py (Story 2.2)
│   │   ├── services/
│   │   │   ├── stability_scoring.py (exists)
│   │   │   ├── failure_detector.py (Story 2.1)
│   │   │   ├── snapshot_capture.py (Story 2.2)
│   │   │   └── failure_context.py (THIS STORY)
│   │   └── config/
```

### Existing Code to Reference

**Already Implemented (Epic 1):**
- `src/selectors/adaptive/db/models/recipe.py` - SQLAlchemy model pattern
- `src/selectors/adaptive/db/repositories/recipe_repository.py` - Repository pattern with async SQLAlchemy
- `src/selectors/adaptive/services/stability_scoring.py` - StabilityScoringService

**Story 2.1 (ready-for-dev):**
- `src/selectors/adaptive/db/models/failure_event.py` - FailureEvent model with base fields
- `src/selectors/adaptive/db/repositories/failure_event_repository.py` - FailureEvent CRUD
- `src/selectors/adaptive/services/failure_detector.py` - FailureDetectorService

**Story 2.2 (ready-for-dev):**
- `src/selectors/adaptive/db/models/snapshot.py` - Snapshot model
- `src/selectors/adaptive/db/repositories/snapshot_repository.py` - Snapshot repository
- `src/selectors/adaptive/services/snapshot_capture.py` - Snapshot capture service

---

## 3. Developer Implementation Guardrails

### Critical Requirements

1. **DO NOT DUPLICATE STORAGE**: Story 2.1 already created the failure_events table
   - Extend the existing FailureEvent model with new context fields
   - Add migration for new columns

2. **FOLLOW EXISTING MODEL PATTERNS**: Use `src/selectors/adaptive/db/models/recipe.py` as template
   - SQLAlchemy 2.0 async models
   - Use `Base` from `src/selectors/adaptive/db/base.py`
   - Include proper typing and Pydantic schemas

3. **INTEGRATE WITH STORIES 2.1 AND 2.2**:
   - Story 2.1 provides the failure event trigger
   - Story 2.2 provides the snapshot reference
   - This story enriches with context data

4. **CONTEXT FIELDS ARE CRITICAL**:
   - `sport` - Sport context (from page context)
   - `page_state` - State of the page at failure time
   - `tab_type` - Type of tab being extracted
   - `previous_strategy_used` - Strategy that was attempted before failure
   - `confidence_score_at_failure` - Confidence at time of failure

5. **ASYNC PATTERNS**:
   - All database operations must be async
   - Use `async with` for session management
   - Follow the repository pattern from `recipe_repository.py`

### Testing Standards

- Unit tests in `tests/unit/selectors/adaptive/services/`
- Repository tests in `tests/unit/selectors/adaptive/db/`
- Follow existing test patterns from `test_recipe_repository.py`

### Naming Conventions

- Python: snake_case (functions, variables)
- Database: snake_case (tables, columns)
- API: RESTful plural nouns (`/failures`)
- Files: snake_case.py

---

## 4. Acceptance Criteria Deep Dive

### AC1: Capture Comprehensive Failure Context

**Implementation Approach:**

1. **ExtendEvent Model**:
 Failure   ```python
   # Extend existing FailureEvent with new fields
   class FailureEvent(Base):
       # Existing fields from Story 2.1...
       
       # NEW: Context fields
       sport: Mapped[str] = mapped_column(String(50), nullable=True)
       page_state: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
       tab_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
       previous_strategy_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
       confidence_score_at_failure: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
   ```

2. **Context Extraction Service**:
   ```python
   class FailureContextService:
       """Service for capturing and enriching failure context."""
       
       async def capture_context(
           self,
           failure_event: FailureEvent,
           page_context: PageContext,
           selector_config: SelectorConfig,
       ) -> FailureEvent:
           """Enrich failure event with context data."""
           
           # Extract sport from page context
           failure_event.sport = page_context.sport
           
           # Capture page state (scroll position, loaded content, etc.)
           failure_event.page_state = await self._capture_page_state(page)
           
           # Get tab type from configuration
           failure_event.tab_type = page_context.tab_type
           
           # Previous strategy used
           failure_event.previous_strategy_used = selector_config.strategy_used
           
           # Confidence score at time of failure
           failure_event.confidence_score_at_failure = selector_config.confidence_score
           
           return failure_event
   ```

### AC2: Filterable Context

**Required Query Filters:**
- `sport` - Filter by sport name
- `date_from` / `date_to` - Filter by date range
- `selector_type` - Filter by selector type
- `error_type` - Filter by error type (from Story 2.1)

**Repository Methods:**
```python
class FailureEventRepository:
    async def find_with_filters(
        self,
        sport: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        selector_type: Optional[str] = None,
        error_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FailureEvent]:
        """Query failures with filters."""
        
    async def aggregate_by_sport(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Aggregate failures by sport."""
        
    async def aggregate_by_error_type(
        self,
        sport: Optional[str] = None,
    ) -> Dict[str, int]:
        """Aggregate failures by error type."""
```

### AC3: Integration with Stories 2.1 and 2.2

**Integration Flow:**

1. **Story 2.1** triggers failure detection → creates FailureEvent
2. **Story 2.2** captures DOM snapshot → links snapshot to FailureEvent
3. **This Story (2.3)** enriches with context → adds sport, page_state, tab_type, etc.

**Data Flow:**
```
Selector Engine Failure
    ↓
Story 2.1: FailureDetectorService
    → Creates FailureEvent (base fields)
    ↓
Story 2.2: SnapshotCaptureService  
    → Links snapshot to FailureEvent
    ↓
Story 2.3: FailureContextService (THIS STORY)
    → Enriches with context fields
    → Updates in database
```

### AC4: Pattern Analysis Support

**Aggregation Queries:**
```python
# Get failure counts by sport
SELECT sport, COUNT(*) as count 
FROM failure_events 
GROUP BY sport;

# Get failure counts by sport and error type
SELECT sport, error_type, COUNT(*) as count 
FROM failure_events 
GROUP BY sport, error_type;

# Get failure trend over time
SELECT DATE(timestamp) as date, COUNT(*) as count 
FROM failure_events 
GROUP BY DATE(timestamp);
```

---

## 5. Integration Points

### With Story 2.1 (Failure Detection)

- **Input**: Base FailureEvent with selector_id, sport, site, timestamp, error_type
- **Enhancement**: Add context fields (page_state, tab_type, previous_strategy, confidence_score)
- **Output**: Enriched FailureEvent with comprehensive context

### With Story 2.2 (Snapshot Capture)

- **Input**: Snapshot reference linked to FailureEvent
- **Integration**: Context should reference snapshot_id for full analysis
- **Output**: Full picture of failure: event + snapshot + context

### With Epic 3 (Proposal Engine)

- **Input**: Comprehensive failure data including context
- **Usage**: 
  - Analyze patterns by sport for better proposals
  - Use confidence_score_at_failure to weight proposals
  - Use previous_strategy_used to avoid same approach

### With Epic 5 (Learning System)

- **Input**: Context data for learning
- **Usage**:
  - Track which selectors fail more in specific sports
  - Learn from tab_type patterns
  - Use page_state for pattern detection

---

## 6. Edge Cases to Handle

1. **Missing page context**: What if sport/site is not available in context?
2. **Partial context**: Some fields may be None - handle gracefully
3. **Large page_state**: JSON may be large - consider truncation
4. **Historical data**: How to backfill context for old failures?
5. **Concurrent failures**: Multiple failures at same time - handle race conditions

---

## 7. File Checklist

### New Files to Create

1. `src/selectors/adaptive/services/failure_context.py` - Context capture service
2. `tests/unit/selectors/adaptive/services/test_failure_context.py` - Service tests

### Files to Modify

1. `src/selectors/adaptive/db/models/failure_event.py` - Add context fields (if Story 2.1 created it)
2. `src/selectors/adaptive/db/repositories/failure_event_repository.py` - Add query filters
3. `src/selectors/adaptive/db/models/__init__.py` - Export updated model
4. `src/selectors/adaptive/db/repositories/__init__.py` - Export updated repository
5. `src/selectors/adaptive/services/__init__.py` - Export new service

---

## 8. Questions for Developer

1. Should context be captured synchronously or asynchronously?
2. What is the maximum size for page_state JSON?
3. Should we backfill context for existing failures?
4. How to handle missing confidence_score - default to 0.5?
5. Do we need to store page_state in a separate table for large content?

---

## 9. Quick Start for Implementation

### Step 1: Extend FailureEvent Model
Check if Story 2.1 created failure_event.py, add new context fields

### Step 2: Add Migration
Create Alembic or SQL migration for new columns

### Step 3: Update Repository
Add query filter methods to FailureEventRepository

### Step 4: Create Context Service
Create FailureContextService to capture and enrich context

### Step 5: Update API
Add context fields to API responses, add filter parameters

### Step 6: Add Tests
- Test context extraction
- Test query filters
- Test aggregation queries

---

# ARCHITECTURE COMPLIANCE

### From Architecture Document

**Key Architectural Decisions:**
- [Architecture: _bmad-output/planning-artifacts/architecture.md#155-160] - Tables Required: snapshots, recipes, failure_events
- [Architecture: _bmad-output/planning-artifacts/architecture.md#218-227] - Code Organization: New module under `src/selectors/adaptive/`
- [Architecture: _bmad-output/planning-artifacts/architecture.md#151-153] - Database: SQLite (MVP), ORM: SQLAlchemy 2.0
- [Architecture: _bmad-output/planning-artifacts/architecture.md#219] - Python: `snake_case` functions/variables

**Integration Points:**
- Must integrate with Story 2.1's FailureEvent model
- Must integrate with Story 2.2's Snapshot model
- Must provide context for Epic 3 (Proposal Engine)
- Must provide data for Epic 5 (Learning System)

### Technical Stack Constraints

- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0 with async support
- **Database**: SQLite (MVP)
- **Event Handling**: Existing scrapemoja event system (`src/observability/events.py`)

---

# TECHNICAL REQUIREMENTS

### Failure Context Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sport` | String | No | Sport context (from page context) |
| `page_state` | JSON | No | State of the page at failure time |
| `tab_type` | String | No | Type of tab being extracted |
| `previous_strategy_used` | String | No | Strategy that was attempted before failure |
| `confidence_score_at_failure` | Float | No | Confidence score at time of failure |

### Service Interface: FailureContextService

```python
class FailureContextService:
    """Service for capturing and enriching failure context."""
    
    def __init__(self, failure_repository, snapshot_repository):
        self.repository = failure_repository
        self.snapshot_repository = snapshot_repository
    
    async def capture_context(
        self,
        failure_event: FailureEvent,
        page_context: PageContext,
        selector_config: SelectorConfig,
    ) -> FailureEvent:
        """Capture and enrich failure event with context data."""
    
    async def update_failure_context(
        self,
        failure_id: int,
        context_data: FailureContextData,
    ) -> FailureEvent:
        """Update existing failure with context data."""
    
    async def get_failure_with_context(
        self,
        failure_id: int,
    ) -> FailureEvent:
        """Retrieve failure event with all context data."""
```

### Query Interface: FailureEventRepository (Extensions)

```python
class FailureEventRepository:
    # Existing methods from Story 2.1...
    
    async def find_with_filters(
        self,
        sport: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        selector_type: Optional[str] = None,
        error_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FailureEvent]:
        """Query failures with context filters."""
    
    async def aggregate_by_sport(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Aggregate failures by sport."""
    
    async def aggregate_by_error_type(
        self,
        sport: Optional[str] = None,
    ) -> Dict[str, int]:
        """Aggregate failures by error type."""
```

---

# LIBRARY FRAMEWORK REQUIREMENTS

### Existing Dependencies

- **SQLAlchemy 2.0+**: Already added in Epic 1
- **Python 3.11+**: Using dataclasses and modern Python features
- **PyYAML**: Already in project
- **Playwright**: Already in project for browser automation

### No New Dependencies Required

This story extends existing functionality using the existing event system and does not require new external dependencies.

---

# FILE STRUCTURE REQUIREMENTS

### Directory Structure

```
src/selectors/adaptive/
├── __init__.py
├── db/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── recipe.py           # EXISTING
│   │   ├── failure_event.py    # Story 2.1 - Extend with context
│   │   └── snapshot.py         # Story 2.2
│   └── repositories/
│       ├── __init__.py
│       ├── recipe_repository.py     # EXISTING
│       ├── failure_event_repository.py  # Story 2.1 - Add query filters
│       └── snapshot_repository.py   # Story 2.2
├── services/
│   ├── __init__.py
│   ├── stability_scoring.py    # EXISTING
│   ├── failure_detector.py     # Story 2.1
│   ├── snapshot_capture.py     # Story 2.2
│   └── failure_context.py      # NEW - Context capture service
└── config/
```

### Test File Location

- `tests/unit/selectors/adaptive/services/test_failure_context.py` - Service tests

---

# TESTING REQUIREMENTS

### Unit Tests

1. **FailureContextService**
   - Test context extraction from page context
   - Test context enrichment
   - Test handling of missing context fields

2. **FailureEventRepository**
   - Test query filters (sport, date range, selector type)
   - Test aggregation queries
   - Test pagination

### Integration Tests

1. **Context Capture Flow**
   - Simulate failure event
   - Verify context is captured and stored
   - Verify context is queryable

2. **End-to-End Flow**
   - Test full flow from Story 2.1 → 2.2 → 2.3
   - Verify all data is linked correctly

---

# PREVIOUS STORY INTELLIGENCE

### From Epic 1 (Foundation Complete)

**Key Learnings from Epic 1:**

- **Story 1.1**: Extended ConfigurationMetadata with recipe_id, stability_score, generation, parent_recipe_id
- **Story 1.2**: Created Recipe model and RecipeRepository with SQLite
- **Story 1.3**: Implemented StabilityScoringService with on_selector_failure() method

**Files Created in Epic 1:**
- `src/selectors/adaptive/db/models/recipe.py` - Recipe model
- `src/selectors/adaptive/db/repositories/recipe_repository.py` - Recipe CRUD
- `src/selectors/adaptive/services/stability_scoring.py` - StabilityScoringService

### From Epic 2 Stories

**Story 2.1 (ready-for-dev):**
- Created FailureEvent model with base fields
- Created FailureDetectorService
- Created FailureEventRepository with CRUD operations

**Story 2.2 (ready-for-dev):**
- Created Snapshot model
- Created SnapshotCaptureService
- Integrated with failure detection

**This Story (2.3) Builds On:**
- Epic 1's database infrastructure
- Story 2.1's FailureEvent model (extend with context)
- Story 2.2's Snapshot integration

### Epic 1 Retrospective Insights

From [epic-1-retro-2026-03-03.md]:
- Ensure backward compatibility with existing configs
- Keep services focused and single-purpose
- Use async/await properly for event handling
- Write comprehensive tests early

---

# LATEST TECH INFORMATION

### Event-Driven Architecture Best Practices

1. **Context Enrichment**: Capture context at failure time, not later
2. **Graceful Degradation**: If context capture fails, log and continue with base event
3. **Performance**: Context queries should use indexes on sport, timestamp
4. **Logging**: Log all context capture attempts for debugging

### SQLAlchemy Considerations

- Use `AsyncSession` for async database operations
- Consider using `event.listen` for automatic timestamp updates
- Use proper indexes on frequently queried columns (sport, timestamp, error_type)

### Future Extensibility

- **Epic 3**: Alternative selector proposal will use context for better proposals
- **Epic 5**: Learning system will analyze context patterns
- **Epic 6**: Audit logging will reference failure context

---

# PROJECT CONTEXT REFERENCE

### From PRD

- [PRD: _bmad-output/planning-artifacts/prd.md] - Full requirements for adaptive selector system
- FR1: System can detect when a selector fails during extraction
- FR2: System captures DOM snapshot at time of failure
- FR3: System records failure context (sport, status, page state)

### From Architecture

- [Architecture: _bmad-output/planning-artifacts/architecture.md#155-160] - Tables Required: snapshots, recipes, failure_events
- [Architecture: _bmad-output/planning-artifacts/architecture.md#218-227] - Code Organization: New module under `src/selectors/adaptive/`
- [Architecture: _bmad-output/planning-artifacts/architecture.md#261-269] - Integration Points: Selector Engine, Snapshot System

### From Epic 2

- [Epic 2: _bmad-output/planning-artifacts/epics.md#215-270] - Failure Detection & Capture
- **Story 2.1**: Detect Selector Resolution Failures (ready-for-dev)
- **Story 2.2**: Capture DOM Snapshot at Failure (ready-for-dev)
- **Story 2.3**: Record Failure Context (THIS STORY - backlog)

### Dependencies Note

**Epic 1 is COMPLETE** - The following are available:
- Recipe model with stability tracking
- RecipeRepository with CRUD operations
- StabilityScoringService with on_selector_failure() method
- Database infrastructure with SQLite

**Epic 2 Stories Available:**
- Story 2.1: FailureEvent model, FailureDetectorService, FailureEventRepository
- Story 2.2: Snapshot model, SnapshotCaptureService, SnapshotRepository

**Integration Points:**
- Subscribe to existing `selector.failed` events from `src/observability/events.py`
- Call `stability_service.on_selector_failure(recipe_id, selector_id, severity)`
- Link snapshots from Story 2.2 to failure events

---

# STORY COMPLETION STATUS

- **Status**: ready-for-dev
- **Epic**: 2 (Failure Detection & Capture)
- **Story Key**: 2-3-record-failure-context
- **Dependencies**: 
  - Epic 1 Complete (Recipe model, StabilityScoringService available)
  - Story 2.1 Complete (FailureEvent model, FailureDetectorService available)
  - Story 2.2 Complete (Snapshot model, SnapshotCaptureService available)
- **Next Stories in Epic 2**: 
  - (All stories in Epic 2 will be complete after this)
- **Next Epic**: Epic 3 - Alternative Selector Proposal

---
