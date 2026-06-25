"""
Error handling infrastructure for the modular site scraper template system.

This module provides comprehensive error handling, recovery strategies,
circuit breakers, and resilience patterns for modular components.
"""

import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import functools
import logging
from contextlib import asynccontextmanager

from .component_interface import BaseComponent
from .logging import StructuredLogger, LogLevel, LogCategory


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    NETWORK = "network"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    COMPONENT = "component"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"
    TIMEOUT = "timeout"
    RESOURCE = "resource"


class RecoveryStrategy(Enum):
    """Recovery strategies for error handling."""
    RETRY = "retry"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK = "fallback"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    FAIL_FAST = "fail_fast"
    IGNORE = "ignore"


@dataclass
class ErrorContext:
    """Context information for errors."""
    component_id: Optional[str] = None
    operation: Optional[str] = None
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    site_id: Optional[str] = None
    environment: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


@dataclass
class ErrorInfo:
    """Detailed error information."""
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: datetime
    context: ErrorContext
    traceback: Optional[str] = None
    retry_count: int = 0
    recovery_attempts: List[str] = field(default_factory=list)
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.recovery_attempts is None:
            self.recovery_attempts = []


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_exceptions: List[Type[Exception]] = field(default_factory=lambda: [Exception])
    
    def __post_init__(self):
        if self.retry_on_exceptions is None:
            self.retry_on_exceptions = [Exception]


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout_ms: int = 60000
    expected_exception: Type[Exception] = Exception
    success_threshold: int = 3
    
    def __post_init__(self):
        pass


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker implementation for resilience."""
    
    def __init__(self, config: CircuitBreakerConfig, name: str):
        """
        Initialize circuit breaker.
        
        Args:
            config: Circuit breaker configuration
            name: Circuit breaker name
        """
        self.config = config
        self.name = name
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.logger = logging.getLogger(f"circuit_breaker.{name}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit breaker is open or function fails
        """
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.config.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if not self.last_failure_time:
            return False
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() * 1000 >= self.config.recovery_timeout_ms
    
    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(f"Circuit breaker {self.name} transitioning to OPEN")
        elif (self.state == CircuitBreakerState.CLOSED and 
              self.failure_count >= self.config.failure_threshold):
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(f"Circuit breaker {self.name} transitioning to OPEN")
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state information."""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class ErrorHandler:
    """Central error handler for modular components."""
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        """
        Initialize error handler.
        
        Args:
            logger: Structured logger instance
        """
        self.logger = logger or logging.getLogger("error_handler")
        self.error_history: List[ErrorInfo] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_handlers: Dict[ErrorCategory, List[Callable]] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        self.max_history_size = 1000
        
        # Register default error handlers
        self._register_default_handlers()
    
    def register_circuit_breaker(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """
        Register a circuit breaker.
        
        Args:
            name: Circuit breaker name
            config: Circuit breaker configuration
            
        Returns:
            Circuit breaker instance
        """
        circuit_breaker = CircuitBreaker(config, name)
        self.circuit_breakers[name] = circuit_breaker
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self.circuit_breakers.get(name)
    
    def register_error_handler(
        self,
        category: ErrorCategory,
        handler: Callable[[ErrorInfo], bool]
    ) -> None:
        """
        Register error handler for a category.
        
        Args:
            category: Error category
            handler: Error handler function (returns True if handled)
        """
        if category not in self.error_handlers:
            self.error_handlers[category] = []
        
        self.error_handlers[category].append(handler)
    
    def register_fallback_handler(self, operation: str, handler: Callable) -> None:
        """
        Register fallback handler for an operation.
        
        Args:
            operation: Operation name
            handler: Fallback handler function
        """
        self.fallback_handlers[operation] = handler
    
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY
    ) -> ErrorInfo:
        """
        Handle an error with appropriate recovery strategy.
        
        Args:
            error: Exception that occurred
            context: Error context
            severity: Error severity
            category: Error category
            recovery_strategy: Recovery strategy to use
            
        Returns:
            Error information
        """
        # Create error info
        error_info = ErrorInfo(
            error_type=type(error).__name__,
            error_message=str(error),
            severity=severity,
            category=category,
            timestamp=datetime.utcnow(),
            context=context,
            traceback=traceback.format_exc()
        )
        
        # Log error
        if self.logger:
            log_method = {
                ErrorSeverity.LOW: self.logger.debug,
                ErrorSeverity.MEDIUM: self.logger.warning,
                ErrorSeverity.HIGH: self.logger.error,
                ErrorSeverity.CRITICAL: self.logger.critical
            }.get(severity, self.logger.error)
            
            log_method(
                f"Error in {context.component_id}: {error_info.error_message}",
                category=LogCategory.SYSTEM,
                component_id=context.component_id,
                details={
                    'error_type': error_info.error_type,
                    'severity': severity.value,
                    'category': category.value,
                    'recovery_strategy': recovery_strategy.value
                }
            )
        
        # Apply recovery strategy
        await self._apply_recovery_strategy(error_info, recovery_strategy)
        
        # Store in history
        self._store_error(error_info)
        
        return error_info
    
    async def _apply_recovery_strategy(self, error_info: ErrorInfo, strategy: RecoveryStrategy) -> None:
        """Apply recovery strategy to error."""
        try:
            if strategy == RecoveryStrategy.RETRY:
                await self._retry_operation(error_info)
            elif strategy == RecoveryStrategy.FALLBACK:
                await self._apply_fallback(error_info)
            elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                await self._graceful_degradation(error_info)
            elif strategy == RecoveryStrategy.FAIL_FAST:
                # Don't attempt recovery
                pass
            elif strategy == RecoveryStrategy.IGNORE:
                # Mark as resolved
                error_info.resolved = True
                error_info.resolution_time = datetime.utcnow()
            
            # Run category-specific handlers
            await self._run_category_handlers(error_info)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Recovery strategy failed: {str(e)}")
    
    async def _retry_operation(self, error_info: ErrorInfo) -> None:
        """Retry operation with exponential backoff."""
        # This would be implemented with specific retry logic
        # For now, just record the attempt
        error_info.recovery_attempts.append("retry")
    
    async def _apply_fallback(self, error_info: ErrorInfo) -> None:
        """Apply fallback handler."""
        operation = error_info.context.operation
        if operation and operation in self.fallback_handlers:
            try:
                fallback_result = self.fallback_handlers[operation](error_info)
                if asyncio.iscoroutinefunction(self.fallback_handlers[operation]):
                    await fallback_result
                
                error_info.recovery_attempts.append("fallback")
                error_info.resolved = True
                error_info.resolution_time = datetime.utcnow()
                
            except Exception as e:
                error_info.recovery_attempts.append(f"fallback_failed: {str(e)}")
    
    async def _graceful_degradation(self, error_info: ErrorInfo) -> None:
        """Apply graceful degradation."""
        error_info.recovery_attempts.append("graceful_degradation")
        # Implementation would depend on specific degradation strategies
    
    async def _run_category_handlers(self, error_info: ErrorInfo) -> None:
        """Run category-specific error handlers."""
        if error_info.category in self.error_handlers:
            for handler in self.error_handlers[error_info.category]:
                try:
                    handled = await handler(error_info) if asyncio.iscoroutinefunction(handler) else handler(error_info)
                    if handled:
                        error_info.recovery_attempts.append(f"handler_{handler.__name__}")
                        break
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error handler failed: {str(e)}")
    
    def _store_error(self, error_info: ErrorInfo) -> None:
        """Store error in history."""
        self.error_history.append(error_info)
        
        # Maintain history size
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def _register_default_handlers(self) -> None:
        """Register default error handlers."""
        # Network error handler
        async def handle_network_error(error_info: ErrorInfo) -> bool:
            if error_info.category == ErrorCategory.NETWORK:
                # Implement network-specific recovery
                return False
            return False
        
        self.register_error_handler(ErrorCategory.NETWORK, handle_network_error)
        
        # Validation error handler
        async def handle_validation_error(error_info: ErrorInfo) -> bool:
            if error_info.category == ErrorCategory.VALIDATION:
                # Validation errors are usually not recoverable
                return False
            return False
        
        self.register_error_handler(ErrorCategory.VALIDATION, handle_validation_error)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics."""
        if not self.error_history:
            return {
                'total_errors': 0,
                'errors_by_severity': {},
                'errors_by_category': {},
                'resolved_errors': 0,
                'unresolved_errors': 0
            }
        
        errors_by_severity = {}
        errors_by_category = {}
        resolved_count = 0
        
        for error in self.error_history:
            # Count by severity
            severity = error.severity.value
            errors_by_severity[severity] = errors_by_severity.get(severity, 0) + 1
            
            # Count by category
            category = error.category.value
            errors_by_category[category] = errors_by_category.get(category, 0) + 1
            
            # Count resolved
            if error.resolved:
                resolved_count += 1
        
        return {
            'total_errors': len(self.error_history),
            'errors_by_severity': errors_by_severity,
            'errors_by_category': errors_by_category,
            'resolved_errors': resolved_count,
            'unresolved_errors': len(self.error_history) - resolved_count,
            'circuit_breakers': {
                name: cb.get_state() for name, cb in self.circuit_breakers.items()
            }
        }
    
    def get_recent_errors(self, limit: int = 50) -> List[ErrorInfo]:
        """Get recent errors."""
        return self.error_history[-limit:]
    
    async def cleanup(self) -> None:
        """Clean up error handler resources."""
        self.error_history.clear()
        self.circuit_breakers.clear()
        self.error_handlers.clear()
        self.fallback_handlers.clear()


