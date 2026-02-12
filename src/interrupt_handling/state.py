"""
Interrupt state management for tracking and coordinating interrupt handling.
"""

import threading
import time
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
from contextlib import contextmanager

from .handler import InterruptContext


class InterruptPhase(Enum):
    """Phases of interrupt handling."""
    NORMAL = "normal"
    SIGNAL_RECEIVED = "signal_received"
    ACKNOWLEDGED = "acknowledged"
    CLEANUP_STARTED = "cleanup_started"
    CLEANUP_IN_PROGRESS = "cleanup_in_progress"
    DATA_PRESERVATION = "data_preservation"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    ERROR = "error"


class InterruptSeverity(Enum):
    """Severity levels for interrupt events."""
    LOW = "low"        # Graceful interrupt, plenty of time
    MEDIUM = "medium"  # Normal interrupt, standard cleanup
    HIGH = "high"      # Urgent interrupt, minimal cleanup
    CRITICAL = "critical"  # Immediate termination required


@dataclass
class InterruptState:
    """Current state of interrupt handling."""
    phase: InterruptPhase = InterruptPhase.NORMAL
    severity: InterruptSeverity = InterruptSeverity.LOW
    context: Optional[InterruptContext] = None
    start_time: float = field(default_factory=time.time)
    phase_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None
    
    def transition_to(self, new_phase: InterruptPhase, metadata: Optional[Dict[str, Any]] = None):
        """Transition to a new phase."""
        old_phase = self.phase
        self.phase = new_phase
        
        # Record transition
        transition_record = {
            'from_phase': old_phase.value,
            'to_phase': new_phase.value,
            'timestamp': time.time(),
            'duration': time.time() - self.start_time,
            'metadata': metadata or {}
        }
        self.phase_history.append(transition_record)
        
        if metadata:
            self.metadata.update(metadata)
    
    def set_error(self, error: Exception):
        """Set error state."""
        self.error = error
        self.transition_to(InterruptPhase.ERROR, {'error_type': type(error).__name__})
    
    def get_duration(self) -> float:
        """Get total duration in current state."""
        return time.time() - self.start_time
    
    def get_phase_duration(self, phase: InterruptPhase) -> Optional[float]:
        """Get duration spent in a specific phase."""
        for record in self.phase_history:
            if record['from_phase'] == phase.value:
                return record['duration']
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            'phase': self.phase.value,
            'severity': self.severity.value,
            'start_time': self.start_time,
            'duration': self.get_duration(),
            'context': {
                'signal_number': self.context.signal_number,
                'signal_name': self.context.signal_name,
                'timestamp': self.context.timestamp
            } if self.context else None,
            'phase_history': self.phase_history,
            'metadata': self.metadata,
            'error': {
                'type': type(self.error).__name__,
                'message': str(self.error)
            } if self.error else None
        }


