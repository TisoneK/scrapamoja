# Story 3.2: Full Context Failure Logging

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want **to log failure events with full context**,
so that **I can debug issues and understand the root cause of failures**.

## Acceptance Criteria

**AC1: Full Failure Event Logging**
- **Given** a failure event with all required fields
- **When** the event is logged
- **Then** the log includes: selector_id, page_url, timestamp, failure_type, extractor_id
- **And** attempted_fallbacks array is included (even if empty)

**AC2: Fallback Chain Context**
- **Given** a failure event during fallback chain execution
- **When** logging the event
- **Then** the attempted_fallbacks array includes all selectors that were tried
- **And** each fallback includes its result (success/failure)

**AC3: Page Context with Metadata**
- **Given** a page context with additional metadata
- **When** creating the failure event
- **Then** the page_url includes full URL with any relevant parameters
- **And** timestamp is in ISO8601 format

**AC4: Structured Logging with Correlation**
- **Given** a failure event
- **When** logging to structured logger
- **Then** correlation ID is included for tracing
- **And** log level is set appropriately (WARNING for single failure, ERROR for critical)

## Tasks / Subtasks

- [x] Task 1: Extend FailureEvent with attempted_fallbacks (AC: 1, 2)
  - [x] Subtask 1.1: Add attempted_fallbacks field to FailureEvent context
  - [x] Subtask 1.2: Create dataclass for FallbackAttemptInfo (selector, result, timestamp)
- [x] Task 2: Capture attempted_fallbacks during chain execution (AC: 2)
  - [x] Subtask 2.1: Modify FallbackChainExecutor to collect all attempted selectors
  - [x] Subtask 2.2: Track success/failure status for each fallback
  - [x] Subtask 2.3: Pass attempted_fallbacks to failure event creation
- [x] Task 3: Implement structured logging (AC: 4)
  - [x] Subtask 3.1: Add correlation_id generation/propagation
  - [x] Subtask 3.2: Set appropriate log levels (WARNING/ERROR)
  - [x] Subtask 3.3: Use existing structured logging pattern (per architecture)
- [x] Task 4: Ensure ISO8601 timestamps (AC: 3)
  - [x] Subtask 4.1: Verify all timestamps use ISO8601 format
  - [x] Subtask 4.2: Include full URL with query parameters
- [x] Task 5: Write unit tests (AC: 1, 2, 3, 4)
  - [x] Subtask 5.1: Test attempted_fallbacks capture
  - [x] Subtask 5.2: Test correlation_id in logs
  - [x] Subtask 5.3: Test log level selection
  - [x] Subtask 5.4: Test ISO8601 timestamp format

## Dev Notes

### What This Story Implements

1. **Extended failure context** - Add attempted_fallbacks to failure logging
2. **Fallback chain tracking** - Track which selectors were tried and their results
3. **Structured logging** - Correlation IDs and appropriate log levels
4. **ISO8601 timestamps** - Consistent time format across logs

### What This Story Does NOT Include

- DB submission to adaptive module (Story 3-3)
- Async failure capture for learning (Story 3-5 - Phase 2)
- Graceful degradation when adaptive unavailable (Epic 4)

### 🚨 Critical Anti-Patterns to Avoid

1. **DO NOT** modify the FailureEvent dataclass fields directly in `src/selectors/fallback/models.py`
2. **DO** store attempted_fallbacks in the `context` dict of FailureEvent
3. **DO NOT** break existing fallback chain - must continue working after integration
4. **DO NOT** use different logging patterns - use existing structured logger
5. **DO NOT** block the main thread with logging operations
6. **DO NOT** duplicate selector tracking - reuse `FallbackResult.attempted_selectors`

### Architecture: Integration Flow

