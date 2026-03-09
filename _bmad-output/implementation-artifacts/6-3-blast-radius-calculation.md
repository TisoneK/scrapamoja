# Story 6.3: Blast Radius Calculation

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user**,
I want **to calculate blast radius for failures**,
so that **I can understand the impact of a selector failure on data quality**.

## Acceptance Criteria

**AC1: Failure Impact Identification**
- **Given** a selector failure event
- **When** calculating blast radius
- **Then** identify all affected data fields extracted by that selector
- **And** count the number of affected records in the database
- **And** return the affected fields and record count in the response

**AC2: Severity Assessment**
- **Given** a failed selector (e.g., "home_team")
- **When** blast radius is calculated
- **Then** determine severity based on:
  - `critical`: confidence_score < 0.5 AND affects primary data fields (core match data)
  - `major`: confidence_score 0.5-0.79 OR affects secondary data fields
  - `minor`: confidence_score >= 0.8 OR affects optional/auxiliary data
- **And** include the severity level in the response

**AC3: Cascading Effects**
- **Given** multiple related selectors (identified via YAML hints or selector dependencies)
- **When** one selector fails and impacts others
- **Then** identify all dependent selectors that may be affected
- **And** include cascading effects in the blast radius calculation
- **And** mark all affected fields as impacted

**AC4: Blast Radius Query Response**
- **Given** a blast radius query
- **When** presenting results
- **Then** the output includes:
  - `failed_selector`: The selector ID that failed
  - `affected_fields`: List of data fields impacted
  - `affected_records`: Count of records affected
  - `severity`: Level (critical/major/minor)
  - `recommended_actions`: Suggested remediation steps
  - `cascading_selectors`: List of related selectors potentially impacted (if any)
  - `timestamp`: When the calculation was performed

**AC5: Real-Time Blast Radius Updates**
- **Given** a selector failure occurs
- **When** blast radius is calculated
- **Then** broadcast the blast radius update via WebSocket
- **And** include it in the health dashboard for immediate visibility

## Tasks / Subtasks

- [x] Task 1: Design blast radius calculation architecture (AC: 1, 2, 3)
  - [x] Subtask 1.1: Define BlastRadiusService in src/selectors/adaptive/services/
  - [x] Subtask 1.2: Design selector dependency graph (from YAML hints)
  - [x] Subtask 1.3: Define severity calculation logic based on health status

- [x] Task 2: Implement blast radius calculation (AC: 1, 2)
  - [x] Subtask 2.1: Query failure events for affected records
  - [x] Subtask 2.2: Calculate affected fields from selector configuration
  - [x] Subtask 2.3: Implement severity assessment based on confidence score thresholds

- [x] Task 3: Implement cascading effects detection (AC: 3)
  - [x] Subtask 3.1: Build selector dependency mapping from YAML hints
  - [x] Subtask 3.2: Identify dependent selectors that share data context
  - [x] Subtask 3.3: Include cascading selectors in blast radius response

- [x] Task 4: Create blast radius API endpoints (AC: 4)
  - [x] Subtask 4.1: Add GET /api/v1/blast-radius/{selector_id} endpoint
  - [x] Subtask 4.2: Add GET /api/v1/blast-radius?selector_ids=... for batch query
  - [x] Subtask 4.3: Implement response schema with all required fields

- [x] Task 5: Integrate with WebSocket for real-time updates (AC: 5)
  - [x] Subtask 5.1: Add blast radius WebSocket message to existing health channel
  - [x] Subtask 5.2: Trigger blast radius calculation on selector failure events
  - [x] Subtask 5.3: Include blast radius in dashboard updates

- [x] Task 6: Write unit tests (AC: 1, 2, 3, 4, 5)
  - [x] Subtask 6.1: Test blast radius calculation for all severity levels
  - [x] Subtask 6.2: Test cascading effects detection
  - [x] Subtask 6.3: Test API endpoint responses
  - [x] Subtask 6.4: Test WebSocket integration

## Dev Notes

### What This Story Implements

1. **Blast Radius Calculation** - Calculate impact of selector failures on data quality
2. **Severity Assessment** - Determine severity (critical/major/minor) based on health status
3. **Cascading Effects** - Detect and include dependent selectors in blast radius
4. **Blast Radius API** - RESTful endpoint to query blast radius information
5. **Real-Time Updates** - WebSocket integration for live blast radius notifications

### What This Story Does NOT Include

