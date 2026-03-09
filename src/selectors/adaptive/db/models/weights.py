"""
Weights SQLAlchemy model for storing learned approval weights in the database.

This model stores the approval learning data from Epic 5 (Learning & Weight Adjustment)
so that learned weights persist across service restarts.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Integer, String, Float, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from .recipe import Base


class ApprovalWeight(Base):
    """ApprovalWeight model for storing learned approval weights.
    
    Stores approval counts and boost amounts per strategy type to enable
    the confidence scoring system to learn from human approvals.
    """
    __tablename__ = "approval_weights"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Strategy identification
    strategy_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="The selector strategy type (css, xpath, text_anchor, etc.)"
    )
    
    # Approval tracking
    approval_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of times this strategy has been approved"
    )
    
    # Boost data
    total_boost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Total confidence boost from approvals (capped at MAX_APPROVAL_BOOST)"
    )
    
    related_boost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Boost from related strategies"
    )
    
    # Timestamps
    first_approval: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Timestamp of first approval"
    )
    last_approval: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Timestamp of most recent approval"
    )
    
    # Metadata
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional metadata (related strategies, notes, etc.)"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        doc="Last update timestamp"
    )
    
    # Unique constraint on strategy_type
    __table_args__ = (
        Index('ix_approval_weights_strategy_unique', 'strategy_type', unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<ApprovalWeight(strategy={self.strategy_type}, count={self.approval_count}, boost={self.total_boost})>"


class SelectorApprovalHistory(Base):
    """SelectorApprovalHistory model for tracking individual selector approvals.
    
    Stores the history of each specific selector that has been approved,
    enabling detailed learning from human feedback.
    """
    __tablename__ = "selector_approval_history"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Selector identification
    selector_string: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        index=True,
        doc="The approved selector string"
    )
    strategy_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="The strategy type used"
    )
    
    # Approval data
    confidence_at_approval: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence score at time of approval"
    )
    boosted_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence score after applying approval boost"
    )
    
    # Context
    failure_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Associated failure event ID (if any)"
    )
    sport: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Sport context"
    )
    site: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Site context"
    )
    
    # User/audit info
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="User who approved (or system)"
    )
    approval_notes: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        doc="Notes from approver"
    )
    
    # Timestamp
    approved_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        doc="Timestamp of approval"
    )
    
    def __repr__(self) -> str:
        return f"<SelectorApprovalHistory(selector={self.selector_string[:30]}..., strategy={self.strategy_type})>"


class RejectionWeight(Base):
    """RejectionWeight model for storing learned rejection weights.
    
    Stores rejection counts and penalty amounts per strategy type to enable
    the confidence scoring system to learn from human rejections.
    """
    __tablename__ = "rejection_weights"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Strategy identification
    strategy_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="The selector strategy type (css, xpath, text_anchor, etc.)"
    )
    
    # Rejection tracking
    rejection_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of times this strategy has been rejected"
    )
    
    # Penalty data
    total_penalty: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Total confidence penalty from rejections (capped at MAX_REJECTION_PENALTY)"
    )
    
    related_penalty: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Penalty from related strategies"
    )
    
    # Timestamps
    first_rejection: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Timestamp of first rejection"
    )
    last_rejection: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Timestamp of most recent rejection"
    )
    
    # Metadata
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional metadata (rejection reasons, pattern analysis, etc.)"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        doc="Last update timestamp"
    )
    
    # Unique constraint on strategy_type
    __table_args__ = (
        Index('ix_rejection_weights_strategy_unique', 'strategy_type', unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<RejectionWeight(strategy={self.strategy_type}, count={self.rejection_count}, penalty={self.total_penalty})>"


class SelectorRejectionHistory(Base):
    """SelectorRejectionHistory model for tracking individual selector rejections.
    
    Stores the history of each specific selector that has been rejected,
    enabling detailed learning from human feedback and pattern analysis.
    """
    __tablename__ = "selector_rejection_history"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Selector identification
    selector_string: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        index=True,
        doc="The rejected selector string"
    )
    strategy_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="The strategy type used"
    )
    
    # Rejection data
    confidence_at_rejection: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence score at time of rejection"
    )
    penalized_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence score after applying rejection penalty"
    )
    
    # Rejection reason (for pattern analysis)
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Reason for rejection provided by human"
    )
    reason_pattern: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Parsed reason pattern (too_specific, too_generic, wrong_element, fragile, etc.)"
    )
    
    # Context
    failure_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Associated failure event ID (if any)"
    )
    sport: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Sport context"
    )
    site: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Site context"
    )
    
    # User/audit info
    rejected_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="User who rejected (or system)"
    )
    rejection_notes: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        doc="Notes from rejecter"
    )
    
    # Timestamp
    rejected_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        doc="Timestamp of rejection"
    )
    
    def __repr__(self) -> str:
        return f"<SelectorRejectionHistory(selector={self.selector_string[:30]}..., strategy={self.strategy_type})>"


class GenerationData(Base):
    """GenerationData model for tracking selector survival across generations.
    
    Stores generation tracking data per recipe to enable the system to track
    how selectors survive site layout changes (generations).
    
    Story 5.3: Track Selector Survival Across Generations
    """
    __tablename__ = "generation_data"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Recipe identification
    recipe_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="The recipe identifier"
    )
    
    # Generation tracking
    current_generation: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Current generation number for this recipe"
    )
    
    generations_survived: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of generations this recipe has survived"
    )
    
    generation_failures: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total number of generation failures"
    )
    
    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Consecutive failure count (for triggering review)"
    )
    
    # Context
    sport: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Sport context"
    )
    site: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Site context"
    )
    
    # Timestamps
    first_generation: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Timestamp of first generation tracking"
    )
    last_generation_change: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="Timestamp of most recent generation change"
    )
    
    # Metadata
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional metadata"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        doc="Last update timestamp"
    )
    
    # Unique constraint on recipe_id
    __table_args__ = (
        Index('ix_generation_data_recipe_unique', 'recipe_id', unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<GenerationData(recipe={self.recipe_id}, gen={self.current_generation}, survived={self.generations_survived})>"
