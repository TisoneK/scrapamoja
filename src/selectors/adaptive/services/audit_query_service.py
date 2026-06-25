"""
Audit Query Service for advanced audit history querying.

This implements Epic 6 (Audit Logging) requirements for Story 6.3.
Provides advanced query capabilities with multi-criteria filtering,
pagination, and sorting for efficient audit history investigation.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Literal
from dataclasses import dataclass
from enum import Enum

import structlog

from ..db.repositories.audit_event_repository import AuditEventRepository
from ..db.models.audit_event import AuditEvent

logger = structlog.get_logger(__name__)


class SortField(str, Enum):
    """Sort field options for audit queries."""
    TIMESTAMP = "timestamp"
    USER = "user_id"
    SELECTOR = "selector_id"
    ACTION = "action_type"


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class AuditQueryParams:
    """Parameters for audit query with pagination and sorting."""
    selector_id: Optional[str] = None
    user_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    action_types: Optional[List[str]] = None
    # Pagination
    limit: int = 100
    offset: int = 0
    cursor: Optional[str] = None  # Cursor-based pagination
    # Sorting
    sort_by: SortField = SortField.TIMESTAMP
    sort_order: SortOrder = SortOrder.DESC


@dataclass
class PaginatedAuditResponse:
    """Paginated response for audit queries."""
    events: List[AuditEvent]
    total_count: int
    has_more: bool
    filters_applied: Dict[str, Any]
    next_cursor: Optional[str] = None


class AuditQueryService:
    """
    Service for advanced audit query operations.
    
    This service provides:
    - Multi-criteria filtering (selector, user, date, action type)
    - Pagination (offset-based and cursor-based)
    - Sorting by various fields
    - Combined query support
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize audit query service.
        
        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        if db_path is None:
            from pathlib import Path
            db_path_str = str(Path("data/audit_log.db"))
            Path(db_path_str).parent.mkdir(parents=True, exist_ok=True)
        else:
            db_path_str = db_path
        
        self.repository = AuditEventRepository(db_path_str)
        logger.info("Audit query service initialized", db_path=db_path_str)
    
    def query_audit_history(
        self,
        params: AuditQueryParams,
    ) -> PaginatedAuditResponse:
        """
        Query audit history with filters, pagination, and sorting.
        
        Args:
            params: Query parameters including filters, pagination, and sorting
            
        Returns:
            Paginated response with audit events
        """
        try:
            # Build filters
            filters: Dict[str, Any] = {}
            if params.selector_id:
                filters["selector_id"] = params.selector_id
            if params.user_id:
                filters["user_id"] = params.user_id
            if params.start_date:
                filters["start_date"] = params.start_date
            if params.end_date:
                filters["end_date"] = params.end_date
            if params.action_types:
                filters["action_types"] = params.action_types
            
            # Get total count for pagination
            total_count = self._get_filtered_count(
                selector_id=params.selector_id,
                user_id=params.user_id,
                start_date=params.start_date,
                end_date=params.end_date,
                action_types=params.action_types,
            )
            
            # Get events with pagination and sorting
            events = self._query_with_pagination_and_sort(params)
            
            # Determine if there are more results
            has_more = (params.offset + len(events)) < total_count
            
            # Generate next cursor if there are more results
            next_cursor = None
            if has_more and events:
                # Use the last event's ID as cursor
                next_cursor = str(events[-1].id)
            
            logger.info(
                "Queried audit history",
                total_count=total_count,
                returned_count=len(events),
                has_more=has_more,
                filters=filters,
                sort_by=params.sort_by.value,
                sort_order=params.sort_order.value,
            )
            
            return PaginatedAuditResponse(
                events=events,
                total_count=total_count,
                has_more=has_more,
                next_cursor=next_cursor,
                filters_applied=self._serialize_filters(params),
            )
            
        except Exception as e:
            logger.error(
                "Failed to query audit history",
                error=str(e),
                params=params,
            )
            raise
    
    def query_by_selector(
        self,
        selector_id: str,
        limit: int = 100,
        offset: int = 0,
        sort_by: SortField = SortField.TIMESTAMP,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> PaginatedAuditResponse:
        """
        Query audit events by selector ID.
        
        Args:
            selector_id: The selector ID to filter by
            limit: Maximum number of events to return
            offset: Number of events to skip
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            
        Returns:
            Paginated response with audit events
        """
        params = AuditQueryParams(
            selector_id=selector_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return self.query_audit_history(params)
    
    def query_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        sort_by: SortField = SortField.TIMESTAMP,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> PaginatedAuditResponse:
        """
        Query audit events by user ID.
        
        Args:
            user_id: The user ID to filter by
            limit: Maximum number of events to return
            offset: Number of events to skip
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            
        Returns:
            Paginated response with audit events
        """
        params = AuditQueryParams(
            user_id=user_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return self.query_audit_history(params)
    
    def query_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100,
        offset: int = 0,
        sort_by: SortField = SortField.TIMESTAMP,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> PaginatedAuditResponse:
        """
        Query audit events within a date range.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            limit: Maximum number of events to return
            offset: Number of events to skip
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            
        Returns:
            Paginated response with audit events
        """
        params = AuditQueryParams(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return self.query_audit_history(params)
    
    def query_with_cursor(
        self,
        cursor: Optional[str] = None,
        limit: int = 100,
        selector_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action_types: Optional[List[str]] = None,
        sort_by: SortField = SortField.TIMESTAMP,
        sort_order: SortOrder = SortOrder.DESC,
    ) -> PaginatedAuditResponse:
        """
        Query audit events using cursor-based pagination.
        
        Args:
            cursor: Cursor from previous response (last event ID)
            limit: Maximum number of events to return
            selector_id: Optional selector ID filter
            user_id: Optional user ID filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            action_types: Optional action types filter
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            
        Returns:
            Paginated response with audit events
        """
        params = AuditQueryParams(
            selector_id=selector_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            action_types=action_types,
            limit=limit,
            cursor=cursor,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return self.query_audit_history(params)
    
    def _get_filtered_count(
        self,
        selector_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action_types: Optional[List[str]] = None,
    ) -> int:
        """
        Get count of filtered audit events using efficient COUNT query.
        
        Args:
            selector_id: Optional selector ID filter
            user_id: Optional user ID filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            action_types: Optional action types filter
            
        Returns:
            Count of matching events
        """
        # Use repository's count method for efficient counting
        return self.repository.count_events_by_multiple_filters(
            selector_ids=[selector_id] if selector_id else None,
            user_ids=[user_id] if user_id else None,
            action_types=action_types,
            start_date=start_date,
            end_date=end_date,
        )
    
    def _query_with_pagination_and_sort(
        self,
        params: AuditQueryParams,
    ) -> List[AuditEvent]:
        """
        Query events with pagination and sorting applied.
        
        Args:
            params: Query parameters
            
        Returns:
            List of audit events
        """
        # Get events using repository
        events = self.repository.get_events_by_multiple_filters(
            selector_ids=[params.selector_id] if params.selector_id else None,
            user_ids=[params.user_id] if params.user_id else None,
            action_types=params.action_types,
            start_date=params.start_date,
            end_date=params.end_date,
            limit=100000,  # Get all to apply sorting
        )
        
        # Apply sorting
        events = self._sort_events(events, params.sort_by, params.sort_order)
        
        # Apply cursor-based pagination if cursor provided
        if params.cursor:
            try:
                cursor_id = int(params.cursor)
                # Find index of cursor event
                for i, event in enumerate(events):
                    event_id = int(event.id)
                    if event_id == cursor_id:
                        # Start from next event after cursor
                        events = events[i + 1:]
                        break
            except ValueError:
                logger.warning("Invalid cursor value", cursor=params.cursor)
        
        # Apply offset and limit
        events = events[params.offset:params.offset + params.limit]
        
        return events
    
    def _sort_events(
        self,
        events: List[AuditEvent],
        sort_by: SortField,
        sort_order: SortOrder,
    ) -> List[AuditEvent]:
        """
        Sort events by specified field and order.
        
        Args:
            events: List of audit events
            sort_by: Field to sort by
            sort_order: Sort order
            
        Returns:
            Sorted list of events
        """
        reverse = sort_order == SortOrder.DESC
        
        if sort_by == SortField.TIMESTAMP:
            return sorted(events, key=lambda e: e.timestamp or datetime.min, reverse=reverse)
        elif sort_by == SortField.USER:
            return sorted(events, key=lambda e: e.user_id or "", reverse=reverse)
        elif sort_by == SortField.SELECTOR:
            return sorted(events, key=lambda e: e.selector_id or "", reverse=reverse)
        elif sort_by == SortField.ACTION:
            return sorted(events, key=lambda e: e.action_type or "", reverse=reverse)
        
        return events
    
    def _serialize_filters(self, params: AuditQueryParams) -> Dict[str, Any]:
        """
        Serialize filters for response.
        
        Args:
            params: Query parameters
            
        Returns:
            Dictionary of applied filters
        """
        filters: Dict[str, Any] = {}
        
        if params.selector_id:
            filters["selector_id"] = params.selector_id
        if params.user_id:
            filters["user_id"] = params.user_id
        if params.start_date:
            filters["start_date"] = params.start_date.isoformat()
        if params.end_date:
            filters["end_date"] = params.end_date.isoformat()
        if params.action_types:
            filters["action_types"] = params.action_types
        
        filters["sort_by"] = params.sort_by.value
        filters["sort_order"] = params.sort_order.value
        filters["limit"] = params.limit
        filters["offset"] = params.offset
        
        return filters


# Global audit query service instance
_audit_query_service: Optional[AuditQueryService] = None


def get_audit_query_service() -> AuditQueryService:
    """
    Get global audit query service instance.
    
    Returns:
        Global audit query service instance
    """
    global _audit_query_service
    if _audit_query_service is None:
        _audit_query_service = AuditQueryService()
    return _audit_query_service
