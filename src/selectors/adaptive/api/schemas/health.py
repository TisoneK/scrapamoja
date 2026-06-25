"""
Pydantic schemas for Health Status Display API endpoints.

These schemas define the request/response models for the health status API
as specified in Story 6.2: Selector Health Status Display.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from src.selectors.adaptive.services.health_status_service import HealthStatus


class SelectorHealthResponse(BaseModel):
    """Response model for individual selector health."""
    
    model_config = ConfigDict(from_attributes=True)
    
    selector_id: str = Field(description="The selector ID")
    status: HealthStatus = Field(description="Health status: healthy, degraded, or failed")
    confidence_score: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Confidence score between 0.0 and 1.0"
    )
    last_failure: Optional[datetime] = Field(
        default=None, 
        description="Timestamp of last failure"
    )
    recommended_action: str = Field(description="Recommended action based on status")
    alternatives: List[str] = Field(
        default_factory=list, 
        description="Alternative selector IDs"
    )


class SingleSelectorHealthResponse(BaseModel):
    """Response model for single selector health query."""
    
    selector_id: str = Field(description="The selector ID")
    status: HealthStatus = Field(description="Health status")
    confidence_score: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Confidence score"
    )
    last_failure: Optional[datetime] = Field(
        default=None, 
        description="Timestamp of last failure"
    )
    recommended_action: str = Field(description="Recommended action")
    alternatives: List[str] = Field(
        default_factory=list, 
        description="Alternative selectors"
    )
    history_summary: Optional[dict] = Field(
        default=None, 
        description="Optional: recent trend summary"
    )


class HealthDashboardResponse(BaseModel):
    """Response model for dashboard grouped by health status."""
    
    healthy: List[SelectorHealthResponse] = Field(
        default_factory=list, 
        description="Selectors with healthy status"
    )
    degraded: List[SelectorHealthResponse] = Field(
        default_factory=list, 
        description="Selectors with degraded status"
    )
    failed: List[SelectorHealthResponse] = Field(
        default_factory=list, 
        description="Selectors with failed status"
    )
    total: int = Field(description="Total number of selectors")
    last_updated: datetime = Field(description="Timestamp of last update")


class HealthStatusUpdateMessage(BaseModel):
    """WebSocket message for health status changes."""
    
    type: str = Field(default="health_status_update", description="Message type")
    selector_id: str = Field(description="Selector ID")
    old_status: Optional[HealthStatus] = Field(
        default=None, 
        description="Previous health status"
    )
    new_status: HealthStatus = Field(description="New health status")
    confidence_score: float = Field(description="Current confidence score")
    timestamp: datetime = Field(description="Timestamp of update")


class HealthStatusConfigResponse(BaseModel):
    """Response model for health status configuration."""
    
    healthy_threshold: float = Field(description="Threshold for healthy status")
    degraded_threshold: float = Field(description="Threshold for degraded status")
    failed_threshold: float = Field(description="Threshold for failed status")
