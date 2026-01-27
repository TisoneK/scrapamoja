"""
Browser-specific exceptions for error handling.

This module defines custom exceptions for browser lifecycle management
with structured error information and correlation IDs.
"""

from typing import Dict, Any, Optional


class BrowserError(Exception):
    """Base exception for browser-related errors."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class BrowserSessionError(BrowserError):
    """Raised when browser session operations fail."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class BrowserManagerError(BrowserError):
    """Raised when browser manager operations fail."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class ResourceMonitoringError(BrowserError):
    """Raised when resource monitoring operations fail."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class BrowserConfigurationError(BrowserError):
    """Raised when browser configuration is invalid."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class StateCorruptionError(BrowserError):
    """Raised when browser state is corrupted or unreadable."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class ConfigurationError(BrowserError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, component: str, setting: str, message: str):
        error_code = f"{component}_{setting}_config_error"
        super().__init__(error_code, message, {"component": component, "setting": setting})
        self.component = component
        self.setting = setting


class ResourceExhaustionError(BrowserError):
    """Raised when system resources are exhausted."""
    
    def __init__(self, resource_type: str, current_usage: float, threshold: float, details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type} exhausted: {current_usage:.2f}% exceeds threshold {threshold:.2f}%"
        error_details = details or {}
        error_details.update({
            "resource_type": resource_type,
            "current_usage": current_usage,
            "threshold": threshold
        })
        super().__init__("resource_exhaustion", message, error_details)
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.threshold = threshold


class MonitoringError(BrowserError):
    """Raised when resource monitoring operations fail."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)
        self.error_code = error_code
        self.message = message
        self.details = details or {}

class ResourceExhaustionError(BrowserError):
    """Raised when resource limits are exceeded."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)
        self.error_code = error_code
        self.message = message
        self.details = details or {}


class MonitoringError(BrowserError):
    """Raised when monitoring operations fail."""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)
        self.error_code = error_code
        self.message = message
        self.details = details or {}