```
Selector Execution (primary selector)
        │
        ▼
   Validation Layer Hook (Story 3-1)
   ├─ Check if result is empty (None, "", [])
   ├─ Check if exception was raised
   └─ Check if timeout occurred
        │
        ▼ (if failure detected)
   Create FailureEvent (Story 3-1)
        │
        ▼
   THIS STORY: Full Context Logging (3-2)
   ├─ Add attempted_fallbacks from chain
   ├─ Add correlation_id
   └─ Set log level (WARNING/ERROR)
        │
        ▼
   Story 3-3: DB Submission
```

### Key Implementation Details

**Extending FailureEvent with attempted_fallbacks:**
```python
from src.selectors.fallback.models import FailureEvent, FailureType, FallbackResult
from datetime import datetime, timezone

def create_full_context_failure_event(
    failure_event: FailureEvent,
    fallback_result: Optional[FallbackResult] = None,
    correlation_id: Optional[str] = None
) -> FailureEvent:
    """Add full context to failure event (AC1, AC2)."""
    
    # AC2: Collect attempted_fallbacks from chain
    attempted_fallbacks = []
    if fallback_result and fallback_result.attempted_selectors:
        for selector_attempt in fallback_result.attempted_selectors:
            attempted_fallbacks.append({
                "selector": selector_attempt.name,
                "result": selector_attempt.result,
                "reason": selector_attempt.reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    # Add to context (AC1)
    context = failure_event.context.copy()
    context["attempted_fallbacks"] = attempted_fallbacks
    
    # AC4: Add correlation_id
    if correlation_id:
        context["correlation_id"] = correlation_id
    
    # AC4: Set log level based on criticality
    log_level = "ERROR" if fallback_result and not fallback_result.fallback_executed else "WARNING"
    context["log_level"] = log_level
    
    return FailureEvent(
        selector_id=failure_event.selector_id,
        url=failure_event.url,
        timestamp=failure_event.timestamp,
        failure_type=failure_event.failure_type,
        error_message=failure_event.error_message,
        context=context
    )
```

**Correlation ID Pattern:**
```python
import uuid
from contextvars import ContextVar

# Track correlation ID across async calls
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default=None)

def get_or_create_correlation_id() -> str:
    """Get existing or create new correlation ID (AC4)."""
    current = correlation_id_var.get()
    if current is None:
        current = str(uuid.uuid4())
        correlation_id_var.set(current)
    return current
```

**Structured Logging:**
```python
import logging
import json

def log_failure_event(failure_event: FailureEvent, log_level: str = "WARNING"):
    """Log failure with full context (AC4)."""
    logger = logging.getLogger("selector_failures")
    
    # AC3: ISO8601 timestamp
    log_entry = {
        "selector_id": failure_event.selector_id,
        "url": failure_event.url,
        "timestamp": failure_event.timestamp.isoformat(),
        "failure_type": failure_event.failure_type.value,
        "extractor_id": failure_event.context.get("extractor_id"),
        "attempted_fallbacks": failure_event.context.get("attempted_fallbacks", []),
        "correlation_id": failure_event.context.get("correlation_id")
    }
    
    # AC4: Log level based on severity
    if log_level == "ERROR":
        logger.error(json.dumps(log_entry))
    else:
        logger.warning(json.dumps(log_entry))
```

### Key Files to Modify

**Files to modify:**
```
src/selectors/hooks/post_extraction.py      ← Extend with full context
src/selectors/fallback/chain.py              ← Pass attempted_fallbacks
```

**New files (if needed):**
```
src/selectors/hooks/logging.py              ← Optional: dedicated logging helpers
```

**UNCHANGED (do NOT touch):**
```
src/selectors/fallback/models.py            ← Don't modify dataclass fields
src/selectors/adaptive/db/                   ← DB submission (Story 3-3)
```

### Naming Conventions (MUST Follow)

- Module: `hooks` (snake_case)
- Class: `FullContextLogger` or extend `PostExtractionValidator`
- Method: `add_fallback_context`, `log_with_correlation`
- Logger: `"selector_failures"` (new) or extend `"selector_hooks"`
- Test file: `test_full_context_logging.py`

