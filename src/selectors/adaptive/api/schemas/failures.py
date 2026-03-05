"""
Pydantic schemas for Failure API endpoints.

These schemas define the request/response models for the failures API
as specified in Story 4.1: View Proposed Selectors with Visual Preview.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ConfidenceScoreMixin(BaseModel):
    """Mixin for confidence score information."""
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    confidence_tier: Optional[str] = Field(None, description="Confidence tier: high, medium, low")
    scoring_breakdown: Optional[Dict[str, Any]] = Field(None, description="Detailed scoring breakdown")


class BlastRadiusInfo(BaseModel):
    """Blast radius impact information."""
    affected_count: int = Field(default=0, description="Number of affected selectors")
    affected_sports: List[str] = Field(default_factory=list, description="Sports that would be affected")
    severity: str = Field(default="low", description="Impact severity: low, medium, high, critical")
    container_path: str = Field(default="", description="Shared container path")


class AlternativeSelectorSchema(BaseModel):
    """Schema for an alternative selector proposal."""
    selector: str = Field(description="The alternative selector string")
    strategy: str = Field(description="Selector strategy type: css, xpath, text, attribute")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    blast_radius: Optional[BlastRadiusInfo] = Field(None, description="Blast radius impact")
    highlight_css: Optional[str] = Field(None, description="CSS for visual highlighting")
    is_custom: bool = Field(default=False, description="Whether this is a custom (user-created) selector")
    custom_notes: Optional[str] = Field(None, description="Notes from custom selector creator")
    
    class Config:
        from_attributes = True


class FailureDetailSchema(BaseModel):
    """Schema for failure detail response."""
    failure_id: int = Field(description="Unique failure event ID")
    selector_id: str = Field(description="The selector that failed")
    failed_selector: str = Field(description="The failed selector string")
    recipe_id: Optional[str] = Field(None, description="Associated recipe ID")
    sport: Optional[str] = Field(None, description="Sport context")
    site: Optional[str] = Field(None, description="Site identifier")
    timestamp: datetime = Field(description="When the failure occurred")
    error_type: str = Field(description="Error type classification")
    failure_reason: Optional[str] = Field(None, description="Detailed failure reason")
    severity: str = Field(default="minor", description="Failure severity")
    snapshot_id: Optional[int] = Field(None, description="Associated snapshot ID")
    alternatives: List[AlternativeSelectorSchema] = Field(
        default_factory=list, 
        description="Proposed alternative selectors"
    )
    flagged: bool = Field(default=False, description="Whether failure is flagged for developer review")
    flag_note: Optional[str] = Field(None, description="Note from flagging user")
    flagged_at: Optional[datetime] = Field(None, description="When the failure was flagged")
    
    class Config:
        from_attributes = True


class FailureListItemSchema(BaseModel):
    """Schema for failure list item (summary view)."""
    failure_id: int
    selector_id: str
    failed_selector: str
    sport: Optional[str] = None
    site: Optional[str] = None
    timestamp: datetime
    error_type: str
    severity: str
    has_alternatives: bool = Field(default=False, description="Whether alternatives are proposed")
    alternative_count: int = Field(default=0, description="Number of proposed alternatives")
    flagged: bool = Field(default=False, description="Whether failure is flagged for developer review")
    flag_note: Optional[str] = Field(None, description="Note from flagging user")
    
    class Config:
        from_attributes = True


class FailureListResponseSchema(BaseModel):
    """Schema for paginated failure list response."""
    data: List[FailureListItemSchema]
    total: int = Field(description="Total number of failures matching filters")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=20, description="Results per page")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Active filters")


class FailureDetailResponseSchema(BaseModel):
    """Schema for single failure detail response."""
    data: FailureDetailSchema


class ApprovalRequestSchema(BaseModel):
    """Schema for approving a proposed selector."""
    selector: str = Field(description="The selector to approve")
    notes: Optional[str] = Field(None, description="Optional approval notes")


class RejectionRequestSchema(BaseModel):
    """Schema for rejecting a proposed selector."""
    selector: str = Field(description="The selector to reject")
    reason: str = Field(description="Reason for rejection")
    suggested_alternative: Optional[str] = Field(None, description="Suggested alternative if any")


class ApprovalResponseSchema(BaseModel):
    """Schema for approval/rejection response."""
    success: bool
    message: str
    selector: str
    failure_id: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FlagRequestSchema(BaseModel):
    """Schema for flagging a selector for developer review."""
    note: str = Field(min_length=1, description="Note explaining why this needs developer review")


class FlagResponseSchema(BaseModel):
    """Schema for flag response."""
    success: bool
    message: str
    failure_id: int
    flagged: bool = True
    flag_note: str
    flagged_at: datetime = Field(default_factory=datetime.utcnow)


class CustomSelectorRequestSchema(BaseModel):
    """Schema for creating a custom selector."""
    selector_string: str = Field(min_length=1, description="The custom selector string")
    strategy_type: str = Field(description="Selector strategy type: css, xpath, text_anchor, attribute_match")
    notes: Optional[str] = Field(None, description="Optional notes about the custom selector approach")


class CustomSelectorResponseSchema(BaseModel):
    """Schema for custom selector response."""
    success: bool
    message: str
    failure_id: int
    selector: str
    strategy_type: str
    is_custom: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


# RFC 7807 Problem Details for error responses
class ProblemDetailSchema(BaseModel):
    """RFC 7807 Problem Details error response."""
    type: str = Field(description="URI reference for the problem type")
    title: str = Field(description="Short human-readable summary")
    detail: str = Field(description="Human-readable explanation")
    status: int = Field(description="HTTP status code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "about:blank",
                "title": "Not Found",
                "detail": "Failure with ID 123 not found",
                "status": 404
            }
        }
