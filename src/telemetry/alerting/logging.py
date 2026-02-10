"""
Structured Logging for Alerting

Comprehensive logging system for alerting operations with
correlation tracking, performance monitoring, and audit trails.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import sys

from ..interfaces import Alert, AlertSeverity, AlertType
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryAlertingError
from ..configuration.logging import get_logger


class AlertLogLevel(Enum):
    """Alert log level enumeration."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertLogCategory(Enum):
    """Alert log category enumeration."""
    ALERT_GENERATION = "alert_generation"
    ALERT_ACKNOWLEDGMENT = "alert_acknowledgment"
    ALERT_RESOLUTION = "alert_resolution"
    ALERT_ESCALATION = "alert_escalation"
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_FAILED = "notification_failed"
    THRESHOLD_EVALUATION = "threshold_evaluation"
    ANOMALY_DETECTION = "anomaly_detection"
    SEVERITY_CLASSIFICATION = "severity_classification"
    SYSTEM_ERROR = "system_error"


@dataclass
class AlertLogEntry:
    """Structured alert log entry."""
    timestamp: datetime
    level: AlertLogLevel
    category: AlertLogCategory
    alert_id: Optional[str]
    correlation_id: Optional[str]
    operation: Optional[str]
    message: str
    context: Dict[str, Any]
    duration_ms: Optional[float] = None
    error_details: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class AlertLogStatistics:
    """Statistics for alert logging."""
    total_logs: int = 0
    logs_by_level: Dict[str, int] = None
    logs_by_category: Dict[str, int] = None
    average_log_duration_ms: float = 0.0
    error_count: int = 0
    most_common_category: str = ""
    last_log: Optional[datetime] = None
    
    def __post_init__(self):
        if self.logs_by_level is None:
            self.logs_by_level = {}
        if self.logs_by_category is None:
            self.logs_by_category = {}


