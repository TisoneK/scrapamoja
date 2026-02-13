"""
Structured Logging for Telemetry Data Management

This module provides structured logging capabilities for the storage system,
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
class StorageLogEntry:
    """Structured storage log entry"""
    timestamp: datetime
    level: LogLevel
    message: str
    correlation_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    storage_path: Optional[str] = None
    file_count: Optional[int] = None
    size_mb: Optional[float] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StorageOperationMetrics:
    """Storage operation performance metrics"""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: Optional[bool] = None
    files_processed: Optional[int] = None
    bytes_processed: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StorageTelemetryLogger:
    """
    Structured logging system for telemetry data management
    
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
        name: str = "telemetry_storage",
        log_level: LogLevel = LogLevel.INFO,
        enable_file_logging: bool = True,
        log_file_path: Optional[str] = None,
        enable_console_logging: bool = True,
        correlation_id_header: str = "X-Correlation-ID"
    ):
        """Initialize the storage telemetry logger"""
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
    
    def log_storage_operation_start(self, operation_name: str, storage_path: str, **metadata) -> str:
        """Log the start of a storage operation"""
        operation_id = str(uuid.uuid4())
        
        metrics = StorageOperationMetrics(
            operation_name=operation_name,
            start_time=datetime.now(),
            metadata={"storage_path": storage_path, **metadata}
        )
        
        with self._operation_lock:
            self._operation_metrics[operation_id] = metrics
        
        self.info(
            f"Storage operation started: {operation_name}",
            operation=operation_name,
            storage_path=storage_path,
            operation_id=operation_id,
            **metadata
        )
        
        return operation_id
    
    def log_storage_operation_end(
        self,
        operation_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        **metadata
    ) -> None:
        """Log the end of a storage operation"""
        with self._operation_lock:
            metrics = self._operation_metrics.get(operation_id)
            if not metrics:
                self.warning(f"Storage operation metrics not found for ID: {operation_id}")
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
        message = f"Storage operation {'completed' if success else 'failed'}: {metrics.operation_name}"
        
        self._log(
            log_level,
            message,
            operation=metrics.operation_name,
            operation_id=operation_id,
            storage_path=metrics.metadata.get("storage_path") if metrics.metadata else None,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            **(metrics.metadata or {})
        )
    
    @contextmanager
    def storage_operation_timer(self, operation_name: str, storage_path: str, **metadata):
        """Context manager for timing storage operations"""
        operation_id = self.log_storage_operation_start(operation_name, storage_path, **metadata)
        
        try:
            yield operation_id
            self.log_storage_operation_end(operation_id, success=True)
        except Exception as e:
            self.log_storage_operation_end(operation_id, success=False, error_message=str(e))
            raise
    
    def log_with_timing(
        self,
        level: LogLevel,
        message: str,
        operation_name: str,
        storage_path: str,
        **context
    ):
        """Log message with operation timing"""
        with self.storage_operation_timer(operation_name, storage_path, **context):
            self._log(level, message, **context)
    
    def log_retention_operation(
        self,
        operation_type: str,
        records_processed: int,
        duration_ms: float,
        success: bool = True
    ) -> None:
        """Log retention operation event"""
        log_level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Retention operation {'completed' if success else 'failed'}: {operation_type}"
        
        self._log(
            log_level,
            message,
            operation="retention",
            operation_type=operation_type,
            records_processed=records_processed,
            duration_ms=duration_ms,
            success=success
        )
    
    def log_backup_operation(
        self,
        backup_type: str,
        backup_path: str,
        file_count: int,
        size_mb: float,
        duration_ms: float,
        success: bool = True
    ) -> None:
        """Log backup operation event"""
        log_level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Backup operation {'completed' if success else 'failed'}: {backup_type}"
        
        self._log(
            log_level,
            message,
            operation="backup",
            backup_type=backup_type,
            backup_path=backup_path,
            file_count=file_count,
            size_mb=size_mb,
            duration_ms=duration_ms,
            success=success
        )
    
    def log_archival_operation(
        self,
        archival_type: str,
        source_path: str,
        archive_path: str,
        compression_ratio: float,
        duration_ms: float,
        success: bool = True
    ) -> None:
        """Log archival operation event"""
        log_level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Archival operation {'completed' if success else 'failed'}: {archival_type}"
        
        self._log(
            log_level,
            message,
            operation="archival",
            archival_type=archival_type,
            source_path=source_path,
            archive_path=archive_path,
            compression_ratio=compression_ratio,
            duration_ms=duration_ms,
            success=success
        )
    
    def log_cleanup_operation(
        self,
        cleanup_type: str,
        files_deleted: int,
        space_freed_mb: float,
        duration_ms: float,
        success: bool = True
    ) -> None:
        """Log cleanup operation event"""
        log_level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Cleanup operation {'completed' if success else 'failed'}: {cleanup_type}"
        
        self._log(
            log_level,
            message,
            operation="cleanup",
            cleanup_type=cleanup_type,
            files_deleted=files_deleted,
            space_freed_mb=space_freed_mb,
            duration_ms=duration_ms,
            success=success
        )
    
    def log_integrity_check(
        self,
        check_type: str,
        target_path: str,
        status: str,
        duration_ms: float,
        issues_found: int = 0
    ) -> None:
        """Log integrity check event"""
        log_level = LogLevel.INFO if status == "valid" else LogLevel.WARNING
        message = f"Integrity check {status}: {check_type}"
        
        self._log(
            log_level,
            message,
            operation="integrity_check",
            check_type=check_type,
            target_path=target_path,
            status=status,
            duration_ms=duration_ms,
            issues_found=issues_found
        )
    
    def get_operation_metrics(self, operation_id: str) -> Optional[StorageOperationMetrics]:
        """Get metrics for a specific operation"""
        with self._operation_lock:
            return self._operation_metrics.get(operation_id)
    
    def get_all_operation_metrics(self) -> Dict[str, StorageOperationMetrics]:
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
        """Get storage logging statistics"""
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
        log_entry = StorageLogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            correlation_id=self.get_correlation_id(),
            operation_id=context.get('operation_id'),
            **{k: v for k, v in context.items() if k not in ['operation_id']}
        )
        
        self._log_to_python_logger(level, log_entry)
    
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
    
    def _log_to_python_logger(self, level: LogLevel, log_entry: StorageLogEntry) -> None:
        """Log entry to Python's standard logging system"""
        # Update statistics
        self._update_stats(level)
        
        # Create structured log data for extra fields
        log_data = asdict(log_entry)
        
        # Convert datetime to string for JSON serialization
        log_data['timestamp'] = log_entry.timestamp.isoformat()
        log_data['level'] = log_entry.level.value
        
        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        # Use message + extra pattern instead of JSON string
        message = log_data.pop('message', 'telemetry_log_event')
        
        if level == LogLevel.DEBUG:
            self.logger.debug(message, extra=log_data)
        elif level == LogLevel.INFO:
            self.logger.info(message, extra=log_data)
        elif level == LogLevel.WARNING:
            self.logger.warning(message, extra=log_data)
        elif level == LogLevel.ERROR:
            self.logger.error(message, extra=log_data)
        elif level == LogLevel.CRITICAL:
            self.logger.critical(message, extra=log_data)
    
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
_storage_logger = None


def get_storage_logger() -> StorageTelemetryLogger:
    """Get the global storage logger instance"""
    global _storage_logger
    if _storage_logger is None:
        _storage_logger = StorageTelemetryLogger()
    return _storage_logger


def setup_storage_logging(
    name: str = "telemetry_storage",
    log_level: LogLevel = LogLevel.INFO,
    enable_file_logging: bool = True,
    log_file_path: Optional[str] = None,
    enable_console_logging: bool = True
) -> StorageTelemetryLogger:
    """Setup and return storage logger"""
    global _storage_logger
    _storage_logger = StorageTelemetryLogger(
        name=name,
        log_level=log_level,
        enable_file_logging=enable_file_logging,
        log_file_path=log_file_path,
        enable_console_logging=enable_console_logging
    )
    return _storage_logger
