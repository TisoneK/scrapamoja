"""
Resilience Module Exception Classes

Base exceptions for all resilience-related errors with context and correlation tracking.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid


class ResilienceException(Exception):
    """Base exception for all resilience-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.correlation_id = correlation_id or str(uuid.uuid4())
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message} (correlation: {self.correlation_id})"


# Checkpoint Exceptions
class CheckpointCreationError(ResilienceException):
    """Raised when checkpoint creation fails."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CHECKPOINT_CREATION_ERROR", context)


class CheckpointCorruptionError(ResilienceException):
    """Raised when checkpoint corruption is detected."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CHECKPOINT_CORRUPTION_ERROR", context)


class CheckpointNotFoundError(ResilienceException):
    """Raised when checkpoint is not found."""
    
    def __init__(self, checkpoint_id: str, context: Optional[Dict[str, Any]] = None):
        message = f"Checkpoint not found: {checkpoint_id}"
        context = context or {}
        context["checkpoint_id"] = checkpoint_id
        super().__init__(message, "CHECKPOINT_NOT_FOUND_ERROR", context)


class CheckpointValidationError(ResilienceException):
    """Raised when checkpoint validation fails."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CHECKPOINT_VALIDATION_ERROR", context)


# Retry Exceptions
class MaxRetriesExceededError(ResilienceException):
    """Raised when maximum retry attempts are exceeded."""
    
    def __init__(self, attempts: int, context: Optional[Dict[str, Any]] = None):
        message = f"Maximum retry attempts exceeded: {attempts}"
        context = context or {}
        context["max_attempts"] = attempts
        super().__init__(message, "MAX_RETRIES_EXCEEDED_ERROR", context)


class PermanentFailureError(ResilienceException):
    """Raised when a permanent failure is detected."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "PERMANENT_FAILURE_ERROR", context)


class RetryPolicyNotFoundError(ResilienceException):
    """Raised when retry policy is not found."""
    
    def __init__(self, policy_id: str, context: Optional[Dict[str, Any]] = None):
        message = f"Retry policy not found: {policy_id}"
        context = context or {}
        context["policy_id"] = policy_id
        super().__init__(message, "RETRY_POLICY_NOT_FOUND_ERROR", context)


class RetryConfigurationError(ResilienceException):
    """Raised when retry configuration is invalid."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RETRY_CONFIGURATION_ERROR", context)


# Resource Exceptions
class ResourceThresholdExceededError(ResilienceException):
    """Raised when resource threshold is exceeded."""
    
    def __init__(self, threshold: str, value: float, limit: float, context: Optional[Dict[str, Any]] = None):
        message = f"Resource threshold exceeded: {threshold}={value} (limit={limit})"
        context = context or {}
        context.update({"threshold": threshold, "value": value, "limit": limit})
        super().__init__(message, "RESOURCE_THRESHOLD_EXCEEDED_ERROR", context)


class ResourceMonitoringError(ResilienceException):
    """Raised when resource monitoring fails."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RESOURCE_MONITORING_ERROR", context)


class ResourceCleanupError(ResilienceException):
    """Raised when resource cleanup fails."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RESOURCE_CLEANUP_ERROR", context)


class ResourceThresholdNotFoundError(ResilienceException):
    """Raised when resource threshold configuration is not found."""
    
    def __init__(self, threshold_id: str, context: Optional[Dict[str, Any]] = None):
        message = f"Resource threshold not found: {threshold_id}"
        context = context or {}
        context["threshold_id"] = threshold_id
        super().__init__(message, "RESOURCE_THRESHOLD_NOT_FOUND_ERROR", context)


# Abort Exceptions
class AbortPolicyNotFoundError(ResilienceException):
    """Raised when abort policy is not found."""
    
    def __init__(self, policy_id: str, context: Optional[Dict[str, Any]] = None):
        message = f"Abort policy not found: {policy_id}"
        context = context or {}
        context["policy_id"] = policy_id
        super().__init__(message, "ABORT_POLICY_NOT_FOUND_ERROR", context)


class AbortExecutionError(ResilienceException):
    """Raised when abort execution fails."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "ABORT_EXECUTION_ERROR", context)


class AbortConfigurationError(ResilienceException):
    """Raised when abort configuration is invalid."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "ABORT_CONFIGURATION_ERROR", context)


# General Resilience Exceptions
class ConfigurationError(ResilienceException):
    """Raised when resilience configuration is invalid."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIGURATION_ERROR", context)


class ValidationError(ResilienceException):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", context)


class IntegrationError(ResilienceException):
    """Raised when integration with external systems fails."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, "INTEGRATION_ERROR", context)
