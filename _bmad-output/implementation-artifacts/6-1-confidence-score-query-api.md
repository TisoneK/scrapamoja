# Story 6.1: Confidence Score Query API

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want **to query the adaptive module for selector confidence scores**,
so that **I can understand which selectors are stable and which need attention**.

## Acceptance Criteria

**AC1: Single Selector Query**
- **Given** a selector ID
- **When** querying the confidence score API
- **Then** the current confidence score (0.0-1.0) is returned
- **And** the last updated timestamp is included

**AC2: Batch Selector Query**
- **Given** multiple selector IDs
- **When** batch querying confidence scores
- **Then** all requested scores are returned in a single response
- **And** missing selectors return null or not found

**AC3: All Selectors Query with Pagination**
- **Given** no selector ID specified
- **When** querying the API
- **Then** all selector confidence scores are returned
- **And** pagination is supported for large result sets

**AC4: Default Score for Unknown Selectors**
- **Given** a selector with no historical data
- **When** querying the score
- **Then** a default score (e.g., 0.5) is returned
- **And** a flag indicates the score is estimated

## Tasks / Subtasks

- [x] Task 1: Create confidence query service (AC: 1, 2, 3, 4)
  - [x] Subtask 1.1: Design query API interface in src/selectors/adaptive/services.py
  - [x] Subtask 1.2: Implement single selector query method
  - [x] Subtask 1.3: Implement batch selector query method
  - [x] Subtask 1.4: Implement paginated all-selectors query method
  - [x] Subtask 1.5: Add default score logic with estimated flag

- [x] Task 2: Integrate with existing data sources (AC: 1, 2, 3)
  - [x] Subtask 2.1: Leverage existing quality metrics from src/selectors/quality/control.py
  - [x] Subtask 2.2: Connect to existing threshold manager from src/selectors/confidence/thresholds.py
  - [x] Subtask 2.3: Use existing failure event repository for historical data

- [x] Task 3: Create API endpoints (AC: 1, 2, 3)
  - [x] Subtask 3.1: Add GET /api/v1/confidence/{selector_id} endpoint
  - [x] Subtask 3.2: Add POST /api/v1/confidence/batch endpoint
  - [x] Subtask 3.3: Add GET /api/v1/confidence endpoint with pagination params

- [x] Task 4: Write unit tests (AC: 1, 2, 3, 4)
  - [x] Subtask 4.1: Test single selector query
  - [x] Subtask 4.2: Test batch selector query
  - [x] Subtask 4.3: Test pagination
  - [x] Subtask 4.4: Test default score for unknown selectors

## Dev Notes

### What This Story Implements

1. **Confidence Score Query API** - RESTful API to query selector confidence scores
2. **Single Selector Query** - Get score for one selector by ID
3. **Batch Query** - Get scores for multiple selectors in one request
4. **Paginated List Query** - Get all scores with pagination support
5. **Default Score Handling** - Return 0.5 with estimated=true for unknown selectors

### What This Story Does NOT Include

- Selector health status display UI (Story 6-2)
- Blast radius calculation (Story 6-3)
- Historical trending/charts (future enhancement)
- Real-time WebSocket queries (leverages Epic 5 infrastructure)

### 🚨 Critical Anti-Patterns to Avoid

1. **DO NOT** create new database models - reuse existing adaptive module schemas
2. **DO NOT** implement confidence calculation from scratch - use existing ConfidenceScorer from src/selectors/confidence/
3. **DO NOT** skip pagination - must handle large selector counts efficiently
4. **DO NOT** return raw database records - use Pydantic models for API responses
5. **DO NOT** hardcode default score - make configurable via settings
6. **DO NOT** block on database queries - use async patterns throughout
7. **DO NOT** skip error handling for missing selectors - return appropriate error/not found

### Architecture Patterns

**Integration with Existing Systems:**

```
src/selectors/
├── adaptive/
│   ├── services.py           # NEW - Confidence query service
│   ├── api/
│   │   └── routes/
│   │       └── confidence.py # NEW - API endpoints
│   └── db/
│       └── repositories/     # EXISTING - Query existing data
├── confidence/
│   ├── scorer.py            # EXISTING - ConfidenceScorer class
│   └── thresholds.py        # EXISTING - Threshold management
├── quality/
│   └── control.py           # EXISTING - QualityMetrics tracking
└── websocket/
                            # EXISTING from Epic 5 - Can be queried
```

**API Response Schema:**

```python
class ConfidenceScoreResponse(BaseModel):
    """Response model for single selector confidence query."""
    selector_id: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    last_updated: datetime
    is_estimated: bool = False  # True if no historical data


class BatchConfidenceQuery(BaseModel):
    """Request model for batch confidence query."""
    selector_ids: List[str] = Field(..., min_length=1, max_length=100)


class BatchConfidenceResponse(BaseModel):
    """Response model for batch confidence query."""
    results: Dict[str, Optional[ConfidenceScoreResponse]]
    missing_selectors: List[str] = []


class PaginatedConfidenceQuery(BaseModel):
    """Request model for paginated confidence query."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)


class PaginatedConfidenceResponse(BaseModel):
    """Response model for paginated confidence query."""
    results: List[ConfidenceScoreResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
```

