"""
Data models for Selector Engine.

Defines core entities for semantic selectors, strategies, results, and related
components as specified in the data model documentation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator


class StrategyType(str, Enum):
    """Types of selector resolution strategies."""
    TEXT_ANCHOR = "text_anchor"
    ATTRIBUTE_MATCH = "attribute_match"
    DOM_RELATIONSHIP = "dom_relationship"
    ROLE_BASED = "role_based"


class ValidationType(str, Enum):
    """Types of content validation rules."""
    REGEX = "regex"
    DATA_TYPE = "data_type"
    SEMANTIC = "semantic"
    CUSTOM = "custom"


class SnapshotType(str, Enum):
    """Types of DOM snapshots."""
    FAILURE = "failure"
    DRIFT_ANALYSIS = "drift_analysis"
    MANUAL = "manual"


class TrendDirection(str, Enum):
    """Directions for performance trends."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"


class TabState(str, Enum):
    """States for tab contexts."""
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"
    UNLOADED = "unloaded"


class TabType(str, Enum):
    """Types of tabs."""
    CONTENT = "content"
    NAVIGATION = "navigation"
    SETTINGS = "settings"
    MODAL = "modal"


class TabVisibility(str, Enum):
    """Visibility states for tabs."""
    VISIBLE = "visible"
    HIDDEN = "hidden"
    PARTIALLY_VISIBLE = "partially_visible"


@dataclass
class ValidationRule:
    """Defines content validation criteria for selectors."""
    type: ValidationType
    pattern: str
    required: bool = True
    weight: float = 1.0
    
    def __post_init__(self):
        """Validate validation rule parameters."""
        if self.weight < 0.0 or self.weight > 1.0:
            raise ValueError("Weight must be between 0.0 and 1.0")
        if self.required and self.weight <= 0.0:
            raise ValueError("Required validation rules must have positive weight")


@dataclass
class StrategyPattern:
    """Defines a specific approach to element resolution."""
    id: str
    type: StrategyType
    priority: int
    config: Dict[str, Any]
    success_rate: float = 0.0
    avg_resolution_time: float = 0.0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate strategy pattern parameters."""
        if self.priority < 1:
            raise ValueError("Priority must be >= 1")
        if self.success_rate < 0.0 or self.success_rate > 1.0:
            raise ValueError("Success rate must be between 0.0 and 1.0")
        if self.avg_resolution_time < 0.0:
            raise ValueError("Average resolution time must be >= 0")
    
    def update_performance(self, success: bool, resolution_time: float):
        """Update performance metrics."""
        # Simple exponential moving average for success rate
        alpha = 0.1  # Learning rate
        new_success = 1.0 if success else 0.0
        self.success_rate = alpha * new_success + (1 - alpha) * self.success_rate
        
        # Update resolution time
        self.avg_resolution_time = (
            alpha * resolution_time + (1 - alpha) * self.avg_resolution_time
        )
        self.last_updated = datetime.utcnow()


@dataclass
class ElementInfo:
    """Detailed information about resolved DOM elements."""
    tag_name: str
    text_content: str
    attributes: Dict[str, str]
    css_classes: List[str]
    dom_path: str
    visibility: bool
    interactable: bool
    
    def get_text_clean(self) -> str:
        """Get cleaned text content."""
        return self.text_content.strip()
    
    def has_class(self, class_name: str) -> bool:
        """Check if element has specific CSS class."""
        return class_name in self.css_classes
    
    def get_attribute(self, attr_name: str, default: str = "") -> str:
        """Get attribute value with default."""
        return self.attributes.get(attr_name, default)


@dataclass
class ValidationResult:
    """Result of content validation."""
    rule_type: str
    passed: bool
    score: float
    message: str
    weight: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate validation result parameters."""
        if self.score < 0.0 or self.score > 1.0:
            raise ValueError("Score must be between 0.0 and 1.0")


