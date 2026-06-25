"""
Pydantic schemas for Confidence Score Query API endpoints.

These schemas define the request/response models for the confidence query API
as specified in Story 6.1: Confidence Score Query API.
"""

from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, ConfigDict


class ConfidenceScoreResponse(BaseModel):
    """Response model for single selector confidence query."""

    model_config = ConfigDict(from_attributes=True)

    selector_id: str = Field(description="The selector ID")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    last_updated: datetime = Field(description="Timestamp of last score update")
    is_estimated: bool = Field(default=False, description="True if no historical data, score is estimated")


class BatchConfidenceQuery(BaseModel):
    """Request model for batch confidence query."""

    selector_ids: List[str] = Field(
        ..., min_length=1, max_length=100, description="List of selector IDs to query"
    )


class BatchConfidenceResponse(BaseModel):
    """Response model for batch confidence query."""

    results: Dict[str, Optional[ConfidenceScoreResponse]] = Field(
        description="Results keyed by selector ID"
    )
    missing_selectors: List[str] = Field(
        default_factory=list, description="Selectors not found in the system"
    )


class PaginatedConfidenceQuery(BaseModel):
    """Request model for paginated confidence query."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=50, ge=1, le=100, description="Results per page")


class PaginatedConfidenceResponse(BaseModel):
    """Response model for paginated confidence query."""

    results: List[ConfidenceScoreResponse] = Field(description="List of confidence scores")
    total: int = Field(description="Total number of selectors")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Results per page")
    total_pages: int = Field(description="Total number of pages")
