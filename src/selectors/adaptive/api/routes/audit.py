"""
Audit Trail API Routes.

This implements Epic 6 (Audit Logging) requirements for Story 6.2.
Provides REST API endpoints for querying audit trails with filtering,
connected decision detection, and user attribution.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse, StreamingResponse
import structlog
import csv
import io

from ..schemas.audit_schemas import (
    AuditTrailResponse,
    SelectorAuditTrailResponse,
    UserDecisionHistoryResponse,
    ConnectedDecisionResponse,
    AuditTrailSummaryResponse,
    AuditEventResponse
)
from ...services.audit_trail_service import AuditTrailService, get_audit_trail_service
from ...services.audit_service import get_audit_logger

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/trail", response_model=AuditTrailResponse)
async def get_audit_trail(
    start_date: Optional[str] = Query(None, description="Start date for filtering (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date for filtering (ISO format)"),
    user_ids: Optional[List[str]] = Query(None, description="Filter by user IDs"),
    action_types: Optional[List[str]] = Query(None, description="Filter by action types"),
    selector_ids: Optional[List[str]] = Query(None, description="Filter by selector IDs"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of events to return"),
    audit_trail_service: AuditTrailService = Depends(get_audit_trail_service)
) -> AuditTrailResponse:
    """
    Get audit trail with optional filtering.
    
    Provides chronological audit trail with support for:
    - Date range filtering
    - User filtering
    - Action type filtering
    - Selector filtering
    - Connected decision detection
    """
    try:
        # Parse date strings if provided
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid start_date format: {e}")
        
        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid end_date format: {e}")
        
        # Validate date range
        if parsed_start_date and parsed_end_date and parsed_start_date > parsed_end_date:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")
        
        # Get audit trail
        events = audit_trail_service.get_chronological_audit_trail(
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            user_ids=user_ids,
            action_types=action_types,
            selector_ids=selector_ids,
            limit=limit
        )
        
        # Convert to response models
        event_responses = [AuditEventResponse.from_audit_event(event) for event in events]
        
        return AuditTrailResponse(
            events=event_responses,
            total_count=len(events),
            filters_applied={
                "start_date": start_date,
                "end_date": end_date,
                "user_ids": user_ids,
                "action_types": action_types,
                "selector_ids": selector_ids,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get audit trail",
            start_date=start_date,
            end_date=end_date,
            user_ids=user_ids,
            action_types=action_types,
            selector_ids=selector_ids,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trail/{selector_id}", response_model=SelectorAuditTrailResponse)
async def get_selector_audit_trail(
    selector_id: str,
    include_connected_decisions: bool = Query(True, description="Include connected decision analysis"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    audit_trail_service: AuditTrailService = Depends(get_audit_trail_service)
) -> SelectorAuditTrailResponse:
    """
    Get complete audit trail for a specific selector.
    
    Returns all audit events for the selector with optional
    connected decision analysis showing relationships between events.
    """
    try:
        # Get selector audit trail
        trail_data = audit_trail_service.get_selector_audit_trail(
            selector_id=selector_id,
            include_connected_decisions=include_connected_decisions,
            limit=limit
        )
        
        # Convert events to response models
        event_responses = [AuditEventResponse.from_audit_event(event) for event in trail_data["events"]]
        
        # Convert connected decisions to response models
        connected_decisions = []
        if include_connected_decisions and "connected_decisions" in trail_data:
            for connection in trail_data["connected_decisions"]:
                connected_decisions.append(ConnectedDecisionResponse(
                    type=connection["type"],
                    selector_id=connection["selector_id"],
                    time_difference=str(connection["time_difference"]),
                    approval_event=AuditEventResponse.from_audit_event(connection["approval_event"]) if "approval_event" in connection else None,
                    rejection_event=AuditEventResponse.from_audit_event(connection["rejection_event"]) if "rejection_event" in connection else None,
                ))
        
        return SelectorAuditTrailResponse(
            selector_id=selector_id,
            events=event_responses,
            event_count=trail_data["event_count"],
            user_summary=trail_data["user_summary"],
            action_type_summary=trail_data["action_type_summary"],
            connected_decisions=connected_decisions if include_connected_decisions else None,
        )
        
    except Exception as e:
        logger.error(
            "Failed to get selector audit trail",
            selector_id=selector_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trail/user/{user_id}", response_model=UserDecisionHistoryResponse)
async def get_user_decision_history(
    user_id: str,
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[str] = Query(None, description="Start date for filtering (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date for filtering (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    audit_trail_service: AuditTrailService = Depends(get_audit_trail_service)
) -> UserDecisionHistoryResponse:
    """
    Get decision history for a specific user.
    
    Returns all decisions made by the user with optional filtering
    by action type and date range.
    """
    try:
        # Parse date strings if provided
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid start_date format: {e}")
        
        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid end_date format: {e}")
        
        # Validate date range
        if parsed_start_date and parsed_end_date and parsed_start_date > parsed_end_date:
            raise HTTPException(status_code=400, detail="start_date must be before end_date")
        
        # Get user decision history
        events = audit_trail_service.get_user_decision_history(
            user_id=user_id,
            action_type=action_type,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            limit=limit
        )
        
        # Convert to response models
        event_responses = [AuditEventResponse.from_audit_event(event) for event in events]
        
        return UserDecisionHistoryResponse(
            user_id=user_id,
            events=event_responses,
            event_count=len(events),
            filters_applied={
                "action_type": action_type,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get user decision history",
            user_id=user_id,
            action_type=action_type,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/summary", response_model=AuditTrailSummaryResponse)
async def get_audit_trail_summary(
    start_date: Optional[str] = Query(None, description="Start date for filtering (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date for filtering (ISO format)"),
    audit_trail_service: AuditTrailService = Depends(get_audit_trail_service)
) -> AuditTrailSummaryResponse:
    """
    Get audit trail summary statistics.
    
    Returns summary statistics including:
    - Total events
    - Action type breakdown
    - User activity summary
    - Date range information
    """
    try:
        # Parse date strings if provided
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid start_date format: {e}")
        
        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid end_date format: {e}")
        
        # Get summary statistics
        summary = audit_trail_service.get_audit_trail_summary(
            start_date=parsed_start_date,
            end_date=parsed_end_date
        )
        
        return AuditTrailSummaryResponse(
            total_events=summary["total_events"],
            unique_users=summary["unique_users"],
            action_counts=summary["action_counts"],
            user_activity=summary["user_activity"],
            date_range=summary["date_range"],
            average_approval_confidence=summary.get("average_approval_confidence"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get audit trail summary",
            start_date=start_date,
            end_date=end_date,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/export/json")
async def export_audit_trail_json(
    start_date: Optional[str] = Query(None, description="Start date for filtering (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date for filtering (ISO format)"),
    user_ids: Optional[List[str]] = Query(None, description="Filter by user IDs"),
    action_types: Optional[List[str]] = Query(None, description="Filter by action types"),
    selector_ids: Optional[List[str]] = Query(None, description="Filter by selector IDs"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of events to export"),
    audit_trail_service: AuditTrailService = Depends(get_audit_trail_service)
) -> JSONResponse:
    """
    Export audit trail in JSON format.
    
    Returns audit trail data in JSON format with full context
    for compliance and analysis purposes.
    """
    try:
        # Parse date strings if provided
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid start_date format: {e}")
        
        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid end_date format: {e}")
        
        # Get audit trail with memory-efficient chunking for large datasets
        if limit > 20000:  # Use chunking for very large exports
            events = []
            chunk_size = 5000
            remaining = limit
            
            while remaining > 0:
                current_chunk_size = min(chunk_size, remaining)
                chunk_events = audit_trail_service.get_chronological_audit_trail(
                    start_date=parsed_start_date,
                    end_date=parsed_end_date,
                    user_ids=user_ids,
                    action_types=action_types,
                    selector_ids=selector_ids,
                    limit=current_chunk_size
                )
                events.extend(chunk_events)
                remaining -= len(chunk_events)
                
                if len(chunk_events) < current_chunk_size:
                    break  # No more events available
        else:
            events = audit_trail_service.get_chronological_audit_trail(
                start_date=parsed_start_date,
                end_date=parsed_end_date,
                user_ids=user_ids,
                action_types=action_types,
                selector_ids=selector_ids,
                limit=limit
            )
        
        # Convert to full context JSON
        export_data = {
            "export_metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "filters_applied": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "user_ids": user_ids,
                    "action_types": action_types,
                    "selector_ids": selector_ids,
                },
                "total_events": len(events),
            },
            "audit_events": [event.to_dict() for event in events]
        }
        
        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f"attachment; filename=audit_trail_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to export audit trail as JSON",
            start_date=start_date,
            end_date=end_date,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/export/csv")
async def export_audit_trail_csv(
    start_date: Optional[str] = Query(None, description="Start date for filtering (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date for filtering (ISO format)"),
    user_ids: Optional[List[str]] = Query(None, description="Filter by user IDs"),
    action_types: Optional[List[str]] = Query(None, description="Filter by action types"),
    selector_ids: Optional[List[str]] = Query(None, description="Filter by selector IDs"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of events to export"),
    audit_trail_service: AuditTrailService = Depends(get_audit_trail_service)
) -> StreamingResponse:
    """
    Export audit trail in CSV format.
    
    Returns audit trail data in CSV format for compliance reporting
    and data analysis in spreadsheet applications.
    """
    try:
        # Parse date strings if provided
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid start_date format: {e}")
        
        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid end_date format: {e}")
        
        def generate_csv():
            """Generator function for streaming CSV data."""
            # Write header
            yield ",".join([
                "id", "timestamp", "action_type", "selector_id", "selector",
                "user_id", "failure_id", "before_state", "after_state",
                "confidence_at_time", "reason", "suggested_alternative", "notes"
            ]) + "\n"
            
            # Get audit trail with memory-efficient chunking for large datasets
            chunk_size = 2000
            remaining = limit
            offset = 0
            
            while remaining > 0:
                current_chunk_size = min(chunk_size, remaining)
                
                # Get chunk of events with offset for true pagination
                events = audit_trail_service.get_chronological_audit_trail(
                    start_date=parsed_start_date,
                    end_date=parsed_end_date,
                    user_ids=user_ids,
                    action_types=action_types,
                    selector_ids=selector_ids,
                    limit=current_chunk_size,
                    offset=offset
                )
                
                if not events:
                    break
                
                # Write data rows for this chunk
                for event in events:
                    # Escape CSV fields and handle quotes
                    def escape_field(value):
                        if value is None:
                            return ""
                        str_value = str(value)
                        if '"' in str_value or ',' in str_value or '\n' in str_value:
                            return f'"{str_value.replace('"', '""')}"'
                        return str_value
                    
                    row = [
                        escape_field(event.id),
                        escape_field(event.timestamp.isoformat() if event.timestamp else ""),
                        escape_field(event.action_type),
                        escape_field(event.selector_id or ""),
                        escape_field(event.selector),
                        escape_field(event.user_id),
                        escape_field(event.failure_id or ""),
                        escape_field(event.before_state or ""),
                        escape_field(event.after_state or ""),
                        escape_field(event.confidence_at_time or ""),
                        escape_field(event.reason or ""),
                        escape_field(event.suggested_alternative or ""),
                        escape_field(event.notes or "")
                    ]
                    yield ",".join(row) + "\n"
                
                remaining -= len(events)
                offset += len(events)
                
                if len(events) < current_chunk_size:
                    break  # No more events available
        
        # Create streaming response
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_trail_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to export audit trail as CSV",
            start_date=start_date,
            end_date=end_date,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")
