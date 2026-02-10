"""
Structured Logging for Selector Telemetry Reporting

This module provides structured logging capabilities for the reporting system,
including correlation tracking, performance monitoring, and audit trails.
"""

import asyncio
import logging
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import threading
from contextlib import contextmanager
from pathlib import Path

from ..models.selector_models import SeverityLevel


class LogLevel(Enum):
    """Log levels for structured logging"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    level: LogLevel
    message: str
    correlation_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OperationMetrics:
    """Operation performance metrics"""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TelemetryReportingLogger:
    """
    Structured logging system for telemetry reporting
    
    This class provides comprehensive logging capabilities:
    - Structured log entries with correlation IDs
    - Performance monitoring and timing
    - Operation tracking and metrics
    - Error logging with stack traces
    - Audit trail functionality
    - Thread-safe logging
    """
    
    def __init__(
        self,
        name: str = "telemetry_reporting",
        log_level: LogLevel = LogLevel.INFO,
        enable_file_logging: bool = True,
        log_file_path: Optional[str] = None,
        enable_console_logging: bool = True,
        correlation_id_header: str = "X-Correlation-ID"
    ):
        """Initialize the telemetry reporting logger"""
        self.name = name
        self.log_level = log_level
        self.enable_file_logging = enable_file_logging
        self.enable_console_logging = enable_console_logging
        self.correlation_id_header = correlation_id_header
        
        # Initialize Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.value))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Setup file logging
        if enable_file_logging:
            log_path = Path(log_file_path or f"logs/{name}.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # Setup console logging
        if enable_console_logging:
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # Thread-local storage for correlation IDs
        self._thread_local = threading.local()
        
        # Operation metrics storage
        self._operation_metrics = {}
        self._operation_lock = threading.Lock()
        
        # Log statistics
        self._stats = {
            "total_logs": 0,
            "logs_by_level": {},
            "operations_tracked": 0,
            "errors_logged": 0
        }
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for current thread"""
        self._thread_local.correlation_id = correlation_id
    
    def get_correlation_id(self) -> Optional[str]:
        """Get correlation ID for current thread"""
        return getattr(self._thread_local, 'correlation_id', None)
    
    def clear_correlation_id(self) -> None:
        """Clear correlation ID for current thread"""
        self._thread_local.correlation_id = None
    
    @contextmanager
    def correlation_context(self, correlation_id: str):
        """Context manager for correlation ID"""
        old_correlation_id = self.get_correlation_id()
        self.set_correlation_id(correlation_id)
        try:
            yield
        finally:
            if old_correlation_id:
                self.set_correlation_id(old_correlation_id)
            else:
                self.clear_correlation_id()
    
    def debug(self, message: str, **context) -> None:
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, **context)
    
    def info(self, message: str, **context) -> None:
        """Log info message"""
        self._log(LogLevel.INFO, message, **context)
    
    def warning(self, message: str, **context) -> None:
        """Log warning message"""
        self._log(LogLevel.WARNING, message, **context)
    
    def error(self, message: str, error: Optional[Exception] = None, **context) -> None:
        """Log error message"""
        error_info = None
        stack_trace = None
        
        if error:
            error_info = f"{type(error).__name__}: {str(error)}"
            stack_trace = traceback.format_exc()
        
        self._log(LogLevel.ERROR, message, error=error_info, stack_trace=stack_trace, **context)
    
    def critical(self, message: str, error: Optional[Exception] = None, **context) -> None:
        """Log critical message"""
        error_info = None
        stack_trace = None
        
        if error:
            error_info = f"{type(error).__name__}: {str(error)}"
            stack_trace = traceback.format_exc()
        
        self._log(LogLevel.CRITICAL, message, error=error_info, stack_trace=stack_trace, **context)
    
    def log_operation_start(self, operation_name: str, **metadata) -> str:
        """Log the start of an operation"""
        operation_id = str(uuid.uuid4())
        
        metrics = OperationMetrics(
            operation_name=operation_name,
            start_time=datetime.now(),
            metadata=metadata
        )
        
        with self._operation_lock:
            self._operation_metrics[operation_id] = metrics
        
        self.info(
            f"Operation started: {operation_name}",
            operation=operation_name,
            operation_id=operation_id,
            **metadata
        )
        
        return operation_id
    
    def log_operation_end(
        self,
        operation_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        **metadata
    ) -> None:
        """Log the end of an operation"""
        with self._operation_lock:
            metrics = self._operation_metrics.get(operation_id)
            if not metrics:
                self.warning(f"Operation metrics not found for ID: {operation_id}")
                return
            
            end_time = datetime.now()
            duration_ms = (end_time - metrics.start_time).total_seconds() * 1000
            
            metrics.end_time = end_time
            metrics.duration_ms = duration_ms
            metrics.success = success
            metrics.error_message = error_message
            
            if metadata:
                if metrics.metadata:
                    metrics.metadata.update(metadata)
                else:
                    metrics.metadata = metadata
        
        log_level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Operation {'completed' if success else 'failed'}: {metrics.operation_name}"
        
        self._log(
            log_level,
            message,
            operation=metrics.operation_name,
            operation_id=operation_id,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            **(metrics.metadata or {})
        )
    
    @contextmanager
    def operation_timer(self, operation_name: str, **metadata):
        """Context manager for timing operations"""
        operation_id = self.log_operation_start(operation_name, **metadata)
        
        try:
            yield operation_id
            self.log_operation_end(operation_id, success=True)
        except Exception as e:
            self.log_operation_end(operation_id, success=False, error_message=str(e))
            raise
    
    def log_with_timing(
        self,
        level: LogLevel,
        message: str,
        operation_name: str,
        **context
    ):
        """Log message with operation timing"""
        with self.operation_timer(operation_name, **context):
            self._log(level, message, **context)
    
    def log_report_generation(
        self,
        report_type: str,
        report_id: str,
        duration_ms: float,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """Log report generation event"""
        log_level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Report generation {'completed' if success else 'failed'}: {report_type}"
        
        self._log(
            log_level,
            message,
            operation="report_generation",
            report_type=report_type,
            report_id=report_id,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message
        )
    
    def log_data_processing(
        self,
        processing_type: str,
        records_processed: int,
        duration_ms: float,
        success: bool = True
    ) -> None:
        """Log data processing event"""
        log_level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Data processing {'completed' if success else 'failed'}: {processing_type}"
        
        self._log(
            log_level,
            message,
            operation="data_processing",
            processing_type=processing_type,
            records_processed=records_processed,
            duration_ms=duration_ms,
            success=success
        )
    
    def log_quality_check(
        self,
        check_type: str,
        quality_score: float,
        threshold: float,
        passed: bool
    ) -> None:
        """Log quality check event"""
        log_level = LogLevel.INFO if passed else LogLevel.WARNING
        message = f"Quality check {'passed' if passed else 'failed'}: {check_type}"
        
        self._log(
            log_level,
            message,
            operation="quality_check",
            check_type=check_type,
            quality_score=quality_score,
            threshold=threshold,
            passed=passed
        )
    
    def log_alert_event(
        self,
        alert_type: str,
        severity: SeverityLevel,
        message: str,
        alert_id: Optional[str] = None
    ) -> None:
        """Log alert event"""
        self._log(
            LogLevel.WARNING if severity == SeverityLevel.WARNING else LogLevel.ERROR,
            f"Alert triggered: {alert_type} - {message}",
            operation="alert",
            alert_type=alert_type,
            severity=severity.value,
            alert_id=alert_id,
            alert_message=message
        )
    
    def get_operation_metrics(self, operation_id: str) -> Optional[OperationMetrics]:
        """Get metrics for a specific operation"""
        with self._operation_lock:
            return self._operation_metrics.get(operation_id)
    
    def get_all_operation_metrics(self) -> Dict[str, OperationMetrics]:
        """Get all operation metrics"""
        with self._operation_lock:
            return self._operation_metrics.copy()
    
    def clear_operation_metrics(self, older_than_hours: int = 24) -> None:
        """Clear old operation metrics"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        with self._operation_lock:
            to_remove = [
                op_id for op_id, metrics in self._operation_metrics.items()
                if metrics.start_time < cutoff_time
            ]
            
            for op_id in to_remove:
                del self._operation_metrics[op_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics"""
        with self._operation_lock:
            return {
                **self._stats,
                "active_operations": len(self._operation_metrics),
                "correlation_id_active": self.get_correlation_id() is not None
            }
    
    def _log(self, level: LogLevel, message: str, **context) -> None:
        """Internal logging method"""
        # Check log level
        if not self._should_log(level):
            return
        
        # Create log entry
        log_entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            correlation_id=self.get_correlation_id(),
            **context
        )
        
        # Update statistics
        self._update_stats(level)
        
        # Log to Python logger
        log_message = self._format_log_message(log_entry)
        
        if level == LogLevel.DEBUG:
            self.logger.debug(log_message)
        elif level == LogLevel.INFO:
            self.logger.info(log_message)
        elif level == LogLevel.WARNING:
            self.logger.warning(log_message)
        elif level == LogLevel.ERROR:
            self.logger.error(log_message)
        elif level == LogLevel.CRITICAL:
            self.logger.critical(log_message)
    
    def _should_log(self, level: LogLevel) -> bool:
        """Check if message should be logged based on level"""
        level_order = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4
        }
        
        return level_order[level] >= level_order[self.log_level]
    
    def _format_log_message(self, log_entry: LogEntry) -> str:
        """Format log message for output"""
        # Create structured log data
        log_data = asdict(log_entry)
        
        # Convert datetime to string for JSON serialization
        log_data['timestamp'] = log_entry.timestamp.isoformat()
        log_data['level'] = log_entry.level.value
        
        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        # Return formatted message
        return json.dumps(log_data, default=str)
    
    def _update_stats(self, level: LogLevel) -> None:
        """Update logging statistics"""
        self._stats["total_logs"] += 1
        
        level_name = level.value
        self._stats["logs_by_level"][level_name] = (
            self._stats["logs_by_level"].get(level_name, 0) + 1
        )
        
        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            self._stats["errors_logged"] += 1


# Global logger instance
_telemetry_logger = None


def get_telemetry_logger() -> TelemetryReportingLogger:
    """Get the global telemetry logger instance"""
    global _telemetry_logger
    if _telemetry_logger is None:
        _telemetry_logger = TelemetryReportingLogger()
    return _telemetry_logger


def setup_telemetry_logging(
    name: str = "telemetry_reporting",
    log_level: LogLevel = LogLevel.INFO,
    enable_file_logging: bool = True,
    log_file_path: Optional[str] = None,
    enable_console_logging: bool = True
) -> TelemetryReportingLogger:
    """Setup and return telemetry logger"""
    global _telemetry_logger
    _telemetry_logger = TelemetryReportingLogger(
        name=name,
        log_level=log_level,
        enable_file_logging=enable_file_logging,
        log_file_path=log_file_path,
        enable_console_logging=enable_console_logging
    )
    return _telemetry_logger
