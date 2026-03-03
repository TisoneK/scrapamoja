"""
Failure Event SQLAlchemy model for storing selector failure events in the database.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Integer, String, Float, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from .recipe import Base


class FailureEvent(Base):
    """FailureEvent model for tracking selector resolution failures."""
    __tablename__ = "failure_events"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Required fields
    selector_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    error_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        index=True,
        default="exception"
    )
    
    # Optional context fields
    recipe_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True, 
        index=True
    )
    sport: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True, 
        index=True
    )
    site: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True, 
        index=True
    )
    
    # Error details
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(1000), 
        nullable=True
    )
    strategy_used: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True
    )
    
    # NEW: Context fields for Story 2.3
    previous_strategy_used: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        doc="Strategy used before the current failure (for tracking what was attempted)"
    )
    confidence_score_at_failure: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence score at the time of failure"
    )
    tab_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Type of tab being extracted (e.g., 'odds', 'results', 'schedule')"
    )
    page_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Page state at time of failure (scroll position, loaded content, etc.)"
    )
    resolution_time: Mapped[Optional[float]] = mapped_column(
        Float, 
        nullable=True
    )
    
    # Severity
    severity: Mapped[Optional[str]] = mapped_column(
        String(20), 
        nullable=True, 
        default="minor",
        index=True
    )
    
    # Additional context as JSON
    context_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        nullable=True
    )
    
    # Correlation ID for tracing
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True, 
        index=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    
    # Table indexes for common queries
    __table_args__ = (
        Index('ix_failure_events_selector_timestamp', 'selector_id', 'timestamp'),
        Index('ix_failure_events_sport_site', 'sport', 'site'),
        Index('ix_failure_events_recipe_timestamp', 'recipe_id', 'timestamp'),
        Index('ix_failure_events_error_type_timestamp', 'error_type', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<FailureEvent(selector_id={self.selector_id!r}, error_type={self.error_type!r}, timestamp={self.timestamp})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert failure event to dictionary representation."""
        return {
            "id": self.id,
            "selector_id": self.selector_id,
            "recipe_id": self.recipe_id,
            "sport": self.sport,
            "site": self.site,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "error_type": self.error_type,
            "failure_reason": self.failure_reason,
            "strategy_used": self.strategy_used,
            "previous_strategy_used": self.previous_strategy_used,
            "confidence_score_at_failure": self.confidence_score_at_failure,
            "tab_type": self.tab_type,
            "page_state": self.page_state,
            "resolution_time": self.resolution_time,
            "severity": self.severity,
            "context_snapshot": self.context_snapshot,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FailureEvent":
        """Create FailureEvent instance from dictionary."""
        # Handle timestamp conversion
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        return cls(
            selector_id=data["selector_id"],
            timestamp=timestamp or datetime.utcnow(),
            error_type=data.get("error_type", "exception"),
            recipe_id=data.get("recipe_id"),
            sport=data.get("sport"),
            site=data.get("site"),
            failure_reason=data.get("failure_reason"),
            strategy_used=data.get("strategy_used"),
            previous_strategy_used=data.get("previous_strategy_used"),
            confidence_score_at_failure=data.get("confidence_score_at_failure"),
            tab_type=data.get("tab_type"),
            page_state=data.get("page_state"),
            resolution_time=data.get("resolution_time"),
            severity=data.get("severity", "minor"),
            context_snapshot=data.get("context_snapshot"),
            correlation_id=data.get("correlation_id"),
            created_at=created_at or datetime.utcnow(),
        )


class ErrorType:
    """Enumeration for error type classification."""
    EMPTY_RESULT = "empty_result"
    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is a valid error type."""
        return value in (
            cls.EMPTY_RESULT, 
            cls.EXCEPTION, 
            cls.TIMEOUT, 
            cls.VALIDATION
        )
    
    @classmethod
    def get_default_severity(cls, error_type: str) -> str:
        """Get default severity for error type."""
        severity_mapping = {
            cls.EMPTY_RESULT: "minor",
            cls.EXCEPTION: "moderate",
            cls.TIMEOUT: "moderate",
            cls.VALIDATION: "minor",
        }
        return severity_mapping.get(error_type, "minor")
