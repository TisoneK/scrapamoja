"""
Audit Service for recording human decisions with full context.

This implements Epic 6 (Audit Logging) requirements for Story 6.1.
Provides a high-level service for recording all human decisions in the system.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
from pathlib import Path

import structlog

from ..db.repositories.audit_event_repository import AuditEventRepository
from ..db.models.audit_event import AuditEvent

logger = structlog.get_logger(__name__)


class AuditLogger:
    """
    Service for recording human decisions with full context.
    
    This service provides a high-level interface for recording all human
    decisions (approve, reject, flag, create custom) with complete context
    snapshots for audit trail purposes.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the audit logger.
        
        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        if db_path is None:
            # Use default database location in project data directory
            db_path = Path("data/audit_log.db")
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.repository = AuditEventRepository(str(db_path))
        logger.info("Audit logger initialized", db_path=str(db_path))
    
    def record_decision(
        self,
        action_type: str,
        selector: str,
        user_id: str,
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
        Record a human decision with full context.
        
        Args:
            action_type: Type of action (selector_approved, selector_rejected, 
                        selector_flagged, custom_selector_created)
            selector: The selector string
            user_id: User who performed the action
            selector_id: Unique selector identifier
            failure_id: Associated failure event ID (if applicable)
            context_snapshot: Full context snapshot at decision time
            before_state: State before the change
            after_state: State after the change
            confidence_at_time: Confidence score at time of decision
            reason: Reason for the decision (especially for rejections)
            suggested_alternative: User's suggested alternative selector
            notes: Additional notes
            
        Returns:
            Created audit event
        """
        try:
            # Validate action_type
            valid_actions = {
                "selector_approved",
                "selector_rejected", 
                "selector_flagged",
                "custom_selector_created"
            }
            if action_type not in valid_actions:
                raise ValueError(f"Invalid action_type: {action_type}. Must be one of: {valid_actions}")
            
            # Create audit event
            audit_event = self.repository.create_audit_event(
                action_type=action_type,
                selector=selector,
                user_id=user_id,
                selector_id=selector_id,
                failure_id=failure_id,
                context_snapshot=context_snapshot,
                before_state=before_state,
                after_state=after_state,
                confidence_at_time=confidence_at_time,
                reason=reason,
                suggested_alternative=suggested_alternative,
                notes=notes,
            )
            
            logger.info(
                "Human decision recorded",
                action_type=action_type,
                selector_id=selector_id,
                user_id=user_id,
                audit_event_id=audit_event.id,
            )
            
            return audit_event
            
        except Exception as e:
            logger.error(
                "Failed to record human decision",
                action_type=action_type,
                selector=selector,
                user_id=user_id,
                error=str(e),
            )
            raise
    
    def record_approval(
        self,
        selector: str,
        user_id: str,
        selector_id: Optional[str] = None,
        failure_id: Optional[int] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        confidence_at_time: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> AuditEvent:
        """
        Record a selector approval decision.
        
        Args:
            selector: The approved selector
            user_id: User who approved
            selector_id: Unique selector identifier
            failure_id: Associated failure event ID
            context_snapshot: Context at approval time
            confidence_at_time: Confidence score
            notes: Additional notes
            
        Returns:
            Created audit event
        """
        return self.record_decision(
            action_type="selector_approved",
            selector=selector,
            user_id=user_id,
            selector_id=selector_id,
            failure_id=failure_id,
            context_snapshot=context_snapshot,
            after_state=selector,  # Approved selector becomes the new state
            confidence_at_time=confidence_at_time,
            notes=notes,
        )
    
    def record_rejection(
        self,
        selector: str,
        user_id: str,
        reason: str,
        selector_id: Optional[str] = None,
        failure_id: Optional[int] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        confidence_at_time: Optional[float] = None,
        suggested_alternative: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AuditEvent:
        """
        Record a selector rejection decision.
        
        Args:
            selector: The rejected selector
            user_id: User who rejected
            reason: Reason for rejection
            selector_id: Unique selector identifier
            failure_id: Associated failure event ID
            context_snapshot: Context at rejection time
            confidence_at_time: Confidence score
            suggested_alternative: User's suggested alternative
            notes: Additional notes
            
        Returns:
            Created audit event
        """
        return self.record_decision(
            action_type="selector_rejected",
            selector=selector,
            user_id=user_id,
            selector_id=selector_id,
            failure_id=failure_id,
            context_snapshot=context_snapshot,
            before_state=selector,  # Rejected selector was the previous state
            reason=reason,
            confidence_at_time=confidence_at_time,
            suggested_alternative=suggested_alternative,
            notes=notes,
        )
    
    def record_flagging(
        self,
        selector: str,
        user_id: str,
        selector_id: Optional[str] = None,
        failure_id: Optional[int] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        confidence_at_time: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> AuditEvent:
        """
        Record a selector flagging decision.
        
        Args:
            selector: The flagged selector
            user_id: User who flagged
            selector_id: Unique selector identifier
            failure_id: Associated failure event ID
            context_snapshot: Context at flagging time
            confidence_at_time: Confidence score
            notes: Additional notes
            
        Returns:
            Created audit event
        """
        return self.record_decision(
            action_type="selector_flagged",
            selector=selector,
            user_id=user_id,
            selector_id=selector_id,
            failure_id=failure_id,
            context_snapshot=context_snapshot,
            confidence_at_time=confidence_at_time,
            notes=notes,
        )
    
    def record_custom_selector_creation(
        self,
        selector: str,
        user_id: str,
        selector_id: Optional[str] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        confidence_at_time: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> AuditEvent:
        """
        Record a custom selector creation decision.
        
        Args:
            selector: The created custom selector
            user_id: User who created it
            selector_id: Unique selector identifier
            context_snapshot: Context at creation time
            confidence_at_time: Confidence score
            notes: Additional notes
            
        Returns:
            Created audit event
        """
        return self.record_decision(
            action_type="custom_selector_created",
            selector=selector,
            user_id=user_id,
            selector_id=selector_id,
            context_snapshot=context_snapshot,
            after_state=selector,  # Created selector becomes the new state
            confidence_at_time=confidence_at_time,
            notes=notes,
        )
    
    def get_decision_history(
        self,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        selector_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """
        Get decision history with optional filters.
        
        Args:
            user_id: Filter by user ID
            action_type: Filter by action type
            selector_id: Filter by selector ID
            limit: Maximum number of events to return
            
        Returns:
            List of audit events
        """
        try:
            if user_id:
                return self.repository.get_by_user_id(user_id, limit)
            elif action_type:
                return self.repository.get_by_action_type(action_type, limit)
            else:
                # If no specific filters, get recent events
                # This would require adding a get_recent_events method to repository
                logger.warning("Getting recent events not implemented, returning empty list")
                return []
                
        except Exception as e:
            logger.error(
                "Failed to get decision history",
                user_id=user_id,
                action_type=action_type,
                selector_id=selector_id,
                error=str(e),
            )
            raise
    
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
        try:
            return self.repository.get_audit_statistics(start_date, end_date)
            
        except Exception as e:
            logger.error(
                "Failed to get audit statistics",
                start_date=start_date,
                end_date=end_date,
                error=str(e),
            )
            raise


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Get the global audit logger instance.
    
    Returns:
        Global audit logger instance
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def record_human_decision(
    action_type: str,
    selector: str,
    user_id: str,
    **kwargs
) -> AuditEvent:
    """
    Convenience function to record a human decision.
    
    Args:
        action_type: Type of action
        selector: The selector string
        user_id: User who performed the action
        **kwargs: Additional arguments passed to record_decision
        
    Returns:
        Created audit event
    """
    audit_logger = get_audit_logger()
    return audit_logger.record_decision(
        action_type=action_type,
        selector=selector,
        user_id=user_id,
        **kwargs
    )
