"""
Base Telemetry Exception Classes

Exception hierarchy for the telemetry system following Constitution
principles for structured error handling and graceful degradation.
"""

from typing import Optional, Dict, Any


class TelemetryError(Exception):
    """
    Base exception for all telemetry system errors.
    
    All telemetry exceptions should inherit from this base class
    to enable consistent error handling and logging.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "TEL-000"
        self.correlation_id = correlation_id
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "context": self.context
        }


class TelemetryConfigurationError(TelemetryError):
    """
    Exception raised for telemetry configuration errors.
    
    Error codes: TEL-100 to TEL-199
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "TEL-100",
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, correlation_id, context)


class TelemetryStorageError(TelemetryError):
    """
    Exception raised for telemetry storage operations.
    
    Error codes: TEL-200 to TEL-299
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "TEL-200",
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, correlation_id, context)


class TelemetryCollectionError(TelemetryError):
    """
    Exception raised during telemetry data collection.
    
    Error codes: TEL-300 to TEL-399
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "TEL-300",
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, correlation_id, context)


class TelemetryProcessingError(TelemetryError):
    """
    Exception raised during telemetry data processing.
    
    Error codes: TEL-400 to TEL-499
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "TEL-400",
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, correlation_id, context)


class TelemetryAlertingError(TelemetryError):
    """
    Exception raised during alert generation or management.
    
    Error codes: TEL-500 to TEL-599
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "TEL-500",
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, correlation_id, context)


class TelemetryReportingError(TelemetryError):
    """
    Exception raised during report generation.
    
    Error codes: TEL-600 to TEL-699
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "TEL-600",
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, correlation_id, context)


class TelemetryValidationError(TelemetryError):
    """
    Exception raised during data validation.
    
    Error codes: TEL-700 to TEL-799
    """
    
    def __init__(
        self,
        message: str,
        validation_errors: Optional[list] = None,
        error_code: str = "TEL-700",
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, correlation_id, context)
        self.validation_errors = validation_errors or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary including validation errors."""
        base_dict = super().to_dict()
        base_dict["validation_errors"] = self.validation_errors
        return base_dict


class TelemetryBufferError(TelemetryError):
    """
    Exception raised during buffer operations.
    
    Error codes: TEL-800 to TEL-899
    """
    
    def __init__(
        self,
        message: str,
        buffer_size: Optional[int] = None,
        current_count: Optional[int] = None,
        error_code: str = "TEL-800",
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, correlation_id, context)
        self.buffer_size = buffer_size
        self.current_count = current_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary including buffer info."""
        base_dict = super().to_dict()
        if self.buffer_size is not None:
            base_dict["buffer_size"] = self.buffer_size
        if self.current_count is not None:
            base_dict["current_count"] = self.current_count
        return base_dict


class TelemetryIntegrationError(TelemetryError):
    """
    Exception raised during integration with other systems.
    
    Error codes: TEL-900 to TEL-999
    """
    
    def __init__(
        self,
        message: str,
        integration_point: Optional[str] = None,
        error_code: str = "TEL-900",
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, correlation_id, context)
        self.integration_point = integration_point
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary including integration point."""
        base_dict = super().to_dict()
        if self.integration_point:
            base_dict["integration_point"] = self.integration_point
        return base_dict


# Specific error instances with predefined error codes

class StorageUnavailableError(TelemetryStorageError):
    """Storage system is unavailable."""
    
    def __init__(self, storage_type: str, correlation_id: Optional[str] = None):
        super().__init__(
            f"Storage system unavailable: {storage_type}",
            error_code="TEL-201",
            correlation_id=correlation_id,
            context={"storage_type": storage_type}
        )


class BufferOverflowError(TelemetryBufferError):
    """Telemetry buffer has overflowed."""
    
    def __init__(self, buffer_size: int, current_count: int, correlation_id: Optional[str] = None):
        super().__init__(
            f"Telemetry buffer overflow: {current_count}/{buffer_size}",
            buffer_size=buffer_size,
            current_count=current_count,
            error_code="TEL-801",
            correlation_id=correlation_id
        )


class InvalidEventDataError(TelemetryValidationError):
    """Invalid telemetry event data."""
    
    def __init__(self, validation_errors: list, correlation_id: Optional[str] = None):
        super().__init__(
            f"Invalid telemetry event data: {len(validation_errors)} validation errors",
            validation_errors=validation_errors,
            error_code="TEL-701",
            correlation_id=correlation_id
        )


class PerformanceThresholdExceededError(TelemetryAlertingError):
    """Performance threshold has been exceeded."""
    
    def __init__(
        self,
        selector_name: str,
        metric: str,
        value: float,
        threshold: float,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            f"Performance threshold exceeded for {selector_name}: {metric}={value} > {threshold}",
            error_code="TEL-501",
            correlation_id=correlation_id,
            context={
                "selector_name": selector_name,
                "metric": metric,
                "value": value,
                "threshold": threshold
            }
        )


class CorrelationIdError(TelemetryIntegrationError):
    """Error with correlation ID generation or management."""
    
    def __init__(self, operation: str, correlation_id: Optional[str] = None):
        super().__init__(
            f"Correlation ID error during {operation}",
            integration_point="correlation_id",
            error_code="TEL-901",
            correlation_id=correlation_id,
            context={"operation": operation}
        )


def is_recoverable_error(error: Exception) -> bool:
    """
    Determine if a telemetry error is recoverable.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error is recoverable, False otherwise
    """
    recoverable_errors = (
        TelemetryStorageError,
        TelemetryBufferError,
        TelemetryCollectionError,
        TelemetryProcessingError
    )
    
    return isinstance(error, recoverable_errors)


def is_critical_error(error: Exception) -> bool:
    """
    Determine if a telemetry error is critical.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error is critical, False otherwise
    """
    critical_errors = (
        TelemetryConfigurationError,
        TelemetryValidationError,
        TelemetryIntegrationError
    )
    
    return isinstance(error, critical_errors)
