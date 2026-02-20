"""
Snapshot Circuit Breaker

Prevents snapshot system from overwhelming the application
when too many failures occur in a short time period.
"""

import time
from typing import Optional, List
from dataclasses import dataclass, field

from src.observability.logger import get_logger

from .exceptions import SnapshotCircuitOpen

logger = get_logger(__name__)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # Number of failures before opening
    time_window: int = 60  # Time window in seconds
    cooldown_period: int = 300  # Cooldown period in seconds (5 minutes)
    half_open_attempts: int = 3  # Number of attempts in half-open state


@dataclass
class FailureRecord:
    """Record of a failure event."""
    timestamp: float
    error_type: str
    error_message: str


class SnapshotCircuitBreaker:
    """Circuit breaker for snapshot system to prevent cascading failures."""
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker with configuration."""
        self.config = config or CircuitBreakerConfig()
        self.failures: List[FailureRecord] = []
        self.state = "closed"  # closed, open, half_open
        self.last_state_change = time.time()
        self.half_open_attempts = 0
        
        # Statistics
        self.total_trips = 0
        self.total_failures = 0
        self.total_successes = 0
    
    def should_allow_snapshot(self) -> bool:
        """Check if snapshot should be allowed based on circuit state."""
        current_time = time.time()
        
        # Clean up old failures outside time window
        self._cleanup_old_failures(current_time)
        
        if self.state == "closed":
            # Normal operation - check if we should open
            if len(self.failures) >= self.config.failure_threshold:
                self._open_circuit(current_time)
                return False
            return True
        
        elif self.state == "open":
            # Circuit is open - check if cooldown period has passed
            if current_time - self.last_state_change >= self.config.cooldown_period:
                self._half_open_circuit(current_time)
                return True
            return False
        
        elif self.state == "half_open":
            # Half-open - allow limited attempts
            if self.half_open_attempts >= self.config.half_open_attempts:
                self._open_circuit(current_time)
                return False
            return True
        
        return False
    
    def record_success(self):
        """Record a successful snapshot."""
        current_time = time.time()
        self.total_successes += 1
        
        if self.state == "half_open":
            # Success in half-open state - close the circuit
            self._close_circuit(current_time)
        
        # Reset half-open attempts on success
        self.half_open_attempts = 0
    
    def record_failure(self, error_type: str, error_message: str):
        """Record a failed snapshot."""
        current_time = time.time()
        self.total_failures += 1
        
        # Record failure
        failure = FailureRecord(
            timestamp=current_time,
            error_type=error_type,
            error_message=error_message
        )
        self.failures.append(failure)
        
        # Handle failure based on current state
        if self.state == "closed":
            # Check if we should open circuit
            if len(self.failures) >= self.config.failure_threshold:
                self._open_circuit(current_time)
        
        elif self.state == "half_open":
            # Failure in half-open state - open circuit immediately
            self.half_open_attempts += 1
            if self.half_open_attempts >= self.config.half_open_attempts:
                self._open_circuit(current_time)
    
    def _cleanup_old_failures(self, current_time: float):
        """Remove failures outside the time window."""
        cutoff_time = current_time - self.config.time_window
        self.failures = [
            f for f in self.failures 
            if f.timestamp >= cutoff_time
        ]
    
    def _open_circuit(self, current_time: float):
        """Open the circuit to prevent further snapshots."""
        if self.state != "open":
            self.state = "open"
            self.last_state_change = current_time
            self.total_trips += 1
            self.half_open_attempts = 0
            
            logger.warning("Snapshot circuit breaker OPEN",
                          failure_count=len(self.failures),
                          time_window=self.config.time_window,
                          cooldown_period=self.config.cooldown_period)
    
    def _close_circuit(self, current_time: float):
        """Close the circuit to allow normal operation."""
        if self.state != "closed":
            self.state = "closed"
            self.last_state_change = current_time
            self.failures = []  # Clear failure history
            self.half_open_attempts = 0
            
            logger.info("Snapshot circuit breaker CLOSED - resuming normal operation")
    
    def _half_open_circuit(self, current_time: float):
        """Move to half-open state to test recovery."""
        if self.state != "half_open":
            self.state = "half_open"
            self.last_state_change = current_time
            self.half_open_attempts = 0
            
            logger.info("Snapshot circuit breaker HALF-OPEN - testing recovery")
    
    def get_state_info(self) -> dict:
        """Get current circuit breaker state and statistics."""
        current_time = time.time()
        self._cleanup_old_failures(current_time)
        
        return {
            "state": self.state,
            "last_state_change": self.last_state_change,
            "time_in_state": current_time - self.last_state_change,
            "recent_failures": len(self.failures),
            "failure_threshold": self.config.failure_threshold,
            "half_open_attempts": self.half_open_attempts,
            "statistics": {
                "total_trips": self.total_trips,
                "total_failures": self.total_failures,
                "total_successes": self.total_successes,
                "success_rate": (
                    self.total_successes / (self.total_successes + self.total_failures) * 100
                    if (self.total_successes + self.total_failures) > 0 else 0
                )
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "time_window": self.config.time_window,
                "cooldown_period": self.config.cooldown_period,
                "half_open_attempts": self.config.half_open_attempts
            }
        }
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        self.state = "closed"
        self.last_state_change = time.time()
        self.failures = []
        self.half_open_attempts = 0
        logger.info("Snapshot circuit breaker RESET to closed state")
    
    def force_open(self, reason: str):
        """Force the circuit open (for manual intervention)."""
        current_time = time.time()
        self._open_circuit(current_time)
        logger.warning("Snapshot circuit breaker FORCED OPEN", reason=reason)
    
    def force_close(self, reason: str):
        """Force the circuit closed (for manual intervention)."""
        current_time = time.time()
        self._close_circuit(current_time)
        logger.info("Snapshot circuit breaker FORCED CLOSED", reason=reason)


# Global circuit breaker instance
_circuit_breaker: Optional[SnapshotCircuitBreaker] = None


def get_circuit_breaker() -> SnapshotCircuitBreaker:
    """Get the global circuit breaker instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = SnapshotCircuitBreaker()
    return _circuit_breaker


def check_circuit_breaker() -> None:
    """Check if snapshot is allowed, raise exception if not."""
    circuit_breaker = get_circuit_breaker()
    if not circuit_breaker.should_allow_snapshot():
        state_info = circuit_breaker.get_state_info()
        raise SnapshotCircuitOpen(
            f"Snapshot circuit breaker is {state_info['state']}. "
            f"Recent failures: {state_info['recent_failures']}, "
            f"Threshold: {state_info['failure_threshold']}"
        )
