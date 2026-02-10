"""
Data validator template for the modular site scraper template.

This module provides data validation functionality with configurable
rules for validating scraped data quality and integrity.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
import re
from urllib.parse import urlparse

from src.sites.base.base_processor import BaseProcessor
from src.sites.base.component_interface import ComponentResult


class DataValidator(BaseProcessor):
    """Data validator with configurable validation rules."""
    
    def __init__(
        self,
        component_id: str = "data_validator",
        name: str = "Data Validator",
        version: str = "1.0.0",
        description: str = "Validates scraped data quality and integrity with configurable rules"
    ):
        """
        Initialize data validator.
        
        Args:
            component_id: Unique identifier for the processor
            name: Human-readable name for the processor
            version: Processor version
            description: Processor description
        """
        super().__init__(
            component_id=component_id,
            name=name,
            version=version,
            description=description,
            processor_type="VALIDATOR"
        )
        
        # Validation configuration
        self._strict_mode: bool = False
        self._fail_fast: bool = False
        self._enable_required_field_validation: bool = True
        self._enable_type_validation: bool = True
        self._enable_format_validation: bool = True
        self._enable_range_validation: bool = True
        self._enable_custom_validation: bool = True
        
        # Validation rules
        self._field_rules: Dict[str, Dict[str, Any]] = {}
        self._global_rules: Dict[str, Any] = {}
        self._custom_validators: Dict[str, Callable] = {}
        
        # Validation statistics
        self._validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'validation_errors': []
        }
    
    async def execute(self, target: Any, **kwargs) -> ComponentResult:
        """
        Execute data validation.
        
        Args:
            target: Data to validate
            **kwargs: Additional validation parameters
            
        Returns:
            Validation result
        """
        try:
            start_time = datetime.utcnow()
            
            # Reset validation stats
            self._validation_stats = {
                'total_validations': 0,
                'passed_validations': 0,
                'failed_validations': 0,
                'validation_errors': []
            }
            
            # Handle different data types
            if isinstance(target, list):
                validation_result = await self._validate_list(target)
            elif isinstance(target, dict):
                validation_result = await self._validate_dict(target)
            else:
                validation_result = await self._validate_value(target, "root")
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Determine overall success
            is_valid = (
                self._validation_stats['failed_validations'] == 0 or
                (not self._strict_mode and self._validation_stats['passed_validations'] > 0)
            )
            
            return ComponentResult(
                success=is_valid,
                data={
                    'is_valid': is_valid,
                    'validation_result': validation_result,
                    'validation_stats': self._validation_stats,
                    'validation_rules_applied': self._get_applied_rules(),
                    'execution_time_ms': execution_time
                },
                execution_time_ms=execution_time,
                errors=self._validation_stats['validation_errors'] if not is_valid else []
            )
            
        except Exception as e:
            self._log_operation("execute", f"Validation failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def _validate_list(self, data_list: List[Any]) -> Dict[str, Any]:
        """Validate a list of data items."""
        validation_results = []
        
        for index, item in enumerate(data_list):
            field_name = f"item_{index}"
            
            if isinstance(item, dict):
                item_result = await self._validate_dict(item, field_name)
            elif isinstance(item, list):
                item_result = await self._validate_list(item)
            else:
                item_result = await self._validate_value(item, field_name)
            
            validation_results.append({
                'index': index,
                'result': item_result
            })
            
            # Fail fast if enabled and validation failed
            if self._fail_fast and not item_result.get('is_valid', True):
                break
        
        return {
            'type': 'list',
            'length': len(data_list),
            'items': validation_results,
            'is_valid': all(item['result'].get('is_valid', True) for item in validation_results)
        }
    
    async def _validate_dict(self, data_dict: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Validate a dictionary of data."""
        validation_results = {}
        
        for key, value in data_dict.items():
            field_name = f"{prefix}.{key}" if prefix else key
            
            # Check for field-specific rules
            field_rules = self._field_rules.get(key, {})
            
            # Apply field-specific validation
            if field_rules:
                field_result = await self._validate_field(key, value, field_rules)
            else:
                # Apply global validation rules
                field_result = await self._validate_value(value, field_name)
            
            validation_results[key] = field_result
            
            # Fail fast if enabled and validation failed
            if self._fail_fast and not field_result.get('is_valid', True):
                break
        
        return {
            'type': 'dict',
            'fields': validation_results,
            'is_valid': all(result.get('is_valid', True) for result in validation_results.values())
        }
    
    async def _validate_value(self, value: Any, field_name: str) -> Dict[str, Any]:
        """Validate a single value."""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'value_type': type(value).__name__
        }
        
        # Check for None values
        if value is None:
            if self._enable_required_field_validation:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"{field_name}: Value is required but is None")
            return validation_result
        
        # Type validation
        if self._enable_type_validation:
            type_result = self._validate_type(value, field_name)
            validation_result['errors'].extend(type_result['errors'])
            validation_result['warnings'].extend(type_result['warnings'])
            if not type_result['is_valid']:
                validation_result['is_valid'] = False
        
        # String-specific validation
        if isinstance(value, str):
            string_result = await self._validate_string(value, field_name)
            validation_result['errors'].extend(string_result['errors'])
            validation_result['warnings'].extend(string_result['warnings'])
            if not string_result['is_valid']:
                validation_result['is_valid'] = False
        
        # Number-specific validation
        elif isinstance(value, (int, float)):
            number_result = self._validate_number(value, field_name)
            validation_result['errors'].extend(number_result['errors'])
            validation_result['warnings'].extend(number_result['warnings'])
            if not number_result['is_valid']:
                validation_result['is_valid'] = False
        
        # Apply custom validators
        if self._enable_custom_validation:
            for validator_name, validator in self._custom_validators.items():
                try:
                    custom_result = validator(value, field_name)
                    if isinstance(custom_result, dict):
                        validation_result['errors'].extend(custom_result.get('errors', []))
                        validation_result['warnings'].extend(custom_result.get('warnings', []))
                        if not custom_result.get('is_valid', True):
                            validation_result['is_valid'] = False
                except Exception as e:
                    validation_result['warnings'].append(f"Custom validator {validator_name} failed: {str(e)}")
        
        # Update statistics
        self._validation_stats['total_validations'] += 1
        if validation_result['is_valid']:
            self._validation_stats['passed_validations'] += 1
        else:
            self._validation_stats['failed_validations'] += 1
            self._validation_stats['validation_errors'].extend(validation_result['errors'])
        
        return validation_result
    
    async def _validate_field(self, field_name: str, value: Any, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a field with specific rules."""
        validation_result = await self._validate_value(value, field_name)
        
        # Required field validation
        if rules.get('required', False) and (value is None or (isinstance(value, str) and not value.strip())):
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"{field_name}: Field is required")
        
        # Type validation
        if 'type' in rules and value is not None:
            expected_type = rules['type']
            actual_type = type(value).__name__
            
            type_mapping = {
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict
            }
            
            if expected_type in type_mapping:
                expected_python_type = type_mapping[expected_type]
                if not isinstance(value, expected_python_type):
                    validation_result['is_valid'] = False
                    validation_result['errors'].append(
                        f"{field_name}: Expected type {expected_type}, got {actual_type}"
                    )
        
        # Length validation for strings
        if isinstance(value, str):
            if 'min_length' in rules and len(value) < rules['min_length']:
                validation_result['is_valid'] = False
                validation_result['errors'].append(
                    f"{field_name}: Minimum length {rules['min_length']}, got {len(value)}"
                )
            
            if 'max_length' in rules and len(value) > rules['max_length']:
                validation_result['is_valid'] = False
                validation_result['errors'].append(
                    f"{field_name}: Maximum length {rules['max_length']}, got {len(value)}"
                )
        
        # Range validation for numbers
        if isinstance(value, (int, float)):
            if 'min_value' in rules and value < rules['min_value']:
                validation_result['is_valid'] = False
                validation_result['errors'].append(
                    f"{field_name}: Minimum value {rules['min_value']}, got {value}"
                )
            
            if 'max_value' in rules and value > rules['max_value']:
                validation_result['is_valid'] = False
                validation_result['errors'].append(
                    f"{field_name}: Maximum value {rules['max_value']}, got {value}"
                )
        
        # Pattern validation for strings
        if isinstance(value, str) and 'pattern' in rules:
            pattern = rules['pattern']
            if not re.match(pattern, value):
                validation_result['is_valid'] = False
                validation_result['errors'].append(
                    f"{field_name}: Value does not match pattern {pattern}"
                )
        
        # Allowed values validation
        if 'allowed_values' in rules and value not in rules['allowed_values']:
            validation_result['is_valid'] = False
            validation_result['errors'].append(
                f"{field_name}: Value {value} not in allowed values {rules['allowed_values']}"
            )
        
        # Custom field validation
        if 'custom_validation' in rules:
            custom_validator = rules['custom_validation']
            try:
                custom_result = custom_validator(value, field_name)
                if isinstance(custom_result, dict):
                    validation_result['errors'].extend(custom_result.get('errors', []))
                    validation_result['warnings'].extend(custom_result.get('warnings', []))
                    if not custom_result.get('is_valid', True):
                        validation_result['is_valid'] = False
            except Exception as e:
                validation_result['warnings'].append(f"Custom field validation failed: {str(e)}")
        
        return validation_result
    
    def _validate_type(self, value: Any, field_name: str) -> Dict[str, Any]:
        """Validate the type of a value."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        # Basic type validation is handled in field validation
        # This method can be extended for more complex type validation
        
        return result
    
    async def _validate_string(self, value: str, field_name: str) -> Dict[str, Any]:
        """Validate a string value."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        if not self._enable_format_validation:
            return result
        
        # Email validation
        if '@' in value and '.' in value:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                result['warnings'].append(f"{field_name}: Invalid email format")
        
        # URL validation
        elif value.startswith(('http://', 'https://')):
            try:
                parsed = urlparse(value)
                if not parsed.netloc:
                    result['warnings'].append(f"{field_name}: Invalid URL format")
            except:
                result['warnings'].append(f"{field_name}: Invalid URL format")
        
        # Phone number validation
        elif re.search(r'\d', value):
            phone_pattern = r'^(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$'
            if not re.match(phone_pattern, value):
                result['warnings'].append(f"{field_name}: Possible invalid phone format")
        
        return result
    
    def _validate_number(self, value: Union[int, float], field_name: str) -> Dict[str, Any]:
        """Validate a numeric value."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        if not self._enable_range_validation:
            return result
        
        # Check for NaN or infinity
        if isinstance(value, float):
            if value != value:  # NaN check
                result['is_valid'] = False
                result['errors'].append(f"{field_name}: Value is NaN")
            elif value in (float('inf'), float('-inf')):
                result['is_valid'] = False
                result['errors'].append(f"{field_name}: Value is infinity")
        
        return result
    
    def _get_applied_rules(self) -> List[str]:
        """Get list of applied validation rules."""
        rules = []
        
        if self._enable_required_field_validation:
            rules.append("required_field_validation")
        if self._enable_type_validation:
            rules.append("type_validation")
        if self._enable_format_validation:
            rules.append("format_validation")
        if self._enable_range_validation:
            rules.append("range_validation")
        if self._enable_custom_validation:
            rules.append("custom_validation")
        
        rules.extend(self._custom_validators.keys())
        
        return rules
    
    def configure_validation(
        self,
        strict_mode: Optional[bool] = None,
        fail_fast: Optional[bool] = None,
        enable_required_field_validation: Optional[bool] = None,
        enable_type_validation: Optional[bool] = None,
        enable_format_validation: Optional[bool] = None,
        enable_range_validation: Optional[bool] = None,
        enable_custom_validation: Optional[bool] = None
    ) -> None:
        """
        Configure validation settings.
        
        Args:
            strict_mode: Enable strict validation mode
            fail_fast: Stop validation on first error
            enable_required_field_validation: Enable required field validation
            enable_type_validation: Enable type validation
            enable_format_validation: Enable format validation
            enable_range_validation: Enable range validation
            enable_custom_validation: Enable custom validation
        """
        if strict_mode is not None:
            self._strict_mode = strict_mode
        if fail_fast is not None:
            self._fail_fast = fail_fast
        if enable_required_field_validation is not None:
            self._enable_required_field_validation = enable_required_field_validation
        if enable_type_validation is not None:
            self._enable_type_validation = enable_type_validation
        if enable_format_validation is not None:
            self._enable_format_validation = enable_format_validation
        if enable_range_validation is not None:
            self._enable_range_validation = enable_range_validation
        if enable_custom_validation is not None:
            self._enable_custom_validation = enable_custom_validation
    
    def add_field_rule(self, field_name: str, rules: Dict[str, Any]) -> None:
        """
        Add validation rules for a specific field.
        
        Args:
            field_name: Name of the field
            rules: Validation rules for the field
        """
        self._field_rules[field_name] = rules
    
    def add_custom_validator(self, name: str, validator: Callable) -> None:
        """
        Add a custom validator function.
        
        Args:
            name: Name of the validator
            validator: Validator function
        """
        self._custom_validators[name] = validator
    
    def remove_field_rule(self, field_name: str) -> None:
        """Remove validation rules for a field."""
        if field_name in self._field_rules:
            del self._field_rules[field_name]
    
    def remove_custom_validator(self, name: str) -> None:
        """Remove a custom validator."""
        if name in self._custom_validators:
            del self._custom_validators[name]
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self._validation_stats.copy()
    
    def reset_validation_statistics(self) -> None:
        """Reset validation statistics."""
        self._validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'validation_errors': []
        }
    
    def get_validation_configuration(self) -> Dict[str, Any]:
        """Get current validation configuration."""
        return {
            'strict_mode': self._strict_mode,
            'fail_fast': self._fail_fast,
            'enable_required_field_validation': self._enable_required_field_validation,
            'enable_type_validation': self._enable_type_validation,
            'enable_format_validation': self._enable_format_validation,
            'enable_range_validation': self._enable_range_validation,
            'enable_custom_validation': self._enable_custom_validation,
            'field_rules': self._field_rules,
            'custom_validators': list(self._custom_validators.keys()),
            **self.get_configuration()
        }
