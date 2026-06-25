"""
Audit Event model for tracking selector approvals and rejections.

This implements Epic 6 (Audit Logging) requirements for Story 4.2.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .recipe import Base


class AuditEvent(Base):
    """
    Audit event for tracking selector decisions and system changes.
    
    This table stores all human decisions (approve/reject/flag) for:
    - Compliance and accountability
    - Learning system training data
    - System behavior analysis
    """
    
    __tablename__ = "audit_log"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Event metadata
    action_type = Column(String(50), nullable=False, index=True)  # selector_approved, selector_rejected, selector_flagged
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Selector context
    failure_id = Column(Integer, nullable=True, index=True)  # Links to failure event (optional)
    selector_id = Column(String(100), nullable=True, index=True)  # Unique selector identifier
    selector = Column(Text, nullable=False)  # The selector string
    context_snapshot = Column(JSON, nullable=True)  # Full context snapshot at decision time
    
    # User context
    user_id = Column(String(100), nullable=False, default="system", index=True)
    
    # State change tracking
    before_state = Column(Text, nullable=True)  # Original selector value
    after_state = Column(Text, nullable=True)   # New selector value (for approvals)
    
    # Decision context
    confidence_at_time = Column(Float, nullable=True)  # Confidence score when decision made
    reason = Column(Text, nullable=True)  # Reason for rejection
    suggested_alternative = Column(Text, nullable=True)  # User's suggested alternative
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "action_type": self.action_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "failure_id": self.failure_id,
            "selector_id": self.selector_id,
            "selector": self.selector,
            "context_snapshot": self.context_snapshot,
            "user_id": self.user_id,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "confidence_at_time": self.confidence_at_time,
            "reason": self.reason,
            "suggested_alternative": self.suggested_alternative,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<AuditEvent(id={self.id}, action_type={self.action_type}, failure_id={self.failure_id}, user_id={self.user_id})>"
