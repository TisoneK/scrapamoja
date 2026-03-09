# Story 6.2: Selector Health Status Display

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to display selector health status**,
so that **I can quickly see which selectors are working, degraded, or failed**.

## Acceptance Criteria

**AC1: Health Status Calculation**
- **Given** a selector's confidence score
- **When** calculating health status
- **Then** the status is determined by thresholds:
  - `healthy` if confidence_score ≥ 0.8
  - `degraded` if 0.5 ≤ confidence_score < 0.8
  - `failed` if confidence_score < 0.5
- **And** status is calculated based on recent confidence score

**AC2: Dashboard Display**
- **Given** a dashboard request
- **When** displaying selector health
- **Then** all selectors are grouped by status (healthy, degraded, failed)
- **And** the display shows: selector_id, status, confidence_score, last_failure

**AC3: Recommended Actions**
- **Given** a degraded or failed selector
- **When** displaying health
- **Then** recommended action is shown based on status:
  - degraded: "Consider reviewing selector - moderate failure rate"
  - failed: "Selector requires immediate attention - high failure rate"
- **And** any available alternative selectors are suggested (from YAML hints or adaptive module)

**AC4: Real-Time Updates**
- **Given** a WebSocket connection is active
- **When** health status changes
- **Then** changes are pushed immediately via WebSocket
- **And** the dashboard auto-updates without refresh
- **Note:** Leverages existing WebSocket infrastructure from Epic 5

## Tasks / Subtasks

- [x] Task 1: Create health status calculation service (AC: 1)
  - [x] Subtask 1.1: Design health status enum and thresholds in src/selectors/adaptive/services/
  - [x] Subtask 1.2: Implement health status calculation from confidence score
  - [x] Subtask 1.3: Add last_failure timestamp retrieval

- [x] Task 2: Create health display API endpoints (AC: 2)
  - [x] Subtask 2.1: Add GET /api/v1/health endpoint returning all selectors grouped by status
  - [x] Subtask 2.2: Add GET /api/v1/health/{selector_id} endpoint for single selector
  - [x] Subtask 2.3: Implement grouping logic for dashboard display

- [x] Task 3: Implement recommended actions (AC: 3)
  - [x] Subtask 3.1: Create recommendation engine based on health status
  - [x] Subtask 3.2: Integrate alternative selector lookup from YAML hints
  - [x] Subtask 3.3: Add alternatives suggestion to API response

- [x] Task 4: Integrate with WebSocket for real-time updates (AC: 4)
  - [x] Subtask 4.1: Leverage existing WebSocket from Story 5-3
  - [x] Subtask 4.2: Add health status change notification to WebSocket
  - [x] Subtask 4.3: Ensure auto-update behavior in dashboard

- [x] Task 5: Write unit tests (AC: 1, 2, 3, 4)
  - [x] Subtask 5.1: Test health status calculation for all thresholds
  - [x] Subtask 5.2: Test dashboard grouping
  - [x] Subtask 5.3: Test recommended actions
  - [x] Subtask 5.4: Test WebSocket integration

## Dev Notes

### What This Story Implements

1. **Health Status Calculation** - Transform confidence scores to health status using thresholds
2. **Health Dashboard API** - RESTful API to get all selectors grouped by health
3. **Recommended Actions** - Actionable recommendations based on selector health
4. **Real-Time Updates** - WebSocket integration for live health status changes

### What This Story Does NOT Include

- Blast radius calculation (Story 6-3)
- Historical trending/charts (future enhancement)
- Alert configuration UI (future enhancement)
- Health status persistence/database (uses in-memory calculation)

### 🚨 Critical Anti-Patterns to DO NOT

1. **DO NOT** create new database models - reuse existing confidence query service from Story 6-1
2. **DO NOT** hardcode health thresholds - make configurable via settings (can reuse ConfidenceQueryConfig)
3. **DO NOT** skip WebSocket integration - must leverage existing Epic 5 infrastructure
4. **DO NOT** calculate confidence from scratch - query from existing ConfidenceQueryService
5. **DO NOT** create new exceptions - extend from `src/selectors/exceptions.py`
6. **DO NOT** block on database queries - use async patterns throughout
7. **DO NOT** duplicate WebSocket client - reuse existing from src/selectors/websocket/

### Architecture Patterns

**Integration with Existing Systems:**

```
src/selectors/
├── adaptive/
│   ├── services/
│   │   ├── confidence_query_service.py  # EXISTING from Story 6-1
│   │   └── health_status_service.py     # NEW - Health calculation
│   ├── api/
│   │   └── routes/
│       ├── confidence.py               # EXISTING from Story 6-1
│       └── health.py                   # NEW - Health endpoints
│   └── db/
│       └── repositories/
│           └── failure_event_repository.py  # EXISTING - For last_failure
├── websocket/
│   ├── client.py                       # EXISTING from Epic 5
│   └── integration.py                  # EXISTING - WebSocket handler
└── yaml_loader.py                      # EXISTING - For alternative selectors
```

**Health Status Thresholds Configuration:**

```python
from enum import Enum

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"

class HealthStatusConfig(BaseModel):
    healthy_threshold: float = 0.8      # Score >= 0.8 = healthy
    degraded_threshold: float = 0.5      # Score 0.5-0.79 = degraded
    failed_threshold: float = 0.5        # Score < 0.5 = failed
```

**API Response Schema:**

