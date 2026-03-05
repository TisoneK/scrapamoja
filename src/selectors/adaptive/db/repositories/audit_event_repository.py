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
        selector: str,
        user_id: Optional[str] = None,
        selector_id: Optional[str] = None,
        failure_id: Optional[int] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
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
            action_type: Type of action (selector_approved, selector_rejected, selector_flagged, custom_selector_created)
            selector: The selector string
            user_id: User who performed action
            selector_id: Unique selector identifier (optional)
            failure_id: The failure event ID (optional)
            context_snapshot: Full context snapshot at decision time
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
                selector=selector,
                user_id=user_id or "system",
                selector_id=selector_id,
                failure_id=failure_id,
                context_snapshot=context_snapshot,
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
    
    def get_all_events(self, limit: int = 1000) -> List[AuditEvent]:
        """
        Get all audit events in chronological order.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of all audit events ordered by timestamp
        """
        session = self.get_session()
        try:
            return (
                session.query(AuditEvent)
                .order_by(AuditEvent.timestamp.asc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    def get_events_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        limit: int = 1000
    ) -> List[AuditEvent]:
        """
        Get audit events within a date range.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            limit: Maximum number of events to return
            
        Returns:
            List of audit events within date range ordered by timestamp
        """
        session = self.get_session()
        try:
            return (
                session.query(AuditEvent)
                .filter(and_(
                    AuditEvent.timestamp >= start_date,
                    AuditEvent.timestamp <= end_date
                ))
                .order_by(AuditEvent.timestamp.asc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    def get_events_by_selector_id(self, selector_id: str, limit: int = 100) -> List[AuditEvent]:
        """
        Get all audit events for a specific selector.
        
        Args:
            selector_id: The selector ID
            limit: Maximum number of events to return
            
        Returns:
            List of audit events for selector ordered by timestamp
        """
        session = self.get_session()
        try:
            return (
                session.query(AuditEvent)
                .filter(AuditEvent.selector_id == selector_id)
                .order_by(AuditEvent.timestamp.asc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    def get_events_by_user_ids(self, user_ids: List[str], limit: int = 1000) -> List[AuditEvent]:
        """
        Get audit events for multiple users.
        
        Args:
            user_ids: List of user IDs
            limit: Maximum number of events to return
            
        Returns:
            List of audit events for users ordered by timestamp
        """
        session = self.get_session()
        try:
            return (
                session.query(AuditEvent)
                .filter(AuditEvent.user_id.in_(user_ids))
                .order_by(AuditEvent.timestamp.asc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    def get_events_by_action_types(self, action_types: List[str], limit: int = 1000) -> List[AuditEvent]:
        """
        Get audit events for multiple action types.
        
        Args:
            action_types: List of action types
            limit: Maximum number of events to return
            
        Returns:
            List of audit events for action types ordered by timestamp
        """
        session = self.get_session()
        try:
            return (
                session.query(AuditEvent)
                .filter(AuditEvent.action_type.in_(action_types))
                .order_by(AuditEvent.timestamp.asc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    def get_events_by_selector_ids(self, selector_ids: List[str], limit: int = 1000) -> List[AuditEvent]:
        """
        Get audit events for multiple selectors.
        
        Args:
            selector_ids: List of selector IDs
            limit: Maximum number of events to return
            
        Returns:
            List of audit events for selectors ordered by timestamp
        """
        session = self.get_session()
        try:
            return (
                session.query(AuditEvent)
                .filter(AuditEvent.selector_id.in_(selector_ids))
                .order_by(AuditEvent.timestamp.asc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    def get_events_by_multiple_filters(
        self,
        user_ids: Optional[List[str]] = None,
        action_types: Optional[List[str]] = None,
        selector_ids: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[AuditEvent]:
        """
        Get audit events with multiple filters applied.
        
        Args:
            user_ids: Optional list of user IDs to filter by
            action_types: Optional list of action types to filter by
            selector_ids: Optional list of selector IDs to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Maximum number of events to return
            
        Returns:
            List of filtered audit events ordered by timestamp
        """
        session = self.get_session()
        try:
            query = session.query(AuditEvent)
            
            if user_ids:
                query = query.filter(AuditEvent.user_id.in_(user_ids))
            
            if action_types:
                query = query.filter(AuditEvent.action_type.in_(action_types))
            
            if selector_ids:
                query = query.filter(AuditEvent.selector_id.in_(selector_ids))
            
            if start_date:
                query = query.filter(AuditEvent.timestamp >= start_date)
            
            if end_date:
                query = query.filter(AuditEvent.timestamp <= end_date)
            
            return (
                query.order_by(AuditEvent.timestamp.asc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()
    
    def get_by_user_id_and_action_type(
        self, 
        user_id: str, 
        action_type: str, 
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        Get audit events for a specific user and action type.
        
        Args:
            user_id: The user ID
            action_type: The action type
            limit: Maximum number of events to return
            
        Returns:
            List of audit events for user and action type ordered by timestamp
        """
        session = self.get_session()
        try:
            return (
                session.query(AuditEvent)
                .filter(and_(
                    AuditEvent.user_id == user_id,
                    AuditEvent.action_type == action_type
                ))
                .order_by(desc(AuditEvent.timestamp))
                .limit(limit)
                .all()
            )
        finally:
            session.close()
