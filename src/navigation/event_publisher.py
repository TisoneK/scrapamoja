"""
Navigation event publishing system

Provides event publishing and subscription capabilities for navigation components
with support for multiple channels, filtering, and asynchronous processing.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import weakref
import threading

from .models import NavigationEvent, NavigationOutcome
from .logging_config import get_navigation_logger


class EventType(Enum):
    """Navigation event types"""
    ROUTE_DISCOVERY_STARTED = "route_discovery_started"
    ROUTE_DISCOVERY_COMPLETED = "route_discovery_completed"
    ROUTE_DISCOVERY_FAILED = "route_discovery_failed"
    
    PATH_PLANNING_STARTED = "path_planning_started"
    PATH_PLANNING_COMPLETED = "path_planning_completed"
    PATH_PLANNING_FAILED = "path_planning_failed"
    
    NAVIGATION_STARTED = "navigation_started"
    NAVIGATION_COMPLETED = "navigation_completed"
    NAVIGATION_FAILED = "navigation_failed"
    NAVIGATION_TIMEOUT = "navigation_timeout"
    
    ROUTE_ADAPTATION_STARTED = "route_adaptation_started"
    ROUTE_ADAPTATION_COMPLETED = "route_adaptation_completed"
    ROUTE_ADAPTATION_FAILED = "route_adaptation_failed"
    
    CONTEXT_CREATED = "context_created"
    CONTEXT_UPDATED = "context_updated"
    CONTEXT_DELETED = "context_deleted"
    
    OPTIMIZATION_STARTED = "optimization_started"
    OPTIMIZATION_COMPLETED = "optimization_completed"
    OPTIMIZATION_FAILED = "optimization_failed"
    
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_ALERT = "performance_alert"


@dataclass
class NavigationEventMessage:
    """Navigation event message for publishing"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    source_component: str
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class EventFilter:
    """Event filter for subscription"""
    
    def __init__(
        self,
        event_types: Optional[Set[EventType]] = None,
        source_components: Optional[Set[str]] = None,
        correlation_ids: Optional[Set[str]] = None,
        session_ids: Optional[Set[str]] = None,
        custom_filter: Optional[Callable[[NavigationEventMessage], bool]] = None
    ):
        """Initialize event filter"""
        self.event_types = event_types or set()
        self.source_components = source_components or set()
        self.correlation_ids = correlation_ids or set()
        self.session_ids = session_ids or set()
        self.custom_filter = custom_filter
    
    def matches(self, event: NavigationEventMessage) -> bool:
        """Check if event matches filter"""
        # Check event types
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        # Check source components
        if self.source_components and event.source_component not in self.source_components:
            return False
        
        # Check correlation IDs
        if self.correlation_ids and event.correlation_id not in self.correlation_ids:
            return False
        
        # Check session IDs
        if self.session_ids and event.session_id not in self.session_ids:
            return False
        
        # Check custom filter
        if self.custom_filter and not self.custom_filter(event):
            return False
        
        return True


