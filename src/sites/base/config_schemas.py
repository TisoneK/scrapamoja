"""
Configuration schema definitions for the scraper framework.

This module provides comprehensive schema definitions for all configuration
types, including validation rules, default values, and environment-specific overrides.
"""

from typing import Dict, Any, List, Optional, Union, Type
from datetime import datetime
import json
from dataclasses import dataclass, field
from enum import Enum


class ConfigType(Enum):
    """Configuration type enumeration."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    DATETIME = "datetime"
    URL = "url"
    EMAIL = "email"
    REGEX = "regex"


class ValidationRule(Enum):
    """Validation rule enumeration."""
    REQUIRED = "required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    PATTERN = "pattern"
    ENUM = "enum"
    CUSTOM = "custom"


@dataclass
class ConfigField:
    """Configuration field definition."""
    name: str
    type: ConfigType
    required: bool = False
    default: Any = None
    description: str = ""
    validation_rules: Dict[ValidationRule, Any] = field(default_factory=dict)
    environment_overrides: Dict[str, Any] = field(default_factory=dict)
    sensitive: bool = False
    deprecated: bool = False
    deprecation_message: str = ""
    
    def __post_init__(self):
        """Post-initialization validation."""
        if self.required and self.default is not None:
            # Required fields shouldn't have defaults
            pass
        
        # Validate type-specific rules
        if self.type == ConfigType.INTEGER:
            self._validate_numeric_rules()
        elif self.type == ConfigType.FLOAT:
            self._validate_numeric_rules()
        elif self.type == ConfigType.STRING:
            self._validate_string_rules()
        elif self.type == ConfigType.LIST:
            self._validate_list_rules()
    
    def _validate_numeric_rules(self):
        """Validate numeric field rules."""
        for rule, value in self.validation_rules.items():
            if rule in [ValidationRule.MIN_VALUE, ValidationRule.MAX_VALUE]:
                if not isinstance(value, (int, float)):
                    raise ValueError(f"Numeric validation rule {rule} must be numeric")
    
    def _validate_string_rules(self):
        """Validate string field rules."""
        for rule, value in self.validation_rules.items():
            if rule in [ValidationRule.MIN_LENGTH, ValidationRule.MAX_LENGTH]:
                if not isinstance(value, int):
                    raise ValueError(f"String validation rule {rule} must be integer")
            elif rule == ValidationRule.PATTERN:
                if not isinstance(value, str):
                    raise ValueError(f"Pattern validation rule must be string")
    
    def _validate_list_rules(self):
        """Validate list field rules."""
        for rule, value in self.validation_rules.items():
            if rule == ValidationRule.MIN_LENGTH:
                if not isinstance(value, int):
                    raise ValueError(f"List validation rule {rule} must be integer")
    
    def validate_value(self, value: Any, environment: str = None) -> Dict[str, Any]:
        """Validate a configuration value."""
        errors = []
        warnings = []
        
        # Check required
        if self.required and value is None:
            errors.append(f"Field '{self.name}' is required")
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        # Skip validation if value is None and not required
        if value is None:
            return {'valid': True, 'errors': errors, 'warnings': warnings}
        
        # Type validation
        type_error = self._validate_type(value)
        if type_error:
            errors.append(type_error)
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        # Apply validation rules
        for rule, rule_value in self.validation_rules.items():
            rule_error = self._apply_validation_rule(rule, rule_value, value)
            if rule_error:
                errors.append(rule_error)
        
        # Check deprecation
        if self.deprecated:
            warnings.append(f"Field '{self.name}' is deprecated: {self.deprecation_message}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_type(self, value: Any) -> Optional[str]:
        """Validate value type."""
        try:
            if self.type == ConfigType.STRING:
                if not isinstance(value, str):
                    return f"Expected string, got {type(value).__name__}"
            elif self.type == ConfigType.INTEGER:
                if not isinstance(value, int):
                    return f"Expected integer, got {type(value).__name__}"
            elif self.type == ConfigType.FLOAT:
                if not isinstance(value, (int, float)):
                    return f"Expected number, got {type(value).__name__}"
            elif self.type == ConfigType.BOOLEAN:
                if not isinstance(value, bool):
                    return f"Expected boolean, got {type(value).__name__}"
            elif self.type == ConfigType.LIST:
                if not isinstance(value, list):
                    return f"Expected list, got {type(value).__name__}"
            elif self.type == ConfigType.DICT:
                if not isinstance(value, dict):
                    return f"Expected dict, got {type(value).__name__}"
            elif self.type == ConfigType.DATETIME:
                if not isinstance(value, (str, datetime)):
                    return f"Expected datetime or string, got {type(value).__name__}"
            elif self.type == ConfigType.URL:
                if not isinstance(value, str):
                    return f"Expected URL string, got {type(value).__name__}"
                if not value.startswith(('http://', 'https://')):
                    return f"Expected valid URL, got {value}"
            elif self.type == ConfigType.EMAIL:
                if not isinstance(value, str):
                    return f"Expected email string, got {type(value).__name__}"
                if '@' not in value:
                    return f"Expected valid email, got {value}"
            elif self.type == ConfigType.REGEX:
                if not isinstance(value, str):
                    return f"Expected regex string, got {type(value).__name__}"
                try:
                    import re
                    re.compile(value)
                except re.error as e:
                    return f"Invalid regex pattern: {str(e)}"
            
            return None
            
        except Exception as e:
            return f"Type validation error: {str(e)}"
    
    def _apply_validation_rule(self, rule: ValidationRule, rule_value: Any, value: Any) -> Optional[str]:
        """Apply a validation rule to a value."""
        try:
            if rule == ValidationRule.MIN_LENGTH:
                if len(value) < rule_value:
                    return f"Value length {len(value)} is less than minimum {rule_value}"
            elif rule == ValidationRule.MAX_LENGTH:
                if len(value) > rule_value:
                    return f"Value length {len(value)} exceeds maximum {rule_value}"
            elif rule == ValidationRule.MIN_VALUE:
                if value < rule_value:
                    return f"Value {value} is less than minimum {rule_value}"
            elif rule == ValidationRule.MAX_VALUE:
                if value > rule_value:
                    return f"Value {value} exceeds maximum {rule_value}"
            elif rule == ValidationRule.PATTERN:
                import re
                if not re.match(rule_value, str(value)):
                    return f"Value '{value}' does not match pattern '{rule_value}'"
            elif rule == ValidationRule.ENUM:
                if value not in rule_value:
                    return f"Value '{value}' not in allowed values: {rule_value}"
            elif rule == ValidationRule.CUSTOM:
                # Custom validation function should be callable
                if callable(rule_value):
                    result = rule_value(value)
                    if result is not True:
                        return str(result) if result else "Custom validation failed"
            
            return None
            
        except Exception as e:
            return f"Validation rule error: {str(e)}"
    
    def get_default_value(self, environment: str = None) -> Any:
        """Get default value for a specific environment."""
        if environment and environment in self.environment_overrides:
            return self.environment_overrides[environment]
        return self.default


@dataclass
class ConfigSchema:
    """Configuration schema definition."""
    name: str
    version: str
    description: str = ""
    fields: List[ConfigField] = field(default_factory=list)
    environment_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def add_field(self, field: ConfigField) -> None:
        """Add a field to the schema."""
        self.fields.append(field)
    
    def get_field(self, name: str) -> Optional[ConfigField]:
        """Get a field by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None
    
    def validate_config(self, config: Dict[str, Any], environment: str = None) -> Dict[str, Any]:
        """Validate a configuration dictionary."""
        errors = []
        warnings = []
        
        # Check for unknown fields
        known_fields = {field.name for field in self.fields}
        unknown_fields = set(config.keys()) - known_fields
        if unknown_fields:
            warnings.append(f"Unknown fields: {list(unknown_fields)}")
        
        # Validate each field
        for field in self.fields:
            field_value = config.get(field.name)
            field_result = field.validate_value(field_value, environment)
            
            errors.extend(field_result.get('errors', []))
            warnings.extend(field_result.get('warnings', []))
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'schema_name': self.name,
            'schema_version': self.version,
            'environment': environment
        }
    
    def get_defaults(self, environment: str = None) -> Dict[str, Any]:
        """Get default values for all fields."""
        defaults = {}
        
        for field in self.fields:
            defaults[field.name] = field.get_default_value(environment)
        
        return defaults
    
    def merge_with_defaults(self, config: Dict[str, Any], environment: str = None) -> Dict[str, Any]:
        """Merge configuration with defaults."""
        defaults = self.get_defaults(environment)
        merged = defaults.copy()
        merged.update(config)
        return merged
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary."""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'fields': [
                {
                    'name': field.name,
                    'type': field.type.value,
                    'required': field.required,
                    'default': field.default,
                    'description': field.description,
                    'validation_rules': {rule.value: value for rule, value in field.validation_rules.items()},
                    'environment_overrides': field.environment_overrides,
                    'sensitive': field.sensitive,
                    'deprecated': field.deprecated,
                    'deprecation_message': field.deprecation_message
                }
                for field in self.fields
            ],
            'environment_overrides': self.environment_overrides
        }


# Predefined schemas
def create_base_config_schema() -> ConfigSchema:
    """Create base configuration schema."""
    schema = ConfigSchema(
        name="base_config",
        version="1.0.0",
        description="Base configuration schema for all scrapers"
    )
    
    # Basic fields
    schema.add_field(ConfigField(
        name="site_id",
        type=ConfigType.STRING,
        required=True,
        description="Unique identifier for the site"
    ))
    
    schema.add_field(ConfigField(
        name="site_name",
        type=ConfigType.STRING,
        required=True,
        description="Human-readable name for the site"
    ))
    
    schema.add_field(ConfigField(
        name="base_url",
        type=ConfigType.URL,
        required=True,
        description="Base URL for the site"
    ))
    
    schema.add_field(ConfigField(
        name="enabled",
        type=ConfigType.BOOLEAN,
        default=True,
        description="Whether the scraper is enabled"
    ))
    
    schema.add_field(ConfigField(
        name="timeout",
        type=ConfigType.INTEGER,
        default=30000,
        validation_rules={ValidationRule.MIN_VALUE: 1000, ValidationRule.MAX_VALUE: 300000},
        description="Timeout in milliseconds"
    ))
    
    schema.add_field(ConfigField(
        name="retry_count",
        type=ConfigType.INTEGER,
        default=3,
        validation_rules={ValidationRule.MIN_VALUE: 0, ValidationRule.MAX_VALUE: 10},
        description="Number of retry attempts"
    ))
    
    schema.add_field(ConfigField(
        name="retry_delay",
        type=ConfigType.INTEGER,
        default=1000,
        validation_rules={ValidationRule.MIN_VALUE: 100, ValidationRule.MAX_VALUE: 10000},
        description="Delay between retries in milliseconds"
    ))
    
    return schema


def create_browser_config_schema() -> ConfigSchema:
    """Create browser configuration schema."""
    schema = ConfigSchema(
        name="browser_config",
        version="1.0.0",
        description="Browser configuration schema"
    )
    
    schema.add_field(ConfigField(
        name="headless",
        type=ConfigType.BOOLEAN,
        default=True,
        description="Run browser in headless mode"
    ))
    
    schema.add_field(ConfigField(
        name="browser_type",
        type=ConfigType.STRING,
        default="chromium",
        validation_rules={ValidationRule.ENUM: ["chromium", "firefox", "webkit"]},
        description="Browser type to use"
    ))
    
    schema.add_field(ConfigField(
        name="viewport_width",
        type=ConfigType.INTEGER,
        default=1920,
        validation_rules={ValidationRule.MIN_VALUE: 800, ValidationRule.MAX_VALUE: 3840},
        description="Browser viewport width"
    ))
    
    schema.add_field(ConfigField(
        name="viewport_height",
        type=ConfigType.INTEGER,
        default=1080,
        validation_rules={ValidationRule.MIN_VALUE: 600, ValidationRule.MAX_VALUE: 2160},
        description="Browser viewport height"
    ))
    
    schema.add_field(ConfigField(
        name="user_agent",
        type=ConfigType.STRING,
        description="Custom user agent string"
    ))
    
    return schema


def create_rate_limiting_config_schema() -> ConfigSchema:
    """Create rate limiting configuration schema."""
    schema = ConfigSchema(
        name="rate_limiting_config",
        version="1.0.0",
        description="Rate limiting configuration schema"
    )
    
    schema.add_field(ConfigField(
        name="enabled",
        type=ConfigType.BOOLEAN,
        default=True,
        description="Enable rate limiting"
    ))
    
    schema.add_field(ConfigField(
        name="max_requests_per_minute",
        type=ConfigType.INTEGER,
        default=60,
        validation_rules={ValidationRule.MIN_VALUE: 1, ValidationRule.MAX_VALUE: 1000},
        description="Maximum requests per minute"
    ))
    
    schema.add_field(ConfigField(
        name="max_requests_per_hour",
        type=ConfigType.INTEGER,
        default=1000,
        validation_rules={ValidationRule.MIN_VALUE: 1, ValidationRule.MAX_VALUE: 100000},
        description="Maximum requests per hour"
    ))
    
    schema.add_field(ConfigField(
        name="burst_size",
        type=ConfigType.INTEGER,
        default=10,
        validation_rules={ValidationRule.MIN_VALUE: 1, ValidationRule.MAX_VALUE: 100},
        description="Maximum burst size"
    ))
    
    return schema


def create_stealth_config_schema() -> ConfigSchema:
    """Create stealth configuration schema."""
    schema = ConfigSchema(
        name="stealth_config",
        version="1.0.0",
        description="Stealth configuration schema"
    )
    
    schema.add_field(ConfigField(
        name="enabled",
        type=ConfigType.BOOLEAN,
        default=False,
        description="Enable stealth mode"
    ))
    
    schema.add_field(ConfigField(
        name="randomize_user_agent",
        type=ConfigType.BOOLEAN,
        default=True,
        description="Randomize user agent"
    ))
    
    schema.add_field(ConfigField(
        name="randomize_viewport",
        type=ConfigType.BOOLEAN,
        default=True,
        description="Randomize viewport size"
    ))
    
    schema.add_field(ConfigField(
        name="simulate_mouse_movement",
        type=ConfigType.BOOLEAN,
        default=True,
        description="Simulate mouse movement"
    ))
    
    schema.add_field(ConfigField(
        name="random_delays",
        type=ConfigType.BOOLEAN,
        default=True,
        description="Add random delays"
    ))
    
    return schema


def create_logging_config_schema() -> ConfigSchema:
    """Create logging configuration schema."""
    schema = ConfigSchema(
        name="logging_config",
        version="1.0.0",
        description="Logging configuration schema"
    )
    
    schema.add_field(ConfigField(
        name="level",
        type=ConfigType.STRING,
        default="INFO",
        validation_rules={ValidationRule.ENUM: ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
        description="Logging level"
    ))
    
    schema.add_field(ConfigField(
        name="format",
        type=ConfigType.STRING,
        default="json",
        validation_rules={ValidationRule.ENUM: ["json", "text"]},
        description="Log format"
    ))
    
    schema.add_field(ConfigField(
        name="file_path",
        type=ConfigType.STRING,
        description="Log file path"
    ))
    
    schema.add_field(ConfigField(
        name="max_file_size",
        type=ConfigType.INTEGER,
        default=10485760,  # 10MB
        validation_rules={ValidationRule.MIN_VALUE: 1024, ValidationRule.MAX_VALUE: 1073741824},  # 1GB
        description="Maximum log file size in bytes"
    ))
    
    schema.add_field(ConfigField(
        name="backup_count",
        type=ConfigType.INTEGER,
        default=5,
        validation_rules={ValidationRule.MIN_VALUE: 1, ValidationRule.MAX_VALUE: 100},
        description="Number of backup log files"
    ))
    
    return schema


# Schema registry
SCHEMA_REGISTRY = {
    "base": create_base_config_schema(),
    "browser": create_browser_config_schema(),
    "rate_limiting": create_rate_limiting_config_schema(),
    "stealth": create_stealth_config_schema(),
    "logging": create_logging_config_schema()
}


def get_schema(name: str) -> Optional[ConfigSchema]:
    """Get a schema by name."""
    return SCHEMA_REGISTRY.get(name)


def register_schema(schema: ConfigSchema) -> None:
    """Register a schema in the registry."""
    SCHEMA_REGISTRY[schema.name] = schema


def get_all_schemas() -> Dict[str, ConfigSchema]:
    """Get all registered schemas."""
    return SCHEMA_REGISTRY.copy()


def validate_config_by_schema(config: Dict[str, Any], schema_name: str, environment: str = None) -> Dict[str, Any]:
    """Validate configuration using a specific schema."""
    schema = get_schema(schema_name)
    if not schema:
        return {
            'valid': False,
            'errors': [f"Schema '{schema_name}' not found"],
            'warnings': []
        }
    
    return schema.validate_config(config, environment)


# Utility functions
def create_field(name: str, type: ConfigType, **kwargs) -> ConfigField:
    """Create a configuration field."""
    return ConfigField(name=name, type=type, **kwargs)


def create_schema(name: str, version: str, **kwargs) -> ConfigSchema:
    """Create a configuration schema."""
    return ConfigSchema(name=name, version=version, **kwargs)


# Environment-specific validation
def validate_environment_config(config: Dict[str, Any], environment: str) -> Dict[str, Any]:
    """Validate configuration for a specific environment."""
    all_errors = []
    all_warnings = []
    
    for schema_name, schema in get_all_schemas().items():
        result = schema.validate_config(config, environment)
        all_errors.extend(result.get('errors', []))
        all_warnings.extend(result.get('warnings', []))
    
    return {
        'valid': len(all_errors) == 0,
        'errors': all_errors,
        'warnings': all_warnings,
        'environment': environment
    }


# Schema export/import
def export_schemas() -> Dict[str, Any]:
    """Export all schemas to dictionary format."""
    return {
        name: schema.to_dict()
        for name, schema in get_all_schemas().items()
    }


def import_schemas(schemas_data: Dict[str, Any]) -> None:
    """Import schemas from dictionary format."""
    for name, schema_data in schemas_data.items():
        fields = []
        for field_data in schema_data.get('fields', []):
            field = ConfigField(
                name=field_data['name'],
                type=ConfigType(field_data['type']),
                required=field_data.get('required', False),
                default=field_data.get('default'),
                description=field_data.get('description', ''),
                validation_rules={
                    ValidationRule(rule): value
                    for rule, value in field_data.get('validation_rules', {}).items()
                },
                environment_overrides=field_data.get('environment_overrides', {}),
                sensitive=field_data.get('sensitive', False),
                deprecated=field_data.get('deprecated', False),
                deprecation_message=field_data.get('deprecation_message', '')
            )
            fields.append(field)
        
        schema = ConfigSchema(
            name=schema_data['name'],
            version=schema_data['version'],
            description=schema_data.get('description', ''),
            fields=fields,
            environment_overrides=schema_data.get('environment_overrides', {})
        )
        
        register_schema(schema)
