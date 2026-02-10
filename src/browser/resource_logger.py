"""
Resource Monitoring Logging

This module provides structured logging with correlation IDs for resource monitoring operations.
"""

import uuid
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import structlog


class ResourceOperation(Enum):
    """Resource monitoring operation types."""
    START_MONITORING = "start_monitoring"
    STOP_MONITORING = "stop_monitoring"
    COLLECT_METRICS = "collect_metrics"
    CHECK_THRESHOLDS = "check_thresholds"
    TRIGGER_CLEANUP = "trigger_cleanup"
    SET_THRESHOLDS = "set_thresholds"
    ALERT_TRIGGERED = "alert_triggered"
    CLEANUP_COMPLETED = "cleanup_completed"


class AlertLevel(Enum):
    """Resource alert levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ResourceOperationContext:
    """Context for resource monitoring operations."""
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: ResourceOperation = ResourceOperation.COLLECT_METRICS
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    error_type: Optional[str] = None
    alert_level: Optional[AlertLevel] = None
    
    def complete(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark operation as completed."""
        self.completed_at = time.time()
        self.duration_ms = (self.completed_at - self.started_at) * 1000
        
        if not success:
            self.error = error
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "operation_id": self.operation_id,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "operation": self.operation.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "error": self.error,
            "error_type": self.error_type,
            "alert_level": self.alert_level.value if self.alert_level else None
        }


