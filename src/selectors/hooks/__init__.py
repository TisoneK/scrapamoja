"""
Validation layer hooks for selector execution.

This module provides post-extraction validation hooks that detect and capture
selector failures for analysis and learning.

Story 3-1: Selector Failure Event Capture
- PostExtractionValidator: Validates extraction results and captures failures
- create_failure_event: Creates basic failure event
- AC1: Empty Result Detection (None, "", [], {})
- AC2: Exception Detection (with error details)
- AC3: Timeout Detection
- AC4: Failure Event Fields (selector_id, url, timestamp, failure_type, extractor_id)

Story 3-2: Full Context Failure Logging
- add_fallback_context_to_failure: Adds attempted_fallbacks to failure event
- create_full_context_failure_event: Creates full context failure event
- get_or_create_correlation_id: Correlation ID management
- add_correlation_to_failure: Adds correlation ID to failure event
- FailureEventLogger: Structured logging for failure events
- AC1: Full Failure Event Logging (attempted_fallbacks in context)
- AC2: Fallback Chain Context (all attempted selectors with results)
- AC3: Page Context with Metadata (full URL, ISO8601 timestamps)
- AC4: Structured Logging with Correlation (correlation_id, log levels)

Story 7.4: Registration Automation
- RegistrationHook: Automatic selector registration via engine hooks
- create_registration_hook: Factory function to create and register hook
- auto_register_from_directory: Utility for manual trigger of auto-registration
- AC2: Registration happens automatically via engine hooks
- AC3: Selectors available immediately on scraper startup
"""

from src.selectors.hooks.post_extraction import (
    PostExtractionValidator,
    create_failure_event,
    submit_failure_with_timeout,  # Story 3-4: Timeout-aware submission
    submit_success_for_learning,  # Story 3-5: Success event capture
    # Story 3-2: Full Context Failure Logging
    get_or_create_correlation_id,
    set_correlation_id,
    clear_correlation_id,
    add_correlation_to_failure,
    add_fallback_context_to_failure,
    create_full_context_failure_event,
    FailureEventLogger,
)

# Story 3-3: Adaptive Module DB Submission
from src.selectors.hooks.submission import (
    FailureEventSubmissionService,
    get_submission_service,
    submit_failure_to_db,
    create_and_submit_failure_event,
)

# Story 3-4: Sync Failure Capture (Immediate)
from src.selectors.hooks.submission import (
    submit_with_timeout,
    DEFAULT_SUBMISSION_TIMEOUT,
    MAX_LATENCY_THRESHOLD,
    BACKPRESSURE_THRESHOLD,
)

# Story 3-5: Async Failure Capture (Learning)
from src.selectors.hooks.submission import (
    submit_failure_async,
    submit_success_event_to_db,
    PersistentQueue,
    ASYNC_MODE_ENABLED,
    QUEUE_PERSISTENCE_PATH,
    RETRY_BACKOFF_BASE,
    MAX_RETRY_ATTEMPTS,
)

# Story 7.4: Registration Automation
from src.selectors.hooks.registration import (
    RegistrationHook,
    create_registration_hook,
    auto_register_from_directory,
)

__all__ = [
    # Story 3-1 exports
    "PostExtractionValidator",
    "create_failure_event",
    "submit_failure_with_timeout",
    "submit_success_for_learning",  # Story 3-5
    # Story 3-2 exports
    "get_or_create_correlation_id",
    "set_correlation_id",
    "clear_correlation_id",
    "add_correlation_to_failure",
    "add_fallback_context_to_failure",
    "create_full_context_failure_event",
    "FailureEventLogger",
    # Story 3-3 exports
    "FailureEventSubmissionService",
    "get_submission_service",
    "submit_failure_to_db",
    "create_and_submit_failure_event",
    # Story 3-4 exports
    "submit_with_timeout",
    "DEFAULT_SUBMISSION_TIMEOUT",
    "MAX_LATENCY_THRESHOLD",
    "BACKPRESSURE_THRESHOLD",
    # Story 3-5 exports
    "submit_failure_async",
    "submit_success_event_to_db",
    "PersistentQueue",
    "ASYNC_MODE_ENABLED",
    "QUEUE_PERSISTENCE_PATH",
    "RETRY_BACKOFF_BASE",
    "MAX_RETRY_ATTEMPTS",
    # Story 7.4: Registration Automation
    "RegistrationHook",
    "create_registration_hook",
    "auto_register_from_directory",
]
