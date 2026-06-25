"""
Backoff Strategies

Implements various backoff strategies for retry operations including
exponential, linear, fixed, and custom backoff with jitter support.
"""

import random
import math
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from ..models.retry_policy import BackoffType, JitterType
from ..utils.time import BackoffCalculator


class BackoffStrategy(ABC):
    """Abstract base class for backoff strategies."""
    
    @abstractmethod
    def calculate_delay(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1
    ) -> float:
        """
        Calculate delay for retry attempt.
        
        Args:
            attempt: Current attempt number (1-based)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Backoff multiplier
            jitter_factor: Jitter factor (0.0-1.0)
            
        Returns:
            Delay in seconds
        """
        pass


class FixedBackoffStrategy(BackoffStrategy):
    """Fixed delay backoff strategy."""
    
    def calculate_delay(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1
    ) -> float:
        """Calculate fixed delay."""
        delay = base_delay
        return min(delay, max_delay)


class LinearBackoffStrategy(BackoffStrategy):
    """Linear backoff strategy."""
    
    def calculate_delay(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1
    ) -> float:
        """Calculate linear backoff delay."""
        delay = base_delay * attempt
        return min(delay, max_delay)


class ExponentialBackoffStrategy(BackoffStrategy):
    """Exponential backoff strategy."""
    
    def calculate_delay(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1
    ) -> float:
        """Calculate exponential backoff delay."""
        delay = base_delay * (multiplier ** (attempt - 1))
        return min(delay, max_delay)


class ExponentialWithJitterBackoffStrategy(BackoffStrategy):
    """Exponential backoff strategy with jitter."""
    
    def calculate_delay(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1
    ) -> float:
        """Calculate exponential backoff delay with jitter."""
        delay = base_delay * (multiplier ** (attempt - 1))
        delay = min(delay, max_delay)
        
        # Apply full jitter
        jitter = delay * jitter_factor * (random.random() * 2 - 1)
        return max(0, delay + jitter)


class CustomBackoffStrategy(BackoffStrategy):
    """Custom backoff strategy using a user-provided function."""
    
    def __init__(self, delay_function: callable):
        """
        Initialize custom backoff strategy.
        
        Args:
            delay_function: Function that takes (attempt, base_delay, max_delay, multiplier, jitter_factor)
                           and returns delay in seconds
        """
        self.delay_function = delay_function
    
    def calculate_delay(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1
    ) -> float:
        """Calculate custom delay."""
        try:
            delay = self.delay_function(attempt, base_delay, max_delay, multiplier, jitter_factor)
            return min(max(0, delay), max_delay)
        except Exception:
            # Fallback to exponential backoff if custom function fails
            return ExponentialBackoffStrategy().calculate_delay(
                attempt, base_delay, max_delay, multiplier, jitter_factor
            )


class BackoffStrategyFactory:
    """Factory for creating backoff strategies."""
    
    _strategies = {
        BackoffType.FIXED: FixedBackoffStrategy,
        BackoffType.LINEAR: LinearBackoffStrategy,
        BackoffType.EXPONENTIAL: ExponentialBackoffStrategy,
        BackoffType.EXPONENTIAL_WITH_JITTER: ExponentialWithJitterBackoffStrategy,
        BackoffType.CUSTOM: CustomBackoffStrategy
    }
    
    @classmethod
    def create_strategy(
        self,
        backoff_type: BackoffType,
        custom_function: Optional[callable] = None
    ) -> BackoffStrategy:
        """
        Create a backoff strategy instance.
        
        Args:
            backoff_type: Type of backoff strategy
            custom_function: Custom function for CUSTOM backoff type
            
        Returns:
            Backoff strategy instance
        """
        if backoff_type == BackoffType.CUSTOM:
            if not custom_function:
                raise ValueError("Custom function required for CUSTOM backoff type")
            return CustomBackoffStrategy(custom_function)
        
        strategy_class = self._strategies.get(backoff_type)
        if not strategy_class:
            raise ValueError(f"Unknown backoff type: {backoff_type}")
        
        return strategy_class()
    
    @classmethod
    def register_strategy(
        self,
        backoff_type: BackoffType,
        strategy_class: type
    ) -> None:
        """
        Register a custom backoff strategy.
        
        Args:
            backoff_type: Backoff type to register
            strategy_class: Strategy class to register
        """
        self._strategies[backoff_type] = strategy_class


