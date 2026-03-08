# Story 3.3: Adaptive Module DB Submission

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **scraper system**,
I want **to submit failure events to the adaptive module database**,
so that **the adaptive system can learn from failures and improve selector suggestions**.

## Acceptance Criteria

**AC1: Sync DB Submission**
- **Given** a captured failure event
- **When** the sync failure capture is triggered
- **Then** the event is submitted to the adaptive module DB
- **And** the submission completes before continuing

**AC2: Successful DB Storage**
- **Given** a submission to the adaptive module
- **When** the DB operation succeeds
- **Then** the event is stored with all fields
- **And** no error is raised to the caller

**AC3: Graceful Failure Handling**
- **Given** a submission to the adaptive module
- **When** the DB operation fails
- **Then** the error is logged
- **And** the failure is handled gracefully (doesn't crash the scraper)

**AC4: Queue for Retry on Unavailability**
- **Given** the adaptive module is unavailable
- **When** submitting a failure event
- **Then** the event is queued for later retry
- **And** the scraper continues without blocking

## Tasks / Subtasks

- [x] Task 1: Create DB submission service (AC: 1, 2)
  - [x] Subtask 1.1: Create FailureEventSubmissionService class
  - [x] Subtask 1.2: Implement convert_runtime_to_db_event() method
  - [x] Subtask 1.3: Integrate with FailureEventRepository.create()
  - [x] Subtask 1.4: Add singleton pattern for repository access
- [x] Task 2: Handle DB failures gracefully (AC: 3)
  - [x] Subtask 2.1: Wrap DB calls in try/except
  - [x] Subtask 2.2: Log errors without crashing scraper
  - [x] Subtask 2.3: Return success to caller even on DB failure
- [x] Task 3: Implement retry queue for unavailable DB (AC: 4)
  - [x] Subtask 3.1: Create local queue for failed submissions
  - [x] Subtask 3.2: Implement retry mechanism when DB recovers
  - [x] Subtask 3.3: Add queue persistence (optional: file-based)
- [x] Task 4: Integrate with post-extraction hook (AC: 1)
  - [x] Subtask 4.1: Call submission service after failure event creation
  - [x] Subtask 4.2: Ensure sync behavior (await completion)
  - [x] Subtask 4.3: Handle the flow from Story 3-2 full context
- [x] Task 5: Write unit tests (AC: 1, 2, 3, 4)
  - [x] Subtask 5.1: Test successful DB submission
  - [x] Subtask 5.2: Test graceful failure handling
  - [x] Subtask 5.3: Test retry queue behavior
  - [x] Subtask 5.4: Test integration with post-extraction hook

## Dev Notes

### What This Story Implements

1. **DB Submission Service** - Submit failure events to adaptive module DB
2. **Runtime to DB conversion** - Convert FailureEvent dataclass to SQLAlchemy model
3. **Graceful error handling** - Log errors but don't crash scraper
4. **Retry queue** - Queue events when DB unavailable, retry later

### What This Story Does NOT Include

- Async failure capture for learning (Story 3-5 - Phase 2)
- Graceful degradation when adaptive unavailable (Epic 4)
- WebSocket notifications for failures (Epic 5)
- Sync failure capture timing optimization (Story 3-4)

### 🚨 Critical Anti-Patterns to Avoid

1. **DO NOT** create new FailureEventRepository - USE existing `src/selectors/adaptive/db/repositories/failure_event_repository.py`
2. **DO NOT** modify existing FailureEvent dataclass in `src/selectors/fallback/models.py`
3. **DO NOT** use different DB path - follow existing pattern from adaptive module
4. **DO NOT** block the main thread - use sync submission as per AC1
5. **DO NOT** crash the scraper on DB failure - always handle gracefully
6. **DO NOT** skip logging - log all DB operations (success and failure)
7. **DO NOT** use asyncio for this story - sync submission per AC1

### Architecture: Integration Flow

```
Selector Execution (primary selector)
        │
        ▼
   Validation Layer Hook (Story 3-1)
   ├─ Check if result is empty
   ├─ Check if exception was raised
   └─ Check if timeout occurred
        │
        ▼ (if failure detected)
   Create FailureEvent (Story 3-1)
        │
        ▼
   Full Context Logging (Story 3-2)
   ├─ Add attempted_fallbacks
   ├─ Add correlation_id
   └─ Set log level
        │
        ▼
   THIS STORY: DB Submission (3-3)
   ├─ Convert runtime to DB event
   ├─ Submit to FailureEventRepository
   ├─ Handle DB failures gracefully
   └─ Queue for retry if unavailable
        │
        ▼
   Story 3-4: Sync Failure Capture (Immediate)
```

### Key Implementation Details

**Submission Service Pattern:**
```python
from src.selectors.fallback.models import FailureEvent, FailureType
from src.selectors.adaptive.db.repositories.failure_event_repository import FailureEventRepository

class FailureEventSubmissionService:
    """Service for submitting failure events to adaptive module DB."""
    
    _instance = None
    _repository = None
    _retry_queue: List[FailureEvent] = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._repository = FailureEventRepository()
        return cls._instance
    
    def submit(self, failure_event: FailureEvent) -> bool:
        """Submit failure event to DB (AC1, AC2)."""
        try:
            # Convert runtime FailureEvent to DB model
            db_event = self._convert_to_db_event(failure_event)
            
            # Submit to repository
            self._repository.create(
                selector_id=db_event.selector_id,
                error_type=db_event.error_type,
                timestamp=db_event.timestamp,
                recipe_id=db_event.recipe_id,
                sport=db_event.sport,
                site=db_event.site,
                failure_reason=db_event.failure_reason,
                strategy_used=db_event.strategy_used,
                resolution_time=db_event.resolution_time,
                severity=db_event.severity,
                context_snapshot=db_event.context_snapshot,
                correlation_id=db_event.correlation_id,
            )
            
            # Process retry queue if any
            self._process_retry_queue()
            
            return True  # AC2: No error raised
            
        except Exception as e:
            # AC3: Handle gracefully, log error
            logger.warning(f"DB submission failed: {e}")
            self._queue_for_retry(failure_event)
            return True  # Don't crash scraper
    
    def _convert_to_db_event(self, failure_event: FailureEvent) -> dict:
        """Convert runtime FailureEvent to DB dict."""
        return {
            "selector_id": failure_event.selector_id,
            "error_type": failure_event.failure_type.value,
            "timestamp": failure_event.timestamp,
            "failure_reason": failure_event.error_message,
            "context_snapshot": failure_event.context,
            "correlation_id": failure_event.context.get("correlation_id"),
            # Extract additional fields from context
            "recipe_id": failure_event.context.get("recipe_id"),
            "sport": failure_event.context.get("sport"),
            "site": failure_event.context.get("site"),
        }
    
    def _queue_for_retry(self, failure_event: FailureEvent):
        """Queue event for retry when DB unavailable (AC4)."""
        if len(self._retry_queue) < 1000:  # Limit queue size
            self._retry_queue.append(failure_event)
    
    def _process_retry_queue(self):
        """Process queued events when DB recovers (AC4)."""
        while self._retry_queue:
            event = self._retry_queue.pop(0)
            try:
                db_event = self._convert_to_db_event(event)
                self._repository.create(**db_event)
            except Exception:
                # Put back in queue
                self._retry_queue.insert(0, event)
                break
```

**Integration with Post-Extraction Hook:**
```python
# In src/selectors/hooks/post_extraction.py
from src.selectors.hooks.submission import FailureEventSubmissionService

class PostExtractionValidator:
    def __init__(self):
        self.submission_service = FailureEventSubmissionService()
    
    async def validate_and_submit(
        self,
        result: Any,
        selector_id: str,
        page_url: str,
        extractor_id: str,
        fallback_result: Optional[FallbackResult] = None,
    ) -> Optional[FailureEvent]:
        # Create failure event (from Story 3-1, 3-2)
        failure_event = self.validate_result(...)
        
        if failure_event:
            # Story 3-3: Submit to DB
            self.submission_service.submit(failure_event)
        
        return failure_event
```

### Key Files to Modify

**New files:**
```
src/selectors/hooks/
└── submission.py          ← NEW: FailureEventSubmissionService
```

**Modified files:**
```
src/selectors/hooks/post_extraction.py   ← Integrate submission call
```

**UNCHANGED (do NOT touch):**
```
src/selectors/fallback/models.py              ← Already complete
src/selectors/adaptive/db/models/failure_event.py  ← SQLAlchemy model
src/selectors/adaptive/db/repositories/failure_event_repository.py  ← Repository
```

### Naming Conventions (MUST Follow)

- Module: `submission` (snake_case) in hooks/
- Class: `FailureEventSubmissionService` (PascalCase)
- Method: `submit`, `_convert_to_db_event`, `_queue_for_retry` (snake_case)
- Test file: `test_submission.py`, test class: `TestFailureEventSubmissionService`
- Logger: `"selector_submission"` (use same `_get_logger` pattern)

### Error Handling

- DB connection failure → Queue for retry, log warning
- DB operation timeout → Queue for retry, log warning
- Invalid failure event → Log error, return True (don't crash)
- Queue full → Drop oldest, log warning

### Dependency Flow Context

```
Epic 1: Fallback Chain ← COMPLETE (1-1, 1-2, 1-3, 1-4)
                     ↓
Epic 2: YAML Hints ← COMPLETE (2-1, 2-2, 2-3)
                 ↓
Epic 3: Failure Event Capture & Logging
├── 3-1: Selector Failure Event Capture ← COMPLETE (review)
│       ↓
├── 3-2: Full Context Failure Logging ← COMPLETE (review)
│       ↓
├── 3-3: Adaptive Module DB Submission (THIS)
│       ↓
├── 3-4: Sync Failure Capture (Immediate)
│       ↓
└── 3-5: Async Failure Capture (Learning) - Phase 2

Epic 4: Graceful Degradation ← BACKLOG
Epic 5: Real-Time Notifications - Phase 2 ← BACKLOG
Epic 6: Health Monitoring - Phase 2 ← BACKLOG
```

**Story 3-3 builds on Stories 3-1 and 3-2:**
- Story 3-1 created the validation hook and basic FailureEvent
- Story 3-2 extended with attempted_fallbacks and structured logging
- Story 3-3 adds DB submission using existing FailureEventRepository
- Story 3-4 will optimize sync capture timing

### References

- Epic 3 details: `_bmad-output/planning-artifacts/epics.md#L347-375` (Story 3.3 ACs)
- Architecture: `_bmad-output/planning-artifacts/architecture.md` (Validation Layer, In-process Integration)
- PRD: `_bmad-output/planning-artifacts/prd.md` (FR10 - Adaptive DB submission)
- Previous stories: 
  - Story 3-1: `_bmad-output/implementation-artifacts/3-1-selector-failure-event-capture.md`
  - Story 3-2: `_bmad-output/implementation-artifacts/3-2-full-context-failure-logging.md`
- FailureEvent runtime: `src/selectors/fallback/models.py`
- FailureEventRepository: `src/selectors/adaptive/db/repositories/failure_event_repository.py`
- FailureEvent SQLAlchemy: `src/selectors/adaptive/db/models/failure_event.py`

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

- Created `src/selectors/hooks/submission.py` with FailureEventSubmissionService class
- Modified `src/selectors/hooks/post_extraction.py` to add submission integration
- Updated `src/selectors/hooks/__init__.py` to export new functions
- Created `tests/unit/selectors/test_submission.py` with 16 unit tests

### Completion Notes List

- **Task 1 (DB Submission Service)**: ✅ Complete
  - Created FailureEventSubmissionService with singleton pattern
  - Implemented _convert_to_db_event() method for runtime-to-DB conversion
  - Integrated with existing FailureEventRepository.create()
  - Added singleton pattern for repository access

- **Task 2 (Graceful Failure Handling)**: ✅ Complete
  - All DB calls wrapped in try/except blocks
  - Errors logged with warning level without crashing scraper
  - Returns True to caller even on DB failure (AC3 satisfied)

- **Task 3 (Retry Queue)**: ✅ Complete
  - Implemented _retry_queue for failed submissions (max 1000 events)
  - Implemented _process_retry_queue() for automatic retry when DB recovers
  - Queue respects MAX_QUEUE_SIZE limit

- **Task 4 (Post-Extraction Hook Integration)**: ✅ Complete
  - Added submit_failure_to_db() function
  - Added create_and_submit_failure_event() convenience function
  - Both functions are sync (blocking) as required by AC1
  - Added import to post_extraction.py
  - Exported functions in __init__.py

- **Task 5 (Unit Tests)**: ✅ Complete
  - 16 unit tests covering all ACs
  - Tests for successful submission, failure handling, retry queue
  - All tests passing (16/16)
  - Existing post-extraction tests still pass (47/47)

### Review Fixes Applied

- **FIXED**: Added integration with post_extraction.py - now imports and uses submission service
- **FIXED**: Added missing functions submit_failure_to_db() and create_and_submit_failure_event()
- **FIXED**: Updated __init__.py to export all submission functions

### File List

**New Files:**
- `src/selectors/hooks/submission.py` - FailureEventSubmissionService

**Modified Files:**
- `src/selectors/hooks/post_extraction.py` - Integrate submission call

**Test Files:**
- `tests/unit/selectors/test_submission.py`
