"""
Shutdown state management.

Provides enum for tracking shutdown lifecycle states and
state transition validation.
"""

from enum import Enum


class ShutdownState(Enum):
    """Enum representing the current shutdown state of the application."""
    
    RUNNING = "running"
    SHUTTING_DOWN = "shutting_down"
    COMPLETED = "completed"
    
    def can_transition_to(self, target_state: "ShutdownState") -> bool:
        """Check if transition to target state is valid."""
        valid_transitions = {
            ShutdownState.RUNNING: [ShutdownState.SHUTTING_DOWN],
            ShutdownState.SHUTTING_DOWN: [ShutdownState.COMPLETED],
            ShutdownState.COMPLETED: [],  # Terminal state
        }
        return target_state in valid_transitions.get(self, [])
    
    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self == ShutdownState.COMPLETED
    
    def is_shutdown_in_progress(self) -> bool:
        """Check if shutdown has been initiated."""
        return self in [ShutdownState.SHUTTING_DOWN, ShutdownState.COMPLETED]