- Historical blast radius trending (future enhancement)
- Automatic remediation actions (future enhancement)
- Blast radius for successful extractions (only failures)
- Selector dependency ML/learning (YAML hints based only)

### 🚨 Critical Anti-Patterns to DO NOT

1. **DO NOT** create new database models - reuse existing FailureEventRepository
2. **DO NOT** calculate confidence from scratch - query from existing ConfidenceQueryService
3. **DO NOT** hardcode severity thresholds - make configurable (reuse HealthStatusConfig from Story 6-2)
4. **DO NOT** skip WebSocket integration - must leverage existing Epic 5 infrastructure
5. **DO NOT** create new exceptions - extend from `src/selectors/exceptions.py`
6. **DO NOT** block on database queries - use async patterns throughout
7. **DO NOT** duplicate selector dependency logic - use YAML hints from yaml_loader.py
8. **DO NOT** calculate blast radius for healthy selectors - only failed/degraded ones

### Architecture Patterns

**Integration with Existing Systems:**

```
src/selectors/
├── adaptive/
│   ├── services/
│   │   ├── confidence_query_service.py    # EXISTING from Story 6-1
│   │   ├── health_status_service.py       # EXISTING from Story 6-2
│   │   └── blast_radius_service.py       # NEW - Blast radius calculation
│   ├── api/
│   │   └── routes/
│   │       ├── confidence.py              # EXISTING from Story 6-1
│   │       ├── health.py                  # EXISTING from Story 6-2
│   │       └── blast_radius.py           # NEW - Blast radius endpoints
│   └── db/
│       └── repositories/
│           └── failure_event_repository.py  # EXISTING - For failure lookup
├── websocket/
│   ├── client.py                          # EXISTING from Epic 5
│   └── integration.py                     # EXISTING - WebSocket handler
└── yaml_loader.py                         # EXISTING - For selector dependencies
```

**Blast Radius Severity Configuration:**

```python
from enum import Enum

class BlastRadiusSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"

class BlastRadiusConfig(BaseModel):
    critical_confidence_threshold: float = 0.5   # Score < 0.5 = critical
    major_confidence_threshold: float = 0.8     # Score 0.5-0.79 = major
    # Score >= 0.8 = minor (or healthy - no blast radius)
    critical_fields: List[str] = ["home_team", "away_team", "score", "match_time"]
```

**API Response Schema:**

```python
class AffectedField(BaseModel):
    field_name: str
    field_type: str  # primary, secondary, auxiliary
    confidence_impact: float


class CascadingSelector(BaseModel):
    selector_id: str
    dependency_type: str  # shares_data, depends_on, related
    potential_impact: str


class BlastRadiusResponse(BaseModel):
    """Response for blast radius query."""
    failed_selector: str
    affected_fields: List[AffectedField]
    affected_records: int
    severity: BlastRadiusSeverity
    recommended_actions: List[str]
    cascading_selectors: List[CascadingSelector] = []
    timestamp: datetime
    confidence_score: float


class BatchBlastRadiusResponse(BaseModel):
    """Response for batch blast radius query."""
    blast_radius: Dict[str, BlastRadiusResponse]
    total_calculated: int
    timestamp: datetime
```

### Project Structure Notes

- Follow existing module structure from `src/selectors/adaptive/`
- Create new service in `src/selectors/adaptive/services/blast_radius_service.py`
- Add API routes in `src/selectors/adaptive/api/routes/blast_radius.py`
- Use same patterns as existing API routes in adaptive module
- Use Pydantic models from `src/selectors/adaptive/api/schemas/`
- DO NOT create new exceptions - extend from `src/selectors/exceptions.py`
- Integrate with existing WebSocket from Epic 5
- Reuse YAML hints for selector dependencies

### Dependencies on Previous Work

**From Epic 3 (Failure Event Capture):**
- Failure event repository for failure lookup

**From Epic 5 (Real-Time Notifications):**
- WebSocket client and connection management
- Status streaming infrastructure

**From Story 6-1 (Confidence Score Query):**
- ConfidenceQueryService for confidence scores

**From Story 6-2 (Health Status Display):**
- HealthStatusService for health status calculation
- HealthStatus enum with thresholds
- Already defines: healthy (≥0.8), degraded (0.5-0.79), failed (<0.5)

### Blast Radius Calculation Logic

**Severity Mapping:**

