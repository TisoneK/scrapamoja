"""
Data Validation Utilities

Utilities for validating telemetry data including schema validation,
data integrity checks, and format validation.
"""

import json
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from urllib.parse import urlparse
import uuid

from ..models import TelemetryEvent
from ..exceptions import TelemetryValidationError
from ..configuration.schemas import (
    validate_telemetry_event as validate_event_schema,
    validate_alert as validate_alert_schema,
    validate_configuration as validate_config_schema,
    is_valid_telemetry_event,
    is_valid_alert,
    is_valid_configuration
)


class TelemetryDataValidator:
    """
    Comprehensive validator for telemetry data.
    
    Provides validation for telemetry events, metrics, and configuration
    data with detailed error reporting and integrity checks.
    """
    
    def __init__(self):
        """Initialize telemetry data validator."""
        self._validation_rules = self._initialize_validation_rules()
    
    def _initialize_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize validation rules for different data types."""
        return {
            "selector_name": {
                "required": True,
                "type": str,
                "min_length": 1,
                "max_length": 255,
                "pattern": r"^[a-zA-Z0-9_-]+$",
                "description": "Selector name must be alphanumeric with underscores and hyphens"
            },
            "correlation_id": {
                "required": True,
                "type": str,
                "min_length": 1,
                "max_length": 128,
                "pattern": r"^[a-zA-Z0-9_-]+$",
                "description": "Correlation ID must be alphanumeric with underscores and hyphens"
            },
            "operation_type": {
                "required": True,
                "type": str,
                "allowed_values": ["resolution", "validation", "execution", "cleanup"],
                "description": "Operation type must be one of: resolution, validation, execution, cleanup"
            },
            "confidence_score": {
                "required": False,
                "type": (int, float),
                "min_value": 0.0,
                "max_value": 1.0,
                "description": "Confidence score must be between 0.0 and 1.0"
            },
            "resolution_time_ms": {
                "required": False,
                "type": (int, float),
                "min_value": 0,
                "max_value": 300000,  # 5 minutes max
                "description": "Resolution time must be non-negative and less than 5 minutes"
            },
            "memory_usage_mb": {
                "required": False,
                "type": (int, float),
                "min_value": 0,
                "max_value": 1024,  # 1GB max
                "description": "Memory usage must be non-negative and less than 1GB"
            },
            "cpu_usage_percent": {
                "required": False,
                "type": (int, float),
                "min_value": 0,
                "max_value": 100,
                "description": "CPU usage must be between 0 and 100 percent"
            },
            "page_url": {
                "required": False,
                "type": str,
                "validator": self._validate_url,
                "description": "Page URL must be a valid URL"
            },
            "event_id": {
                "required": True,
                "type": str,
                "validator": self._validate_uuid,
                "description": "Event ID must be a valid UUID"
            },
            "timestamp": {
                "required": True,
                "type": str,
                "validator": self._validate_timestamp,
                "description": "Timestamp must be a valid ISO datetime string"
            }
        }
    
    def validate_telemetry_event(self, event: Union[Dict[str, Any], TelemetryEvent]) -> List[str]:
        """
        Validate a telemetry event.
        
        Args:
            event: Telemetry event to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Convert to dictionary if needed
        if isinstance(event, TelemetryEvent):
            event_dict = event.dict()
        else:
            event_dict = event
        
        # Schema validation
        schema_errors = validate_event_schema(event_dict)
        errors.extend(schema_errors)
        
        # Custom validation rules
        field_errors = self._validate_fields(event_dict)
        errors.extend(field_errors)
        
        # Business logic validation
        business_errors = self._validate_business_logic(event_dict)
        errors.extend(business_errors)
        
        return errors
    
    def validate_performance_metrics(self, metrics: Dict[str, Any]) -> List[str]:
        """
        Validate performance metrics.
        
        Args:
            metrics: Performance metrics to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not isinstance(metrics, dict):
            errors.append("Performance metrics must be a dictionary")
            return errors
        
        # Validate required fields
        required_fields = ["resolution_time_ms", "strategy_execution_time_ms", "total_duration_ms"]
        for field in required_fields:
            if field not in metrics:
                errors.append(f"Performance metrics missing required field: {field}")
        
        # Validate individual fields
        for field, rule in self._validation_rules.items():
            if field in metrics and field.endswith("_ms"):
                field_errors = self._validate_field_value(
                    field, metrics[field], rule
                )
                errors.extend(field_errors)
        
        # Validate timing consistency
        if "resolution_time_ms" in metrics and "strategy_execution_time_ms" in metrics and "total_duration_ms" in metrics:
            resolution = metrics["resolution_time_ms"]
            strategy = metrics["strategy_execution_time_ms"]
            total = metrics["total_duration_ms"]
            
            if resolution + strategy > total * 1.1:  # Allow 10% tolerance
                errors.append("Total duration should be greater than or equal to resolution + strategy time")
        
        return errors
    
    def validate_quality_metrics(self, metrics: Dict[str, Any]) -> List[str]:
        """
        Validate quality metrics.
        
        Args:
            metrics: Quality metrics to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not isinstance(metrics, dict):
            errors.append("Quality metrics must be a dictionary")
            return errors
        
        # Validate confidence score
        if "confidence_score" in metrics:
            confidence_errors = self._validate_field_value(
                "confidence_score", metrics["confidence_score"],
                self._validation_rules["confidence_score"]
            )
            errors.extend(confidence_errors)
        
        # Validate elements found
        if "elements_found" in metrics:
            elements = metrics["elements_found"]
            if not isinstance(elements, int) or elements < 0:
                errors.append("elements_found must be a non-negative integer")
        
        # Validate success flag
        if "success" in metrics:
            if not isinstance(metrics["success"], bool):
                errors.append("success must be a boolean")
        
        return errors
    
    def validate_strategy_metrics(self, metrics: Dict[str, Any]) -> List[str]:
        """
        Validate strategy metrics.
        
        Args:
            metrics: Strategy metrics to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not isinstance(metrics, dict):
            errors.append("Strategy metrics must be a dictionary")
            return errors
        
        # Validate primary strategy
        if "primary_strategy" in metrics:
            primary = metrics["primary_strategy"]
            if not isinstance(primary, str) or not primary.strip():
                errors.append("primary_strategy must be a non-empty string")
        
        # Validate secondary strategies
        if "secondary_strategies" in metrics:
            secondary = metrics["secondary_strategies"]
            if not isinstance(secondary, list):
                errors.append("secondary_strategies must be a list")
            else:
                for i, strategy in enumerate(secondary):
                    if not isinstance(strategy, str) or not strategy.strip():
                        errors.append(f"secondary_strategies[{i}] must be a non-empty string")
        
        # Validate strategy switches count
        if "strategy_switches_count" in metrics:
            switches = metrics["strategy_switches_count"]
            if not isinstance(switches, int) or switches < 0:
                errors.append("strategy_switches_count must be a non-negative integer")
        
        return errors
    
    def validate_error_data(self, error_data: Dict[str, Any]) -> List[str]:
        """
        Validate error data.
        
        Args:
            error_data: Error data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not isinstance(error_data, dict):
            errors.append("Error data must be a dictionary")
            return errors
        
        # Validate required fields
        required_fields = ["error_type", "error_message"]
        for field in required_fields:
            if field not in error_data:
                errors.append(f"Error data missing required field: {field}")
            elif not isinstance(error_data[field], str) or not error_data[field].strip():
                errors.append(f"{field} must be a non-empty string")
        
        # Validate retry attempts
        if "retry_attempts" in error_data:
            retries = error_data["retry_attempts"]
            if not isinstance(retries, int) or retries < 0:
                errors.append("retry_attempts must be a non-negative integer")
        
        # Validate fallback attempts
        if "fallback_attempts" in error_data:
            fallbacks = error_data["fallback_attempts"]
            if not isinstance(fallbacks, int) or fallbacks < 0:
                errors.append("fallback_attempts must be a non-negative integer")
        
        return errors
    
    def validate_context_data(self, context_data: Dict[str, Any]) -> List[str]:
        """
        Validate context data.
        
        Args:
            context_data: Context data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not isinstance(context_data, dict):
            errors.append("Context data must be a dictionary")
            return errors
        
        # Validate required fields
        required_fields = ["browser_session_id", "tab_context_id"]
        for field in required_fields:
            if field not in context_data:
                errors.append(f"Context data missing required field: {field}")
            elif not isinstance(context_data[field], str) or not context_data[field].strip():
                errors.append(f"{field} must be a non-empty string")
        
        # Validate page URL
        if "page_url" in context_data and context_data["page_url"]:
            url_errors = self._validate_field_value(
                "page_url", context_data["page_url"],
                self._validation_rules["page_url"]
            )
            errors.extend(url_errors)
        
        # Validate viewport size
        if "viewport_size" in context_data:
            viewport = context_data["viewport_size"]
            if not isinstance(viewport, dict):
                errors.append("viewport_size must be a dictionary")
            else:
                if "width" in viewport:
                    if not isinstance(viewport["width"], int) or viewport["width"] <= 0:
                        errors.append("viewport_size.width must be a positive integer")
                
                if "height" in viewport:
                    if not isinstance(viewport["height"], int) or viewport["height"] <= 0:
                        errors.append("viewport_size.height must be a positive integer")
        
        return errors
    
    def _validate_fields(self, data: Dict[str, Any]) -> List[str]:
        """Validate individual fields against rules."""
        errors = []
        
        for field, rule in self._validation_rules.items():
            if field in data:
                field_errors = self._validate_field_value(field, data[field], rule)
                errors.extend(field_errors)
            elif rule.get("required", False):
                errors.append(f"Required field missing: {field}")
        
        return errors
    
    def _validate_field_value(self, field: str, value: Any, rule: Dict[str, Any]) -> List[str]:
        """Validate a single field value against a rule."""
        errors = []
        
        # Type validation
        if "type" in rule:
            expected_type = rule["type"]
            if not isinstance(value, expected_type):
                if isinstance(expected_type, tuple):
                    type_names = [t.__name__ for t in expected_type]
                    errors.append(f"{field} must be one of types: {', '.join(type_names)}")
                else:
                    errors.append(f"{field} must be of type {expected_type.__name__}")
                return errors
        
        # String-specific validations
        if isinstance(value, str):
            if "min_length" in rule and len(value) < rule["min_length"]:
                errors.append(f"{field} must be at least {rule['min_length']} characters long")
            
            if "max_length" in rule and len(value) > rule["max_length"]:
                errors.append(f"{field} must be at most {rule['max_length']} characters long")
            
            if "pattern" in rule and not re.match(rule["pattern"], value):
                errors.append(f"{field}: {rule['description']}")
        
        # Numeric validations
        if isinstance(value, (int, float)):
            if "min_value" in rule and value < rule["min_value"]:
                errors.append(f"{field} must be at least {rule['min_value']}")
            
            if "max_value" in rule and value > rule["max_value"]:
                errors.append(f"{field} must be at most {rule['max_value']}")
        
        # Allowed values validation
        if "allowed_values" in rule and value not in rule["allowed_values"]:
            errors.append(f"{field}: {rule['description']}")
        
        # Custom validator
        if "validator" in rule:
            try:
                if not rule["validator"](value):
                    errors.append(f"{field}: {rule['description']}")
            except Exception as e:
                errors.append(f"{field} validation error: {e}")
        
        return errors
    
    def _validate_business_logic(self, event: Dict[str, Any]) -> List[str]:
        """Validate business logic for telemetry events."""
        errors = []
        
        # Check timestamp is not in future
        if "timestamp" in event:
            try:
                event_time = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                if event_time > datetime.utcnow():
                    errors.append("Event timestamp cannot be in the future")
            except Exception:
                # Timestamp format error already caught by schema validation
                pass
        
        # Check consistency between success and error data
        success = event.get("quality_metrics", {}).get("success", True)
        has_error_data = "error_data" in event and event["error_data"]
        
        if success and has_error_data:
            errors.append("Successful event should not have error data")
        
        if not success and not has_error_data:
            errors.append("Failed event should have error data")
        
        return errors
    
    def _validate_uuid(self, value: str) -> bool:
        """Validate UUID format."""
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False
    
    def _validate_url(self, value: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(value)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _validate_timestamp(self, value: str) -> bool:
        """Validate timestamp format."""
        try:
            # Try ISO format first
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            try:
                # Try other common formats
                datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                return True
            except ValueError:
                return False


# Global validator instance
_default_validator = TelemetryDataValidator()


def validate_telemetry_data(
    data: Union[Dict[str, Any], TelemetryEvent],
    data_type: str = "event"
) -> List[str]:
    """
    Validate telemetry data using default validator.
    
    Args:
        data: Data to validate
        data_type: Type of data (event, performance, quality, strategy, error, context)
        
    Returns:
        List of validation errors (empty if valid)
    """
    if data_type == "event":
        return _default_validator.validate_telemetry_event(data)
    elif data_type == "performance":
        return _default_validator.validate_performance_metrics(data)
    elif data_type == "quality":
        return _default_validator.validate_quality_metrics(data)
    elif data_type == "strategy":
        return _default_validator.validate_strategy_metrics(data)
    elif data_type == "error":
        return _default_validator.validate_error_data(data)
    elif data_type == "context":
        return _default_validator.validate_context_data(data)
    else:
        raise ValueError(f"Unknown data type: {data_type}")


def is_valid_telemetry_data(
    data: Union[Dict[str, Any], TelemetryEvent],
    data_type: str = "event"
) -> bool:
    """
    Check if telemetry data is valid using default validator.
    
    Args:
        data: Data to validate
        data_type: Type of data
        
    Returns:
        True if data is valid
    """
    errors = validate_telemetry_data(data, data_type)
    return len(errors) == 0
