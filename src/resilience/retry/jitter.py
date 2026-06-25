"""
Jitter Calculation Utilities

Provides various jitter calculation strategies to prevent thundering herd
problems and distribute retry attempts over time.
"""

import random
import math
from typing import Dict, Any, Optional, Callable
from enum import Enum
from abc import ABC, abstractmethod

from ..models.retry_policy import JitterType


class JitterStrategy(ABC):
    """Abstract base class for jitter strategies."""
    
    @abstractmethod
    def calculate_jitter(
        self,
        base_delay: float,
        attempt: int,
        jitter_factor: float = 0.1,
        **kwargs
    ) -> float:
        """
        Calculate jitter value.
        
        Args:
            base_delay: Base delay value
            attempt: Current attempt number (1-based)
            jitter_factor: Jitter factor (0.0-1.0)
            **kwargs: Additional parameters
            
        Returns:
            Jitter value to add to base delay
        """
        pass


class FullJitterStrategy(JitterStrategy):
    """Full jitter strategy: random between 0 and base_delay."""
    
    def calculate_jitter(
        self,
        base_delay: float,
        attempt: int,
        jitter_factor: float = 0.1,
        **kwargs
    ) -> float:
        """Calculate full jitter."""
        return base_delay * jitter_factor * random.random()


class EqualJitterStrategy(JitterStrategy):
    """Equal jitter strategy: base_delay/2 ± base_delay/2 * jitter_factor."""
    
    def calculate_jitter(
        self,
        base_delay: float,
        attempt: int,
        jitter_factor: float = 0.1,
        **kwargs
    ) -> float:
        """Calculate equal jitter."""
        half_delay = base_delay / 2
        jitter = half_delay * jitter_factor * (random.random() * 2 - 1)
        return jitter


class DecorrelatedJitterStrategy(JitterStrategy):
    """Decorrelated jitter strategy: random between base_delay and delay * 3."""
    
    def calculate_jitter(
        self,
        base_delay: float,
        attempt: int,
        jitter_factor: float = 0.1,
        **kwargs
    ) -> float:
        """Calculate decorrelated jitter."""
        # Random between base_delay and base_delay * 3
        return random.uniform(base_delay, base_delay * 3) - base_delay


class ExponentialJitterStrategy(JitterStrategy):
    """Exponential jitter strategy with exponential distribution."""
    
    def calculate_jitter(
        self,
        base_delay: float,
        attempt: int,
        jitter_factor: float = 0.1,
        **kwargs
    ) -> float:
        """Calculate exponential jitter."""
        # Use exponential distribution for more natural spread
        return base_delay * jitter_factor * random.expovariate(1.0)


class GaussianJitterStrategy(JitterStrategy):
    """Gaussian jitter strategy using normal distribution."""
    
    def calculate_jitter(
        self,
        base_delay: float,
        attempt: int,
        jitter_factor: float = 0.1,
        **kwargs
    ) -> float:
        """Calculate Gaussian jitter."""
        # Use normal distribution centered at 0
        return base_delay * jitter_factor * random.gauss(0, 1)


class BoundedJitterStrategy(JitterStrategy):
    """Bounded jitter strategy with configurable bounds."""
    
    def __init__(self, min_jitter: float = 0.0, max_jitter: float = None):
        """
        Initialize bounded jitter strategy.
        
        Args:
            min_jitter: Minimum jitter value
            max_jitter: Maximum jitter value (None for no limit)
        """
        self.min_jitter = min_jitter
        self.max_jitter = max_jitter
    
    def calculate_jitter(
        self,
        base_delay: float,
        attempt: int,
        jitter_factor: float = 0.1,
        **kwargs
    ) -> float:
        """Calculate bounded jitter."""
        jitter = base_delay * jitter_factor * (random.random() * 2 - 1)
        
        # Apply bounds
        jitter = max(self.min_jitter, jitter)
        if self.max_jitter is not None:
            jitter = min(self.max_jitter, jitter)
        
        return jitter


