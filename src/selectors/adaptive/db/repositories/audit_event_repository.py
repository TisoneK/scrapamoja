"""
Repository for Audit Event operations.

This implements the data access layer for audit logging.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import desc, and_

from ..models.audit_event import AuditEvent
from ..models.recipe import Base


class AuditEventRepository:
    """Repository for audit event data access."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the audit event repository.
        
        Args:
            db_path: Optional path to SQLite database file.
                    If not provided, uses ':memory:' for testing.
        """
        if db_path is None:
            db_path = ":memory:"
        
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def create_audit_event(
        self,
        action_type: str,
        failure_id: int,
        selector: str,
        user_id: Optional[str] = None,
        before_state: Optional[str] = None,
        after_state: Optional[str] = None,
        confidence_at_time: Optional[float] = None,
        reason: Optional[str] = None,
        suggested_alternative: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AuditEvent:
        """
        Create a new audit event.
        
        Args:
            action_type: Type of action (selector_approved, selector_rejected, selector_flagged)
            failure_id: The failure event ID
            selector: The selector involved
            user_id: User who performed the action
            before_state: State before change
            after_state: State after change
            confidence_at_time: Confidence score at time of action
            reason: Reason for rejection
            suggested_alternative: Suggested alternative selector
            notes: Additional notes
            
        Returns:
            Created audit event
        """
        session = self.get_session()
        try:
            audit_event = AuditEvent(
                action_type=action_type,
                failure_id=failure_id,
                selector=selector,
                user_id=user_id or "system",
                before_state=before_state,
                after_state=after_state,
                confidence_at_time=confidence_at_time,
                reason=reason,
                suggested_alternative=suggested_alternative,
                notes=notes,
                timestamp=datetime.now(timezone.utc),
            )
            
            session.add(audit_event)
            session.commit()
            session.refresh(audit_event)
            
            return audit_event
        finally:
            session.close()
    
    def get_by_failure_id(self, failure_id: int) -> List[AuditEvent]:
        """
        Get all audit events for a specific failure.
        
        Args:
            failure_id: The failure event ID
            
        Returns:
            List of audit events for the failure
        """
        session = self.get_session()
        try:
            return (
                session.query(AuditEvent)
                .filter(AuditEvent.failure_id == failure_id)
                .order_by(desc(AuditEvent.timestamp))
                .all()
            )
        finally:
            session.close()
    
    def get_by_user_id(self, user_id: str, limit: int = 100) -> List[AuditEvent]:
        """
        Get audit events for a specific user.
        
        Args:
            user_id: The user ID
            limit: Maximum number of events to return
            
        Returns:
            List of audit events for the user
        """
        session = self.get_session()
        try:
            return (
                session.query(AuditEvent)
                .filter(AuditEvent.user_id == user_id)
                .order_by(desc(AuditEvent.timestamp))
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    def get_by_action_type(self, action_type: str, limit: int = 100) -> List[AuditEvent]:
        """
        Get audit events by action type.
        
        Args:
            action_type: The action type (selector_approved, selector_rejected, etc.)
            limit: Maximum number of events to return
            
        Returns:
            List of audit events matching the action type
        """
        session = self.get_session()
        try:
            return (
                session.query(AuditEvent)
                .filter(AuditEvent.action_type == action_type)
                .order_by(desc(AuditEvent.timestamp))
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    def get_audit_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get audit statistics for reporting.
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Dictionary with audit statistics
        """
        session = self.get_session()
        try:
            query = session.query(AuditEvent)
            
            if start_date:
                query = query.filter(AuditEvent.timestamp >= start_date)
            if end_date:
                query = query.filter(AuditEvent.timestamp <= end_date)
            
            total_events = query.count()
            
            # Count by action type
            action_counts = {}
            for action_type in ["selector_approved", "selector_rejected", "selector_flagged"]:
                count = query.filter(AuditEvent.action_type == action_type).count()
                action_counts[action_type] = count
            
            # Average confidence for approvals
            avg_confidence = (
                query.filter(AuditEvent.action_type == "selector_approved")
                .filter(AuditEvent.confidence_at_time.isnot(None))
                .with_entities(AuditEvent.confidence_at_time)
                .all()
            )
            
            if avg_confidence:
                avg_confidence_value = sum(conf[0] for conf in avg_confidence) / len(avg_confidence)
            else:
                avg_confidence_value = None
            
            return {
                "total_events": total_events,
                "action_counts": action_counts,
                "average_approval_confidence": avg_confidence_value,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            }
        finally:
            session.close()