### Dependency Flow Context

```
Epic 1: Fallback Chain ← COMPLETE (1-1, 1-2, 1-3, 1-4)
                     ↓
Epic 2: YAML Hints ← COMPLETE (2-1, 2-2, 2-3)
                 ↓
Epic 3: Failure Event Capture & Logging
├── 3-1: Selector Failure Event Capture ← COMPLETE (review)
│       ↓
├── 3-2: Full Context Failure Logging (THIS)
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

**Story 3-2 builds on Story 3-1:**
- Story 3-1 created the validation hook and basic FailureEvent
- Story 3-2 extends with attempted_fallbacks and structured logging
- Story 3-3 adds DB submission

### References

- Epic 3 details: `_bmad-output/planning-artifacts/epics.md#L317-345` (Story 3.2 ACs)
- Architecture: `_bmad-output/planning-artifacts/architecture.md` (Validation Layer, Structured Logging)
- PRD: `_bmad-output/planning-artifacts/prd.md` (FR9 - Full context logging)
- Previous story 3-1: `_bmad-output/implementation-artifacts/3-1-selector-failure-event-capture.md`
- FailureEvent dataclass: `src/selectors/fallback/models.py` (lines 52-76)
- FallbackResult: `src/selectors/fallback/models.py` (lines 130-169)
- FallbackChainExecutor: `src/selectors/fallback/chain.py`

---

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5:free

### Debug Log References

- PostExtractionValidator: `src/selectors/hooks/post_extraction.py`
- FallbackChainExecutor: `src/selectors/fallback/chain.py`
- Test file: `tests/unit/selectors/test_post_extraction.py`

### Completion Notes List

**Implementation completed on 2026-03-07**

✅ **Task 1: Extend FailureEvent with attempted_fallbacks (AC1, AC2)**
- Added `add_fallback_context_to_failure()` function to add attempted_fallbacks to FailureEvent context
- Added `create_full_context_failure_event()` as main entry point for full context failure events
- Implemented in `src/selectors/hooks/post_extraction.py`

✅ **Task 2: Capture attempted_fallbacks during chain execution (AC2)**
- Modified `FallbackChainExecutor.execute_with_fallback()` to track all attempted selectors
- Populates `attempted_selectors` list with primary and fallback selector attempts
- Each attempt includes: name, result, reason, value, resolution_time_ms

✅ **Task 3: Implement structured logging (AC4)**
- Added correlation ID management via ContextVar (`get_or_create_correlation_id()`, `set_correlation_id()`, `clear_correlation_id()`)
- Added `add_correlation_to_failure()` to add correlation ID to failure events
- Added `FailureEventLogger` class for structured logging with appropriate log levels
- Log level: WARNING for single failure, ERROR for critical (fallback executed but failed)

✅ **Task 4: Ensure ISO8601 timestamps (AC3)**
- All timestamps now use `datetime.now(timezone.utc).isoformat()`
- Full URL with query parameters preserved in failure events
- ISO8601 format verified in unit tests

✅ **Task 5: Write unit tests (14 new tests)**
- TestCorrelationIdManagement: 3 tests
- TestAttemptedFallbacksCapture: 3 tests
- TestISO8601Timestamps: 3 tests
- TestCorrelationIdInLogs: 3 tests
- TestFailureEventLogger: 2 tests

**All 47 tests pass (33 existing + 14 new)**

### File List

**Modified files:**
- `src/selectors/hooks/post_extraction.py` - Extended with full context logging functions
- `src/selectors/hooks/__init__.py` - Updated exports
- `src/selectors/fallback/chain.py` - Added attempted_selectors tracking
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - Updated status to in-progress

**Test files:**
- `tests/unit/selectors/test_post_extraction.py` - Added 14 new tests for Story 3-2
