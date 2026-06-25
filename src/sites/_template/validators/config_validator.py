"""
Configuration validator template for the modular site scraper template.

This module provides configuration validation functionality with
configurable rules for validating scraper configurations.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
import os
from urllib.parse import urlparse

from src.sites.base.base_validator import BaseValidator
from src.sites.base.component_interface import ComponentResult


class ConfigValidator(BaseValidator):
    """Configuration validator with configurable validation rules."""
    
    def __init__(
        self,
        component_id: str = "config_validator",
        name: str = "Configuration Validator",
        version: str = "1.0.0",
        description: str = "Validates scraper configuration with configurable rules"
    ):
        """
        Initialize configuration validator.
        
        Args:
            component_id: Unique identifier for the validator
            name: Human-readable name for the validator
            version: Validator version
            description: Validator description
        """
        super().__init__(
            component_id=component_id,
            name=name,
            version=version,
            description=description,
            validator_type="CONFIG"
        )
        
        # Validation configuration
        self._strict_mode: bool = False
        self._validate_required_fields: bool = True
        self._validate_field_types: bool = True
        self._validate_field_values: bool = True
        self._validate_file_paths: bool = True
        self._validate_urls: bool = True
        self._validate_ranges: bool = True
        self._validate_dependencies: bool = True
        
        # Validation rules
        self._required_fields: List[str] = []
        self._field_types: Dict[str, type] = {}
        self._field_value_rules: Dict[str, Dict[str, Any]] = {}
        self._dependency_rules: Dict[str, List[str]] = {}
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
        Execute configuration validation.
        
        Args:
            target: Configuration to validate
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
            
            # Ensure target is a dictionary
            if not isinstance(target, dict):
                return ComponentResult(
                    success=False,
                    data={'error': 'Configuration must be a dictionary'},
                    errors=['Configuration must be a dictionary']
                )
            
            # Perform validation
            validation_result = await self._validate_config(target)
            
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
            self._log_operation("execute", f"Configuration validation failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the configuration dictionary."""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'field_validations': {}
        }
        
        # Validate required fields
        if self._validate_required_fields:
            required_result = await self._validate_required_fields(config)
            validation_result['errors'].extend(required_result['errors'])
            validation_result['warnings'].extend(required_result['warnings'])
            validation_result['field_validations']['required_fields'] = required_result
            if not required_result['is_valid']:
                validation_result['is_valid'] = False
        
        # Validate field types
        if self._validate_field_types:
            type_result = await self._validate_field_types(config)
            validation_result['errors'].extend(type_result['errors'])
            validation_result['warnings'].extend(type_result['warnings'])
            validation_result['field_validations']['field_types'] = type_result
            if not type_result['is_valid']:
                validation_result['is_valid'] = False
        
        # Validate field values
        if self._validate_field_values:
            value_result = await self._validate_field_values(config)
            validation_result['errors'].extend(value_result['errors'])
            validation_result['warnings'].extend(value_result['warnings'])
            validation_result['field_validations']['field_values'] = value_result
            if not value_result['is_valid']:
                validation_result['is_valid'] = False
        
        # Validate file paths
        if self._validate_file_paths:
            path_result = await self._validate_file_paths(config)
            validation_result['errors'].extend(path_result['errors'])
            validation_result['warnings'].extend(path_result['warnings'])
            validation_result['field_validations']['file_paths'] = path_result
            if not path_result['is_valid']:
                validation_result['is_valid'] = False
        
        # Validate URLs
        if self._validate_urls:
            url_result = await self._validate_urls(config)
            validation_result['errors'].extend(url_result['errors'])
            validation_result['warnings'].extend(url_result['warnings'])
            validation_result['field_validations']['urls'] = url_result
            if not url_result['is_valid']:
                validation_result['is_valid'] = False
        
        # Validate ranges
        if self._validate_ranges:
            range_result = await self._validate_ranges(config)
            validation_result['errors'].extend(range_result['errors'])
            validation_result['warnings'].extend(range_result['warnings'])
            validation_result['field_validations']['ranges'] = range_result
            if not range_result['is_valid']:
                validation_result['is_valid'] = False
        
        # Validate dependencies
        if self._validate_dependencies:
            dependency_result = await self._validate_dependencies(config)
            validation_result['errors'].extend(dependency_result['errors'])
            validation_result['warnings'].extend(dependency_result['warnings'])
            validation_result['field_validations']['dependencies'] = dependency_result
            if not dependency_result['is_valid']:
                validation_result['is_valid'] = False
        
        # Apply custom validators
        for validator_name, validator in self._custom_validators.items():
            try:
                custom_result = validator(config)
                if isinstance(custom_result, dict):
                    validation_result['errors'].extend(custom_result.get('errors', []))
                    validation_result['warnings'].extend(custom_result.get('warnings', []))
                    validation_result['field_validations'][validator_name] = custom_result
                    if not custom_result.get('is_valid', True):
                        validation_result['is_valid'] = False
            except Exception as e:
                validation_result['warnings'].append(f"Custom validator {validator_name} failed: {str(e)}")
        
        # Update statistics
        self._validation_stats['total_validations'] = 1
        if validation_result['is_valid']:
            self._validation_stats['passed_validations'] = 1
        else:
            self._validation_stats['failed_validations'] = 1
            self._validation_stats['validation_errors'].extend(validation_result['errors'])
        
        return validation_result
    
    async def _validate_required_fields(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate required fields are present."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        for field in self._required_fields:
            if field not in config:
                result['is_valid'] = False
                result['errors'].append(f"Required field '{field}' is missing")
            elif config[field] is None:
                result['is_valid'] = False
                result['errors'].append(f"Required field '{field}' is None")
            elif isinstance(config[field], str) and not config[field].strip():
                result['is_valid'] = False
                result['errors'].append(f"Required field '{field}' is empty")
        
        return result
    
    async def _validate_field_types(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate field types."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        for field, expected_type in self._field_types.items():
            if field in config:
                value = config[field]
                actual_type = type(value)
                
                # Handle special cases
                if expected_type == bool and isinstance(value, str):
                    if value.lower() in ('true', 'false'):
                        continue  # String representation of boolean is acceptable
                
                if not isinstance(value, expected_type):
                    result['is_valid'] = False
                    result['errors'].append(
                        f"Field '{field}' should be {expected_type.__name__}, got {actual_type.__name__}"
                    )
        
        return result
    
    async def _validate_field_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate field values against rules."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        for field, rules in self._field_value_rules.items():
            if field in config:
                value = config[field]
                field_result = await self._validate_field_value(field, value, rules)
                result['errors'].extend(field_result['errors'])
                result['warnings'].extend(field_result['warnings'])
                if not field_result['is_valid']:
                    result['is_valid'] = False
        
        return result
    
    async def _validate_field_value(self, field: str, value: Any, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single field value against rules."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        # Length validation for strings
        if isinstance(value, str):
            if 'min_length' in rules and len(value) < rules['min_length']:
                result['is_valid'] = False
                result['errors'].append(
                    f"Field '{field}': Minimum length {rules['min_length']}, got {len(value)}"
                )
            
            if 'max_length' in rules and len(value) > rules['max_length']:
                result['is_valid'] = False
                result['errors'].append(
                    f"Field '{field}': Maximum length {rules['max_length']}, got {len(value)}"
                )
        
        # Range validation for numbers
        if isinstance(value, (int, float)):
            if 'min_value' in rules and value < rules['min_value']:
                result['is_valid'] = False
                result['errors'].append(
                    f"Field '{field}': Minimum value {rules['min_value']}, got {value}"
                )
            
            if 'max_value' in rules and value > rules['max_value']:
                result['is_valid'] = False
                result['errors'].append(
                    f"Field '{field}': Maximum value {rules['max_value']}, got {value}"
                )
        
        # Allowed values validation
        if 'allowed_values' in rules and value not in rules['allowed_values']:
            result['is_valid'] = False
            result['errors'].append(
                f"Field '{field}': Value '{value}' not in allowed values {rules['allowed_values']}"
            )
        
        # Pattern validation for strings
        if isinstance(value, str) and 'pattern' in rules:
            import re
            if not re.match(rules['pattern'], value):
                result['is_valid'] = False
                result['errors'].append(
                    f"Field '{field}': Value '{value}' does not match pattern {rules['pattern']}"
                )
        
        return result
    
    async def _validate_file_paths(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate file paths in configuration."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        # Common file path fields
        path_fields = [
            'log_file_path', 'output_file_path', 'config_file_path',
            'data_file_path', 'cache_file_path'
        ]
        
        for field in path_fields:
            if field in config and config[field]:
                path = config[field]
                
                # Check if path is string
                if not isinstance(path, str):
                    result['is_valid'] = False
                    result['errors'].append(f"Field '{field}' must be a string path")
                    continue
                
                # Check if directory exists (or can be created)
                directory = os.path.dirname(path)
                if directory and not os.path.exists(directory):
                    try:
                        os.makedirs(directory, exist_ok=True)
                        result['warnings'].append(f"Created directory for field '{field}': {directory}")
                    except Exception as e:
                        result['is_valid'] = False
                        result['errors'].append(f"Cannot create directory for field '{field}': {str(e)}")
        
        return result
    
    async def _validate_urls(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate URLs in configuration."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        # Common URL fields
        url_fields = ['base_url', 'login_url', 'api_url', 'callback_url']
        
        for field in url_fields:
            if field in config and config[field]:
                url = config[field]
                
                # Check if URL is string
                if not isinstance(url, str):
                    result['is_valid'] = False
                    result['errors'].append(f"Field '{field}' must be a string URL")
                    continue
                
                # Validate URL format
                try:
                    parsed = urlparse(url)
                    if not parsed.scheme or not parsed.netloc:
                        result['is_valid'] = False
                        result['errors'].append(f"Field '{field}': Invalid URL format: {url}")
                except Exception as e:
                    result['is_valid'] = False
                    result['errors'].append(f"Field '{field}': URL parsing failed: {str(e)}")
        
        return result
    
    async def _validate_ranges(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate numeric ranges in configuration."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        # Common range fields
        range_fields = {
            'timeout_ms': (1000, 300000),
            'retry_attempts': (0, 10),
            'max_results': (1, 10000),
            'requests_per_minute': (1, 1000),
            'memory_limit_mb': (64, 8192),
            'cpu_limit_percent': (1.0, 100.0)
        }
        
        for field, (min_val, max_val) in range_fields.items():
            if field in config and config[field] is not None:
                value = config[field]
                
                try:
                    numeric_value = float(value)
                    if numeric_value < min_val or numeric_value > max_val:
                        result['is_valid'] = False
                        result['errors'].append(
                            f"Field '{field}': Value {numeric_value} out of range [{min_val}, {max_val}]"
                        )
                except (ValueError, TypeError):
                    result['is_valid'] = False
                    result['errors'].append(f"Field '{field}': Must be a numeric value")
        
        return result
    
    async def _validate_dependencies(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate field dependencies."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        for field, dependencies in self._dependency_rules.items():
            if field in config and config[field]:
                for dependency in dependencies:
                    if dependency not in config or not config[dependency]:
                        result['is_valid'] = False
                        result['errors'].append(
                            f"Field '{field}' requires '{dependency}' to be set"
                        )
        
        return result
    
    def _get_applied_rules(self) -> List[str]:
        """Get list of applied validation rules."""
        rules = []
        
        if self._validate_required_fields:
            rules.append("required_fields")
        if self._validate_field_types:
            rules.append("field_types")
        if self._validate_field_values:
            rules.append("field_values")
        if self._validate_file_paths:
            rules.append("file_paths")
        if self._validate_urls:
            rules.append("urls")
        if self._validate_ranges:
            rules.append("ranges")
        if self._validate_dependencies:
            rules.append("dependencies")
        
        rules.extend(self._custom_validators.keys())
        
        return rules
    
    def configure_validation(
        self,
        strict_mode: Optional[bool] = None,
        validate_required_fields: Optional[bool] = None,
        validate_field_types: Optional[bool] = None,
        validate_field_values: Optional[bool] = None,
        validate_file_paths: Optional[bool] = None,
        validate_urls: Optional[bool] = None,
        validate_ranges: Optional[bool] = None,
        validate_dependencies: Optional[bool] = None
    ) -> None:
        """
        Configure validation settings.
        
        Args:
            strict_mode: Enable strict validation mode
            validate_required_fields: Enable required field validation
            validate_field_types: Enable field type validation
            validate_field_values: Enable field value validation
            validate_file_paths: Enable file path validation
            validate_urls: Enable URL validation
            validate_ranges: Enable range validation
            validate_dependencies: Enable dependency validation
        """
        if strict_mode is not None:
            self._strict_mode = strict_mode
        if validate_required_fields is not None:
            self._validate_required_fields = validate_required_fields
        if validate_field_types is not None:
            self._validate_field_types = validate_field_types
        if validate_field_values is not None:
            self._validate_field_values = validate_field_values
        if validate_file_paths is not None:
            self._validate_file_paths = validate_file_paths
        if validate_urls is not None:
            self._validate_urls = validate_urls
        if validate_ranges is not None:
            self._validate_ranges = validate_ranges
        if validate_dependencies is not None:
            self._validate_dependencies = validate_dependencies
    
    def add_required_field(self, field_name: str) -> None:
        """Add a required field."""
        if field_name not in self._required_fields:
            self._required_fields.append(field_name)
    
    def add_field_type(self, field_name: str, field_type: type) -> None:
        """Add a field type validation."""
        self._field_types[field_name] = field_type
    
    def add_field_value_rules(self, field_name: str, rules: Dict[str, Any]) -> None:
        """Add field value validation rules."""
        self._field_value_rules[field_name] = rules
    
    def add_dependency_rule(self, field: str, dependencies: List[str]) -> None:
        """Add a dependency rule."""
        self._dependency_rules[field] = dependencies
    
    def add_custom_validator(self, name: str, validator: Callable) -> None:
        """Add a custom validator function."""
        self._custom_validators[name] = validator
    
    def get_validation_configuration(self) -> Dict[str, Any]:
        """Get current validation configuration."""
        return {
            'strict_mode': self._strict_mode,
            'validate_required_fields': self._validate_required_fields,
            'validate_field_types': self._validate_field_types,
            'validate_field_values': self._validate_field_values,
            'validate_file_paths': self._validate_file_paths,
            'validate_urls': self._validate_urls,
            'validate_ranges': self._validate_ranges,
            'validate_dependencies': self._validate_dependencies,
            'required_fields': self._required_fields,
            'field_types': {k: v.__name__ for k, v in self._field_types.items()},
            'field_value_rules': self._field_value_rules,
            'dependency_rules': self._dependency_rules,
            'custom_validators': list(self._custom_validators.keys()),
            **self.get_configuration()
        }
