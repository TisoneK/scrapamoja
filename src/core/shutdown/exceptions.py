"""
Exception classes for the shutdown system.

Provides specific exceptions for different types of shutdown failures
to enable proper error handling and reporting.
"""


class ShutdownError(Exception):
    """Base exception for shutdown-related errors."""
    
    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)
        self.cause = cause
        self.message = message
    
    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class TimeoutError(ShutdownError):
    """Exception raised when cleanup operations exceed timeout."""
    
    def __init__(self, message: str, timeout_seconds: float, cause: Exception = None):
        super().__init__(message, cause)
        self.timeout_seconds = timeout_seconds
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        return f"{base_msg} (timeout: {self.timeout_seconds}s)"
