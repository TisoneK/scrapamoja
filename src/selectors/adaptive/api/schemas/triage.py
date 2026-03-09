"""
API schemas for fast triage operations.

Defines request/response models for:
- Optimized failure listing
- One-click approvals
- Bulk operations
- Performance metrics

Story: 7.3 - Fast Triage Workflow
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TriageSummarySchema(BaseModel):
    """Minimal failure summary for fast loading."""
    id: int
    selector_id: str
    error_type: str
    timestamp: Optional[str]
    severity: str
    sport: Optional[str]
    site: Optional[str]
    has_alternatives: bool


class FailureCountsSchema(BaseModel):
    """Failure counts by severity."""
    total: int
    critical: int = 0
    high: int = 0
    medium: int = 0
    minor: int = 0


class PerformanceMetricsSchema(BaseModel):
    """Performance metrics for triage operations."""
    load_time_ms: float
    target_met: bool
    action_time_ms: Optional[float] = None


class FastTriageListResponseSchema(BaseModel):
    """Response for optimized failure listing."""
    failures: List[TriageSummarySchema]
    next_cursor: Optional[int] = None
    counts: FailureCountsSchema
    performance: PerformanceMetricsSchema


class QuickApproveRequestSchema(BaseModel):
    """Request for one-click approval."""
    user_id: Optional[str] = None


class QuickApproveResponseSchema(BaseModel):
    """Response for one-click approval."""
    success: bool
    message: str
    failure_id: int
    selector: str
    confidence: float
    performance: PerformanceMetricsSchema


class BulkActionRequestSchema(BaseModel):
    """Request for bulk triage actions."""
    failure_ids: List[int] = Field(..., min_length=1, max_length=100)
    strategy: str = "highest_confidence"  # For approve: highest_confidence, most_stable
    reason: str = "Bulk action"  # For reject
    user_id: Optional[str] = None


class BulkActionResultSchema(BaseModel):
    """Result for a single failure in bulk action."""
    failure_id: int
    success: bool
    message: Optional[str] = None
    selector: Optional[str] = None


class BulkPerformanceSchema(BaseModel):
    """Performance metrics for bulk operations."""
    total_time_ms: float
    avg_time_per_failure: float
    target_met: bool


class BulkActionResponseSchema(BaseModel):
    """Response for bulk triage actions."""
    success: bool
    operation_id: str
    total: int
    success_count: int
    failure_count: int
    results: List[BulkActionResultSchema]
    performance: BulkPerformanceSchema


class EscalateRequestSchema(BaseModel):
    """Request for quick escalation."""
    failure_ids: List[int] = Field(..., min_length=1)
    reason: str = "Escalated for review"
    user_id: Optional[str] = None


class EscalateResponseSchema(BaseModel):
    """Response for quick escalation."""
    success: bool
    operation_id: str
    total: int
    success_count: int
    failure_count: int
    results: List[BulkActionResultSchema]
    performance: BulkPerformanceSchema


class PerformanceTargetSchema(BaseModel):
    """Performance target thresholds."""
    page_load_ms: int = 2000
    action_response_ms: int = 500
    triage_workflow_minutes: int = 5


class PerformanceStatusSchema(BaseModel):
    """Performance target status."""
    load_target_met: bool
    action_target_met: bool


class PerformanceSummaryResponseSchema(BaseModel):
    """Response for performance metrics summary."""
    period_hours: int
    total_actions: int
    averages: Dict[str, float]
    targets: PerformanceTargetSchema
    status: PerformanceStatusSchema
    by_action_type: Dict[str, Dict[str, Any]]
