"""
Event bus for component communication in Selector Engine.

Provides publish-subscribe pattern for loose coupling between components
as required by the modular architecture principles.
"""

import asyncio
import weakref
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from uuid import uuid4

from src.observability.logger import get_logger


class EventTypes:
    """Event type constants for the system."""
    
    # Selector Engine Events
    SELECTOR_RESOLVED = "selector.resolved"
    SELECTOR_FAILED = "selector.failed"
    DRIFT_DETECTED = "drift.detected"
    SNAPSHOT_CAPTURED = "snapshot.captured"
    PERFORMANCE_ALERT = "performance.alert"
    
    # Browser lifecycle events
    BROWSER_SESSION_CREATED = "browser.session.created"
    BROWSER_SESSION_INITIALIZED = "browser.session.initialized"
    BROWSER_SESSION_CLOSED = "browser.session.closed"
    BROWSER_SESSION_FAILED = "browser.session.failed"
    BROWSER_CONTEXT_CREATED = "browser.context.created"
    BROWSER_CONTEXT_CLOSED = "browser.context.closed"
    BROWSER_PAGE_CREATED = "browser.page.created"
    BROWSER_PAGE_CLOSED = "browser.page.closed"
    BROWSER_RESOURCE_ALERT = "browser.resource.alert"
    BROWSER_CLEANUP_STARTED = "browser.cleanup.started"
    BROWSER_CLEANUP_COMPLETED = "browser.cleanup.completed"
    BROWSER_STATE_SAVED = "browser.state.saved"
    BROWSER_STATE_RESTORED = "browser.state.restored"
    BROWSER_TAB_SWITCHED = "browser.tab.switched"
    BROWSER_NAVIGATION_STARTED = "browser.navigation.started"
    BROWSER_NAVIGATION_COMPLETED = "browser.navigation.completed"


@dataclass
class Event:
    """Event data structure."""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        """Validate event structure."""
        if not self.event_type.strip():
            raise ValueError("Event type cannot be empty")
        if not isinstance(self.data, dict):
            raise ValueError("Event data must be a dictionary")


