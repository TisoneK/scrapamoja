"""
Retry Event Logging

Specialized logging for retry operations with detailed context, correlation tracking,
and structured output for debugging and analysis of retry behavior.
"""

import json
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..correlation import get_correlation_id
from ..models.retry_policy import RetryPolicy, BackoffType, JitterType
from .resilience_logger import ResilienceLogger


class RetryLogger:
    """Specialized logger for retry operations with enhanced context tracking."""
    
    def __init__(self, name: str = "retry_logger"):
        """
        Initialize retry logger.
        
        Args:
            name: Logger name
        """
        self.logger = ResilienceLogger(name)
    
    def log_retry_attempt(
        self,
        operation: str,
        attempt: int,
        max_attempts: int,
        delay: float,
        policy_id: str,
        policy_name: str,
        backoff_type: BackoffType,
        jitter_type: JitterType,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a retry attempt with comprehensive context.
        
        Args:
            operation: Operation being retried
            attempt: Current attempt number
            max_attempts: Maximum number of attempts
            delay: Delay before this attempt
            policy_id: Retry policy ID
            policy_name: Retry policy name
            backoff_type: Type of backoff strategy
            jitter_type: Type of jitter strategy
            correlation_id: Correlation ID
            context: Additional context information
        """
        log_context = {
            "operation": operation,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "delay": delay,
            "policy_id": policy_id,
            "policy_name": policy_name,
            "backoff_type": backoff_type.value,
            "jitter_type": jitter_type.value,
            "retry_progress": f"{attempt}/{max_attempts}",
            "remaining_attempts": max_attempts - attempt,
            **(context or {})
        }
        
        # Determine log level based on attempt number
        if attempt == 1:
            level = "info"
        elif attempt <= max_attempts // 2:
            level = "warning"
        else:
            level = "error"
        
        message = (
            f"Retry attempt {attempt}/{max_attempts} for {operation} "
            f"after {delay:.2f}s delay (policy: {policy_name})"
        )
        
        self.logger._log_structured(
            level=level,
            message=message,
            event_type="retry_attempt",
            correlation_id=correlation_id or get_correlation_id(),
            context=log_context,
            component="retry_manager"
        )
    
    def log_retry_success(
        self,
        operation: str,
        attempt: int,
        total_attempts: int,
        total_duration: float,
        policy_id: str,
        policy_name: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log successful retry operation.
        
        Args:
            operation: Operation that succeeded
            attempt: Successful attempt number
            total_attempts: Total number of attempts made
            total_duration: Total duration of all attempts
            policy_id: Retry policy ID
            policy_name: Retry policy name
            correlation_id: Correlation ID
            context: Additional context information
        """
        log_context = {
            "operation": operation,
            "successful_attempt": attempt,
            "total_attempts": total_attempts,
            "total_duration": total_duration,
            "policy_id": policy_id,
            "policy_name": policy_name,
            "retry_count": total_attempts - 1,
            "success_rate": (1.0 / total_attempts) * 100,
            "average_attempt_duration": total_duration / total_attempts,
            **(context or {})
        }
        
        message = (
            f"Operation succeeded on attempt {attempt}/{total_attempts}: {operation} "
            f"(total duration: {total_duration:.2f}s, policy: {policy_name})"
        )
        
        self.logger.info(
            message=message,
            event_type="retry_success",
            correlation_id=correlation_id or get_correlation_id(),
            context=log_context,
            component="retry_manager"
        )
    
    def log_retry_failure(
        self,
        operation: str,
        error: Exception,
        attempt: int,
        max_attempts: int,
        policy_id: str,
        policy_name: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log retry failure.
        
        Args:
            operation: Operation that failed
            error: The error that occurred
            attempt: Failed attempt number
            max_attempts: Maximum number of attempts
            policy_id: Retry policy ID
            policy_name: Retry policy name
            correlation_id: Correlation ID
            context: Additional context information
        """
        log_context = {
            "operation": operation,
            "failed_attempt": attempt,
            "max_attempts": max_attempts,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "policy_id": policy_id,
            "policy_name": policy_name,
            "will_retry": attempt < max_attempts,
            "remaining_attempts": max_attempts - attempt,
            "stack_trace": traceback.format_exc(),
            **(context or {})
        }
        
        message = (
            f"Operation failed on attempt {attempt}/{max_attempts}: {operation} - {str(error)}"
        )
        
        self.logger.error(
            message=message,
            event_type="retry_failure",
            correlation_id=correlation_id or get_correlation_id(),
            context=log_context,
            component="retry_manager"
        )
    
    def log_max_retries_exceeded(
        self,
        operation: str,
        max_attempts: int,
        total_duration: float,
        last_error: Exception,
        policy_id: str,
        policy_name: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log when maximum retry attempts are exceeded.
        
        Args:
            operation: Operation that failed
            max_attempts: Maximum number of attempts
            total_duration: Total duration of all attempts
            last_error: The final error that occurred
            policy_id: Retry policy ID
            policy_name: Retry policy name
            correlation_id: Correlation ID
            context: Additional context information
        """
        log_context = {
            "operation": operation,
            "max_attempts": max_attempts,
            "total_duration": total_duration,
            "last_error_type": type(last_error).__name__,
            "last_error_message": str(last_error),
            "policy_id": policy_id,
            "policy_name": policy_name,
            "average_attempt_duration": total_duration / max_attempts,
            "failure_rate": 100.0,
            "stack_trace": traceback.format_exc(),
            **(context or {})
        }
        
        message = (
            f"Maximum retry attempts exceeded for {operation}: "
            f"{max_attempts} attempts over {total_duration:.2f}s - {str(last_error)}"
        )
        
        self.logger.critical(
            message=message,
            event_type="max_retries_exceeded",
            correlation_id=correlation_id or get_correlation_id(),
            context=log_context,
            component="retry_manager"
        )
    
    def log_permanent_failure(
        self,
        operation: str,
        error: Exception,
        policy_id: str,
        policy_name: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log permanent failure (non-retryable).
        
        Args:
            operation: Operation that failed permanently
            error: The error that occurred
            policy_id: Retry policy ID
            policy_name: Retry policy name
            correlation_id: Correlation ID
            context: Additional context information
        """
        log_context = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "policy_id": policy_id,
            "policy_name": policy_name,
            "failure_classification": "permanent",
            "stack_trace": traceback.format_exc(),
            **(context or {})
        }
        
        message = (
            f"Permanent failure for {operation}: {str(error)} (policy: {policy_name})"
        )
        
        self.logger.error(
            message=message,
            event_type="permanent_failure",
            correlation_id=correlation_id or get_correlation_id(),
            context=log_context,
            component="retry_manager"
        )
    
    def log_rate_limit_detected(
        self,
        operation: str,
        limit_type: str,
        strategy: str,
        wait_time: float,
        policy_id: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log rate limiting detection.
        
        Args:
            operation: Operation being rate limited
            limit_type: Type of rate limiting
            strategy: Strategy being used
            wait_time: Time to wait before retry
            policy_id: Retry policy ID
            correlation_id: Correlation ID
            context: Additional context information
        """
        log_context = {
            "operation": operation,
            "limit_type": limit_type,
            "strategy": strategy,
            "wait_time": wait_time,
            "policy_id": policy_id,
            "rate_limiting": True,
            **(context or {})
        }
        
        message = (
            f"Rate limiting detected for {operation}: {limit_type} "
            f"(strategy: {strategy}, wait: {wait_time:.2f}s)"
        )
        
        self.logger.warning(
            message=message,
            event_type="rate_limit_detected",
            correlation_id=correlation_id or get_correlation_id(),
            context=log_context,
            component="retry_manager"
        )
    
    def log_circuit_breaker_opened(
        self,
        policy_id: str,
        policy_name: str,
        failure_count: int,
        threshold: int,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log circuit breaker opening.
        
        Args:
            policy_id: Retry policy ID
            policy_name: Retry policy name
            failure_count: Number of failures that triggered opening
            threshold: Failure threshold
            correlation_id: Correlation ID
            context: Additional context information
        """
        log_context = {
            "policy_id": policy_id,
            "policy_name": policy_name,
            "failure_count": failure_count,
            "threshold": threshold,
            "circuit_breaker_state": "open",
            **(context or {})
        }
        
        message = (
            f"Circuit breaker opened for policy {policy_name}: "
            f"{failure_count}/{threshold} failures"
        )
        
        self.logger.warning(
            message=message,
            event_type="circuit_breaker_opened",
            correlation_id=correlation_id or get_correlation_id(),
            context=log_context,
            component="retry_manager"
        )
    
    def log_retry_session_summary(
        self,
        session_id: str,
        operation: str,
        total_attempts: int,
        success: bool,
        total_duration: float,
        policy_id: str,
        policy_name: str,
        final_result: Optional[Any] = None,
        final_error: Optional[Exception] = None,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log summary of a complete retry session.
        
        Args:
            session_id: Unique session identifier
            operation: Operation that was retried
            total_attempts: Total number of attempts made
            success: Whether the operation eventually succeeded
            total_duration: Total duration of the session
            policy_id: Retry policy ID
            policy_name: Retry policy name
            final_result: Final result if successful
            final_error: Final error if failed
            correlation_id: Correlation ID
            context: Additional context information
        """
        log_context = {
            "session_id": session_id,
            "operation": operation,
            "total_attempts": total_attempts,
            "success": success,
            "total_duration": total_duration,
            "policy_id": policy_id,
            "policy_name": policy_name,
            "retry_count": total_attempts - 1,
            "success_rate": (100.0 if success else 0.0),
            "average_attempt_duration": total_duration / total_attempts,
            **(context or {})
        }
        
        if success:
            log_context["final_result"] = str(final_result) if final_result else None
            message = (
                f"Retry session completed successfully: {operation} "
                f"({total_attempts} attempts, {total_duration:.2f}s, policy: {policy_name})"
            )
            level = "info"
        else:
            log_context["final_error_type"] = type(final_error).__name__ if final_error else None
            log_context["final_error_message"] = str(final_error) if final_error else None
            message = (
                f"Retry session failed: {operation} "
                f"({total_attempts} attempts, {total_duration:.2f}s, policy: {policy_name})"
            )
            level = "error"
        
        self.logger._log_structured(
            level=level,
            message=message,
            event_type="retry_session_summary",
            correlation_id=correlation_id or get_correlation_id(),
            context=log_context,
            component="retry_manager"
        )
    
    def log_retry_statistics(
        self,
        statistics: Dict[str, Any],
        time_range: Optional[str] = None
    ) -> None:
        """
        Log retry statistics.
        
        Args:
            statistics: Retry statistics dictionary
            time_range: Time range for the statistics
        """
        context = {
            "time_range": time_range,
            "statistics": statistics
        }
        
        self.logger.info(
            f"Retry Statistics: {statistics.get('total_sessions', 0)} sessions, "
            f"{statistics.get('success_rate', 0):.1f}% success rate",
            event_type="retry_statistics",
            correlation_id=get_correlation_id(),
            context=context,
            component="retry_manager"
        )
    
    def create_retry_report(
        self,
        sessions: List[Dict[str, Any]],
        report_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a comprehensive retry report.
        
        Args:
            sessions: List of retry session data
            report_context: Additional context for the report
            
        Returns:
            Comprehensive retry report
        """
        if not sessions:
            return {
                "report_timestamp": datetime.utcnow().isoformat(),
                "total_sessions": 0,
                "successful_sessions": 0,
                "failed_sessions": 0,
                "success_rate": 0.0,
                "average_attempts": 0.0,
                "average_duration": 0.0,
                "context": report_context or {}
            }
        
        # Calculate statistics
        total_sessions = len(sessions)
        successful_sessions = sum(1 for s in sessions if s.get("success", False))
        failed_sessions = total_sessions - successful_sessions
        
        total_attempts = sum(s.get("total_attempts", 0) for s in sessions)
        total_duration = sum(s.get("total_duration", 0.0) for s in sessions)
        
        # Calculate averages
        average_attempts = total_attempts / total_sessions if total_sessions > 0 else 0
        average_duration = total_duration / total_sessions if total_sessions > 0 else 0
        
        # Calculate success rate
        success_rate = (successful_sessions / total_sessions) * 100 if total_sessions > 0 else 0
        
        report = {
            "report_timestamp": datetime.utcnow().isoformat(),
            "total_sessions": total_sessions,
            "successful_sessions": successful_sessions,
            "failed_sessions": failed_sessions,
            "success_rate": success_rate,
            "total_attempts": total_attempts,
            "average_attempts": average_attempts,
            "total_duration": total_duration,
            "average_duration": average_duration,
            "context": report_context or {},
            "session_details": sessions
        }
        
        # Log the report
        self.log_retry_statistics(
            {
                "total_sessions": total_sessions,
                "successful_sessions": successful_sessions,
                "failed_sessions": failed_sessions,
                "success_rate": success_rate,
                "average_attempts": average_attempts,
                "average_duration": average_duration
            },
            "retry_report"
        )
        
        return report


# Global retry logger instance
_retry_logger = RetryLogger()


def get_retry_logger() -> RetryLogger:
    """Get the global retry logger instance."""
    return _retry_logger


def log_retry_attempt(
    operation: str,
    attempt: int,
    max_attempts: int,
    delay: float,
    policy_id: str,
    policy_name: str,
    backoff_type: BackoffType,
    jitter_type: JitterType,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Log a retry attempt using the global retry logger."""
    _retry_logger.log_retry_attempt(
        operation, attempt, max_attempts, delay, policy_id, policy_name,
        backoff_type, jitter_type, correlation_id, context
    )


def log_retry_success(
    operation: str,
    attempt: int,
    total_attempts: int,
    total_duration: float,
    policy_id: str,
    policy_name: str,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Log successful retry using the global retry logger."""
    _retry_logger.log_retry_success(
        operation, attempt, total_attempts, total_duration,
        policy_id, policy_name, correlation_id, context
    )


def log_max_retries_exceeded(
    operation: str,
    max_attempts: int,
    total_duration: float,
    last_error: Exception,
    policy_id: str,
    policy_name: str,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Log maximum retries exceeded using the global retry logger."""
    _retry_logger.log_max_retries_exceeded(
        operation, max_attempts, total_duration, last_error,
        policy_id, policy_name, correlation_id, context
    )
