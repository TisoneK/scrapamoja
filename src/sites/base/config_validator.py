"""
Configuration validation engine for the scraper framework.

This module provides comprehensive configuration validation capabilities, including
schema-based validation, custom validation rules, and detailed error reporting.
"""

from typing import Dict, Any, List, Optional, Callable, Union, Type
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .config_schemas import ConfigSchema, ConfigField, get_schema, get_all_schemas


class ValidationSeverity(Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationRule:
    """Custom validation rule."""
    
    def __init__(self, name: str, validator: Callable[[Any], bool], 
                 message: str, severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.name = name
        self.validator = validator
        self.message = message
        self.severity = severity
    
    def validate(self, value: Any) -> Dict[str, Any]:
        """Validate a value against this rule."""
        try:
            is_valid = self.validator(value)
            return {
                'valid': is_valid,
                'message': self.message,
                'severity': self.severity.value,
                'rule_name': self.name
            }
        except Exception as e:
            return {
                'valid': False,
                'message': f"Validation rule '{self.name}' failed: {str(e)}",
                'severity': ValidationSeverity.ERROR.value,
                'rule_name': self.name
            }


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    valid: bool
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    info: List[Dict[str, Any]] = field(default_factory=list)
    field_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    schema_name: str = ""
    environment: str = ""
    validation_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ConfigValidator:
    """Configuration validation engine."""
    
    def __init__(self):
        """Initialize configuration validator."""
        self._custom_rules: Dict[str, List[ValidationRule]] = {}
        self._global_rules: List[ValidationRule] = []
        self._validation_history: List[ValidationResult] = []
        self._performance_stats = {
            'total_validations': 0,
            'total_time_ms': 0.0,
            'average_time_ms': 0.0
        }
    
    def add_custom_rule(self, field_name: str, rule: ValidationRule) -> None:
        """Add a custom validation rule for a field."""
        if field_name not in self._custom_rules:
            self._custom_rules[field_name] = []
        self._custom_rules[field_name].append(rule)
    
    def add_global_rule(self, rule: ValidationRule) -> None:
        """Add a global validation rule."""
        self._global_rules.append(rule)
    
    def remove_custom_rule(self, field_name: str, rule_name: str) -> bool:
        """Remove a custom validation rule."""
        if field_name in self._custom_rules:
            self._custom_rules[field_name] = [
                rule for rule in self._custom_rules[field_name]
                if rule.name != rule_name
            ]
            return True
        return False
    
    def validate_config(self, config: Dict[str, Any], 
                        schema_name: Optional[str] = None,
                        environment: Optional[str] = None) -> ValidationResult:
        """
        Validate configuration against schema and custom rules.
        
        Args:
            config: Configuration to validate
            schema_name: Schema name to validate against
            environment: Environment for validation
            
        Returns:
            Validation result
        """
        start_time = datetime.utcnow()
        
        try:
            result = ValidationResult(
                valid=True,
                schema_name=schema_name or "",
                environment=environment or ""
            )
            
            # Get schema if specified
            schema = None
            if schema_name:
                schema = get_schema(schema_name)
                if not schema:
                    result.errors.append({
                        'message': f"Schema '{schema_name}' not found",
                        'severity': ValidationSeverity.ERROR.value,
                        'field': 'schema'
                    })
                    result.valid = False
                else:
                    # Validate against schema
                    schema_result = schema.validate_config(config, environment)
                    result.errors.extend([
                        {'message': error, 'severity': 'error', 'field': 'schema'}
                        for error in schema_result.get('errors', [])
                    ])
                    result.warnings.extend([
                        {'message': warning, 'severity': 'warning', 'field': 'schema'}
                        for warning in schema_result.get('warnings', [])
                    ])
                    result.valid = result.valid and schema_result['valid']
            
            # Validate each field with custom rules
            for field_name, field_value in config.items():
                field_result = self._validate_field(field_name, field_value, schema)
                result.field_results[field_name] = field_result
                
                # Collect field-level results
                for validation in field_result.get('validations', []):
                    if validation['severity'] == ValidationSeverity.ERROR.value:
                        result.errors.append(validation)
                        result.valid = False
                    elif validation['severity'] == ValidationSeverity.WARNING.value:
                        result.warnings.append(validation)
                    else:
                        result.info.append(validation)
            
            # Apply global rules
            for rule in self._global_rules:
                try:
                    rule_result = rule.validate(config)
                    if rule_result['severity'] == ValidationSeverity.ERROR.value:
                        result.errors.append(rule_result)
                        result.valid = False
                    elif rule_result['severity'] == ValidationSeverity.WARNING.value:
                        result.warnings.append(rule_result)
                    else:
                        result.info.append(rule_result)
                except Exception as e:
                    result.errors.append({
                        'message': f"Global rule '{rule.name}' failed: {str(e)}",
                        'severity': ValidationSeverity.ERROR.value,
                        'rule_name': rule.name
                    })
                    result.valid = False
            
            # Calculate validation time
            end_time = datetime.utcnow()
            result.validation_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Update performance stats
            self._update_performance_stats(result.validation_time_ms)
            
            # Store in history
            self._validation_history.append(result)
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            validation_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return ValidationResult(
                valid=False,
                errors=[{
                    'message': f"Validation failed: {str(e)}",
                    'severity': ValidationSeverity.ERROR.value
                }],
                validation_time_ms=validation_time_ms
            )
    
    def _validate_field(self, field_name: str, field_value: Any, 
                        schema: Optional[ConfigSchema] = None) -> Dict[str, Any]:
        """Validate a specific field."""
        field_result = {
            'field_name': field_name,
            'value': field_value,
            'valid': True,
            'validations': []
        }
        
        # Validate against schema field if available
        if schema:
            field = schema.get_field(field_name)
            if field:
                schema_result = field.validate_value(field_value)
                if not schema_result['valid']:
                    field_result['valid'] = False
                
                # Convert schema validation results to our format
                for error in schema_result.get('errors', []):
                    field_result['validations'].append({
                        'message': error,
                        'severity': ValidationSeverity.ERROR.value,
                        'rule_name': 'schema'
                    })
                
                for warning in schema_result.get('warnings', []):
                    field_result['validations'].append({
                        'message': warning,
                        'severity': ValidationSeverity.WARNING.value,
                        'rule_name': 'schema'
                    })
        
        # Apply custom rules for this field
        if field_name in self._custom_rules:
            for rule in self._custom_rules[field_name]:
                try:
                    rule_result = rule.validate(field_value)
                    field_result['validations'].append(rule_result)
                    
                    if rule_result['severity'] == ValidationSeverity.ERROR.value:
                        field_result['valid'] = False
                except Exception as e:
                    field_result['validations'].append({
                        'message': f"Custom rule '{rule.name}' failed: {str(e)}",
                        'severity': ValidationSeverity.ERROR.value,
                        'rule_name': rule.name
                    })
                    field_result['valid'] = False
        
        return field_result
    
    def validate_field(self, field_name: str, field_value: Any, 
                       schema_name: Optional[str] = None) -> ValidationResult:
        """Validate a single field."""
        config = {field_name: field_value}
        return self.validate_config(config, schema_name)
    
    def validate_all_schemas(self, config: Dict[str, Any], 
                             environment: Optional[str] = None) -> Dict[str, ValidationResult]:
        """Validate configuration against all available schemas."""
        results = {}
        
        for schema_name in get_all_schemas().keys():
            result = self.validate_config(config, schema_name, environment)
            results[schema_name] = result
        
        return results
    
    def create_custom_rule(self, name: str, validator: Callable[[Any], bool], 
                           message: str, severity: ValidationSeverity = ValidationSeverity.ERROR) -> ValidationRule:
        """Create a custom validation rule."""
        return ValidationRule(name, validator, message, severity)
    
    def add_required_field_rule(self, field_name: str, message: Optional[str] = None) -> None:
        """Add a required field validation rule."""
        message = message or f"Field '{field_name}' is required"
        
        def validator(value):
            return value is not None and value != ""
        
        rule = ValidationRule(
            name=f"required_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )
        
        self.add_custom_rule(field_name, rule)
    
    def add_type_rule(self, field_name: str, expected_type: Type, 
                      message: Optional[str] = None) -> None:
        """Add a type validation rule."""
        message = message or f"Field '{field_name}' must be of type {expected_type.__name__}"
        
        def validator(value):
            return isinstance(value, expected_type)
        
        rule = ValidationRule(
            name=f"type_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )
        
        self.add_custom_rule(field_name, rule)
    
    def add_range_rule(self, field_name: str, min_value: Any = None, 
                       max_value: Any = None, message: Optional[str] = None) -> None:
        """Add a range validation rule."""
        def validator(value):
            if min_value is not None and value < min_value:
                return False
            if max_value is not None and value > max_value:
                return False
            return True
        
        message = message or f"Field '{field_name}' must be between {min_value} and {max_value}"
        
        rule = ValidationRule(
            name=f"range_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )
        
        self.add_custom_rule(field_name, rule)
    
    def add_pattern_rule(self, field_name: str, pattern: str, 
                         message: Optional[str] = None) -> None:
        """Add a pattern validation rule."""
        import re
        
        def validator(value):
            if not isinstance(value, str):
                return False
            return bool(re.match(pattern, value))
        
        message = message or f"Field '{field_name}' must match pattern '{pattern}'"
        
        rule = ValidationRule(
            name=f"pattern_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )
        
        self.add_custom_rule(field_name, rule)
    
    def add_enum_rule(self, field_name: str, allowed_values: List[Any], 
                     message: Optional[str] = None) -> None:
        """Add an enum validation rule."""
        def validator(value):
            return value in allowed_values
        
        message = message or f"Field '{field_name}' must be one of: {allowed_values}"
        
        rule = ValidationRule(
            name=f"enum_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )
        
        self.add_custom_rule(field_name, rule)
    
    def add_url_rule(self, field_name: str, message: Optional[str] = None) -> None:
        """Add a URL validation rule."""
        def validator(value):
            if not isinstance(value, str):
                return False
            return value.startswith(('http://', 'https://'))
        
        message = message or f"Field '{field_name}' must be a valid URL"
        
        rule = ValidationRule(
            name=f"url_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )
        
        self.add_custom_rule(field_name, rule)
    
    def add_email_rule(self, field_name: str, message: Optional[str] = None) -> None:
        """Add an email validation rule."""
        import re
        
        def validator(value):
            if not isinstance(value, str):
                return False
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(email_pattern, value))
        
        message = message or f"Field '{field_name}' must be a valid email address"
        
        rule = ValidationRule(
            name=f"email_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )
        
        self.add_custom_rule(field_name, rule)
    
    def _update_performance_stats(self, validation_time_ms: float) -> None:
        """Update performance statistics."""
        self._performance_stats['total_validations'] += 1
        self._performance_stats['total_time_ms'] += validation_time_ms
        self._performance_stats['average_time_ms'] = (
            self._performance_stats['total_time_ms'] / 
            self._performance_stats['total_validations']
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self._performance_stats.copy()
    
    def get_validation_history(self, limit: Optional[int] = None) -> List[ValidationResult]:
        """Get validation history."""
        if limit:
            return self._validation_history[-limit:]
        return self._validation_history.copy()
    
    def clear_history(self) -> None:
        """Clear validation history."""
        self._validation_history.clear()
    
    def get_rule_summary(self) -> Dict[str, Any]:
        """Get summary of all validation rules."""
        summary = {
            'custom_rules': {},
            'global_rules': len(self._global_rules),
            'total_custom_rules': sum(len(rules) for rules in self._custom_rules.values())
        }
        
        for field_name, rules in self._custom_rules.items():
            summary['custom_rules'][field_name] = {
                'count': len(rules),
                'rules': [rule.name for rule in rules]
            }
        
        return summary
    
    def export_rules(self) -> Dict[str, Any]:
        """Export all validation rules."""
        exported = {
            'custom_rules': {},
            'global_rules': []
        }
        
        # Export custom rules
        for field_name, rules in self._custom_rules.items():
            exported['custom_rules'][field_name] = [
                {
                    'name': rule.name,
                    'message': rule.message,
                    'severity': rule.severity.value
                }
                for rule in rules
            ]
        
        # Export global rules
        exported['global_rules'] = [
            {
                'name': rule.name,
                'message': rule.message,
                'severity': rule.severity.value
            }
            for rule in self._global_rules
        ]
        
        return exported
    
    def import_rules(self, rules_data: Dict[str, Any]) -> None:
        """Import validation rules from data."""
        # Import custom rules
        for field_name, rules in rules_data.get('custom_rules', {}).items():
            for rule_data in rules:
                # Note: This only imports rule metadata, not the validator function
                # The validator function would need to be recreated
                pass
        
        # Import global rules
        for rule_data in rules_data.get('global_rules', []):
            # Note: This only imports rule metadata, not the validator function
            # The validator function would need to be recreated
            pass


# Predefined validation rules
class CommonValidationRules:
    """Common validation rules."""
    
    @staticmethod
    def required_field(field_name: str, message: Optional[str] = None) -> ValidationRule:
        """Create a required field rule."""
        message = message or f"Field '{field_name}' is required"
        
        def validator(value):
            return value is not None and value != ""
        
        return ValidationRule(
            name=f"required_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )
    
    @staticmethod
    def positive_number(field_name: str, message: Optional[str] = None) -> ValidationRule:
        """Create a positive number rule."""
        message = message or f"Field '{field_name}' must be a positive number"
        
        def validator(value):
            return isinstance(value, (int, float)) and value > 0
        
        return ValidationRule(
            name=f"positive_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )
    
    @staticmethod
    def non_empty_string(field_name: str, message: Optional[str] = None) -> ValidationRule:
        """Create a non-empty string rule."""
        message = message or f"Field '{field_name}' must be a non-empty string"
        
        def validator(value):
            return isinstance(value, str) and len(value.strip()) > 0
        
        return ValidationRule(
            name=f"non_empty_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )
    
    @staticmethod
    def url_field(field_name: str, message: Optional[str] = None) -> ValidationRule:
        """Create a URL field rule."""
        message = message or f"Field '{field_name}' must be a valid URL"
        
        def validator(value):
            if not isinstance(value, str):
                return False
            return value.startswith(('http://', 'https://'))
        
        return ValidationRule(
            name=f"url_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )
    
    @staticmethod
    def email_field(field_name: str, message: Optional[str] = None) -> ValidationRule:
        """Create an email field rule."""
        import re
        
        message = message or f"Field '{field_name}' must be a valid email"
        
        def validator(value):
            if not isinstance(value, str):
                return False
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(email_pattern, value))
        
        return ValidationRule(
            name=f"email_{field_name}",
            validator=validator,
            message=message,
            severity=ValidationSeverity.ERROR
        )


# Global validator instance
_config_validator = ConfigValidator()


# Convenience functions
def validate_config(config: Dict[str, Any], 
                 schema_name: Optional[str] = None,
                 environment: Optional[str] = None) -> ValidationResult:
    """Validate configuration."""
    return _config_validator.validate_config(config, schema_name, environment)


def add_validation_rule(field_name: str, rule: ValidationRule) -> None:
    """Add a validation rule."""
    _config_validator.add_custom_rule(field_name, rule)


def add_required_field_rule(field_name: str, message: Optional[str] = None) -> None:
    """Add a required field rule."""
    _config_validator.add_required_field_rule(field_name, message)


def add_type_rule(field_name: str, expected_type: Type, message: Optional[str] = None) -> None:
    """Add a type validation rule."""
    _config_validator.add_type_rule(field_name, expected_type, message)


def add_range_rule(field_name: str, min_value: Any = None, max_value: Any = None, 
                   message: Optional[str] = None) -> None:
    """Add a range validation rule."""
    _config_validator.add_range_rule(field_name, min_value, max_value, message)


def add_pattern_rule(field_name: str, pattern: str, message: Optional[str] = None) -> None:
    """Add a pattern validation rule."""
    _config_validator.add_pattern_rule(field_name, pattern, message)


def add_enum_rule(field_name: str, allowed_values: List[Any], message: Optional[str] = None) -> None:
    """Add an enum validation rule."""
    _config_validator.add_enum_rule(field_name, allowed_values, message)


def get_validation_stats() -> Dict[str, Any]:
    """Get validation statistics."""
    return _config_validator.get_performance_stats()


def get_validation_history(limit: Optional[int] = None) -> List[ValidationResult]:
    """Get validation history."""
    return _config_validator.get_validation_history(limit)
