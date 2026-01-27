"""
Browser Resilience Framework

This module provides retry logic, circuit breaker patterns, and graceful
failure handling for browser operations, following the Production Resilience
constitution principle.
"""

import asyncio
import random
import time
from typing import Optional, Callable, Any, Dict, Type, Union
from enum import Enum
import structlog

from .exceptions import BrowserError


class RetryStrategy(Enum):
    """Retry strategies for different failure types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovery occurred


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Type[Exception]] = None
    ):
        self.max_attempts = max_attempts
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (BrowserError,)


class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = BrowserError
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception


class CircuitBreaker:
    """Circuit breaker for preventing cascade failures."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.logger = structlog.get_logger("browser.circuit_breaker")
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker half-open", failure_count=self.failure_count)
            else:
                raise BrowserError("CIRCUIT_OPEN", "Circuit breaker is open")
                
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise
            
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.config.recovery_timeout
        
    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.logger.info("Circuit breaker closed", failure_count=self.failure_count)
            
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(
                "Circuit breaker opened",
                failure_count=self.failure_count,
                threshold=self.config.failure_threshold
            )


class RetryHandler:
    """Handles retry logic with various strategies."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.logger = structlog.get_logger("browser.retry")
        
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except self.config.retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.config.max_attempts:
                    self.logger.error(
                        "All retry attempts exhausted",
                        attempt=attempt,
                        max_attempts=self.config.max_attempts,
                        error=str(e),
                        context=context
                    )
                    raise
                    
                delay = self._calculate_delay(attempt - 1)
                self.logger.warning(
                    "Retry attempt failed",
                    attempt=attempt,
                    max_attempts=self.config.max_attempts,
                    delay=delay,
                    error=str(e),
                    context=context
                )
                
                await asyncio.sleep(delay)
                
        raise last_exception
        
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay based on strategy."""
        if self.config.strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif self.config.strategy == RetryStrategy.FIXED_DELAY:
            return self.config.base_delay
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * (attempt + 1)
        else:  # EXPONENTIAL_BACKOFF
            delay = self.config.base_delay * (self.config.backoff_multiplier ** attempt)
            
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            # Add ±25% jitter
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
            
        return max(0, delay)


class ResilienceManager:
    """Manages retry and circuit breaker strategies."""
    
    def __init__(self):
        self.retry_configs: Dict[str, RetryConfig] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = structlog.get_logger("browser.resilience")
        
    def register_retry_config(self, name: str, config: RetryConfig) -> None:
        """Register retry configuration."""
        self.retry_configs[name] = config
        self.logger.debug("Retry config registered", name=name, config=config.strategy.value)
        
    def register_circuit_breaker(self, name: str, config: CircuitBreakerConfig) -> None:
        """Register circuit breaker."""
        self.circuit_breakers[name] = CircuitBreaker(config)
        self.logger.debug("Circuit breaker registered", name=name)
        
    async def execute_with_resilience(
        self,
        operation_name: str,
        func: Callable,
        *args,
        retry_config: Optional[str] = None,
        circuit_breaker: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Execute function with resilience patterns."""
        context = context or {}
        
        # Apply circuit breaker if specified
        if circuit_breaker and circuit_breaker in self.circuit_breakers:
            func = self.circuit_breakers[circuit_breaker].call(func)
            
        # Apply retry logic if specified
        if retry_config and retry_config in self.retry_configs:
            return await self.retry_configs[retry_config].execute_with_retry(
                func, *args, context=context, **kwargs
            )
        else:
            return await func(*args, **kwargs)
            
    def get_circuit_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: {
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "last_failure_time": cb.last_failure_time
            }
            for name, cb in self.circuit_breakers.items()
        }


# Global resilience manager
resilience_manager = ResilienceManager()

# Default configurations
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0,
    max_delay=30.0
)

DEFAULT_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60.0
)

# Register defaults
resilience_manager.register_retry_config("default", DEFAULT_RETRY_CONFIG)
resilience_manager.register_circuit_breaker("default", DEFAULT_CIRCUIT_CONFIG)