class JitterCalculator:
    """Calculates jitter for backoff delays."""
    
    @staticmethod
    def apply_jitter(
        delay: float,
        jitter_type: JitterType,
        jitter_factor: float = 0.1
    ) -> float:
        """
        Apply jitter to a delay value.
        
        Args:
            delay: Original delay value
            jitter_type: Type of jitter to apply
            jitter_factor: Jitter factor (0.0-1.0)
            
        Returns:
            Delay with jitter applied
        """
        if jitter_type == JitterType.NONE:
            return delay
        
        if jitter_type == JitterType.FULL:
            # Full jitter: random between 0 and delay
            return delay * random.random()
        
        if jitter_type == JitterType.EQUAL:
            # Equal jitter: delay/2 ± delay/2 * jitter_factor
            half_delay = delay / 2
            jitter = half_delay * jitter_factor * (random.random() * 2 - 1)
            return half_delay + jitter
        
        if jitter_type == JitterType.DECORRELATED:
            # Decorrelated jitter: random between base_delay and delay * 3
            return random.uniform(delay * 0.1, delay * 3)
        
        return delay
    
    @staticmethod
    def calculate_full_jitter(delay: float, jitter_factor: float = 0.1) -> float:
        """Calculate full jitter."""
        return delay * jitter_factor * random.random()
    
    @staticmethod
    def calculate_equal_jitter(delay: float, jitter_factor: float = 0.1) -> float:
        """Calculate equal jitter."""
        half_delay = delay / 2
        jitter = half_delay * jitter_factor * (random.random() * 2 - 1)
        return half_delay + jitter
    
    @staticmethod
    def calculate_decorrelated_jitter(
        delay: float,
        base_delay: float,
        jitter_factor: float = 0.1
    ) -> float:
        """Calculate decorrelated jitter."""
        return random.uniform(base_delay, delay * 3)


# Predefined backoff strategies
FIXED_BACKOFF = BackoffStrategyFactory.create_strategy(BackoffType.FIXED)
LINEAR_BACKOFF = BackoffStrategyFactory.create_strategy(BackoffType.LINEAR)
EXPONENTIAL_BACKOFF = BackoffStrategyFactory.create_strategy(BackoffType.EXPONENTIAL)
EXPONENTIAL_WITH_JITTER_BACKOFF = BackoffStrategyFactory.create_strategy(
    BackoffType.EXPONENTIAL_WITH_JITTER
)


# Custom backoff functions
def fibonacci_backoff(attempt: int, base_delay: float, max_delay: float, **kwargs) -> float:
    """
    Fibonacci backoff strategy.
    
    Args:
        attempt: Current attempt number
        base_delay: Base delay
        max_delay: Maximum delay
        **kwargs: Additional arguments (ignored)
        
    Returns:
        Delay in seconds
    """
    # Calculate Fibonacci number
    if attempt <= 1:
        fib = 1
    else:
        fib = 1
        for i in range(2, attempt):
            fib += i
    
    delay = base_delay * fib
    return min(delay, max_delay)


def adaptive_backoff(attempt: int, base_delay: float, max_delay: float, **kwargs) -> float:
    """
    Adaptive backoff that adjusts based on attempt number.
    
    Args:
        attempt: Current attempt number
        base_delay: Base delay
        max_delay: Maximum delay
        **kwargs: Additional arguments (ignored)
        
    Returns:
        Delay in seconds
    """
    if attempt <= 3:
        # Aggressive for first few attempts
        multiplier = 1.5
    elif attempt <= 6:
        # Moderate for middle attempts
        multiplier = 2.0
    else:
        # Conservative for later attempts
        multiplier = 3.0
    
    delay = base_delay * (multiplier ** (attempt - 1))
    return min(delay, max_delay)


