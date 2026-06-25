"""
JSON schema validation for navigation data models

Provides schema validation for Navigation & Routing Intelligence system following
Constitution Principle V - Production Resilience.
"""

import json
from typing import Dict, Any, Optional
from jsonschema import validate, ValidationError, Draft7Validator
from .exceptions import ValidationError as NavigationValidationError


class NavigationSchemaValidator:
    """Schema validator for navigation data models"""
    
    def __init__(self):
        """Initialize with navigation schemas"""
        self.schemas = self._load_schemas()
        self.validators = {
            name: Draft7Validator(schema) 
            for name, schema in self.schemas.items()
        }
    
    def _load_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Load JSON schemas for navigation models"""
        return {
            "NavigationRoute": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": [
                    "route_id", "source_url", "destination_url", 
                    "route_type", "traversal_method"
                ],
                "properties": {
                    "route_id": {"type": "string", "minLength": 1},
                    "source_url": {"type": "string", "minLength": 1},
                    "destination_url": {"type": "string", "minLength": 1},
                    "route_type": {
                        "type": "string",
                        "enum": ["link", "form", "api", "client", "js"]
                    },
                    "traversal_method": {
                        "type": "string",
                        "enum": ["click", "form_submit", "api_call", "client_route", "js_exec"]
                    },
                    "selector_confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "detection_risk": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "interaction_requirements": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["interaction_type", "element_selector"],
                            "properties": {
                                "interaction_type": {"type": "string"},
                                "element_selector": {"type": "string"},
                                "required_data": {"type": "object"},
                                "timing_delay": {"type": "number", "minimum": 0.0}
                            }
                        }
                    },
                    "timing_constraints": {
                        "type": "object",
                        "properties": {
                            "min_delay": {"type": "number", "minimum": 0.0},
                            "max_delay": {"type": "number", "minimum": 0.0},
                            "interaction_delay": {"type": "number", "minimum": 0.0},
                            "page_load_wait": {"type": "number", "minimum": 0.0}
                        }
                    },
                    "metadata": {"type": "object"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                    "last_validated": {"type": "string", "format": "date-time"}
                }
            },
            
            "RouteGraph": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["graph_id", "routes", "adjacency_matrix"],
                "properties": {
                    "graph_id": {"type": "string", "minLength": 1},
                    "routes": {
                        "type": "object",
                        "patternProperties": {
                            ".*": {"$ref": "#/definitions/NavigationRoute"}
                        }
                    },
                    "adjacency_matrix": {
                        "type": "object",
                        "patternProperties": {
                            ".*": {
                                "type": "object",
                                "patternProperties": {
                                    ".*": {"type": "number", "minimum": 0.0}
                                }
                            }
                        }
                    },
                    "graph_metadata": {"type": "object"},
                    "last_updated": {"type": "string", "format": "date-time"},
                    "created_at": {"type": "string", "format": "date-time"}
                },
                "definitions": {
                    "NavigationRoute": {"$ref": "#/definitions/NavigationRouteRef"}
                },
                "definitions": {
                    "NavigationRouteRef": {
                        "type": "object",
                        "required": [
                            "route_id", "source_url", "destination_url", 
                            "route_type", "traversal_method"
                        ],
                        "properties": {
                            "route_id": {"type": "string", "minLength": 1},
                            "source_url": {"type": "string", "minLength": 1},
                            "destination_url": {"type": "string", "minLength": 1},
                            "route_type": {
                                "type": "string",
                                "enum": ["link", "form", "api", "client", "js"]
                            },
                            "traversal_method": {
                                "type": "string",
                                "enum": ["click", "form_submit", "api_call", "client_route", "js_exec"]
                            }
                        }
                    }
                }
            },
            
            "NavigationContext": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["context_id", "session_id", "current_page"],
                "properties": {
                    "context_id": {"type": "string", "minLength": 1},
                    "session_id": {"type": "string", "minLength": 1},
                    "current_page": {
                        "type": "object",
                        "required": ["url"],
                        "properties": {
                            "url": {"type": "string", "minLength": 1},
                            "title": {"type": "string"},
                            "page_type": {"type": "string"},
                            "load_time": {"type": "number", "minimum": 0.0},
                            "dom_elements_count": {"type": "integer", "minimum": 0},
                            "has_dynamic_content": {"type": "boolean"},
                            "requires_authentication": {"type": "boolean"},
                            "last_accessed": {"type": "string", "format": "date-time"}
                        }
                    },
                    "navigation_history": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "session_data": {"type": "object"},
                    "authentication_state": {
                        "type": "object",
                        "properties": {
                            "is_authenticated": {"type": "boolean"},
                            "auth_method": {"type": "string"},
                            "auth_domain": {"type": "string"},
                            "session_id": {"type": "string"},
                            "user_agent": {"type": "string"},
                            "expires_at": {"type": "string", "format": "date-time"},
                            "permissions": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    "correlation_id": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                    "pages_visited": {"type": "integer", "minimum": 0},
                    "total_navigation_time": {"type": "number", "minimum": 0.0},
                    "successful_navigations": {"type": "integer", "minimum": 0},
                    "failed_navigations": {"type": "integer", "minimum": 0}
                }
            },
            
            "PathPlan": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["plan_id", "source_context", "target_destination"],
                "properties": {
                    "plan_id": {"type": "string", "minLength": 1},
                    "source_context": {"type": "string", "minLength": 1},
                    "target_destination": {"type": "string", "minLength": 1},
                    "route_sequence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["step_number", "route_id", "action_type"],
                            "properties": {
                                "step_number": {"type": "integer", "minimum": 1},
                                "route_id": {"type": "string", "minLength": 1},
                                "action_type": {"type": "string", "minLength": 1},
                                "target_selector": {"type": "string"},
                                "target_url": {"type": "string"},
                                "expected_delay": {"type": "number", "minimum": 0.0},
                                "interaction_data": {"type": "object"},
                                "step_description": {"type": "string"}
                            }
                        }
                    },
                    "total_risk_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "estimated_duration": {"type": "number", "minimum": 0.0},
                    "fallback_plans": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "plan_metadata": {"type": "object"},
                    "status": {
                        "type": "string",
                        "enum": ["planned", "executing", "completed", "failed", "aborted"]
                    },
                    "current_step": {"type": "integer", "minimum": 0},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                    "execution_started": {"type": "string", "format": "date-time"},
                    "execution_completed": {"type": "string", "format": "date-time"}
                }
            },
            
            "NavigationEvent": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["event_id", "route_id", "context_before", "context_after"],
                "properties": {
                    "event_id": {"type": "string", "minLength": 1},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "route_id": {"type": "string", "minLength": 1},
                    "context_before": {"type": "string", "minLength": 1},
                    "context_after": {"type": "string", "minLength": 1},
                    "outcome": {
                        "type": "string",
                        "enum": ["success", "failure", "timeout", "detected", "redirected"]
                    },
                    "performance_metrics": {
                        "type": "object",
                        "properties": {
                            "duration_seconds": {"type": "number", "minimum": 0.0},
                            "cpu_usage_percent": {"type": "number", "minimum": 0.0},
                            "memory_usage_mb": {"type": "number", "minimum": 0.0},
                            "network_requests_count": {"type": "integer", "minimum": 0},
                            "dom_changes_count": {"type": "integer", "minimum": 0},
                            "javascript_errors_count": {"type": "integer", "minimum": 0},
                            "console_warnings_count": {"type": "integer", "minimum": 0},
                            "page_load_time": {"type": "number", "minimum": 0.0},
                            "render_time": {"type": "number", "minimum": 0.0}
                        }
                    },
                    "error_details": {"type": "string"},
                    "error_code": {"type": "string"},
                    "error_stack_trace": {"type": "string"},
                    "user_agent": {"type": "string"},
                    "page_url_before": {"type": "string"},
                    "page_url_after": {"type": "string"},
                    "session_id": {"type": "string"},
                    "correlation_id": {"type": "string"},
                    "detection_triggers": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "stealth_score_before": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "stealth_score_after": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "metadata": {"type": "object"}
                }
            }
        }
    
    def validate(self, data: Dict[str, Any], schema_name: str) -> bool:
        """Validate data against specified schema"""
        if schema_name not in self.schemas:
            raise NavigationValidationError(
                f"Unknown schema: {schema_name}",
                "UNKNOWN_SCHEMA"
            )
        
        try:
            validate(instance=data, schema=self.schemas[schema_name])
            return True
        except ValidationError as e:
            raise NavigationValidationError(
                f"Schema validation failed: {str(e)}",
                "SCHEMA_VALIDATION_ERROR",
                {
                    "schema_name": schema_name,
                    "validation_error": str(e),
                    "data": data
                }
            )
    
    def validate_route(self, route_data: Dict[str, Any]) -> bool:
        """Validate NavigationRoute data"""
        return self.validate(route_data, "NavigationRoute")
    
    def validate_graph(self, graph_data: Dict[str, Any]) -> bool:
        """Validate RouteGraph data"""
        return self.validate(graph_data, "RouteGraph")
    
    def validate_context(self, context_data: Dict[str, Any]) -> bool:
        """Validate NavigationContext data"""
        return self.validate(context_data, "NavigationContext")
    
    def validate_plan(self, plan_data: Dict[str, Any]) -> bool:
        """Validate PathPlan data"""
        return self.validate(plan_data, "PathPlan")
    
    def validate_event(self, event_data: Dict[str, Any]) -> bool:
        """Validate NavigationEvent data"""
        return self.validate(event_data, "NavigationEvent")
    
    def get_validation_errors(self, data: Dict[str, Any], schema_name: str) -> list:
        """Get validation errors without raising exception"""
        if schema_name not in self.validators:
            return [f"Unknown schema: {schema_name}"]
        
        errors = []
        for error in self.validators[schema_name].iter_errors(data):
            errors.append(f"{'/'.join(str(p) for p in error.path)}: {error.message}")
        
        return errors


# Global validator instance
navigation_validator = NavigationSchemaValidator()