def retry(
    max_attempts: int = 3,
    base_delay_ms: int = 1000,
    max_delay_ms: int = 30000,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: List[Type[Exception]] = None
):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay_ms: Base delay in milliseconds
        max_delay_ms: Maximum delay in milliseconds
        exponential_base: Exponential backoff base
        jitter: Add jitter to delay
        exceptions: List of exceptions to retry on
    """
    if exceptions is None:
        exceptions = [Exception]
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except tuple(exceptions) as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        break
                    
                    # Calculate delay
                    delay = min(
                        base_delay_ms * (exponential_base ** attempt),
                        max_delay_ms
                    )
                    
                    # Add jitter if enabled
                    if jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    await asyncio.sleep(delay / 1000.0)
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except tuple(exceptions) as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        break
                    
                    # Calculate delay
                    delay = min(
                        base_delay_ms * (exponential_base ** attempt),
                        max_delay_ms
                    )
                    
                    # Add jitter if enabled
                    if jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    import time
                    time.sleep(delay / 1000.0)
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout_ms: int = 60000,
    expected_exception: Type[Exception] = Exception,
    success_threshold: int = 3
):
    """
    Decorator for circuit breaker protection.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout_ms: Time to wait before attempting recovery
        expected_exception: Exception type to track
        success_threshold: Success count to close circuit
    """
    def decorator(func):
        circuit_breaker_instance = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                recovery_timeout_ms=recovery_timeout_ms,
                expected_exception=expected_exception,
                success_threshold=success_threshold
            ),
            func.__name__
        )
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await circuit_breaker_instance.call(func, *args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return circuit_breaker_instance.call(func, *args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


@asynccontextmanager
async def error_context(
    error_handler: ErrorHandler,
    component_id: str,
    operation: str,
    **context_kwargs
):
    """Context manager for error handling."""
    context = ErrorContext(
        component_id=component_id,
        operation=operation,
        **context_kwargs
    )
    
    try:
        yield context
    except Exception as e:
        await error_handler.handle_error(
            error=e,
            context=context,
            category=ErrorCategory.COMPONENT
        )
        raise


class ComponentErrorMixin:
    """Mixin for adding error handling to components."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._error_handler: Optional[ErrorHandler] = None
    
    def _setup_error_handling(self, component_id: str) -> None:
        """Setup error handling for the component."""
        self._error_handler = ErrorHandler()
    
    async def _handle_error(
        self,
        error: Exception,
        operation: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.COMPONENT
    ) -> ErrorInfo:
        """Handle error with component context."""
        if not self._error_handler:
            raise error
        
        context = ErrorContext(
            component_id=getattr(self, 'component_id', None),
            operation=operation
        )
        
        return await self._error_handler.handle_error(
            error=error,
            context=context,
            severity=severity,
            category=category
        )


class ErrorHandlingException(Exception):
    """Exception raised when error handling operations fail."""
    pass


class RecoveryException(ErrorHandlingException):
    """Exception raised when recovery strategies fail."""
    pass


class CircuitBreakerException(ErrorHandlingException):
    """Exception raised when circuit breaker operations fail."""
    pass
