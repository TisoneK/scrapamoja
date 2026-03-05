"""
Failure Detection Service for detecting and recording selector resolution failures.

This service subscribes to selector failure events, classifies errors,
and triggers stability scoring updates.
"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING

from ..db.repositories.failure_event_repository import FailureEventRepository
from ..db.models.failure_event import ErrorType
from ..db.models import FailureEvent
from .stability_scoring import StabilityScoringService, FailureSeverity

if TYPE_CHECKING:
    from src.observability.events import Event


# Logger for this module
logger = logging.getLogger(__name__)


class FailureDetectorService:
    """
    Service for detecting and recording selector failures.
    
    This service:
    - Subscribes to selector failure events from the event bus
    - Classifies errors into types (empty_result, exception, timeout, validation)
    - Determines severity based on error type and context
    - Persists failure events to database
    - Triggers stability scoring updates
    - Enforces 1-second SLA for event processing
    """
    
    # Timeout threshold in seconds
    DEFAULT_TIMEOUT_THRESHOLD = 30.0
    
    # Severity thresholds for resolution time
    TIMEOUT_SEVERITY_THRESHOLD = 60.0  # 60 seconds = critical
    
    # SLA threshold for event processing (1 second as per AC2)
    SLA_THRESHOLD_SECONDS = 1.0
    
    def __init__(
        self,
        failure_repository: FailureEventRepository,
        stability_service: Optional[StabilityScoringService] = None,
        timeout_threshold: float = DEFAULT_TIMEOUT_THRESHOLD,
        enforce_sla: bool = True,
    ):
        """
        Initialize the failure detector service.
        
        Args:
            failure_repository: Repository for storing failure events
            stability_service: Optional stability scoring service for integration
            timeout_threshold: Threshold in seconds to classify as timeout
            enforce_sla: Whether to enforce 1-second SLA for processing
        """
        self.repository = failure_repository
        self.stability_service = stability_service
        self.timeout_threshold = timeout_threshold
        self.enforce_sla = enforce_sla
        self._subscription_id: Optional[str] = None
        self._event_bus = None
        self._sla_violations = 0
        self._total_processed = 0
    
    async def on_selector_failed(
        self,
        selector_name: str,
        strategy: str,
        failure_reason: str,
        resolution_time: float,
        recipe_id: Optional[str] = None,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> FailureEvent:
        """
        Handle selector failure event from selector engine.
        
        This method:
        1. Tracks processing time for SLA compliance
        2. Classifies the error type
        3. Determines severity
        4. Creates and persists the failure event
        5. Triggers stability scoring update
        
        Args:
            selector_name: Name of the failed selector
            strategy: Strategy that was attempted
            failure_reason: Detailed error message
            resolution_time: Time taken before failure (seconds)
            recipe_id: Optional associated recipe
            sport: Optional sport context
            site: Optional site identifier
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            Created FailureEvent instance
        """
        # Start timing for SLA verification
        start_time = time.perf_counter()
        
        # Classify error type
        error_type = self.classify_error_type(failure_reason, strategy, resolution_time)
        
        # Determine severity
        severity = self.determine_severity(error_type, resolution_time)
        
        # Create failure event
        failure_event = self.repository.create(
            selector_id=selector_name,
            error_type=error_type,
            recipe_id=recipe_id,
            sport=sport,
            site=site,
            failure_reason=failure_reason,
            strategy_used=strategy,
            resolution_time=resolution_time * 1000,  # Convert to ms
            severity=severity,
            correlation_id=correlation_id,
        )
        
        # Trigger stability scoring if service is available and recipe_id exists
        if self.stability_service and recipe_id:
            await self._trigger_stability_update(recipe_id, severity)
        
        # Verify SLA compliance
        processing_time = time.perf_counter() - start_time
        self._total_processed += 1
        
        # Only enforce/track SLA if enabled
        if self.enforce_sla:
            if processing_time > self.SLA_THRESHOLD_SECONDS:
                self._sla_violations += 1
                logger.warning(
                    f"SLA violation: processing took {processing_time:.3f}s "
                    f"(threshold: {self.SLA_THRESHOLD_SECONDS}s) for selector {selector_name}"
                )
        else:
            # Still track stats even if not enforcing
            if processing_time > self.SLA_THRESHOLD_SECONDS:
                self._sla_violations += 1
        
        return failure_event
    
    def classify_error_type(
        self,
        failure_reason: str,
        strategy: str,
        resolution_time: float,
    ) -> str:
        """
        Classify error into: empty_result, exception, timeout, validation.
        
        Args:
            failure_reason: Detailed error message
            strategy: Strategy that was attempted
            resolution_time: Time taken before failure (seconds)
            
        Returns:
            Error type classification
        """
        reason_lower = failure_reason.lower() if failure_reason else ""
        
        # Check for timeout first (time-based)
        if resolution_time >= self.timeout_threshold:
            return ErrorType.TIMEOUT
        
        # Check for empty result
        if "no elements" in reason_lower or "empty" in reason_lower:
            return ErrorType.EMPTY_RESULT
        
        # Check for validation errors
        if "validation" in reason_lower or "invalid" in reason_lower:
            return ErrorType.VALIDATION
        
        # Check for exceptions/errors
        if "exception" in reason_lower or "error" in reason_lower:
            return ErrorType.EXCEPTION
        
        # Check for specific error patterns
        if "timeout" in reason_lower:
            return ErrorType.TIMEOUT
        
        if "not found" in reason_lower or "could not" in reason_lower:
            return ErrorType.EMPTY_RESULT
        
        # Default to exception
        return ErrorType.EXCEPTION
    
    def determine_severity(
        self,
        error_type: str,
        resolution_time: float,
    ) -> str:
        """
        Determine severity based on error type and context.
        
        Args:
            error_type: Classified error type
            resolution_time: Time taken before failure (seconds)
            
        Returns:
            Severity level: minor, moderate, critical
        """
        # Get default severity for error type
        severity = ErrorType.get_default_severity(error_type)
        
        # Override with time-based severity for timeouts
        if error_type == ErrorType.TIMEOUT:
            if resolution_time >= self.TIMEOUT_SEVERITY_THRESHOLD:
                severity = FailureSeverity.CRITICAL
            else:
                severity = FailureSeverity.MODERATE
        
        # Override with critical for very slow resolutions
        if resolution_time >= self.TIMEOUT_SEVERITY_THRESHOLD * 2:
            severity = FailureSeverity.CRITICAL
        
        return severity
    
    async def _trigger_stability_update(
        self,
        recipe_id: str,
        severity: str,
    ) -> None:
        """
        Trigger stability scoring update for the recipe.
        
        Args:
            recipe_id: Recipe identifier
            severity: Failure severity
        """
        try:
            if self.stability_service:
                await self.stability_service.on_selector_failure(
                    recipe_id=recipe_id,
                    selector_id=None,  # We don't track specific selector
                    severity=severity,
                )
        except Exception as e:
            # Log error but don't fail the failure detection
            import logging
            logging.getLogger(__name__).error(
                f"Failed to trigger stability update for recipe {recipe_id}: {e}"
            )
    
    async def handle_event(self, event: "Event") -> None:
        """
        Handle selector failed event from the event bus.
        
        This is the event handler that gets called when a selector.failed
        event is published.
        
        Args:
            event: Event from the event bus
        """
        data = event.data
        
        # Extract sport/site from context if available
        sport = data.get("sport")
        site = data.get("site")
        recipe_id = data.get("recipe_id")
        
        # Extract correlation ID if available
        correlation_id = event.correlation_id
        
        # Call the main handler
        await self.on_selector_failed(
            selector_name=data.get("selector_name", ""),
            strategy=data.get("strategy", "unknown"),
            failure_reason=data.get("failure_reason", "Unknown error"),
            resolution_time=data.get("resolution_time", 0.0),
            recipe_id=recipe_id,
            sport=sport,
            site=site,
            correlation_id=correlation_id,
        )
    
    def subscribe_to_events(self) -> str:
        """
        Subscribe to selector.failed events from the event bus.
        
        Returns:
            Subscription ID
        """
        from src.observability.events import (
            EventTypes, 
            subscribe_to_events,
        )
        
        # Store reference to unsubscribe later
        self._subscription_id = subscribe_to_events(
            EventTypes.SELECTOR_FAILED,
            self.handle_event,
        )
        
        return self._subscription_id
    
    def unsubscribe_from_events(self) -> bool:
        """
        Unsubscribe from selector.failed events.
        
        Returns:
            True if unsubscribed successfully
        """
        from src.observability.events import unsubscribe_from_events
        
        if self._subscription_id:
            result = unsubscribe_from_events(self._subscription_id)
            self._subscription_id = None
            return result
        return False
    
    def get_failure_statistics(
        self,
        selector_id: Optional[str] = None,
        recipe_id: Optional[str] = None,
        sport: Optional[str] = None,
        site: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get failure statistics for analysis.
        
        Args:
            selector_id: Optional filter by selector
            recipe_id: Optional filter by recipe
            sport: Optional filter by sport
            site: Optional filter by site
            
        Returns:
            Dictionary with failure statistics
        """
        # Get recent failures
        failures = self.repository.get_recent_failures(
            limit=100,
            sport=sport,
            site=site,
        )
        
        # Filter by selector_id if provided
        if selector_id:
            failures = [f for f in failures if f.selector_id == selector_id]
        
        # Filter by recipe_id if provided
        if recipe_id:
            failures = [f for f in failures if f.recipe_id == recipe_id]
        
        # Calculate statistics
        total = len(failures)
        error_type_counts = {}
        severity_counts = {}
        
        for failure in failures:
            # Count by error type
            error_type_counts[failure.error_type] = error_type_counts.get(failure.error_type, 0) + 1
            
            # Count by severity
            severity_counts[failure.severity] = severity_counts.get(failure.severity, 0) + 1
        
        return {
            "total_failures": total,
            "error_type_distribution": error_type_counts,
            "severity_distribution": severity_counts,
            "recent_failures": [f.to_dict() for f in failures[:10]],
        }
    
    def get_sla_stats(self) -> Dict[str, Any]:
        """
        Get SLA compliance statistics.
        
        Returns:
            Dictionary with SLA statistics including violations count
        """
        return {
            "total_processed": self._total_processed,
            "sla_violations": self._sla_violations,
            "compliance_rate": (
                (self._total_processed - self._sla_violations) / self._total_processed * 100
                if self._total_processed > 0 else 100.0
            ),
            "sla_threshold_seconds": self.SLA_THRESHOLD_SECONDS,
        }