class InterruptStateManager:
    """Manages interrupt state transitions and coordination."""
    
    def __init__(self):
        self._state = InterruptState()
        self._lock = threading.RLock()
        self._observers: List[Callable[[InterruptState], None]] = []
        self._phase_handlers: Dict[InterruptPhase, List[Callable[[], None]]] = {}
    
    @property
    def current_state(self) -> InterruptState:
        """Get current interrupt state."""
        with self._lock:
            return self._state
    
    @property
    def phase(self) -> InterruptPhase:
        """Get current phase."""
        with self._lock:
            return self._state.phase
    
    @property
    def is_interrupted(self) -> bool:
        """Check if interrupt has been received."""
        with self._lock:
            return self._state.phase != InterruptPhase.NORMAL
    
    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        with self._lock:
            return self._state.phase in [
                InterruptPhase.CLEANUP_STARTED,
                InterruptPhase.CLEANUP_IN_PROGRESS,
                InterruptPhase.DATA_PRESERVATION,
                InterruptPhase.FINALIZING
            ]
    
    @property
    def is_complete(self) -> bool:
        """Check if interrupt handling is complete."""
        with self._lock:
            return self._state.phase in [InterruptPhase.COMPLETE, InterruptPhase.ERROR]
    
    def initialize_interrupt(self, context: InterruptContext, severity: InterruptSeverity = InterruptSeverity.MEDIUM):
        """Initialize interrupt state."""
        with self._lock:
            self._state = InterruptState(
                phase=InterruptPhase.SIGNAL_RECEIVED,
                severity=severity,
                context=context,
                start_time=time.time()
            )
            
            self._notify_observers()
            self._execute_phase_handlers(InterruptPhase.SIGNAL_RECEIVED)
    
    def transition_to(self, new_phase: InterruptPhase, metadata: Optional[Dict[str, Any]] = None):
        """Transition to a new phase."""
        with self._lock:
            if self._state.phase == new_phase:
                return  # Already in this phase
            
            self._state.transition_to(new_phase, metadata)
            self._notify_observers()
            self._execute_phase_handlers(new_phase)
    
    def set_error(self, error: Exception):
        """Set error state."""
        with self._lock:
            self._state.set_error(error)
            self._notify_observers()
            self._execute_phase_handlers(InterruptPhase.ERROR)
    
    def reset(self):
        """Reset to normal state."""
        with self._lock:
            self._state = InterruptState()
            self._notify_observers()
    
    def add_observer(self, observer: Callable[[InterruptState], None]):
        """Add state change observer."""
        with self._lock:
            self._observers.append(observer)
    
    def remove_observer(self, observer: Callable[[InterruptState], None]):
        """Remove state change observer."""
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)
    
    def add_phase_handler(self, phase: InterruptPhase, handler: Callable[[], None]):
        """Add handler for specific phase."""
        with self._lock:
            if phase not in self._phase_handlers:
                self._phase_handlers[phase] = []
            self._phase_handlers[phase].append(handler)
    
    def remove_phase_handler(self, phase: InterruptPhase, handler: Callable[[], None]):
        """Remove phase handler."""
        with self._lock:
            if phase in self._phase_handlers and handler in self._phase_handlers[phase]:
                self._phase_handlers[phase].remove(handler)
    
    def _notify_observers(self):
        """Notify all observers of state change."""
        for observer in self._observers:
            try:
                observer(self._state)
            except Exception as e:
                # Log error but don't let it break state management
                import logging
                logging.getLogger(__name__).error(f"Error in state observer: {e}")
    
    def _execute_phase_handlers(self, phase: InterruptPhase):
        """Execute handlers for specific phase."""
        if phase in self._phase_handlers:
            for handler in self._phase_handlers[phase]:
                try:
                    handler()
                except Exception as e:
                    # Log error but don't let it break state management
                    import logging
                    logging.getLogger(__name__).error(f"Error in phase handler for {phase}: {e}")
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state."""
        with self._lock:
            return {
                'phase': self._state.phase.value,
                'severity': self._state.severity.value,
                'duration': self._state.get_duration(),
                'is_interrupted': self.is_interrupted,
                'is_shutting_down': self.is_shutting_down,
                'is_complete': self.is_complete,
                'has_error': self._state.error is not None,
                'phase_count': len(self._state.phase_history)
            }
    
    @contextmanager
    def phase_context(self, target_phase: InterruptPhase, metadata: Optional[Dict[str, Any]] = None):
        """Context manager for phase transitions."""
        original_phase = self.phase
        try:
            self.transition_to(target_phase, metadata)
            yield
        finally:
            if self.phase == target_phase:  # Only revert if not changed by other logic
                self.transition_to(original_phase, {'reverted': True})


# Global state manager instance
_state_manager = InterruptStateManager()


def get_state_manager() -> InterruptStateManager:
    """Get the global state manager instance."""
    return _state_manager


@contextmanager
def interrupt_state_context(severity: InterruptSeverity = InterruptSeverity.MEDIUM):
    """Context manager for interrupt handling operations."""
    state_manager = get_state_manager()
    original_state = state_manager.current_state
    
    try:
        yield state_manager
    finally:
        # Reset if we're still in an interrupt state and this was the initiator
        if state_manager.is_interrupted and original_state.phase == InterruptPhase.NORMAL:
            state_manager.reset()
