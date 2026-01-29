"""
Structured Logging with Correlation IDs

Specialized logging module for telemetry data collection with
correlation ID tracking, structured output, and performance monitoring.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import sys

from ..utils import get_thread_correlation_id, set_thread_correlation_id, clear_thread_correlation_id
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryCollectionError
from ..configuration.logging import get_logger


class LogLevel(Enum):
    """Log levels for telemetry logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Structured log entry with correlation ID."""
    timestamp: datetime
    level: LogLevel
    correlation_id: Optional[str]
    component: str
    operation: Optional[str]
    message: str
    context: Dict[str, Any]
    duration_ms: Optional[float] = None
    error_details: Optional[Dict[str, Any]] = None


class TelemetryLogger:
    """
    Structured logger for telemetry operations with correlation ID support.
    
    Provides comprehensive logging with correlation tracking, performance
    monitoring, and structured output for telemetry operations.
    """
    
    def __init__(self, config: TelemetryConfiguration, component_name: str):
        """
        Initialize telemetry logger.
        
        Args:
            config: Telemetry configuration
            component_name: Name of the component
        """
        self.config = config
        self.component_name = component_name
        self.logger = get_logger(f"telemetry.{component_name}")
        
        # Logging configuration
        self.log_level = config.get("log_level", "INFO")
        self.structured_logging = config.get("structured_logging", True)
        self.include_performance = config.get("include_performance_in_logs", True)
        
        # Log storage
        self._log_entries: List[LogEntry] = []
        self._log_lock = asyncio.Lock()
        self._max_entries = config.get("max_log_entries", 10000)
        
        # Performance tracking
        self._operation_timers: Dict[str, float] = {}
        self._performance_stats = {
            "total_logs": 0,
            "logs_by_level": {},
            "average_log_duration": 0.0,
            "slowest_operations": []
        }
    
    def debug(self, message: str, correlation_id: Optional[str] = None, **context) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, correlation_id, **context)
    
    def info(self, message: str, correlation_id: Optional[str] = None, **context) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, correlation_id, **context)
    
    def warning(self, message: str, correlation_id: Optional[str] = None, **context) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, correlation_id, **context)
    
    def error(self, message: str, correlation_id: Optional[str] = None, **context) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, message, correlation_id, **context)
    
    def critical(self, message: str, correlation_id: Optional[str] = None, **context) -> None:
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, correlation_id, **context)
    
    def event_collected(
        self,
        event_id: str,
        selector_name: str,
        operation_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **context
    ) -> None:
        """Log event collection."""
        message = f"Event collected: {event_id}"
        log_context = {
            "event_id": event_id,
            "selector_name": selector_name,
            "operation_type": operation_type,
            **context
        }
        self._log(LogLevel.INFO, message, correlation_id, "event_collection", **log_context)
    
    def event_stored(
        self,
        event_id: str,
        storage_type: str,
        correlation_id: Optional[str] = None,
        **context
    ) -> None:
        """Log event storage."""
        message = f"Event stored: {event_id}"
        log_context = {
            "event_id": event_id,
            "storage_type": storage_type,
            **context
        }
        self._log(LogLevel.INFO, message, correlation_id, "event_storage", **log_context)
    
    def buffer_overflow(
        self,
        max_size: int,
        current_size: int,
        correlation_id: Optional[str] = None,
        **context
    ) -> None:
        """Log buffer overflow."""
        message = f"Buffer overflow: {current_size}/{max_size}"
        log_context = {
            "max_size": max_size,
            "current_size": current_size,
            "overflow_percentage": (current_size / max_size) * 100,
            **context
        }
        self._log(LogLevel.WARNING, message, correlation_id, "buffer_management", **log_context)
    
    def storage_error(
        self,
        operation: str,
        error: str,
        event_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **context
    ) -> None:
        """Log storage error."""
        message = f"Storage error in {operation}: {error}"
        log_context = {
            "operation": operation,
            "error": error,
            "event_id": event_id,
            **context
        }
        self._log(LogLevel.ERROR, message, correlation_id, "storage", **log_context)
    
    def performance_warning(
        self,
        operation: str,
        duration_ms: float,
        threshold_ms: float,
        correlation_id: Optional[str] = None,
        **context
    ) -> None:
        """Log performance warning."""
        message = f"Slow operation: {operation} took {duration_ms:.2f}ms (threshold: {threshold_ms}ms)"
        log_context = {
            "operation": operation,
            "duration_ms": duration_ms,
            "threshold_ms": threshold_ms,
            "excess_ms": duration_ms - threshold_ms,
            **context
        }
        self._log(LogLevel.WARNING, message, correlation_id, "performance", **log_context)
    
    def start_operation_timer(self, operation_id: str) -> None:
        """Start timing an operation."""
        self._operation_timers[operation_id] = time.time()
    
    def end_operation_timer(
        self,
        operation_id: str,
        operation_name: str,
        correlation_id: Optional[str] = None,
        **context
    ) -> float:
        """End timing an operation and log duration."""
        start_time = self._operation_timers.pop(operation_id, time.time())
        duration_ms = (time.time() - start_time) * 1000
        
        message = f"Operation completed: {operation_name}"
        log_context = {
            "operation_name": operation_name,
            "operation_id": operation_id,
            "duration_ms": duration_ms,
            **context
        }
        
        self._log(LogLevel.DEBUG, message, correlation_id, "timing", **log_context)
        
        # Update performance statistics
        self._update_performance_stats(operation_name, duration_ms)
        
        return duration_ms
    
    def log_with_timing(
        self,
        level: LogLevel,
        message: str,
        operation_name: str,
        correlation_id: Optional[str] = None,
        **context
    ):
        """Context manager for logging with automatic timing."""
        return TimingLogContext(self, level, message, operation_name, correlation_id, **context)
    
    def create_operation_logger(
        self,
        operation_name: str,
        correlation_id: Optional[str] = None
    ) -> "OperationLogger":
        """Create an operation-specific logger."""
        return OperationLogger(self, operation_name, correlation_id)
    
    async def get_log_entries(
        self,
        level: Optional[LogLevel] = None,
        correlation_id: Optional[str] = None,
        component: Optional[str] = None,
        limit: Optional[int] = None,
        time_window: Optional[timedelta] = None
    ) -> List[LogEntry]:
        """
        Get log entries with filtering.
        
        Args:
            level: Optional log level filter
            correlation_id: Optional correlation ID filter
            component: Optional component filter
            limit: Optional limit on number of entries
            time_window: Optional time window for entries
            
        Returns:
            Filtered log entries
        """
        try:
            async with self._log_lock:
                entries = self._log_entries.copy()
            
            # Apply filters
            if level:
                entries = [entry for entry in entries if entry.level == level]
            
            if correlation_id:
                entries = [entry for entry in entries if entry.correlation_id == correlation_id]
            
            if component:
                entries = [entry for entry in entries if entry.component == component]
            
            if time_window:
                cutoff_time = datetime.utcnow() - time_window
                entries = [entry for entry in entries if entry.timestamp >= cutoff_time]
            
            # Sort by timestamp (newest first)
            entries.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit
            if limit:
                entries = entries[:limit]
            
            return entries
            
        except Exception as e:
            self.logger.error(f"Failed to get log entries: {e}")
            return []
    
    async def get_performance_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics for logging operations.
        
        Returns:
            Performance statistics
        """
        try:
            async with self._log_lock:
                stats = self._performance_stats.copy()
            
            # Calculate additional statistics
            if stats["total_logs"] > 0:
                stats["logs_per_second"] = stats["total_logs"] / (
                    (datetime.utcnow() - self._log_entries[0].timestamp).total_seconds()
                    if self._log_entries else 1
                )
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get performance statistics: {e}")
            return {}
    
    async def clear_log_entries(
        self,
        level: Optional[LogLevel] = None,
        correlation_id: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> int:
        """
        Clear log entries with filtering.
        
        Args:
            level: Optional log level filter
            correlation_id: Optional correlation ID filter
            time_window: Optional time window for entries to clear
            
        Returns:
            Number of entries cleared
        """
        try:
            async with self._log_lock:
                original_count = len(self._log_entries)
                
                # Apply filters for entries to keep
                if level or correlation_id or time_window:
                    entries_to_keep = []
                    
                    for entry in self._log_entries:
                        keep = True
                        
                        if level and entry.level == level:
                            keep = False
                        
                        if correlation_id and entry.correlation_id == correlation_id:
                            keep = False
                        
                        if time_window and entry.timestamp >= (datetime.utcnow() - time_window):
                            keep = False
                        
                        if keep:
                            entries_to_keep.append(entry)
                    
                    self._log_entries = entries_to_keep
                else:
                    self._log_entries.clear()
                
                cleared_count = original_count - len(self._log_entries)
                
                self.logger.info(f"Cleared {cleared_count} log entries")
                return cleared_count
                
        except Exception as e:
            self.logger.error(f"Failed to clear log entries: {e}")
            return 0
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        correlation_id: Optional[str] = None,
        operation: Optional[str] = None,
        **context
    ) -> None:
        """Internal logging method."""
        try:
            # Get correlation ID from thread local if not provided
            if not correlation_id:
                correlation_id = get_thread_correlation_id()
            
            # Create log entry
            entry = LogEntry(
                timestamp=datetime.utcnow(),
                level=level,
                correlation_id=correlation_id,
                component=self.component_name,
                operation=operation,
                message=message,
                context=context
            )
            
            # Add to storage
            asyncio.create_task(self._add_log_entry(entry))
            
            # Output to standard logger
            log_message = self._format_log_message(entry)
            
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
            
        except Exception as e:
            # Fallback logging to avoid infinite recursion
            self.logger.error(f"Failed to log message: {e}")
    
    async def _add_log_entry(self, entry: LogEntry) -> None:
        """Add log entry to storage."""
        try:
            async with self._log_lock:
                self._log_entries.append(entry)
                
                # Limit entries
                if len(self._log_entries) > self._max_entries:
                    self._log_entries = self._log_entries[-self._max_entries:]
                
                # Update statistics
                self._performance_stats["total_logs"] += 1
                
                level_name = entry.level.value
                if level_name not in self._performance_stats["logs_by_level"]:
                    self._performance_stats["logs_by_level"][level_name] = 0
                self._performance_stats["logs_by_level"][level_name] += 1
                
        except Exception as e:
            self.logger.error(f"Failed to add log entry: {e}")
    
    def _format_log_message(self, entry: LogEntry) -> str:
        """Format log message for output."""
        if self.structured_logging:
            # Structured JSON format
            log_data = {
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.value,
                "correlation_id": entry.correlation_id,
                "component": entry.component,
                "operation": entry.operation,
                "message": entry.message,
                "context": entry.context
            }
            
            if entry.duration_ms:
                log_data["duration_ms"] = entry.duration_ms
            
            if entry.error_details:
                log_data["error"] = entry.error_details
            
            return json.dumps(log_data, default=str)
        else:
            # Traditional format
            parts = [
                entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                entry.level.value,
                entry.component
            ]
            
            if entry.correlation_id:
                parts.append(f"[{entry.correlation_id}]")
            
            if entry.operation:
                parts.append(f"({entry.operation})")
            
            parts.append(entry.message)
            
            message = " ".join(parts)
            
            if entry.context:
                context_str = " | ".join(f"{k}={v}" for k, v in entry.context.items())
                message += f" | {context_str}"
            
            return message
    
    def _update_performance_stats(self, operation_name: str, duration_ms: float) -> None:
        """Update performance statistics."""
        try:
            # Update average duration
            total_logs = self._performance_stats["total_logs"]
            current_avg = self._performance_stats["average_log_duration"]
            new_avg = ((current_avg * (total_logs - 1)) + duration_ms) / total_logs
            self._performance_stats["average_log_duration"] = new_avg
            
            # Update slowest operations
            slowest = self._performance_stats["slowest_operations"]
            slowest.append({
                "operation": operation_name,
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow()
            })
            
            # Keep only top 10 slowest
            slowest.sort(key=lambda x: x["duration_ms"], reverse=True)
            self._performance_stats["slowest_operations"] = slowest[:10]
            
        except Exception:
            pass  # Don't let stats updates break logging


