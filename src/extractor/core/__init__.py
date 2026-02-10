"""
Core extractor components.

This package contains the main extraction logic, data models,
and configuration systems for the extractor module.
"""

from .extractor import Extractor, ExtractorConfig, ExtractionContext
from .rules import (
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
from .validators import ValidationResult, ValidationEngine
from .transformers import TransformationEngine

__all__ = [
    # Main extractor
    "Extractor",
    "ExtractorConfig",
    "ExtractionContext",
    
    # Data models and enums
    "ExtractionRule",
    "ExtractionResult",
    "TransformationRule",
    "ValidationError",
    "ExtractionType",
    "TransformationType",
    "DataType",
    "ValidationErrorType",
    "ErrorSeverity",
    
    # Processing engines
    "ValidationResult",
    "ValidationEngine",
    "TransformationEngine",
]