@dataclass
class SelectorResult:
    """Result of selector resolution attempt."""
    selector_name: str
    strategy_used: str
    element_info: Optional[ElementInfo]
    confidence_score: float
    resolution_time: float
    validation_results: List[ValidationResult]
    success: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    failure_reason: Optional[str] = None
    
    def __post_init__(self):
        """Validate selector result parameters."""
        if self.confidence_score < 0.0 or self.confidence_score > 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        if self.resolution_time < 0.0:
            raise ValueError("Resolution time must be >= 0")
        if not self.success and not self.failure_reason:
            raise ValueError("Failed results must have failure reason")
        if self.success and self.failure_reason:
            raise ValueError("Successful results should not have failure reason")
    
    @classmethod
    def failure(cls, selector_name: str, failure_reason: str, 
                strategy_used: str = "none", resolution_time: float = 0.0) -> 'SelectorResult':
        """Create a failed selector result."""
        return cls(
            selector_name=selector_name,
            strategy_used=strategy_used,
            element_info=None,
            confidence_score=0.0,
            resolution_time=resolution_time,
            validation_results=[],
            success=False,
            failure_reason=failure_reason
        )
    
    def get_text_content(self) -> Optional[str]:
        """Get text content if successful."""
        return self.element_info.get_text_clean() if self.element_info else None
    
    def get_validation_score(self) -> float:
        """Calculate average validation score."""
        if not self.validation_results:
            return 0.0
        return sum(r.score for r in self.validation_results) / len(self.validation_results)


@dataclass
class SemanticSelector:
    """Represents business meaning mapped to DOM reality."""
    name: str
    description: str
    context: str
    strategies: List[StrategyPattern]
    validation_rules: List[ValidationRule]
    confidence_threshold: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate selector after initialization."""
        if not self.name.strip():
            raise ValueError("Selector name cannot be empty")
        # Note: Strategy count validation moved to engine.validate_selector for testing flexibility
        if self.confidence_threshold < 0.0 or self.confidence_threshold > 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        
        # Validate strategy priorities are unique
        priorities = [s.priority for s in self.strategies]
        if len(priorities) != len(set(priorities)):
            raise ValueError("Strategy priorities must be unique")
        
        # Sort strategies by priority
        self.strategies.sort(key=lambda s: s.priority)
    
    def get_strategies_by_priority(self) -> List[StrategyPattern]:
        """Get strategies sorted by priority (lowest first)."""
        return sorted(self.strategies, key=lambda s: s.priority)
    
    def get_active_strategies(self) -> List[StrategyPattern]:
        """Get only active strategies."""
        return [s for s in self.strategies if s.is_active]
    
    def meets_confidence_threshold(self, confidence: float) -> bool:
        """Check if confidence meets threshold."""
        return confidence >= self.confidence_threshold


@dataclass
class SnapshotMetadata:
    """Metadata for DOM snapshots."""
    page_url: str
    tab_context: str
    viewport_size: Tuple[int, int]
    user_agent: str
    resolution_attempt: int
    failure_reason: str
    performance_metrics: Dict[str, float]
    
    def __post_init__(self):
        """Validate snapshot metadata."""
        if self.resolution_attempt < 1:
            raise ValueError("Resolution attempt must be >= 1")


@dataclass
class DOMSnapshot:
    """Captured page state with metadata for failure analysis."""
    id: str
    selector_name: str
    snapshot_type: SnapshotType
    dom_content: str
    metadata: SnapshotMetadata
    file_path: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    file_size: int = 0
    
    def __post_init__(self):
        """Validate DOM snapshot."""
        if not self.dom_content.strip():
            raise ValueError("DOM content cannot be empty")
        self.file_size = len(self.dom_content.encode('utf-8'))


@dataclass
class ConfidenceMetrics:
    """Tracks success rates, performance, and reliability statistics."""
    selector_name: str
    strategy_id: str
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    avg_confidence: float = 0.0
    avg_resolution_time: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    current_streak: int = 0
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate consistency of metrics."""
        if self.total_attempts != self.successful_attempts + self.failed_attempts:
            raise ValueError("Total attempts must equal successful + failed attempts")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.successful_attempts / self.total_attempts
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.failed_attempts / self.total_attempts
    
    @property
    def reliability_score(self) -> float:
        """Calculate weighted reliability score."""
        # Combine success rate (70%) and confidence (30%)
        return (self.success_rate * 0.7) + (self.avg_confidence * 0.3)
    
    def record_attempt(self, success: bool, confidence: float, resolution_time: float):
        """Record a resolution attempt."""
        self.total_attempts += 1
        
        if success:
            self.successful_attempts += 1
            self.last_success = datetime.utcnow()
            self.current_streak = max(0, self.current_streak + 1)
        else:
            self.failed_attempts += 1
            self.last_failure = datetime.utcnow()
            self.current_streak = min(0, self.current_streak - 1)
        
        # Update averages using exponential moving average
        alpha = 0.1
        self.avg_confidence = alpha * confidence + (1 - alpha) * self.avg_confidence
        self.avg_resolution_time = (
            alpha * resolution_time + (1 - alpha) * self.avg_resolution_time
        )
        self.updated_at = datetime.utcnow()


