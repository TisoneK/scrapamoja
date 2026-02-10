"""
Custom exceptions for the extractor module.

This module defines the exception hierarchy used throughout the extractor
to provide clear error handling and debugging information.
"""

from typing import Any, Dict, Optional
from datetime import datetime


class ExtractionError(Exception):
    """Base exception for extraction errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        rule_name: Optional[str] = None,
        element_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.rule_name = rule_name
        self.element_info = element_info or {}
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        super().__init__(message)
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "rule_name": self.rule_name,
            "element_info": self.element_info,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }


class ValidationError(ExtractionError):
    """Raised when validation fails."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "VALID_001",
        field_path: Optional[str] = None,
        actual_value: Optional[Any] = None,
        expected_value: Optional[Any] = None,
        **kwargs
    ):
        self.field_path = field_path
        self.actual_value = actual_value
        self.expected_value = expected_value
        super().__init__(message, error_code, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "field_path": self.field_path,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
        })
        return result


class ExtractionTimeoutError(ExtractionError):
    """Raised when extraction times out."""
    
    def __init__(
        self,
        message: str = "Extraction operation timed out",
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        self.timeout_seconds = timeout_seconds
        super().__init__(message, "EXTRACT_005", **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["timeout_seconds"] = self.timeout_seconds
        return result


class RuleValidationError(ExtractionError):
    """Raised when rule validation fails."""
    
    def __init__(
        self,
        message: str,
        rule_name: Optional[str] = None,
        validation_errors: Optional[list] = None,
        **kwargs
    ):
        self.validation_errors = validation_errors or []
        super().__init__(message, "RULE_001", rule_name=rule_name, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["validation_errors"] = self.validation_errors
        return result


class ElementNotFoundError(ExtractionError):
    """Raised when an element cannot be found."""
    
    def __init__(
        self,
        message: str = "Element not found",
        selector: Optional[str] = None,
        **kwargs
    ):
        self.selector = selector
        super().__init__(message, "EXTRACT_001", **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["selector"] = self.selector
        return result


class PatternNotFoundError(ExtractionError):
    """Raised when a regex pattern is not found in the content."""
    
    def __init__(
        self,
        message: str = "Pattern not found",
        pattern: Optional[str] = None,
        content_sample: Optional[str] = None,
        **kwargs
    ):
        self.pattern = pattern
        self.content_sample = content_sample
        super().__init__(message, "EXTRACT_002", **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["pattern"] = self.pattern
        result["content_sample"] = self.content_sample
        return result


class TypeConversionError(ExtractionError):
    """Raised when type conversion fails."""
    
    def __init__(
        self,
        message: str = "Type conversion failed",
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        self.source_type = source_type
        self.target_type = target_type
        self.value = value
        super().__init__(message, "EXTRACT_003", **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "source_type": self.source_type,
            "target_type": self.target_type,
            "value": self.value,
        })
        return result
