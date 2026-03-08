# Story 3.1: Selector Failure Event Capture

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **scraper system**,
I want **to capture selector failure events**,
so that **all failures are detected and recorded for analysis and learning**.

## Acceptance Criteria

**AC1: Empty Result Detection**
- **Given** a selector that returns empty or null result
- **When** the validation layer checks the result
- **Then** a failure event is created
- **And** the failure type is set to "empty_result"

**AC2: Exception Detection**
- **Given** a selector that throws an exception
- **When** the exception is caught
- **Then** a failure event is created
- **And** the failure type is set to "exception" with error details

**AC3: Timeout Detection**
- **Given** a selector that times out
- **When** the timeout is detected
- **Then** a failure event is created
- **And** the failure type is set to "timeout"

**AC4: Failure Event Fields**
- **Given** any failure detection
- **When** the event is captured
- **Then** the event includes: selector_id, page_url, timestamp, failure_type, extractor_id

## Tasks / Subtasks

- [x] Task 1: Create validation layer hook for failure detection (AC: 1, 2, 3, 4)
  - [x] Subtask 1.1: Create `src/selectors/hooks/` directory with `__init__.py`
  - [x] Subtask 1.2: Create `post_extraction.py` with failure detection logic
  - [x] Subtask 1.3: Implement detection for empty_result (returns None, empty string, empty list)
  - [x] Subtask 1.4: Implement detection for exception (try/except wrapper or callback)
  - [x] Subtask 1.5: Implement detection for timeout (timeout exception handling)

- [x] Task 2: Integrate failure event capture into existing fallback chain (AC: 4)
  - [x] Subtask 2.1: Modify `FallbackChainExecutor` to call validation hook on primary failure
  - [x] Subtask 2.2: Ensure extractor_id is passed through the chain context
  - [x] Subtask 2.3: Include page_url from extraction context

- [x] Task 3: Write unit tests (AC: 1, 2, 3, 4)
  - [x] Subtask 3.1: Test empty_result detection for None, "", []
  - [x] Subtask 3.2: Test exception detection with various exception types
  - [x] Subtask 3.3: Test timeout detection (timeout exception)
  - [x] Subtask 3.4: Test failure event fields are populated correctly

## Dev Notes

### What This Story Implements

1. **Validation layer hook** - Create `src/selectors/hooks/post_extraction.py` for failure detection
2. **Failure type detection** - Detect empty_result, exception, timeout scenarios
3. **Event creation** - Create FailureEvent with all required fields
4. **Hook integration** - Wire hook into existing fallback chain execution

### What This Story Does NOT Include

- DB submission to adaptive module (Story 3-3)
- Async failure capture for learning (Story 3-5 - Phase 2)
- Full context failure logging with attempted fallbacks (Story 3-2)
- Graceful degradation when adaptive unavailable (Epic 4)

### 🚨 Critical Anti-Patterns to Avoid

1. **DO NOT** create new FailureEvent dataclass - USE existing `src/selectors/fallback/models.py::FailureEvent`
2. **DO NOT** modify existing FailureEvent dataclass fields - it's already complete
3. **DO NOT** implement DB submission here - Story 3-3 handles that
4. **DO NOT** use dictionaries instead of FailureEvent dataclass
5. **DO NOT** duplicate FailureEvent model - there are TWO:
   - `src/selectors/fallback/models.py::FailureEvent` - runtime dataclass (USE THIS)
   - `src/selectors/adaptive/db/models/failure_event.py::FailureEvent` - SQLAlchemy for DB (Story 3-3 uses this)
6. **DO NOT** break existing fallback chain - must continue working after integration
7. **DO NOT** add synchronous blocking operations - keep async-friendly

### Architecture: Integration Flow