@dataclass
class PerformanceTrend:
    """Performance trend information."""
    strategy_id: str
    success_rate_trend: float
    confidence_trend: float
    performance_trend: float
    volatility: float
    
    def __post_init__(self):
        """Validate trend values."""
        for trend_name, trend_value in [
            ("success_rate_trend", self.success_rate_trend),
            ("confidence_trend", self.confidence_trend),
            ("performance_trend", self.performance_trend),
        ]:
            if trend_value < -1.0 or trend_value > 1.0:
                raise ValueError(f"{trend_name} must be between -1.0 and 1.0")
        if self.volatility < 0.0:
            raise ValueError("Volatility must be >= 0")


@dataclass
class DriftAnalysis:
    """Contains patterns and trends in selector performance over time."""
    selector_name: str
    analysis_period: Tuple[datetime, datetime]
    drift_score: float
    trend_direction: TrendDirection
    strategy_performance: Dict[str, PerformanceTrend]
    recommendations: List[str]
    manual_review_required: bool
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate drift analysis."""
        if self.drift_score < 0.0 or self.drift_score > 1.0:
            raise ValueError("Drift score must be between 0.0 and 1.0")
        if self.analysis_period[0] >= self.analysis_period[1]:
            raise ValueError("Analysis period start must be before end")
    
    def requires_immediate_attention(self) -> bool:
        """Check if drift requires immediate attention."""
        return self.drift_score > 0.8 or self.manual_review_required


@dataclass
class TabContext:
    """Defines tab-specific context for selector scoping."""
    tab_id: str
    tab_type: TabType
    state: TabState
    visibility: TabVisibility
    is_active: bool
    dom_scope: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_active_tab(self) -> bool:
        """Check if this tab is currently active."""
        return self.is_active
    
    def is_visible(self) -> bool:
        """Check if this tab is visible."""
        return self.visibility == TabVisibility.VISIBLE
    
    def is_loaded(self) -> bool:
        """Check if this tab is loaded."""
        return self.state == TabState.LOADED


@dataclass
class StrategyRecommendation:
    """Recommendation for strategy improvement."""
    strategy_id: str
    recommendation_type: str  # "add", "remove", "modify", "reorder"
    priority: int
    reason: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_high_priority(self) -> bool:
        """Check if recommendation is high priority."""
        return self.priority <= 2
    
    def is_high_confidence(self) -> bool:
        """Check if recommendation has high confidence."""
        return self.confidence >= 0.8


# Pydantic models for API serialization
class SemanticSelectorModel(BaseModel):
    """Pydantic model for SemanticSelector serialization."""
    name: str
    description: str
    context: str
    strategies: List[Dict[str, Any]]
    validation_rules: List[Dict[str, Any]]
    confidence_threshold: float = 0.8
    metadata: Dict[str, Any] = {}
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SelectorResultModel(BaseModel):
    """Pydantic model for SelectorResult serialization."""
    selector_name: str
    strategy_used: str
    element_info: Optional[Dict[str, Any]]
    confidence_score: float
    resolution_time: float
    validation_results: List[Dict[str, Any]]
    success: bool
    timestamp: datetime
    failure_reason: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConfidenceMetricsModel(BaseModel):
    """Pydantic model for ConfidenceMetrics serialization."""
    selector_name: str
    strategy_id: str
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    avg_confidence: float = 0.0
    avg_resolution_time: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    current_streak: int = 0
    updated_at: datetime
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.successful_attempts / self.total_attempts
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
