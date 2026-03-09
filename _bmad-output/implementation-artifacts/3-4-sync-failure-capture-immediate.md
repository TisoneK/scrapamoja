# Story 3.4: Sync Failure Capture (Immediate)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **scraper system**,
I want **to operate with sync failure capture (immediate)**,
so that **failures are captured and submitted right away during extraction**.

## Acceptance Criteria

**AC1: Immediate Sync Failure Capture**
- **Given** a selector execution that returns empty
- **When** the validation layer detects the failure
- **Then** the failure event is captured synchronously
- **And** the fallback chain is triggered immediately
- **And** the total added latency is ≤ 5 seconds (NFR1)

**AC2: DB Timeout Handling**
- **Given** a sync failure capture in progress
- **When** the adaptive module DB is slow
- **Then** the timeout is applied (default 30s per NFR4)
- **And** the scraper continues with primary selectors if timeout occurs

**AC3: High-Volume Handling**
- **Given** high-volume scraping operations
- **When** many failures occur in quick succession
- **Then** each failure is captured and submitted
- **And** the system handles the load without blocking

## Tasks / Subtasks

- [x] Task 1: Optimize sync capture timing (AC: 1)
  - [x] Subtask 1.1: Profile current submission service latency
  - [x] Subtask 1.2: Identify and remove blocking operations
  - [x] Subtask 1.3: Add timing instrumentation
  - [x] Subtask 1.4: Verify total latency ≤ 5 seconds
- [x] Task 2: Implement timeout handling (AC: 2)
  - [x] Subtask 2.1: Add configurable timeout to submission service
  - [x] Subtask 2.2: Handle timeout gracefully (continue with primary)
  - [x] Subtask 2.3: Log timeout events for diagnostics
- [x] Task 3: Handle high-volume scenarios (AC: 3)
  - [x] Subtask 3.1: Add connection pooling for DB submissions
  - [x] Subtask 3.2: Implement batch submission capability
  - [x] Subtask 3.3: Add backpressure handling
- [x] Task 4: Integration with existing hooks (AC: 1, 2, 3)
  - [x] Subtask 4.1: Verify post-extraction hook integration
  - [x] Subtask 4.2: Ensure sync behavior from Story 3-3 is preserved
  - [x] Subtask 4.3: Add performance metrics collection
- [x] Task 5: Write unit tests (AC: 1, 2, 3)
  - [x] Subtask 5.1: Test timing under 5 seconds
  - [x] Subtask 5.2: Test timeout handling
  - [x] Subtask 5.3: Test high-volume scenarios
  - [x] Subtask 5.4: Test integration with existing hooks

## Dev Notes

### What This Story Implements

1. **Timing Optimization** - Ensure sync failure capture adds ≤ 5 seconds latency
2. **Timeout Handling** - Apply 30s timeout to DB operations, continue on timeout
3. **High-Volume Handling** - Handle many failures without blocking

### What This Story Does NOT Include

- Async failure capture (Story 3-5 - Phase 2)
- WebSocket notifications for failures (Epic 5)
- Graceful degradation when adaptive unavailable (Epic 4)
- Health monitoring and blast radius (Epic 6)

### 🚨 Critical Anti-Patterns to Avoid

1. **DO NOT** break existing Story 3-3 functionality - submission service must still work
2. **DO NOT** use async/await for this story - sync capture is required per AC1
3. **DO NOT** increase latency beyond 5 seconds - performance is critical
4. **DO NOT** crash the scraper on timeout - continue with primary selectors
5. **DO NOT** block on high-volume - use non-blocking patterns
6. **DO NOT** modify existing FailureEvent dataclass
7. **DO NOT** bypass the existing FailureEventSubmissionService - extend it

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
   DB Submission (Story 3-3)
   ├─ Convert runtime to DB event
   ├─ Submit to FailureEventRepository
   └─ Handle DB failures gracefully
        │
        ▼
   THIS STORY: Sync Failure Capture (3-4)
   ├─ Ensure sync capture timing ≤ 5s
   ├─ Apply timeout (30s default)
   ├─ Handle high-volume without blocking
   └─ Continue on timeout/error
        │
        ▼
   Story 3-5: Async Failure Capture (Phase 2)
```

### Key Implementation Details

**Extension of FailureEventSubmissionService:**

The existing `FailureEventSubmissionService` from Story 3-3 needs to be extended with timing optimization and timeout handling.

```python
# In src/selectors/hooks/submission.py
# EXISTING: FailureEventSubmissionService class (from Story 3-3)
# EXTEND with the following new methods:

