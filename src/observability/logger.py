"""
Structured logging configuration for Selector Engine.

Provides JSON-formatted logging with correlation IDs and run traceability
as required by the Scorewise Constitution.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from contextvars import ContextVar
# Removed structlog import to prevent double JSON encoding


# Context variables for correlation tracking
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
run_id: ContextVar[Optional[str]] = ContextVar('run_id', default=None)
selector_name: ContextVar[Optional[str]] = ContextVar('selector_name', default=None)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add correlation context if available
        if correlation_id.get():
            log_entry['correlation_id'] = correlation_id.get()
        if run_id.get():
            log_entry['run_id'] = run_id.get()
        if selector_name.get():
            log_entry['selector_name'] = selector_name.get()
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'lineno', 
                          'funcName', 'created', 'msecs', 'relativeCreated', 
                          'thread', 'threadName', 'processName', 'process',
                          'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class ContextualLogger:
    """Logger wrapper that automatically includes context."""
    
    def __init__(self, logger: logging.Logger, context: Dict[str, Any]):
        self.logger = logger
        self.context = context
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        extra = self.context.copy()
        extra.update(kwargs)
        self.logger.info(message, extra=extra)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        extra = self.context.copy()
        extra.update(kwargs)
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        extra = self.context.copy()
        extra.update(kwargs)
        self.logger.error(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        extra = self.context.copy()
        extra.update(kwargs)
        self.logger.debug(message, extra=extra)


class SelectorEngineLogger:
    """Selector Engine logger with correlation context support."""
    
    def __init__(self, name: str = "selector_engine"):
        self.name = name
        self.logger = logging.getLogger(name)
        # Removed structlog to prevent double JSON encoding
    
    def with_context(self, **kwargs):
        """Create logger with additional context."""
        # Merge context with correlation variables
        context = {}
        if correlation_id.get():
            context['correlation_id'] = correlation_id.get()
        if run_id.get():
            context['run_id'] = run_id.get()
        if selector_name.get():
            context['selector_name'] = selector_name.get()
        context.update(kwargs)
        
        # Return a new logger instance with merged context
        return ContextualLogger(self.logger, context)
    
    def info(self, message: str, **kwargs):
        """Log info message with correlation context."""
        self._log_with_context("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with correlation context."""
        self._log_with_context("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with correlation context."""
        self._log_with_context("error", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with correlation context."""
        self._log_with_context("debug", message, **kwargs)
    
    def _log_with_context(self, level: str, message: str, **kwargs):
        """Log message with correlation context."""
        context = {}
        
        # Add correlation context
        if correlation_id.get():
            context['correlation_id'] = correlation_id.get()
        if run_id.get():
            context['run_id'] = run_id.get()
        if selector_name.get():
            context['selector_name'] = selector_name.get()
        
        # Add provided kwargs
        context.update(kwargs)
        
        # Log the message using extra= parameter
        logger_method = getattr(self.logger, level)
        logger_method(message, extra=context)


class CorrelationContext:
    """Manager for correlation context across async operations."""
    
    @staticmethod
    def set_correlation_id(cid: str) -> None:
        """Set correlation ID for current context."""
        correlation_id.set(cid)
    
    @staticmethod
    def get_correlation_id() -> Optional[str]:
        """Get correlation ID from current context."""
        return correlation_id.get()
    
    @staticmethod
    def generate_correlation_id() -> str:
        """Generate new correlation ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def set_run_id(rid: str) -> None:
        """Set run ID for current context."""
        run_id.set(rid)
    
    @staticmethod
    def get_run_id() -> Optional[str]:
        """Get run ID from current context."""
        return run_id.get()
    
    @staticmethod
    def set_selector_name(sname: str) -> None:
        """Set selector name for current context."""
        selector_name.set(sname)
    
    @staticmethod
    def get_selector_name() -> Optional[str]:
        """Get selector name from current context."""
        return selector_name.get()
    
    @staticmethod
    def clear_context() -> None:
        """Clear all correlation context."""
        correlation_id.set(None)
        run_id.set(None)
        selector_name.set(None)


class PerformanceLogger:
    """Logger for performance metrics and timing."""
    
    def __init__(self, base_logger: SelectorEngineLogger):
        self.logger = base_logger
    
    def log_resolution_time(self, selector_name: str, strategy: str, 
                          resolution_time: float, confidence: float, 
                          success: bool):
        """Log selector resolution performance."""
        self.logger.info(
            "selector_resolution_completed",
            selector_name=selector_name,
            strategy=strategy,
            resolution_time_ms=resolution_time,
            confidence_score=confidence,
            success=success
        )
    
    def log_batch_performance(self, total_selectors: int, total_time: float, 
                            success_rate: float):
        """Log batch resolution performance."""
        self.logger.info(
            "batch_resolution_completed",
            total_selectors=total_selectors,
            total_time_ms=total_time,
            avg_time_per_selector=total_time / total_selectors,
            success_rate=success_rate
        )
    
    def log_drift_detection(self, selector_name: str, drift_score: float, 
                          trend: str, recommendations: list):
        """Log drift detection results."""
        self.logger.warning(
            "drift_detected",
            selector_name=selector_name,
            drift_score=drift_score,
            trend=trend,
            recommendations=recommendations
        )


class FailureLogger:
    """Logger for failure analysis and debugging."""
    
    def __init__(self, base_logger: SelectorEngineLogger):
        self.logger = base_logger
    
    def log_selector_failure(self, selector_name: str, strategies_tried: list, 
                           failure_reason: str, context: Dict[str, Any]):
        """Log selector failure with detailed context."""
        self.logger.error(
            "selector_resolution_failed",
            selector_name=selector_name,
            strategies_tried=strategies_tried,
            failure_reason=failure_reason,
            context=context
        )
    
    def log_snapshot_capture(self, selector_name: str, snapshot_id: str, 
                            file_size: int, capture_reason: str):
        """Log DOM snapshot capture."""
        self.logger.info(
            "dom_snapshot_captured",
            selector_name=selector_name,
            snapshot_id=snapshot_id,
            file_size_bytes=file_size,
            capture_reason=capture_reason
        )
    
    def log_strategy_failure(self, selector_name: str, strategy_id: str, 
                           error: str, execution_time: float):
        """Log individual strategy failure."""
        self.logger.warning(
            "strategy_execution_failed",
            selector_name=selector_name,
            strategy_id=strategy_id,
            error=error,
            execution_time_ms=execution_time
        )


# Global logger instance
selector_logger = SelectorEngineLogger()
performance_logger = PerformanceLogger(selector_logger)
failure_logger = FailureLogger(selector_logger)


def get_logger(name: str = "selector_engine") -> SelectorEngineLogger:
    """Get logger instance with specified name."""
    return SelectorEngineLogger(name)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration."""
    # TODO: Remove this - replaced by JsonLoggingConfigurator
    # # Create logs directory if it doesn't exist
    # log_dir = Path("data/logs")
    # log_dir.mkdir(parents=True, exist_ok=True)
    
    # # Configure logging level
    # level = getattr(logging, log_level.upper(), logging.INFO)
    
    # # Configure handlers
    # handlers = [
    #     RichHandler(console=Console(stderr=True)),
    #     logging.FileHandler(log_file or log_dir / "selector_engine.log")
    # ]
    
    # # Apply configuration
    # logging.basicConfig(
    #     level=level,
    #     handlers=handlers,
    #     format="%(message)s"
    # )
    
    # Apply JSON formatter to file handler
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            handler.setFormatter(JSONFormatter())
