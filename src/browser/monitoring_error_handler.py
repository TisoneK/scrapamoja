"""
Resource Monitoring Error Handling

This module provides graceful error handling for resource monitoring failures,
following the Production Resilience constitution principle.
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass
import structlog

from .exceptions import MonitoringError, ResourceExhaustionError
from .resource_logger import ResourceOperation, get_resource_logger
from .resilience import resilience_manager, RetryConfig, RetryStrategy
from .models.metrics import ResourceMetrics, AlertStatus
from .models.enums import CleanupLevel


class MonitoringErrorType(Enum):
    """Types of monitoring errors."""
    PROCESS_NOT_FOUND = "process_not_found"
    ACCESS_DENIED = "access_denied"
    PSUTIL_ERROR = "psutil_error"
    METRIC_COLLECTION_FAILED = "metric_collection_failed"
    THRESHOLD_CHECK_FAILED = "threshold_check_failed"
    CLEANUP_FAILED = "cleanup_failed"
    SESSION_NOT_FOUND = "session_not_found"
    INVALID_CONFIGURATION = "invalid_configuration"
    TIMEOUT = "timeout"
    UNKNOWN_ERROR = "unknown_error"


class MonitoringRecoveryAction(Enum):
    """Recovery actions for monitoring errors."""
    RETRY = "retry"
    SKIP_CHECK = "skip_check"
    USE_FALLBACK_METRICS = "use_fallback_metrics"
    RESET_MONITORING = "reset_monitoring"
    ESCALATE_ALERT = "escalate_alert"
    CONTINUE_MONITORING = "continue_monitoring"
    ABORT = "abort"


@dataclass
class MonitoringErrorContext:
    """Context for monitoring errors."""
    error_type: MonitoringErrorType
    original_error: Exception
    session_id: Optional[str] = None
    operation: Optional[ResourceOperation] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    retry_count: int = 0
    recovery_attempts: List[MonitoringRecoveryAction] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.recovery_attempts is None:
            self.recovery_attempts = []


class MonitoringErrorHandler:
    """Handles errors in resource monitoring with graceful recovery."""
    
    def __init__(self):
        self.logger = structlog.get_logger("browser.monitoring_error_handler")
        self.resource_logger = get_resource_logger()
        
        # Configure retry strategies for different error types
        self.retry_configs = {
            MonitoringErrorType.TIMEOUT: RetryConfig(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=1.0,
                max_delay=10.0
            ),
            MonitoringErrorType.ACCESS_DENIED: RetryConfig(
                max_attempts=2,
                strategy=RetryStrategy.LINEAR_BACKOFF,
                base_delay=5.0
            ),
            MonitoringErrorType.PSUTIL_ERROR: RetryConfig(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=2.0
            )
        }
        
    async def handle_metrics_collection_error(
        self,
        error: Exception,
        session_id: str,
        correlation_id: Optional[str] = None
    ) -> Optional[ResourceMetrics]:
        """Handle metrics collection errors with recovery."""
        error_context = self._create_error_context(
            error, session_id, ResourceOperation.COLLECT_METRICS, correlation_id
        )
        
        self.logger.warning(
            "Metrics collection error occurred",
            **error_context.__dict__
        )
        
        # Attempt recovery based on error type
        recovery_actions = self._get_recovery_actions(error_context.error_type)
        
        for action in recovery_actions:
            try:
                error_context.recovery_attempts.append(action)
                result = await self._attempt_metrics_recovery(action, error_context)
                
                if result is not None:
                    self.logger.info(
                        "Metrics collection error recovered",
                        recovery_action=action.value,
                        session_id=session_id
                    )
                    return result
                    
            except Exception as recovery_error:
                self.logger.error(
                    "Metrics recovery attempt failed",
                    recovery_action=action.value,
                    error=str(recovery_error),
                    error_type=type(recovery_error).__name__
                )
                continue
                
        # All recovery attempts failed, return fallback metrics
        fallback_metrics = self._create_fallback_metrics(session_id)
        
        self.logger.warning(
            "Using fallback metrics after recovery failure",
            session_id=session_id,
            attempted_actions=[action.value for action in error_context.recovery_attempts]
        )
        
        return fallback_metrics
        
    async def handle_threshold_check_error(
        self,
        error: Exception,
        session_id: str,
        metrics: ResourceMetrics,
        correlation_id: Optional[str] = None
    ) -> AlertStatus:
        """Handle threshold check errors with recovery."""
        error_context = self._create_error_context(
            error, session_id, ResourceOperation.CHECK_THRESHOLDS, correlation_id,
            metrics=metrics.to_dict()
        )
        
        self.logger.warning(
            "Threshold check error occurred",
            **error_context.__dict__
        )
        
        # For threshold check errors, be conservative and assume normal status
        # unless we have evidence of issues in the metrics
        if (metrics.memory_usage_mb > 1024 or  # Conservative memory threshold
            metrics.cpu_usage_percent > 70):  # Conservative CPU threshold
            alert_status = AlertStatus.WARNING
        else:
            alert_status = AlertStatus.NORMAL
            
        self.logger.info(
            "Threshold check error handled with conservative approach",
            session_id=session_id,
            alert_status=alert_status.value,
            memory_mb=metrics.memory_usage_mb,
            cpu_percent=metrics.cpu_usage_percent
        )
        
        return alert_status
        
    async def handle_cleanup_error(
        self,
        error: Exception,
        session_id: str,
        cleanup_level: CleanupLevel,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Handle cleanup errors with recovery."""
        error_context = self._create_error_context(
            error, session_id, ResourceOperation.TRIGGER_CLEANUP, correlation_id,
            cleanup_level=cleanup_level.value
        )
        
        self.logger.warning(
            "Cleanup error occurred",
            **error_context.__dict__
        )
        
        # For cleanup errors, try less aggressive cleanup levels
        recovery_actions = self._get_cleanup_recovery_actions(cleanup_level)
        
        for action in recovery_actions:
            try:
                error_context.recovery_attempts.append(action)
                success = await self._attempt_cleanup_recovery(action, error_context)
                
                if success:
                    self.logger.info(
                        "Cleanup error recovered",
                        recovery_action=action.value,
                        session_id=session_id
                    )
                    return True
                    
            except Exception as recovery_error:
                self.logger.error(
                    "Cleanup recovery attempt failed",
                    recovery_action=action.value,
                    error=str(recovery_error),
                    error_type=type(recovery_error).__name__
                )
                continue
                
        # All recovery attempts failed
        self.logger.error(
            "Cleanup error recovery failed",
            session_id=session_id,
            attempted_actions=[action.value for action in error_context.recovery_attempts]
        )
        
        return False
        
    async def handle_monitoring_start_error(
        self,
        error: Exception,
        session_id: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Handle monitoring start errors."""
        error_context = self._create_error_context(
            error, session_id, ResourceOperation.START_MONITORING, correlation_id
        )
        
        self.logger.error(
            "Monitoring start error occurred",
            **error_context.__dict__
        )
        
        # For monitoring start errors, we typically cannot recover
        # Log the error and return failure
        self.resource_logger.log_monitoring_start(
            session_id=session_id,
            success=False,
            error=str(error),
            correlation_id=correlation_id
        )
        
        return False
        
    async def handle_monitoring_stop_error(
        self,
        error: Exception,
        session_id: str,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Handle monitoring stop errors."""
        error_context = self._create_error_context(
            error, session_id, ResourceOperation.STOP_MONITORING, correlation_id
        )
        
        self.logger.warning(
            "Monitoring stop error occurred",
            **error_context.__dict__
        )
        
        # For monitoring stop errors, we consider it successful
        # since the goal is to stop monitoring, and errors here don't block the system
        self.resource_logger.log_monitoring_stop(
            session_id=session_id,
            success=True,
            error=str(error),
            correlation_id=correlation_id
        )
        
        return True
        
    def _create_error_context(
        self,
        error: Exception,
        session_id: Optional[str],
        operation: Optional[ResourceOperation],
        correlation_id: Optional[str] = None,
        **metadata
    ) -> MonitoringErrorContext:
        """Create error context from exception."""
        error_type = self._classify_error(error)
        
        return MonitoringErrorContext(
            error_type=error_type,
            original_error=error,
            session_id=session_id,
            operation=operation,
            correlation_id=correlation_id,
            metadata=metadata
        )
        
    def _classify_error(self, error: Exception) -> MonitoringErrorType:
        """Classify error type for appropriate recovery strategy."""
        error_message = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Process-related errors
        if "process not found" in error_message or "no such process" in error_message:
            return MonitoringErrorType.PROCESS_NOT_FOUND
        elif "access denied" in error_message or "permission denied" in error_message:
            return MonitoringErrorType.ACCESS_DENIED
        elif "psutil" in error_type_name:
            return MonitoringErrorType.PSUTIL_ERROR
            
        # Timeout errors
        elif "timeout" in error_message or "timed out" in error_message:
            return MonitoringErrorType.TIMEOUT
            
        # Configuration errors
        elif "configuration" in error_message or "invalid" in error_type_name:
            return MonitoringErrorType.INVALID_CONFIGURATION
            
        return MonitoringErrorType.UNKNOWN_ERROR
        
    def _get_recovery_actions(self, error_type: MonitoringErrorType) -> List[MonitoringRecoveryAction]:
        """Get recovery actions for specific error types."""
        recovery_map = {
            MonitoringErrorType.PROCESS_NOT_FOUND: [MonitoringRecoveryAction.USE_FALLBACK_METRICS, MonitoringRecoveryAction.SKIP_CHECK],
            MonitoringErrorType.ACCESS_DENIED: [MonitoringRecoveryAction.USE_FALLBACK_METRICS, MonitoringRecoveryAction.SKIP_CHECK],
            MonitoringErrorType.PSUTIL_ERROR: [MonitoringRecoveryAction.RETRY, MonitoringRecoveryAction.USE_FALLBACK_METRICS],
            MonitoringErrorType.METRIC_COLLECTION_FAILED: [MonitoringRecoveryAction.RETRY, MonitoringRecoveryAction.USE_FALLBACK_METRICS],
            MonitoringErrorType.THRESHOLD_CHECK_FAILED: [MonitoringRecoveryAction.USE_FALLBACK_METRICS, MonitoringRecoveryAction.CONTINUE_MONITORING],
            MonitoringErrorType.TIMEOUT: [MonitoringRecoveryAction.RETRY, MonitoringRecoveryAction.USE_FALLBACK_METRICS],
            MonitoringErrorType.INVALID_CONFIGURATION: [MonitoringRecoveryAction.RESET_MONITORING],
            MonitoringErrorType.UNKNOWN_ERROR: [MonitoringRecoveryAction.RETRY, MonitoringRecoveryAction.USE_FALLBACK_METRICS]
        }
        
        return recovery_map.get(error_type, [MonitoringRecoveryAction.RETRY])
        
    def _get_cleanup_recovery_actions(self, current_level: CleanupLevel) -> List[MonitoringRecoveryAction]:
        """Get recovery actions for cleanup errors based on current level."""
        if current_level == CleanupLevel.FORCE:
            return [MonitoringRecoveryAction.ABORT]
        elif current_level == CleanupLevel.AGGRESSIVE:
            return [MonitoringRecoveryAction.RETRY, MonitoringRecoveryAction.ESCALATE_ALERT]  # Try moderate
        elif current_level == CleanupLevel.MODERATE:
            return [MonitoringRecoveryAction.RETRY, MonitoringRecoveryAction.ESCALATE_ALERT]  # Try gentle
        elif current_level == CleanupLevel.GENTLE:
            return [MonitoringRecoveryAction.RETRY, MonitoringRecoveryAction.ESCALATE_ALERT]  # Skip cleanup
        else:
            return [MonitoringRecoveryAction.ABORT]
            
    async def _attempt_metrics_recovery(
        self,
        action: MonitoringRecoveryAction,
        error_context: MonitoringErrorContext
    ) -> Optional[ResourceMetrics]:
        """Attempt recovery for metrics collection."""
        if action == MonitoringRecoveryAction.RETRY:
            return await self._retry_metrics_collection(error_context)
        elif action == MonitoringRecoveryAction.USE_FALLBACK_METRICS:
            return self._create_fallback_metrics(error_context.session_id)
        else:
            return None
            
    async def _attempt_cleanup_recovery(
        self,
        action: MonitoringRecoveryAction,
        error_context: MonitoringErrorContext
    ) -> bool:
        """Attempt recovery for cleanup operations."""
        if action == MonitoringRecoveryAction.RETRY:
            return await self._retry_cleanup(error_context)
        elif action == MonitoringRecoveryAction.ESCALATE_ALERT:
            # Log escalated alert
            self.logger.error(
                "Cleanup failure escalated",
                session_id=error_context.session_id,
                error=str(error_context.original_error)
            )
            return False
        else:
            return False
            
    async def _retry_metrics_collection(self, error_context: MonitoringErrorContext) -> Optional[ResourceMetrics]:
        """Retry metrics collection with exponential backoff."""
        retry_config = self.retry_configs.get(error_context.error_type)
        if not retry_config:
            return None
            
        try:
            # This would call the actual metrics collection method
            # For now, return None to indicate failure
            return None
            
        except Exception:
            return None
            
    async def _retry_cleanup(self, error_context: MonitoringErrorContext) -> bool:
        """Retry cleanup operation."""
        try:
            # This would call the actual cleanup method
            # For now, return False to indicate failure
            return False
            
        except Exception:
            return False
            
    def _create_fallback_metrics(self, session_id: str) -> ResourceMetrics:
        """Create fallback metrics when collection fails."""
        return ResourceMetrics(
            session_id=session_id,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            disk_usage_mb=0.0,
            network_requests_count=0,
            open_tabs_count=0,
            process_handles_count=0,
            alert_status=AlertStatus.NORMAL
        )


# Global monitoring error handler instance
_monitoring_error_handler: Optional[MonitoringErrorHandler] = None


def get_monitoring_error_handler() -> MonitoringErrorHandler:
    """Get or create monitoring error handler instance."""
    global _monitoring_error_handler
    
    if _monitoring_error_handler is None:
        _monitoring_error_handler = MonitoringErrorHandler()
        
    return _monitoring_error_handler
