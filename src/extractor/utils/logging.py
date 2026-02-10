"""
Structured logging utilities for the extractor module.

This module provides centralized logging functionality with structured
JSON output and correlation ID support.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class ExtractorFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "lineno", "funcName", "created",
                "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "getMessage", "exc_info",
                "exc_text", "stack_info"
            }:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


def setup_logging(
    level: str = "INFO",
    include_performance_metrics: bool = True,
    logger_name: str = "extractor"
) -> logging.Logger:
    """Setup structured logging for the extractor module."""
    
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))
    
    # Use custom formatter
    formatter = ExtractorFormatter()
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


def get_logger(name: str = "extractor") -> logging.Logger:
    """Get a logger instance for the extractor module."""
    return logging.getLogger(name)


class ExtractionLogger:
    """Specialized logger for extraction operations with correlation support."""
    
    def __init__(
        self,
        logger_name: str = "extractor",
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.logger = get_logger(logger_name)
        self.correlation_id = correlation_id
        self.session_id = session_id
    
    def _log_with_context(
        self,
        level: int,
        message: str,
        **kwargs
    ):
        """Log message with extraction context."""
        extra = {
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            **kwargs
        }
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def log_extraction_start(
        self,
        rule_name: str,
        extraction_type: str,
        element_info: Optional[Dict[str, Any]] = None,
    ):
        """Log the start of an extraction operation."""
        self.info(
            "Extraction started",
            rule_name=rule_name,
            extraction_type=extraction_type,
            element_info=element_info,
        )
    
    def log_extraction_success(
        self,
        rule_name: str,
        value: Any,
        extraction_time_ms: float,
        transformations_applied: Optional[list] = None,
    ):
        """Log successful extraction."""
        self.info(
            "Extraction successful",
            rule_name=rule_name,
            value=value,
            extraction_time_ms=extraction_time_ms,
            transformations_applied=transformations_applied or [],
        )
    
    def log_extraction_failure(
        self,
        rule_name: str,
        error_message: str,
        error_code: str,
        used_default: bool = False,
    ):
        """Log extraction failure."""
        self.warning(
            "Extraction failed",
            rule_name=rule_name,
            error_message=error_message,
            error_code=error_code,
            used_default=used_default,
        )
    
    def log_validation_failure(
        self,
        rule_name: str,
        field_path: str,
        validation_errors: list,
    ):
        """Log validation failure."""
        self.warning(
            "Validation failed",
            rule_name=rule_name,
            field_path=field_path,
            validation_errors=validation_errors,
        )
    
    def log_performance_metrics(
        self,
        total_extractions: int,
        successful_extractions: int,
        average_time_ms: float,
        cache_hit_rate: float,
    ):
        """Log performance metrics."""
        self.info(
            "Performance metrics",
            total_extractions=total_extractions,
            successful_extractions=successful_extractions,
            success_rate=successful_extractions / total_extractions if total_extractions > 0 else 0,
            average_time_ms=average_time_ms,
            cache_hit_rate=cache_hit_rate,
        )
