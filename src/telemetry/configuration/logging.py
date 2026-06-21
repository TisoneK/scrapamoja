"""
Structured Logging Configuration for Telemetry System

Logging configuration with correlation IDs, structured formatting,
and telemetry-specific logging utilities.
"""

import structlog
import logging
import sys
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path


def configure_telemetry_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    correlation_id_enabled: bool = True
) -> None:
    """
    Configure structured logging for the telemetry system.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        correlation_id_enabled: Whether correlation IDs are enabled
    """
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper())
    )
    
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if correlation_id_enabled:
        processors.append(add_correlation_id_processor)
    
    processors.append(structlog.processors.UnicodeDecoder())
    
    # Add JSON or console renderer based on environment
    if log_file or _is_production_environment():
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure file logging if specified
    if log_file:
        _configure_file_logging(log_file, level)


def add_correlation_id_processor(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add correlation ID to log record if present in context.
    
    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The event dictionary
        
    Returns:
        Updated event dictionary with correlation ID
    """
    # Try to get correlation ID from various sources
    correlation_id = (
        event_dict.get("correlation_id") or
        getattr(logger._context, "correlation_id", None) or
        _get_thread_local_correlation_id()
    )
    
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    
    return event_dict


def _configure_file_logging(log_file: str, level: str) -> None:
    """
    Configure file logging for telemetry.
    
    Args:
        log_file: Path to log file
        level: Logging level
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, level.upper()))
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Add to root logger
    logging.getLogger().addHandler(file_handler)


def _is_production_environment() -> bool:
    """Check if running in production environment."""
    import os
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def _get_thread_local_correlation_id() -> Optional[str]:
    """Get correlation ID from thread local storage."""
    try:
        import threading
        local = threading.local()
        return getattr(local, "correlation_id", None)
    except (ImportError, AttributeError):
        return None


class TelemetryLogger:
    """
    Structured logger for telemetry system with correlation ID support.
    """
    
    def __init__(self, name: str = "telemetry"):
        self.logger = structlog.get_logger(name)
    
    def with_correlation_id(self, correlation_id: str) -> "TelemetryLogger":
        """
        Create a new logger instance with correlation ID bound.
        
        Args:
            correlation_id: Correlation ID to bind
            
        Returns:
            New logger instance with correlation ID
        """
        return TelemetryLogger(self.logger.bind(correlation_id=correlation_id))
    
    def with_context(self, **kwargs) -> "TelemetryLogger":
        """
        Create a new logger instance with additional context.
        
        Args:
            **kwargs: Additional context to bind
            
        Returns:
            New logger instance with additional context
        """
        return TelemetryLogger(self.logger.bind(**kwargs))
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, **kwargs)
    
    def event_collected(self, event_id: str, selector_name: str, **kwargs) -> None:
        """Log telemetry event collection."""
        self.info(
            "telemetry_event_collected",
            event_id=event_id,
            selector_name=selector_name,
            **kwargs
        )
    
    def event_stored(self, event_id: str, storage_type: str, **kwargs) -> None:
        """Log telemetry event storage."""
        self.info(
            "telemetry_event_stored",
            event_id=event_id,
            storage_type=storage_type,
            **kwargs
        )
    
    def alert_generated(self, alert_id: str, alert_type: str, severity: str, **kwargs) -> None:
        """Log alert generation."""
        self.warning(
            "telemetry_alert_generated",
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            **kwargs
        )
    
    def performance_warning(self, selector_name: str, metric: str, value: float, threshold: float, **kwargs) -> None:
        """Log performance warning."""
        self.warning(
            "telemetry_performance_warning",
            selector_name=selector_name,
            metric=metric,
            value=value,
            threshold=threshold,
            **kwargs
        )
    
    def storage_error(self, operation: str, error: str, **kwargs) -> None:
        """Log storage error."""
        self.error(
            "telemetry_storage_error",
            operation=operation,
            error=error,
            **kwargs
        )
    
    def buffer_overflow(self, buffer_size: int, current_count: int, **kwargs) -> None:
        """Log buffer overflow."""
        self.warning(
            "telemetry_buffer_overflow",
            buffer_size=buffer_size,
            current_count=current_count,
            **kwargs
        )
    
    def degradation_active(self, reason: str, **kwargs) -> None:
        """Log graceful degradation activation."""
        self.warning(
            "telemetry_degradation_active",
            reason=reason,
            **kwargs
        )


# Global logger instance
default_logger = TelemetryLogger()


def get_logger(name: str = "telemetry") -> TelemetryLogger:
    """
    Get a telemetry logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        TelemetryLogger instance
    """
    return TelemetryLogger(name)


def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    correlation_id_enabled: bool = True
) -> None:
    """
    Configure telemetry logging.
    
    Args:
        level: Logging level
        log_file: Optional log file path
        correlation_id_enabled: Whether correlation IDs are enabled
    """
    configure_telemetry_logging(level, log_file, correlation_id_enabled)
