"""
Pydantic schemas for Custom Strategy API endpoints.

These schemas define the request/response models for custom selector strategy
management as specified in Story 7.2: Technical and Non-Technical Views.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CustomStrategyCreateSchema(BaseModel):
    """Schema for creating a new custom strategy."""
    name: str = Field(min_length=1, max_length=100, description="Strategy name")
    description: str = Field(min_length=1, max_length=500, description="Strategy description")
    selector: str = Field(min_length=1, max_length=1000, description="Selector string")
    strategy_type: str = Field(description="Strategy type: css, xpath, text_anchor, custom")
    confidence_weight: float = Field(
        default=0.5, 
        ge=0.0, 
        le=1.0, 
        description="Weight for confidence scoring (0.0-1.0)"
    )
    blast_radius_protection: bool = Field(
        default=True, 
        description="Enable blast radius protection"
    )
    validation_rules: Optional[Dict[str, Any]] = Field(
        None, 
        description="Custom validation rules as key-value pairs"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Team Name Enhanced",
                "description": "Enhanced team name selector with fallback support",
                "selector": ".team-info .name, .team-name",
                "strategy_type": "css",
                "confidence_weight": 0.8,
                "blast_radius_protection": True,
                "validation_rules": {"require_text": True, "min_length": 2}
            }
        }


class CustomStrategyUpdateSchema(BaseModel):
    """Schema for updating a custom strategy."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Strategy name")
    description: Optional[str] = Field(None, min_length=1, max_length=500, description="Strategy description")
    selector: Optional[str] = Field(None, min_length=1, max_length=1000, description="Selector string")
    strategy_type: Optional[str] = Field(None, description="Strategy type: css, xpath, text_anchor, custom")
    confidence_weight: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Weight for confidence scoring (0.0-1.0)"
    )
    blast_radius_protection: Optional[bool] = Field(None, description="Enable blast radius protection")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Custom validation rules")
    is_active: Optional[bool] = Field(None, description="Whether the strategy is active")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Team Name Selector",
                "confidence_weight": 0.9,
                "is_active": True
            }
        }


class CustomStrategyResponseSchema(BaseModel):
    """Schema for custom strategy response."""
    id: str = Field(description="Unique strategy ID")
    name: str = Field(description="Strategy name")
    description: str = Field(description="Strategy description")
    selector: str = Field(description="Selector string")
    strategy_type: str = Field(description="Strategy type")
    confidence_weight: float = Field(description="Weight for confidence scoring")
    blast_radius_protection: bool = Field(description="Blast radius protection enabled")
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="Validation rules")
    created_by: str = Field(description="User who created the strategy")
    created_at: datetime = Field(description="When the strategy was created")
    is_active: bool = Field(description="Whether the strategy is active")

    class Config:
        from_attributes = True


class CustomStrategyListSchema(BaseModel):
    """Schema for custom strategy list response."""
    strategies: List[CustomStrategyResponseSchema] = Field(description="List of strategies")
    total: int = Field(description="Total number of strategies")


class ValidationResultSchema(BaseModel):
    """Schema for selector validation results."""
    is_valid: bool = Field(description="Whether the selector is valid")
    confidence_score: float = Field(description="Predicted confidence score (0.0-1.0)")
    error_message: Optional[str] = Field(None, description="Error message if invalid")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    test_results: Dict[str, Any] = Field(default_factory=dict, description="Detailed test results")

    class Config:
        from_attributes = True


class TestResultSchema(BaseModel):
    """Schema for strategy test results."""
    strategy_id: str = Field(description="ID of the tested strategy")
    test_passed: bool = Field(description="Whether the test passed")
    matches_found: int = Field(description="Number of matches found")
    execution_time_ms: int = Field(description="Test execution time in milliseconds")
    confidence_score: float = Field(description="Confidence score from test")
    test_timestamp: datetime = Field(description="When the test was performed")
    sample_content_used: bool = Field(description="Whether sample content was used for testing")

    class Config:
        from_attributes = True


class StrategyCreateResponseSchema(BaseModel):
    """Schema for strategy creation response with validation."""
    strategy: CustomStrategyResponseSchema = Field(description="Created strategy")
    validation: ValidationResultSchema = Field(description="Validation results")


# Request schemas for specific operations
class SelectorValidationRequest(BaseModel):
    """Schema for selector validation request."""
    selector: str = Field(min_length=1, max_length=1000, description="Selector to validate")
    strategy_type: str = Field(description="Strategy type: css, xpath, text_anchor, custom")

    class Config:
        json_schema_extra = {
            "example": {
                "selector": ".team-name",
                "strategy_type": "css"
            }
        }


class StrategyTestRequest(BaseModel):
    """Schema for strategy testing request."""
    test_content: Optional[str] = Field(None, max_length=5000, description="Sample content to test against")

    class Config:
        json_schema_extra = {
            "example": {
                "test_content": "<div class='team'><span class='team-name'>Team A</span></div>"
            }
        }


# Response schemas for additional endpoints
class StrategyTypeSchema(BaseModel):
    """Schema for strategy type information."""
    id: str = Field(description="Strategy type ID")
    name: str = Field(description="Human-readable name")
    description: str = Field(description="Description of the strategy type")
    examples: List[str] = Field(description="Example selectors")
    confidence_range: List[float] = Field(description="Typical confidence range")


class StrategyTypesResponseSchema(BaseModel):
    """Schema for strategy types response."""
    strategy_types: List[StrategyTypeSchema] = Field(description="Available strategy types")


# Error response schemas
class ValidationErrorSchema(BaseModel):
    """Schema for validation errors."""
    field: str = Field(description="Field that failed validation")
    message: str = Field(description="Error message")
    code: str = Field(description="Error code")


class ProblemDetailSchema(BaseModel):
    """Schema for RFC 7807 problem details."""
    type: str = Field(description="Error type URI")
    title: str = Field(description="Error title")
    detail: str = Field(description="Error detail")
    status: int = Field(description="HTTP status code")
    instance: Optional[str] = Field(None, description="Error instance")
    errors: Optional[List[ValidationErrorSchema]] = Field(None, description="Field validation errors")
