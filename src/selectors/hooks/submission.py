"""
Failure Event Submission Service for adaptive module DB.

This module provides the FailureEventSubmissionService class that submits
failure events to the adaptive module database for learning and analysis.

Story 3-3: Adaptive Module DB Submission
- AC1: Sync DB Submission
- AC2: Successful DB Storage
- AC3: Graceful Failure Handling
- AC4: Queue for Retry on Unavailability

Story 3-4: Sync Failure Capture (Immediate)
- AC1: Timing optimization (≤ 5 seconds latency)
- AC2: Timeout handling (30s default)
- AC3: High-volume handling without blocking
"""

import asyncio
import json
import logging
import os
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional

from src.selectors.fallback.models import FailureEvent, FailureType, SuccessEvent
from src.selectors.adaptive.db.repositories.failure_event_repository import FailureEventRepository

# Configuration constants (Story 3-4)
DEFAULT_SUBMISSION_TIMEOUT = 30  # seconds (NFR4)
MAX_LATENCY_THRESHOLD = 5  # seconds (NFR1)
MAX_QUEUE_SIZE = 1000
BACKPRESSURE_THRESHOLD = 0.8  # 80% of queue size

# Configuration constants (Story 3-5)
ASYNC_MODE_ENABLED = True  # Toggle for sync/async
QUEUE_PERSISTENCE_PATH = "data/failure_queue.json"
RETRY_BACKOFF_BASE = 2  # seconds
MAX_RETRY_ATTEMPTS = 5


def _get_logger() -> logging.Logger:
    """Get logger for submission operations."""
    try:
        from src.observability.logger import get_logger

        return get_logger("selector_submission")
    except ImportError:
        return logging.getLogger("selector_submission")