```
Selector Execution (primary selector)
        │
        ▼
  Validation Layer Hook (NEW - this story)
  ├─ Check if result is empty (None, "", [])
  ├─ Check if exception was raised
  └─ Check if timeout occurred
        │
        ▼ (if failure detected)
  Create FailureEvent with:
  ├─ selector_id (from selector config)
  ├─ page_url (from extraction context)
  ├─ timestamp (now)
  ├─ failure_type (empty_result | exception | timeout)
  └─ extractor_id (from context)
        │
        ▼
  Trigger Fallback Chain (Story 1-2, 1-3)
        │
        ▼
  Story 3-2: Full Context Logging (attempted_fallbacks)
  Story 3-3: DB Submission (FailureEventRepository)
```

### Key Implementation Details

**Using Existing FailureEvent Dataclass:**
```python
from src.selectors.fallback.models import FailureEvent, FailureType
from datetime import datetime, timezone

def create_failure_event(
    selector_id: str,
    page_url: str,
    failure_type: FailureType,
    extractor_id: str,
    error_message: Optional[str] = None
) -> FailureEvent:
    """Create a failure event with required fields (AC4)."""
    return FailureEvent(
        selector_id=selector_id,
        url=page_url,  # Note: uses 'url', not 'page_url'
        timestamp=datetime.now(timezone.utc),
        failure_type=failure_type,
        error_message=error_message,
        context={"extractor_id": extractor_id}
    )
```

**FailureType Enum Values (already exists):**
```python
from src.selectors.fallback.models import FailureType

# Use these values:
FailureType.EMPTY_RESULT  # "empty_result"
FailureType.EXCEPTION     # "exception"
FailureType.TIMEOUT       # "timeout"
FailureType.LOW_CONFIDENCE  # "low_confidence" (Story 3-2+)
FailureType.VALIDATION_FAILED  # "validation_failed" (Story 3-2+)
```

**Post-Extraction Hook Pattern:**
```python
# src/selectors/hooks/post_extraction.py
class PostExtractionValidator:
    """Validates extraction results and captures failures."""
    
    def validate_result(
        self,
        result: Any,
        selector_id: str,
        page_url: str,
        extractor_id: str,
        exception: Optional[Exception] = None
    ) -> Optional[FailureEvent]:
        """Check result and return FailureEvent if failed, None if success."""
        
        # AC2: Exception detection
        if exception is not None:
            return FailureEvent(
                selector_id=selector_id,
                url=page_url,
                timestamp=datetime.now(timezone.utc),
                failure_type=FailureType.EXCEPTION,
                error_message=str(exception),
                context={"extractor_id": extractor_id}
            )
        
        # AC1: Empty result detection
        if result is None or result == "" or (isinstance(result, (list, dict)) and len(result) == 0):
            return FailureEvent(
                selector_id=selector_id,
                url=page_url,
                timestamp=datetime.now(timezone.utc),
                failure_type=FailureType.EMPTY_RESULT,
                context={"extractor_id": extractor_id}
            )
        
        # Success - no failure event
        return None
```

### Key Files to Modify

**New files:**
```
src/selectors/hooks/
├── __init__.py
└── post_extraction.py     ← NEW: Validation layer for failure detection
```

**Modified files:**
```
src/selectors/fallback/chain.py      ← Integrate validation hook call
src/selectors/engine.py              ← Add hook registration (if needed)
```

**UNCHANGED (do NOT touch):**
```
src/selectors/fallback/models.py              ← Already has FailureEvent
src/selectors/adaptive/db/models/failure_event.py  ← SQLAlchemy model (Story 3-3)
src/selectors/adaptive/db/repositories/       ← Repository (Story 3-3)
src/selectors/hints/
src/selectors/yaml_loader.py
```

### Naming Conventions (MUST Follow)

- Module: `hooks` (snake_case)
- Class: `PostExtractionValidator` (PascalCase)
- Method: `validate_result`, `is_empty_result` (snake_case)
- Test file: `test_post_extraction.py`, test class: `TestPostExtractionValidator`
- Logger: `"selector_hooks"` (use same `_get_logger` pattern)