class EventChannel:
    """Event channel for publishing and subscribing"""
    
    def __init__(self, name: str, max_buffer_size: int = 1000):
        """Initialize event channel"""
        self.name = name
        self.max_buffer_size = max_buffer_size
        self.subscribers: Dict[str, Callable] = {}
        self.event_buffer: List[NavigationEventMessage] = []
        self.logger = get_navigation_logger(f"event_channel_{name}")
        
        self.logger.debug(
            "Event channel initialized",
            channel_name=name,
            max_buffer_size=max_buffer_size
        )
    
    def subscribe(self, subscriber_id: str, callback: Callable[[NavigationEventMessage], None]) -> None:
        """Subscribe to event channel"""
        self.subscribers[subscriber_id] = callback
        self.logger.debug(
            "Subscriber added",
            subscriber_id=subscriber_id,
            total_subscribers=len(self.subscribers)
        )
    
    def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe from event channel"""
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
            self.logger.debug(
                "Subscriber removed",
                subscriber_id=subscriber_id,
                total_subscribers=len(self.subscribers)
            )
    
    async def publish(self, event: NavigationEventMessage) -> None:
        """Publish event to channel"""
        try:
            # Add to buffer
            self.event_buffer.append(event)
            
            # Trim buffer if needed
            if len(self.event_buffer) > self.max_buffer_size:
                self.event_buffer = self.event_buffer[-self.max_buffer_size:]
            
            # Notify subscribers
            for subscriber_id, callback in self.subscribers.items():
                try:
                    # Call callback asynchronously
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    self.logger.error(
                        f"Subscriber callback failed: {str(e)}",
                        subscriber_id=subscriber_id,
                        event_id=event.event_id
                    )
            
            self.logger.debug(
                "Event published",
                event_id=event.event_id,
                event_type=event.event_type.value,
                subscribers_count=len(self.subscribers)
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to publish event: {str(e)}",
                event_id=event.event_id
            )
    
    def get_recent_events(self, limit: int = 100) -> List[NavigationEventMessage]:
        """Get recent events from buffer"""
        return self.event_buffer[-limit:]


class NavigationEventPublisher:
    """Navigation event publishing system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize event publisher"""
        self.logger = get_navigation_logger("navigation_event_publisher")
        self.config = config or {}
        
        # Event channels
        self.channels: Dict[str, EventChannel] = {}
        self.default_channel = "navigation_events"
        
        # Subscription management
        self.subscriptions: Dict[str, Dict[str, EventFilter]] = defaultdict(dict)
        
        # Publishing state
        self._publishing_active = False
        self._publish_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._publisher_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.enable_persistence = self.config.get("enable_persistence", False)
        self.persistence_file = self.config.get("persistence_file", "data/navigation/events.json")
        self.max_queue_size = self.config.get("max_queue_size", 10000)
        
        # Create default channel
        self.create_channel(self.default_channel)
        
        self.logger.info(
            "Navigation event publisher initialized",
            default_channel=self.default_channel,
            enable_persistence=self.enable_persistence
        )
    
    def create_channel(self, channel_name: str, max_buffer_size: int = 1000) -> EventChannel:
        """Create event channel"""
        if channel_name in self.channels:
            return self.channels[channel_name]
        
        channel = EventChannel(channel_name, max_buffer_size)
        self.channels[channel_name] = channel
        
        self.logger.info(
            "Event channel created",
            channel_name=channel_name,
            max_buffer_size=max_buffer_size
        )
        
        return channel
    
    def get_channel(self, channel_name: str) -> Optional[EventChannel]:
        """Get event channel"""
        return self.channels.get(channel_name)
    
    def subscribe(
        self,
        subscriber_id: str,
        callback: Callable[[NavigationEventMessage], None],
        filter: Optional[EventFilter] = None,
        channel_name: Optional[str] = None
    ) -> None:
        """Subscribe to navigation events"""
        channel_name = channel_name or self.default_channel
        channel = self.get_channel(channel_name)
        
        if not channel:
            raise ValueError(f"Channel not found: {channel_name}")
        
        # Create filtered callback
        if filter:
            original_callback = callback
            def filtered_callback(event):
                if filter.matches(event):
                    if asyncio.iscoroutinefunction(original_callback):
                        asyncio.create_task(original_callback(event))
                    else:
                        original_callback(event)
            
            callback = filtered_callback
        
        channel.subscribe(subscriber_id, callback)
        self.subscriptions[channel_name][subscriber_id] = filter
        
        self.logger.info(
            "Event subscription created",
            subscriber_id=subscriber_id,
            channel_name=channel_name,
            has_filter=filter is not None
        )
    
    def unsubscribe(
        self,
        subscriber_id: str,
        channel_name: Optional[str] = None
    ) -> None:
        """Unsubscribe from navigation events"""
        channel_name = channel_name or self.default_channel
        channel = self.get_channel(channel_name)
        
        if channel:
            channel.unsubscribe(subscriber_id)
            self.subscriptions[channel_name].pop(subscriber_id, None)
            
            self.logger.info(
                "Event subscription removed",
                subscriber_id=subscriber_id,
                channel_name=channel_name
            )
    
    async def publish_event(
        self,
        event_type: EventType,
        source_component: str,
        data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        channel_name: Optional[str] = None
    ) -> str:
        """Publish navigation event"""
        try:
            # Generate event ID
            event_id = f"{event_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Create event message
            event = NavigationEventMessage(
                event_id=event_id,
                event_type=event_type,
                timestamp=datetime.utcnow(),
                source_component=source_component,
                correlation_id=correlation_id,
                session_id=session_id,
                data=data,
                metadata=metadata
            )
            
            # Get channel
            channel_name = channel_name or self.default_channel
            channel = self.get_channel(channel_name)
            
            if not channel:
                raise ValueError(f"Channel not found: {channel_name}")
            
            # Publish to channel
            await channel.publish(event)
            
            # Persist if enabled
            if self.enable_persistence:
                await self._persist_event(event)
            
            self.logger.debug(
                "Event published successfully",
                event_id=event_id,
                event_type=event_type.value,
                channel_name=channel_name
            )
            
            return event_id
            
        except Exception as e:
            self.logger.error(
                f"Failed to publish event: {str(e)}",
                event_type=event_type.value,
                source_component=source_component
            )
            raise
    
    async def publish_navigation_event(
        self,
        navigation_event: NavigationEvent,
        source_component: str,
        channel_name: Optional[str] = None
    ) -> str:
        """Publish navigation event from NavigationEvent model"""
        # Determine event type based on outcome
        event_type_mapping = {
            NavigationOutcome.SUCCESS: EventType.NAVIGATION_COMPLETED,
            NavigationOutcome.FAILURE: EventType.NAVIGATION_FAILED,
            NavigationOutcome.TIMEOUT: EventType.NAVIGATION_TIMEOUT,
            NavigationOutcome.DETECTED: EventType.NAVIGATION_FAILED
        }
        
        event_type = event_type_mapping.get(navigation_event.outcome, EventType.NAVIGATION_COMPLETED)
        
        return await self.publish_event(
            event_type=event_type,
            source_component=source_component,
            data={
                "route_id": navigation_event.route_id,
                "context_before": navigation_event.context_before,
                "context_after": navigation_event.context_after,
                "outcome": navigation_event.outcome.value,
                "error_details": navigation_event.error_details,
                "error_code": navigation_event.error_code,
                "page_url_after": navigation_event.page_url_after,
                "performance_metrics": navigation_event.performance_metrics,
                "stealth_score_before": navigation_event.stealth_score_before,
                "stealth_score_after": navigation_event.stealth_score_after,
                "detection_triggers": navigation_event.detection_triggers
            },
            correlation_id=navigation_event.correlation_id,
            channel_name=channel_name
        )
    
    def start_publishing(self) -> None:
        """Start background publishing task"""
        if self._publishing_active:
            return
        
        self._publishing_active = True
        self._publisher_task = asyncio.create_task(self._publishing_loop())
        
        self.logger.info("Event publishing started")
    
    def stop_publishing(self) -> None:
        """Stop background publishing task"""
        if not self._publishing_active:
            return
        
        self._publishing_active = False
        
        if self._publisher_task:
            self._publisher_task.cancel()
        
        self.logger.info("Event publishing stopped")
    
    def get_channel_statistics(self, channel_name: Optional[str] = None) -> Dict[str, Any]:
        """Get channel statistics"""
        if channel_name:
            channel = self.get_channel(channel_name)
            if not channel:
                return {}
            
            return {
                "channel_name": channel.name,
                "subscribers_count": len(channel.subscribers),
                "buffer_size": len(channel.event_buffer),
                "max_buffer_size": channel.max_buffer_size
            }
        
        # Return statistics for all channels
        return {
            channel_name: {
                "subscribers_count": len(channel.subscribers),
                "buffer_size": len(channel.event_buffer),
                "max_buffer_size": channel.max_buffer_size
            }
            for channel_name, channel in self.channels.items()
        }
    
    def get_recent_events(
        self,
        channel_name: Optional[str] = None,
        limit: int = 100
    ) -> List[NavigationEventMessage]:
        """Get recent events"""
        if channel_name:
            channel = self.get_channel(channel_name)
            return channel.get_recent_events(limit) if channel else []
        
        # Get events from all channels
        all_events = []
        for channel in self.channels.values():
            all_events.extend(channel.get_recent_events(limit))
        
        # Sort by timestamp and limit
        all_events.sort(key=lambda e: e.timestamp, reverse=True)
        return all_events[:limit]
    
    async def _publishing_loop(self) -> None:
        """Background publishing loop"""
        self.logger.debug("Publishing loop started")
        
        while self._publishing_active:
            try:
                # Process events from queue
                while not self._publish_queue.empty():
                    event = self._publish_queue.get_nowait()
                    
                    # Publish to appropriate channel
                    channel_name = event.metadata.get("channel_name", self.default_channel)
                    channel = self.get_channel(channel_name)
                    
                    if channel:
                        await channel.publish(event)
                
                # Sleep briefly
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in publishing loop: {str(e)}")
                await asyncio.sleep(1)
        
        self.logger.debug("Publishing loop stopped")
    
    async def _persist_event(self, event: NavigationEventMessage) -> None:
        """Persist event to storage"""
        try:
            # Convert event to dictionary
            event_dict = asdict(event)
            event_dict["timestamp"] = event.timestamp.isoformat()
            event_dict["event_type"] = event.event_type.value
            
            # Load existing events
            events = []
            try:
                with open(self.persistence_file, 'r') as f:
                    events = json.load(f)
            except FileNotFoundError:
                pass
            
            # Add new event
            events.append(event_dict)
            
            # Keep only last 1000 events
            events = events[-1000:]
            
            # Save to file
            with open(self.persistence_file, 'w') as f:
                json.dump(events, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to persist event: {str(e)}")


# Global event publisher instance
_event_publisher: Optional[NavigationEventPublisher] = None


def get_event_publisher(config: Optional[Dict[str, Any]] = None) -> NavigationEventPublisher:
    """Get global event publisher instance"""
    global _event_publisher
    
    if _event_publisher is None:
        _event_publisher = NavigationEventPublisher(config)
    
    return _event_publisher


def start_event_publishing(config: Optional[Dict[str, Any]] = None) -> None:
    """Start global event publishing"""
    publisher = get_event_publisher(config)
    publisher.start_publishing()


def stop_event_publishing() -> None:
    """Stop global event publishing"""
    global _event_publisher
    
    if _event_publisher:
        _event_publisher.stop_publishing()


async def publish_navigation_event(
    event_type: EventType,
    source_component: str,
    data: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    session_id: Optional[str] = None,
    channel_name: Optional[str] = None
) -> str:
    """Publish navigation event using global publisher"""
    publisher = get_event_publisher()
    return await publisher.publish_event(
        event_type=event_type,
        source_component=source_component,
        data=data,
        correlation_id=correlation_id,
        session_id=session_id,
        channel_name=channel_name
    )
