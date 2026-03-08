"""
Post-extraction validation layer for selector failure detection.

This module provides the PostExtractionValidator class that validates extraction
results and captures failure events for analysis and learning.

Story 3-1: Selector Failure Event Capture
- AC1: Empty Result Detection (None, "", [], {})
- AC2: Exception Detection (with error details)
- AC3: Timeout Detection
- AC4: Failure Event Fields (selector_id, url, timestamp, failure_type, extractor_id)

Story 3-2: Full Context Failure Logging
- AC1: Full Failure Event Logging (attempted_fallbacks in context)
- AC2: Fallback Chain Context (all attempted selectors with results)
- AC3: Page Context with Metadata (full URL, ISO8601 timestamps)
- AC4: Structured Logging with Correlation (correlation_id, log levels)
"""

import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.selectors.fallback.models import FailureEvent, FailureType, FallbackResult, SuccessEvent
from src.selectors.hooks.submission import (
    FailureEventSubmissionService,
    submit_failure_to_db,
    submit_with_timeout,  # Story 3-4: Timeout-aware submission
    submit_failure_async,  # Story 3-5: Async submission
    submit_success_event_to_db,  # Story 3-5: Success event submission
    create_and_submit_failure_event,
)

# Context variable for correlation ID tracking across async calls
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def get_or_create_correlation_id() -> str:
    """
    Get existing or create new correlation ID (AC4).
    
    This function propagates correlation IDs across async calls for
    distributed tracing of failure events.
    
    Returns:
        str: Correlation ID for tracing
    """
    current = correlation_id_var.get()
    if current is None:
        current = str(uuid.uuid4())
        correlation_id_var.set(current)
    return current


