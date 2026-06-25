"""
Blast Radius API schemas for request and response models.

This module provides Pydantic models for:
- Blast radius query requests and responses
- Cascading effects detection
- Severity assessment
- Batch blast radius queries

Story: 6.3 - Blast Radius Calculation
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

from pydantic import BaseModel, Field


class BlastRadiusSeverity(str, Enum):
    """Severity levels for blast radius assessment."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class FieldType(str, Enum):
    """Type of data field affected by selector failure."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    AUXILIARY = "auxiliary"


class DependencyType(str, Enum):
    """Type of dependency between selectors."""
    SHARES_DATA = "shares_data"
    DEPENDS_ON = "depends_on"
    RELATED = "related"


class AffectedField(BaseModel):
    """Model for an affected data field."""
    field_name: str = Field(..., description="Name of the affected field")
    field_type: FieldType = Field(..., description="Type of field (primary/secondary/auxiliary)")
    confidence_impact: float = Field(..., description="Impact on confidence score (0.0 to 1.0)")


class CascadingSelector(BaseModel):
    """Model for a potentially cascading selector."""
    selector_id: str = Field(..., description="ID of the dependent selector")
    dependency_type: DependencyType = Field(..., description="Type of dependency")
    potential_impact: str = Field(..., description="Description of potential impact")


class RecommendedAction(BaseModel):
    """Model for a recommended remediation action."""
    priority: str = Field(..., description="Priority level (high/medium/low)")
    action: str = Field(..., description="Description of the recommended action")
    selector_id: Optional[str] = Field(None, description="Related selector ID if applicable")


class BlastRadiusResponse(BaseModel):
    """Response model for blast radius query."""
    failed_selector: str = Field(..., description="The selector ID that failed")
    affected_fields: List[AffectedField] = Field(
        default_factory=list, 
        description="List of data fields impacted"
    )
    affected_records: int = Field(..., description="Count of records affected by this failure")
    severity: BlastRadiusSeverity = Field(..., description="Severity level of the blast radius")
    recommended_actions: List[str] = Field(
        default_factory=list, 
        description="Suggested remediation steps"
    )
    cascading_selectors: List[CascadingSelector] = Field(
        default_factory=list, 
        description="List of related selectors potentially impacted"
    )
    timestamp: datetime = Field(..., description="When the calculation was performed")
    confidence_score: float = Field(..., description="Current confidence score of the selector")
    message: Optional[str] = Field(None, description="Additional message about the blast radius")


class BatchBlastRadiusResponse(BaseModel):
    """Response model for batch blast radius query."""
    blast_radius: Dict[str, BlastRadiusResponse] = Field(
        ..., 
        description="Dictionary of blast radius results keyed by selector_id"
    )
    total_calculated: int = Field(..., description="Total number of blast radius calculations performed")
    timestamp: datetime = Field(..., description="When the batch calculation was performed")


class BlastRadiusQueryRequest(BaseModel):
    """Request model for blast radius query."""
    selector_ids: List[str] = Field(
        ..., 
        min_items=1,
        max_items=100,
        description="List of selector IDs to query blast radius for"
    )
    include_cascading: bool = Field(
        default=True, 
        description="Whether to include cascading selectors in the response"
    )
    include_recommended_actions: bool = Field(
        default=True, 
        description="Whether to include recommended actions in the response"
    )


class BlastRadiusConfigResponse(BaseModel):
    """Response model for blast radius configuration."""
    critical_confidence_threshold: float = Field(
        ..., 
        description="Score below this threshold is critical (< 0.5)"
    )
    major_confidence_threshold: float = Field(
        ..., 
        description="Score range for major severity (0.5-0.79)"
    )
    critical_fields: List[str] = Field(
        ..., 
        description="List of fields considered critical/primary"
    )


class BlastRadiusSummary(BaseModel):
    """Summary model for blast radius overview."""
    total_affected_records: int = Field(..., description="Total records affected across all selectors")
    critical_count: int = Field(..., description="Number of critical severity selectors")
    major_count: int = Field(..., description="Number of major severity selectors")
    minor_count: int = Field(..., description="Number of minor severity selectors")
    selectors_analyzed: int = Field(..., description="Total number of selectors analyzed")
