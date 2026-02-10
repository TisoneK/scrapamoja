"""
Data models and enums for the extractor module.

This module defines the core data structures used throughout the extractor
including extraction rules, results, transformations, and validation errors.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ExtractionType(str, Enum):
    """Types of extraction operations."""
    TEXT = "text"
    ATTRIBUTE = "attribute"
    REGEX = "regex"
    LIST = "list"
    NESTED = "nested"


class TransformationType(str, Enum):
    """Types of data transformations."""
    TRIM = "trim"
    CLEAN = "clean"
    NORMALIZE = "normalize"
    LOWERCASE = "lowercase"
    UPPERCASE = "uppercase"
    REMOVE_WHITESPACE = "remove_whitespace"
    EXTRACT_NUMBERS = "extract_numbers"
    EXTRACT_EMAILS = "extract_emails"
    EXTRACT_PHONES = "extract_phones"


class DataType(str, Enum):
    """Target data types for extracted values."""
    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    LIST = "list"
    DICT = "dict"


class ValidationErrorType(str, Enum):
    """Types of validation errors."""
    TYPE_MISMATCH = "type_mismatch"
    PATTERN_MISMATCH = "pattern_mismatch"
    LENGTH_INVALID = "length_invalid"
    VALUE_OUT_OF_RANGE = "value_out_of_range"
    REQUIRED_FIELD_MISSING = "required_field_missing"
    INVALID_FORMAT = "invalid_format"
    VALIDATION_RULE_FAILED = "validation_rule_failed"


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ExtractionRule(BaseModel):
    """Defines extraction rules for a specific data field."""
    
    # Core identification
    name: str = Field(..., description="Unique name for this extraction rule")
    field_path: str = Field(..., description="Path to the field in output structure")
    
    # Extraction targets
    extraction_type: ExtractionType = Field(..., description="Type of extraction to perform")
    attribute_name: Optional[str] = Field(None, description="Attribute name for attribute extraction")
    
    # Pattern matching
    regex_pattern: Optional[str] = Field(None, description="Regex pattern for pattern extraction")
    regex_flags: int = Field(0, description="Regex flags (re.IGNORECASE, etc.)")
    
    # Data transformation
    transformations: List[TransformationType] = Field(default_factory=list, description="Transformations to apply")
    
    # Type conversion
    target_type: DataType = Field(DataType.TEXT, description="Target data type")
    date_format: Optional[str] = Field(None, description="Date format string for parsing")
    
    # Fallback handling
    default_value: Any = Field(None, description="Default value if extraction fails")
    required: bool = Field(False, description="Whether this field is required")
    
    # Validation
    validation_pattern: Optional[str] = Field(None, description="Validation regex pattern")
    min_length: Optional[int] = Field(None, description="Minimum length for text")
    max_length: Optional[int] = Field(None, description="Maximum length for text")
    min_value: Optional[Union[int, float]] = Field(None, description="Minimum value for numbers")
    max_value: Optional[Union[int, float]] = Field(None, description="Maximum value for numbers")
    
    # Metadata
    description: Optional[str] = Field(None, description="Human-readable description")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    
    class Config:
        use_enum_values = True


class ExtractionResult(BaseModel):
    """Result of an extraction operation with metadata."""
    
    # Core result
    value: Any = Field(..., description="Extracted value")
    success: bool = Field(..., description="Whether extraction was successful")
    
    # Metadata
    rule_name: str = Field(..., description="Name of the rule used")
    extraction_type: ExtractionType = Field(..., description="Type of extraction performed")
    target_type: DataType = Field(..., description="Target data type")
    
    # Performance metrics
    extraction_time_ms: float = Field(..., description="Time taken for extraction in milliseconds")
    transformations_applied: List[TransformationType] = Field(default_factory=list, description="Transformations applied")
    
    # Error handling
    errors: List[str] = Field(default_factory=list, description="Errors encountered during extraction")
    warnings: List[str] = Field(default_factory=list, description="Warnings during extraction")
    used_default: bool = Field(False, description="Whether default value was used")
    
    # Validation
    validation_passed: bool = Field(True, description="Whether validation passed")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")
    
    # Context
    element_info: Optional[Dict[str, Any]] = Field(None, description="Information about the source element")
    extraction_context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    
    # Timestamps
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="When extraction was performed")
    
    class Config:
        use_enum_values = True


class TransformationRule(BaseModel):
    """Defines data transformation rules."""
    
    # Core transformation
    transformation_type: TransformationType = Field(..., description="Type of transformation")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for transformation")
    
    # Conditional application
    condition: Optional[str] = Field(None, description="Condition for applying transformation")
    apply_if_success: bool = Field(True, description="Apply only if extraction was successful")
    
    # Ordering
    order: int = Field(0, description="Order of application (lower = earlier)")
    
    # Metadata
    description: Optional[str] = Field(None, description="Description of transformation")
    
    class Config:
        use_enum_values = True


class ValidationError(BaseModel):
    """Represents a validation error with context and suggestions."""
    
    # Error identification
    error_code: str = Field(..., description="Unique error code")
    field_path: str = Field(..., description="Path to the field with error")
    rule_name: str = Field(..., description="Name of the rule that failed")
    
    # Error details
    error_message: str = Field(..., description="Human-readable error message")
    error_type: ValidationErrorType = Field(..., description="Type of validation error")
    severity: ErrorSeverity = Field(ErrorSeverity.ERROR, description="Error severity")
    
    # Context
    actual_value: Any = Field(..., description="Actual value that failed validation")
    expected_value: Optional[Any] = Field(None, description="Expected value or pattern")
    
    # Suggestions
    suggested_fixes: List[str] = Field(default_factory=list, description="Suggested fixes for the error")
    auto_fixable: bool = Field(False, description="Whether error can be auto-fixed")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When error occurred")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    
    class Config:
        use_enum_values = True


class ValidationResult(BaseModel):
    """Result of validation operations."""
    
    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[ValidationError] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    
    # Performance
    validation_time_ms: float = Field(0.0, description="Time taken for validation")
    
    # Context
    rule_name: Optional[str] = Field(None, description="Name of the rule that was validated")
    field_path: Optional[str] = Field(None, description="Path to the field that was validated")
    
    # Timestamps
    validated_at: datetime = Field(default_factory=datetime.utcnow, description="When validation was performed")
