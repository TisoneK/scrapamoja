"""
Validation engine for the extractor module.

This module provides validation functionality for extraction rules
and extracted data values.
"""

import re
from typing import Any, Dict, List, Optional

from .rules import (
    ExtractionRule,
    ExtractionResult,
    ValidationResult,
    ValidationError,
    ValidationErrorType,
    ErrorSeverity,
    DataType
)
from ..exceptions import ValidationError as ExtractorValidationError


class ValidationEngine:
    """Engine for validating extraction rules and results."""
    
    def validate_rule(self, rule: ExtractionRule) -> ValidationResult:
        """
        Validate an extraction rule.
        
        Args:
            rule: The extraction rule to validate
            
        Returns:
            ValidationResult with validation status and any errors
        """
        errors = []
        warnings = []
        start_time = self._get_time_ms()
        
        try:
            # Validate required fields
            if not rule.name or not rule.name.strip():
                errors.append(self._create_validation_error(
                    field_path="name",
                    rule_name=rule.name or "unnamed",
                    error_message="Rule name is required and cannot be empty",
                    error_type=ValidationErrorType.REQUIRED_FIELD_MISSING,
                    actual_value=rule.name,
                    severity=ErrorSeverity.ERROR
                ))
            
            if not rule.field_path or not rule.field_path.strip():
                errors.append(self._create_validation_error(
                    field_path="field_path",
                    rule_name=rule.name,
                    error_message="Field path is required and cannot be empty",
                    error_type=ValidationErrorType.REQUIRED_FIELD_MISSING,
                    actual_value=rule.field_path,
                    severity=ErrorSeverity.ERROR
                ))
            
            # Validate extraction type consistency
            if rule.extraction_type.value == "attribute" and not rule.attribute_name:
                errors.append(self._create_validation_error(
                    field_path="attribute_name",
                    rule_name=rule.name,
                    error_message="Attribute extraction requires attribute_name to be specified",
                    error_type=ValidationErrorType.REQUIRED_FIELD_MISSING,
                    actual_value=rule.attribute_name,
                    severity=ErrorSeverity.ERROR
                ))
            
            # Validate regex pattern
            if rule.regex_pattern:
                try:
                    re.compile(rule.regex_pattern, rule.regex_flags)
                except re.error as e:
                    errors.append(self._create_validation_error(
                        field_path="regex_pattern",
                        rule_name=rule.name,
                        error_message=f"Invalid regex pattern: {str(e)}",
                        error_type=ValidationErrorType.INVALID_FORMAT,
                        actual_value=rule.regex_pattern,
                        severity=ErrorSeverity.ERROR
                    ))
            
            # Validate date format
            if rule.target_type in [DataType.DATE, DataType.DATETIME] and rule.date_format:
                try:
                    from datetime import datetime
                    datetime.now().strftime(rule.date_format)
                except ValueError as e:
                    errors.append(self._create_validation_error(
                        field_path="date_format",
                        rule_name=rule.name,
                        error_message=f"Invalid date format: {str(e)}",
                        error_type=ValidationErrorType.INVALID_FORMAT,
                        actual_value=rule.date_format,
                        severity=ErrorSeverity.ERROR
                    ))
            
            # Validate value constraints
            if rule.min_value is not None or rule.max_value is not None:
                if rule.target_type not in [DataType.INTEGER, DataType.FLOAT]:
                    warnings.append(f"Value constraints (min/max) are only applicable to numeric types, but rule target type is {rule.target_type}")
                else:
                    if rule.min_value is not None and rule.max_value is not None:
                        if rule.min_value > rule.max_value:
                            errors.append(self._create_validation_error(
                                field_path="min_value",
                                rule_name=rule.name,
                                error_message="min_value cannot be greater than max_value",
                                error_type=ValidationErrorType.VALUE_OUT_OF_RANGE,
                                actual_value=rule.min_value,
                                expected_value=f"<= {rule.max_value}",
                                severity=ErrorSeverity.ERROR
                            ))
            
            # Validate length constraints
            if rule.min_length is not None or rule.max_length is not None:
                if rule.target_type != DataType.TEXT:
                    warnings.append(f"Length constraints (min/max_length) are only applicable to text type, but rule target type is {rule.target_type}")
                else:
                    if rule.min_length is not None and rule.max_length is not None:
                        if rule.min_length > rule.max_length:
                            errors.append(self._create_validation_error(
                                field_path="min_length",
                                rule_name=rule.name,
                                error_message="min_length cannot be greater than max_length",
                                error_type=ValidationErrorType.VALUE_OUT_OF_RANGE,
                                actual_value=rule.min_length,
                                expected_value=f"<= {rule.max_length}",
                                severity=ErrorSeverity.ERROR
                            ))
            
            # Validate validation pattern
            if rule.validation_pattern:
                try:
                    re.compile(rule.validation_pattern)
                except re.error as e:
                    errors.append(self._create_validation_error(
                        field_path="validation_pattern",
                        rule_name=rule.name,
                        error_message=f"Invalid validation pattern: {str(e)}",
                        error_type=ValidationErrorType.INVALID_FORMAT,
                        actual_value=rule.validation_pattern,
                        severity=ErrorSeverity.ERROR
                    ))
            
            # Check for potential issues
            if not rule.transformations and rule.target_type != DataType.TEXT:
                if rule.extraction_type.value == "text":
                    warnings.append("Rule extracts text but targets non-text type without transformations - consider adding type conversion transformations")
            
            validation_time_ms = self._get_time_ms() - start_time
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                validation_time_ms=validation_time_ms,
                rule_name=rule.name,
                field_path=rule.field_path
            )
            
        except Exception as e:
            validation_time_ms = self._get_time_ms() - start_time
            error = self._create_validation_error(
                field_path="rule",
                rule_name=rule.name,
                error_message=f"Unexpected validation error: {str(e)}",
                error_type=ValidationErrorType.VALIDATION_RULE_FAILED,
                actual_value=str(rule),
                severity=ErrorSeverity.CRITICAL
            )
            
            return ValidationResult(
                is_valid=False,
                errors=[error],
                validation_time_ms=validation_time_ms,
                rule_name=rule.name,
                field_path=rule.field_path
            )
    
    def validate_result(
        self,
        result: ExtractionResult,
        rule: ExtractionRule
    ) -> ValidationResult:
        """
        Validate an extraction result against its rule.
        
        Args:
            result: The extraction result to validate
            rule: The rule that was used for extraction
            
        Returns:
            ValidationResult with validation status and any errors
        """
        errors = []
        warnings = []
        start_time = self._get_time_ms()
        
        try:
            # Validate success status
            if not result.success and rule.required:
                errors.append(self._create_validation_error(
                    field_path=rule.field_path,
                    rule_name=rule.name,
                    error_message="Required field extraction failed",
                    error_type=ValidationErrorType.REQUIRED_FIELD_MISSING,
                    actual_value=result.value,
                    severity=ErrorSeverity.ERROR
                ))
            
            # Skip further validation if extraction failed and not required
            if not result.success and not rule.required:
                validation_time_ms = self._get_time_ms() - start_time
                return ValidationResult(
                    is_valid=True,
                    warnings=["Extraction failed but field is not required"],
                    validation_time_ms=validation_time_ms,
                    rule_name=rule.name,
                    field_path=rule.field_path
                )
            
            # Validate type consistency
            if not self._validate_type(result.value, rule.target_type):
                errors.append(self._create_validation_error(
                    field_path=rule.field_path,
                    rule_name=rule.name,
                    error_message=f"Expected {rule.target_type}, got {type(result.value).__name__}",
                    error_type=ValidationErrorType.TYPE_MISMATCH,
                    actual_value=result.value,
                    expected_value=rule.target_type.value,
                    severity=ErrorSeverity.ERROR
                ))
            
            # Validate string-specific constraints
            if isinstance(result.value, str):
                if rule.min_length is not None and len(result.value) < rule.min_length:
                    errors.append(self._create_validation_error(
                        field_path=rule.field_path,
                        rule_name=rule.name,
                        error_message=f"String length {len(result.value)} is less than minimum {rule.min_length}",
                        error_type=ValidationErrorType.LENGTH_INVALID,
                        actual_value=len(result.value),
                        expected_value=f">= {rule.min_length}",
                        severity=ErrorSeverity.ERROR
                    ))
                
                if rule.max_length is not None and len(result.value) > rule.max_length:
                    errors.append(self._create_validation_error(
                        field_path=rule.field_path,
                        rule_name=rule.name,
                        error_message=f"String length {len(result.value)} exceeds maximum {rule.max_length}",
                        error_type=ValidationErrorType.LENGTH_INVALID,
                        actual_value=len(result.value),
                        expected_value=f"<= {rule.max_length}",
                        severity=ErrorSeverity.ERROR
                    ))
                
                if rule.validation_pattern:
                    if not re.match(rule.validation_pattern, result.value):
                        errors.append(self._create_validation_error(
                            field_path=rule.field_path,
                            rule_name=rule.name,
                            error_message=f"String does not match validation pattern: {rule.validation_pattern}",
                            error_type=ValidationErrorType.PATTERN_MISMATCH,
                            actual_value=result.value,
                            expected_value=rule.validation_pattern,
                            severity=ErrorSeverity.ERROR
                        ))
            
            # Validate numeric constraints
            if isinstance(result.value, (int, float)):
                if rule.min_value is not None and result.value < rule.min_value:
                    errors.append(self._create_validation_error(
                        field_path=rule.field_path,
                        rule_name=rule.name,
                        error_message=f"Value {result.value} is less than minimum {rule.min_value}",
                        error_type=ValidationErrorType.VALUE_OUT_OF_RANGE,
                        actual_value=result.value,
                        expected_value=f">= {rule.min_value}",
                        severity=ErrorSeverity.ERROR
                    ))
                
                if rule.max_value is not None and result.value > rule.max_value:
                    errors.append(self._create_validation_error(
                        field_path=rule.field_path,
                        rule_name=rule.name,
                        error_message=f"Value {result.value} exceeds maximum {rule.max_value}",
                        error_type=ValidationErrorType.VALUE_OUT_OF_RANGE,
                        actual_value=result.value,
                        expected_value=f"<= {rule.max_value}",
                        severity=ErrorSeverity.ERROR
                    ))
            
            # Validate list constraints
            if isinstance(result.value, list):
                if rule.min_length is not None and len(result.value) < rule.min_length:
                    errors.append(self._create_validation_error(
                        field_path=rule.field_path,
                        rule_name=rule.name,
                        error_message=f"List length {len(result.value)} is less than minimum {rule.min_length}",
                        error_type=ValidationErrorType.LENGTH_INVALID,
                        actual_value=len(result.value),
                        expected_value=f">= {rule.min_length}",
                        severity=ErrorSeverity.ERROR
                    ))
                
                if rule.max_length is not None and len(result.value) > rule.max_length:
                    errors.append(self._create_validation_error(
                        field_path=rule.field_path,
                        rule_name=rule.name,
                        error_message=f"List length {len(result.value)} exceeds maximum {rule.max_length}",
                        error_type=ValidationErrorType.LENGTH_INVALID,
                        actual_value=len(result.value),
                        expected_value=f"<= {rule.max_length}",
                        severity=ErrorSeverity.ERROR
                    ))
            
            validation_time_ms = self._get_time_ms() - start_time
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                validation_time_ms=validation_time_ms,
                rule_name=rule.name,
                field_path=rule.field_path
            )
            
        except Exception as e:
            validation_time_ms = self._get_time_ms() - start_time
            error = self._create_validation_error(
                field_path=rule.field_path,
                rule_name=rule.name,
                error_message=f"Unexpected validation error: {str(e)}",
                error_type=ValidationErrorType.VALIDATION_RULE_FAILED,
                actual_value=str(result),
                severity=ErrorSeverity.CRITICAL
            )
            
            return ValidationResult(
                is_valid=False,
                errors=[error],
                validation_time_ms=validation_time_ms,
                rule_name=rule.name,
                field_path=rule.field_path
            )
    
    def _validate_type(self, value: Any, target_type: DataType) -> bool:
        """Check if value matches the target type."""
        if target_type == DataType.TEXT:
            return isinstance(value, str)
        elif target_type == DataType.INTEGER:
            return isinstance(value, int)
        elif target_type == DataType.FLOAT:
            return isinstance(value, (int, float))
        elif target_type == DataType.BOOLEAN:
            return isinstance(value, bool)
        elif target_type == DataType.DATE:
            # Check if it's a date object or string that can be parsed as date
            if hasattr(value, 'date'):  # datetime object
                return True
            return isinstance(value, str)  # Assume string dates are valid
        elif target_type == DataType.DATETIME:
            # Check if it's a datetime object
            return hasattr(value, 'date') or isinstance(value, str)
        elif target_type == DataType.LIST:
            return isinstance(value, list)
        elif target_type == DataType.DICT:
            return isinstance(value, dict)
        else:
            return True  # Unknown type, assume valid
    
    def _create_validation_error(
        self,
        field_path: str,
        rule_name: str,
        error_message: str,
        error_type: ValidationErrorType,
        actual_value: Any,
        expected_value: Any = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> ValidationError:
        """Create a ValidationError object."""
        return ValidationError(
            error_code=f"VALID_{error_type.value.upper()}",
            field_path=field_path,
            rule_name=rule_name,
            error_message=error_message,
            error_type=error_type,
            severity=severity,
            actual_value=actual_value,
            expected_value=expected_value,
            suggested_fixes=self._get_suggested_fixes(error_type, actual_value, expected_value),
            auto_fixable=self._is_auto_fixable(error_type)
        )
    
    def _get_suggested_fixes(
        self,
        error_type: ValidationErrorType,
        actual_value: Any,
        expected_value: Any
    ) -> List[str]:
        """Get suggested fixes for validation errors."""
        fixes = []
        
        if error_type == ValidationErrorType.TYPE_MISMATCH:
            fixes.append(f"Convert value to expected type: {expected_value}")
            fixes.append("Add appropriate transformation to the extraction rule")
        
        elif error_type == ValidationErrorType.PATTERN_MISMATCH:
            fixes.append("Update the validation pattern to match the expected format")
            fixes.append("Add transformation to clean the value before validation")
        
        elif error_type == ValidationErrorType.LENGTH_INVALID:
            fixes.append("Adjust the min/max length constraints")
            fixes.append("Add transformation to truncate or pad the value")
        
        elif error_type == ValidationErrorType.VALUE_OUT_OF_RANGE:
            fixes.append("Adjust the min/max value constraints")
            fixes.append("Add transformation to scale or clamp the value")
        
        elif error_type == ValidationErrorType.REQUIRED_FIELD_MISSING:
            fixes.append("Provide a default value for the rule")
            fixes.append("Make the field optional by setting required=False")
        
        elif error_type == ValidationErrorType.INVALID_FORMAT:
            fixes.append("Correct the format specification")
            fixes.append("Use a valid format string or pattern")
        
        return fixes
    
    def _is_auto_fixable(self, error_type: ValidationErrorType) -> bool:
        """Check if a validation error can be automatically fixed."""
        auto_fixable_types = [
            ValidationErrorType.LENGTH_INVALID,
            ValidationErrorType.VALUE_OUT_OF_RANGE,
            ValidationErrorType.PATTERN_MISMATCH
        ]
        return error_type in auto_fixable_types
    
    def _get_time_ms(self) -> float:
        """Get current time in milliseconds."""
        import time
        return time.time() * 1000
