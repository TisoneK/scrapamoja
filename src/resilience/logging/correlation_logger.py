"""
Correlation ID Logging for Failure Handling

Specialized logging for failure events with enhanced correlation tracking,
context propagation, and structured output for debugging and analysis.
"""

import json
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

from ..correlation import get_correlation_id, with_correlation_id
from ..models.failure_event import FailureEvent, FailureSeverity, FailureCategory
from .resilience_logger import ResilienceLogger


class CorrelationLogger:
    """Logger with enhanced correlation ID tracking for failure events."""
    
    def __init__(self, name: str = "correlation_logger"):
        """
        Initialize correlation logger.
        
        Args:
            name: Logger name
        """
        self.logger = ResilienceLogger(name)
    
    def log_failure_with_correlation(
        self,
        failure: FailureEvent,
        correlation_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a failure event with correlation ID tracking.
        
        Args:
            failure: The failure event to log
            correlation_id: Correlation ID (uses current if not provided)
            additional_context: Additional context information
        """
        effective_correlation_id = correlation_id or get_correlation_id()
        
        context = {
            "failure_id": failure.id,
            "severity": failure.severity.value,
            "category": failure.category.value,
            "source": failure.source,
            "resolved": failure.resolved,
            "resolution_time": failure.resolution_time,
            "job_id": failure.job_id,
            "component": failure.component,
            "operation": failure.operation,
            "recovery_action": failure.recovery_action.value if failure.recovery_action else None,
            "correlation_id": effective_correlation_id,
            **failure.context,
            **(additional_context or {})
        }
        
        # Determine log level based on severity
        if failure.severity == FailureSeverity.CRITICAL:
            self.logger.critical(
                f"[{effective_correlation_id}] CRITICAL FAILURE: {failure.message}",
                event_type="correlated_failure_event",
                correlation_id=effective_correlation_id,
                context=context,
                component=failure.source
            )
        elif failure.severity == FailureSeverity.HIGH:
            self.logger.error(
                f"[{effective_correlation_id}] HIGH SEVERITY FAILURE: {failure.message}",
                event_type="correlated_failure_event",
                correlation_id=effective_correlation_id,
                context=context,
                component=failure.source
            )
        elif failure.severity == FailureSeverity.MEDIUM:
            self.logger.warning(
                f"[{effective_correlation_id}] MEDIUM SEVERITY FAILURE: {failure.message}",
                event_type="correlated_failure_event",
                correlation_id=effective_correlation_id,
                context=context,
                component=failure.source
            )
        else:
            self.logger.info(
                f"[{effective_correlation_id}] LOW SEVERITY FAILURE: {failure.message}",
                event_type="correlated_failure_event",
                correlation_id=effective_correlation_id,
                context=context,
                component=failure.source
            )
    
    def log_failure_chain(
        self,
        failures: list[FailureEvent],
        correlation_id: Optional[str] = None,
        chain_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a chain of related failures with correlation tracking.
        
        Args:
            failures: List of related failure events
            correlation_id: Correlation ID for the chain
            chain_context: Additional context for the chain
        """
        effective_correlation_id = correlation_id or get_correlation_id()
        
        chain_info = {
            "chain_length": len(failures),
            "chain_timestamp": datetime.utcnow().isoformat(),
            **(chain_context or {})
        }
        
        for i, failure in enumerate(failures):
            context = {
                "chain_index": i,
                "chain_info": chain_info,
                "chain_correlation_id": effective_correlation_id
            }
            
            self.log_failure_with_correlation(failure, effective_correlation_id, context)
    
    def log_correlation_context(
        self,
        correlation_id: str,
        context_type: str,
        context_data: Dict[str, Any],
        severity: str = "info"
    ) -> None:
        """
        Log correlation context information.
        
        Args:
            correlation_id: Correlation ID
            context_type: Type of context (e.g., "operation_start", "operation_end")
            context_data: Context data
            severity: Log level
        """
        self.logger.info(
            f"[{correlation_id}] {context_type}: {json.dumps(context_data, default=str)}",
            event_type="correlation_context",
            correlation_id=correlation_id,
            context={
                "context_type": context_type,
                "context_data": context_data,
                "severity": severity
            },
            component="correlation_logger"
        )
    
    def log_operation_start(
        self,
        operation: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log the start of an operation with correlation tracking.
        
        Args:
            operation: Operation description
            correlation_id: Correlation ID (generates new if not provided)
            context: Additional context
            
        Returns:
            Correlation ID for the operation
        """
        effective_correlation_id = correlation_id or get_correlation_id()
        
        context_data = {
            "operation": operation,
            "status": "started",
            "timestamp": datetime.utcnow().isoformat(),
            **(context or {})
        }
        
        self.log_correlation_context(
            effective_correlation_id, "operation_start", context_data
        )
        
        return effective_correlation_id
    
    def log_operation_end(
        self,
        operation: str,
        correlation_id: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log the end of an operation with correlation tracking.
        
        Args:
            operation: Operation description
            correlation_id: Correlation ID
            success: Whether operation succeeded
            result: Operation result
            context: Additional context
        """
        context_data = {
            "operation": operation,
            "status": "completed" if success else "failed",
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            **(result or {}),
            **(context or {})
        }
        
        self.log_correlation_context(
            correlation_id, "operation_end", context_data, "warning" if not success else "info"
        )
    
    def log_error_with_correlation(
        self,
        error: Exception,
        operation: Optional[str] = None,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log an error with correlation tracking.
        
        Args:
            error: The exception to log
            operation: Related operation
            correlation_id: Correlation ID (generates new if not provided)
            context: Additional context
            
        Returns:
            Correlation ID for the error
        """
        effective_correlation_id = correlation_id or get_correlation_id()
        
        context_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat(),
            **(context or {})
        }
        
        self.logger.error(
            f"[{effective_correlation_id}] Error in {operation or 'unknown operation'}: {str(error)}",
            event_type="correlated_error",
            correlation_id=effective_correlation_id,
            context=context_data,
            component="correlation_logger"
        )
        
        return effective_correlation_id
    
    def log_recovery_with_correlation(
        self,
        original_error: str,
        recovery_action: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log recovery information with correlation tracking.
        
        Args:
            original_error: Original error message
            recovery_action: Recovery action taken
            correlation_id: Correlation ID
            context: Additional context
        """
        effective_correlation_id = correlation_id or get_correlation_id()
        
        context_data = {
            "original_error": original_error,
            "recovery_action": recovery_action,
            "timestamp": datetime.utcnow().isoformat(),
            **(context or {})
        }
        
        self.logger.info(
            f"[{effective_correlation_id}] Recovery: {recovery_action} for error: {original_error}",
            event_type="correlated_recovery",
            correlation_id=effective_correlation_id,
            context=context_data,
            component="correlation_logger"
        )
    
    def create_correlation_context(
        self,
        correlation_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> 'CorrelationContext':
        """
        Create a correlation context manager.
        
        Args:
            correlation_id: Correlation ID
            initial_context: Initial context data
            
        Returns:
            CorrelationContext manager
        """
        return CorrelationContext(self, correlation_id, initial_context)
    
    def trace_operation(
        self,
        operation: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracing an operation with correlation tracking.
        
        Args:
            operation: Operation description
            correlation_id: Correlation ID (generates new if not provided)
            context: Additional context
            
        Returns:
            Context manager for the operation
        """
        return self.create_correlation_context(
            correlation_id or get_correlation_id(),
            {"operation": operation, **(context or {})}
        )


class CorrelationContext:
    """Context manager for correlation tracking during operations."""
    
    def __init__(
        self,
        logger: CorrelationLogger,
        correlation_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize correlation context.
        
        Args:
            logger: Correlation logger instance
            correlation_id: Correlation ID
            initial_context: Initial context data
        """
        self.logger = logger
        self.correlation_id = correlation_id
        self.initial_context = initial_context or {}
        self.start_time = datetime.utcnow()
        self.operations = []
    
    def __enter__(self):
        """Enter the correlation context."""
        # Log operation start
        self.correlation_id = self.logger.log_operation_start(
            "correlation_context_enter",
            self.correlation_id,
            {
                "initial_context": self.initial_context,
                "start_time": self.start_time.isoformat()
            }
        )
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the correlation context."""
        # Log operation end
        success = exc_type is None
        result = {"success": success}
        
        if not success and exc_val:
            result["error"] = str(exc_val)
            result["error_type"] = type(exc_val).__name__
        
        self.logger.log_operation_end(
            "correlation_context_exit",
            self.correlation_id,
            success,
            result,
            {
                "operations": self.operations,
                "duration": (datetime.utcnow() - self.start_time).total_seconds(),
                "initial_context": self.initial_context
            }
        )
    
    def log_operation(self, operation: str, **kwargs) -> None:
        """
        Log an operation within the correlation context.
        
        Args:
            operation: Operation description
            **kwargs: Additional context
        """
        self.operations.append({
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        })
        
        self.logger.info(
            f"[{self.correlation_id}] Operation: {operation}",
            event_type="correlation_operation",
            correlation_id=self.correlation_id,
            context={
                "operation": operation,
                "operations_count": len(self.operations),
                **kwargs
            },
            component="correlation_logger"
        )
    
    def log_failure(self, failure: FailureEvent, **kwargs) -> None:
        """
        Log a failure within the correlation context.
        
        Args:
            failure: Failure event to log
            **kwargs: Additional context
        """
        self.logger.log_failure_with_correlation(failure, self.correlation_id, kwargs)
    
    def log_error(self, error: Exception, operation: Optional[str] = None, **kwargs) -> None:
        """
        Log an error within the correlation context.
        
        Args:
            error: Exception to log
            operation: Related operation
            **kwargs: Additional context
        """
        self.logger.log_error_with_correlation(error, operation, self.correlation_id, kwargs)


# Global correlation logger instance
_correlation_logger = CorrelationLogger()


def get_correlation_logger() -> CorrelationLogger:
    """Get the global correlation logger instance."""
    return _correlation_logger


def log_failure_with_correlation(
    failure: FailureEvent,
    correlation_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log a failure event with correlation tracking using the global logger."""
    _correlation_logger.log_failure_with_correlation(failure, correlation_id, additional_context)


def trace_operation_with_correlation(
    operation: str,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> CorrelationContext:
    """Create a correlation context manager for operation tracing."""
    return _correlation_logger.trace_operation(operation, correlation_id, context)
