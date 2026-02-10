"""
Exception classes for the YAML selector system.

This module defines custom exceptions for different types of errors that can occur
during YAML selector loading, validation, and registration.
"""

from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class SelectorError(Exception):
    """Base exception for all selector-related errors."""
    
    def __init__(self, message: str, selector_id: Optional[str] = None, 
                 error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.selector_id = selector_id
        self.error_code = error_code
        self.details = details or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "selector_id": self.selector_id,
            "error_code": self.error_code,
            "details": self.details
        }
    
    def __str__(self) -> str:
        """String representation of the exception."""
        base_msg = self.message
        if self.selector_id:
            base_msg = f"[{self.selector_id}] {base_msg}"
        if self.error_code:
            base_msg = f"{self.error_code}: {base_msg}"
        return base_msg


class SelectorLoadingError(SelectorError):
    """Exception raised when loading selectors fails."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 selector_id: Optional[str] = None, loading_errors: Optional[List[str]] = None):
        super().__init__(message, selector_id, "SELECTOR_LOADING_ERROR")
        self.file_path = file_path
        self.loading_errors = loading_errors or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        result = super().to_dict()
        result.update({
            "file_path": self.file_path,
            "loading_errors": self.loading_errors
        })
        return result


class SelectorValidationError(SelectorError):
    """Exception raised when selector validation fails."""
    
    def __init__(self, message: str, selector_id: Optional[str] = None, 
                 validation_errors: Optional[List[str]] = None, field_path: Optional[str] = None):
        super().__init__(message, selector_id, "SELECTOR_VALIDATION_ERROR")
        self.validation_errors = validation_errors or []
        self.field_path = field_path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        result = super().to_dict()
        result.update({
            "validation_errors": self.validation_errors,
            "field_path": self.field_path
        })
        return result


class SelectorRegistrationError(SelectorError):
    """Exception raised when selector registration fails."""
    
    def __init__(self, message: str, selector_id: Optional[str] = None, 
                 existing_selector_id: Optional[str] = None):
        super().__init__(message, selector_id, "SELECTOR_REGISTRATION_ERROR")
        self.existing_selector_id = existing_selector_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        result = super().to_dict()
        result.update({
            "existing_selector_id": self.existing_selector_id
        })
        return result


class SelectorConfigurationError(SelectorError):
    """Exception raised when selector configuration is invalid."""
    
    def __init__(self, message: str, selector_id: Optional[str] = None, 
                 config_key: Optional[str] = None, config_value: Optional[Any] = None):
        super().__init__(message, selector_id, "SELECTOR_CONFIGURATION_ERROR")
        self.config_key = config_key
        self.config_value = config_value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        result = super().to_dict()
        result.update({
            "config_key": self.config_key,
            "config_value": self.config_value
        })
        return result


class SelectorFileError(SelectorError):
    """Exception raised when file operations fail."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 operation: Optional[str] = None, original_error: Optional[Exception] = None):
        super().__init__(message, error_code="SELECTOR_FILE_ERROR")
        self.file_path = file_path
        self.operation = operation
        self.original_error = original_error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        result = super().to_dict()
        result.update({
            "file_path": self.file_path,
            "operation": self.operation,
            "original_error": str(self.original_error) if self.original_error else None
        })
        return result


class SelectorCacheError(SelectorError):
    """Exception raised when cache operations fail."""
    
    def __init__(self, message: str, cache_key: Optional[str] = None, 
                 operation: Optional[str] = None):
        super().__init__(message, error_code="SELECTOR_CACHE_ERROR")
        self.cache_key = cache_key
        self.operation = operation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        result = super().to_dict()
        result.update({
            "cache_key": self.cache_key,
            "operation": self.operation
        })
        return result


class SelectorPerformanceError(SelectorError):
    """Exception raised when performance thresholds are exceeded."""
    
    def __init__(self, message: str, operation: Optional[str] = None, 
                 duration_ms: Optional[float] = None, threshold_ms: Optional[float] = None):
        super().__init__(message, error_code="SELECTOR_PERFORMANCE_ERROR")
        self.operation = operation
        self.duration_ms = duration_ms
        self.threshold_ms = threshold_ms
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        result = super().to_dict()
        result.update({
            "operation": self.operation,
            "duration_ms": self.duration_ms,
            "threshold_ms": self.threshold_ms
        })
        return result


class SelectorDependencyError(SelectorError):
    """Exception raised when selector dependencies are not met."""
    
    def __init__(self, message: str, selector_id: Optional[str] = None, 
                 missing_dependencies: Optional[List[str]] = None):
        super().__init__(message, selector_id, "SELECTOR_DEPENDENCY_ERROR")
        self.missing_dependencies = missing_dependencies or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        result = super().to_dict()
        result.update({
            "missing_dependencies": self.missing_dependencies
        })
        return result


class SelectorHotReloadError(SelectorError):
    """Exception raised when hot-reloading fails."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 reload_errors: Optional[List[str]] = None):
        super().__init__(message, error_code="SELECTOR_HOT_RELOAD_ERROR")
        self.file_path = file_path
        self.reload_errors = reload_errors or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        result = super().to_dict()
        result.update({
            "file_path": self.file_path,
            "reload_errors": self.reload_errors
        })
        return result


# Utility functions for exception handling
def handle_selector_error(func):
    """Decorator to handle selector exceptions consistently."""
    
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SelectorError:
            # Re-raise selector exceptions as-is
            raise
        except Exception as e:
            # Wrap other exceptions in SelectorError
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise SelectorError(
                message=f"Unexpected error: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                details={"function": func.__name__, "original_error": str(e)}
            ) from e
    
    return wrapper


def log_selector_error(error: SelectorError, context: Optional[str] = None):
    """Log selector error with context information."""
    error_dict = error.to_dict()
    
    if context:
        error_dict["context"] = context
    
    if error.error_code in ["SELECTOR_LOADING_ERROR", "SELECTOR_VALIDATION_ERROR"]:
        logger.error(f"Selector error: {error}")
    elif error.error_code in ["SELECTOR_PERFORMANCE_ERROR"]:
        logger.warning(f"Performance issue: {error}")
    else:
        logger.info(f"Selector issue: {error}")
    
    # Log detailed error information for debugging
    logger.debug(f"Error details: {error_dict}")


def create_file_error(file_path: str, operation: str, original_error: Exception) -> SelectorFileError:
    """Create a standardized file error."""
    return SelectorFileError(
        message=f"File operation '{operation}' failed for '{file_path}': {str(original_error)}",
        file_path=file_path,
        operation=operation,
        original_error=original_error
    )


def create_validation_error(selector_id: str, errors: List[str], field_path: Optional[str] = None) -> SelectorValidationError:
    """Create a standardized validation error."""
    return SelectorValidationError(
        message=f"Selector validation failed: {'; '.join(errors)}",
        selector_id=selector_id,
        validation_errors=errors,
        field_path=field_path
    )


def create_loading_error(file_path: str, errors: List[str]) -> SelectorLoadingError:
    """Create a standardized loading error."""
    return SelectorLoadingError(
        message=f"Failed to load selectors from '{file_path}': {'; '.join(errors)}",
        file_path=file_path,
        loading_errors=errors
    )


def create_registration_error(selector_id: str, existing_id: Optional[str] = None) -> SelectorRegistrationError:
    """Create a standardized registration error."""
    message = f"Failed to register selector '{selector_id}'"
    if existing_id:
        message += f" (conflicts with existing selector '{existing_id}')"
    
    return SelectorRegistrationError(
        message=message,
        selector_id=selector_id,
        existing_selector_id=existing_id
    )
