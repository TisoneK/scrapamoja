"""
Logging infrastructure for the modular site scraper template system.

This module provides structured JSON logging with multiple log levels,
component-specific logging, and observability features.
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import asyncio
import traceback
from contextlib import asynccontextmanager

from .component_interface import BaseComponent


class LogLevel(Enum):
    """Log levels for structured logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Log categories for better organization."""
    SYSTEM = "system"
    COMPONENT = "component"
    FLOW = "flow"
    PROCESSOR = "processor"
    VALIDATOR = "validator"
    SCRAPER = "scraper"
    CONFIG = "config"
    PLUGIN = "plugin"
    PERFORMANCE = "performance"
    SECURITY = "security"


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    category: str
    component_id: Optional[str]
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    site_id: Optional[str] = None
    environment: Optional[str] = None
    execution_context: Dict[str, Any] = field(default_factory=dict)
    error_info: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if self.details is None:
            self.details = {}
        if self.execution_context is None:
            self.execution_context = {}


@dataclass
class PerformanceMetrics:
    """Performance metrics for logging."""
    execution_time_ms: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    network_requests_count: int = 0
    cache_hit_rate: Optional[float] = None
    throughput_items_per_second: Optional[float] = None
    
    def __post_init__(self):
        if self.memory_usage_mb is None:
            self.memory_usage_mb = 0.0
        if self.cpu_usage_percent is None:
            self.cpu_usage_percent = 0.0
        if self.cache_hit_rate is None:
            self.cache_hit_rate = 0.0
        if self.throughput_items_per_second is None:
            self.throughput_items_per_second = 0.0


class StructuredLogger:
    """Structured JSON logger for modular components."""
    
    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        log_file: Optional[str] = None,
        max_file_size_mb: int = 100,
        backup_count: int = 5,
        enable_console: bool = True,
        enable_json_format: bool = True
    ):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            level: Log level
            log_file: Log file path
            max_file_size_mb: Maximum file size in MB
            backup_count: Number of backup files
            enable_console: Enable console logging
            enable_json_format: Enable JSON formatting
        """
        self.name = name
        self.level = level
        self.log_file = log_file
        self.enable_console = enable_console
        self.enable_json_format = enable_json_format
        
        # Create Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Setup formatters
        self.json_formatter = self._create_json_formatter()
        self.plain_formatter = self._create_plain_formatter()
        
        # Setup handlers
        if enable_console:
            self._setup_console_handler()
        
        if log_file:
            self._setup_file_handler(max_file_size_mb, backup_count)
        
        # Context for correlation
        self._correlation_id: Optional[str] = None
        self._session_id: Optional[str] = None
        self._site_id: Optional[str] = None
        self._environment: Optional[str] = None
    
    def _create_json_formatter(self) -> logging.Formatter:
        """Create JSON formatter for structured logging."""
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = LogEntry(
                    timestamp=datetime.fromtimestamp(record.created).isoformat(),
                    level=record.levelname,
                    category=getattr(record, 'category', LogCategory.SYSTEM.value),
                    component_id=getattr(record, 'component_id', None),
                    message=record.getMessage(),
                    details=getattr(record, 'details', {}),
                    correlation_id=getattr(record, 'correlation_id', None),
                    session_id=getattr(record, 'session_id', None),
                    site_id=getattr(record, 'site_id', None),
                    environment=getattr(record, 'environment', None),
                    execution_context=getattr(record, 'execution_context', {}),
                    error_info=getattr(record, 'error_info', None),
                    performance_metrics=getattr(record, 'performance_metrics', None)
                )
                
                return json.dumps(asdict(log_entry), default=str)
        
        return JsonFormatter()
    
    def _create_plain_formatter(self) -> logging.Formatter:
        """Create plain formatter for console logging."""
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(category)s] - %(message)s'
        )
    
    def _setup_console_handler(self) -> None:
        """Setup console logging handler."""
        handler = logging.StreamHandler(sys.stdout)
        
        if self.enable_json_format:
            handler.setFormatter(self.json_formatter)
        else:
            handler.setFormatter(self.plain_formatter)
        
        self.logger.addHandler(handler)
    
    def _setup_file_handler(self, max_size_mb: int, backup_count: int) -> None:
        """Setup file logging handler with rotation."""
        if not self.log_file:
            return
        
        # Ensure log directory exists
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.handlers.RotatingFileHandler(
            filename=self.log_file,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        # Always use JSON format for file logging
        handler.setFormatter(self.json_formatter)
        self.logger.addHandler(handler)
    
    def set_context(
        self,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        site_id: Optional[str] = None,
        environment: Optional[str] = None
    ) -> None:
        """Set logging context."""
        self._correlation_id = correlation_id
        self._session_id = session_id
        self._site_id = site_id
        self._environment = environment
    
    def _log(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        component_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_info: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[PerformanceMetrics] = None
    ) -> None:
        """Internal logging method."""
        log_record = self.logger.makeRecord(
            name=self.logger.name,
            level=getattr(logging, level.value),
            fn='',
            lno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        
        # Add custom attributes
        log_record.category = category.value
        log_record.component_id = component_id
        log_record.details = details or {}
        log_record.correlation_id = self._correlation_id
        log_record.session_id = self._session_id
        log_record.site_id = self._site_id
        log_record.environment = self._environment
        log_record.execution_context = {
            'logger_name': self.name,
            'log_level': level.value,
            'category': category.value
        }
        log_record.error_info = error_info
        log_record.performance_metrics = asdict(performance_metrics) if performance_metrics else None
        
        self.logger.handle(log_record)
    
    def debug(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        component_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, category, message, component_id, details)
    
    def info(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        component_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, category, message, component_id, details)
    
    def warning(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        component_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, category, message, component_id, details)
    
    def error(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        component_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log error message."""
        error_info = None
        if error:
            error_info = {
                'type': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            }
        
        self._log(LogLevel.ERROR, category, message, component_id, details, error_info)
    
    def critical(
        self,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        component_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log critical message."""
        error_info = None
        if error:
            error_info = {
                'type': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            }
        
        self._log(LogLevel.CRITICAL, category, message, component_id, details, error_info)
    
    def performance(
        self,
        message: str,
        metrics: PerformanceMetrics,
        component_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log performance metrics."""
        self._log(
            LogLevel.INFO,
            LogCategory.PERFORMANCE,
            message,
            component_id,
            details,
            performance_metrics=metrics
        )
    
    def component_operation(
        self,
        operation: str,
        component_id: str,
        success: bool,
        execution_time_ms: float,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log component operation."""
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"Component {operation} {'succeeded' if success else 'failed'}"
        
        log_details = {
            'operation': operation,
            'success': success,
            'execution_time_ms': execution_time_ms
        }
        
        if details:
            log_details.update(details)
        
        if success:
            self._log(level, LogCategory.COMPONENT, message, component_id, log_details)
        else:
            error_info = None
            if error:
                error_info = {
                    'type': type(error).__name__,
                    'message': str(error),
                    'traceback': traceback.format_exc()
                }
            
            self._log(level, LogCategory.COMPONENT, message, component_id, log_details, error_info)
    
    @asynccontextmanager
    async def log_operation(
        self,
        operation: str,
        component_id: Optional[str] = None,
        category: LogCategory = LogCategory.SYSTEM,
        details: Optional[Dict[str, Any]] = None
    ):
        """Context manager for logging operations with timing."""
        start_time = datetime.utcnow()
        
        self.info(
            f"Starting {operation}",
            category=category,
            component_id=component_id,
            details=details
        )
        
        try:
            yield
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            self.info(
                f"Completed {operation}",
                category=category,
                component_id=component_id,
                details={
                    **(details or {}),
                    'execution_time_ms': execution_time,
                    'success': True
                }
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            self.error(
                f"Failed {operation}",
                category=category,
                component_id=component_id,
                details={
                    **(details or {}),
                    'execution_time_ms': execution_time,
                    'success': False
                },
                error=e
            )
            raise


class LoggingManager:
    """Manages multiple structured loggers."""
    
    def __init__(self):
        """Initialize logging manager."""
        self._loggers: Dict[str, StructuredLogger] = {}
        self._global_context = {
            'correlation_id': None,
            'session_id': None,
            'site_id': None,
            'environment': None
        }
    
    def create_logger(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        log_file: Optional[str] = None,
        **kwargs
    ) -> StructuredLogger:
        """
        Create a new structured logger.
        
        Args:
            name: Logger name
            level: Log level
            log_file: Log file path
            **kwargs: Additional logger arguments
            
        Returns:
            Structured logger instance
        """
        if name in self._loggers:
            return self._loggers[name]
        
        logger = StructuredLogger(
            name=name,
            level=level,
            log_file=log_file,
            **kwargs
        )
        
        # Set global context
        logger.set_context(**self._global_context)
        
        self._loggers[name] = logger
        return logger
    
    def get_logger(self, name: str) -> Optional[StructuredLogger]:
        """Get existing logger by name."""
        return self._loggers.get(name)
    
    def set_global_context(
        self,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        site_id: Optional[str] = None,
        environment: Optional[str] = None
    ) -> None:
        """Set global context for all loggers."""
        self._global_context.update({
            'correlation_id': correlation_id,
            'session_id': session_id,
            'site_id': site_id,
            'environment': environment
        })
        
        # Update existing loggers
        for logger in self._loggers.values():
            logger.set_context(**self._global_context)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get logging manager statistics."""
        return {
            'total_loggers': len(self._loggers),
            'logger_names': list(self._loggers.keys()),
            'global_context': self._global_context
        }
    
    async def cleanup(self) -> None:
        """Clean up logging manager resources."""
        for logger in self._loggers.values():
            # Close all file handlers
            for handler in logger.logger.handlers:
                if isinstance(handler, (logging.FileHandler, logging.handlers.RotatingFileHandler)):
                    handler.close()
        
        self._loggers.clear()


# Global logging manager instance
logging_manager = LoggingManager()


def get_logger(name: str, **kwargs) -> StructuredLogger:
    """
    Get or create a structured logger.
    
    Args:
        name: Logger name
        **kwargs: Logger creation arguments
        
    Returns:
        Structured logger instance
    """
    return logging_manager.create_logger(name, **kwargs)


def set_logging_context(**kwargs) -> None:
    """Set global logging context."""
    logging_manager.set_global_context(**kwargs)


# Component logging mixin
class ComponentLoggingMixin:
    """Mixin for adding logging capabilities to components."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger: Optional[StructuredLogger] = None
    
    def _setup_logging(self, component_id: str) -> None:
        """Setup logging for the component."""
        self._logger = get_logger(f"component.{component_id}")
    
    def _log_operation(self, operation: str, message: str, level: str = "info", **kwargs) -> None:
        """Log component operation."""
        if not self._logger:
            return
        
        log_method = getattr(self._logger, level, self._logger.info)
        log_method(
            message,
            category=LogCategory.COMPONENT,
            component_id=getattr(self, 'component_id', None),
            details={'operation': operation, **kwargs}
        )


class LoggingError(Exception):
    """Exception raised when logging operations fail."""
    pass
