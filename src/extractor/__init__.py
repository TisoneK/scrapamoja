"""
Extractor Module - Site-agnostic data extraction utility.

This module provides flexible, site-agnostic extraction of structured data
from HTML elements, JSON objects, and other structured nodes with support for
multiple data types, transformations, and comprehensive error handling.
"""

from .core.extractor import Extractor, ExtractorConfig, ExtractionContext
from .core.rules import (
    ExtractionRule,
    ExtractionResult,
    TransformationRule,
    ValidationError,
    ExtractionType,
    TransformationType,
    DataType,
    ValidationErrorType,
    ErrorSeverity,
)
from .exceptions import (
    ExtractionError,
    ValidationError as ExtractorValidationError,
    ExtractionTimeoutError,
    RuleValidationError,
)

__version__ = "1.0.0"
__all__ = [
    # Main classes
    "Extractor",
    "ExtractorConfig", 
    "ExtractionContext",
    
    # Data models
    "ExtractionRule",
    "ExtractionResult",
    "TransformationRule",
    "ValidationError",
    
    # Enums
    "ExtractionType",
    "TransformationType",
    "DataType",
    "ValidationErrorType",
    "ErrorSeverity",
    
    # Exceptions
    "ExtractionError",
    "ExtractorValidationError",
    "ExtractionTimeoutError",
    "RuleValidationError",
]
