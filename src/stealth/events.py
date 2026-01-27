"""
Event logging framework for the Stealth & Anti-Detection System.

Manages AntiDetectionEvent creation, publishing, and persistence.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .models import AntiDetectionEvent, EventSeverity, EventType


class EventPublisher:
    """Publishes stealth system events for logging and monitoring."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize event publisher.
        
        Args:
            log_dir: Directory for JSON event logs (default: data/logs/)
        """
        self.log_dir = log_dir or Path("data/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._handlers: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)
        
    def publish(self, event: AntiDetectionEvent) -> None:
        """
        Publish event to all registered handlers.
        
        Args:
            event: AntiDetectionEvent to publish
        """
        # Call registered handlers
        handlers = self._handlers.get(event.event_type.value, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Error in event handler: {e}", exc_info=True)
        
        # Log to JSON
        self._log_to_json(event)
    
    def subscribe(self, event_type: str, handler: Callable[[AntiDetectionEvent], None]) -> None:
        """
        Subscribe to events of specific type.
        
        Args:
            event_type: Event type to subscribe to (e.g., "fingerprint_initialized")
            handler: Callable that receives AntiDetectionEvent
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def _log_to_json(self, event: AntiDetectionEvent) -> None:
        """
        Log event to JSON file.
        
        Args:
            event: AntiDetectionEvent to log
        """
        log_file = self.log_dir / f"stealth-{event.run_id}.json"
        
        try:
            # Read existing events
            if log_file.exists():
                with open(log_file, "r") as f:
                    events = json.load(f)
            else:
                events = []
            
            # Append new event
            events.append(event.to_dict())
            
            # Write back
            with open(log_file, "w") as f:
                json.dump(events, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to log event to {log_file}: {e}", exc_info=True)


class EventBuilder:
    """Builder for constructing AntiDetectionEvent instances."""
    
    def __init__(self, run_id: str):
        """
        Initialize event builder.
        
        Args:
            run_id: Run identifier for all events
        """
        self.run_id = run_id
    
    def create_event(
        self,
        event_type: EventType,
        match_id: str,
        subsystem: str,
        severity: EventSeverity = EventSeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
    ) -> AntiDetectionEvent:
        """
        Create an AntiDetectionEvent.
        
        Args:
            event_type: Type of event
            match_id: Match being scraped
            subsystem: Which subsystem generated event
            severity: Event severity level
            details: Event-specific data
            duration_ms: How long operation took
            success: Whether operation succeeded
            
        Returns:
            Constructed AntiDetectionEvent
        """
        return AntiDetectionEvent(
            timestamp=datetime.utcnow(),
            run_id=self.run_id,
            match_id=match_id,
            event_type=event_type,
            subsystem=subsystem,
            severity=severity,
            details=details or {},
            duration_ms=duration_ms,
            success=success,
        )


# Global event publisher instance
_publisher: Optional[EventPublisher] = None


def get_publisher() -> EventPublisher:
    """Get or create global event publisher."""
    global _publisher
    if _publisher is None:
        _publisher = EventPublisher()
    return _publisher


def set_publisher(publisher: EventPublisher) -> None:
    """Set global event publisher."""
    global _publisher
    _publisher = publisher