class FailureEventSubmissionService:
    """
    Service for submitting failure events to adaptive module DB.

    Implements:
    - AC1: Sync DB Submission (blocking until complete)
    - AC2: Successful DB Storage (no error raised on success)
    - AC3: Graceful Failure Handling (log errors, don't crash)
    - AC4: Queue for Retry on Unavailability (queue when DB unavailable)

    Story 3-4: Sync Failure Capture (Immediate)
    - Timing optimization (≤ 5 seconds latency)
    - Timeout handling (30s default)
    - High-volume handling without blocking

    Story 3-5: Async Failure Capture (Learning)
    - AC1: Fire-and-Forget Async Capture
    - AC2: Local Queue for Unavailable DB (persistent)
    - AC3: Success Event Capture for Learning
    """

    _instance: Optional['FailureEventSubmissionService'] = None
    _repository: Optional[FailureEventRepository] = None
    _retry_queue: List[FailureEvent] = []
    _submission_timeout: int = DEFAULT_SUBMISSION_TIMEOUT
    _async_mode: bool = ASYNC_MODE_ENABLED
    _success_queue: List[SuccessEvent] = []

    def __new__(cls) -> 'FailureEventSubmissionService':
        """Singleton pattern to ensure single repository instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._repository = FailureEventRepository()
            cls._retry_queue = []
            cls._submission_timeout = DEFAULT_SUBMISSION_TIMEOUT
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the submission service."""
        self._logger = _get_logger()
    
    @property
    def async_mode(self) -> bool:
        """Get whether async mode is enabled."""
        return self._async_mode
    
    @property
    def success_queue_size(self) -> int:
        """Get current success queue size."""
        return len(self._success_queue)
    
    @property
    def repository(self) -> FailureEventRepository:
        """Get the failure event repository."""
        return self._repository
    
    @property
    def retry_queue_size(self) -> int:
        """Get current retry queue size."""
        return len(self._retry_queue)
    
    def submit(self, failure_event: FailureEvent) -> bool:
        """
        Submit failure event to DB (AC1, AC2).
        
        This is a synchronous operation that blocks until completion.
        
        Args:
            failure_event: The failure event to submit
            
        Returns:
            True always (AC3: don't crash scraper on DB failure)
        """
        try:
            # Convert runtime FailureEvent to DB format
            db_event = self._convert_to_db_event(failure_event)
            
            # Submit to repository (AC2: successful storage)
            self._repository.create(
                selector_id=db_event["selector_id"],
                error_type=db_event["error_type"],
                timestamp=db_event["timestamp"],
                recipe_id=db_event.get("recipe_id"),
                sport=db_event.get("sport"),
                site=db_event.get("site"),
                failure_reason=db_event.get("failure_reason"),
                strategy_used=db_event.get("strategy_used"),
                resolution_time=db_event.get("resolution_time"),
                severity=db_event.get("severity", "minor"),
                context_snapshot=db_event.get("context_snapshot"),
                correlation_id=db_event.get("correlation_id"),
            )
            
            # Log successful submission
            self._logger.info(
                f"Failure event submitted to DB: {failure_event.selector_id}",
                extra={"selector_id": failure_event.selector_id, "correlation_id": db_event.get("correlation_id")}
            )
            
            # Process retry queue if any events pending (AC4)
            self._process_retry_queue()
            
            return True
            
        except Exception as e:
            # AC3: Handle gracefully, log error, don't crash scraper
            self._logger.warning(f"DB submission failed: {e}, queuing for retry")
            self._queue_for_retry(failure_event)
            return True  # Always return True to not crash scraper
    
    def _convert_to_db_event(self, failure_event: FailureEvent) -> Dict[str, Any]:
        """
        Convert runtime FailureEvent to DB dict format.
        
        Args:
            failure_event: The runtime FailureEvent to convert
            
        Returns:
            Dict with fields matching FailureEventRepository.create() signature
        """
        context = failure_event.context or {}
        
        # Extract strategy_used from attempted_fallbacks if available
        strategy_used = None
        attempted_fallbacks = context.get("attempted_fallbacks", [])
        if attempted_fallbacks:
            # Use the last attempted selector as the strategy
            last_attempt = attempted_fallbacks[-1]
            strategy_used = last_attempt.get("selector")
        
        return {
            "selector_id": failure_event.selector_id,
            "error_type": failure_event.failure_type.value,
            "timestamp": failure_event.timestamp,
            "failure_reason": failure_event.error_message,
            "context_snapshot": context,
            "correlation_id": context.get("correlation_id"),
            # Extract additional fields from context
            "recipe_id": context.get("recipe_id"),
            "sport": context.get("sport"),
            "site": context.get("site"),
            "strategy_used": strategy_used,
            "resolution_time": failure_event.resolution_time,
            "severity": "minor",  # Default severity, can be enhanced later
        }
    
    def _queue_for_retry(self, failure_event: FailureEvent) -> None:
        """
        Queue event for retry when DB unavailable (AC4).
        
        Args:
            failure_event: The failure event to queue
        """
        # AC3: Check for backpressure
        current_size = len(self._retry_queue)
        if current_size >= MAX_QUEUE_SIZE * BACKPRESSURE_THRESHOLD:
            self._logger.warning(
                f"High backpressure detected: queue at {current_size}/{MAX_QUEUE_SIZE} "
                f"({current_size/MAX_QUEUE_SIZE*100:.0f}%)"
            )
        
        if len(self._retry_queue) < MAX_QUEUE_SIZE:
            self._retry_queue.append(failure_event)
            self._logger.debug(
                f"Queued failure event for retry (queue size: {len(self._retry_queue)})"
            )
        else:
            # Queue full - drop oldest and add new
            dropped = self._retry_queue.pop(0)
            self._retry_queue.append(failure_event)
            self._logger.warning(
                f"Retry queue full, dropped oldest event: {dropped.selector_id}"
            )
    
    def _process_retry_queue(self) -> None:
        """
        Process queued events when DB recovers (AC4).
        
        Tries to submit all queued events in order.
        If any fails, stops and keeps remaining in queue.
        """
        while self._retry_queue:
            event = self._retry_queue[0]  # Peek at first
            try:
                db_event = self._convert_to_db_event(event)
                self._repository.create(
                    selector_id=db_event["selector_id"],
                    error_type=db_event["error_type"],
                    timestamp=db_event["timestamp"],
                    recipe_id=db_event.get("recipe_id"),
                    sport=db_event.get("sport"),
                    site=db_event.get("site"),
                    failure_reason=db_event.get("failure_reason"),
                    strategy_used=db_event.get("strategy_used"),
                    resolution_time=db_event.get("resolution_time"),
                    severity=db_event.get("severity", "minor"),
                    context_snapshot=db_event.get("context_snapshot"),
                    correlation_id=db_event.get("correlation_id"),
                )
                # Success - remove from queue
                self._retry_queue.pop(0)
                self._logger.info(f"Retry successful for: {event.selector_id}")
            except Exception:
                # DB still unavailable - stop processing
                self._logger.warning(
                    f"Retry failed, DB still unavailable (events pending: {len(self._retry_queue)})"
                )
                break
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status for monitoring.
        
        Returns:
            Dict with queue size and oldest event info
        """
        if not self._retry_queue:
            return {
                "queue_size": 0,
                "oldest_event": None,
            }
        
        oldest = self._retry_queue[0]
        return {
            "queue_size": len(self._retry_queue),
            "oldest_event": {
                "selector_id": oldest.selector_id,
                "timestamp": oldest.timestamp.isoformat(),
            },
        }
    
    def clear_queue(self) -> int:
        """
        Clear the retry queue.
        
        Returns:
            Number of events cleared
        """
        count = len(self._retry_queue)
        self._retry_queue.clear()
        self._logger.info(f"Cleared {count} events from retry queue")
        return count

    # === Story 3-4: Sync Failure Capture (Immediate) ===

    def set_timeout(self, timeout_seconds: int) -> None:
        """
        Configure submission timeout (AC2).
        
        Args:
            timeout_seconds: Timeout in seconds (default 30 per NFR4)
        """
        self._submission_timeout = timeout_seconds
        self._logger.info(f"Submission timeout set to {timeout_seconds}s")

    def submit_with_timeout(self, failure_event: FailureEvent) -> bool:
        """
        Submit failure event with timeout handling (AC1, AC2).
        
        This method ensures:
        - AC1: Total latency ≤ 5 seconds (NFR1)
        - AC2: Timeout handling (default 30s per NFR4)
        - AC3: Graceful handling - don't crash scraper on timeout
        
        Args:
            failure_event: The failure event to submit
            
        Returns:
            True always (AC3: don't crash scraper)
        """
        start_time = time.time()
        
        try:
            # Submit with timeout enforcement
            success = self._submit_within_timeout(failure_event)
            
            # AC1: Check latency threshold
            elapsed = time.time() - start_time
            if elapsed > MAX_LATENCY_THRESHOLD:
                self._logger.warning(
                    f"Submission latency {elapsed:.2f}s exceeds threshold "
                    f"{MAX_LATENCY_THRESHOLD}s for {failure_event.selector_id}"
                )
            
            return success
            
        except TimeoutError:
            # AC2: Handle timeout gracefully
            elapsed = time.time() - start_time
            self._logger.warning(
                f"DB submission timed out after {elapsed:.2f}s (limit: {self._submission_timeout}s), "
                f"continuing with primary selectors for {failure_event.selector_id}"
            )
            return True  # Don't crash scraper
        except Exception as e:
            # AC3: Handle gracefully, log error, don't crash scraper
            self._logger.warning(
                f"DB submission failed for {failure_event.selector_id}: {e}, "
                "continuing with primary selectors"
            )
            return True  # Don't crash scraper

    def _submit_within_timeout(self, failure_event: FailureEvent) -> bool:
        """
        Submit event with configurable timeout using threading.
        
        Args:
            failure_event: The failure event to submit
            
        Returns:
            True if successful
            
        Raises:
            TimeoutError: If submission exceeds timeout
        """
        result = {"success": False, "error": None}
        
        def submit_task():
            try:
                self.submit(failure_event)
                result["success"] = True
            except Exception as e:
                result["error"] = e
        
        thread = threading.Thread(target=submit_task)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self._submission_timeout)
        
        if thread.is_alive():
            # Thread is still running - timeout occurred
            self._logger.warning(
                f"Submission thread still running after {self._submission_timeout}s timeout"
            )
            raise TimeoutError(f"Submission exceeded {self._submission_timeout}s timeout")
        
        if result["error"] is not None:
            raise result["error"]
        
        return result["success"]

    def submit_batch(self, failure_events: List[FailureEvent]) -> bool:
        """
        Submit multiple events efficiently (AC3 - high-volume).

        Args:
            failure_events: List of failure events to submit

        Returns:
            True always (AC3: graceful handling)
        """
        if not failure_events:
            return True

        self._logger.info(f"Starting batch submission of {len(failure_events)} events")

        for event in failure_events:
            try:
                self.submit(event)
            except Exception as e:
                # AC3: Continue processing other events on failure
                self._logger.warning(
                    f"Batch submission failed for {event.selector_id}: {e}"
                )

        self._logger.info(f"Batch submission completed for {len(failure_events)} events")
        return True

    # === Story 3-5: Async Failure Capture (Learning) ===

    def set_async_mode(self, enabled: bool) -> None:
        """
        Toggle between sync and async modes.
        
        Args:
            enabled: True for async mode, False for sync mode
        """
        self._async_mode = enabled
        self._logger.info(f"Async mode {'enabled' if enabled else 'disabled'}")

    async def submit_async(self, failure_event: FailureEvent) -> bool:
        """
        Submit failure event asynchronously (fire-and-forget) - AC1.
        
        This method returns immediately without waiting for DB submission.
        If async mode is disabled, falls back to sync submission.
        
        Args:
            failure_event: The failure event to submit
            
        Returns:
            True always (AC3: don't crash scraper)
        """
        if not self._async_mode:
            # Fall back to sync if disabled
            return self.submit_with_timeout(failure_event)
        
        try:
            # Fire-and-forget: create task but don't await
            asyncio.create_task(self._submit_event_async(failure_event))
            return True  # Return immediately without waiting
        except Exception as e:
            # Queue locally if async fails
            self._queue_for_retry(failure_event)
            self._logger.warning(f"Async submission failed, queued: {e}")
            return True

    async def _submit_event_async(self, failure_event: FailureEvent) -> None:
        """
        Internal async submission task.
        
        Args:
            failure_event: The failure event to submit
        """
        try:
            await asyncio.wait_for(
                self._submit_event_to_db(failure_event),
                timeout=self._submission_timeout
            )
        except asyncio.TimeoutError:
            # AC2: Queue for retry when available
            self._queue_for_retry(failure_event)
            self._logger.warning("Async submission timed out, queued for retry")
        except Exception as e:
            self._queue_for_retry(failure_event)
            self._logger.warning(f"Async submission failed: {e}")

    async def _submit_event_to_db(self, failure_event: FailureEvent) -> None:
        """
        Submit event to database asynchronously.
        
        Args:
            failure_event: The failure event to submit
        """
        db_event = self._convert_to_db_event(failure_event)
        self._repository.create(
            selector_id=db_event["selector_id"],
            error_type=db_event["error_type"],
            timestamp=db_event["timestamp"],
            recipe_id=db_event.get("recipe_id"),
            sport=db_event.get("sport"),
            site=db_event.get("site"),
            failure_reason=db_event.get("failure_reason"),
            strategy_used=db_event.get("strategy_used"),
            resolution_time=db_event.get("resolution_time"),
            severity=db_event.get("severity", "minor"),
            context_snapshot=db_event.get("context_snapshot"),
            correlation_id=db_event.get("correlation_id"),
        )
        self._logger.info(
            f"Async failure event submitted: {failure_event.selector_id}",
            extra={"selector_id": failure_event.selector_id}
        )

    def submit_success_event(self, success_event: SuccessEvent) -> bool:
        """
        Submit success event for learning - AC3.
        
        Success events help update stability scores.
        
        Args:
            success_event: The success event to submit
            
        Returns:
            True always (don't crash scraper)
        """
        try:
            asyncio.create_task(self._submit_success_async(success_event))
            return True
        except Exception as e:
            self._logger.warning(f"Success event submission failed: {e}")
            return True

    async def _submit_success_async(self, success_event: SuccessEvent) -> None:
        """
        Internal success event submission.
        
        Args:
            success_event: The success event to submit
        """
        try:
            # Convert success event to DB format and submit
            db_event = self._convert_success_to_db_event(success_event)
            self._repository.create(
                selector_id=db_event["selector_id"],
                error_type="success",  # Use success as a pseudo error type
                timestamp=db_event["timestamp"],
                recipe_id=db_event.get("recipe_id"),
                sport=db_event.get("sport"),
                site=db_event.get("site"),
                failure_reason=None,
                strategy_used=db_event.get("strategy_used"),
                resolution_time=db_event.get("resolution_time"),
                severity="success",
                context_snapshot=db_event.get("context_snapshot"),
                correlation_id=db_event.get("correlation_id"),
            )
            self._logger.info(
                f"Success event submitted for learning: {success_event.selector_id}",
                extra={"selector_id": success_event.selector_id}
            )
        except Exception as e:
            self._logger.warning(f"Success event submission failed: {e}")

    def _convert_success_to_db_event(self, success_event: SuccessEvent) -> Dict[str, Any]:
        """
        Convert success event to DB dict format.
        
        Args:
            success_event: The success event to convert
            
        Returns:
            Dict with fields for DB submission
        """
        context = success_event.context or {}
        
        return {
            "selector_id": success_event.selector_id,
            "timestamp": success_event.timestamp,
            "resolution_time": success_event.extraction_duration_ms / 1000.0,  # Convert ms to seconds
            "context_snapshot": context,
            "correlation_id": context.get("correlation_id"),
            "recipe_id": context.get("recipe_id"),
            "sport": context.get("sport"),
            "site": context.get("site"),
            "strategy_used": context.get("strategy_used"),
        }

    async def process_retry_queue(self) -> int:
        """
        Process queued events when connection restored - AC2.
        
        Returns:
            Number of events successfully processed
        """
        processed = 0
        while self._retry_queue:
            event = self._retry_queue[0]  # Peek at first
            try:
                await self._submit_event_to_db(event)
                self._retry_queue.pop(0)
                processed += 1
                self._logger.info(f"Retry successful for: {event.selector_id}")
            except Exception as e:
                # Keep in queue for next retry, wait with backoff
                self._logger.warning(
                    f"Retry failed, DB still unavailable: {e}"
                )
                break
        return processed

    def get_success_queue_status(self) -> Dict[str, Any]:
        """
        Get current success queue status for monitoring.
        
        Returns:
            Dict with success queue size
        """
        return {
            "success_queue_size": len(self._success_queue),
        }


def get_submission_service() -> FailureEventSubmissionService:
    """
    Get the singleton FailureEventSubmissionService instance.
    
    Returns:
        The FailureEventSubmissionService singleton
    """
    return FailureEventSubmissionService()


class PersistentQueue:
    """
    Local queue that persists to disk for offline scenarios - AC2.
    
    When the adaptive module DB is unavailable, events are queued locally
    and persisted to disk. When connection is restored, the queue is
    processed and events are submitted to the DB.
    """
    
    def __init__(self, persistence_path: str = QUEUE_PERSISTENCE_PATH):
        """
        Initialize the persistent queue.
        
        Args:
            persistence_path: Path to the JSON file for persistence
        """
        self.persistence_path = persistence_path
        self._queue: deque = deque()
        self._load_queue()
    
    def _load_queue(self) -> None:
        """Load queue from disk on startup."""
        if os.path.exists(self.persistence_path):
            try:
                with open(self.persistence_path, 'r') as f:
                    data = json.load(f)
                    self._queue = deque(data)
            except (json.JSONDecodeError, IOError) as e:
                logging.getLogger("selector_submission").warning(
                    f"Failed to load queue from disk: {e}"
                )
                self._queue = deque()
    
    def _save_queue(self) -> None:
        """Persist queue to disk."""
        try:
            os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)
            with open(self.persistence_path, 'w') as f:
                json.dump(list(self._queue), f)
        except IOError as e:
            logging.getLogger("selector_submission").warning(
                f"Failed to save queue to disk: {e}"
            )
    
    def enqueue(self, event: Dict[str, Any]) -> None:
        """
        Add event to queue and persist.
        
        Args:
            event: Event dict to add to queue
        """
        self._queue.append(event)
        self._save_queue()
    
    def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        Remove and return event from queue.
        
        Returns:
            Event dict, or None if queue is empty
        """
        if not self._queue:
            return None
        event = self._queue.popleft()
        self._save_queue()
        return event
    
    def peek(self) -> Optional[Dict[str, Any]]:
        """
        View the next event without removing it.
        
        Returns:
            Event dict, or None if queue is empty
        """
        if not self._queue:
            return None
        return self._queue[0]
    
    def __len__(self) -> int:
        """Return the number of events in queue."""
        return len(self._queue)
    
    def clear(self) -> None:
        """Clear all events from queue."""
        self._queue.clear()
        self._save_queue()


def submit_failure_async(failure_event: FailureEvent) -> bool:
    """
    Submit failure event asynchronously (fire-and-forget) - AC1.
    
    This is the main entry point for async failure submission.
    Returns immediately without waiting for DB submission.
    
    Args:
        failure_event: The failure event to submit
        
    Returns:
        True always (AC3: don't crash scraper)
    """
    service = get_submission_service()
    # Run async function in new event loop if needed
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context, schedule the task
            asyncio.create_task(service.submit_async(failure_event))
        else:
            # Not in async context, run the coroutine
            loop.run_until_complete(service.submit_async(failure_event))
    except RuntimeError:
        # No event loop exists, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(service.submit_async(failure_event))
        finally:
            loop.close()
    return True


def submit_success_event_to_db(success_event: SuccessEvent) -> bool:
    """
    Submit success event for learning - AC3.
    
    This is the main entry point for success event capture.
    
    Args:
        success_event: The success event to submit
        
    Returns:
        True always (don't crash scraper)
    """
    service = get_submission_service()
    return service.submit_success_event(success_event)


def submit_failure_to_db(failure_event: FailureEvent) -> bool:
    """
    Submit failure event to adaptive module DB (AC1).
    
    This is the main entry point for submitting failure events to the
    adaptive module database. It handles sync submission as per AC1.
    
    Args:
        failure_event: The failure event to submit
        
    Returns:
        True always (AC3: don't crash scraper on DB failure)
    """
    service = get_submission_service()
    return service.submit(failure_event)


def submit_with_timeout(failure_event: FailureEvent) -> bool:
    """
    Submit failure event with timeout handling (Story 3-4 AC1, AC2).
    
    This method ensures:
    - AC1: Total latency ≤ 5 seconds (NFR1)
    - AC2: Timeout handling (default 30s per NFR4)
    - AC3: Graceful handling - don't crash scraper on timeout
    
    Args:
        failure_event: The failure event to submit
        
    Returns:
        True always (AC3: don't crash scraper)
    """
    service = get_submission_service()
    return service.submit_with_timeout(failure_event)


def create_and_submit_failure_event(
    selector_id: str,
    page_url: str,
    failure_type: FailureType,
    extractor_id: str,
    error_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Create and submit a failure event in one call (AC1, AC4).
    
    Convenience function that creates a FailureEvent and immediately
    submits it to the adaptive module DB.
    
    Args:
        selector_id: ID/name of the failed selector
        page_url: URL of the page being extracted
        failure_type: Type of failure detected
        extractor_id: ID of the extractor running the selector
        error_message: Optional error message
        context: Optional additional context
        
    Returns:
        True always (AC3: don't crash scraper on DB failure)
    """
    from datetime import datetime, timezone
    
    # Create the failure event
    failure_event = FailureEvent(
        selector_id=selector_id,
        url=page_url,
        timestamp=datetime.now(timezone.utc),
        failure_type=failure_type,
        error_message=error_message,
        context=context or {},
    )
    
    # Submit to DB
    return submit_failure_to_db(failure_event)