def bounded_exponential_backoff(attempt: int, base_delay: float, max_delay: float, **kwargs) -> float:
    """
    Bounded exponential backoff with upper limit.
    
    Args:
        attempt: Current attempt number
        base_delay: Base delay
        max_delay: Maximum delay
        **kwargs: Additional arguments (ignored)
        
    Returns:
        Delay in seconds
    """
    # Use a smaller multiplier to avoid reaching max_delay too quickly
    multiplier = 1.5
    delay = base_delay * (multiplier ** (attempt - 1))
    return min(delay, max_delay)


# Create custom strategies
FIBONACCI_BACKOFF = BackoffStrategyFactory.create_strategy(
    BackoffType.CUSTOM, fibonacci_backoff
)
ADAPTIVE_BACKOFF = BackoffStrategyFactory.create_strategy(
    BackoffType.CUSTOM, adaptive_backoff
)
BOUNDED_EXPONENTIAL_BACKOFF = BackoffStrategyFactory.create_strategy(
    BackoffType.CUSTOM, bounded_exponential_backoff
)


# Utility functions
def calculate_backoff_delay(
    attempt: int,
    backoff_type: BackoffType,
    base_delay: float,
    max_delay: float,
    multiplier: float = 2.0,
    jitter_type: JitterType = JitterType.NONE,
    jitter_factor: float = 0.1,
    custom_function: Optional[callable] = None
) -> float:
    """
    Calculate backoff delay using specified strategy.
    
    Args:
        attempt: Current attempt number (1-based)
        backoff_type: Type of backoff strategy
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        multiplier: Backoff multiplier
        jitter_type: Type of jitter to apply
        jitter_factor: Jitter factor (0.0-1.0)
        custom_function: Custom function for CUSTOM backoff type
        
    Returns:
        Delay in seconds
    """
    # Get base delay from strategy
    strategy = BackoffStrategyFactory.create_strategy(backoff_type, custom_function)
    delay = strategy.calculate_delay(attempt, base_delay, max_delay, multiplier, jitter_factor)
    
    # Apply jitter if not already applied by strategy
    if backoff_type != BackoffType.EXPONENTIAL_WITH_JITTER:
        delay = JitterCalculator.apply_jitter(delay, jitter_type, jitter_factor)
    
    return delay


def create_backoff_calculator(
    backoff_type: BackoffType,
    base_delay: float = 1.0,
    max_delay: float = 300.0,
    multiplier: float = 2.0,
    jitter_type: JitterType = JitterType.NONE,
    jitter_factor: float = 0.1,
    custom_function: Optional[callable] = None
) -> callable:
    """
    Create a backoff calculator function.
    
    Args:
        backoff_type: Type of backoff strategy
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        multiplier: Backoff multiplier
        jitter_type: Type of jitter to apply
        jitter_factor: Jitter factor (0.0-1.0)
        custom_function: Custom function for CUSTOM backoff type
        
    Returns:
        Function that takes attempt number and returns delay
    """
    def calculator(attempt: int) -> float:
        return calculate_backoff_delay(
            attempt, backoff_type, base_delay, max_delay,
            multiplier, jitter_type, jitter_factor, custom_function
        )
    
    return calculator


# Predefined calculators
def exponential_backoff_calculator(
    base_delay: float = 1.0,
    max_delay: float = 300.0,
    jitter_factor: float = 0.1
) -> callable:
    """Create exponential backoff calculator."""
    return create_backoff_calculator(
        BackoffType.EXPONENTIAL_WITH_JITTER,
        base_delay, max_delay, 2.0,
        JitterType.FULL, jitter_factor
    )


def linear_backoff_calculator(
    base_delay: float = 1.0,
    max_delay: float = 300.0,
    jitter_factor: float = 0.1
) -> callable:
    """Create linear backoff calculator."""
    return create_backoff_calculator(
        BackoffType.LINEAR,
        base_delay, max_delay, 1.0,
        JitterType.EQUAL, jitter_factor
    )


def fixed_backoff_calculator(
    delay: float = 1.0,
    jitter_factor: float = 0.1
) -> callable:
    """Create fixed backoff calculator."""
    return create_backoff_calculator(
        BackoffType.FIXED,
        delay, delay, 1.0,
        JitterType.FULL, jitter_factor
    )
