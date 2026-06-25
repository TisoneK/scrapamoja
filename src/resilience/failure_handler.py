"""
Failure Handler

Centralized failure handling coordinator that manages failure detection,
classification, recovery actions, and event publishing for all resilience components.
"""

import asyncio
import traceback
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from .interfaces import IFailureHandler, IEventSubscriber
from .models.failure_event import FailureEvent, FailureSeverity, FailureCategory, RecoveryAction
from .events import EventBus, get_event_bus, publish_failure_event, publish_recovery_event
from .logging.resilience_logger import get_logger
from .correlation import get_correlation_id, set_correlation_id
from .exceptions import ResilienceException


class FailureHandler(IFailureHandler, IEventSubscriber):
    """Centralized failure handler for resilience components."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize failure handler.
        
        Args:
            event_bus: Event bus for publishing events (uses global if not provided)
        """
        self.event_bus = event_bus or get_event_bus()
        self.logger = get_logger("failure_handler")
        self.failure_handlers: Dict[str, List[Callable]] = {}
        self.failure_statistics: Dict[str, Any] = {
            "total_failures": 0,
            "failures_by_category": {},
            "failures_by_severity": {},
            "resolved_failures": 0,
            "unresolved_failures": 0
        }
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the failure handler."""
        if self._initialized:
            return
        
        # Subscribe to global events
        await self.event_bus.subscribe_global(self.handle_event)
        
        # Register default failure handlers
        self._register_default_handlers()
        
        self._initialized = True
        self.logger.info(
            "Failure handler initialized",
            event_type="handler_initialized",
            component="failure_handler"
        )
    
    async def shutdown(self) -> None:
        """Shutdown the failure handler gracefully."""
        if not self._initialized:
            return
        
        # Unsubscribe from events
        # Note: In a real implementation, we'd store subscription IDs and unsubscribe
        
        self._initialized = False
        self.logger.info(
            "Failure handler shutdown",
            event_type="handler_shutdown",
            component="failure_handler"
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "registered_handlers": len(self.failure_handlers),
            "statistics": self.failure_statistics.copy()
        }
    
    async def handle_failure(
        self,
        failure_event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a failure event with appropriate recovery actions.
        
        Args:
            failure_event: Failure event details
            context: Additional context information
            
        Returns:
            Handling result with recovery actions taken
        """
        try:
            # Ensure correlation ID is set
            correlation_id = failure_event.get("correlation_id") or get_correlation_id()
            if correlation_id:
                set_correlation_id(correlation_id)
            
            # Create FailureEvent object
            failure = FailureEvent.from_dict(failure_event)
            failure.context.update(context)
            
            # Update statistics
            self._update_statistics(failure)
            
            # Log the failure
            self.logger.error(
                f"Handling failure: {failure.message}",
                event_type="failure_handling",
                correlation_id=failure.correlation_id,
                context={
                    "failure_id": failure.id,
                    "severity": failure.severity.value,
                    "category": failure.category.value,
                    "source": failure.source
                },
                component="failure_handler"
            )
            
            # Publish failure event
            await publish_failure_event(
                failure_type=failure.category.value,
                message=failure.message,
                severity=failure.severity.value,
                job_id=failure.job_id,
                context=failure.to_dict(),
                component=failure.source
            )
            
            # Get appropriate handler
            handler_result = await self._execute_failure_handler(failure)
            
            # Mark as resolved if handler succeeded
            if handler_result.get("success", False):
                recovery_action = RecoveryAction(handler_result.get("recovery_action", "manual"))
                failure.mark_resolved(recovery_action, handler_result.get("resolution_time"))
                
                # Publish recovery event
                await publish_recovery_event(
                    recovery_type="automatic",
                    original_error=failure.message,
                    action_taken=recovery_action.value,
                    job_id=failure.job_id,
                    context={"failure_id": failure.id},
                    component=failure.source
                )
                
                self.logger.info(
                    f"Failure resolved: {failure.message}",
                    event_type="failure_resolved",
                    correlation_id=failure.correlation_id,
                    context={
                        "failure_id": failure.id,
                        "recovery_action": recovery_action.value,
                        "resolution_time": failure.resolution_time
                    },
                    component="failure_handler"
                )
            
            return {
                "success": handler_result.get("success", False),
                "failure_id": failure.id,
                "action_taken": handler_result.get("action_taken", "none"),
                "recovery_action": handler_result.get("recovery_action"),
                "resolution_time": failure.resolution_time,
                "resolved": failure.resolved,
                "context": handler_result.get("context", {})
            }
            
        except Exception as e:
            self.logger.error(
                f"Error handling failure: {e}",
                event_type="failure_handler_error",
                correlation_id=get_correlation_id(),
                context={
                    "error": str(e),
                    "stack_trace": traceback.format_exc()
                },
                component="failure_handler"
            )
            
            return {
                "success": False,
                "error": str(e),
                "action_taken": "error",
                "resolved": False
            }
    
    async def register_failure_handler(
        self,
        failure_type: str,
        handler: Callable
    ) -> None:
        """
        Register a handler for specific failure types.
        
        Args:
            failure_type: Type of failure to handle
            handler: Handler function
        """
        if failure_type not in self.failure_handlers:
            self.failure_handlers[failure_type] = []
        
        self.failure_handlers[failure_type].append(handler)
        
        self.logger.info(
            f"Registered failure handler for type: {failure_type}",
            event_type="handler_registered",
            context={"failure_type": failure_type},
            component="failure_handler"
        )
    
    async def get_failure_statistics(
        self,
        job_id: Optional[str] = None,
        time_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Get failure statistics.
        
        Args:
            job_id: Optional job identifier filter
            time_range: Optional time range filter
            
        Returns:
            Failure statistics
        """
        # In a real implementation, this would filter by job_id and time_range
        # For now, return overall statistics
        return self.failure_statistics.copy()
    
    async def handle_event(self, event) -> None:
        """Handle resilience events."""
        # Handle events related to failures
        if hasattr(event, 'event_type') and event.event_type == "failure_event":
            # Process failure events if needed
            pass
    
    def _register_default_handlers(self) -> None:
        """Register default failure handlers for common failure types."""
        
        # Network failure handler
        async def handle_network_failure(failure: FailureEvent) -> Dict[str, Any]:
            return {
                "success": True,
                "action_taken": "retry_with_backoff",
                "recovery_action": "retry",
                "context": {"retry_delay": 5.0}
            }
        
        # Browser failure handler
        async def handle_browser_failure(failure: FailureEvent) -> Dict[str, Any]:
            return {
                "success": True,
                "action_taken": "restart_browser",
                "recovery_action": "restart",
                "context": {"preserve_session": True}
            }
        
        # System failure handler
        async def handle_system_failure(failure: FailureEvent) -> Dict[str, Any]:
            if failure.severity == FailureSeverity.CRITICAL:
                return {
                    "success": True,
                    "action_taken": "abort_operation",
                    "recovery_action": "abort",
                    "context": {"reason": "critical_system_failure"}
                }
            else:
                return {
                    "success": True,
                    "action_taken": "cleanup_and_retry",
                    "recovery_action": "retry",
                    "context": {"cleanup_resources": True}
                }
        
        # Application failure handler
        async def handle_application_failure(failure: FailureEvent) -> Dict[str, Any]:
            return {
                "success": True,
                "action_taken": "skip_operation",
                "recovery_action": "skip",
                "context": {"continue_with_next": True}
            }
        
        # External failure handler
        async def handle_external_failure(failure: FailureEvent) -> Dict[str, Any]:
            return {
                "success": True,
                "action_taken": "retry_with_exponential_backoff",
                "recovery_action": "retry",
                "context": {"max_retries": 5}
            }
        
        # Register handlers
        asyncio.create_task(self.register_failure_handler("network", handle_network_failure))
        asyncio.create_task(self.register_failure_handler("browser", handle_browser_failure))
        asyncio.create_task(self.register_failure_handler("system", handle_system_failure))
        asyncio.create_task(self.register_failure_handler("application", handle_application_failure))
        asyncio.create_task(self.register_failure_handler("external", handle_external_failure))
    
    async def _execute_failure_handler(self, failure: FailureEvent) -> Dict[str, Any]:
        """Execute the appropriate failure handler for the failure."""
        failure_type = failure.category.value
        
        # Get handlers for this failure type
        handlers = self.failure_handlers.get(failure_type, [])
        
        if not handlers:
            # No specific handler, use default handling
            return {
                "success": False,
                "action_taken": "no_handler",
                "context": {"failure_type": failure_type}
            }
        
        # Execute first handler (could implement handler chaining)
        try:
            handler = handlers[0]
            if asyncio.iscoroutinefunction(handler):
                result = await handler(failure)
            else:
                result = handler(failure)
            
            return result or {
                "success": False,
                "action_taken": "handler_no_result"
            }
            
        except Exception as e:
            self.logger.error(
                f"Error in failure handler: {e}",
                event_type="handler_error",
                correlation_id=failure.correlation_id,
                context={
                    "failure_id": failure.id,
                    "failure_type": failure_type,
                    "error": str(e),
                    "stack_trace": traceback.format_exc()
                },
                component="failure_handler"
            )
            
            return {
                "success": False,
                "action_taken": "handler_error",
                "error": str(e)
            }
    
    def _update_statistics(self, failure: FailureEvent) -> None:
        """Update failure statistics."""
        self.failure_statistics["total_failures"] += 1
        
        # Update by category
        category = failure.category.value
        self.failure_statistics["failures_by_category"][category] = \
            self.failure_statistics["failures_by_category"].get(category, 0) + 1
        
        # Update by severity
        severity = failure.severity.value
        self.failure_statistics["failures_by_severity"][severity] = \
            self.failure_statistics["failures_by_severity"].get(severity, 0) + 1
        
        # Update resolved/unresolved counts
        if failure.resolved:
            self.failure_statistics["resolved_failures"] += 1
        else:
            self.failure_statistics["unresolved_failures"] += 1


# Global failure handler instance
_failure_handler = FailureHandler()


def get_failure_handler() -> FailureHandler:
    """Get the global failure handler instance."""
    return _failure_handler


async def handle_failure(
    failure_event: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Handle a failure event using the global failure handler."""
    return await _failure_handler.handle_failure(
        failure_event, context or {}
    )


async def register_failure_handler(
    failure_type: str,
    handler: Callable
) -> None:
    """Register a failure handler using the global failure handler."""
    await _failure_handler.register_failure_handler(failure_type, handler)
