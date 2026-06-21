"""
Telemetry Event Model

Represents a single selector operation event with comprehensive metrics
following the data model specification.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class TelemetryEvent(BaseModel):
    """
    Represents a single selector operation event with comprehensive metrics.
    
    This is the core entity for telemetry data collection, containing all
    information about a selector operation including performance metrics,
    quality metrics, strategy usage, and error data.
    """
    
    event_id: str = Field(..., description="Unique identifier for the event")
    correlation_id: str = Field(..., description="Links to specific selector operation/session")
    selector_name: str = Field(..., description="Name/identifier of the selector")
    timestamp: datetime = Field(..., description="When the event occurred (UTC)")
    operation_type: str = Field(..., description="Type of selector operation")
    performance_metrics: Optional[Dict[str, Any]] = Field(None, description="Timing and resource usage")
    quality_metrics: Optional[Dict[str, Any]] = Field(None, description="Confidence scores and success indicators")
    strategy_metrics: Optional[Dict[str, Any]] = Field(None, description="Strategy usage and effectiveness")
    error_data: Optional[Dict[str, Any]] = Field(None, description="Error information if operation failed")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Execution context information")
    
    @validator('event_id')
    def validate_event_id(cls, v):
        """Validate event ID is a valid UUID."""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("event_id must be a valid UUID")
        return v
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp is not in the future."""
        if v > datetime.utcnow():
            raise ValueError("timestamp cannot be in the future")
        return v
    
    @validator('selector_name')
    def validate_selector_name(cls, v):
        """Validate selector name is not empty."""
        if not v or not v.strip():
            raise ValueError("selector_name cannot be empty")
        return v.strip()
    
    @validator('operation_type')
    def validate_operation_type(cls, v):
        """Validate operation type is supported."""
        valid_types = ["resolution", "validation", "execution", "cleanup"]
        if v not in valid_types:
            raise ValueError(f"operation_type must be one of {valid_types}")
        return v
    
    @validator('performance_metrics')
    def validate_performance_metrics(cls, v):
        """Validate performance metrics structure."""
        if v is None:
            return v
        
        required_fields = {
            "resolution_time_ms": (int, float),
            "strategy_execution_time_ms": (int, float),
            "total_duration_ms": (int, float)
        }
        
        for field, field_type in required_fields.items():
            if field in v and not isinstance(v[field], field_type):
                raise ValueError(f"performance_metrics.{field} must be {field_type.__name__}")
            if field in v and v[field] < 0:
                raise ValueError(f"performance_metrics.{field} must be non-negative")
        
        return v
    
    @validator('quality_metrics')
    def validate_quality_metrics(cls, v):
        """Validate quality metrics structure."""
        if v is None:
            return v
        
        if "confidence_score" in v:
            if not isinstance(v["confidence_score"], (int, float)):
                raise ValueError("quality_metrics.confidence_score must be a number")
            if not 0.0 <= v["confidence_score"] <= 1.0:
                raise ValueError("quality_metrics.confidence_score must be between 0.0 and 1.0")
        
        if "elements_found" in v:
            if not isinstance(v["elements_found"], int):
                raise ValueError("quality_metrics.elements_found must be an integer")
            if v["elements_found"] < 0:
                raise ValueError("quality_metrics.elements_found must be non-negative")
        
        return v
    
    @validator('strategy_metrics')
    def validate_strategy_metrics(cls, v):
        """Validate strategy metrics structure."""
        if v is None:
            return v
        
        if "primary_strategy" in v:
            if not isinstance(v["primary_strategy"], str) or not v["primary_strategy"].strip():
                raise ValueError("strategy_metrics.primary_strategy must be a non-empty string")
        
        if "strategy_switches_count" in v:
            if not isinstance(v["strategy_switches_count"], int):
                raise ValueError("strategy_metrics.strategy_switches_count must be an integer")
            if v["strategy_switches_count"] < 0:
                raise ValueError("strategy_metrics.strategy_switches_count must be non-negative")
        
        return v
    
    @validator('error_data')
    def validate_error_data(cls, v):
        """Validate error data structure."""
        if v is None:
            return v
        
        if "error_type" in v:
            if not isinstance(v["error_type"], str) or not v["error_type"].strip():
                raise ValueError("error_data.error_type must be a non-empty string")
        
        if "error_message" in v:
            if not isinstance(v["error_message"], str) or not v["error_message"].strip():
                raise ValueError("error_data.error_message must be a non-empty string")
        
        if "retry_attempts" in v:
            if not isinstance(v["retry_attempts"], int):
                raise ValueError("error_data.retry_attempts must be an integer")
            if v["retry_attempts"] < 0:
                raise ValueError("error_data.retry_attempts must be non-negative")
        
        return v
    
    @validator('context_data')
    def validate_context_data(cls, v):
        """Validate context data structure."""
        if v is None:
            return v
        
        if "browser_session_id" in v:
            if not isinstance(v["browser_session_id"], str) or not v["browser_session_id"].strip():
                raise ValueError("context_data.browser_session_id must be a non-empty string")
        
        if "tab_context_id" in v:
            if not isinstance(v["tab_context_id"], str) or not v["tab_context_id"].strip():
                raise ValueError("context_data.tab_context_id must be a non-empty string")
        
        if "viewport_size" in v:
            viewport = v["viewport_size"]
            if not isinstance(viewport, dict):
                raise ValueError("context_data.viewport_size must be a dictionary")
            
            if "width" in viewport:
                if not isinstance(viewport["width"], int) or viewport["width"] <= 0:
                    raise ValueError("context_data.viewport_size.width must be a positive integer")
            
            if "height" in viewport:
                if not isinstance(viewport["height"], int) or viewport["height"] <= 0:
                    raise ValueError("context_data.viewport_size.height must be a positive integer")
        
        return v
    
    def has_metrics(self) -> bool:
        """Check if event has any metrics data."""
        return any([
            self.performance_metrics,
            self.quality_metrics,
            self.strategy_metrics,
            self.error_data,
            self.context_data
        ])
    
    def is_successful(self) -> bool:
        """Check if the operation was successful."""
        if self.error_data:
            return False
        if self.quality_metrics and "success" in self.quality_metrics:
            return self.quality_metrics["success"]
        return True
    
    def get_confidence_score(self) -> Optional[float]:
        """Get confidence score if available."""
        if self.quality_metrics and "confidence_score" in self.quality_metrics:
            return self.quality_metrics["confidence_score"]
        return None
    
    def get_resolution_time(self) -> Optional[float]:
        """Get resolution time if available."""
        if self.performance_metrics and "resolution_time_ms" in self.performance_metrics:
            return self.performance_metrics["resolution_time_ms"]
        return None
    
    def get_primary_strategy(self) -> Optional[str]:
        """Get primary strategy if available."""
        if self.strategy_metrics and "primary_strategy" in self.strategy_metrics:
            return self.strategy_metrics["primary_strategy"]
        return None
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True