@dataclass
class Subscription:
    """Subscription information."""
    id: str
    event_type: str
    handler: Callable
    filter_func: Optional[Callable[[Event], bool]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    active: bool = True


class EventBus:
    """Event bus for publish-subscribe communication."""
    
    def __init__(self):
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._global_subscriptions: List[Subscription] = []
        self._logger = get_logger("event_bus")
        self._event_history: List[Event] = []
        self._max_history_size = 1000
        self._weak_refs: Dict[str, weakref.ref] = {}
    
    async def publish(self, event_type: str, data: Dict[str, Any], 
                     correlation_id: Optional[str] = None,
                     source: Optional[str] = None) -> int:
        """Publish event to subscribers."""
        try:
            # Create event
            event = Event(
                event_type=event_type,
                data=data,
                correlation_id=correlation_id,
                source=source
            )
            
            # Add to history
            self._add_to_history(event)
            
            # Get subscribers
            subscribers = self._get_subscribers_for_event(event_type)
            
            if not subscribers:
                self._logger.debug(
                    "event_published_no_subscribers",
                    event_type=event_type,
                    correlation_id=correlation_id
                )
                return 0
            
            # Publish to all subscribers
            tasks = []
            for subscription in subscribers:
                if subscription.active and self._should_publish(subscription, event):
                    task = asyncio.create_task(
                        self._publish_to_subscriber(subscription, event)
                    )
                    tasks.append(task)
            
            # Wait for all publications
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            self._logger.debug(
                "event_published",
                event_type=event_type,
                subscriber_count=len(tasks),
                correlation_id=correlation_id
            )
            
            return len(tasks)
            
        except Exception as e:
            self._logger.error(
                "event_publish_failed",
                event_type=event_type,
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    def subscribe(self, event_type: str, handler: Callable,
                  filter_func: Optional[Callable[[Event], bool]] = None) -> str:
        """Subscribe to event type, return subscription ID."""
        try:
            subscription_id = str(uuid4())
            
            subscription = Subscription(
                id=subscription_id,
                event_type=event_type,
                handler=handler,
                filter_func=filter_func
            )
            
            # Add to appropriate subscription list
            if event_type == "*":
                self._global_subscriptions.append(subscription)
            else:
                if event_type not in self._subscriptions:
                    self._subscriptions[event_type] = []
                self._subscriptions[event_type].append(subscription)
            
            # Store weak reference for cleanup
            if hasattr(handler, '__self__'):
                self._weak_refs[subscription_id] = weakref.ref(handler.__self__)
            
            self._logger.debug(
                "event_subscribed",
                subscription_id=subscription_id,
                event_type=event_type
            )
            
            return subscription_id
            
        except Exception as e:
            self._logger.error(
                "event_subscribe_failed",
                event_type=event_type,
                error=str(e)
            )
            raise
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        try:
            # Remove from type-specific subscriptions
            removed = False
            for event_type, subscriptions in self._subscriptions.items():
                for i, subscription in enumerate(subscriptions):
                    if subscription.id == subscription_id:
                        subscription.active = False
                        subscriptions.pop(i)
                        removed = True
                        break
                if removed:
                    break
            
            # Remove from global subscriptions
            if not removed:
                for i, subscription in enumerate(self._global_subscriptions):
                    if subscription.id == subscription_id:
                        subscription.active = False
                        self._global_subscriptions.pop(i)
                        removed = True
                        break
            
            # Clean up weak references
            if subscription_id in self._weak_refs:
                del self._weak_refs[subscription_id]
            
            self._logger.debug(
                "event_unsubscribed",
                subscription_id=subscription_id,
                success=removed
            )
            
            return removed
            
        except Exception as e:
            self._logger.error(
                "event_unsubscribe_failed",
                subscription_id=subscription_id,
                error=str(e)
            )
            return False
    
    def _get_subscribers_for_event(self, event_type: str) -> List[Subscription]:
        """Get all subscribers for an event type."""
        subscribers = []
        
        # Add type-specific subscribers
        if event_type in self._subscriptions:
            subscribers.extend(self._subscriptions[event_type])
        
        # Add global subscribers
        subscribers.extend(self._global_subscriptions)
        
        # Clean up dead weak references
        active_subscribers = []
        for subscription in subscribers:
            if subscription.id in self._weak_refs:
                ref = self._weak_refs[subscription.id]
                if ref() is None:
                    # Object was garbage collected, remove subscription
                    self._cleanup_dead_subscription(subscription)
                    continue
            active_subscribers.append(subscription)
        
        return active_subscribers
    
    def _should_publish(self, subscription: Subscription, event: Event) -> bool:
        """Check if event should be published to subscription."""
        if not subscription.active:
            return False
        
        if subscription.filter_func:
            try:
                return subscription.filter_func(event)
            except Exception as e:
                self._logger.warning(
                    "event_filter_error",
                    subscription_id=subscription.id,
                    error=str(e)
                )
                return False
        
        return True
    
    async def _publish_to_subscriber(self, subscription: Subscription, event: Event) -> None:
        """Publish event to a specific subscriber."""
        try:
            # Call handler
            if asyncio.iscoroutinefunction(subscription.handler):
                await subscription.handler(event)
            else:
                subscription.handler(event)
                
        except Exception as e:
            self._logger.error(
                "event_handler_error",
                subscription_id=subscription.id,
                event_type=event.event_type,
                error=str(e),
                correlation_id=event.correlation_id
            )
    
    def _add_to_history(self, event: Event) -> None:
        """Add event to history."""
        self._event_history.append(event)
        
        # Maintain history size
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
    
    def _cleanup_dead_subscription(self, subscription: Subscription) -> None:
        """Clean up subscription with dead weak reference."""
        # Remove from type-specific subscriptions
        if subscription.event_type in self._subscriptions:
            self._subscriptions[subscription.event_type] = [
                s for s in self._subscriptions[subscription.event_type]
                if s.id != subscription.id
            ]
        
        # Remove from global subscriptions
        self._global_subscriptions = [
            s for s in self._global_subscriptions
            if s.id != subscription.id
        ]
        
        # Remove weak reference
        if subscription.id in self._weak_refs:
            del self._weak_refs[subscription.id]
    
    def get_subscription_count(self, event_type: Optional[str] = None) -> int:
        """Get number of subscriptions."""
        if event_type is None:
            total = len(self._global_subscriptions)
            for subscriptions in self._subscriptions.values():
                total += len(subscriptions)
            return total
        else:
            count = len(self._subscriptions.get(event_type, []))
            if event_type == "*":
                count += len(self._global_subscriptions)
            return count
    
    def get_event_history(self, event_type: Optional[str] = None,
                        limit: Optional[int] = None) -> List[Event]:
        """Get event history."""
        history = self._event_history
        
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        
        if limit:
            history = history[-limit:]
        
        return history.copy()
    
    def clear_history(self) -> int:
        """Clear event history."""
        count = len(self._event_history)
        self._event_history.clear()
        return count
    
    def cleanup_dead_subscriptions(self) -> int:
        """Clean up subscriptions with dead weak references."""
        cleaned = 0
        dead_subscription_ids = []
        
        # Find dead subscriptions
        for subscription_id, ref in self._weak_refs.items():
            if ref() is None:
                dead_subscription_ids.append(subscription_id)
        
        # Clean up dead subscriptions
        for subscription_id in dead_subscription_ids:
            if self.unsubscribe(subscription_id):
                cleaned += 1
        
        self._logger.info(
            "dead_subscriptions_cleaned",
            cleaned_count=cleaned
        )
        
        return cleaned


# Event decorators for convenience

def event_handler(event_type: str, filter_func: Optional[Callable[[Event], bool]] = None):
    """Decorator to register event handler."""
    def decorator(handler_func):
        # Get global event bus
        bus = get_event_bus()
        
        # Subscribe the handler
        subscription_id = bus.subscribe(event_type, handler_func, filter_func)
        
        # Store subscription ID on function for potential unsubscription
        handler_func._event_subscription_id = subscription_id
        handler_func._event_bus = bus
        
        return handler_func
    
    return decorator


def unsubscribe_event_handler(handler_func: Callable) -> bool:
    """Unsubscribe event handler that was decorated with @event_handler."""
    if hasattr(handler_func, '_event_subscription_id') and hasattr(handler_func, '_event_bus'):
        return handler_func._event_bus.unsubscribe(handler_func._event_subscription_id)
    return False


# Event filter utilities

def create_correlation_filter(correlation_id: str) -> Callable[[Event], bool]:
    """Create filter for specific correlation ID."""
    def filter_func(event: Event) -> bool:
        return event.correlation_id == correlation_id
    return filter_func


def create_source_filter(source: str) -> Callable[[Event], bool]:
    """Create filter for specific source."""
    def filter_func(event: Event) -> bool:
        return event.source == source
    return filter_func


def create_time_range_filter(start_time: datetime, end_time: datetime) -> Callable[[Event], bool]:
    """Create filter for time range."""
    def filter_func(event: Event) -> bool:
        return start_time <= event.timestamp <= end_time
    return filter_func


def create_data_filter(key: str, value: Any) -> Callable[[Event], bool]:
    """Create filter for specific data key-value pair."""
    def filter_func(event: Event) -> bool:
        return event.data.get(key) == value
    return filter_func


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def set_event_bus(event_bus: EventBus) -> None:
    """Set global event bus instance."""
    global _event_bus
    _event_bus = event_bus


# Utility functions

async def publish_event(event_type: str, data: Dict[str, Any],
                      correlation_id: Optional[str] = None,
                      source: Optional[str] = None) -> int:
    """Publish event using global event bus."""
    bus = get_event_bus()
    return await bus.publish(event_type, data, correlation_id, source)


def subscribe_to_events(event_type: str, handler: Callable,
                        filter_func: Optional[Callable[[Event], bool]] = None) -> str:
    """Subscribe to events using global event bus."""
    bus = get_event_bus()
    return bus.subscribe(event_type, handler, filter_func)


def unsubscribe_from_events(subscription_id: str) -> bool:
    """Unsubscribe from events using global event bus."""
    bus = get_event_bus()
    return bus.unsubscribe(subscription_id)


# Event publishing utilities

async def publish_selector_resolved(selector_name: str, strategy: str, 
                                  confidence: float, resolution_time: float,
                                  correlation_id: Optional[str] = None) -> int:
    """Publish selector resolved event."""
    return await publish_event(
        EventTypes.SELECTOR_RESOLVED,
        {
            "selector_name": selector_name,
            "strategy": strategy,
            "confidence": confidence,
            "resolution_time": resolution_time
        },
        correlation_id,
        "selector_engine"
    )


async def publish_selector_failed(selector_name: str, strategy: str,
                                 failure_reason: str, resolution_time: float,
                                 correlation_id: Optional[str] = None) -> int:
    """Publish selector failed event."""
    return await publish_event(
        EventTypes.SELECTOR_FAILED,
        {
            "selector_name": selector_name,
            "strategy": strategy,
            "failure_reason": failure_reason,
            "resolution_time": resolution_time
        },
        correlation_id,
        "selector_engine"
    )


async def publish_drift_detected(selector_name: str, drift_score: float,
                               trend: str, recommendations: List[str],
                               correlation_id: Optional[str] = None) -> int:
    """Publish drift detected event."""
    return await publish_event(
        EventTypes.DRIFT_DETECTED,
        {
            "selector_name": selector_name,
            "drift_score": drift_score,
            "trend": trend,
            "recommendations": recommendations
        },
        correlation_id,
        "drift_detector"
    )


async def publish_snapshot_captured(selector_name: str, snapshot_id: str,
                                   file_size: int, capture_reason: str,
                                   correlation_id: Optional[str] = None) -> int:
    """Publish snapshot captured event."""
    return await publish_event(
        EventTypes.SNAPSHOT_CAPTURED,
        {
            "selector_name": selector_name,
            "snapshot_id": snapshot_id,
            "file_size": file_size,
            "capture_reason": capture_reason
        },
        correlation_id,
        "snapshot_manager"
    )


async def publish_performance_alert(selector_name: str, metric: str,
                                   value: float, threshold: float,
                                   correlation_id: Optional[str] = None) -> int:
    """Publish performance alert event."""
    return await publish_event(
        EventTypes.PERFORMANCE_ALERT,
        {
            "selector_name": selector_name,
            "metric": metric,
            "value": value,
            "threshold": threshold
        },
        correlation_id,
        "performance_monitor"
    )


# Browser lifecycle event publishing utilities

async def publish_browser_session_created(session_id: str, browser_type: str,
                                        correlation_id: Optional[str] = None) -> int:
    """Publish browser session created event."""
    return await publish_event(
        EventTypes.BROWSER_SESSION_CREATED,
        {
            "session_id": session_id,
            "browser_type": browser_type
        },
        correlation_id,
        "browser_manager"
    )


async def publish_browser_session_initialized(session_id: str, process_id: Optional[int],
                                            correlation_id: Optional[str] = None) -> int:
    """Publish browser session initialized event."""
    return await publish_event(
        EventTypes.BROWSER_SESSION_INITIALIZED,
        {
            "session_id": session_id,
            "process_id": process_id
        },
        correlation_id,
        "browser_session"
    )


async def publish_browser_session_closed(session_id: str,
                                        correlation_id: Optional[str] = None) -> int:
    """Publish browser session closed event."""
    return await publish_event(
        EventTypes.BROWSER_SESSION_CLOSED,
        {
            "session_id": session_id
        },
        correlation_id,
        "browser_session"
    )


async def publish_browser_session_failed(session_id: str, error: str,
                                       correlation_id: Optional[str] = None) -> int:
    """Publish browser session failed event."""
    return await publish_event(
        EventTypes.BROWSER_SESSION_FAILED,
        {
            "session_id": session_id,
            "error": error
        },
        correlation_id,
        "browser_session"
    )


async def publish_browser_context_created(session_id: str, context_id: str,
                                        correlation_id: Optional[str] = None) -> int:
    """Publish browser context created event."""
    return await publish_event(
        EventTypes.BROWSER_CONTEXT_CREATED,
        {
            "session_id": session_id,
            "context_id": context_id
        },
        correlation_id,
        "browser_session"
    )


async def publish_browser_page_created(session_id: str, page_id: str, url: Optional[str],
                                     correlation_id: Optional[str] = None) -> int:
    """Publish browser page created event."""
    return await publish_event(
        EventTypes.BROWSER_PAGE_CREATED,
        {
            "session_id": session_id,
            "page_id": page_id,
            "url": url
        },
        correlation_id,
        "browser_session"
    )


async def publish_browser_resource_alert(session_id: str, resource_type: str, value: float, threshold: float,
                                       correlation_id: Optional[str] = None) -> int:
    """Publish browser resource alert event."""
    return await publish_event(
        EventTypes.BROWSER_RESOURCE_ALERT,
        {
            "session_id": session_id,
            "resource_type": resource_type,
            "value": value,
            "threshold": threshold
        },
        correlation_id,
        "resource_monitor"
    )


async def publish_browser_cleanup_started(session_count: int,
                                         correlation_id: Optional[str] = None) -> int:
    """Publish browser cleanup started event."""
    return await publish_event(
        EventTypes.BROWSER_CLEANUP_STARTED,
        {
            "session_count": session_count
        },
        correlation_id,
        "browser_manager"
    )


async def publish_browser_cleanup_completed(cleaned_count: int,
                                           correlation_id: Optional[str] = None) -> int:
    """Publish browser cleanup completed event."""
    return await publish_event(
        EventTypes.BROWSER_CLEANUP_COMPLETED,
        {
            "cleaned_count": cleaned_count
        },
        correlation_id,
        "browser_manager"
    )


async def publish_browser_tab_switched(session_id: str, context_id: str,
                                       correlation_id: Optional[str] = None) -> int:
    """Publish browser tab switched event."""
    return await publish_event(
        EventTypes.BROWSER_TAB_SWITCHED,
        {
            "session_id": session_id,
            "context_id": context_id
        },
        correlation_id,
        "browser_session"
    )
