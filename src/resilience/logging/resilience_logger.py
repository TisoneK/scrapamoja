"""
Structured Logging for Resilience Components

Provides structured logging with correlation IDs and context tracking for all
resilience operations including failures, retries, checkpoints, and resource events.
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
import uuid


class ResilienceLogger:
    """Structured logger for resilience components with correlation tracking."""
    
    def __init__(self, name: str = "resilience"):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Setup the logger with appropriate handlers and formatters."""
        if not self.logger.handlers:
            # Create console handler
            handler = logging.StreamHandler()
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            
            # Add handler to logger
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _create_log_entry(
        self,
        level: str,
        message: str,
        event_type: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None,
        severity: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a structured log entry."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "event_type": event_type,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "context": context or {},
            "component": component or "resilience",
            "severity": severity or level.lower()
        }
        
        return entry
    
    def _log_structured(
        self,
        level: str,
        message: str,
        event_type: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None,
        severity: Optional[str] = None
    ) -> None:
        """Log a structured entry."""
        entry = self._create_log_entry(
            level, message, event_type, correlation_id, context, component, severity
        )
        
        # Log as JSON for structured parsing
        log_message = json.dumps(entry, default=str)
        
        # Use appropriate logging level
        if level.upper() == "DEBUG":
            self.logger.debug(log_message)
        elif level.upper() == "INFO":
            self.logger.info(log_message)
        elif level.upper() == "WARNING":
            self.logger.warning(log_message)
        elif level.upper() == "ERROR":
            self.logger.error(log_message)
        elif level.upper() == "CRITICAL":
            self.logger.critical(log_message)
        else:
            self.logger.info(log_message)
    
    def info(
        self,
        message: str,
        event_type: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None
    ) -> None:
        """Log an info message."""
        self._log_structured(
            "INFO", message, event_type, correlation_id, context, component
        )
    
    def warning(
        self,
        message: str,
        event_type: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None
    ) -> None:
        """Log a warning message."""
        self._log_structured(
            "WARNING", message, event_type, correlation_id, context, component
        )
    
    def error(
        self,
        message: str,
        event_type: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None,
        include_traceback: bool = True
    ) -> None:
        """Log an error message."""
        log_context = context or {}
        
        if include_traceback:
            log_context["stack_trace"] = traceback.format_exc()
        
        self._log_structured(
            "ERROR", message, event_type, correlation_id, log_context, component
        )
    
    def critical(
        self,
        message: str,
        event_type: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None,
        include_traceback: bool = True
    ) -> None:
        """Log a critical message."""
        log_context = context or {}
        
        if include_traceback:
            log_context["stack_trace"] = traceback.format_exc()
        
        self._log_structured(
            "CRITICAL", message, event_type, correlation_id, log_context, component
        )
    
    def debug(
        self,
        message: str,
        event_type: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None
    ) -> None:
        """Log a debug message."""
        self._log_structured(
            "DEBUG", message, event_type, correlation_id, context, component
        )


# Global logger instance
_resilience_logger = ResilienceLogger()


def get_logger(name: str = "resilience") -> ResilienceLogger:
    """Get a resilience logger instance."""
    return ResilienceLogger(name)


def log_failure_event(
    failure_type: str,
    message: str,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Log a failure event."""
    _resilience_logger.error(
        message=message,
        event_type="failure_event",
        correlation_id=correlation_id,
        context={
            "failure_type": failure_type,
            **(context or {})
        },
        component=component
    )


def log_retry_event(
    operation: str,
    attempt: int,
    max_attempts: int,
    delay: float,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Log a retry event."""
    _resilience_logger.info(
        message=f"Retry attempt {attempt}/{max_attempts} for {operation} after {delay}s delay",
        event_type="retry_attempt",
        correlation_id=correlation_id,
        context={
            "operation": operation,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "delay": delay,
            **(context or {})
        },
        component=component
    )


def log_checkpoint_event(
    action: str,
    checkpoint_id: str,
    job_id: str,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Log a checkpoint event."""
    _resilience_logger.info(
        message=f"Checkpoint {action}: {checkpoint_id} for job {job_id}",
        event_type="checkpoint_event",
        correlation_id=correlation_id,
        context={
            "action": action,
            "checkpoint_id": checkpoint_id,
            "job_id": job_id,
            **(context or {})
        },
        component=component
    )


def log_resource_event(
    resource_type: str,
    action: str,
    value: float,
    threshold: float,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Log a resource monitoring event."""
    severity = "warning" if value > threshold else "info"
    
    _resilience_logger._log_structured(
        level=severity.upper(),
        message=f"Resource {action}: {resource_type}={value} (threshold={threshold})",
        event_type="resource_event",
        correlation_id=correlation_id,
        context={
            "resource_type": resource_type,
            "action": action,
            "value": value,
            "threshold": threshold,
            **(context or {})
        },
        component=component,
        severity=severity
    )


def log_abort_event(
    reason: str,
    job_id: str,
    policy_id: str,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Log an abort event."""
    _resilience_logger.critical(
        message=f"Job abort triggered: {reason} for job {job_id} using policy {policy_id}",
        event_type="abort_event",
        correlation_id=correlation_id,
        context={
            "reason": reason,
            "job_id": job_id,
            "policy_id": policy_id,
            **(context or {})
        },
        component=component
    )


def log_recovery_event(
    recovery_type: str,
    original_error: str,
    action_taken: str,
    correlation_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    component: Optional[str] = None
) -> None:
    """Log a recovery event."""
    _resilience_logger.info(
        message=f"Recovery {recovery_type}: {action_taken} for error: {original_error}",
        event_type="recovery_event",
        correlation_id=correlation_id,
        context={
            "recovery_type": recovery_type,
            "original_error": original_error,
            "action_taken": action_taken,
            **(context or {})
        },
        component=component
    )