```python
class SelectorHealth(BaseModel):
    """Individual selector health status."""
    selector_id: str
    status: HealthStatus
    confidence_score: float
    last_failure: Optional[datetime] = None
    recommended_action: str
    alternatives: List[str] = []


class HealthDashboardResponse(BaseModel):
    """Response for dashboard grouped by health status."""
    healthy: List[SelectorHealth]
    degraded: List[SelectorHealth]
    failed: List[SelectorHealth]
    total: int
    last_updated: datetime


class SingleSelectorHealthResponse(BaseModel):
    """Response for single selector health query."""
    selector_id: str
    status: HealthStatus
    confidence_score: float
    last_failure: Optional[datetime]
    recommended_action: str
    alternatives: List[str]
    history_summary: Optional[dict] = None  # Optional: recent trend
```

### Project Structure Notes

- Follow existing module structure from `src/selectors/adaptive/`
- Create new service in `src/selectors/adaptive/services/health_status_service.py`
- Add API routes in `src/selectors/adaptive/api/routes/health.py`
- Use same patterns as existing API routes in adaptive module
- Use Pydantic models from `src/selectors/adaptive/api/schemas/`
- DO NOT create new exceptions - extend from `src/selectors/exceptions.py`
- Integrate with existing WebSocket from Epic 5

### Dependencies on Previous Work

**From Epic 3 (Failure Event Capture):**
- Failure event repository for last_failure timestamp lookup

**From Epic 5 (Real-Time Notifications):**
- WebSocket client and connection management
- Status streaming infrastructure (Story 5-3)
- Reuse the existing health status WebSocket message format

**From Story 6-1 (Confidence Score Query):**
- ConfidenceQueryService for confidence scores
- FailureEventRepository.get_all() and get_unique_selectors()
- API route patterns

**From Epic 6 (current epic):**
- Story 6-3 will use health status for blast radius calculation

### Confidence Score to Health Status Mapping

```
confidence_score >= 0.8  →  HEALTHY (green)
0.5 <= confidence_score < 0.8  →  DEGRADED (yellow)
confidence_score < 0.5  →  FAILED (red)
```

**Recommended Actions:**

```python
def get_recommended_action(status: HealthStatus, alternatives: List[str]) -> str:
    if status == HealthStatus.HEALTHY:
        return "Selector is performing well"
    elif status == HealthStatus.DEGRADED:
        if alternatives:
            return f"Consider reviewing selector - moderate failure rate. Alternatives available: {', '.join(alternatives)}"
        return "Consider reviewing selector - moderate failure rate"
    else:  # FAILED
        if alternatives:
            return f"Selector requires immediate attention - high failure rate. Use alternatives: {', '.join(alternatives)}"
        return "Selector requires immediate attention - high failure rate"
```

### Alternative Selectors Lookup

1. **From YAML Hints:** Check selector config for `alternatives` in hints
2. **From Adaptive Module:** Query for suggested alternatives based on failure patterns
3. **Prioritize:** YAML hints first (configured), then adaptive suggestions

### WebSocket Integration

**Message Format (leverage from Story 5-3):**

```python
class HealthStatusUpdate(BaseModel):
    """WebSocket message for health status changes."""
    type: str = "health_status_update"
    selector_id: str
    old_status: Optional[HealthStatus]
    new_status: HealthStatus
    confidence_score: float
    timestamp: datetime
```

**Channels:**
- Subscribe to `health.status` channel for all selector health updates
- Individual selector subscriptions: `health.status.{selector_id}`

### Testing Requirements

- Unit tests in `tests/selectors/adaptive/`
- Follow existing test patterns from Epic 3-6
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Mock confidence query service for unit tests
- Test all health threshold boundaries (0.5, 0.8)
- Test recommended actions for each status
- Test WebSocket message format compatibility with Epic 5
- Test coverage target: 80%+ for new modules

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Deferred-Decisions]
- [Source: _bmad-output/project-context.md#Technology-Stack]
- [Source: _bmad-output/project-context.md#Framework-Specific-Rules]
- [Source: _bmad-output/implementation-artifacts/6-1-confidence-score-query-api.md]
- [Source: _bmad-output/implementation-artifacts/5-3-selector-health-status-streaming.md]
- [FR15: System can display selector health status]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**NEW:**
- `src/selectors/adaptive/services/health_status_service.py` - Health status calculation service
- `src/selectors/adaptive/api/routes/health.py` - API endpoints for health display
- `src/selectors/adaptive/api/schemas/health.py` - Pydantic request/response schemas for health
- `tests/selectors/adaptive/test_health_status.py` - Unit tests for health status

**MODIFIED:**
- `src/selectors/adaptive/__init__.py` - Add exports for new health service
- `src/selectors/adaptive/services/__init__.py` - Add exports
- `src/selectors/adaptive/api/routes/__init__.py` - Add health router export
- `src/selectors/adaptive/api/app.py` - Add health router and endpoints

**REUSE FROM EXISTING:**
- `src/selectors/adaptive/services/confidence_query_service.py` - Story 6-1
- `src/selectors/adaptive/api/routes/confidence.py` - Story 6-1
- `src/selectors/websocket/client.py` - Epic 5
- `src/selectors/websocket/integration.py` - Epic 5
- `src/selectors/yaml_loader.py` - For alternative selectors lookup

## Review Follow-ups (AI)

- [x] [AI-Review][HIGH] AC4 Real-Time Updates - FIXED: Added WebSocket notification integration
- [x] [AI-Review][HIGH] Dashboard empty for selectors without failures - FIXED: Now includes selectors from YAML loader
- [x] [AI-Review][MEDIUM] Missing health endpoints in root API docs - FIXED: Added to app.py root endpoint
- [x] [AI-Review][LOW] MockYAMLLoader property bug - FIXED: Corrected property implementation
- [ ] [AI-Review][MEDIUM] Inconsistent thresholds with Story 5-3 - Story 5-3 uses 0.7/0.4, this uses 0.8/0.5 - needs alignment