class ResourceMonitoringLogger:
    """Structured logger for resource monitoring operations."""
    
    def __init__(self, logger_name: str = "browser.resource_monitoring"):
        self.logger = structlog.get_logger(logger_name)
        self.active_operations: Dict[str, ResourceOperationContext] = {}
        
    def start_operation(
        self,
        operation: ResourceOperation,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **metadata
    ) -> ResourceOperationContext:
        """Start a new resource monitoring operation."""
        context = ResourceOperationContext(
            correlation_id=correlation_id,
            session_id=session_id,
            operation=operation,
            metadata=metadata
        )
        
        self.active_operations[context.operation_id] = context
        
        self.logger.info(
            "Resource operation started",
            **context.to_dict()
        )
        
        return context
        
    def complete_operation(
        self,
        operation_id: str,
        success: bool = True,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
        **final_metadata
    ) -> Optional[ResourceOperationContext]:
        """Complete an operation."""
        context = self.active_operations.get(operation_id)
        if context is None:
            self.logger.warning(
                "Operation not found for completion",
                operation_id=operation_id
            )
            return None
            
        context.complete(success, error)
        context.error_type = error_type
        context.metadata.update(final_metadata)
        
        log_level = "info" if success else "error"
        getattr(self.logger, log_level)(
            f"Resource operation {context.operation.value}",
            **context.to_dict()
        )
        
        # Remove from active operations
        del self.active_operations[operation_id]
        
        return context
        
    def log_monitoring_start(
        self,
        session_id: str,
        process_id: Optional[int] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log monitoring start operation."""
        context = self.start_operation(
            ResourceOperation.START_MONITORING,
            session_id=session_id,
            correlation_id=correlation_id,
            process_id=process_id
        )
        
        self.complete_operation(
            context.operation_id,
            success=True
        )
        
        return context.operation_id
        
    def log_monitoring_stop(
        self,
        session_id: str,
        success: bool,
        session_duration_seconds: Optional[float] = None,
        check_count: Optional[int] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log monitoring stop operation."""
        context = self.start_operation(
            ResourceOperation.STOP_MONITORING,
            session_id=session_id,
            correlation_id=correlation_id,
            session_duration_seconds=session_duration_seconds,
            check_count=check_count
        )
        
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="monitoring_error" if error else None
        )
        
    def log_metrics_collection(
        self,
        session_id: str,
        metrics: Dict[str, Any],
        success: bool,
        collection_time_ms: Optional[float] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log metrics collection operation."""
        context = self.start_operation(
            ResourceOperation.COLLECT_METRICS,
            session_id=session_id,
            correlation_id=correlation_id,
            metrics=metrics
        )
        
        final_metadata = {}
        if collection_time_ms is not None:
            final_metadata["collection_time_ms"] = collection_time_ms
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="collection_error" if error else None,
            **final_metadata
        )
        
    def log_threshold_check(
        self,
        session_id: str,
        alert_level: AlertLevel,
        metrics: Dict[str, Any],
        thresholds: Dict[str, Any],
        success: bool,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log threshold check operation."""
        context = self.start_operation(
            ResourceOperation.CHECK_THRESHOLDS,
            session_id=session_id,
            correlation_id=correlation_id,
            alert_level=alert_level,
            metrics=metrics,
            thresholds=thresholds
        )
        
        context.alert_level = alert_level
        
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="threshold_error" if error else None
        )
        
    def log_cleanup_trigger(
        self,
        session_id: str,
        cleanup_level: str,
        alert_level: AlertLevel,
        metrics: Dict[str, Any],
        success: bool,
        cleanup_time_ms: Optional[float] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log cleanup trigger operation."""
        context = self.start_operation(
            ResourceOperation.TRIGGER_CLEANUP,
            session_id=session_id,
            correlation_id=correlation_id,
            cleanup_level=cleanup_level,
            alert_level=alert_level,
            metrics=metrics
        )
        
        context.alert_level = alert_level
        
        final_metadata = {}
        if cleanup_time_ms is not None:
            final_metadata["cleanup_time_ms"] = cleanup_time_ms
            
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="cleanup_error" if error else None,
            **final_metadata
        )
        
    def log_threshold_update(
        self,
        old_thresholds: Dict[str, Any],
        new_thresholds: Dict[str, Any],
        success: bool,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log threshold update operation."""
        context = self.start_operation(
            ResourceOperation.SET_THRESHOLDS,
            correlation_id=correlation_id,
            old_thresholds=old_thresholds,
            new_thresholds=new_thresholds
        )
        
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="threshold_update_error" if error else None
        )
        
    def log_alert_triggered(
        self,
        session_id: str,
        alert_level: AlertLevel,
        alert_type: str,
        metrics: Dict[str, Any],
        thresholds: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> None:
        """Log alert triggered event."""
        context = self.start_operation(
            ResourceOperation.ALERT_TRIGGERED,
            session_id=session_id,
            correlation_id=correlation_id,
            alert_level=alert_level,
            alert_type=alert_type,
            metrics=metrics,
            thresholds=thresholds
        )
        
        context.alert_level = alert_level
        
        self.complete_operation(
            context.operation_id,
            success=True
        )
        
    def log_cleanup_completed(
        self,
        session_id: str,
        cleanup_level: str,
        success: bool,
        cleanup_results: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log cleanup completed event."""
        context = self.start_operation(
            ResourceOperation.CLEANUP_COMPLETED,
            session_id=session_id,
            correlation_id=correlation_id,
            cleanup_level=cleanup_level,
            cleanup_results=cleanup_results
        )
        
        self.complete_operation(
            context.operation_id,
            success=success,
            error=error,
            error_type="cleanup_completion_error" if error else None
        )
        
    def get_active_operations(self) -> List[ResourceOperationContext]:
        """Get all currently active operations."""
        return list(self.active_operations.values())
        
    def get_operation_stats(self) -> Dict[str, Any]:
        """Get statistics about operations."""
        return {
            "active_operations": len(self.active_operations),
            "active_operation_ids": list(self.active_operations.keys())
        }


# Global resource monitoring logger
resource_logger = ResourceMonitoringLogger()


def get_resource_logger() -> ResourceMonitoringLogger:
    """Get the global resource monitoring logger."""
    return resource_logger


def log_resource_operation(
    operation: ResourceOperation,
    success: bool,
    session_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    error: Optional[str] = None,
    **metadata
) -> None:
    """Convenience function to log resource operations."""
    if success:
        context = resource_logger.start_operation(
            operation,
            session_id=session_id,
            correlation_id=correlation_id,
            **metadata
        )
        resource_logger.complete_operation(context.operation_id, success=True)
    else:
        context = resource_logger.start_operation(
            operation,
            session_id=session_id,
            correlation_id=correlation_id,
            **metadata
        )
        resource_logger.complete_operation(
            context.operation_id,
            success=False,
            error=error
        )