import time
from typing import Optional

# Configuration constants
DEFAULT_SUBMISSION_TIMEOUT = 30  # seconds (NFR4)
MAX_LATENCY_THRESHOLD = 5  # seconds (NFR1)
MAX_QUEUE_SIZE = 1000

class FailureEventSubmissionService:
    """Service for submitting failure events to adaptive module DB."""
    
    _instance = None
    _repository = None
    _retry_queue: List[FailureEvent] = []
    _submission_timeout = DEFAULT_SUBMISSION_TIMEOUT
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._repository = FailureEventRepository()
        return cls._instance
    
    def submit_with_timeout(self, failure_event: FailureEvent) -> bool:
        """Submit failure event with timeout handling (AC2)."""
        start_time = time.time()
        
        try:
            # Submit with timeout
            success = self._submit_within_timeout(failure_event)
            
            # Check latency requirement (AC1)
            elapsed = time.time() - start_time
            if elapsed > MAX_LATENCY_THRESHOLD:
                logger.warning(
                    f"Submission latency {elapsed:.2f}s exceeds threshold "
                    f"{MAX_LATENCY_THRESHOLD}s"
                )
            
            return success
            
        except TimeoutError:
            # AC2: Handle timeout gracefully
            logger.warning(
                f"DB submission timed out after {self._submission_timeout}s, "
                "continuing with primary selectors"
            )
            return True  # Don't crash scraper
        except Exception as e:
            logger.warning(f"DB submission failed: {e}")
            return True  # Don't crash scraper
    
    def _submit_within_timeout(self, failure_event: FailureEvent) -> bool:
        """Submit event with configurable timeout."""
        # Implementation uses threading.Timeout or similar
        # to enforce the 30s timeout
        ...
    
    def submit_batch(self, failure_events: List[FailureEvent]) -> bool:
        """Submit multiple events efficiently (AC3 - high-volume)."""
        # Batch submission for high-volume scenarios
        ...
    
    def set_timeout(self, timeout_seconds: int):
        """Configure submission timeout (default 30s per NFR4)."""
        self._submission_timeout = timeout_seconds
```

**High-Volume Handling Strategy:**

```python
# For AC3: High-volume operations
class SubmissionPool:
    """Connection pool for high-volume submissions."""
    
    def __init__(self, pool_size: int = 5):
        self.pool_size = pool_size
        self._connections = []
        self._available = Queue()
        self._initialize_pool()
    
    def submit_async(self, failure_event: FailureEvent) -> Future:
        """Submit without blocking (non-blocking for high-volume)."""
        # Return Future for async handling
        ...
    
    def apply_backpressure(self, queue_size: int):
        """Handle backpressure when queue is full."""
        if queue_size > MAX_QUEUE_SIZE * 0.8:
            logger.warning("High backpressure, consider batching")
            # Could implement: drop oldest, log warning
```

**Integration with Post-Extraction Hook:**

```python
# In src/selectors/hooks/post_extraction.py
# EXISTING code from Story 3-3 - MODIFY to add timing

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
            # Story 3-4: Submit with timeout and timing check
            self.submission_service.submit_with_timeout(failure_event)
        
        return failure_event
```

### Key Files to Modify

**Modified files:**
```
src/selectors/hooks/submission.py   ← ADD: timeout handling, timing optimization
src/selectors/hooks/post_extraction.py   ← UPDATE: use new submit_with_timeout
```

**UNCHANGED (do NOT touch):**
```
src/selectors/fallback/models.py              ← Already complete
src/selectors/adaptive/db/models/failure_event.py  ← SQLAlchemy model
src/selectors/adaptive/db/repositories/failure_event_repository.py  ← Repository
```

### Naming Conventions (MUST Follow)

- Module: `submission` (existing)
- Class: `FailureEventSubmissionService` (existing), add new methods
- Method: `submit_with_timeout`, `_submit_within_timeout`, `submit_batch` (snake_case)
- Test file: `test_submission.py` (existing - ADD new tests)
- Logger: `"selector_submission"` (use same logger)

### Non-Functional Requirements

| NFR | Requirement | Implementation |
|-----|-------------|----------------|
| NFR1 | Sync fallback path ≤ 5 seconds | Monitor timing, optimize blocking ops |
| NFR4 | Configurable timeout (default 30s) | Add timeout parameter to submission |

### Error Handling

- DB timeout → Log warning, continue with primary selectors (AC2)
- High-volume queue full → Apply backpressure, log warning
- Latency exceeds threshold → Log warning but continue
- All errors → Don't crash scraper, return True

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
├── 3-3: Adaptive Module DB Submission ← COMPLETE (review)
│       ↓
└── 3-4: Sync Failure Capture (Immediate) (THIS)
        ↓
Epic 4: Graceful Degradation ← BACKLOG
Epic 5: Real-Time Notifications - Phase 2 ← BACKLOG
Epic 6: Health Monitoring - Phase 2 ← BACKLOG
```