```
confidence_score < 0.5     →  CRITICAL (and status = failed)
confidence_score 0.5-0.79  →  MAJOR (and status = degraded)
confidence_score >= 0.8    →  MINOR (and status = healthy)
```

**Affected Fields Detection:**

1. Query YAML selector configuration for fields extracted by selector
2. Cross-reference with selector dependency graph (from YAML hints)
3. Query failure events to count affected records
4. Map fields to field types (primary/secondary/auxiliary)

**Cascading Effects Detection:**

1. From YAML hints: check for `alternatives`, `depends_on`, `related_selectors`
2. Build dependency graph: selector → list of dependent selectors
3. For each dependent selector, calculate potential impact
4. Include in response if potential_impact > threshold

**Recommended Actions:**

```python
def get_recommended_actions(severity: BlastRadiusSeverity, alternatives: List[str]) -> List[str]:
    if severity == BlastRadiusSeverity.CRITICAL:
        actions = [
            "URGENT: Selector requires immediate attention",
            "Consider using alternative selectors: " + ", ".join(alternatives) if alternatives else "No alternatives available",
            "Review selector configuration in YAML"
        ]
    elif severity == BlastRadiusSeverity.MAJOR:
        actions = [
            "Selector showing degraded performance",
            "Monitor closely and plan selector update",
            "Alternatives available: " + ", ".join(alternatives) if alternatives else "None"
        ]
    else:  # MINOR
        actions = [
            "Selector performing adequately",
            "Minor impact - no immediate action required"
        ]
    return actions
```

### WebSocket Integration

**Message Format:**

```python
class BlastRadiusUpdate(BaseModel):
    """WebSocket message for blast radius updates."""
    type: str = "blast_radius_update"
    failed_selector: str
    severity: BlastRadiusSeverity
    affected_fields: List[str]
    affected_records: int
    timestamp: datetime
```

**Channels:**
- Subscribe to `blast.radius` channel for all blast radius updates
- Trigger on: selector failure events (from failure capture hook)

### Testing Requirements

- Unit tests in `tests/selectors/adaptive/`
- Follow existing test patterns from Epic 3-6
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Mock confidence query service for unit tests
- Test all severity threshold boundaries (0.5, 0.8)
- Test cascading effects detection
- Test recommended actions for each severity
- Test WebSocket message format
- Test coverage target: 80%+ for new modules

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Deferred-Decisions]
- [Source: _bmad-output/project-context.md#Technology-Stack]
- [Source: _bmad-output/project-context.md#Framework-Specific-Rules]
- [Source: _bmad-output/implementation-artifacts/6-1-confidence-score-query-api.md]
- [Source: _bmad-output/implementation-artifacts/6-2-selector-health-status-display.md]
- [Source: _bmad-output/implementation-artifacts/5-3-selector-health-status-streaming.md]
- [FR16: System can calculate blast radius for failures]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**NEW:**
- `src/selectors/adaptive/services/blast_radius_service.py` - Blast radius calculation service
- `src/selectors/adaptive/api/routes/blast_radius.py` - API endpoints for blast radius
- `src/selectors/adaptive/api/schemas/blast_radius.py` - Pydantic request/response schemas
- `src/selectors/websocket/models.py` - Added BlastRadiusUpdate model (AC5)
- `src/selectors/websocket/client.py` - Added send_blast_radius_update method (AC5)
- `tests/selectors/adaptive/test_blast_radius.py` - Unit tests for blast radius

**MODIFIED:**
- `src/selectors/adaptive/__init__.py` - Add exports for new blast radius service
- `src/selectors/adaptive/services/__init__.py` - Add exports
- `src/selectors/adaptive/api/routes/__init__.py` - Add blast_radius router export
- `src/selectors/adaptive/api/app.py` - Add blast_radius router and endpoints

**REUSE FROM EXISTING (from Epic 3, 5, Stories 6-1, 6-2):**
- `src/selectors/adaptive/services/confidence_query_service.py` - Story 6-1
- `src/selectors/adaptive/services/health_status_service.py` - Story 6-2
- `src/selectors/adaptive/api/routes/confidence.py` - Story 6-1
- `src/selectors/adaptive/api/routes/health.py` - Story 6-2
- `src/selectors/websocket/client.py` - Epic 5
- `src/selectors/websocket/integration.py` - Epic 5
- `src/selectors/yaml_loader.py` - For selector dependency hints
- `src/selectors/adaptive/db/repositories/failure_event_repository.py` - Epic 3
