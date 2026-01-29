"""
Comprehensive error handling for telemetry components.

This module provides centralized error handling, recovery strategies,
and error reporting for all telemetry system components.
"""

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
from functools import wraps
import weakref

from ..exceptions import (
    TelemetryError,
    TelemetryStorageError,
    TelemetryCollectionError,
    TelemetryProcessingError,
    TelemetryConfigurationError
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    STORAGE = "storage"
    COLLECTION = "collection"
    PROCESSING = "processing"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    PERFORMANCE = "performance"
    VALIDATION = "validation"
    SYSTEM = "system"


@dataclass
class ErrorContext:
    """Context information for errors."""
    component: str
    operation: str
    correlation_id: Optional[str] = None
    selector_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorReport:
    """Comprehensive error report."""
    error_id: str
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    exception_type: str
    stack_trace: str
    context: ErrorContext
    recovery_attempted: bool = False
    recovery_successful: bool = False
    retry_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RecoveryStrategy:
    """Base class for error recovery strategies."""
    
    def __init__(self, name: str, max_attempts: int = 3):
        self.name = name
        self.max_attempts = max_attempts
    
    async def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if this strategy can recover from the error."""
        raise NotImplementedError
    
    async def recover(self, error: Exception, context: ErrorContext) -> bool:
        """Attempt to recover from the error."""
        raise NotImplementedError


class RetryStrategy(RecoveryStrategy):
    """Retry recovery strategy with exponential backoff."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        super().__init__("retry", max_attempts)
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Retry for transient errors."""
        # Don't retry configuration or validation errors
        if isinstance(error, (TelemetryConfigurationError, ValueError)):
            return False
        
        # Retry network and temporary storage errors
        return isinstance(error, (TelemetryStorageError, ConnectionError, TimeoutError))
    
    async def recover(self, error: Exception, context: ErrorContext) -> bool:
        """Retry with exponential backoff."""
        delay = min(self.base_delay * (2 ** context.retry_count), self.max_delay)
        await asyncio.sleep(delay)
        return True


class FallbackStrategy(RecoveryStrategy):
    """Fallback recovery strategy using alternative methods."""
    
    def __init__(self, fallback_func: Callable):
        super().__init__("fallback", 1)
        self.fallback_func = fallback_func
    
    async def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Use fallback for storage failures."""
        return isinstance(error, TelemetryStorageError)
    
    async def recover(self, error: Exception, context: ErrorContext) -> bool:
        """Execute fallback function."""
        try:
            await self.fallback_func(context)
            return True
        except Exception:
            return False


class GracefulDegradationStrategy(RecoveryStrategy):
    """Graceful degradation strategy."""
    
    def __init__(self):
        super().__init__("graceful_degradation", 1)
    
    async def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Always attempt graceful degradation."""
        return True
    
    async def recover(self, error: Exception, context: ErrorContext) -> bool:
        """Log error and continue with reduced functionality."""
        logger.warning(f"Graceful degradation activated for {context.component}: {error}")
        return True


class ErrorHandler:
    """Centralized error handler for telemetry components."""
    
    def __init__(self):
        self.recovery_strategies: List[RecoveryStrategy] = []
        self.error_reports: List[ErrorReport] = []
        self.error_callbacks: List[Callable] = []
        self._lock = asyncio.Lock()
        
        # Default recovery strategies
        self.add_recovery_strategy(RetryStrategy())
        self.add_recovery_strategy(FallbackStrategy(self._default_fallback))
        self.add_recovery_strategy(GracefulDegradationStrategy())
    
    def add_recovery_strategy(self, strategy: RecoveryStrategy) -> None:
        """Add a recovery strategy."""
        self.recovery_strategies.append(strategy)
    
    def add_error_callback(self, callback: Callable) -> None:
        """Add error callback for notification."""
        self.error_callbacks.append(callback)
    
    async def handle_error(self,
                          error: Exception,
                          context: ErrorContext,
                          retry_count: int = 0) -> bool:
        """Handle error with recovery strategies."""
        context.retry_count = retry_count
        
        # Create error report
        error_report = self._create_error_report(error, context)
        
        # Log error
        self._log_error(error_report)
        
        # Attempt recovery
        recovery_successful = await self._attempt_recovery(error, context)
        
        # Update error report
        error_report.recovery_attempted = True
        error_report.recovery_successful = recovery_successful
        
        # Store error report
        async with self._lock:
            self.error_reports.append(error_report)
        
        # Notify callbacks
        await self._notify_callbacks(error_report)
        
        return recovery_successful
    
    def _create_error_report(self, error: Exception, context: ErrorContext) -> ErrorReport:
        """Create comprehensive error report."""
        error_id = f"{context.component}_{context.operation}_{int(context.timestamp.timestamp())}"
        
        # Classify error
        severity = self._classify_severity(error)
        category = self._classify_category(error)
        
        return ErrorReport(
            error_id=error_id,
            severity=severity,
            category=category,
            message=str(error),
            exception_type=type(error).__name__,
            stack_trace=traceback.format_exc(),
            context=context
        )
    
    def _classify_severity(self, error: Exception) -> ErrorSeverity:
        """Classify error severity."""
        if isinstance(error, (TelemetryConfigurationError, ValueError)):
            return ErrorSeverity.HIGH
        elif isinstance(error, TelemetryStorageError):
            return ErrorSeverity.MEDIUM
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorSeverity.MEDIUM
        elif isinstance(error, TelemetryError):
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.HIGH
    
    def _classify_category(self, error: Exception) -> ErrorCategory:
        """Classify error category."""
        if isinstance(error, TelemetryStorageError):
            return ErrorCategory.STORAGE
        elif isinstance(error, TelemetryCollectionError):
            return ErrorCategory.COLLECTION
        elif isinstance(error, TelemetryProcessingError):
            return ErrorCategory.PROCESSING
        elif isinstance(error, TelemetryConfigurationError):
            return ErrorCategory.CONFIGURATION
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK
        elif isinstance(error, (MemoryError, OSError)):
            return ErrorCategory.SYSTEM
        elif isinstance(error, ValueError):
            return ErrorCategory.VALIDATION
        else:
            return ErrorCategory.SYSTEM
    
    def _log_error(self, error_report: ErrorReport) -> None:
        """Log error with appropriate level."""
        log_level = {
            ErrorSeverity.LOW: logging.WARNING,
            ErrorSeverity.MEDIUM: logging.ERROR,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_report.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"Error in {error_report.context.component}.{error_report.context.operation}: "
            f"{error_report.message} (ID: {error_report.error_id})"
        )
    
    async def _attempt_recovery(self, error: Exception, context: ErrorContext) -> bool:
        """Attempt recovery using available strategies."""
        for strategy in self.recovery_strategies:
            try:
                if await strategy.can_recover(error, context):
                    if context.retry_count < strategy.max_attempts:
                        logger.info(f"Attempting {strategy.name} recovery for {context.component}")
                        success = await strategy.recover(error, context)
                        if success:
                            logger.info(f"Recovery successful using {strategy.name}")
                            return True
                        else:
                            logger.warning(f"Recovery failed using {strategy.name}")
            except Exception as recovery_error:
                logger.error(f"Recovery strategy {strategy.name} failed: {recovery_error}")
        
        return False
    
    async def _notify_callbacks(self, error_report: ErrorReport) -> None:
        """Notify error callbacks."""
        for callback in self.error_callbacks:
            try:
                await callback(error_report)
            except Exception as callback_error:
                logger.error(f"Error callback failed: {callback_error}")
    
    async def _default_fallback(self, context: ErrorContext) -> None:
        """Default fallback action."""
        logger.warning(f"Using default fallback for {context.component}")
    
    async def get_error_summary(self, 
                               since: Optional[datetime] = None,
                               severity: Optional[ErrorSeverity] = None) -> Dict[str, Any]:
        """Get error summary statistics."""
        async with self._lock:
            filtered_reports = self.error_reports
            
            if since:
                filtered_reports = [r for r in filtered_reports if r.timestamp >= since]
            
            if severity:
                filtered_reports = [r for r in filtered_reports if r.severity == severity]
            
            # Calculate statistics
            total_errors = len(filtered_reports)
            recovery_rate = sum(1 for r in filtered_reports if r.recovery_successful) / max(total_errors, 1)
            
            # Group by category
            category_counts = {}
            for report in filtered_reports:
                category_counts[report.category.value] = category_counts.get(report.category.value, 0) + 1
            
            # Group by severity
            severity_counts = {}
            for report in filtered_reports:
                severity_counts[report.severity.value] = severity_counts.get(report.severity.value, 0) + 1
            
            return {
                'total_errors': total_errors,
                'recovery_rate': recovery_rate,
                'category_counts': category_counts,
                'severity_counts': severity_counts,
                'recent_errors': [r for r in filtered_reports[-10:]]
            }
    
    async def clear_old_errors(self, older_than_hours: int = 24) -> int:
        """Clear old error reports."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        
        async with self._lock:
            original_count = len(self.error_reports)
            self.error_reports = [r for r in self.error_reports if r.timestamp >= cutoff_time]
            cleared_count = original_count - len(self.error_reports)
        
        logger.info(f"Cleared {cleared_count} old error reports")
        return cleared_count


# Global error handler instance
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_errors(component: str, operation: str):
    """Decorator for automatic error handling."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            error_handler = get_error_handler()
            
            # Extract context information
            correlation_id = kwargs.get('correlation_id')
            selector_id = kwargs.get('selector_id')
            
            context = ErrorContext(
                component=component,
                operation=operation,
                correlation_id=correlation_id,
                selector_id=selector_id
            )
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Handle error with recovery
                recovery_successful = await error_handler.handle_error(e, context)
                
                if recovery_successful:
                    # Retry the function once after successful recovery
                    try:
                        return await func(*args, **kwargs)
                    except Exception as retry_error:
                        await error_handler.handle_error(retry_error, context, retry_count=1)
                
                # Re-raise if recovery failed
                raise
        
        return wrapper
    return decorator


async def safe_execute(func: Callable,
                      component: str,
                      operation: str,
                      *args,
                      **kwargs) -> Optional[Any]:
    """Safely execute function with error handling."""
    error_handler = get_error_handler()
    
    context = ErrorContext(
        component=component,
        operation=operation,
        correlation_id=kwargs.get('correlation_id'),
        selector_id=kwargs.get('selector_id')
    )
    
    try:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    except Exception as e:
        await error_handler.handle_error(e, context)
        return None


class ErrorReporter:
    """Error reporting and analytics."""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
    
    async def generate_error_report(self, 
                                  since: Optional[datetime] = None,
                                  format: str = 'summary') -> Dict[str, Any]:
        """Generate comprehensive error report."""
        summary = await self.error_handler.get_error_summary(since=since)
        
        if format == 'detailed':
            return {
                'summary': summary,
                'trends': await self._analyze_error_trends(since),
                'recommendations': await self._generate_recommendations(summary),
                'top_errors': await self._get_top_errors(since)
            }
        else:
            return summary
    
    async def _analyze_error_trends(self, since: Optional[datetime]) -> Dict[str, Any]:
        """Analyze error trends over time."""
        # Implementation for trend analysis
        return {}
    
    async def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on error patterns."""
        recommendations = []
        
        if summary['recovery_rate'] < 0.8:
            recommendations.append("Review recovery strategies - success rate below 80%")
        
        if summary['category_counts'].get('storage', 0) > summary['total_errors'] * 0.5:
            recommendations.append("High storage error rate - check storage configuration")
        
        if summary['severity_counts'].get('critical', 0) > 0:
            recommendations.append("Critical errors detected - immediate attention required")
        
        return recommendations
    
    async def _get_top_errors(self, since: Optional[datetime]) -> List[Dict[str, Any]]:
        """Get most frequent errors."""
        # Implementation for top errors analysis
        return []