**Story 3-4 builds on Story 3-3:**
- Story 3-3 created the FailureEventSubmissionService with retry queue
- Story 3-4 extends with timeout handling and timing optimization
- Ensures sync capture adds ≤ 5 seconds latency
- Handles high-volume scenarios without blocking

### References

- Epic 3 details: `_bmad-output/planning-artifacts/epics.md#L377-401` (Story 3.4 ACs)
- Architecture: `_bmad-output/planning-artifacts/architecture.md` (Validation Layer, In-process Integration)
- PRD: `_bmad-output/planning-artifacts/prd.md` (FR8, FR9, FR19 - Failure capture, Sync capture)
- Previous stories: 
  - Story 3-3: `_bmad-output/implementation-artifacts/3-3-adaptive-module-db-submission.md`
- FailureEventSubmissionService: `src/selectors/hooks/submission.py`
- Post-extraction hook: `src/selectors/hooks/post_extraction.py`

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

- All tests passed: 26 submission tests + 47 post_extraction tests

### Completion Notes List

**Story 3-4 Implementation Complete**

**Implemented Features:**
1. **Timing Optimization (AC1)**: Added `submit_with_timeout()` method with latency monitoring (≤ 5s threshold)
2. **Timeout Handling (AC2)**: Implemented configurable timeout (default 30s) with graceful failure handling
3. **High-Volume Handling (AC3)**: Added `submit_batch()` method and backpressure warnings at 80% queue capacity
4. **Integration**: Added new functions to post_extraction.py while preserving backward compatibility

**Files Modified:**
- `src/selectors/hooks/submission.py` - Added timing, timeout, and batch submission methods
- `src/selectors/hooks/post_extraction.py` - Added timeout-aware submission functions
- `tests/unit/selectors/test_submission.py` - Added 10 new unit tests

**Test Results:**
- All 26 submission tests passed
- All 47 post_extraction tests passed (no regressions)
- All Story 3-4 ACs satisfied

**Key Implementation Details:**
- `DEFAULT_SUBMISSION_TIMEOUT = 30` (seconds, NFR4)
- `MAX_LATENCY_THRESHOLD = 5` (seconds, NFR1)
- `BACKPRESSURE_THRESHOLD = 0.8` (80% queue capacity)
- Threading-based timeout enforcement for sync operations

### File List

```
src/selectors/hooks/submission.py   ← ADDED: timeout handling, timing optimization, batch submission
src/selectors/hooks/post_extraction.py   ← ADDED: timeout-aware submission functions
tests/unit/selectors/test_submission.py   ← ADDED: 10 new unit tests for Story 3-4
```

---

## Code Review Fixes Applied

### Issues Fixed (2026-03-08)

**Issue 1: Story 3-5 Code Removed from Story 3-4**
- Removed `PersistentQueue` class and related code (Story 3-5 feature)
- Removed async methods (`submit_async`, `submit_success_event`, etc.)
- Removed Story 3-5 constants (`ASYNC_MODE_ENABLED`, `QUEUE_PERSISTENCE_PATH`, etc.)
- Removed unused imports (`asyncio`, `json`, `os`, `signal`, `SuccessEvent`)
- Updated module docstring to remove Story 3-5 references

**Issue 2: Added Exports in __init__.py**
- Added `submit_with_timeout` module-level function
- Added exports: `DEFAULT_SUBMISSION_TIMEOUT`, `MAX_LATENCY_THRESHOLD`, `BACKPRESSURE_THRESHOLD`
- Added `submit_failure_with_timeout` in post_extraction.py

**Issue 3: Integrated submit_with_timeout**
- Added import of `submit_with_timeout` in post_extraction.py
- Added new function `submit_failure_with_timeout()` for Story 3-4 integration

**Issue 4: Removed Story 3-5 Tests**
- Removed `TestAsyncFailureCaptureLearning` test class
- Removed `TestPersistentQueue` test class
- All Story 3-4 tests now pass (26 tests)