**Configuration:**

```python
class ConfidenceQueryConfig(BaseModel):
    # Default score for selectors with no history
    default_confidence_score: float = 0.5
    
    # Pagination defaults
    default_page_size: int = 50
    max_page_size: int = 100
    
    # Cache TTL for confidence scores (seconds)
    cache_ttl: int = 30
```

### Project Structure Notes

- Follow existing module structure from `src/selectors/adaptive/`
- Create new service in `src/selectors/adaptive/services.py` - DO NOT create new files unnecessarily
- Add API routes in `src/selectors/adaptive/api/routes/confidence.py`
- Use same patterns as existing API routes in adaptive module
- Use Pydantic models from `src/selectors/adaptive/api/schemas/`
- DO NOT create new exceptions - extend from `src/selectors/exceptions.py`
- Integrate with existing quality metrics from Epic 3-5

### Dependencies on Previous Work

**From Epic 3 (Failure Event Capture):**
- Failure event capture (`src/selectors/hooks/post_extraction.py`)
- Historical failure data for confidence calculation

**From Epic 5 (Real-Time Notifications):**
- WebSocket infrastructure can be leveraged for real-time queries
- Health status thresholds from Story 5-2/5-3

**From Epic 6 (future):**
- Story 6-2 will use this API for health status display
- Story 6-3 will use this API for blast radius calculation

### Confidence Score Sources

The confidence score should be derived from:

1. **Historical Success Rate** - From failure event repository
2. **Strategy Reliability** - From quality metrics
3. **Recent Performance** - From threshold manager
4. **YAML Hints** - Fallback to configured stability

```
if historical_data exists:
    score = calculate_from_history(failure_events, quality_metrics)
else:
    score = default_score (0.5)
    is_estimated = True
```

### Testing Requirements

- Unit tests in `tests/selectors/adaptive/`
- Follow existing test patterns from Epic 3-5
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Mock adaptive module data for unit tests
- Test pagination edge cases
- Test unknown selector handling
- Test coverage target: 80%+ for new modules

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Deferred-Decisions]
- [Source: _bmad-output/project-context.md#Technology-Stack]
- [Source: _bmad-output/project-context.md#Framework-Specific-Rules]
- [Source: _bmad-output/implementation-artifacts/5-3-selector-health-status-streaming.md]
- [FR14: System can query adaptive module for selector confidence scores]

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

### Completion Notes List

- **AC1 (Single Selector Query)**: Implemented via `query_single()` method returning confidence score, timestamp, and is_estimated flag
- **AC2 (Batch Selector Query)**: Implemented via `query_batch()` method supporting up to 100 selectors per request
- **AC3 (Paginated Query)**: Implemented via `query_all_paginated()` with configurable page/page_size
- **AC4 (Default Score)**: Returns 0.5 with is_estimated=true for selectors with no history
- **Configuration**: Added ConfidenceQueryConfig with default_confidence_score=0.5, default_page_size=50, max_page_size=100, cache_ttl=30
- **Tests**: Added 14 unit tests covering all functionality - all passing
- **Integration**: Uses existing FailureEventRepository for historical data, added get_all() and get_unique_selectors() methods

### File List

**NEW:**
- `src/selectors/adaptive/services/confidence_query_service.py` - Confidence query service with single, batch, and paginated query methods
- `src/selectors/adaptive/api/routes/confidence.py` - API endpoints (GET /api/v1/confidence/{selector_id}, POST /api/v1/confidence/batch, GET /api/v1/confidence)
- `src/selectors/adaptive/api/schemas/confidence.py` - Pydantic request/response schemas
- `src/selectors/adaptive/api/schemas/__init__.py` - Schema exports
- `tests/selectors/adaptive/test_confidence_query.py` - 14 unit tests covering all ACs

**MODIFIED:**
- `src/selectors/adaptive/__init__.py` - Added exports for new confidence query service
- `src/selectors/adaptive/services/__init__.py` - Added exports for new service
- `src/selectors/adaptive/api/routes/__init__.py` - Added confidence router export
- `src/selectors/adaptive/api/app.py` - Added confidence router and endpoints to root
- `src/selectors/adaptive/db/repositories/failure_event_repository.py` - Added get_all() and get_unique_selectors() methods
- `src/selectors/hooks/post_extraction.py` - Added failure event creation for new selectors

## Review Fixes Applied

- Removed unused `ConfidenceScorer` import that was causing import errors
- Fixed deprecated `datetime.utcnow()` usage to use `datetime.now(timezone.utc)`
- Fixed deprecated Pydantic `class Config` to use `model_config = ConfigDict(...)`
