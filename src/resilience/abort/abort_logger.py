"""
Abort Event Logging

Specialized logging for abort operations with detailed context,
correlation tracking, and structured output for debugging and analysis.
"""

import json
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..correlation import get_correlation_id
from ..models.abort import (
    AbortPolicy, AbortDecision, AbortAction, AbortTrigger, AbortSeverity,
    ExecutionResult, RollbackInfo
)
from .resilience_logger import ResilienceLogger


class AbortLogger:
    """Specialized logger for abort operations with enhanced context tracking."""
    
    def __init__(self, name: str = "abort_logger"):
        """Initialize abort logger."""
        self.logger = ResilienceLogger(name)
    
    def log_policy_created(
        self,
        policy: AbortPolicy,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log abort policy creation with comprehensive context."""
        context = {
            "policy_id": policy.id,
            "name": policy.name,
            "description": policy.description,
            "status": policy.status.value,
            "conditions": [c.to_dict() for c in policy.conditions],
            "action": policy.action.value,
            "enabled": policy.enabled,
            "priority": policy.priority,
            "cooldown_seconds": policy.cooldown_seconds,
            "max_aborts_per_hour": policy.max_aborts_per_hour,
            "tags": policy.tags,
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Abort policy created: {policy.name}",
            event_type="abort_policy_created",
            correlation_id=get_correlation_id(),
            context=context,
            component="abort_manager"
        )
    
    def log_policy_triggered(
        self,
        policy: AbortPolicy,
        decision: AbortDecision,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log abort policy trigger with decision details."""
        context = {
            "policy_id": policy.id,
            "name": policy.name,
            "decision": decision.to_dict(),
            "abort_count": policy.abort_count,
            "last_triggered": policy.last_triggered.isoformat() if policy.last_triggered else None,
            **(additional_context or {})
        }
        
        self.logger.warning(
            f"Abort policy triggered: {policy.name} - {decision.reason}",
            event_type="abort_policy_triggered",
            correlation_id=get_correlation_id(),
            context=context,
            component="abort_manager"
        )
    
    def log_action_executed(
        self,
        policy: AbortPolicy,
        result: ExecutionResult,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log abort action execution with performance metrics."""
        context = {
            "policy_id": policy.id,
            "name": policy.name,
            "action": result.action.value,
            "success": result.success,
            "execution_time": result.execution_time,
            "error_message": result.error_message,
            "details": result.details,
            "timestamp": result.timestamp.isoformat(),
            **(additional_context or {})
        }
        
        log_level = "info" if result.success else "error"
        
        getattr(self.logger, log_level)(
            f"Abort action executed: {result.action.value} for policy {policy.name} "
            f"({'success' if result.success else 'failed'}, {result.execution_time:.3f}s)",
            event_type="abort_action_executed",
            correlation_id=get_correlation_id(),
            context=context,
            component="abort_executor"
        )
    
    def log_action_rolled_back(
        self,
        policy: AbortPolicy,
        rollback_info: RollbackInfo,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log abort action rollback with recovery details."""
        context = {
            "policy_id": policy.id,
            "name": policy.name,
            "original_action": rollback_info.original_action.value,
            "rollback_action": rollback_info.rollback_action,
            "rollback_success": rollback_info.success,
            "rollback_time": rollback_info.rollback_time,
            "error_message": rollback_info.error_message,
            "timestamp": rollback_info.timestamp.isoformat(),
            **(additional_context or {})
        }
        
        log_level = "info" if rollback_info.success else "error"
        
        getattr(self.logger, log_level)(
            f"Abort action rolled back: {rollback_info.original_action.value} for policy {policy.name} "
            f"({'success' if rollback_info.success else 'failed'}, {rollback_info.rollback_time:.3f}s)",
            event_type="abort_action_rolled_back",
            correlation_id=get_correlation_id(),
            context=context,
            component="abort_executor"
        )
    
    def log_failure_analysis_completed(
        self,
        analysis: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log failure analysis completion with insights."""
        context = {
            "analysis": analysis,
            "total_failures": analysis.get("total_failures", 0),
            "failure_rate": analysis.get("failure_rate", 0.0),
            "patterns_found": len(analysis.get("failure_patterns", [])),
            "critical_failures": len(analysis.get("critical_failures", [])),
            "recommendations": analysis.get("recommendations", []),
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Failure analysis completed: {analysis.get('total_failures', 0)} failures, "
            f"{analysis.get('failure_rate', 0.0):.2%} rate, "
            f"{len(analysis.get('failure_patterns', []))} patterns",
            event_type="failure_analysis_completed",
            correlation_id=get_correlation_id(),
            context=context,
            component="failure_analyzer"
        )
    
    def log_manual_abort_triggered(
        self,
        policy: AbortPolicy,
        reason: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log manual abort trigger with context."""
        context = {
            "policy_id": policy.id,
            "name": policy.name,
            "reason": reason,
            "trigger_type": "manual",
            **(additional_context or {})
        }
        
        self.logger.warning(
            f"Manual abort triggered: {policy.name} - {reason}",
            event_type="manual_abort_triggered",
            correlation_id=get_correlation_id(),
            context=context,
            component="abort_manager"
        )
    
    def log_policy_cooldown(
        self,
        policy: AbortPolicy,
        time_since_abort: float,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log policy cooldown activation."""
        context = {
            "policy_id": policy.id,
            "name": policy.name,
            "time_since_abort": time_since_abort,
            "cooldown_seconds": policy.cooldown_seconds,
            "remaining_cooldown": max(0, policy.cooldown_seconds - time_since_abort),
            **(additional_context or {})
        }
        
        self.logger.info(
            f"Abort policy in cooldown: {policy.name} "
            f"({time_since_abort:.1f}s since last abort, {policy.cooldown_seconds}s cooldown)",
            event_type="abort_policy_cooldown",
            correlation_id=get_correlation_id(),
            context=context,
            component="abort_manager"
        )
    
    def log_policy_limit_exceeded(
        self,
        policy: AbortPolicy,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log policy abort limit exceeded."""
        context = {
            "policy_id": policy.id,
            "name": policy.name,
            "abort_count": policy.abort_count,
            "max_aborts_per_hour": policy.max_aborts_per_hour,
            **(additional_context or {})
        }
        
        self.logger.warning(
            f"Abort policy limit exceeded: {policy.name} "
            f"({policy.abort_count}/{policy.max_aborts_per_hour} aborts per hour)",
            event_type="abort_policy_limit_exceeded",
            correlation_id=get_correlation_id(),
            context=context,
            component="abort_manager"
        )
    
    def log_condition_evaluated(
        self,
        policy: AbortPolicy,
        condition: Dict[str, Any],
        triggered: bool,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log individual condition evaluation."""
        context = {
            "policy_id": policy.id,
            "name": policy.name,
            "condition": condition,
            "triggered": triggered,
            **(additional_context or {})
        }
        
        self.logger.debug(
            f"Abort condition evaluated: {policy.name} - "
            f"{condition.get('trigger_type', 'unknown')} ({'triggered' if triggered else 'not triggered'})",
            event_type="abort_condition_evaluated",
            correlation_id=get_correlation_id(),
            context=context,
            component="abort_manager"
        )
    
    def create_abort_report(
        self,
        policies: List[Dict[str, Any]],
        executions: List[Dict[str, Any]],
        rollbacks: List[Dict[str, Any]],
        report_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a comprehensive abort report."""
        if not policies:
            return {
                "report_timestamp": datetime.utcnow().isoformat(),
                "total_policies": 0,
                "context": report_context or {}
            }
        
        # Calculate statistics
        total_policies = len(policies)
        active_policies = len([p for p in policies if p.get("enabled", False)])
        triggered_policies = len([p for p in policies if p.get("status") == "triggered"])
        
        # Execution statistics
        total_executions = len(executions)
        successful_executions = len([e for e in executions if e.get("success", False)])
        failed_executions = total_executions - successful_executions
        
        # Rollback statistics
        total_rollbacks = len(rollbacks)
        successful_rollbacks = len([r for r in rollbacks if r.get("success", False)])
        
        # Action distribution
        action_counts = {}
        for execution in executions:
            action = execution.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
        
        report = {
            "report_timestamp": datetime.utcnow().isoformat(),
            "policy_statistics": {
                "total_policies": total_policies,
                "active_policies": active_policies,
                "triggered_policies": triggered_policies,
                "inactive_policies": total_policies - active_policies
            },
            "execution_statistics": {
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "failed_executions": failed_executions,
                "success_rate": (successful_executions / total_executions) if total_executions > 0 else 0.0,
                "average_execution_time": sum(e.get("execution_time", 0) for e in executions) / total_executions if total_executions > 0 else 0.0
            },
            "rollback_statistics": {
                "total_rollbacks": total_rollbacks,
                "successful_rollbacks": successful_rollbacks,
                "failed_rollbacks": total_rollbacks - successful_rollbacks,
                "success_rate": (successful_rollbacks / total_rollbacks) if total_rollbacks > 0 else 0.0
            },
            "action_distribution": action_counts,
            "context": report_context or {},
            "policy_details": policies,
            "execution_details": executions,
            "rollback_details": rollbacks
        }
        
        return report


# Global abort logger instance
_abort_logger = AbortLogger()


def get_abort_logger() -> AbortLogger:
    """Get the global abort logger instance."""
    return _abort_logger


def log_policy_created(
    policy: AbortPolicy,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log policy creation using the global logger."""
    _abort_logger.log_policy_created(policy, additional_context)


def log_policy_triggered(
    policy: AbortPolicy,
    decision: AbortDecision,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log policy trigger using the global logger."""
    _abort_logger.log_policy_triggered(policy, decision, additional_context)


def log_action_executed(
    policy: AbortPolicy,
    result: ExecutionResult,
    additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Log action execution using the global logger."""
    _abort_logger.log_action_executed(policy, result, additional_context)
