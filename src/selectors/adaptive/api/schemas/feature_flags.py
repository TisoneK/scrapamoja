"""
Pydantic schemas for Feature Flag API endpoints.

These schemas define the request/response models for sport-based feature flags
as specified in Story 8.1: Sport-Based Feature Flags.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FeatureFlagCreateSchema(BaseModel):
    """Schema for creating a new feature flag."""
    sport: str = Field(
        min_length=1, 
        max_length=100, 
        description="Sport name (e.g., basketball, tennis)"
    )
    site: Optional[str] = Field(
        None, 
        max_length=255,
        description="Optional site name for site-specific flags"
    )
    enabled: bool = Field(
        default=False, 
        description="Whether adaptive system is enabled for this sport/site"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sport": "basketball",
                "site": "flashscore",
                "enabled": True
            }
        }


class FeatureFlagUpdateSchema(BaseModel):
    """Schema for updating a feature flag."""
    enabled: bool = Field(
        description="New enabled state for the feature flag"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True
            }
        }


class FeatureFlagResponseSchema(BaseModel):
    """Schema for feature flag response."""
    id: int = Field(description="Feature flag ID")
    sport: str = Field(description="Sport name")
    site: Optional[str] = Field(description="Site name (null for global flags)")
    enabled: bool = Field(description="Whether adaptive system is enabled")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "sport": "basketball",
                "site": None,
                "enabled": True,
                "created_at": "2026-03-06T10:00:00Z",
                "updated_at": "2026-03-06T10:00:00Z"
            }
        }


class FeatureFlagListResponseSchema(BaseModel):
    """Schema for list of feature flags response."""
    data: List[FeatureFlagResponseSchema] = Field(description="List of feature flags")
    count: int = Field(description="Total number of feature flags")

    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {
                        "id": 1,
                        "sport": "basketball",
                        "site": None,
                        "enabled": True,
                        "created_at": "2026-03-06T10:00:00Z",
                        "updated_at": "2026-03-06T10:00:00Z"
                    }
                ],
                "count": 1
            }
        }


class FeatureFlagToggleSchema(BaseModel):
    """Schema for toggling a sport flag."""
    enabled: bool = Field(
        description="New enabled state after toggle"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True
            }
        }


class FeatureFlagCheckSchema(BaseModel):
    """Schema for checking feature flag status."""
    sport: str = Field(
        min_length=1,
        max_length=100,
        description="Sport name to check"
    )
    site: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional site name to check"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sport": "basketball",
                "site": "flashscore"
            }
        }


class FeatureFlagCheckResponseSchema(BaseModel):
    """Schema for feature flag check response."""
    sport: str = Field(description="Sport name")
    site: Optional[str] = Field(description="Site name (null for global check)")
    enabled: bool = Field(description="Whether adaptive system is enabled")
    flag_exists: bool = Field(description="Whether a flag exists for this sport/site")

    class Config:
        json_schema_extra = {
            "example": {
                "sport": "basketball",
                "site": "flashscore",
                "enabled": True,
                "flag_exists": True
            }
        }


class FeatureFlagBulkCreateSchema(BaseModel):
    """Schema for bulk creating feature flags."""
    flags: List[FeatureFlagCreateSchema] = Field(
        description="List of feature flags to create"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "flags": [
                    {
                        "sport": "basketball",
                        "enabled": False
                    },
                    {
                        "sport": "tennis",
                        "enabled": False
                    }
                ]
            }
        }


class EnabledSportsResponseSchema(BaseModel):
    """Schema for enabled sports list response."""
    sports: List[str] = Field(description="List of sports with adaptive system enabled")
    count: int = Field(description="Total number of enabled sports")

    class Config:
        json_schema_extra = {
            "example": {
                "sports": ["basketball", "tennis"],
                "count": 2
            }
        }


class FeatureFlagStatsResponseSchema(BaseModel):
    """Schema for feature flag statistics response."""
    total_flags: int = Field(description="Total number of feature flags")
    enabled_flags: int = Field(description="Number of enabled flags")
    disabled_flags: int = Field(description="Number of disabled flags")
    global_flags: int = Field(description="Number of global (non-site-specific) flags")
    site_specific_flags: int = Field(description="Number of site-specific flags")
    unique_sports: int = Field(description="Number of unique sports with flags")

    class Config:
        json_schema_extra = {
            "example": {
                "total_flags": 15,
                "enabled_flags": 3,
                "disabled_flags": 12,
                "global_flags": 10,
                "site_specific_flags": 5,
                "unique_sports": 5
            }
        }