class AdaptiveJitterStrategy(JitterStrategy):
    """Adaptive jitter strategy that adjusts based on attempt number."""
    
    def calculate_jitter(
        self,
        base_delay: float,
        attempt: int,
        jitter_factor: float = 0.1,
        **kwargs
    ) -> float:
        """Calculate adaptive jitter."""
        # Increase jitter factor for later attempts
        adaptive_factor = min(1.0, jitter_factor * (1.0 + (attempt - 1) * 0.1))
        return base_delay * adaptive_factor * random.random()


class JitterCalculator:
    """Main jitter calculator with multiple strategies."""
    
    def __init__(self):
        """Initialize jitter calculator."""
        self.strategies = {
            JitterType.NONE: NoneJitterStrategy(),
            JitterType.FULL: FullJitterStrategy(),
            JitterType.EQUAL: EqualJitterStrategy(),
            JitterType.DECORRELATED: DecorrelatedJitterStrategy()
        }
        
        # Additional strategies
        self.exponential_jitter = ExponentialJitterStrategy()
        self.gaussian_jitter = GaussianJitterStrategy()
        self.bounded_jitter = BoundedJitterStrategy()
        self.adaptive_jitter = AdaptiveJitterStrategy()
    
    def calculate_jitter(
        self,
        base_delay: float,
        jitter_type: JitterType,
        attempt: int = 1,
        jitter_factor: float = 0.1,
        **kwargs
    ) -> float:
        """
        Calculate jitter using specified strategy.
        
        Args:
            base_delay: Base delay value
            jitter_type: Type of jitter to apply
            attempt: Current attempt number (1-based)
            jitter_factor: Jitter factor (0.0-1.0)
            **kwargs: Additional parameters for jitter calculation
            
        Returns:
            Jitter value to add to base delay
        """
        strategy = self.strategies.get(jitter_type)
        if strategy is None:
            return 0.0
        
        return strategy.calculate_jitter(base_delay, attempt, jitter_factor, **kwargs)
    
    def apply_jitter(
        self,
        delay: float,
        jitter_type: JitterType,
        attempt: int = 1,
        jitter_factor: float = 0.1,
        **kwargs
    ) -> float:
        """
        Apply jitter to a delay value.
        
        Args:
            delay: Original delay value
            jitter_type: Type of jitter to apply
            attempt: Current attempt number (1-based)
            jitter_factor: Jitter factor (0.0-1.0)
            **kwargs: Additional parameters for jitter calculation
            
        Returns:
            Delay with jitter applied
        """
        jitter = self.calculate_jitter(delay, jitter_type, attempt, jitter_factor, **kwargs)
        return max(0, delay + jitter)
    
    def register_strategy(
        self,
        jitter_type: JitterType,
        strategy: JitterStrategy
    ) -> None:
        """
        Register a custom jitter strategy.
        
        Args:
            jitter_type: Jitter type to register
            strategy: Strategy instance
        """
        self.strategies[jitter_type] = strategy


class NoneJitterStrategy(JitterStrategy):
    """No jitter strategy."""
    
    def calculate_jitter(
        self,
        base_delay: float,
        attempt: int,
        jitter_factor: float = 0.1,
        **kwargs
    ) -> float:
        """Calculate no jitter."""
        return 0.0


# Advanced jitter functions
def calculate_full_jitter(
    base_delay: float,
    jitter_factor: float = 0.1
) -> float:
    """Calculate full jitter."""
    return base_delay * jitter_factor * random.random()


def calculate_equal_jitter(
    base_delay: float,
    jitter_factor: float = 0.1
) -> float:
    """Calculate equal jitter."""
    half_delay = base_delay / 2
    jitter = half_delay * jitter_factor * (random.random() * 2 - 1)
    return jitter


def calculate_decorrelated_jitter(
    base_delay: float,
    jitter_factor: float = 0.1
) -> float:
    """Calculate decorrelated jitter."""
    return random.uniform(base_delay, base_delay * 3) - base_delay


def calculate_exponential_jitter(
    base_delay: float,
    jitter_factor: float = 0.1
) -> float:
    """Calculate exponential jitter."""
    return base_delay * jitter_factor * random.expovariate(1.0)


