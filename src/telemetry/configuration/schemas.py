"""
JSON Schema Validation for Telemetry Data

Schema definitions and validation utilities for telemetry events,
metrics, and configuration data.
"""

import json
import jsonschema
from typing import Dict, Any, List
from pathlib import Path

# Telemetry Event Schema
TELEMETRY_EVENT_SCHEMA = {
    "type": "object",
    "required": [
        "event_id",
        "correlation_id", 
        "selector_name",
        "timestamp",
        "operation_type"
    ],
    "properties": {
        "event_id": {
            "type": "string",
            "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "correlation_id": {"type": "string", "minLength": 1},
        "selector_name": {"type": "string", "minLength": 1},
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        "operation_type": {
            "type": "string",
            "enum": ["resolution", "validation", "execution", "cleanup"]
        },
        "performance_metrics": {"$ref": "#/definitions/performance_metrics"},
        "quality_metrics": {"$ref": "#/definitions/quality_metrics"},
        "strategy_metrics": {"$ref": "#/definitions/strategy_metrics"},
        "error_data": {"$ref": "#/definitions/error_data"},
        "context_data": {"$ref": "#/definitions/context_data"}
    },
    "definitions": {
        "performance_metrics": {
            "type": "object",
            "properties": {
                "resolution_time_ms": {"type": "number", "minimum": 0},
                "strategy_execution_time_ms": {"type": "number", "minimum": 0},
                "total_duration_ms": {"type": "number", "minimum": 0},
                "memory_usage_mb": {"type": "number", "minimum": 0, "maximum": 1024},
                "cpu_usage_percent": {"type": "number", "minimum": 0, "maximum": 100},
                "network_requests_count": {"type": "integer", "minimum": 0},
                "dom_operations_count": {"type": "integer", "minimum": 0}
            }
        },
        "quality_metrics": {
            "type": "object",
            "properties": {
                "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "success": {"type": "boolean"},
                "elements_found": {"type": "integer", "minimum": 0},
                "strategy_success_rate": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "drift_detected": {"type": "boolean"},
                "fallback_used": {"type": "boolean"},
                "validation_passed": {"type": "boolean"}
            }
        },
        "strategy_metrics": {
            "type": "object",
            "required": ["primary_strategy"],
            "properties": {
                "primary_strategy": {"type": "string", "minLength": 1},
                "secondary_strategies": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "strategy_execution_order": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "strategy_success_by_type": {
                    "type": "object",
                    "patternProperties": {
                        ".*": {"type": "boolean"}
                    }
                },
                "strategy_timing_by_type": {
                    "type": "object",
                    "patternProperties": {
                        ".*": {"type": "number", "minimum": 0}
                    }
                },
                "strategy_switches_count": {"type": "integer", "minimum": 0}
            }
        },
        "error_data": {
            "type": "object",
            "properties": {
                "error_type": {"type": "string", "minLength": 1},
                "error_message": {"type": "string", "minLength": 1},
                "stack_trace": {"type": "string"},
                "retry_attempts": {"type": "integer", "minimum": 0},
                "fallback_attempts": {"type": "integer", "minimum": 0},
                "recovery_successful": {"type": "boolean"}
            }
        },
        "context_data": {
            "type": "object",
            "properties": {
                "browser_session_id": {"type": "string", "minLength": 1},
                "tab_context_id": {"type": "string", "minLength": 1},
                "page_url": {
                    "type": "string",
                    "format": "uri"
                },
                "page_title": {"type": "string"},
                "user_agent": {"type": "string"},
                "viewport_size": {
                    "type": "object",
                    "properties": {
                        "width": {"type": "integer", "minimum": 1},
                        "height": {"type": "integer", "minimum": 1}
                    },
                    "required": ["width", "height"]
                },
                "timestamp_context": {"type": "string"}
            }
        }
    }
}

# Alert Schema
ALERT_SCHEMA = {
    "type": "object",
    "required": [
        "alert_id",
        "alert_type",
        "severity",
        "selector_name",
        "threshold_name",
        "threshold_value",
        "actual_value",
        "timestamp",
        "description"
    ],
    "properties": {
        "alert_id": {
            "type": "string",
            "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "alert_type": {
            "type": "string",
            "enum": ["performance", "quality", "health", "usage"]
        },
        "severity": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"]
        },
        "selector_name": {"type": "string", "minLength": 1},
        "threshold_name": {"type": "string", "minLength": 1},
        "threshold_value": {"type": "number", "minimum": 0},
        "actual_value": {"type": "number"},
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        "description": {"type": "string", "minLength": 1},
        "acknowledged": {"type": "boolean"},
        "resolved": {"type": "boolean"}
    }
}

