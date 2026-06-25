"""
Error Data Model

Detailed error information for failed selector operations
following the data model specification.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class ErrorData(BaseModel):
    """
    Detailed error information for failed selector operations.
    
    Contains comprehensive error data including error type, message,
    stack trace, retry information, and recovery status.
    """
    
    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Human-readable error message")
    stack_trace: Optional[str] = Field(None, description="Technical stack trace")
    retry_attempts: Optional[int] = Field(0, description="Number of retry attempts made")
    fallback_attempts: Optional[int] = Field(0, description="Number of fallback attempts")
    recovery_successful: Optional[bool] = Field(None, description="Whether recovery was successful")
    
    @validator('error_type')
    def validate_error_type(cls, v):
        """Validate error type is not empty."""
        if not v or not v.strip():
            raise ValueError("error_type must be a non-empty string")
        return v.strip()
    
    @validator('error_message')
    def validate_error_message(cls, v):
        """Validate error message is not empty."""
        if not v or not v.strip():
            raise ValueError("error_message must be a non-empty string")
        return v.strip()
    
    @validator('retry_attempts')
    def validate_retry_attempts(cls, v):
        """Validate retry attempts is non-negative."""
        if v is not None:
            if not isinstance(v, int):
                raise ValueError("retry_attempts must be an integer")
            if v < 0:
                raise ValueError("retry_attempts must be non-negative")
        return v or 0
    
    @validator('fallback_attempts')
    def validate_fallback_attempts(cls, v):
        """Validate fallback attempts is non-negative."""
        if v is not None:
            if not isinstance(v, int):
                raise ValueError("fallback_attempts must be an integer")
            if v < 0:
                raise ValueError("fallback_attempts must be non-negative")
        return v or 0
    
    def is_timeout_error(self) -> bool:
        """
        Check if this is a timeout error.
        
        Returns:
            True if error type indicates timeout
        """
        timeout_types = ["timeout", "time_out", "time-out", "deadline", "deadlineexceeded"]
        return any(timeout_type in self.error_type.lower() for timeout_type in timeout_types)
    
    def is_network_error(self) -> bool:
        """
        Check if this is a network error.
        
        Returns:
            True if error type indicates network issue
        """
        network_types = ["network", "connection", "http", "request", "socket", "dns"]
        return any(network_type in self.error_type.lower() for network_type in network_types)
    
    def is_parsing_error(self) -> bool:
        """
        Check if this is a parsing error.
        
        Returns:
            True if error type indicates parsing issue
        """
        parsing_types = ["parse", "syntax", "format", "invalid", "malformed"]
        return any(parsing_type in self.error_type.lower() for parsing_type in parsing_types)
    
    def is_selector_error(self) -> bool:
        """
        Check if this is a selector-specific error.
        
        Returns:
            True if error type indicates selector issue
        """
        selector_types = ["selector", "element", "dom", "xpath", "css", "not_found"]
        return any(selector_type in self.error_type.lower() for selector_type in selector_types)
    
    def is_recoverable(self) -> bool:
        """
        Check if the error is potentially recoverable.
        
        Returns:
            True if error might be recoverable
        """
        recoverable_types = ["timeout", "network", "connection", "temporary", "retry"]
        return any(recoverable_type in self.error_type.lower() for recoverable_types in recoverable_types)
    
    def is_critical(self) -> bool:
        """
        Check if the error is critical.
        
        Returns:
            True if error is critical
        """
        critical_types = ["critical", "fatal", "system", "memory", "crash"]
        return any(critical_type in self.error_type.lower() for critical_type in critical_types)
    
    def has_retries(self) -> bool:
        """
        Check if retries were attempted.
        
        Returns:
            True if retry attempts were made
        """
        return (self.retry_attempts or 0) > 0
    
    def has_fallbacks(self) -> bool:
        """
        Check if fallback attempts were made.
        
        Returns:
            True if fallback attempts were made
        """
        return (self.fallback_attempts or 0) > 0
    
    def was_recovered(self) -> bool:
        """
        Check if recovery was successful.
        
        Returns:
            True if recovery was successful
        """
        return self.recovery_successful is True
    
    def failed_recovery(self) -> bool:
        """
        Check if recovery failed.
        
        Returns:
            True if recovery failed
        """
        return self.recovery_successful is False
    
    def get_total_attempts(self) -> int:
        """
        Get total number of attempts (original + retries + fallbacks).
        
        Returns:
            Total number of attempts
        """
        return 1 + (self.retry_attempts or 0) + (self.fallback_attempts or 0)
    
    def get_error_severity(self) -> str:
        """
        Get error severity based on type and recovery status.
        
        Returns:
            Error severity (low, medium, high, critical)
        """
        if self.is_critical():
            return "critical"
        elif self.failed_recovery():
            return "high"
        elif self.is_recoverable():
            return "medium"
        else:
            return "low"
    
    def get_error_category(self) -> str:
        """
        Get error category based on type.
        
        Returns:
            Error category string
        """
        if self.is_timeout_error():
            return "timeout"
        elif self.is_network_error():
            return "network"
        elif self.is_parsing_error():
            return "parsing"
        elif self.is_selector_error():
            return "selector"
        else:
            return "unknown"
    
    def should_retry(self) -> bool:
        """
        Determine if the error should be retried.
        
        Returns:
            True if error should be retried
        """
        return (
            self.is_recoverable() and
            not self.has_retries() and
            not self.is_critical()
        )
    
    def should_use_fallback(self) -> bool:
        """
        Determine if fallback should be used.
        
        Returns:
            True if fallback should be used
        """
        return (
            self.is_selector_error() and
            not self.has_fallbacks() and
            not self.was_recovered()
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary with all fields."""
        return {
            "error_type": self.error_type,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "retry_attempts": self.retry_attempts or 0,
            "fallback_attempts": self.fallback_attempts or 0,
            "recovery_successful": self.recovery_successful
        }
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
