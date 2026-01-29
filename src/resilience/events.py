"""
Resilience Event System

Provides event bus and event handling for resilience components including
failure events, retry events, checkpoint events, resource events, and abort events.
"""

from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from dataclasses import dataclass, field
import asyncio
import uuid
from .correlation import get_correlation_id


@dataclass
class ResilienceEvent:
    """Base event structure for all resilience-related events."""
    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    job_id: Optional[str] = None
    component: str = "resilience"
    severity: str = "info"  # info, warning, error, critical
    data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        if self.correlation_id is None:
            self.correlation_id = get_correlation_id()


class EventBus:
    """Event bus for publishing and subscribing to resilience events."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
        self._lock = asyncio.Lock()
    
    async def subscribe(
        self,
        event_type: str,
        handler: Callable[[ResilienceEvent], None]
    ) -> str:
        """Subscribe to specific event type."""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            subscription_id = str(uuid.uuid4())
            self._subscribers[event_type].append((subscription_id, handler))
            return subscription_id
    
    async def subscribe_global(
        self,
        handler: Callable[[ResilienceEvent], None]
    ) -> str:
        """Subscribe to all events."""
        async with self._lock:
            subscription_id = str(uuid.uuid4())
            self._global_subscribers.append((subscription_id, handler))
            return subscription_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        async with self._lock:
            # Remove from specific event subscribers
            for event_type, subscribers in self._subscribers.items():
                self._subscribers[event_type] = [
                    (sid, handler) for sid, handler in subscribers
                    if sid != subscription_id
                ]
            
            # Remove from global subscribers
            self._global_subscribers = [
                (sid, handler) for sid, handler in self._global_subscribers
                if sid != subscription_id
            ]
            
            return True
    
    async def publish(self, event: ResilienceEvent) -> None:
        """Publish an event to all subscribers."""
        # Ensure correlation ID is set
        if event.correlation_id is None:
            event.correlation_id = get_correlation_id()
        
        # Get subscribers for this event type
        specific_subscribers = self._subscribers.get(event.event_type, [])
        
        # Combine specific and global subscribers
        all_subscribers = specific_subscribers + self._global_subscribers
        
        # Call all subscribers asynchronously
        tasks = []
        for subscription_id, handler in all_subscribers:
            task = asyncio.create_task(self._safe_call_handler(handler, event))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_call_handler(
        self,
        handler: Callable[[ResilienceEvent], None],
        event: ResilienceEvent
    ) -> None:
        """Safely call event handler without exceptions."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            # Log error but don't propagate to avoid breaking event publishing
            print(f"Error in event handler: {e}")


# Global event bus instance
_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    return _event_bus


# Event creation helpers
def create_failure_event(
    failure_type: str,
    message: str,
    severity: str = "error",
    job_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> ResilienceEvent:
    """Create a failure event."""
    return ResilienceEvent(
        event_type="failure_event",
        severity=severity,
        job_id=job_id,
        component=component or "failure_handler",
        data={
            "failure_type": failure_type,
            "message": message,
            **(context or {})
        }
    )


def create_retry_event(
    operation: str,
    attempt: int,
    max_attempts: int,
    delay: float,
    severity: str = "info",
    job_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> ResilienceEvent:
    """Create a retry event."""
    return ResilienceEvent(
        event_type="retry_event",
        severity=severity,
        job_id=job_id,
        component=component or "retry_manager",
        data={
            "operation": operation,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "delay": delay,
            **(context or {})
        }
    )


def create_checkpoint_event(
    action: str,
    checkpoint_id: str,
    job_id: str,
    severity: str = "info",
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> ResilienceEvent:
    """Create a checkpoint event."""
    return ResilienceEvent(
        event_type="checkpoint_event",
        severity=severity,
        job_id=job_id,
        component=component or "checkpoint_manager",
        data={
            "action": action,
            "checkpoint_id": checkpoint_id,
            **(context or {})
        }
    )


def create_resource_event(
    resource_type: str,
    action: str,
    value: float,
    threshold: float,
    severity: str = "info",
    job_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> ResilienceEvent:
    """Create a resource monitoring event."""
    return ResilienceEvent(
        event_type="resource_event",
        severity=severity,
        job_id=job_id,
        component=component or "resource_monitor",
        data={
            "resource_type": resource_type,
            "action": action,
            "value": value,
            "threshold": threshold,
            **(context or {})
        }
    )


def create_abort_event(
    reason: str,
    job_id: str,
    policy_id: str,
    severity: str = "critical",
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> ResilienceEvent:
    """Create an abort event."""
    return ResilienceEvent(
        event_type="abort_event",
        severity=severity,
        job_id=job_id,
        component=component or "abort_manager",
        data={
            "reason": reason,
            "policy_id": policy_id,
            **(context or {})
        }
    )


def create_recovery_event(
    recovery_type: str,
    original_error: str,
    action_taken: str,
    severity: str = "info",
    job_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> ResilienceEvent:
    """Create a recovery event."""
    return ResilienceEvent(
        event_type="recovery_event",
        severity=severity,
        job_id=job_id,
        component=component or "failure_handler",
        data={
            "recovery_type": recovery_type,
            "original_error": original_error,
            "action_taken": action_taken,
            **(context or {})
        }
    )


# Event publishing helpers
async def publish_failure_event(
    failure_type: str,
    message: str,
    severity: str = "error",
    job_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Publish a failure event."""
    event = create_failure_event(
        failure_type, message, severity, job_id, context, component
    )
    await _event_bus.publish(event)


async def publish_retry_event(
    operation: str,
    attempt: int,
    max_attempts: int,
    delay: float,
    severity: str = "info",
    job_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Publish a retry event."""
    event = create_retry_event(
        operation, attempt, max_attempts, delay, severity, job_id, context, component
    )
    await _event_bus.publish(event)


async def publish_checkpoint_event(
    action: str,
    checkpoint_id: str,
    job_id: str,
    severity: str = "info",
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Publish a checkpoint event."""
    event = create_checkpoint_event(
        action, checkpoint_id, job_id, severity, context, component
    )
    await _event_bus.publish(event)


async def publish_resource_event(
    resource_type: str,
    action: str,
    value: float,
    threshold: float,
    severity: str = "info",
    job_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Publish a resource monitoring event."""
    event = create_resource_event(
        resource_type, action, value, threshold, severity, job_id, context, component
    )
    await _event_bus.publish(event)


async def publish_abort_event(
    reason: str,
    job_id: str,
    policy_id: str,
    severity: str = "critical",
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Publish an abort event."""
    event = create_abort_event(
        reason, job_id, policy_id, severity, context, component
    )
    await _event_bus.publish(event)


async def publish_recovery_event(
    recovery_type: str,
    original_error: str,
    action_taken: str,
    severity: str = "info",
    job_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Publish a recovery event."""
    event = create_recovery_event(
        recovery_type, original_error, action_taken, severity, job_id, context, component
    )
    await _event_bus.publish(event)