class AlertLogger:
    """
    Structured logger for alerting operations with correlation tracking.
    
    Provides comprehensive logging for alerting operations with
    correlation tracking, performance monitoring, and audit trails.
    """
    
    def __init__(self, config: TelemetryConfiguration, component_name: str = "alerting"):
        """
        Initialize alert logger.
        
        Args:
            config: Telemetry configuration
            component_name: Name of the component
        """
        self.config = config
        self.component_name = component_name
        self.logger = get_logger(f"alerting.{component_name}")
        
        # Logging configuration
        self.log_level = config.get("alert_log_level", "INFO")
        self.structured_logging = config.get("alert_structured_logging", True)
        self.include_performance = config.get("alert_include_performance_in_logs", True)
        self.audit_trail_enabled = config.get("alert_audit_trail_enabled", True)
        
        # Log storage
        self._log_entries: List[AlertLogEntry] = []
        self._log_lock = asyncio.Lock()
        self._max_entries = config.get("max_alert_log_entries", 10000)
        
        # Performance tracking
        self._operation_timers: Dict[str, float] = {}
        self._performance_stats = {
            "total_logs": 0,
            "logs_by_level": {},
            "logs_by_category": {},
            "average_log_duration": 0.0,
            "slowest_operations": []
        }
        
        # Audit trail
        self._audit_trail: List[Dict[str, Any]] = []
        self._max_audit_entries = config.get("max_audit_trail_entries", 5000)
    
    def trace(self, message: str, alert_id: Optional[str] = None, correlation_id: Optional[str] = None, **context) -> None:
        """Log trace message."""
        self._log(AlertLogLevel.TRACE, message, alert_id, correlation_id, **context)
    
    def debug(self, message: str, alert_id: Optional[str] = None, correlation_id: Optional[str] = None, **context) -> None:
        """Log debug message."""
        self._log(AlertLogLevel.DEBUG, message, alert_id, correlation_id, **context)
    
    def info(self, message: str, alert_id: Optional[str] = None, correlation_id: Optional[str] = None, **context) -> None:
        """Log info message."""
        self._log(AlertLogLevel.INFO, message, alert_id, correlation_id, **context)
    
    def warning(self, message: str, alert_id: Optional[str] = None, correlation_id: Optional[str] = None, **context) -> None:
        """Log warning message."""
        self._log(AlertLogLevel.WARNING, message, alert_id, correlation_id, **context)
    
    def error(self, message: str, alert_id: Optional[str] = None, correlation_id: Optional[str] = None, **context) -> None:
        """Log error message."""
        self._log(AlertLogLevel.ERROR, message, alert_id, correlation_id, **context)
    
    def critical(self, message: str, alert_id: Optional[str] = None, correlation_id: Optional[str] = None, **context) -> None:
        """Log critical message."""
        self._log(AlertLogLevel.CRITICAL, message, alert_id, correlation_id, **context)
    
    # Alert-specific logging methods
    
    def alert_generated(self, alert: Alert, generation_time_ms: float, **context) -> None:
        """Log alert generation."""
        message = f"Alert generated: {alert.title}"
        log_context = {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "severity": alert.severity.value,
            "type": alert.alert_type.value,
            "generation_time_ms": generation_time_ms,
            "selector_name": alert.selector_name,
            "correlation_id": alert.correlation_id,
            "tags": alert.tags,
            **context
        }
        self._log(
            AlertLogLevel.INFO,
            message,
            alert.alert_id,
            alert.correlation_id,
            AlertLogCategory.ALERT_GENERATION,
            generation_time_ms,
            context=log_context
        )
    
    def alert_acknowledged(self, alert_id: str, acknowledged_by: str, acknowledgment_time_ms: float, **context) -> None:
        """Log alert acknowledgment."""
        message = f"Alert acknowledged: {alert_id}"
        log_context = {
            "acknowledged_by": acknowledged_by,
            "acknowledgment_time_ms": acknowledgment_time_ms,
            **context
        }
        self._log(
            AlertLogLevel.INFO,
            message,
            alert_id,
            None,
            AlertLogCategory.ALERT_ACKNOWLEDGMENT,
            acknowledgment_time_ms,
            context=log_context
        )
    
    def alert_resolved(self, alert_id: str, resolved_by: str, resolution_time_ms: float, method: str, **context) -> None:
        """Log alert resolution."""
        message = f"Alert resolved: {alert_id}"
        log_context = {
            "resolved_by": resolved_by,
            "resolution_time_ms": resolution_time_ms,
            "method": method,
            **context
        }
        self._log(
            AlertLogLevel.INFO,
            message,
            alert_id,
            None,
            AlertLogCategory.ALERT_RESOLUTION,
            resolution_time_ms,
            context=log_context
        )
    
    def alert_escalated(self, alert_id: str, escalation_level: str, escalated_by: str, escalation_time_ms: float, **context) -> None:
        """Log alert escalation."""
        message = f"Alert escalated: {alert_id} to {escalation_level}"
        log_context = {
            "escalation_level": escalation_level,
            "escalated_by": escalated_by,
            "escalation_time_ms": escalation_time_ms,
            **context
        }
        self._log(
            AlertLogLevel.WARNING,
            message,
            alert_id,
            None,
            AlertLogCategory.ALERT_ESCALATION,
            escalation_time_ms,
            context=log_context
        )
    
    def notification_sent(self, alert_id: str, channel_id: str, delivery_time_ms: float, **context) -> None:
        """Log successful notification delivery."""
        message = f"Notification sent: {alert_id} via {channel_id}"
        log_context = {
            "channel_id": channel_id,
            "delivery_time_ms": delivery_time_ms,
            **context
        }
        self._log(
            AlertLogLevel.INFO,
            message,
            alert_id,
            None,
            AlertLogCategory.NOTIFICATION_SENT,
            delivery_time_ms,
            context=log_context
        )
    
    def notification_failed(self, alert_id: str, channel_id: str, error: str, **context) -> None:
        """Log failed notification delivery."""
        message = f"Notification failed: {alert_id} via {channel_id}"
        log_context = {
            "channel_id": channel_id,
            "error": error,
            **context
        }
        self._log(
            AlertLogLevel.ERROR,
            message,
            alert_id,
            None,
            AlertLogCategory.NOTIFICATION_FAILED,
            None,
            context=log_context
        )
    
    def threshold_evaluated(self, metric_name: str, current_value: float, threshold_value: float, triggered: bool, evaluation_time_ms: float, **context) -> None:
        """Log threshold evaluation."""
        message = f"Threshold evaluated: {metric_name} = {current_value} vs {threshold_value} - {'TRIGGERED' if triggered else 'OK'}"
        log_context = {
            "metric_name": metric_name,
            "current_value": current_value,
            "threshold_value": threshold_value,
            "triggered": triggered,
            "evaluation_time_ms": evaluation_time_ms,
            **context
        }
        self._log(
            AlertLogLevel.DEBUG,
            message,
            None,
            None,
            AlertLogCategory.THRESHOLD_EVALUATION,
            evaluation_time_ms,
            context=log_context
        )
    
    def anomaly_detected(self, metric_name: str, anomaly_type: str, confidence: float, detection_time_ms: float, **context) -> None:
        """Log anomaly detection."""
        message = f"Anomaly detected: {metric_name} - {anomaly_type}"
        log_context = {
            "metric_name": metric_name,
            "anomaly_type": anomaly_type,
            "confidence": confidence,
            "detection_time_ms": detection_time_ms,
            **context
        }
        self._log(
            AlertLogLevel.INFO,
            message,
            None,
            None,
            AlertLogCategory.ANOMALY_DETECTION,
            detection_time_ms,
            context=log_context
        )
    
    def severity_classified(self, alert_id: str, original_severity: str, classified_severity: str, confidence: float, classification_time_ms: float, **context) -> None:
        """Log severity classification."""
        message = f"Severity classified: {alert_id} - {original_severity} -> {classified_severity}"
        log_context = {
            "original_severity": original_severity,
            "classified_severity": classified_severity,
            "confidence": confidence,
            "classification_time_ms": classification_time_ms,
            **context
        }
        self._log(
            AlertLogLevel.DEBUG,
            message,
            alert_id,
            None,
            AlertLogCategory.SEVERITY_CLASSIFICATION,
            classification_time_ms,
            context=log_context
        )
    
    def system_error(self, operation: str, error: str, error_time_ms: float, **context) -> None:
        """Log system error."""
        message = f"System error in {operation}: {error}"
        log_context = {
            "operation": operation,
            "error": error,
            "error_time_ms": error_time_ms,
            **context
        }
        self._log(
            AlertLogLevel.ERROR,
            message,
            None,
            None,
            AlertLogCategory.SYSTEM_ERROR,
            error_time_ms,
            context=log_context
        )
    
    def start_operation_timer(self, operation_id: str) -> None:
        """Start timing an operation."""
        self._operation_timers[operation_id] = time.time()
    
    def end_operation_timer(
        self,
        operation_id: str,
        operation_name: str,
        alert_id: Optional[str] = None,
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
        
        self._log(
            AlertLogLevel.DEBUG,
            message,
            alert_id,
            correlation_id,
            None,
            duration_ms,
            context=log_context
        )
        
        # Update performance statistics
        self._update_performance_stats(operation_name, duration_ms)
        
        return duration_ms
    
    def log_with_timing(
        self,
        level: AlertLogLevel,
        message: str,
        operation_name: str,
        alert_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **context
    ):
        """Context manager for logging with automatic timing."""
        return AlertTimingLogContext(self, level, message, operation_name, alert_id, correlation_id, **context)
    
    def create_operation_logger(
        self,
        operation_name: str,
        alert_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> "AlertOperationLogger":
        """Create an operation-specific logger."""
        return AlertOperationLogger(self, operation_name, alert_id, correlation_id)
    
    async def get_log_entries(
        self,
        level: Optional[AlertLogLevel] = None,
        category: Optional[AlertLogCategory] = None,
        alert_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: Optional[int] = None,
        time_window: Optional[timedelta] = None
    ) -> List[AlertLogEntry]:
        """
        Get log entries with filtering.
        
        Args:
            level: Optional log level filter
            category: Optional category filter
            alert_id: Optional alert ID filter
            correlation_id: Optional correlation ID filter
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
                
                if category:
                    entries = [entry for entry in entries if entry.category == category]
                
                if alert_id:
                    entries = [entry for entry in entries if entry.alert_id == alert_id]
                
                if correlation_id:
                    entries = [entry for entry in entries if entry.correlation_id == correlation_id]
                
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
    
    async def get_log_statistics(self) -> Dict[str, Any]:
        """
        Get alert logging statistics.
        
        Returns:
            Alert logging statistics
        """
        try:
            async with self._log_lock:
                stats = {
                    "total_logs": self._performance_stats["total_logs"],
                    "logs_by_level": dict(self._performance_stats["logs_by_level"]),
                    "logs_by_category": dict(self._performance_stats["logs_by_category"]),
                    "average_log_duration_ms": self._performance_stats["average_log_duration"],
                    "error_count": self._performance_stats.get("error_count", 0),
                    "most_common_category": self._performance_stats.get("most_common_category", ""),
                    "last_log": self._performance_stats.get("last_log"),
                    "audit_trail_entries": len(self._audit_trail),
                    "max_entries": self._max_entries,
                    "structured_logging": self.structured_logging
                }
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get log statistics: {e}")
            return {}
    
    async def get_audit_trail(
        self,
        alert_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        limit: Optional[int] = None,
        time_window: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail entries.
        
        Args:
            alert_id: Optional alert ID filter
            operation_type: Optional operation type filter
            limit: Optional limit on number of entries
            time_window: Optional time window for entries
            
        Returns:
            Audit trail entries
        """
        try:
            entries = self._audit_trail.copy()
            
            # Apply filters
            if alert_id:
                entries = [entry for entry in entries if entry.get("alert_id") == alert_id]
            
            if operation_type:
                entries = [entry for entry in entries if entry.get("operation_type") == operation_type]
            
            if time_window:
                cutoff_time = datetime.utcnow() - time_window
                entries = [entry for entry in entries if datetime.fromisoformat(entry["timestamp"]) >= cutoff_time]
            
            # Sort by timestamp (newest first)
            entries.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Apply limit
            if limit:
                entries = entries[:limit]
            
            return entries
            
        except Exception as e:
            self.logger.error(f"Failed to get audit trail: {e}")
            return []
    
    async def clear_log_entries(
        self,
        level: Optional[AlertLogLevel] = None,
        category: Optional[AlertLogCategory] = None,
        time_window: Optional[timedelta] = None
    ) -> int:
        """
        Clear log entries with filtering.
        
        Args:
            level: Optional log level filter
            category: Optional category filter
            time_window: Optional time window for entries to clear
            
        Returns:
            Number of entries cleared
        """
        try:
            async with self._log_lock:
                original_count = len(self._log_entries)
                
                # Apply filters for entries to keep
                if level or category or time_window:
                    entries_to_keep = []
                    
                    for entry in self._log_entries:
                        keep = True
                        
                        if level and entry.level == level:
                            keep = False
                        
                        if category and entry.category == category:
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
    
    # Private methods
    
    def _log(
        self,
        level: AlertLogLevel,
        message: str,
        alert_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        category: Optional[AlertLogCategory] = None,
        duration_ms: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Internal logging method."""
        try:
            # Create log entry
            entry = AlertLogEntry(
                timestamp=datetime.utcnow(),
                level=level,
                category=category or AlertLogCategory.SYSTEM_ERROR,
                alert_id=alert_id,
                correlation_id=correlation_id,
                operation=None,
                message=message,
                context=context or {},
                duration_ms=duration_ms
            )
            
            # Add to storage
            asyncio.create_task(self._add_log_entry(entry))
            
            # Output to standard logger
            log_message = self._format_log_message(entry)
            
            if level == AlertLogLevel.TRACE:
                self.logger.debug(log_message)
            elif level == AlertLogLevel.DEBUG:
                self.logger.debug(log_message)
            elif level == AlertLogLevel.INFO:
                self.logger.info(log_message)
            elif level == AlertLogLevel.WARNING:
                self.logger.warning(log_message)
            elif level == AlertLogLevel.ERROR:
                self.logger.error(log_message)
            elif level == AlertLogLevel.CRITICAL:
                self.logger.critical(log_message)
            
            # Add to audit trail if enabled
            if self.audit_trail_enabled and category:
                asyncio.create_task(self._add_to_audit_trail(entry))
            
        except Exception as e:
            # Fallback logging to avoid infinite recursion
            self.logger.error(f"Failed to log message: {e}")
    
    async def _add_log_entry(self, entry: AlertLogEntry) -> None:
        """Add log entry to storage."""
        try:
            async with self._log_lock:
                self._log_entries.append(entry)
                
                # Limit entries
                if len(self._log_entries) > self._max_entries:
                    self._log_entries = self._log_entries[-self._max_entries:]
                
                # Update performance stats
                self._performance_stats["total_logs"] += 1
                
                level_name = entry.level.value
                if level_name not in self._performance_stats["logs_by_level"]:
                    self._performance_stats["logs_by_level"][level_name] = 0
                self._performance_stats["logs_by_level"][level_name] += 1
                
                category_name = entry.category.value
                if category_name not in self._performance_stats["logs_by_category"]:
                    self._performance_stats["logs_by_category"][category_name] = 0
                self._performance_stats["logs_by_category"][category_name] += 1
                
                self._performance_stats["last_log"] = entry.timestamp
                
                # Update most common category
                if self._performance_stats["logs_by_category"]:
                    self._performance_stats["most_common_category"] = max(
                        self._performance_stats["logs_by_category"],
                        key=self._performance_stats["logs_by_category"].get
                    )
                
        except Exception as e:
            self.logger.error(f"Failed to add log entry: {e}")
    
    async def _add_to_audit_trail(self, entry: AlertLogEntry) -> None:
        """Add entry to audit trail."""
        try:
            audit_entry = {
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.value,
                "category": entry.category.value,
                "alert_id": entry.alert_id,
                "correlation_id": entry.correlation_id,
                "message": entry.message,
                "context": entry.context,
                "duration_ms": entry.duration_ms
            }
            
            self._audit_trail.append(audit_entry)
            
            # Limit audit trail
            if len(self._audit_trail) > self._max_audit_entries:
                self._audit_trail = self._audit_trail[-self._max_audit_entries:]
                
        except Exception as e:
            self.logger.error(f"Failed to add to audit trail: {e}")
    
    def _format_log_message(self, entry: AlertLogEntry) -> str:
        """Format log message for output."""
        if self.structured_logging:
            # Structured JSON format
            log_data = {
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.value,
                "category": entry.category.value,
                "alert_id": entry.alert_id,
                "correlation_id": entry.correlation_id,
                "message": entry.message,
                "context": entry.context
            }
            
            if entry.duration_ms:
                log_data["duration_ms"] = entry.duration_ms
            
            return json.dumps(log_data, default=str)
        else:
            # Traditional format
            parts = [
                entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                entry.level.value,
                entry.category.value
            ]
            
            if entry.alert_id:
                parts.append(f"[{entry.alert_id}]")
            
            if entry.correlation_id:
                parts.append(f"[{entry.correlation_id}]")
            
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


class AlertTimingLogContext:
    """Context manager for alert logging with automatic timing."""
    
    def __init__(
        self,
        logger: AlertLogger,
        level: AlertLogLevel,
        message: str,
        operation_name: str,
        alert_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **context
    ):
        self.logger = logger
        self.level = level
        self.message = message
        self.operation_name = operation_name
        self.alert_id = alert_id
        self.correlation_id = correlation_id
        self.context = context
        self.start_time = None
        self.operation_id = f"timing_{int(time.time() * 1000)}"
    
    def __enter__(self):
        """Enter context and start timing."""
        self.start_time = time.time()
        self.logger.start_operation_timer(self.operation_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and complete timing."""
        duration_ms = (time.time() - self.start_time) * 1000
        
        # Add duration to context
        context = self.context.copy()
        context["duration_ms"] = duration_ms
        
        if exc_type:
            context["error_type"] = exc_type.__name__
            context["error_message"] = str(exc_val)
            self.logger._log(self.level, self.message, self.alert_id, self.correlation_id, None, duration_ms, context)
        else:
            self.logger._log(self.level, self.message, self.alert_id, self.correlation_id, None, duration_ms, context)
        
        self.logger.end_operation_timer(self.operation_id, self.operation_name, self.alert_id, self.correlation_id)


class AlertOperationLogger:
    """Logger for alert-specific operations with correlation ID tracking."""
    
    def __init__(self, logger: AlertLogger, operation_name: str, alert_id: Optional[str] = None, correlation_id: Optional[str] = None):
        self.logger = logger
        self.operation_name = operation_name
        self.alert_id = alert_id
        self.correlation_id = correlation_id
        self.start_time = datetime.utcnow()
    
    def trace(self, message: str, **context):
        """Log trace message for this operation."""
        self.logger.trace(message, self.alert_id, self.correlation_id, operation=self.operation_name, **context)
    
    def debug(self, message: str, **context):
        """Log debug message for this operation."""
        self.logger.debug(message, self.alert_id, self.correlation_id, operation=self.operation_name, **context)
    
    def info(self, message: str, **context):
        """Log info message for this operation."""
        self.logger.info(message, self.alert_id, self.correlation_id, operation=self.operation_name, **context)
    
    def warning(self, message: str, **context):
        """Log warning message for this operation."""
        self.logger.warning(message, self.alert_id, self.correlation_id, operation=self.operation_name, **context)
    
    def error(self, message: str, **context):
        """Log error message for this operation."""
        self.logger.error(message, self.alert_id, self.correlation_id, operation=self.operation_name, **context)
    
    def critical(self, message: str, **context):
        """Log critical message for this operation."""
        self.logger.critical(message, self.alert_id, self.correlation_id, operation=self.operation_name, **context)
    
    def performance(self, message: str, duration_ms: float, **context):
        """Log performance message for this operation."""
        context.update({
            "duration_ms": duration_ms,
            "operation": self.operation_name
        })
        self.logger.info(message, self.alert_id, self.correlation_id, **context)
    
    def step(self, step_name: str, **context):
        """Log a step in the operation."""
        message = f"Step: {step_name}"
        self.logger.info(message, self.alert_id, self.correlation_id, operation=self.operation_name, step=step_name, **context)
    
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
            self.logger.info(message, self.alert_id, self.correlation_id, **context)
        else:
            self.logger.error(message, self.alert_id, self.correlation_id, **context)
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        success = exc_type is None
        self.complete(success, error_type=exc_type.__name__ if exc_type else None)
