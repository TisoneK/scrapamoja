"""
Audit Trail API Schemas.

Pydantic models for audit trail API requests and responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    """Audit event response model."""
    
    id: int
    action_type: str
    timestamp: Optional[str] = None
    selector_id: Optional[str] = None
    selector: str
    user_id: str
    failure_id: Optional[int] = None
    context_snapshot: Optional[Dict[str, Any]] = None
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    confidence_at_time: Optional[float] = None
    reason: Optional[str] = None
    suggested_alternative: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    
    @classmethod
    def from_audit_event(cls, audit_event) -> "AuditEventResponse":
        """Create response model from audit event."""
        return cls(
            id=audit_event.id,
            action_type=audit_event.action_type,
            timestamp=audit_event.timestamp.isoformat() if audit_event.timestamp else None,
            selector_id=audit_event.selector_id,
            selector=audit_event.selector,
            user_id=audit_event.user_id,
            failure_id=audit_event.failure_id,
            context_snapshot=audit_event.context_snapshot,
            before_state=audit_event.before_state,
            after_state=audit_event.after_state,
            confidence_at_time=audit_event.confidence_at_time,
            reason=audit_event.reason,
            suggested_alternative=audit_event.suggested_alternative,
            notes=audit_event.notes,
            created_at=audit_event.created_at.isoformat() if audit_event.created_at else None,
        )


class ConnectedDecisionResponse(BaseModel):
    """Connected decision response model."""
    
    type: str = Field(..., description="Type of connection (approval_after_rejection, rejection_after_approval)")
    selector_id: str
    time_difference: str = Field(..., description="Time difference between events")
    approval_event: Optional[AuditEventResponse] = None
    rejection_event: Optional[AuditEventResponse] = None


class AuditTrailResponse(BaseModel):
    """Audit trail response model."""
    
    events: List[AuditEventResponse]
    total_count: int
    filters_applied: Dict[str, Any]


class SelectorAuditTrailResponse(BaseModel):
    """Selector audit trail response model."""
    
    selector_id: str
    events: List[AuditEventResponse]
    event_count: int
    user_summary: Dict[str, Any]
    action_type_summary: Dict[str, int]
    connected_decisions: Optional[List[ConnectedDecisionResponse]] = None


class UserDecisionHistoryResponse(BaseModel):
    """User decision history response model."""
    
    user_id: str
    events: List[AuditEventResponse]
    event_count: int
    filters_applied: Dict[str, Any]


class AuditTrailSummaryResponse(BaseModel):
    """Audit trail summary response model."""
    
    total_events: int
    unique_users: int
    action_counts: Dict[str, int]
    user_activity: Dict[str, Dict[str, Any]]
    date_range: Dict[str, Optional[str]]
    average_approval_confidence: Optional[float] = None


# ===================
# Story 6.3: Query Audit History Schemas
# ===================

class AuditQueryParamsRequest(BaseModel):
    """Request parameters for audit query."""
    
    selector_id: Optional[str] = Field(None, description="Filter by selector ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    start_date: Optional[str] = Field(None, description="Start date for filtering (ISO format)")
    end_date: Optional[str] = Field(None, description="End date for filtering (ISO format)")
    action_types: Optional[List[str]] = Field(None, description="Filter by action types")
    # Pagination
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of events to return")
    offset: int = Field(0, ge=0, description="Number of events to skip")
    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    # Sorting
    sort_by: str = Field("timestamp", description="Sort field: timestamp, user_id, selector_id, action_type")
    sort_order: str = Field("desc", description="Sort order: asc, desc")


class AuditQueryResponse(BaseModel):
    """Response model for audit query with pagination."""
    
    events: List[AuditEventResponse]
    total_count: int
    has_more: bool
    next_cursor: Optional[str] = None
    filters_applied: Dict[str, Any]


class SelectorAuditQueryResponse(BaseModel):
    """Response model for selector-specific audit query."""
    
    selector_id: str
    events: List[AuditEventResponse]
    total_count: int
    has_more: bool
    next_cursor: Optional[str] = None
    filters_applied: Dict[str, Any]


class UserAuditQueryResponse(BaseModel):
    """Response model for user-specific audit query."""
    
    user_id: str
    events: List[AuditEventResponse]
    total_count: int
    has_more: bool
    next_cursor: Optional[str] = None
    filters_applied: Dict[str, Any]


class DateRangeQueryResponse(BaseModel):
    """Response model for date range audit query."""
    
    start_date: str
    end_date: str
    events: List[AuditEventResponse]
    total_count: int
    has_more: bool
    next_cursor: Optional[str] = None
    filters_applied: Dict[str, Any]
