"""
Error handling and logging configuration for the Site Template Integration Framework.

This module provides centralized error handling, logging configuration, and
exception classes for the template framework.
"""

import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import sys


class TemplateError(Exception):
    """Base exception for template-related errors."""
    
    def __init__(self, message: str, template_name: Optional[str] = None, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize template error.
        
        Args:
            message: Error message
            template_name: Name of the template
            error_code: Error code for categorization
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.template_name = template_name
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "template_name": self.template_name,
            "error_code": self.error_code,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "traceback": traceback.format_exc()
        }


class TemplateValidationError(TemplateError):
    """Raised when template validation fails."""
    pass


class TemplateIntegrationError(TemplateError):
    """Raised when template integration fails."""
    pass


class TemplateLoadError(TemplateError):
    """Raised when template loading fails."""
    pass


class SelectorLoadError(TemplateError):
    """Raised when selector loading fails."""
    pass


class ExtractionRuleError(TemplateError):
    """Raised when extraction rule setup fails."""
    pass


class RegistryError(TemplateError):
    """Raised when registry operations fail."""
    pass


class ComplianceError(TemplateError):
    """Raised when compliance checks fail."""
    pass


class ErrorSeverity(Enum):
    """Error severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TemplateLogger:
    """Enhanced logger for template framework with structured logging."""
    
    def __init__(self, name: str, template_name: Optional[str] = None):
        """
        Initialize template logger.
        
        Args:
            name: Logger name
            template_name: Associated template name
        """
        self.logger = logging.getLogger(name)
        self.template_name = template_name
        
        # Configure logger if not already configured
        if not self.logger.handlers:
            self._configure_logger()
    
    def _configure_logger(self) -> None:
        """Configure the logger with structured formatting."""
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)
    
    def _log_structured(self, level: ErrorSeverity, message: str, **kwargs) -> None:
        """Log structured message with additional context."""
        log_data = {
            "template_name": self.template_name,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        # Add structured data to message
        if log_data:
            structured_message = f"{message} | {log_data}"
        else:
            structured_message = message
        
        # Log at appropriate level
        if level == ErrorSeverity.DEBUG:
            self.logger.debug(structured_message)
        elif level == ErrorSeverity.INFO:
            self.logger.info(structured_message)
        elif level == ErrorSeverity.WARNING:
            self.logger.warning(structured_message)
        elif level == ErrorSeverity.ERROR:
            self.logger.error(structured_message)
        elif level == ErrorSeverity.CRITICAL:
            self.logger.critical(structured_message)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log_structured(ErrorSeverity.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log_structured(ErrorSeverity.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log_structured(ErrorSeverity.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log_structured(ErrorSeverity.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self._log_structured(ErrorSeverity.CRITICAL, message, **kwargs)
    
    def log_exception(self, message: str, exception: Exception, **kwargs) -> None:
        """Log exception with full context."""
        if isinstance(exception, TemplateError):
            error_data = exception.to_dict()
        else:
            error_data = {
                "error_type": type(exception).__name__,
                "message": str(exception),
                "traceback": traceback.format_exc()
            }
        
        # Merge with additional kwargs
        error_data.update(kwargs)
        
        self.error(f"{message}: {str(exception)}", **error_data)


class ErrorHandler:
    """Centralized error handler for template framework."""
    
    def __init__(self, logger: Optional[TemplateLogger] = None):
        """
        Initialize error handler.
        
        Args:
            logger: Logger instance for error reporting
        """
        self.logger = logger or TemplateLogger("template_error_handler")
        self.error_counts: Dict[str, int] = {}
        self.error_history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Handle an error with logging and tracking.
        
        Args:
            error: Exception to handle
            context: Additional context information
            reraise: Whether to reraise the exception
            
        Returns:
            Optional[Dict[str, Any]]: Error information
        """
        try:
            # Categorize error
            error_type = type(error).__name__
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            
            # Create error record
            error_record = {
                "error_type": error_type,
                "message": str(error),
                "context": context or {},
                "timestamp": datetime.now().isoformat(),
                "count": self.error_counts[error_type]
            }
            
            # Add to history
            self.error_history.append(error_record)
            if len(self.error_history) > self.max_history:
                self.error_history.pop(0)
            
            # Log the error
            if isinstance(error, TemplateError):
                self.logger.log_exception(
                    f"Template error: {error.message}",
                    error,
                    **error_record
                )
            else:
                self.logger.log_exception(
                    f"Unexpected error: {str(error)}",
                    error,
                    **error_record
                )
            
            # Decide whether to reraise
            if reraise:
                raise error
            
            return error_record
            
        except Exception as handling_error:
            # Error in error handling - last resort
            print(f"CRITICAL: Error in error handling: {handling_error}")
            if reraise and error:
                raise error
            return None
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of all handled errors.
        
        Returns:
            Dict[str, Any]: Error summary
        """
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_types": self.error_counts.copy(),
            "recent_errors": self.error_history[-10:],  # Last 10 errors
            "most_common_error": max(self.error_counts.items(), key=lambda x: x[1])[0] if self.error_counts else None
        }
    
    def clear_history(self) -> None:
        """Clear error history."""
        self.error_history.clear()
        self.error_counts.clear()


class RetryHandler:
    """Handler for retry logic with exponential backoff."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        logger: Optional[TemplateLogger] = None
    ):
        """
        Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries
            backoff_factor: Multiplier for exponential backoff
            logger: Logger instance
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.logger = logger or TemplateLogger("retry_handler")
    
    async def retry_async(
        self,
        func,
        *args,
        retry_on: Optional[List[type]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Retry an async function with exponential backoff.
        
        Args:
            func: Async function to retry
            *args: Function arguments
            retry_on: List of exception types to retry on
            context: Additional context for logging
            **kwargs: Function keyword arguments
            
        Returns:
            Result of the function call
        """
        if retry_on is None:
            retry_on = [Exception]
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    delay = min(self.base_delay * (self.backoff_factor ** (attempt - 1)), self.max_delay)
                    self.logger.info(
                        f"Retry attempt {attempt}/{self.max_retries} after {delay:.2f}s delay",
                        attempt=attempt,
                        max_retries=self.max_retries,
                        delay=delay,
                        **(context or {})
                    )
                    await asyncio.sleep(delay)
                
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(
                        f"Retry successful on attempt {attempt}",
                        attempt=attempt,
                        **(context or {})
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if this exception type should be retried
                should_retry = any(isinstance(e, retry_type) for retry_type in retry_on)
                
                if not should_retry or attempt == self.max_retries:
                    self.logger.error(
                        f"Failed after {attempt + 1} attempts: {str(e)}",
                        attempts=attempt + 1,
                        max_retries=self.max_retries,
                        final_exception=str(e),
                        **(context or {})
                    )
                    raise
                
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {str(e)}",
                    attempt=attempt + 1,
                    error=str(e),
                    **(context or {})
                )
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
    
    def retry_sync(
        self,
        func,
        *args,
        retry_on: Optional[List[type]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Retry a synchronous function with exponential backoff.
        
        Args:
            func: Function to retry
            *args: Function arguments
            retry_on: List of exception types to retry on
            context: Additional context for logging
            **kwargs: Function keyword arguments
            
        Returns:
            Result of the function call
        """
        import time
        
        if retry_on is None:
            retry_on = [Exception]
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    delay = min(self.base_delay * (self.backoff_factor ** (attempt - 1)), self.max_delay)
                    self.logger.info(
                        f"Retry attempt {attempt}/{self.max_retries} after {delay:.2f}s delay",
                        attempt=attempt,
                        max_retries=self.max_retries,
                        delay=delay,
                        **(context or {})
                    )
                    time.sleep(delay)
                
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(
                        f"Retry successful on attempt {attempt}",
                        attempt=attempt,
                        **(context or {})
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if this exception type should be retried
                should_retry = any(isinstance(e, retry_type) for retry_type in retry_on)
                
                if not should_retry or attempt == self.max_retries:
                    self.logger.error(
                        f"Failed after {attempt + 1} attempts: {str(e)}",
                        attempts=attempt + 1,
                        max_retries=self.max_retries,
                        final_exception=str(e),
                        **(context or {})
                    )
                    raise
                
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {str(e)}",
                    attempt=attempt + 1,
                    error=str(e),
                    **(context or {})
                )
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception


# Global error handler instance
_global_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_error(error: Exception, context: Optional[Dict[str, Any]] = None, reraise: bool = False) -> Optional[Dict[str, Any]]:
    """
    Handle an error using the global error handler.
    
    Args:
        error: Exception to handle
        context: Additional context information
        reraise: Whether to reraise the exception
        
    Returns:
        Optional[Dict[str, Any]]: Error information
    """
    return get_error_handler().handle_error(error, context, reraise)


def get_logger(name: str, template_name: Optional[str] = None) -> TemplateLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name
        template_name: Associated template name
        
    Returns:
        TemplateLogger: Configured logger instance
    """
    return TemplateLogger(name, template_name)