class TimingLogContext:
    """Context manager for logging with automatic timing."""
    
    def __init__(
        self,
        logger: TelemetryLogger,
        level: LogLevel,
        message: str,
        operation_name: str,
        correlation_id: Optional[str] = None,
        **context
    ):
        self.logger = logger
        self.level = level
        self.message = message
        self.operation_name = operation_name
        self.correlation_id = correlation_id
        self.context = context
        self.start_time = None
        self.operation_id = f"timing_{int(time.time() * 1000)}"
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.start_operation_timer(self.operation_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        # Add duration to context
        context = self.context.copy()
        context["duration_ms"] = duration_ms
        
        if exc_type:
            context["error_type"] = exc_type.__name__
            context["error_message"] = str(exc_val)
            self.logger._log(LogLevel.ERROR, self.message, self.correlation_id, self.operation_name, **context)
        else:
            self.logger._log(self.level, self.message, self.correlation_id, self.operation_name, **context)
        
        self.logger.end_operation_timer(self.operation_id, self.operation_name, self.correlation_id)


class OperationLogger:
    """Logger for a specific operation with correlation ID tracking."""
    
    def __init__(self, logger: TelemetryLogger, operation_name: str, correlation_id: Optional[str] = None):
        self.logger = logger
        self.operation_name = operation_name
        self.correlation_id = correlation_id
        self.start_time = datetime.utcnow()
        
        # Set thread local correlation ID
        if correlation_id:
            set_thread_correlation_id(correlation_id)
    
    def debug(self, message: str, **context):
        """Log debug message for this operation."""
        self.logger.debug(message, self.correlation_id, operation=self.operation_name, **context)
    
    def info(self, message: str, **context):
        """Log info message for this operation."""
        self.logger.info(message, self.correlation_id, operation=self.operation_name, **context)
    
    def warning(self, message: str, **context):
        """Log warning message for this operation."""
        self.logger.warning(message, self.correlation_id, operation=self.operation_name, **context)
    
    def error(self, message: str, **context):
        """Log error message for this operation."""
        self.logger.error(message, self.correlation_id, operation=self.operation_name, **context)
    
    def critical(self, message: str, **context):
        """Log critical message for this operation."""
        self.logger.critical(message, self.correlation_id, operation=self.operation_name, **context)
    
    def performance(self, message: str, duration_ms: float, **context):
        """Log performance message for this operation."""
        context["duration_ms"] = duration_ms
        self.logger.info(message, self.correlation_id, operation=self.operation_name, **context)
    
    def step(self, step_name: str, **context):
        """Log a step in the operation."""
        message = f"Step: {step_name}"
        self.logger.info(message, self.correlation_id, operation=self.operation_name, step=step_name, **context)
    
    def complete(self, success: bool = True, **context):
        """Complete the operation."""
        duration_ms = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        message = f"Operation {'completed' if success else 'failed'}: {self.operation_name}"
        context.update({
            "success": success,
            "duration_ms": duration_ms,
            "total_duration_ms": duration_ms
        })
        
        if success:
            self.logger.info(message, self.correlation_id, operation=self.operation_name, **context)
        else:
            self.logger.error(message, self.correlation_id, operation=self.operation_name, **context)
        
        # Clear thread local correlation ID
        clear_thread_correlation_id()
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        success = exc_type is None
        self.complete(success, error_type=exc_type.__name__ if exc_type else None)


# Global telemetry logger factory
_telemetry_loggers: Dict[str, TelemetryLogger] = {}


def get_telemetry_logger(component_name: str, config: Optional[TelemetryConfiguration] = None) -> TelemetryLogger:
    """
    Get or create a telemetry logger for a component.
    
    Args:
        component_name: Name of the component
        config: Optional telemetry configuration
        
    Returns:
        TelemetryLogger instance
    """
    if component_name not in _telemetry_loggers:
        if config is None:
            from ..configuration.telemetry_config import TelemetryConfiguration
            config = TelemetryConfiguration()
        
        _telemetry_loggers[component_name] = TelemetryLogger(config, component_name)
    
    return _telemetry_loggers[component_name]


def with_correlation_logging(correlation_id: Optional[str] = None):
    """
    Decorator to add correlation ID logging to a function.
    
    Args:
        correlation_id: Optional correlation ID to use
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Set correlation ID
            if correlation_id:
                set_thread_correlation_id(correlation_id)
            
            try:
                return func(*args, **kwargs)
            finally:
                # Clear correlation ID
                clear_thread_correlation_id()
        
        return wrapper
    return decorator


async def log_operation_with_timing(
    logger: TelemetryLogger,
    operation_name: str,
    level: LogLevel = LogLevel.INFO,
    correlation_id: Optional[str] = None,
    **context
):
    """
    Context manager for logging operations with timing.
    
    Args:
        logger: Telemetry logger instance
        operation_name: Name of the operation
        level: Log level for the operation
        correlation_id: Optional correlation ID
        **context: Additional context
    """
    return logger.log_with_timing(level, f"Starting {operation_name}", operation_name, correlation_id, **context)
