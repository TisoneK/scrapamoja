"""
Time-based Utilities for Resilience Operations

Provides time calculation utilities for backoff strategies, delay calculations,
and timing-related operations for resilience components.
"""

import time
import random
import math
from typing import Optional, Tuple
from datetime import datetime, timedelta


class BackoffCalculator:
    """Calculates backoff delays for retry operations."""
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1
    ):
        """
        Initialize backoff calculator.
        
        Args:
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Backoff multiplier
            jitter_factor: Jitter factor (0.0-1.0)
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter_factor = max(0.0, min(1.0, jitter_factor))
    
    def calculate_exponential_backoff(
        self,
        attempt: int,
        add_jitter: bool = True
    ) -> float:
        """
        Calculate exponential backoff delay.
        
        Args:
            attempt: Current attempt number (1-based)
            add_jitter: Whether to add jitter to delay
            
        Returns:
            Delay in seconds
        """
        # Calculate exponential backoff
        delay = self.base_delay * (self.multiplier ** (attempt - 1))
        
        # Apply maximum limit
        delay = min(delay, self.max_delay)
        
        # Add jitter if requested
        if add_jitter and self.jitter_factor > 0:
            jitter = delay * self.jitter_factor * (random.random() * 2 - 1)
            delay = max(0, delay + jitter)
        
        return delay
    
    def calculate_linear_backoff(
        self,
        attempt: int,
        add_jitter: bool = True
    ) -> float:
        """
        Calculate linear backoff delay.
        
        Args:
            attempt: Current attempt number (1-based)
            add_jitter: Whether to add jitter to delay
            
        Returns:
            Delay in seconds
        """
        # Calculate linear backoff
        delay = self.base_delay * attempt
        
        # Apply maximum limit
        delay = min(delay, self.max_delay)
        
        # Add jitter if requested
        if add_jitter and self.jitter_factor > 0:
            jitter = delay * self.jitter_factor * (random.random() * 2 - 1)
            delay = max(0, delay + jitter)
        
        return delay
    
    def calculate_fixed_backoff(
        self,
        add_jitter: bool = True
    ) -> float:
        """
        Calculate fixed backoff delay.
        
        Args:
            add_jitter: Whether to add jitter to delay
            
        Returns:
            Delay in seconds
        """
        delay = self.base_delay
        
        # Add jitter if requested
        if add_jitter and self.jitter_factor > 0:
            jitter = delay * self.jitter_factor * (random.random() * 2 - 1)
            delay = max(0, delay + jitter)
        
        return delay


class TimeWindow:
    """Manages time windows for sliding window analysis."""
    
    def __init__(self, window_size_seconds: int):
        """
        Initialize time window.
        
        Args:
            window_size_seconds: Size of time window in seconds
        """
        self.window_size = timedelta(seconds=window_size_seconds)
    
    def is_in_window(
        self,
        timestamp: datetime,
        current_time: Optional[datetime] = None
    ) -> bool:
        """
        Check if timestamp is within the time window.
        
        Args:
            timestamp: Timestamp to check
            current_time: Current time (uses now if not provided)
            
        Returns:
            True if timestamp is within window, False otherwise
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        window_start = current_time - self.window_size
        return window_start <= timestamp <= current_time
    
    def get_window_start(
        self,
        current_time: Optional[datetime] = None
    ) -> datetime:
        """
        Get the start time of the current window.
        
        Args:
            current_time: Current time (uses now if not provided)
            
        Returns:
            Window start time
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        return current_time - self.window_size


class RateLimiter:
    """Rate limiter for controlling operation frequency."""
    
    def __init__(self, max_operations: int, time_window_seconds: int):
        """
        Initialize rate limiter.
        
        Args:
            max_operations: Maximum operations allowed in time window
            time_window_seconds: Time window size in seconds
        """
        self.max_operations = max_operations
        self.time_window = TimeWindow(time_window_seconds)
        self.operations = []
    
    def can_proceed(self, current_time: Optional[datetime] = None) -> bool:
        """
        Check if operation can proceed based on rate limit.
        
        Args:
            current_time: Current time (uses now if not provided)
            
        Returns:
            True if operation can proceed, False otherwise
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        # Remove old operations outside window
        self.operations = [
            op_time for op_time in self.operations
            if self.time_window.is_in_window(op_time, current_time)
        ]
        
        # Check if under limit
        return len(self.operations) < self.max_operations
    
    def record_operation(self, current_time: Optional[datetime] = None) -> None:
        """
        Record an operation occurrence.
        
        Args:
            current_time: Current time (uses now if not provided)
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        self.operations.append(current_time)
    
    def get_wait_time(
        self,
        current_time: Optional[datetime] = None
    ) -> Optional[float]:
        """
        Get time to wait before next operation can proceed.
        
        Args:
            current_time: Current time (uses now if not provided)
            
        Returns:
            Seconds to wait, or None if can proceed immediately
        """
        if self.can_proceed(current_time):
            return None
        
        if current_time is None:
            current_time = datetime.utcnow()
        
        # Calculate time until oldest operation falls outside window
        if self.operations:
            oldest_operation = min(self.operations)
            window_start = self.time_window.get_window_start(current_time)
            wait_time = (oldest_operation - window_start).total_seconds()
            return max(0, wait_time)
        
        return 0.0


class TimeoutManager:
    """Manages timeout operations with graceful handling."""
    
    def __init__(self, default_timeout: float = 30.0):
        """
        Initialize timeout manager.
        
        Args:
            default_timeout: Default timeout in seconds
        """
        self.default_timeout = default_timeout
    
    def calculate_timeout(
        self,
        base_timeout: Optional[float] = None,
        multiplier: float = 1.0,
        max_timeout: float = 300.0
    ) -> float:
        """
        Calculate timeout with multiplier and maximum limit.
        
        Args:
            base_timeout: Base timeout (uses default if not provided)
            multiplier: Timeout multiplier
            max_timeout: Maximum allowed timeout
            
        Returns:
            Calculated timeout in seconds
        """
        timeout = (base_timeout or self.default_timeout) * multiplier
        return min(timeout, max_timeout)
    
    def should_timeout(
        self,
        start_time: datetime,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Check if operation should timeout.
        
        Args:
            start_time: Operation start time
            timeout: Timeout duration (uses default if not provided)
            
        Returns:
            True if should timeout, False otherwise
        """
        if timeout is None:
            timeout = self.default_timeout
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        return elapsed >= timeout
    
    def get_remaining_time(
        self,
        start_time: datetime,
        timeout: Optional[float] = None
    ) -> float:
        """
        Get remaining time before timeout.
        
        Args:
            start_time: Operation start time
            timeout: Timeout duration (uses default if not provided)
            
        Returns:
            Remaining time in seconds (0 if already timed out)
        """
        if timeout is None:
            timeout = self.default_timeout
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        remaining = timeout - elapsed
        return max(0, remaining)


