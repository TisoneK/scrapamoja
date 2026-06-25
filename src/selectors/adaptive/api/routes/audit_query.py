"""
Audit Query API Routes.

This implements Epic 6 (Audit Logging) requirements for Story 6.3.
Provides REST API endpoints for querying audit history with:
- Multi-criteria filtering (selector, user, date, action type)
- Pagination (offset-based and cursor-based)
- Sorting by various fields
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends
import structlog

from ..schemas.audit_schemas import (
    AuditQueryResponse,
    SelectorAuditQueryResponse,
    UserAuditQueryResponse,
    DateRangeQueryResponse,
    AuditEventResponse,
)
from ...services.audit_query_service import (
    AuditQueryService,
    get_audit_query_service,
    SortField,
    SortOrder,
    AuditQueryParams,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


def parse_sort_field(field: str) -> SortField:
    """Parse sort field string to SortField enum."""
    field_map = {
        "timestamp": SortField.TIMESTAMP,
        "user_id": SortField.USER,
        "selector_id": SortField.SELECTOR,
        "action_type": SortField.ACTION,
    }
    return field_map.get(field.lower(), SortField.TIMESTAMP)


def parse_sort_order(order: str) -> SortOrder:
    """Parse sort order string to SortOrder enum."""
    return SortOrder.DESC if order.lower() == "desc" else SortOrder.ASC


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")


@router.get("/log", response_model=AuditQueryResponse)
async def query_audit_log(
    selector_id: Optional[str] = Query(None, description="Filter by selector ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Start date for filtering (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date for filtering (ISO format)"),
    action_types: Optional[List[str]] = Query(None, description="Filter by action types"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    sort_by: str = Query("timestamp", description="Sort field: timestamp, user_id, selector_id, action_type"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    audit_query_service: AuditQueryService = Depends(get_audit_query_service)
) -> AuditQueryResponse:
    """
    Query audit log with filters, pagination, and sorting.
    
    Supports:
    - Filtering by selector_id, user_id, date range, action types
    - Offset-based pagination with limit and offset
    - Cursor-based pagination for efficient large dataset traversal
    - Sorting by timestamp, user_id, selector_id, or action_type
    """
    try:
        # Validate date range
        parsed_start_date = parse_date(start_date)
        parsed_end_date = parse_date(end_date)
        
        if parsed_start_date and parsed_end_date and parsed_start_date > parsed_end_date:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")
        
        # Validate sort parameters
        sort_field = parse_sort_field(sort_by)
        sort_order_enum = parse_sort_order(sort_order)
        
        # Build query params
        params = AuditQueryParams(
            selector_id=selector_id,
            user_id=user_id,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            action_types=action_types,
            limit=limit,
            offset=offset,
            cursor=cursor,
            sort_by=sort_field,
            sort_order=sort_order_enum,
        )
        
        # Execute query
        result = audit_query_service.query_audit_history(params)
        
        # Convert to response models
        event_responses = [AuditEventResponse.from_audit_event(event) for event in result.events]
        
        return AuditQueryResponse(
            events=event_responses,
            total_count=result.total_count,
            has_more=result.has_more,
            next_cursor=result.next_cursor,
            filters_applied=result.filters_applied,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to query audit log",
            selector_id=selector_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/log/selector/{selector_id}", response_model=SelectorAuditQueryResponse)
async def query_by_selector(
    selector_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    sort_by: str = Query("timestamp", description="Sort field: timestamp, user_id, selector_id, action_type"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    audit_query_service: AuditQueryService = Depends(get_audit_query_service)
) -> SelectorAuditQueryResponse:
    """
    Query audit log by selector ID.
    
    Returns all decisions related to the specified selector with
    pagination and sorting support.
    """
    try:
        # Validate sort parameters
        sort_field = parse_sort_field(sort_by)
        sort_order_enum = parse_sort_order(sort_order)
        
        # Query by selector
        result = audit_query_service.query_by_selector(
            selector_id=selector_id,
            limit=limit,
            offset=offset,
            sort_by=sort_field,
            sort_order=sort_order_enum,
        )
        
        # Convert to response models
        event_responses = [AuditEventResponse.from_audit_event(event) for event in result.events]
        
        return SelectorAuditQueryResponse(
            selector_id=selector_id,
            events=event_responses,
            total_count=result.total_count,
            has_more=result.has_more,
            next_cursor=result.next_cursor,
            filters_applied=result.filters_applied,
        )
        
    except Exception as e:
        logger.error(
            "Failed to query audit log by selector",
            selector_id=selector_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/log/user/{user_id}", response_model=UserAuditQueryResponse)
async def query_by_user(
    user_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    sort_by: str = Query("timestamp", description="Sort field: timestamp, user_id, selector_id, action_type"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    audit_query_service: AuditQueryService = Depends(get_audit_query_service)
) -> UserAuditQueryResponse:
    """
    Query audit log by user ID.
    
    Returns all decisions made by the specified user with
    pagination and sorting support.
    """
    try:
        # Validate sort parameters
        sort_field = parse_sort_field(sort_by)
        sort_order_enum = parse_sort_order(sort_order)
        
        # Query by user
        result = audit_query_service.query_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
            sort_by=sort_field,
            sort_order=sort_order_enum,
        )
        
        # Convert to response models
        event_responses = [AuditEventResponse.from_audit_event(event) for event in result.events]
        
        return UserAuditQueryResponse(
            user_id=user_id,
            events=event_responses,
            total_count=result.total_count,
            has_more=result.has_more,
            next_cursor=result.next_cursor,
            filters_applied=result.filters_applied,
        )
        
    except Exception as e:
        logger.error(
            "Failed to query audit log by user",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/log/date-range", response_model=DateRangeQueryResponse)
async def query_by_date_range(
    start: str = Query(..., description="Start date for filtering (ISO format)"),
    end: str = Query(..., description="End date for filtering (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    sort_by: str = Query("timestamp", description="Sort field: timestamp, user_id, selector_id, action_type"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    audit_query_service: AuditQueryService = Depends(get_audit_query_service)
) -> DateRangeQueryResponse:
    """
    Query audit log by date range.
    
    Returns all decisions within the specified date range with
    pagination and sorting support.
    """
    try:
        # Parse dates
        parsed_start_date = parse_date(start)
        parsed_end_date = parse_date(end)
        
        if not parsed_start_date or not parsed_end_date:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format.")
        
        if parsed_start_date > parsed_end_date:
            raise HTTPException(status_code=400, detail="start date must be before end date")
        
        # Validate sort parameters
        sort_field = parse_sort_field(sort_by)
        sort_order_enum = parse_sort_order(sort_order)
        
        # Query by date range
        result = audit_query_service.query_by_date_range(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            limit=limit,
            offset=offset,
            sort_by=sort_field,
            sort_order=sort_order_enum,
        )
        
        # Convert to response models
        event_responses = [AuditEventResponse.from_audit_event(event) for event in result.events]
        
        return DateRangeQueryResponse(
            start_date=start,
            end_date=end,
            events=event_responses,
            total_count=result.total_count,
            has_more=result.has_more,
            next_cursor=result.next_cursor,
            filters_applied=result.filters_applied,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to query audit log by date range",
            start=start,
            end=end,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")
