"""
Fast Triage Service for optimized failure triage operations.

This service provides optimized triage operations for quick workflow completion,
including one-click approvals, bulk actions, and performance tracking.

Story: 7.3 - Fast Triage Workflow
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from src.observability.logger import get_logger

from ..db.repositories.failure_event_repository import FailureEventRepository
from ..db.repositories.triage_repository import TriageRepository, TriageSummary
from ..db.models.triage_metrics import TriageMetricsRepository
from .failure_service import FailureService


class FastTriageService:
    """
    Service for fast triage operations.
    
    Provides:
    - Optimized failure loading with cursor-based pagination
    - One-click approval for highest confidence selectors
    - Bulk operations for multiple failures
    - Performance tracking and metrics
    - Quick escalation workflow
    """
    
    def __init__(
        self,
        failure_repository: Optional[FailureEventRepository] = None,
        triage_repository: Optional[TriageRepository] = None,
        metrics_repository: Optional[TriageMetricsRepository] = None,
        failure_service: Optional[FailureService] = None,
    ):
        """
        Initialize the fast triage service.
        
        Args:
            failure_repository: Failure event repository
            triage_repository: Optimized triage repository
            metrics_repository: Performance metrics repository
            failure_service: Existing failure service for approvals
        """
        self._logger = get_logger("fast_triage_service")
        
        self.failure_repository = failure_repository or FailureEventRepository()
        self.triage_repository = triage_repository or TriageRepository()
        self.metrics_repository = metrics_repository or TriageMetricsRepository()
        self.failure_service = failure_service or FailureService()
    
    def get_failures_fast(
        self,
        limit: int = 50,
        cursor: Optional[int] = None,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        severity: Optional[str] = None,
        sort_by: str = "severity",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """
        Get failures with optimized loading for fast triage.
        
        Uses cursor-based pagination and minimal field loading
        for quick initial page loads.
        
        Args:
            limit: Maximum results
            cursor: Pagination cursor
            sport: Filter by sport
            site: Filter by site
            severity: Filter by severity
            sort_by: Sort field
            sort_order: Sort direction
            
        Returns:
            Dictionary with failures, next cursor, and counts
        """
        start_time = time.time()
        
        # Get optimized summaries
        summaries, next_cursor = self.triage_repository.get_failure_summaries_fast(
            limit=limit,
            cursor=cursor,
            sport=sport,
            site=site,
            severity=severity,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        # Get quick counts
        counts = self.triage_repository.get_failure_counts(sport=sport, site=site)
        
        # Check for alternatives (from failure service)
        for summary in summaries:
            failure_id = summary.id
            has_alternatives = failure_id in self.failure_service._alternatives
            summary.has_alternatives = has_alternatives
        
        # Record performance
        load_time_ms = (time.time() - start_time) * 1000
        
        return {
            "failures": [
                {
                    "id": s.id,
                    "selector_id": s.selector_id,
                    "error_type": s.error_type,
                    "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                    "severity": s.severity,
                    "sport": s.sport,
                    "site": s.site,
                    "has_alternatives": s.has_alternatives,
                }
                for s in summaries
            ],
            "next_cursor": next_cursor,
            "counts": counts,
            "performance": {
                "load_time_ms": load_time_ms,
                "target_met": load_time_ms < 2000,  # < 2 second target
            },
        }
    
    def quick_approve(
        self,
        failure_id: int,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        One-click approval using highest confidence selector.
        
        Automatically selects and approves the highest confidence
        alternative selector for a failure.
        
        Args:
            failure_id: Failure ID to approve
            user_id: User performing approval
            
        Returns:
            Result dictionary
        """
        start_time = time.time()
        
        # Get failure details
        detail = self.failure_service.get_failure_detail(failure_id)
        
        if not detail:
            return {
                "success": False,
                "message": f"Failure {failure_id} not found",
            }
        
        # Get alternatives
        alternatives = detail.get("alternatives", [])
        
        if not alternatives:
            return {
                "success": False,
                "message": "No alternatives available for approval",
            }
        
        # Find highest confidence selector
        best_alt = max(alternatives, key=lambda a: a.get("confidence_score", 0))
        
        # Approve the best selector
        result = self.failure_service.approve_alternative(
            failure_id=failure_id,
            selector=best_alt.get("selector", ""),
            notes="Quick approve - highest confidence",
            user_id=user_id,
        )
        
        # Record performance
        action_time_ms = (time.time() - start_time) * 1000
        self.metrics_repository.record_action(
            failure_id=failure_id,
            action_type="quick_approve",
            action_time_ms=action_time_ms,
            user_id=user_id,
            metadata={"selector": best_alt.get("selector", "")[:50]},
        )
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "failure_id": failure_id,
            "selector": best_alt.get("selector", ""),
            "confidence": best_alt.get("confidence_score", 0),
            "performance": {
                "action_time_ms": action_time_ms,
                "target_met": action_time_ms < 500,  # < 500ms target
            },
        }
    
    def bulk_approve(
        self,
        failure_ids: List[int],
        strategy: str = "highest_confidence",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Bulk approve multiple failures.
        
        Args:
            failure_ids: List of failure IDs to approve
            strategy: Selection strategy (highest_confidence, most_stable)
            user_id: User performing bulk action
            
        Returns:
            Result dictionary with success/failure counts
        """
        start_time = time.time()
        
        operation_id = f"bulk_approve_{uuid.uuid4().hex[:8]}"
        success_count = 0
        failure_count = 0
        results = []
        
        for failure_id in failure_ids:
            # Get the best alternative based on strategy
            detail = self.failure_service.get_failure_detail(failure_id)
            
            if not detail or not detail.get("alternatives"):
                failure_count += 1
                results.append({
                    "failure_id": failure_id,
                    "success": False,
                    "message": "No alternatives available",
                })
                continue
            
            alternatives = detail.get("alternatives", [])
            
            # Select best alternative
            if strategy == "highest_confidence":
                best_alt = max(alternatives, key=lambda a: a.get("confidence_score", 0))
            else:
                # Default to highest confidence
                best_alt = max(alternatives, key=lambda a: a.get("confidence_score", 0))
            
            # Approve
            result = self.failure_service.approve_alternative(
                failure_id=failure_id,
                selector=best_alt.get("selector", ""),
                notes=f"Bulk approve ({strategy})",
                user_id=user_id,
            )
            
            if result.get("success"):
                success_count += 1
                results.append({
                    "failure_id": failure_id,
                    "success": True,
                    "selector": best_alt.get("selector", ""),
                })
            else:
                failure_count += 1
                results.append({
                    "failure_id": failure_id,
                    "success": False,
                    "message": result.get("message", ""),
                })
        
        # Calculate total time
        total_time_ms = (time.time() - start_time) * 1000
        
        # Record bulk operation
        self.metrics_repository.record_bulk_operation(
            operation_id=operation_id,
            action="bulk_approve",
            failure_count=len(failure_ids),
            total_time_ms=total_time_ms,
            user_id=user_id,
            success_count=success_count,
            failure_count_op=failure_count,
        )
        
        return {
            "success": True,
            "operation_id": operation_id,
            "total": len(failure_ids),
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results,
            "performance": {
                "total_time_ms": total_time_ms,
                "avg_time_per_failure": total_time_ms / len(failure_ids) if failure_ids else 0,
                "target_met": total_time_ms < len(failure_ids) * 2000,  # < 2s per failure
            },
        }
    
    def bulk_reject(
        self,
        failure_ids: List[int],
        reason: str = "Bulk reject",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Bulk reject multiple failures.
        
        Args:
            failure_ids: List of failure IDs to reject
            reason: Reason for rejection
            user_id: User performing bulk action
            
        Returns:
            Result dictionary with success/failure counts
        """
        start_time = time.time()
        
        operation_id = f"bulk_reject_{uuid.uuid4().hex[:8]}"
        success_count = 0
        failure_count = 0
        results = []
        
        for failure_id in failure_ids:
            # Get the first alternative to reject
            detail = self.failure_service.get_failure_detail(failure_id)
            
            if not detail:
                failure_count += 1
                results.append({
                    "failure_id": failure_id,
                    "success": False,
                    "message": "Failure not found",
                })
                continue
            
            # Get selector to reject
            alternatives = detail.get("alternatives", [])
            selector = alternatives[0].get("selector", "") if alternatives else detail.get("failed_selector", "")
            
            # Reject
            result = self.failure_service.reject_alternative(
                failure_id=failure_id,
                selector=selector,
                reason=reason,
                user_id=user_id,
            )
            
            if result.get("success"):
                success_count += 1
                results.append({
                    "failure_id": failure_id,
                    "success": True,
                })
            else:
                failure_count += 1
                results.append({
                    "failure_id": failure_id,
                    "success": False,
                    "message": result.get("message", ""),
                })
        
        # Calculate total time
        total_time_ms = (time.time() - start_time) * 1000
        
        # Record bulk operation
        self.metrics_repository.record_bulk_operation(
            operation_id=operation_id,
            action="bulk_reject",
            failure_count=len(failure_ids),
            total_time_ms=total_time_ms,
            user_id=user_id,
            success_count=success_count,
            failure_count_op=failure_count,
        )
        
        return {
            "success": True,
            "operation_id": operation_id,
            "total": len(failure_ids),
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results,
            "performance": {
                "total_time_ms": total_time_ms,
                "avg_time_per_failure": total_time_ms / len(failure_ids) if failure_ids else 0,
            },
        }
    
    def quick_escalate(
        self,
        failure_ids: List[int],
        reason: str = "Quick escalation",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Quick escalation for complex cases.
        
        Flags multiple failures for developer review in one action.
        
        Args:
            failure_ids: List of failure IDs to escalate
            reason: Reason for escalation
            user_id: User performing escalation
            
        Returns:
            Result dictionary
        """
        start_time = time.time()
        
        operation_id = f"escalate_{uuid.uuid4().hex[:8]}"
        success_count = 0
        failure_count = 0
        results = []
        
        for failure_id in failure_ids:
            # Flag for developer review
            result = self.failure_service.flag_failure(
                failure_id=failure_id,
                note=f"Escalated: {reason}",
                user_id=user_id,
            )
            
            if result.get("success"):
                success_count += 1
                results.append({
                    "failure_id": failure_id,
                    "success": True,
                })
            else:
                failure_count += 1
                results.append({
                    "failure_id": failure_id,
                    "success": False,
                    "message": result.get("message", ""),
                })
        
        # Calculate total time
        total_time_ms = (time.time() - start_time) * 1000
        
        return {
            "success": True,
            "operation_id": operation_id,
            "total": len(failure_ids),
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results,
            "performance": {
                "total_time_ms": total_time_ms,
                "target_met": total_time_ms < 120000,  # < 2 minutes target
            },
        }
    
    def get_performance_summary(
        self,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get performance metrics summary.
        
        Args:
            hours: Time window for metrics
            
        Returns:
            Performance summary
        """
        avg_times = self.metrics_repository.get_average_times(hours=hours)
        
        # Calculate overall metrics
        total_actions = sum(m.get("count", 0) for m in avg_times.values())
        
        avg_total = sum(m.get("avg_total_ms", 0) for m in avg_times.values()) / len(avg_times) if avg_times else 0
        avg_load = sum(m.get("avg_load_ms", 0) for m in avg_times.values()) / len(avg_times) if avg_times else 0
        avg_action = sum(m.get("avg_action_ms", 0) for m in avg_times.values()) / len(avg_times) if avg_times else 0
        
        return {
            "period_hours": hours,
            "total_actions": total_actions,
            "averages": {
                "total_ms": avg_total,
                "load_ms": avg_load,
                "action_ms": avg_action,
            },
            "targets": {
                "page_load_ms": 2000,
                "action_response_ms": 500,
                "triage_workflow_minutes": 5,
            },
            "status": {
                "load_target_met": avg_load < 2000,
                "action_target_met": avg_action < 500,
            },
            "by_action_type": avg_times,
        }


# Singleton instance
_fast_triage_service: Optional[FastTriageService] = None


def get_fast_triage_service() -> FastTriageService:
    """Get the singleton fast triage service instance."""
    global _fast_triage_service
    if _fast_triage_service is None:
        _fast_triage_service = FastTriageService()
    return _fast_triage_service
