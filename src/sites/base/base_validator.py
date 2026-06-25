"""
Base validator class for data validation in the modular site scraper template system.

This module provides the base class that all validator components must inherit from,
ensuring consistent validation patterns and enabling proper lifecycle management.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from datetime import datetime
import asyncio
import re

from .component_interface import BaseComponent, ComponentContext, ComponentResult


@dataclass
class ValidationRule:
    """Rule for data validation."""
    rule_id: str
    name: str
    field_path: str  # Dot notation for nested fields, e.g., "user.email"
    rule_type: str  # required, pattern, min_length, max_length, custom
    parameters: Dict[str, Any]
    error_message: str
    warning_message: Optional[str] = None
    required: bool = True
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class FieldValidationResult:
    """Result for field validation."""
    field_path: str
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validation_time_ms: float
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ValidationResult:
    """Result object for comprehensive validation."""
    is_valid: bool
    field_results: Dict[str, FieldValidationResult]
    global_errors: List[str]
    global_warnings: List[str]
    validation_time_ms: float
    validator_id: str
    schema_version: str
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if self.field_results is None:
            self.field_results = {}
        if self.global_errors is None:
            self.global_errors = []
        if self.global_warnings is None:
            self.global_warnings = []
        if self.metadata is None:
            self.metadata = {}


class BaseValidator(BaseComponent):
    """Base class for all validator components in the modular template system."""
    
    def __init__(
        self,
        component_id: str,
        name: str,
        version: str,
        description: str,
        validator_type: str,
        validation_rules: Optional[List[ValidationRule]] = None,
        error_messages: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the base validator.
        
        Args:
            component_id: Unique identifier for the validator
            name: Human-readable name for the validator
            version: Validator version following semantic versioning
            description: Validator description
            validator_type: Type of validator (CONFIG, DATA, SCHEMA, BUSINESS_RULE)
            validation_rules: List of validation rules
            error_messages: Error message templates
        """
        super().__init__(component_id, name, version, description)
        self.validator_type = validator_type
        self.validation_rules = validation_rules or []
        self.error_messages = error_messages or {}
        self._validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'average_validation_time_ms': 0.0
        }
        self._custom_validators: Dict[str, Callable] = {}
    
    @property
    def validator_type(self) -> str:
        """Get validator type."""
        return self._validator_type
    
    @property
    def validation_rules(self) -> List[ValidationRule]:
        """Get validation rules."""
        return self._validation_rules
    
    @property
    def error_messages(self) -> Dict[str, str]:
        """Get error messages."""
        return self._error_messages
    
    @property
    def validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self._validation_stats
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize the validator with given context.
        
        Args:
            context: Component execution context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._context = context
            
            # Validate validation rules
            for rule in self.validation_rules:
                if not await self._validate_validation_rule(rule):
                    self._log_operation("initialize", f"Invalid validation rule: {rule.rule_id}", "error")
                    return False
            
            # Register built-in validators
            await self._register_builtin_validators()
            
            self._log_operation("initialize", f"Validator {self.component_id} initialized successfully")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Failed to initialize validator: {str(e)}", "error")
            return False
    
    @abstractmethod
    async def validate(self, target: Any) -> ValidationResult:
        """
        Validate the target according to validator type.
        
        Args:
            target: Target to validate (config, data, schema, etc.)
            
        Returns:
            Validation result
        """
        pass
    
    async def validate_field(self, data: Any, rule: ValidationRule) -> FieldValidationResult:
        """
        Validate a single field against a rule.
        
        Args:
            data: Data to validate
            rule: Validation rule to apply
            
        Returns:
            Field validation result
        """
        try:
            start_time = datetime.utcnow()
            errors = []
            warnings = []
            
            # Get field value using dot notation
            field_value = self._get_field_value(data, rule.field_path)
            
            # Apply validation rule
            rule_result = await self._apply_validation_rule(field_value, rule)
            
            if not rule_result['is_valid']:
                errors.extend(rule_result['errors'])
            
            warnings.extend(rule_result['warnings'])
            
            end_time = datetime.utcnow()
            validation_time = (end_time - start_time).total_seconds() * 1000
            
            return FieldValidationResult(
                field_path=rule.field_path,
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                validation_time_ms=validation_time
            )
            
        except Exception as e:
            self._log_operation("validate_field", f"Field validation failed: {str(e)}", "error")
            return FieldValidationResult(
                field_path=rule.field_path,
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                validation_time_ms=0.0
            )
    
    async def validate_all_rules(self, data: Any) -> ValidationResult:
        """
        Validate data against all validation rules.
        
        Args:
            data: Data to validate
            
        Returns:
            Comprehensive validation result
        """
        try:
            start_time = datetime.utcnow()
            field_results = {}
            global_errors = []
            global_warnings = []
            
            # Validate each rule
            for rule in self.validation_rules:
                field_result = await self.validate_field(data, rule)
                field_results[rule.field_path] = field_result
                
                # Collect errors and warnings
                if not field_result.is_valid and rule.required:
                    global_errors.extend(field_result.errors)
                
                global_warnings.extend(field_result.warnings)
            
            end_time = datetime.utcnow()
            validation_time = (end_time - start_time).total_seconds() * 1000
            
            is_valid = len(global_errors) == 0
            
            # Update statistics
            self._update_validation_stats(is_valid, validation_time)
            
            return ValidationResult(
                is_valid=is_valid,
                field_results=field_results,
                global_errors=global_errors,
                global_warnings=global_warnings,
                validation_time_ms=validation_time,
                validator_id=self.component_id,
                schema_version="1.0.0",
                metadata={
                    'validator_type': self.validator_type,
                    'rules_count': len(self.validation_rules),
                    'fields_validated': len(field_results)
                }
            )
            
        except Exception as e:
            self._log_operation("validate_all_rules", f"Validation failed: {str(e)}", "error")
            return ValidationResult(
                is_valid=False,
                field_results={},
                global_errors=[f"Validation error: {str(e)}"],
                global_warnings=[],
                validation_time_ms=0.0,
                validator_id=self.component_id,
                schema_version="1.0.0",
                metadata={'error': str(e)}
            )
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute the validator's main functionality.
        
        Args:
            **kwargs: Validator-specific arguments (should include 'target')
            
        Returns:
            Component execution result
        """
        try:
            target = kwargs.get('target')
            if target is None:
                raise ValueError("No target provided for validation")
            
            # Perform validation
            validation_result = await self.validate(target)
            
            return self._create_result(
                success=validation_result.is_valid,
                data={'validation_result': validation_result.__dict__},
                errors=validation_result.global_errors,
                warnings=validation_result.global_warnings,
                execution_time_ms=validation_result.validation_time_ms
            )
            
        except Exception as e:
            self._log_operation("execute", f"Validator execution failed: {str(e)}", "error")
            return self._create_result(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def validate(self, **kwargs) -> bool:
        """
        Validate validator configuration and dependencies.
        
        Args:
            **kwargs: Validation parameters
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Validate validation rules
            for rule in self.validation_rules:
                if not await self._validate_validation_rule(rule):
                    return False
            
            # Validate error messages
            for rule in self.validation_rules:
                if rule.rule_id not in self.error_messages:
                    self.error_messages[rule.rule_id] = rule.error_message
            
            self._log_operation("validate", "Validator validation passed")
            return True
            
        except Exception as e:
            self._log_operation("validate", f"Validator validation failed: {str(e)}", "error")
            return False
    
    async def cleanup(self) -> None:
        """Clean up validator resources."""
        try:
            self._log_operation("cleanup", f"Cleaning up validator {self.component_id}")
            
            # Reset statistics
            self._validation_stats = {
                'total_validations': 0,
                'successful_validations': 0,
                'failed_validations': 0,
                'average_validation_time_ms': 0.0
            }
            
            # Clear custom validators
            self._custom_validators.clear()
            
            # Clear references
            self._context = None
            
        except Exception as e:
            self._log_operation("cleanup", f"Cleanup failed: {str(e)}", "error")
    
    def add_custom_validator(self, name: str, validator_func: Callable):
        """
        Add a custom validation function.
        
        Args:
            name: Name of the custom validator
            validator_func: Validation function
        """
        self._custom_validators[name] = validator_func
    
    def get_error_message(self, rule_id: str, **kwargs) -> str:
        """
        Get error message for a rule.
        
        Args:
            rule_id: Rule identifier
            **kwargs: Parameters for message formatting
            
        Returns:
            Formatted error message
        """
        template = self.error_messages.get(rule_id, f"Validation failed for rule {rule_id}")
        
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template
    
    async def _validate_validation_rule(self, rule: ValidationRule) -> bool:
        """Validate a single validation rule."""
        try:
            # Basic validation
            if not rule.rule_id or not rule.name:
                return False
            
            if not rule.field_path:
                return False
            
            if not rule.rule_type:
                return False
            
            # Validate rule type
            valid_types = ['required', 'pattern', 'min_length', 'max_length', 'min_value', 'max_value', 'custom']
            if rule.rule_type not in valid_types:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _register_builtin_validators(self):
        """Register built-in validation functions."""
        
        async def validate_required(value: Any, **kwargs) -> Dict[str, Any]:
            """Validate required field."""
            is_valid = value is not None and value != ""
            return {
                'is_valid': is_valid,
                'errors': [] if is_valid else ['Field is required'],
                'warnings': []
            }
        
        async def validate_pattern(value: Any, **kwargs) -> Dict[str, Any]:
            """Validate pattern (regex)."""
            pattern = kwargs.get('pattern', '')
            if not pattern or not isinstance(value, str):
                return {'is_valid': True, 'errors': [], 'warnings': []}
            
            try:
                is_valid = bool(re.match(pattern, value))
                return {
                    'is_valid': is_valid,
                    'errors': [] if is_valid else [f'Field does not match pattern: {pattern}'],
                    'warnings': []
                }
            except re.error:
                return {'is_valid': False, 'errors': ['Invalid pattern'], 'warnings': []}
        
        async def validate_min_length(value: Any, **kwargs) -> Dict[str, Any]:
            """Validate minimum length."""
            min_length = kwargs.get('min_length', 0)
            if not isinstance(value, (str, list)):
                return {'is_valid': True, 'errors': [], 'warnings': []}
            
            is_valid = len(value) >= min_length
            return {
                'is_valid': is_valid,
                'errors': [] if is_valid else [f'Field must be at least {min_length} characters'],
                'warnings': []
            }
        
        async def validate_max_length(value: Any, **kwargs) -> Dict[str, Any]:
            """Validate maximum length."""
            max_length = kwargs.get('max_length', 0)
            if not isinstance(value, (str, list)):
                return {'is_valid': True, 'errors': [], 'warnings': []}
            
            is_valid = len(value) <= max_length
            return {
                'is_valid': is_valid,
                'errors': [] if is_valid else [f'Field must be at most {max_length} characters'],
                'warnings': []
            }
        
        async def validate_min_value(value: Any, **kwargs) -> Dict[str, Any]:
            """Validate minimum value."""
            min_value = kwargs.get('min_value', 0)
            if not isinstance(value, (int, float)):
                return {'is_valid': True, 'errors': [], 'warnings': []}
            
            is_valid = value >= min_value
            return {
                'is_valid': is_valid,
                'errors': [] if is_valid else [f'Field must be at least {min_value}'],
                'warnings': []
            }
        
        async def validate_max_value(value: Any, **kwargs) -> Dict[str, Any]:
            """Validate maximum value."""
            max_value = kwargs.get('max_value', 0)
            if not isinstance(value, (int, float)):
                return {'is_valid': True, 'errors': [], 'warnings': []}
            
            is_valid = value <= max_value
            return {
                'is_valid': is_valid,
                'errors': [] if is_valid else [f'Field must be at most {max_value}'],
                'warnings': []
            }
        
        # Register built-in validators
        self._custom_validators.update({
            'required': validate_required,
            'pattern': validate_pattern,
            'min_length': validate_min_length,
            'max_length': validate_max_length,
            'min_value': validate_min_value,
            'max_value': validate_max_value
        })
    
    def _get_field_value(self, data: Any, field_path: str) -> Any:
        """Get field value using dot notation."""
        if not field_path:
            return data
        
        keys = field_path.split('.')
        current_value = data
        
        try:
            for key in keys:
                if isinstance(current_value, dict):
                    current_value = current_value.get(key)
                elif isinstance(current_value, (list, tuple)) and key.isdigit():
                    index = int(key)
                    current_value = current_value[index]
                else:
                    return None
                
                if current_value is None:
                    break
            
            return current_value
            
        except (KeyError, IndexError, TypeError):
            return None
    
    async def _apply_validation_rule(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """Apply a single validation rule."""
        try:
            # Get validator function
            validator_func = self._custom_validators.get(rule.rule_type)
            
            if not validator_func:
                return {
                    'is_valid': False,
                    'errors': [f'Unknown validation rule type: {rule.rule_type}'],
                    'warnings': []
                }
            
            # Apply validation
            result = await validator_func(value, **rule.parameters)
            
            return result
            
        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f'Validation rule failed: {str(e)}'],
                'warnings': []
            }
    
    def _update_validation_stats(self, success: bool, validation_time_ms: float):
        """Update validation statistics."""
        self._validation_stats['total_validations'] += 1
        
        if success:
            self._validation_stats['successful_validations'] += 1
        else:
            self._validation_stats['failed_validations'] += 1
        
        # Update average validation time
        total = self._validation_stats['total_validations']
        current_avg = self._validation_stats['average_validation_time_ms']
        self._validation_stats['average_validation_time_ms'] = (
            (current_avg * (total - 1) + validation_time_ms) / total
        )


class ValidationError(Exception):
    """Exception raised when validation operations fail."""
    pass


class RuleValidationError(ValidationError):
    """Exception raised when validation rule fails."""
    pass


class SchemaValidationError(ValidationError):
    """Exception raised when schema validation fails."""
    pass