def calculate_gaussian_jitter(
    base_delay: float,
    jitter_factor: float = 0.1
) -> float:
    """Calculate Gaussian jitter."""
    return base_delay * jitter_factor * random.gauss(0, 1)


def calculate_adaptive_jitter(
    base_delay: float,
    attempt: int,
    jitter_factor: float = 0.1
) -> float:
    """Calculate adaptive jitter."""
    adaptive_factor = min(1.0, jitter_factor * (1.0 + (attempt - 1) * 0.1))
    return base_delay * adaptive_factor * random.random()


def calculate_bounded_jitter(
    base_delay: float,
    jitter_factor: float = 0.1,
    min_jitter: float = 0.0,
    max_jitter: Optional[float] = None
) -> float:
    """Calculate bounded jitter."""
    jitter = base_delay * jitter_factor * (random.random() * 2 - 1)
    jitter = max(min_jitter, jitter)
    if max_jitter is not None:
        jitter = min(max_jitter, jitter)
    return jitter


# Utility functions for common jitter patterns
def thundering_herd_protection(
    base_delay: float,
    num_clients: int,
    client_id: int
) -> float:
    """
    Calculate delay to prevent thundering herd problems.
    
    Args:
        base_delay: Base delay value
        num_clients: Number of clients that might retry simultaneously
        client_id: This client's ID (0 to num_clients-1)
        
    Returns:
        Delay with client-specific offset
    """
    # Distribute clients evenly across the time window
    client_offset = (client_id / num_clients) * base_delay
    return base_delay + client_offset


def distributed_jitter(
    base_delay: float,
    attempt: int,
    max_attempts: int,
    jitter_factor: float = 0.1
) -> float:
    """
    Calculate jitter that distributes retries across time.
    
    Args:
        base_delay: Base delay value
        attempt: Current attempt number
        max_attempts: Maximum number of attempts
        jitter_factor: Jitter factor
        
    Returns:
        Distributed jitter value
    """
    # Use attempt number to create distribution
    attempt_factor = attempt / max_attempts
    time_window = base_delay * max_attempts
        
    # Random position within the time window for this attempt
    position = random.uniform(attempt_factor * time_window, (attempt_factor + 1) * time_window)
    return position - (attempt * base_delay)


def backoff_with_jitter(
    attempt: int,
    base_delay: float,
    max_delay: float,
    multiplier: float = 2.0,
    jitter_type: JitterType = JitterType.FULL,
    jitter_factor: float = 0.1
) -> float:
    """
    Calculate backoff delay with jitter.
    
    Args:
        attempt: Current attempt number (1-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        multiplier: Backoff multiplier
        jitter_type: Type of jitter to apply
        jitter_factor: Jitter factor (0.0-1.0)
        
    Returns:
        Delay with backoff and jitter applied
    """
    # Calculate exponential backoff
    delay = base_delay * (multiplier ** (attempt - 1))
    delay = min(delay, max_delay)
    
    # Apply jitter
    calculator = JitterCalculator()
    return calculator.apply_jitter(delay, jitter_type, attempt, jitter_factor)


# Global jitter calculator instance
_jitter_calculator = JitterCalculator()


def get_jitter_calculator() -> JitterCalculator:
    """Get the global jitter calculator instance."""
    return _jitter_calculator


def calculate_jitter(
    base_delay: float,
    jitter_type: JitterType,
    attempt: int = 1,
    jitter_factor: float = 0.1,
    **kwargs
) -> float:
    """Calculate jitter using the global calculator."""
    return _jitter_calculator.calculate_jitter(
        base_delay, jitter_type, attempt, jitter_factor, **kwargs
    )


def apply_jitter(
    delay: float,
    jitter_type: JitterType,
    attempt: int = 1,
    jitter_factor: float = 0.1,
    **kwargs
) -> float:
    """Apply jitter using the global calculator."""
    return _jitter_calculator.apply_jitter(
        delay, jitter_type, attempt, jitter_factor, **kwargs
    )
