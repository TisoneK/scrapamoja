"""
Navigation system exceptions

Exception hierarchy for Navigation & Routing Intelligence system following
Constitution Principle V - Production Resilience.
"""

from typing import Dict, Any, Optional


class NavigationException(Exception):
    """Base exception for navigation system"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str, 
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging"""
        return {
            'exception_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context
        }


class RouteDiscoveryError(NavigationException):
    """Exception for route discovery failures"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "ROUTE_DISCOVERY_ERROR",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, context)


class PathPlanningError(NavigationException):
    """Exception for path planning failures"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "PATH_PLANNING_ERROR",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, context)


class NavigationExecutionError(NavigationException):
    """Exception for navigation execution failures"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "NAVIGATION_EXECUTION_ERROR",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, context)


class ContextManagementError(NavigationException):
    """Exception for context management failures"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "CONTEXT_MANAGEMENT_ERROR",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, context)


class RouteOptimizationError(NavigationException):
    """Exception for route optimization failures"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "ROUTE_OPTIMIZATION_ERROR",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, context)


class ConfigurationError(NavigationException):
    """Exception for configuration errors"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "CONFIGURATION_ERROR",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, context)


class IntegrationError(NavigationException):
    """Exception for integration failures with external systems"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "INTEGRATION_ERROR",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, context)


class ValidationError(NavigationException):
    """Exception for data validation failures"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "VALIDATION_ERROR",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, context)


class TimeoutError(NavigationException):
    """Exception for operation timeouts"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "TIMEOUT_ERROR",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, context)


class DetectionTriggeredError(NavigationException):
    """Exception when anti-bot detection is triggered"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "DETECTION_TRIGGERED",
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, context)
