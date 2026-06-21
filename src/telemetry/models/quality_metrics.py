"""
Quality Metrics Model

Confidence scoring and quality indicators for selector operations
following the data model specification.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class QualityMetrics(BaseModel):
    """
    Confidence scores and quality indicators for selector operations.
    
    Contains comprehensive quality data including confidence scores,
    success indicators, drift detection, and validation results.
    """
    
    confidence_score: float = Field(..., description="Overall confidence score (0.0-1.0)")
    success: bool = Field(..., description="Whether the operation succeeded")
    elements_found: Optional[int] = Field(None, description="Number of DOM elements found")
    strategy_success_rate: Optional[float] = Field(None, description="Success rate of strategies used")
    drift_detected: Optional[bool] = Field(None, description="Whether selector drift was detected")
    fallback_used: Optional[bool] = Field(None, description="Whether fallback mechanisms were used")
    validation_passed: Optional[bool] = Field(None, description="Whether validation checks passed")
    
    @validator('confidence_score')
    def validate_confidence_score(cls, v):
        """Validate confidence score is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return v
    
    @validator('elements_found')
    def validate_elements_found(cls, v):
        """Validate elements found is non-negative."""
        if v is not None:
            if v < 0:
                raise ValueError("elements_found must be non-negative")
        return v
    
    @validator('strategy_success_rate')
    def validate_strategy_success_rate(cls, v):
        """Validate strategy success rate is within valid range."""
        if v is not None:
            if not 0.0 <= v <= 1.0:
                raise ValueError("strategy_success_rate must be between 0.0 and 1.0")
        return v
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """
        Check if confidence score is high.
        
        Args:
            threshold: Confidence threshold
            
        Returns:
            True if confidence score exceeds threshold
        """
        return self.confidence_score >= threshold
    
    def is_low_confidence(self, threshold: float = 0.5) -> bool:
        """
        Check if confidence score is low.
        
        Args:
            threshold: Confidence threshold
            
        Returns:
            True if confidence score is below threshold
        """
        return self.confidence_score < threshold
    
    def has_multiple_elements(self) -> bool:
        """
        Check if multiple elements were found.
        
        Returns:
            True if more than one element was found
        """
        return self.elements_found is not None and self.elements_found > 1
    
    def has_no_elements(self) -> bool:
        """
        Check if no elements were found.
        
        Returns:
            True if no elements were found
        """
        return self.elements_found is not None and self.elements_found == 0
    
    def has_drift(self) -> bool:
        """
        Check if drift was detected.
        
        Returns:
            True if drift was detected
        """
        return self.drift_detected is True
    
    def used_fallback(self) -> bool:
        """
        Check if fallback mechanisms were used.
        
        Returns:
            True if fallback was used
        """
        return self.fallback_used is True
    
    def validation_failed(self) -> bool:
        """
        Check if validation failed.
        
        Returns:
            True if validation failed
        """
        return self.validation_passed is False
    
    def get_quality_level(self) -> str:
        """
        Get quality level based on confidence score.
        
        Returns:
            Quality level string (excellent, good, fair, poor)
        """
        if self.confidence_score >= 0.9:
            return "excellent"
        elif self.confidence_score >= 0.8:
            return "good"
        elif self.confidence_score >= 0.6:
            return "fair"
        else:
            return "poor"
    
    def get_health_status(self) -> str:
        """
        Get overall health status.
        
        Returns:
            Health status string (healthy, warning, critical)
        """
        issues = []
        
        if not self.success:
            issues.append("failed")
        if self.is_low_confidence():
            issues.append("low_confidence")
        if self.has_drift():
            issues.append("drift")
        if self.validation_failed():
            issues.append("validation_failed")
        
        if not issues:
            return "healthy"
        elif len(issues) <= 2:
            return "warning"
        else:
            return "critical"
    
    def needs_attention(self) -> bool:
        """
        Check if the operation needs attention based on quality metrics.
        
        Returns:
            True if operation needs attention
        """
        return (
            not self.success or
            self.is_low_confidence() or
            self.has_drift() or
            self.validation_failed()
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary with all fields."""
        return {
            "confidence_score": self.confidence_score,
            "success": self.success,
            "elements_found": self.elements_found,
            "strategy_success_rate": self.strategy_success_rate,
            "drift_detected": self.drift_detected,
            "fallback_used": self.fallback_used,
            "validation_passed": self.validation_passed
        }
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
