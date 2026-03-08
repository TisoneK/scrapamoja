"""
Pydantic schemas for User and View API endpoints.

These schemas define the request/response models for user preferences
and view mode management as specified in Story 7.2: Technical and Non-Technical Views.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class UserRoleSchema(BaseModel):
    """Schema for user role enum values."""
    OPERATIONS: str = "operations"
    DEVELOPER: str = "developer"
    ADMIN: str = "admin"

    @classmethod
    def get_all(cls) -> List[str]:
        """Get all valid role values."""
        return [cls.OPERATIONS, cls.DEVELOPER, cls.ADMIN]


class ViewModeSchema(BaseModel):
    """Schema for view mode enum values."""
    TECHNICAL: str = "technical"
    NON_TECHNICAL: str = "non_technical"

    @classmethod
    def get_all(cls) -> List[str]:
        """Get all valid view mode values."""
        return [cls.NON_TECHNICAL, cls.TECHNICAL]


class UserPreferenceCreateSchema(BaseModel):
    """Schema for creating a new user preference."""
    user_id: str = Field(min_length=1, max_length=100, description="Unique user identifier")
    role: str = Field(description="User role: operations, developer, admin")
    default_view: Optional[str] = Field(
        None, 
        description="Default view mode: technical, non_technical"
    )
    custom_settings: Optional[Dict[str, Any]] = Field(
        None, 
        description="Custom settings as key-value pairs"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "role": "operations",
                "default_view": "non_technical",
                "custom_settings": {"theme": "dark", "notifications": True}
            }
        }


class UserPreferenceUpdateSchema(BaseModel):
    """Schema for updating user preferences."""
    role: Optional[str] = Field(None, description="User role: operations, developer, admin")
    default_view: Optional[str] = Field(
        None, 
        description="Default view mode: technical, non_technical"
    )
    custom_settings: Optional[Dict[str, Any]] = Field(
        None, 
        description="Custom settings as key-value pairs"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "role": "developer",
                "default_view": "technical"
            }
        }


class UserPreferenceResponseSchema(BaseModel):
    """Schema for user preference response."""
    id: int = Field(description="Unique preference ID")
    user_id: str = Field(description="User identifier")
    role: str = Field(description="User role")
    default_view: str = Field(description="Default view mode")
    custom_settings: Dict[str, Any] = Field(default_factory=dict, description="Custom settings")
    last_view_mode: Optional[str] = Field(None, description="Last used view mode")
    view_mode_switches: int = Field(default=0, description="Total number of view mode switches")
    created_at: datetime = Field(description="When the preference was created")
    updated_at: datetime = Field(description="When the preference was last updated")

    class Config:
        from_attributes = True


class UserPreferencesResponseSchema(BaseModel):
    """Schema for user preferences list response."""
    data: UserPreferenceResponseSchema


class UserInfoResponseSchema(BaseModel):
    """Schema for user info response with view permissions."""
    data: Dict[str, Any] = Field(
        description="User information including role and available views",
        examples=[{
            "user_id": "user_123",
            "user_role": "operations",
            "default_view": "non_technical",
            "available_views": ["non_technical", "technical"],
            "permissions": ["approve", "reject", "escalate"]
        }]
    )


class ViewModeSwitchSchema(BaseModel):
    """Schema for switching view mode."""
    view_mode: str = Field(description="View mode to switch to: technical, non_technical")

    class Config:
        json_schema_extra = {
            "example": {
                "view_mode": "technical"
            }
        }


class ViewModeSwitchResponseSchema(BaseModel):
    """Schema for view mode switch response."""
    success: bool = Field(description="Whether the switch was successful")
    message: str = Field(description="Response message")
    previous_view_mode: Optional[str] = Field(None, description="Previous view mode")
    new_view_mode: str = Field(description="New view mode")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the switch occurred")


class ViewUsageAnalyticsSchema(BaseModel):
    """Schema for view usage analytics."""
    id: int = Field(description="Unique analytics entry ID")
    user_id: str = Field(description="User identifier")
    view_mode: str = Field(description="View mode used")
    action_count: int = Field(default=0, description="Number of actions in this view mode")
    session_duration_seconds: Optional[int] = Field(
        None, 
        description="Session duration in seconds"
    )
    session_start: datetime = Field(description="When the session started")
    session_end: Optional[datetime] = Field(None, description="When the session ended")
    created_at: datetime = Field(description="When this record was created")

    class Config:
        from_attributes = True


class ViewUsageAnalyticsListSchema(BaseModel):
    """Schema for view usage analytics list."""
    data: List[ViewUsageAnalyticsSchema]
    total: int = Field(description="Total number of entries")


# Non-technical view response schemas
class NonTechnicalFailureView(BaseModel):
    """Schema for non-technical failure view (simplified)."""
    failure_id: int = Field(description="Unique failure ID")
    description: str = Field(description="Plain language failure description")
    impact: str = Field(description="Business impact description")
    visual_preview: Optional[str] = Field(None, description="Base64 encoded visual preview image")
    suggested_action: Optional[str] = Field(None, description="Suggested action in plain language")
    
    class Config:
        from_attributes = True


class TechnicalFailureView(BaseModel):
    """Schema for technical failure view (detailed)."""
    failure_id: int = Field(description="Unique failure ID")
    selector: str = Field(description="The selector that failed")
    strategy: str = Field(description="Selector strategy type")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    dom_path: str = Field(description="DOM path to failed element")
    error: str = Field(description="Technical error message")
    snapshot_id: Optional[int] = Field(None, description="Associated snapshot ID")
    alternatives: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Proposed alternative selectors"
    )
    
    class Config:
        from_attributes = True


class ViewAdaptiveFailureResponse(BaseModel):
    """Schema for view-adaptive failure response."""
    failure: Dict[str, Any] = Field(
        description="Failure data with view-specific formatting",
        examples=[{
            "failure_id": 123,
            "non_technical": {
                "description": "Team scores cannot be extracted from the page",
                "impact": "High - affects live data updates",
                "visual_preview": "data:image/png;base64,..."
            },
            "technical": {
                "selector": ".team-score",
                "strategy": "CSS",
                "confidence": 0.85,
                "dom_path": "div.container > div.scores > span.team-score",
                "error": "Element not found in DOM"
            }
        }]
    )


# API key based role detection
class APIKeyRoleRequest(BaseModel):
    """Schema for requesting role by API key."""
    api_key: str = Field(min_length=1, description="API key to look up")


class APIKeyRoleResponse(BaseModel):
    """Schema for API key role response."""
    user_id: str = Field(description="Associated user ID")
    role: str = Field(description="User role")
    default_view: str = Field(description="Default view mode")
    valid: bool = Field(description="Whether the API key is valid")
