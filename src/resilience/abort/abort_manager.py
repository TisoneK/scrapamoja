"""
Abort Manager

Manages abort policies for intelligent failure detection and automatic shutdown
with comprehensive evaluation, decision making, and execution capabilities.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque

from ..interfaces import IResilienceManager
from ..models.abort import (
    AbortPolicy, AbortTrigger, AbortAction, AbortSeverity, AbortStatus,
    AbortCondition, AbortMetrics, AbortDecision,
    DEFAULT_FAILURE_RATE_POLICY, DEFAULT_ERROR_THRESHOLD_POLICY
)
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_abort_event


class AbortManager(IResilienceManager):
    """Manages abort policies and decision making."""
    
    def __init__(self):
        """Initialize abort manager."""
        self.logger = get_logger("abort_manager")
        self.policies: Dict[str, AbortPolicy] = {}
        self.operation_history: deque = deque(maxlen=10000)
        self.error_history: deque = deque(maxlen=1000)
        self.abort_history: List[AbortDecision] = []
        
        # Metrics tracking
        self.metrics = AbortMetrics()
        
        # Callbacks
        self.abort_callbacks: List[Callable[[AbortDecision], None]] = []
        
        # State tracking
        self._initialized = False
        self._evaluation_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Configuration
        self.evaluation_interval = 30  # seconds
        self.max_abort_history = 1000
    
    async def initialize(self) -> None:
        """Initialize the abort manager."""
        if self._initialized:
            return
        
        # Load default policies
        await self._load_default_policies()
        
        # Start evaluation task
        self._running = True
        self._evaluation_task = asyncio.create_task(self._evaluation_loop())
        
        self._initialized = True
        
        self.logger.info(
            "Abort manager initialized",
            event_type="abort_manager_initialized",
            correlation_id=get_correlation_id(),
            context={
                "policies_loaded": len(self.policies),
                "evaluation_interval": self.evaluation_interval
            },
            component="abort_manager"
        )
    
    async def shutdown(self) -> None:
        """Shutdown the abort manager gracefully."""
        if not self._initialized:
            return
        
        self._running = False
        
        if self._evaluation_task:
            self._evaluation_task.cancel()
            try:
                await self._evaluation_task
            except asyncio.CancelledError:
                pass
        
        self._initialized = False
        
        self.logger.info(
            "Abort manager shutdown",
            event_type="abort_manager_shutdown",
            correlation_id=get_correlation_id(),
            component="abort_manager"
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "total_policies": len(self.policies),
            "active_policies": len([p for p in self.policies.values() if p.enabled]),
            "abort_history_size": len(self.abort_history),
            "operation_history_size": len(self.operation_history),
            "evaluation_interval": self.evaluation_interval
        }
    
    async def create_policy(
        self,
        name: str,
        conditions: List[AbortCondition],
        action: AbortAction,
        description: str = "",
        priority: int = 0,
        **kwargs
    ) -> str:
        """
        Create a new abort policy.
        
        Args:
            name: Policy name
            conditions: List of abort conditions
            action: Action to take when triggered
            description: Policy description
            priority: Policy priority (higher = evaluated first)
            **kwargs: Additional policy parameters
            
        Returns:
            Policy ID
        """
        try:
            policy = AbortPolicy(
                name=name,
                description=description,
                conditions=conditions,
                action=action,
                priority=priority,
                **kwargs
            )
            
            self.policies[policy.id] = policy
            
            # Publish event
            await publish_abort_event(
                action="policy_created",
                policy_id=policy.id,
                context={
                    "name": name,
                    "conditions": len(conditions),
                    "action": action.value
                },
                component="abort_manager"
            )
            
            self.logger.info(
                f"Abort policy created: {name}",
                event_type="abort_policy_created",
                correlation_id=get_correlation_id(),
                context={
                    "policy_id": policy.id,
                    "name": name,
                    "conditions": len(conditions)
                },
                component="abort_manager"
            )
            
            return policy.id
            
        except Exception as e:
            self.logger.error(
                f"Failed to create abort policy {name}: {str(e)}",
                event_type="abort_policy_creation_error",
                correlation_id=get_correlation_id(),
                context={
                    "name": name,
                    "error": str(e)
                },
                component="abort_manager"
            )
            raise
    
    async def get_policy(self, policy_id: str) -> Optional[AbortPolicy]:
        """Get a policy by ID."""
        return self.policies.get(policy_id)
    
    async def list_policies(
        self,
        enabled_only: bool = False
    ) -> List[AbortPolicy]:
        """List policies with optional filtering."""
        policies = list(self.policies.values())
        
        if enabled_only:
            policies = [p for p in policies if p.enabled]
        
        # Sort by priority (descending)
        policies.sort(key=lambda p: p.priority, reverse=True)
        
        return policies
    
    async def update_policy(
        self,
        policy_id: str,
        **kwargs
    ) -> bool:
        """Update a policy."""
        policy = self.policies.get(policy_id)
        if not policy:
            return False
        
        try:
            # Update policy fields
            for key, value in kwargs.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            
            policy.updated_at = datetime.utcnow()
            
            self.logger.info(
                f"Abort policy updated: {policy.name}",
                event_type="abort_policy_updated",
                correlation_id=get_correlation_id(),
                context={
                    "policy_id": policy_id,
                    "updates": list(kwargs.keys())
                },
                component="abort_manager"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to update abort policy {policy_id}: {str(e)}",
                event_type="abort_policy_update_error",
                correlation_id=get_correlation_id(),
                context={
                    "policy_id": policy_id,
                    "error": str(e)
                },
                component="abort_manager"
            )
            return False
    
    async def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy."""
        if policy_id not in self.policies:
            return False
        
        policy = self.policies[policy_id]
        
        try:
            del self.policies[policy_id]
            
            # Publish event
            await publish_abort_event(
                action="policy_deleted",
                policy_id=policy_id,
                context={"name": policy.name},
                component="abort_manager"
            )
            
            self.logger.info(
                f"Abort policy deleted: {policy.name}",
                event_type="abort_policy_deleted",
                correlation_id=get_correlation_id(),
                context={
                    "policy_id": policy_id,
                    "name": policy.name
                },
                component="abort_manager"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to delete abort policy {policy_id}: {str(e)}",
                event_type="abort_policy_deletion_error",
                correlation_id=get_correlation_id(),
                context={
                    "policy_id": policy_id,
                    "error": str(e)
                },
                component="abort_manager"
            )
            return False
    
    async def record_operation(
        self,
        operation_id: str,
        success: bool,
        error_type: Optional[str] = None,
        response_time: float = 0.0,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record an operation for abort evaluation.
        
        Args:
            operation_id: Operation identifier
            success: Whether operation was successful
            error_type: Type of error if failed
            response_time: Operation response time
            context: Additional context
        """
        operation = {
            "id": operation_id,
            "timestamp": datetime.utcnow(),
            "success": success,
            "error_type": error_type,
            "response_time": response_time,
            "context": context or {}
        }
        
        self.operation_history.append(operation)
        
        # Update metrics
        self.metrics.total_operations += 1
        if not success:
            self.metrics.failed_operations += 1
            self.metrics.last_failure_time = datetime.utcnow()
            self.metrics.consecutive_failures += 1
        else:
            self.metrics.consecutive_failures = 0
        
        if error_type:
            self.metrics.error_count += 1
            self.error_history.append({
                "timestamp": datetime.utcnow(),
                "error_type": error_type,
                "operation_id": operation_id
            })
        
        # Calculate rates
        self._update_metrics()
        
        # Trigger immediate evaluation if this was a failure
        if not success:
            await self._evaluate_policies()
    
    async def trigger_abort(
        self,
        policy_id: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Manually trigger an abort for a policy.
        
        Args:
            policy_id: Policy identifier
            reason: Reason for manual abort
            context: Additional context
            
        Returns:
            True if abort was triggered successfully
        """
        policy = self.policies.get(policy_id)
        if not policy or not policy.enabled:
            return False
        
        try:
            # Create abort decision
            decision = AbortDecision(
                policy_id=policy_id,
                triggered=True,
                action=policy.action,
                severity=AbortSeverity.HIGH,
                reason=f"Manual abort: {reason}",
                metrics=self.metrics,
                context=context or {}
            )
            
            # Execute abort action
            await self._execute_abort_action(policy, decision)
            
            # Record decision
            self._record_abort_decision(decision)
            
            # Publish event
            await publish_abort_event(
                action="triggered",
                policy_id=policy_id,
                context={
                    "reason": reason,
                    "action": policy.action.value
                },
                component="abort_manager"
            )
            
            self.logger.warning(
                f"Manual abort triggered: {policy.name} - {reason}",
                event_type="manual_abort_triggered",
                correlation_id=get_correlation_id(),
                context={
                    "policy_id": policy_id,
                    "name": policy.name,
                    "reason": reason
                },
                component="abort_manager"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to trigger manual abort for policy {policy_id}: {str(e)}",
                event_type="manual_abort_error",
                correlation_id=get_correlation_id(),
                context={
                    "policy_id": policy_id,
                    "reason": reason,
                    "error": str(e)
                },
                component="abort_manager"
            )
            return False
    
    async def get_abort_history(
        self,
        limit: Optional[int] = None
    ) -> List[AbortDecision]:
        """Get abort history."""
        history = self.abort_history.copy()
        
        if limit:
            history = history[-limit:]
        
        return history
    
    async def get_metrics(self) -> AbortMetrics:
        """Get current abort metrics."""
        self._update_metrics()
        return self.metrics
    
    def add_abort_callback(self, callback: Callable[[AbortDecision], None]) -> None:
        """Add an abort decision callback."""
        self.abort_callbacks.append(callback)
    
    def remove_abort_callback(self, callback: Callable) -> bool:
        """Remove an abort decision callback."""
        if callback in self.abort_callbacks:
            self.abort_callbacks.remove(callback)
            return True
        return False
    
    async def _load_default_policies(self) -> None:
        """Load default abort policies."""
        default_policies = [
            DEFAULT_FAILURE_RATE_POLICY,
            DEFAULT_ERROR_THRESHOLD_POLICY
        ]
        
        for policy in default_policies:
            self.policies[policy.id] = policy
        
        self.logger.info(
            f"Loaded {len(default_policies)} default abort policies",
            event_type="default_policies_loaded",
            correlation_id=get_correlation_id(),
            context={"count": len(default_policies)},
            component="abort_manager"
        )
    
    async def _evaluation_loop(self) -> None:
        """Main evaluation loop."""
        while self._running:
            try:
                await self._evaluate_policies()
                await asyncio.sleep(self.evaluation_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error in abort evaluation loop: {str(e)}",
                    event_type="abort_evaluation_loop_error",
                    correlation_id=get_correlation_id(),
                    context={"error": str(e)},
                    component="abort_manager"
                )
                await asyncio.sleep(self.evaluation_interval)
    
    async def _evaluate_policies(self) -> None:
        """Evaluate all active policies."""
        # Get active policies sorted by priority
        active_policies = [
            p for p in self.policies.values()
            if p.enabled and p.status == AbortStatus.ACTIVE
        ]
        active_policies.sort(key=lambda p: p.priority, reverse=True)
        
        for policy in active_policies:
            try:
                decision = await self._evaluate_policy(policy)
                
                if decision.triggered:
                    await self._handle_abort_decision(policy, decision)
                    break  # Stop after first triggered policy (highest priority)
                    
            except Exception as e:
                self.logger.error(
                    f"Error evaluating policy {policy.name}: {str(e)}",
                    event_type="policy_evaluation_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "policy_id": policy.id,
                        "name": policy.name,
                        "error": str(e)
                    },
                    component="abort_manager"
                )
    
    async def _evaluate_policy(self, policy: AbortPolicy) -> AbortDecision:
        """Evaluate a single policy."""
        triggered_conditions = []
        
        for condition in policy.conditions:
            if await self._evaluate_condition(condition):
                triggered_conditions.append(condition)
        
        triggered = len(triggered_conditions) > 0
        
        # Determine severity
        severity = AbortSeverity.LOW
        if triggered_conditions:
            severity = max(c.severity for c in triggered_conditions)
        
        # Create decision
        decision = AbortDecision(
            policy_id=policy.id,
            triggered=triggered,
            condition=triggered_conditions[0] if triggered_conditions else None,
            action=policy.action if triggered else None,
            severity=severity,
            reason=f"Conditions triggered: {len(triggered_conditions)}" if triggered else "No conditions triggered",
            metrics=self.metrics,
            context={
                "triggered_conditions": len(triggered_conditions),
                "policy_name": policy.name
            }
        )
        
        return decision
    
    async def _evaluate_condition(self, condition: AbortCondition) -> bool:
        """Evaluate a single abort condition."""
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=condition.time_window_seconds)
        
        if condition.trigger_type == AbortTrigger.FAILURE_RATE:
            return await self._evaluate_failure_rate(condition, cutoff_time)
        elif condition.trigger_type == AbortTrigger.ERROR_THRESHOLD:
            return await self._evaluate_error_threshold(condition, cutoff_time)
        elif condition.trigger_type == AbortTrigger.TIMEOUT:
            return await self._evaluate_timeout(condition, cutoff_time)
        elif condition.trigger_type == AbortTrigger.RESOURCE_EXHAUSTION:
            return await self._evaluate_resource_exhaustion(condition)
        elif condition.trigger_type == AbortTrigger.CRITICAL_ERROR:
            return await self._evaluate_critical_error(condition, cutoff_time)
        else:
            return False
    
    async def _evaluate_failure_rate(
        self,
        condition: AbortCondition,
        cutoff_time: datetime
    ) -> bool:
        """Evaluate failure rate condition."""
        # Count operations in time window
        recent_operations = [
            op for op in self.operation_history
            if op["timestamp"] >= cutoff_time
        ]
        
        if not recent_operations:
            return False
        
        failed_operations = [
            op for op in recent_operations
            if not op["success"]
        ]
        
        failure_rate = len(failed_operations) / len(recent_operations)
        
        return failure_rate >= condition.threshold
    
    async def _evaluate_error_threshold(
        self,
        condition: AbortCondition,
        cutoff_time: datetime
    ) -> bool:
        """Evaluate error threshold condition."""
        recent_errors = [
            error for error in self.error_history
            if error["timestamp"] >= cutoff_time
        ]
        
        return len(recent_errors) >= condition.threshold
    
    async def _evaluate_timeout(
        self,
        condition: AbortCondition,
        cutoff_time: datetime
    ) -> bool:
        """Evaluate timeout condition."""
        recent_operations = [
            op for op in self.operation_history
            if op["timestamp"] >= cutoff_time and op.get("response_time", 0) > 0
        ]
        
        if not recent_operations:
            return False
        
        timeouts = [
            op for op in recent_operations
            if op["response_time"] > condition.threshold
        ]
        
        return len(timeouts) >= condition.threshold
    
    async def _evaluate_resource_exhaustion(self, condition: AbortCondition) -> bool:
        """Evaluate resource exhaustion condition."""
        # This would integrate with resource manager
        # For now, return False (placeholder)
        return False
    
    async def _evaluate_critical_error(
        self,
        condition: AbortCondition,
        cutoff_time: datetime
    ) -> bool:
        """Evaluate critical error condition."""
        critical_errors = [
            error for error in self.error_history
            if error["timestamp"] >= cutoff_time and error["error_type"] == "critical"
        ]
        
        return len(critical_errors) >= condition.threshold
    
    async def _handle_abort_decision(
        self,
        policy: AbortPolicy,
        decision: AbortDecision
    ) -> None:
        """Handle an abort decision."""
        # Check cooldown
        if policy.last_triggered:
            time_since_abort = (datetime.utcnow() - policy.last_triggered).total_seconds()
            if time_since_abort < policy.cooldown_seconds:
                self.logger.info(
                    f"Abort policy {policy.name} in cooldown, skipping",
                    event_type="abort_policy_cooldown",
                    correlation_id=get_correlation_id(),
                    context={
                        "policy_id": policy.id,
                        "name": policy.name,
                        "time_since_abort": time_since_abort,
                        "cooldown_seconds": policy.cooldown_seconds
                    },
                    component="abort_manager"
                )
                return
        
        # Check abort limit
        if policy.abort_count >= policy.max_aborts_per_hour:
            self.logger.warning(
                f"Abort policy {policy.name} exceeded hourly limit",
                event_type="abort_policy_limit_exceeded",
                correlation_id=get_correlation_id(),
                context={
                    "policy_id": policy.id,
                    "name": policy.name,
                    "abort_count": policy.abort_count,
                    "max_aborts_per_hour": policy.max_aborts_per_hour
                },
                component="abort_manager"
            )
            return
        
        # Execute abort action
        await self._execute_abort_action(policy, decision)
        
        # Update policy state
        policy.last_triggered = datetime.utcnow()
        policy.abort_count += 1
        policy.status = AbortStatus.TRIGGERED
        
        # Record decision
        self._record_abort_decision(decision)
        
        # Publish event
        await publish_abort_event(
            action="triggered",
            policy_id=policy.id,
            context={
                "reason": decision.reason,
                "action": decision.action.value if decision.action else None,
                "severity": decision.severity.value
            },
            component="abort_manager"
        )
        
        self.logger.warning(
            f"Abort triggered: {policy.name} - {decision.reason}",
            event_type="abort_triggered",
            correlation_id=get_correlation_id(),
            context={
                "policy_id": policy.id,
                "name": policy.name,
                "reason": decision.reason,
                "action": decision.action.value if decision.action else None
            },
            component="abort_manager"
        )
    
    async def _execute_abort_action(
        self,
        policy: AbortPolicy,
        decision: AbortDecision
    ) -> None:
        """Execute the abort action."""
        if not decision.action:
            return
        
        if decision.action == AbortAction.STOP_IMMEDIATELY:
            await self._stop_immediately(decision)
        elif decision.action == AbortAction.GRACEFUL_SHUTDOWN:
            await self._graceful_shutdown(decision)
        elif decision.action == AbortAction.SAVE_STATE_AND_STOP:
            await self._save_state_and_stop(decision)
        elif decision.action == AbortAction.ROLLBACK:
            await self._rollback(decision)
        
        # Notify callbacks
        self._notify_abort_callbacks(decision)
    
    async def _stop_immediately(self, decision: AbortDecision) -> None:
        """Stop immediately."""
        # This would implement immediate stop logic
        pass
    
    async def _graceful_shutdown(self, decision: AbortDecision) -> None:
        """Perform graceful shutdown."""
        # This would implement graceful shutdown logic
        pass
    
    async def _save_state_and_stop(self, decision: AbortDecision) -> None:
        """Save state and stop."""
        # This would implement state saving and stop logic
        pass
    
    async def _rollback(self, decision: AbortDecision) -> None:
        """Rollback changes."""
        # This would implement rollback logic
        pass
    
    def _record_abort_decision(self, decision: AbortDecision) -> None:
        """Record an abort decision."""
        self.abort_history.append(decision)
        
        # Limit history size
        if len(self.abort_history) > self.max_abort_history:
            self.abort_history = self.abort_history[-self.max_abort_history:]
    
    def _notify_abort_callbacks(self, decision: AbortDecision) -> None:
        """Notify all abort callbacks."""
        for callback in self.abort_callbacks:
            try:
                callback(decision)
            except Exception as e:
                self.logger.error(
                    f"Error in abort callback: {str(e)}",
                    event_type="abort_callback_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "policy_id": decision.policy_id,
                        "error": str(e)
                    },
                    component="abort_manager"
                )
    
    def _update_metrics(self) -> None:
        """Update current metrics."""
        if self.metrics.total_operations > 0:
            self.metrics.failure_rate = self.metrics.failed_operations / self.metrics.total_operations
        
        # Calculate error rate
        recent_time = datetime.utcnow() - timedelta(minutes=5)
        recent_operations = [
            op for op in self.operation_history
            if op["timestamp"] >= recent_time
        ]
        
        if recent_operations:
            recent_errors = len([
                op for op in recent_operations
                if not op["success"]
            ])
            self.metrics.error_rate = recent_errors / len(recent_operations)


# Global abort manager instance
_abort_manager = AbortManager()


def get_abort_manager() -> AbortManager:
    """Get the global abort manager instance."""
    return _abort_manager


async def create_abort_policy(
    name: str,
    conditions: List[AbortCondition],
    action: AbortAction,
    description: str = "",
    priority: int = 0
) -> str:
    """Create an abort policy using the global manager."""
    return await _abort_manager.create_policy(name, conditions, action, description, priority)


async def record_operation(
    operation_id: str,
    success: bool,
    error_type: Optional[str] = None,
    response_time: float = 0.0,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Record an operation using the global manager."""
    await _abort_manager.record_operation(operation_id, success, error_type, response_time, context)
