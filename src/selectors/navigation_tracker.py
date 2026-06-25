"""
Navigation state tracking system for hierarchical selector management.

This module provides comprehensive tracking of navigation states across
multiple levels of the flashscore workflow interface.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field

from src.observability.logger import get_logger
from .context_manager import SelectorContext, NavigationLevel, DOMState


logger = get_logger(__name__)


class NavigationEventType(Enum):
    """Types of navigation events."""
    PAGE_LOAD = "page_load"
    TAB_SWITCH = "tab_switch"
    CONTEXT_CHANGE = "context_change"
    DOM_UPDATE = "dom_update"
    FILTER_CHANGE = "filter_change"
    SEARCH = "search"
    ERROR = "error"


class NavigationState(Enum):
    """States for navigation tracking."""
    IDLE = "idle"
    NAVIGATING = "navigating"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


@dataclass
class NavigationEvent:
    """Represents a navigation event."""
    event_type: NavigationEventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_context: Optional[str] = None
    target_context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class NavigationStateSnapshot:
    """Snapshot of navigation state at a point in time."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    primary_context: Optional[str] = None
    secondary_context: Optional[str] = None
    tertiary_context: Optional[str] = None
    dom_state: Optional[DOMState] = None
    page_url: Optional[str] = None
    active_elements: List[str] = field(default_factory=list)
    visible_tabs: List[str] = field(default_factory=list)
    navigation_state: NavigationState = NavigationState.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)


