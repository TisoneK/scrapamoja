"""
Audit Trail Service for querying and analyzing audit history.

This implements Epic 6 (Audit Logging) requirements for Story 6.2.
Provides comprehensive audit trail querying with chronological ordering,
connected decision detection, and user attribution.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import structlog

from ..db.repositories.audit_event_repository import AuditEventRepository
from ..db.models.audit_event import AuditEvent

logger = structlog.get_logger(__name__)


class AuditTrailService:
    """
    Service for querying and analyzing audit trails.
    
    This service provides comprehensive audit trail functionality including:
    - Chronological ordering of events
    - Connected decision detection (e.g., reject after approval)
    - User attribution and filtering
    - Export capabilities for compliance
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize audit trail service.
        
        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        if db_path is None:
            # Use default database location in project data directory
            from pathlib import Path
            db_path = Path("data/audit_log.db")
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.repository = AuditEventRepository(str(db_path))
        logger.info("Audit trail service initialized", db_path=str(db_path))
    
    def get_chronological_audit_trail(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_ids: Optional[List[str]] = None,
        action_types: Optional[List[str]] = None,
        selector_ids: Optional[List[str]] = None,
        limit: int = 1000,
    ) -> List[AuditEvent]:
        """
        Get audit trail in chronological order with optional filters.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            user_ids: Optional list of user IDs to filter by
            action_types: Optional list of action types to filter by
            selector_ids: Optional list of selector IDs to filter by
            limit: Maximum number of events to return
            
        Returns:
            List of audit events in chronological order
        """
        try:
            # Determine which query method to use based on filters
            if start_date and end_date and not (user_ids or action_types or selector_ids):
                events = self.repository.get_events_by_date_range(start_date, end_date, limit)
            elif user_ids or action_types or selector_ids:
                events = self.repository.get_events_by_multiple_filters(
                    user_ids=user_ids,
                    action_types=action_types,
                    selector_ids=selector_ids,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
            else:
                events = self.repository.get_all_events(limit)
            
            logger.info(
                "Retrieved chronological audit trail",
                event_count=len(events),
                start_date=start_date.isoformat() if start_date else None,
                end_date=end_date.isoformat() if end_date else None,
                user_ids=user_ids,
                action_types=action_types,
                selector_ids=selector_ids,
            )
            
            return events
            
        except Exception as e:
            logger.error(
                "Failed to retrieve chronological audit trail",
                start_date=start_date,
                end_date=end_date,
                user_ids=user_ids,
                action_types=action_types,
                selector_ids=selector_ids,
                error=str(e),
            )
            raise
    
    def detect_connected_decisions(self, selector_id: str) -> List[Dict[str, Any]]:
        """
        Detect connected decisions for a specific selector.
        
        Connected decisions are sequences like:
        - Approval after rejection
        - Rejection after approval
        - Multiple rejections/approvals for same selector
        
        Uses O(n) algorithm with hash maps for performance.
        
        Args:
            selector_id: The selector ID to analyze
            
        Returns:
            List of connected decision relationships
        """
        try:
            events = self.repository.get_events_by_selector_id(selector_id)
            
            connections = []
            
            # Create hash maps for O(1) lookups
            approval_events = {}
            rejection_events = {}
            
            # Categorize events by type and index
            for i, event in enumerate(events):
                if event.action_type == "selector_approved":
                    approval_events[i] = event
                elif event.action_type == "selector_rejected":
                    rejection_events[i] = event
            
            # Find approval after rejection (O(n) instead of O(n²))
            for rej_idx, rejection_event in rejection_events.items():
                # Look for any approval after this rejection
                for appr_idx, approval_event in approval_events.items():
                    if appr_idx > rej_idx:
                        connections.append({
                            "type": "approval_after_rejection",
                            "rejection_event": rejection_event,
                            "approval_event": approval_event,
                            "selector_id": selector_id,
                            "time_difference": approval_event.timestamp - rejection_event.timestamp,
                        })
                        break  # Only need the first approval after rejection
            
            # Find rejection after approval (O(n) instead of O(n²))
            for appr_idx, approval_event in approval_events.items():
                # Look for any rejection after this approval
                for rej_idx, rejection_event in rejection_events.items():
                    if rej_idx > appr_idx:
                        connections.append({
                            "type": "rejection_after_approval",
                            "approval_event": approval_event,
                            "rejection_event": rejection_event,
                            "selector_id": selector_id,
                            "time_difference": rejection_event.timestamp - approval_event.timestamp,
                        })
                        break  # Only need the first rejection after approval
            
            logger.info(
                "Detected connected decisions",
                selector_id=selector_id,
                total_events=len(events),
                connections_found=len(connections),
            )
            
            return connections
            
        except Exception as e:
            logger.error(
                "Failed to detect connected decisions",
                selector_id=selector_id,
                error=str(e),
            )
            raise
    
    def get_user_decision_history(
        self,
        user_id: str,
        action_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """
        Get decision history for a specific user with optional filters.
        
        Args:
            user_id: The user ID
            action_type: Optional action type filter
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Maximum number of events to return
            
        Returns:
            List of audit events for the user in reverse chronological order
        """
        try:
            if action_type:
                events = self.repository.get_by_user_id_and_action_type(
                    user_id, action_type, limit
                )
            else:
                events = self.repository.get_by_user_id(user_id, limit)
            
            # Apply date filtering if specified
            if start_date or end_date:
                filtered_events = []
                for event in events:
                    if start_date and event.timestamp < start_date:
                        continue
                    if end_date and event.timestamp > end_date:
                        continue
                    filtered_events.append(event)
                events = filtered_events
            
            logger.info(
                "Retrieved user decision history",
                user_id=user_id,
                action_type=action_type,
                event_count=len(events),
                start_date=start_date.isoformat() if start_date else None,
                end_date=end_date.isoformat() if end_date else None,
            )
            
            return events
            
        except Exception as e:
            logger.error(
                "Failed to retrieve user decision history",
                user_id=user_id,
                action_type=action_type,
                error=str(e),
            )
            raise
    
    def get_selector_audit_trail(
        self,
        selector_id: str,
        include_connected_decisions: bool = True,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get complete audit trail for a specific selector.
        
        Args:
            selector_id: The selector ID
            include_connected_decisions: Whether to include connected decision analysis
            limit: Maximum number of events to return
            
        Returns:
            Dictionary with selector audit trail and analysis
        """
        try:
            events = self.repository.get_events_by_selector_id(selector_id, limit)
            
            result = {
                "selector_id": selector_id,
                "events": events,
                "event_count": len(events),
                "user_summary": self._summarize_user_activity(events),
                "action_type_summary": self._summarize_action_types(events),
            }
            
            if include_connected_decisions:
                result["connected_decisions"] = self.detect_connected_decisions(selector_id)
            
            logger.info(
                "Retrieved selector audit trail",
                selector_id=selector_id,
                event_count=len(events),
                include_connected_decisions=include_connected_decisions,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to retrieve selector audit trail",
                selector_id=selector_id,
                error=str(e),
            )
            raise
    
    def get_audit_trail_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get summary statistics for the audit trail.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Dictionary with audit trail summary statistics
        """
        try:
            stats = self.repository.get_audit_statistics(start_date, end_date)
            
            # Add additional summary information
            events = self.get_chronological_audit_trail(
                start_date=start_date,
                end_date=end_date,
                limit=10000  # Get more events for accurate summary
            )
            
            # User activity summary
            user_activity = {}
            for event in events:
                user_id = event.user_id
                if user_id not in user_activity:
                    user_activity[user_id] = {
                        "total_events": 0,
                        "approvals": 0,
                        "rejections": 0,
                        "flags": 0,
                        "custom_selectors": 0,
                    }
                
                user_activity[user_id]["total_events"] += 1
                
                if event.action_type == "selector_approved":
                    user_activity[user_id]["approvals"] += 1
                elif event.action_type == "selector_rejected":
                    user_activity[user_id]["rejections"] += 1
                elif event.action_type == "selector_flagged":
                    user_activity[user_id]["flags"] += 1
                elif event.action_type == "custom_selector_created":
                    user_activity[user_id]["custom_selectors"] += 1
            
            # Add to stats
            stats["user_activity"] = user_activity
            stats["unique_users"] = len(user_activity)
            stats["date_range"] = {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            }
            
            logger.info(
                "Generated audit trail summary",
                start_date=start_date.isoformat() if start_date else None,
                end_date=end_date.isoformat() if end_date else None,
                total_events=stats["total_events"],
                unique_users=stats["unique_users"],
            )
            
            return stats
            
        except Exception as e:
            logger.error(
                "Failed to generate audit trail summary",
                start_date=start_date,
                end_date=end_date,
                error=str(e),
            )
            raise
    
    def _summarize_user_activity(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """
        Summarize user activity from a list of events.
        
        Args:
            events: List of audit events
            
        Returns:
            Dictionary with user activity summary
        """
        user_activity = {}
        for event in events:
            user_id = event.user_id
            if user_id not in user_activity:
                user_activity[user_id] = {
                    "event_count": 0,
                    "action_types": set(),
                }
            
            user_activity[user_id]["event_count"] += 1
            user_activity[user_id]["action_types"].add(event.action_type)
        
        # Convert sets to lists for JSON serialization
        for user_id in user_activity:
            user_activity[user_id]["action_types"] = list(user_activity[user_id]["action_types"])
        
        return user_activity
    
    def _summarize_action_types(self, events: List[AuditEvent]) -> Dict[str, int]:
        """
        Summarize action types from a list of events.
        
        Args:
            events: List of audit events
            
        Returns:
            Dictionary with action type counts
        """
        action_counts = {}
        for event in events:
            action_type = event.action_type
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        return action_counts


# Global audit trail service instance
_audit_trail_service: Optional[AuditTrailService] = None


def get_audit_trail_service() -> AuditTrailService:
    """
    Get global audit trail service instance.
    
    Returns:
        Global audit trail service instance
    """
    global _audit_trail_service
    if _audit_trail_service is None:
        _audit_trail_service = AuditTrailService()
    return _audit_trail_service