class CircuitBreakerTimer:
    """Timer for circuit breaker state management."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_recovery_time: float = 30.0
    ):
        """
        Initialize circuit breaker timer.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_recovery_time: Expected time for recovery to complete
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_recovery_time = expected_recovery_time
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.circuit_open = False
    
    def record_failure(self) -> None:
        """Record a failure and potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True
    
    def record_success(self) -> None:
        """Record a success and reset circuit state."""
        self.failure_count = 0
        self.circuit_open = False
        self.last_failure_time = None
    
    def can_proceed(self) -> bool:
        """Check if operation can proceed."""
        if not self.circuit_open:
            return True
        
        if self.last_failure_time is None:
            return True
        
        # Check if recovery timeout has passed
        time_since_failure = (
            datetime.utcnow() - self.last_failure_time
        ).total_seconds()
        
        return time_since_failure >= self.recovery_timeout
    
    def get_recovery_progress(self) -> Tuple[float, bool]:
        """
        Get recovery progress.
        
        Returns:
            Tuple of (progress_percentage, is_recovered)
        """
        if not self.circuit_open:
            return 1.0, True
        
        if self.last_failure_time is None:
            return 1.0, True
        
        time_since_failure = (
            datetime.utcnow() - self.last_failure_time
        ).total_seconds()
        
        progress = min(1.0, time_since_failure / self.recovery_timeout)
        is_recovered = progress >= 1.0
        
        return progress, is_recovered


# Global instances and utility functions
_default_backoff = BackoffCalculator()


def calculate_exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 300.0,
    multiplier: float = 2.0,
    jitter_factor: float = 0.1
) -> float:
    """Calculate exponential backoff delay."""
    calculator = BackoffCalculator(base_delay, max_delay, multiplier, jitter_factor)
    return calculator.calculate_exponential_backoff(attempt)


def calculate_linear_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 300.0,
    jitter_factor: float = 0.1
) -> float:
    """Calculate linear backoff delay."""
    calculator = BackoffCalculator(base_delay, max_delay, 1.0, jitter_factor)
    return calculator.calculate_linear_backoff(attempt)


def add_jitter(delay: float, jitter_factor: float = 0.1) -> float:
    """Add jitter to delay value."""
    jitter = delay * jitter_factor * (random.random() * 2 - 1)
    return max(0, delay + jitter)


def sleep_with_jitter(delay: float, jitter_factor: float = 0.1) -> None:
    """Sleep for specified duration with jitter."""
    actual_delay = add_jitter(delay, jitter_factor)
    time.sleep(actual_delay)