class NavigationStateTracker:
    """
    Tracks navigation states and events for hierarchical selector management.
    
    This class monitors navigation changes, maintains state history,
    and provides context detection capabilities.
    """
    
    def __init__(self):
        """Initialize navigation state tracker."""
        # Current state
        self.current_state: NavigationState = NavigationState.IDLE
        self.current_snapshot: Optional[NavigationStateSnapshot] = None
        
        # Event history
        self.event_history: List[NavigationEvent] = []
        self.state_history: List[NavigationStateSnapshot] = []
        
        # Context tracking
        self.context_transitions: List[Tuple[str, str, datetime]] = []
        self.active_contexts: Set[str] = set()
        
        # Performance tracking
        self.navigation_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        
        # Configuration
        self.max_history_size = 1000
        self.max_event_history = 500
        
        # Event listeners
        self.event_listeners: List[Callable[[NavigationEvent], None]] = []
        
        # State validation rules
        self.validation_rules: List[Callable[[NavigationStateSnapshot], bool]] = []
        
        logger.info("NavigationStateTracker initialized")
    
    async def start_navigation(
        self,
        source_context: Optional[str] = None,
        target_context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start tracking a navigation operation.
        
        Args:
            source_context: Current context before navigation
            target_context: Expected target context
            metadata: Additional navigation metadata
            
        Returns:
            str: Navigation ID for tracking
        """
        navigation_id = f"nav_{int(datetime.utcnow().timestamp() * 1000)}"
        
        # Update state
        self.current_state = NavigationState.NAVIGATING
        
        # Create navigation event
        event = NavigationEvent(
            event_type=NavigationEventType.PAGE_LOAD,
            source_context=source_context,
            target_context=target_context,
            metadata=metadata or {}
        )
        
        # Record event
        self._record_event(event)
        
        logger.info(
            f"Navigation started: {navigation_id}",
            navigation_id=navigation_id,
            source=source_context,
            target=target_context
        )
        
        return navigation_id
    
    async def complete_navigation(
        self,
        navigation_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        final_context: Optional[str] = None
    ) -> None:
        """
        Complete a navigation operation.
        
        Args:
            navigation_id: ID of the navigation operation
            success: Whether navigation was successful
            error_message: Error message if navigation failed
            final_context: Final context after navigation
        """
        # Find the start event
        start_event = None
        for event in reversed(self.event_history):
            if (event.event_type == NavigationEventType.PAGE_LOAD and 
                event.success and not event.duration_ms):
                start_event = event
                break
        
        if start_event:
            # Calculate duration
            duration = (datetime.utcnow() - start_event.timestamp).total_seconds() * 1000
            start_event.duration_ms = duration
            
            # Update performance tracking
            if start_event.target_context:
                if start_event.target_context not in self.navigation_times:
                    self.navigation_times[start_event.target_context] = []
                self.navigation_times[start_event.target_context].append(duration)
        
        # Update state
        self.current_state = NavigationState.READY if success else NavigationState.ERROR
        
        # Create completion event
        completion_event = NavigationEvent(
            event_type=NavigationEventType.PAGE_LOAD,
            source_context=start_event.source_context if start_event else None,
            target_context=final_context,
            success=success,
            error_message=error_message
        )
        
        self._record_event(completion_event)
        
        # Track context transition
        if (start_event and start_event.target_context and 
            final_context and start_event.target_context != final_context):
            self.context_transitions.append((
                start_event.target_context,
                final_context,
                datetime.utcnow()
            ))
        
        logger.info(
            f"Navigation completed: {navigation_id}",
            navigation_id=navigation_id,
            success=success,
            duration_ms=start_event.duration_ms if start_event else None,
            final_context=final_context
        )
    
    async def record_tab_switch(
        self,
        from_tab: str,
        to_tab: str,
        tab_context: Optional[str] = None
    ) -> None:
        """
        Record a tab switch event.
        
        Args:
            from_tab: ID of tab being switched from
            to_tab: ID of tab being switched to
            tab_context: Context of the new tab
        """
        event = NavigationEvent(
            event_type=NavigationEventType.TAB_SWITCH,
            source_context=from_tab,
            target_context=to_tab,
            metadata={"tab_context": tab_context}
        )
        
        self._record_event(event)
        
        # Update active contexts
        self.active_contexts.discard(from_tab)
        if tab_context:
            self.active_contexts.add(tab_context)
        
        logger.debug(f"Tab switch recorded: {from_tab} -> {to_tab}")
    
    async def record_context_change(
        self,
        old_context: Optional[SelectorContext],
        new_context: SelectorContext,
        change_type: str = "navigation"
    ) -> None:
        """
        Record a context change event.
        
        Args:
            old_context: Previous context
            new_context: New context
            change_type: Type of change (navigation, tab_switch, dom_change)
        """
        event = NavigationEvent(
            event_type=NavigationEventType.CONTEXT_CHANGE,
            source_context=old_context.get_context_path() if old_context else None,
            target_context=new_context.get_context_path(),
            metadata={
                "change_type": change_type,
                "primary": new_context.primary_context,
                "secondary": new_context.secondary_context,
                "tertiary": new_context.tertiary_context,
                "dom_state": new_context.dom_state.value if new_context.dom_state else None
            }
        )
        
        self._record_event(event)
        
        # Update active contexts
        self.active_contexts.add(new_context.get_context_path())
        
        logger.debug(f"Context change recorded: {event.source_context} -> {event.target_context}")
    
    async def record_dom_update(
        self,
        update_type: str,
        affected_elements: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a DOM update event.
        
        Args:
            update_type: Type of DOM update
            affected_elements: List of affected element selectors
            metadata: Additional update metadata
        """
        event = NavigationEvent(
            event_type=NavigationEventType.DOM_UPDATE,
            metadata={
                "update_type": update_type,
                "affected_elements": affected_elements,
                **(metadata or {})
            }
        )
        
        self._record_event(event)
        
        logger.debug(f"DOM update recorded: {update_type} affecting {len(affected_elements)} elements")
    
    async def create_state_snapshot(
        self,
        primary_context: Optional[str] = None,
        secondary_context: Optional[str] = None,
        tertiary_context: Optional[str] = None,
        dom_state: Optional[DOMState] = None,
        page_url: Optional[str] = None,
        active_elements: Optional[List[str]] = None,
        visible_tabs: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> NavigationStateSnapshot:
        """
        Create a snapshot of the current navigation state.
        
        Args:
            primary_context: Primary navigation context
            secondary_context: Secondary navigation context
            tertiary_context: Tertiary navigation context
            dom_state: Current DOM state
            page_url: Current page URL
            active_elements: List of active DOM elements
            visible_tabs: List of visible tabs
            metadata: Additional snapshot metadata
            
        Returns:
            NavigationStateSnapshot: Created snapshot
        """
        snapshot = NavigationStateSnapshot(
            primary_context=primary_context,
            secondary_context=secondary_context,
            tertiary_context=tertiary_context,
            dom_state=dom_state,
            page_url=page_url,
            active_elements=active_elements or [],
            visible_tabs=visible_tabs or [],
            navigation_state=self.current_state,
            metadata=metadata or {}
        )
        
        # Validate snapshot
        is_valid = True
        for rule in self.validation_rules:
            if not rule(snapshot):
                is_valid = False
                break
        
        if is_valid:
            self.current_snapshot = snapshot
            self.state_history.append(snapshot)
            
            # Limit history size
            if len(self.state_history) > self.max_history_size:
                self.state_history = self.state_history[-self.max_history_size:]
            
            logger.debug(f"State snapshot created: {snapshot.primary_context}")
        else:
            logger.warning("State snapshot failed validation")
        
        return snapshot
    
    def get_recent_events(
        self,
        event_type: Optional[NavigationEventType] = None,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[NavigationEvent]:
        """
        Get recent navigation events.
        
        Args:
            event_type: Filter by event type (optional)
            limit: Maximum number of events to return
            since: Only events after this time (optional)
            
        Returns:
            List[NavigationEvent]: Recent events
        """
        events = self.event_history
        
        # Filter by event type
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Filter by time
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        # Limit and sort by timestamp
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    def get_context_transitions(
        self,
        limit: int = 20,
        since: Optional[datetime] = None
    ) -> List[Tuple[str, str, datetime]]:
        """
        Get recent context transitions.
        
        Args:
            limit: Maximum number of transitions to return
            since: Only transitions after this time (optional)
            
        Returns:
            List[Tuple[str, str, datetime]]: Recent transitions
        """
        transitions = self.context_transitions
        
        # Filter by time
        if since:
            transitions = [t for t in transitions if t[2] >= since]
        
        # Sort by timestamp and limit
        transitions = sorted(transitions, key=lambda t: t[2], reverse=True)
        return transitions[:limit]
    
    def get_navigation_performance(
        self,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get navigation performance metrics.
        
        Args:
            context: Specific context to get metrics for (optional)
            
        Returns:
            Dict[str, Any]: Performance metrics
        """
        if context:
            times = self.navigation_times.get(context, [])
            if not times:
                return {"context": context, "sample_count": 0}
            
            return {
                "context": context,
                "sample_count": len(times),
                "average_time_ms": sum(times) / len(times),
                "min_time_ms": min(times),
                "max_time_ms": max(times),
                "median_time_ms": sorted(times)[len(times) // 2]
            }
        else:
            # Return metrics for all contexts
            all_metrics = {}
            for ctx, times in self.navigation_times.items():
                if times:
                    all_metrics[ctx] = {
                        "sample_count": len(times),
                        "average_time_ms": sum(times) / len(times),
                        "min_time_ms": min(times),
                        "max_time_ms": max(times)
                    }
            
            return all_metrics
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of navigation errors.
        
        Returns:
            Dict[str, Any]: Error summary
        """
        error_events = [e for e in self.event_history if not e.success]
        
        # Count errors by type
        error_counts = {}
        for event in error_events:
            error_type = event.event_type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Recent errors
        recent_errors = [
            e for e in error_events 
            if e.timestamp >= datetime.utcnow() - timedelta(hours=1)
        ]
        
        return {
            "total_errors": len(error_events),
            "recent_errors": len(recent_errors),
            "error_by_type": error_counts,
            "error_rate": len(error_events) / max(len(self.event_history), 1)
        }
    
    def add_event_listener(self, listener: Callable[[NavigationEvent], None]) -> None:
        """
        Add an event listener.
        
        Args:
            listener: Function to call on events
        """
        self.event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable[[NavigationEvent], None]) -> bool:
        """
        Remove an event listener.
        
        Args:
            listener: Function to remove
            
        Returns:
            bool: True if listener was removed
        """
        if listener in self.event_listeners:
            self.event_listeners.remove(listener)
            return True
        return False
    
    def add_validation_rule(self, rule: Callable[[NavigationStateSnapshot], bool]) -> None:
        """
        Add a state validation rule.
        
        Args:
            rule: Function that validates a snapshot
        """
        self.validation_rules.append(rule)
    
    def _record_event(self, event: NavigationEvent) -> None:
        """
        Record a navigation event.
        
        Args:
            event: Event to record
        """
        self.event_history.append(event)
        
        # Limit history size
        if len(self.event_history) > self.max_event_history:
            self.event_history = self.event_history[-self.max_event_history:]
        
        # Notify listeners
        for listener in self.event_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
    
    def clear_history(self, older_than: Optional[timedelta] = None) -> None:
        """
        Clear navigation history.
        
        Args:
            older_than: Clear events older than this duration (clears all if None)
        """
        if older_than is None:
            # Clear all history
            self.event_history.clear()
            self.state_history.clear()
            self.context_transitions.clear()
            logger.info("Cleared all navigation history")
        else:
            # Clear old history
            cutoff_time = datetime.utcnow() - older_than
            
            self.event_history = [
                e for e in self.event_history if e.timestamp >= cutoff_time
            ]
            self.state_history = [
                s for s in self.state_history if s.timestamp >= cutoff_time
            ]
            self.context_transitions = [
                t for t in self.context_transitions if t[2] >= cutoff_time
            ]
            
            logger.info(f"Cleared navigation history older than {older_than}")
    
    def export_state(self) -> Dict[str, Any]:
        """
        Export current state for persistence.
        
        Returns:
            Dict[str, Any]: Exportable state
        """
        return {
            "current_state": self.current_state.value,
            "current_snapshot": (
                {
                    "timestamp": self.current_snapshot.timestamp.isoformat(),
                    "primary_context": self.current_snapshot.primary_context,
                    "secondary_context": self.current_snapshot.secondary_context,
                    "tertiary_context": self.current_snapshot.tertiary_context,
                    "dom_state": self.current_snapshot.dom_state.value if self.current_snapshot.dom_state else None,
                    "page_url": self.current_snapshot.page_url,
                    "navigation_state": self.current_snapshot.navigation_state.value
                }
                if self.current_snapshot else None
            ),
            "active_contexts": list(self.active_contexts),
            "event_count": len(self.event_history),
            "snapshot_count": len(self.state_history),
            "transition_count": len(self.context_transitions)
        }


# Global navigation tracker instance
_navigation_tracker: Optional[NavigationStateTracker] = None


def get_navigation_tracker() -> NavigationStateTracker:
    """
    Get the global navigation tracker instance.
    
    Returns:
        NavigationStateTracker: Global tracker instance
    """
    global _navigation_tracker
    
    if _navigation_tracker is None:
        _navigation_tracker = NavigationStateTracker()
    
    return _navigation_tracker