### Error Handling

- Invalid result type → treat as empty_result
- Exception without message → use exception type name as message
- No page_url → use empty string (but log warning)
- Import: `from src.selectors.exceptions import SelectorError, FallbackError`

### Testing Patterns

- Use `@pytest.mark.unit` for all tests
- Mock Playwright page/context with `unittest.mock.MagicMock`
- Test empty detection: None, "", [], {}, 0
- Test exception detection: various exception types
- Test timeout: asyncio.TimeoutError handling

### Dependency Flow Context

```
Epic 1: Fallback Chain ← COMPLETE (1-1, 1-2, 1-3, 1-4)
                     ↓
Epic 2: YAML Hints ← COMPLETE (2-1, 2-2, 2-3)
                 ↓
Epic 3: Failure Event Capture & Logging
├── 3-1 (THIS): Selector Failure Event Capture ← NEW
│       ↓
├── 3-2: Full Context Failure Logging
│       ↓
├── 3-3: Adaptive Module DB Submission
│       ↓
├── 3-4: Sync Failure Capture (Immediate)
│       ↓
└── 3-5: Async Failure Capture (Learning) - Phase 2

Epic 4: Graceful Degradation ← BACKLOG
Epic 5: Real-Time Notifications - Phase 2 ← BACKLOG
Epic 6: Health Monitoring - Phase 2 ← BACKLOG
```

**Story 3-1 is the FOUNDATION for Epic 3:**
- This story creates the validation layer hook
- Story 3-2 extends it with full context (attempted_fallbacks)
- Story 3-3 adds DB submission using existing FailureEventRepository

### References

- Epic 3 details: `_bmad-output/planning-artifacts/epics.md#L281-315` (Story 3.1 ACs)
- Architecture: `_bmad-output/planning-artifacts/architecture.md` (Validation Layer)
- PRD: `_bmad-output/planning-artifacts/prd.md` (FR8, FR9, FR10)
- FailureEvent dataclass: `src/selectors/fallback/models.py` (lines 52-76)
- FailureType enum: `src/selectors/fallback/models.py` (lines 14-20)
- Fallback chain executor: `src/selectors/fallback/chain.py`
- Previous Epic 2 story: `_bmad-output/implementation-artifacts/2-3-stability-based-prioritization.md`

---

## Change Log

- 2026-03-07: Implemented Story 3-1: Selector Failure Event Capture
  - Created validation layer hook for failure detection
  - Integrated with fallback chain executor
  - Added comprehensive unit tests (34 tests passing)

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

- Implementation completed with lazy-loading to avoid circular imports
- Used PostExtractionValidator with fallback chain integration

### Completion Notes List

**Implemented:**
1. Created `src/selectors/hooks/` directory with:
   - `__init__.py` - Module exports
   - `post_extraction.py` - PostExtractionValidator class with:
     - `is_empty_result()` - Detects empty values (None, "", [], {})
     - `detect_failure_type()` - Identifies failure type
     - `validate_result()` - Main validation method
     - `create_failure_event()` - Helper function

2. Integrated validation hook into FallbackChainExecutor:
   - Added lazy import in `src/selectors/fallback/chain.py`
   - Added validator call in `execute_with_fallback()` method
   - Added validator call in `execute_chain()` method
   - Used extractor_id from context.tab_context

3. Created comprehensive unit tests:
   - 33 test cases covering all ACs
   - Tests for empty_result detection (None, "", [], etc.)
   - Tests for exception detection
   - Tests for timeout detection
   - Tests for failure event field population

**Testing:**
- All 33 unit tests pass
- Integration with existing fallback chain verified

### File List

**New Files:**
- `src/selectors/hooks/__init__.py`
- `src/selectors/hooks/post_extraction.py`
- `tests/unit/selectors/test_post_extraction.py`

**Modified Files:**
- `src/selectors/fallback/chain.py`

### File List

To be filled by developer upon completion.