# Configuration Schema
CONFIGURATION_SCHEMA = {
    "type": "object",
    "required": ["collection_enabled"],
    "properties": {
        "collection_enabled": {"type": "boolean"},
        "storage_type": {
            "type": "string",
            "enum": ["json", "influxdb"]
        },
        "buffer_size": {
            "type": "integer",
            "minimum": 100,
            "maximum": 10000
        },
        "flush_interval_seconds": {
            "type": "integer",
            "minimum": 1,
            "maximum": 300
        },
        "retention_days": {
            "type": "integer",
            "minimum": 1,
            "maximum": 3650
        },
        "performance_overhead_threshold": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "correlation_id_enabled": {"type": "boolean"}
    }
}


class TelemetrySchemaValidator:
    """Validator for telemetry data using JSON schemas."""
    
    def __init__(self):
        self._telemetry_validator = jsonschema.Draft7Validator(TELEMETRY_EVENT_SCHEMA)
        self._alert_validator = jsonschema.Draft7Validator(ALERT_SCHEMA)
        self._config_validator = jsonschema.Draft7Validator(CONFIGURATION_SCHEMA)
    
    def validate_telemetry_event(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate telemetry event data against schema.
        
        Args:
            data: Telemetry event data to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        for error in self._telemetry_validator.iter_errors(data):
            errors.append(f"{'.'.join(str(p) for p in error.path)}: {error.message}")
        return errors
    
    def validate_alert(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate alert data against schema.
        
        Args:
            data: Alert data to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        for error in self._alert_validator.iter_errors(data):
            errors.append(f"{'.'.join(str(p) for p in error.path)}: {error.message}")
        return errors
    
    def validate_configuration(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate configuration data against schema.
        
        Args:
            data: Configuration data to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        for error in self._config_validator.iter_errors(data):
            errors.append(f"{'.'.join(str(p) for p in error.path)}: {error.message}")
        return errors
    
    def is_valid_telemetry_event(self, data: Dict[str, Any]) -> bool:
        """Check if telemetry event data is valid."""
        return len(self.validate_telemetry_event(data)) == 0
    
    def is_valid_alert(self, data: Dict[str, Any]) -> bool:
        """Check if alert data is valid."""
        return len(self.validate_alert(data)) == 0
    
    def is_valid_configuration(self, data: Dict[str, Any]) -> bool:
        """Check if configuration data is valid."""
        return len(self.validate_configuration(data)) == 0


# Global validator instance
validator = TelemetrySchemaValidator()


def validate_telemetry_event(data: Dict[str, Any]) -> List[str]:
    """Validate telemetry event data."""
    return validator.validate_telemetry_event(data)


def validate_alert(data: Dict[str, Any]) -> List[str]:
    """Validate alert data."""
    return validator.validate_alert(data)


def validate_configuration(data: Dict[str, Any]) -> List[str]:
    """Validate configuration data."""
    return validator.validate_configuration(data)


def is_valid_telemetry_event(data: Dict[str, Any]) -> bool:
    """Check if telemetry event data is valid."""
    return validator.is_valid_telemetry_event(data)


def is_valid_alert(data: Dict[str, Any]) -> bool:
    """Check if alert data is valid."""
    return validator.is_valid_alert(data)


def is_valid_configuration(data: Dict[str, Any]) -> bool:
    """Check if configuration data is valid."""
    return validator.is_valid_configuration(data)