def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID for current context.
    
    Args:
        correlation_id: Correlation ID to set
    """
    correlation_id_var.set(correlation_id)


def clear_correlation_id() -> None:
    """
    Clear correlation ID from current context.
    """
    correlation_id_var.set(None)


class PostExtractionValidator:
    """
    Validates extraction results and captures failures.

    This validator detects three types of failures:
    - AC1: Empty result (None, "", [], {})
    - AC2: Exception during extraction
    - AC3: Timeout during extraction
    """

    def __init__(self) -> None:
        """Initialize the post-extraction validator."""
        self._logger = self._get_logger()

    def _get_logger(self):
        """Get structured logger for validation operations."""
        try:
            from src.observability.logger import get_logger

            return get_logger("selector_hooks")
        except ImportError:
            import logging

            return logging.getLogger("selector_hooks")

    def is_empty_result(self, result: Any) -> bool:
        """
        Check if the result is empty.

        Args:
            result: The extraction result to check

        Returns:
            True if result is considered empty, False otherwise
        """
        # AC1: Empty result detection
        if result is None:
            return True
        if result == "":
            return True
        if isinstance(result, (list, dict, tuple, set)):
            return len(result) == 0
        return False

    def detect_failure_type(
        self,
        result: Any,
        exception: Optional[Exception] = None,
    ) -> Optional[FailureType]:
        """
        Detect the type of failure from result or exception.

        Args:
            result: The extraction result
            exception: Optional exception that occurred

        Returns:
            FailureType if failure detected, None otherwise
        """
        # AC2: Exception detection (check timeout first)
        if exception is not None:
            # Check for asyncio.TimeoutError specifically
            if hasattr(exception, '__class__') and exception.__class__.__name__ == 'TimeoutError':
                return FailureType.TIMEOUT
            # Check for timeout module's TimeoutError
            try:
                import asyncio
                if isinstance(exception, asyncio.TimeoutError):
                    return FailureType.TIMEOUT
            except ImportError:
                pass
            return FailureType.EXCEPTION

        # AC1: Empty result detection
        if self.is_empty_result(result):
            return FailureType.EMPTY_RESULT

        # No failure detected
        return None

    def validate_result(
        self,
        result: Any,
        selector_id: str,
        page_url: str,
        extractor_id: str,
        exception: Optional[Exception] = None,
    ) -> Optional[FailureEvent]:
        """
        Validate extraction result and create failure event if needed.

        Args:
            result: The extraction result to validate
            selector_id: ID/name of the selector that produced the result
            page_url: URL of the page being extracted
            extractor_id: ID of the extractor running the selector
            exception: Optional exception that occurred during extraction

        Returns:
            FailureEvent if validation failed, None if successful

        Example:
            >>> validator = PostExtractionValidator()
            >>> failure = validator.validate_result(
            ...     result=None,
            ...     selector_id="team_name",
            ...     page_url="https://example.com/match",
            ...     extractor_id="flashscore_extractor"
            ... )
            >>> if failure:
            ...     print(f"Failure detected: {failure.failure_type}")
        """
        # Detect failure type
        failure_type = self.detect_failure_type(result, exception)

        if failure_type is None:
            # No failure - validation passed
            return None

        # AC4: Create failure event with all required fields
        error_message = None
        if exception is not None:
            # AC2: Get error message from exception
            error_message = str(exception) if str(exception) else type(exception).__name__
        elif failure_type == FailureType.EMPTY_RESULT:
            error_message = "Result is empty"

        failure_event = FailureEvent(
            selector_id=selector_id,
            url=page_url or "",
            timestamp=datetime.now(timezone.utc),
            failure_type=failure_type,
            error_message=error_message,
            context={"extractor_id": extractor_id},
        )

        # Log the failure event
        self._logger.error(
            "selector_failure_detected",
            extra=failure_event.to_dict(),
        )

        return failure_event


def add_correlation_to_failure(
    failure_event: FailureEvent,
    correlation_id: Optional[str] = None,
) -> FailureEvent:
    """
    Add correlation ID to failure event context (AC4).
    
    Args:
        failure_event: The failure event to add correlation ID to
        correlation_id: Optional correlation ID. If not provided, will get/create one.
    
    Returns:
        FailureEvent with correlation_id added to context
    """
    if correlation_id is None:
        correlation_id = get_or_create_correlation_id()
    
    context = failure_event.context.copy()
    context["correlation_id"] = correlation_id
    
    return FailureEvent(
        selector_id=failure_event.selector_id,
        url=failure_event.url,
        timestamp=failure_event.timestamp,
        failure_type=failure_event.failure_type,
        error_message=failure_event.error_message,
        context=context,
    )


def add_fallback_context_to_failure(
    failure_event: FailureEvent,
    fallback_result: Optional[FallbackResult] = None,
) -> FailureEvent:
    """
    Add attempted_fallbacks context to failure event (AC1, AC2).
    
    Args:
        failure_event: The failure event to add fallback context to
        fallback_result: Optional fallback result containing attempted selectors
    
    Returns:
        FailureEvent with attempted_fallbacks added to context
    """
    context = failure_event.context.copy()
    
    # AC2: Collect attempted_fallbacks from chain
    attempted_fallbacks = []
    if fallback_result and fallback_result.attempted_selectors:
        for selector_attempt in fallback_result.attempted_selectors:
            attempted_fallbacks.append({
                "selector": selector_attempt.get("name"),
                "result": selector_attempt.get("result"),
                "reason": selector_attempt.get("reason"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    # Add to context (AC1)
    context["attempted_fallbacks"] = attempted_fallbacks
    
    return FailureEvent(
        selector_id=failure_event.selector_id,
        url=failure_event.url,
        timestamp=failure_event.timestamp,
        failure_type=failure_event.failure_type,
        error_message=failure_event.error_message,
        context=context,
    )


def create_full_context_failure_event(
    failure_event: FailureEvent,
    fallback_result: Optional[FallbackResult] = None,
    correlation_id: Optional[str] = None,
) -> FailureEvent:
    """
    Add full context to failure event (AC1, AC2, AC4).
    
    This is the main entry point for creating full context failure events
    that include attempted_fallbacks and correlation_id.
    
    Args:
        failure_event: The base failure event
        fallback_result: Optional fallback result containing attempted selectors
        correlation_id: Optional correlation ID. If not provided, will get/create one.
    
    Returns:
        FailureEvent with full context (attempted_fallbacks and correlation_id)
    """
    # AC2: Add attempted_fallbacks from chain
    failure_event = add_fallback_context_to_failure(failure_event, fallback_result)
    
    # AC4: Add correlation_id
    failure_event = add_correlation_to_failure(failure_event, correlation_id)
    
    # AC4: Set log level based on criticality
    log_level = "ERROR" if fallback_result and fallback_result.fallback_executed else "WARNING"
    context = failure_event.context.copy()
    context["log_level"] = log_level
    
    return FailureEvent(
        selector_id=failure_event.selector_id,
        url=failure_event.url,
        timestamp=failure_event.timestamp,
        failure_type=failure_event.failure_type,
        error_message=failure_event.error_message,
        context=context,
    )


class FailureEventLogger:
    """
    Structured logger for failure events (AC4).
    
    This class provides structured logging with appropriate log levels
    based on failure severity.
    """
    
    def __init__(self, logger_name: str = "selector_failures"):
        """
        Initialize the failure event logger.
        
        Args:
            logger_name: Name of the logger to use
        """
        try:
            from src.observability.logger import get_logger
            self._logger = get_logger(logger_name)
        except ImportError:
            self._logger = logging.getLogger(logger_name)
    
    def log_failure_event(self, failure_event: FailureEvent) -> None:
        """
        Log failure event with structured logging (AC4).
        
        Args:
            failure_event: The failure event to log
        """
        # Determine log level from context
        log_level = failure_event.context.get("log_level", "WARNING")
        
        # AC3: ISO8601 timestamp
        log_entry = {
            "selector_id": failure_event.selector_id,
            "url": failure_event.url,
            "timestamp": failure_event.timestamp.isoformat(),
            "failure_type": failure_event.failure_type.value,
            "extractor_id": failure_event.context.get("extractor_id"),
            "attempted_fallbacks": failure_event.context.get("attempted_fallbacks", []),
            "correlation_id": failure_event.context.get("correlation_id"),
        }
        
        # AC4: Log level based on severity
        if log_level == "ERROR":
            self._logger.error("failure_event", extra=log_entry)
        else:
            self._logger.warning("failure_event", extra=log_entry)
    
    def log_with_details(
        self,
        failure_event: FailureEvent,
        additional_context: Optional[dict] = None,
    ) -> None:
        """
        Log failure event with additional context.
        
        Args:
            failure_event: The failure event to log
            additional_context: Optional additional context to include
        """
        log_level = failure_event.context.get("log_level", "WARNING")
        
        log_entry = {
            "selector_id": failure_event.selector_id,
            "url": failure_event.url,
            "timestamp": failure_event.timestamp.isoformat(),
            "failure_type": failure_event.failure_type.value,
            "extractor_id": failure_event.context.get("extractor_id"),
            "attempted_fallbacks": failure_event.context.get("attempted_fallbacks", []),
            "correlation_id": failure_event.context.get("correlation_id"),
        }
        
        if additional_context:
            log_entry.update(additional_context)
        
        if log_level == "ERROR":
            self._logger.error("failure_event", extra=log_entry)
        else:
            self._logger.warning("failure_event", extra=log_entry)


def create_failure_event(
    selector_id: str,
    page_url: str,
    failure_type: FailureType,
    extractor_id: str,
    error_message: Optional[str] = None,
) -> FailureEvent:
    """
    Create a failure event with required fields (AC4).

    Args:
        selector_id: ID/name of the failed selector
        page_url: URL of the page being extracted
        failure_type: Type of failure detected
        extractor_id: ID of the extractor running the selector
        error_message: Optional error message

    Returns:
        FailureEvent with all required fields populated
    """
    return FailureEvent(
        selector_id=selector_id,
        url=page_url,
        timestamp=datetime.now(timezone.utc),
        failure_type=failure_type,
        error_message=error_message,
        context={"extractor_id": extractor_id},
    )


def submit_failure_with_timeout(
    failure_event: FailureEvent,
) -> bool:
    """
    Submit failure event with timeout handling (Story 3-4).
    
    This is the Story 3-4 integration point - it uses submit_with_timeout
    instead of the basic submit to ensure:
    - AC1: Total latency ≤ 5 seconds (NFR1)
    - AC2: Timeout handling (default 30s per NFR4)
    - AC3: Graceful handling - don't crash scraper on timeout
    
    Args:
        failure_event: The failure event to submit
        
    Returns:
        True always (AC3: don't crash scraper)
    """
    return submit_with_timeout(failure_event)


def submit_success_for_learning(
    selector_id: str,
    page_url: str,
    extractor_id: str,
    extraction_duration_ms: int,
    confidence_score: float = 1.0,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Submit success event for learning (Story 3-5 - AC3).
    
    When learning-mode is enabled, successful extractions are captured
    and submitted to the adaptive module to update stability scores.
    
    Args:
        selector_id: ID/name of the successful selector
        page_url: URL of the page being extracted
        extractor_id: ID of the extractor running the selector
        extraction_duration_ms: How long extraction took in milliseconds
        confidence_score: Confidence score of the extraction result
        context: Optional additional context
        
    Returns:
        True always (don't crash scraper)
    """
    success_event = SuccessEvent(
        selector_id=selector_id,
        page_url=page_url,
        timestamp=datetime.now(timezone.utc),
        extractor_id=extractor_id,
        extraction_duration_ms=extraction_duration_ms,
        confidence_score=confidence_score,
        context=context or {},
    )
    
    return submit_success_event_to_db(success_event)
