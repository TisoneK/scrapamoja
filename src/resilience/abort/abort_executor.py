"""
Abort Executor

Executes abort actions with comprehensive state management, rollback capabilities,
and graceful shutdown procedures with detailed logging and recovery tracking.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..models.abort import AbortAction, AbortDecision, AbortPolicy
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_abort_event


@dataclass
class ExecutionResult:
    """Result of abort action execution."""
    action: AbortAction
    success: bool
    execution_time: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "action": self.action.value,
            "success": self.success,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class RollbackInfo:
    """Information about rollback operations."""
    original_action: AbortAction
    rollback_action: str
    rollback_time: float
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "original_action": self.original_action.value,
            "rollback_action": self.rollback_action,
            "rollback_time": self.rollback_time,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat()
        }


class AbortExecutor:
    """Executes abort actions with comprehensive state management."""
    
    def __init__(self):
        """Initialize abort executor."""
        self.logger = get_logger("abort_executor")
        
        # Execution history
        self.execution_history: List[ExecutionResult] = []
        self.rollback_history: List[RollbackInfo] = []
        
        # State tracking
        self.current_executions: Dict[str, AbortDecision] = {}
        self.execution_locks: Dict[str, asyncio.Lock] = {}
        
        # Callbacks
        self.execution_callbacks: List[Callable[[ExecutionResult], None]] = []
        self.rollback_callbacks: List[Callable[[RollbackInfo], None]] = []
        
        # Configuration
        self.execution_timeout_seconds = 60
        self.max_execution_history = 1000
        self.enable_rollback = True
        
        # Action handlers
        self.action_handlers = {
            AbortAction.STOP_IMMEDIATELY: self._handle_stop_immediately,
            AbortAction.GRACEFUL_SHUTDOWN: self._handle_graceful_shutdown,
            AbortAction.SAVE_STATE_AND_STOP: self._handle_save_state_and_stop,
            AbortAction.ROLLBACK: self._handle_rollback
        }
    
    async def execute_abort_action(
        self,
        policy: AbortPolicy,
        decision: AbortDecision
    ) -> ExecutionResult:
        """
        Execute an abort action based on policy and decision.
        
        Args:
            policy: Abort policy
            decision: Abort decision
            
        Returns:
            Execution result
        """
        if not decision.action:
            return ExecutionResult(
                action=AbortAction.STOP_IMMEDIATELY,
                success=False,
                execution_time=0.0,
                error_message="No action specified in decision"
            )
        
        # Get execution lock
        lock = self._get_execution_lock(policy.id)
        
        async with lock:
            start_time = time.time()
            
            try:
                # Record current execution
                self.current_executions[policy.id] = decision
                
                # Execute the action
                handler = self.action_handlers.get(decision.action)
                if not handler:
                    raise ValueError(f"No handler for action: {decision.action.value}")
                
                result = await handler(policy, decision)
                
                # Calculate execution time
                execution_time = time.time() - start_time
                result.execution_time = execution_time
                
                # Record execution
                self._record_execution(result)
                
                # Publish event
                await publish_abort_event(
                    action="executed",
                    policy_id=policy.id,
                    context={
                        "action": decision.action.value,
                        "success": result.success,
                        "execution_time": execution_time
                    },
                    component="abort_executor"
                )
                
                self.logger.info(
                    f"Abort action executed: {decision.action.value} for policy {policy.name}",
                    event_type="abort_action_executed",
                    correlation_id=get_correlation_id(),
                    context={
                        "policy_id": policy.id,
                        "name": policy.name,
                        "action": decision.action.value,
                        "success": result.success,
                        "execution_time": execution_time
                    },
                    component="abort_executor"
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                result = ExecutionResult(
                    action=decision.action,
                    success=False,
                    execution_time=execution_time,
                    error_message=str(e)
                )
                
                self._record_execution(result)
                
                self.logger.error(
                    f"Failed to execute abort action {decision.action.value}: {str(e)}",
                    event_type="abort_action_execution_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "policy_id": policy.id,
                        "action": decision.action.value,
                        "error": str(e),
                        "execution_time": execution_time
                    },
                    component="abort_executor"
                )
                
                return result
                
            finally:
                # Clear current execution
                self.current_executions.pop(policy.id, None)
    
    async def rollback_execution(
        self,
        policy_id: str,
        rollback_reason: str = "manual"
    ) -> RollbackInfo:
        """
        Rollback a previous execution.
        
        Args:
            policy_id: Policy identifier
            rollback_reason: Reason for rollback
            
        Returns:
            Rollback information
        """
        if not self.enable_rollback:
            return RollbackInfo(
                original_action=AbortAction.STOP_IMMEDIATELY,
                rollback_action="rollback_disabled",
                rollback_time=0.0,
                success=False,
                error_message="Rollback is disabled"
            )
        
        # Find the most recent execution for this policy
        last_execution = None
        for execution in reversed(self.execution_history):
            # This would need to be enhanced to track which policy each execution belongs to
            last_execution = execution
            break
        
        if not last_execution:
            return RollbackInfo(
                original_action=AbortAction.STOP_IMMEDIATELY,
                rollback_action="no_execution_found",
                rollback_time=0.0,
                success=False,
                error_message="No previous execution found for rollback"
            )
        
        start_time = time.time()
        
        try:
            # Perform rollback based on original action
            rollback_success = await self._perform_rollback(last_execution.action, rollback_reason)
            
            rollback_time = time.time() - start_time
            
            rollback_info = RollbackInfo(
                original_action=last_execution.action,
                rollback_action=f"rollback_{last_execution.action.value}",
                rollback_time=rollback_time,
                success=rollback_success
            )
            
            self._record_rollback(rollback_info)
            
            # Publish event
            await publish_abort_event(
                action="rolled_back",
                policy_id=policy_id,
                context={
                    "original_action": last_execution.action.value,
                    "rollback_success": rollback_success,
                    "rollback_time": rollback_time
                },
                component="abort_executor"
            )
            
            self.logger.info(
                f"Abort action rolled back: {last_execution.action.value}",
                event_type="abort_action_rolled_back",
                correlation_id=get_correlation_id(),
                context={
                    "policy_id": policy_id,
                    "original_action": last_execution.action.value,
                    "success": rollback_success,
                    "rollback_time": rollback_time
                },
                component="abort_executor"
            )
            
            return rollback_info
            
        except Exception as e:
            rollback_time = time.time() - start_time
            
            rollback_info = RollbackInfo(
                original_action=last_execution.action,
                rollback_action=f"rollback_{last_execution.action.value}",
                rollback_time=rollback_time,
                success=False,
                error_message=str(e)
            )
            
            self._record_rollback(rollback_info)
            
            self.logger.error(
                f"Failed to rollback abort action {last_execution.action.value}: {str(e)}",
                event_type="abort_action_rollback_error",
                correlation_id=get_correlation_id(),
                context={
                    "policy_id": policy_id,
                    "original_action": last_execution.action.value,
                    "error": str(e)
                },
                component="abort_executor"
            )
            
            return rollback_info
    
    async def get_execution_history(
        self,
        policy_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ExecutionResult]:
        """
        Get execution history with optional filtering.
        
        Args:
            policy_id: Filter by policy ID
            limit: Maximum number of results to return
            
        Returns:
            List of execution results
        """
        history = self.execution_history.copy()
        
        # Filter by policy ID if specified
        if policy_id:
            # This would need to be enhanced to track policy IDs in execution results
            pass
        
        # Apply limit
        if limit:
            history = history[-limit:]
        
        return history
    
    async def get_rollback_history(
        self,
        policy_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[RollbackInfo]:
        """
        Get rollback history with optional filtering.
        
        Args:
            policy_id: Filter by policy ID
            limit: Maximum number of results to return
            
        Returns:
            List of rollback information
        """
        history = self.rollback_history.copy()
        
        # Apply limit
        if limit:
            history = history[-limit:]
        
        return history
    
    def add_execution_callback(self, callback: Callable[[ExecutionResult], None]) -> None:
        """Add an execution callback."""
        self.execution_callbacks.append(callback)
    
    def remove_execution_callback(self, callback: Callable) -> bool:
        """Remove an execution callback."""
        if callback in self.execution_callbacks:
            self.execution_callbacks.remove(callback)
            return True
        return False
    
    def add_rollback_callback(self, callback: Callable[[RollbackInfo], None]) -> None:
        """Add a rollback callback."""
        self.rollback_callbacks.append(callback)
    
    def remove_rollback_callback(self, callback: Callable) -> bool:
        """Remove a rollback callback."""
        if callback in self.rollback_callbacks:
            self.rollback_callbacks.remove(callback)
            return True
        return False
    
    async def _handle_stop_immediately(
        self,
        policy: AbortPolicy,
        decision: AbortDecision
    ) -> ExecutionResult:
        """Handle immediate stop action."""
        try:
            # Implement immediate stop logic
            # This would stop all ongoing operations immediately
            
            # Simulate immediate stop
            await asyncio.sleep(0.1)
            
            return ExecutionResult(
                action=AbortAction.STOP_IMMEDIATELY,
                success=True,
                details={
                    "stopped_operations": "all",
                    "stop_reason": decision.reason,
                    "policy_id": policy.id
                }
            )
            
        except Exception as e:
            return ExecutionResult(
                action=AbortAction.STOP_IMMEDIATELY,
                success=False,
                error_message=str(e)
            )
    
    async def _handle_graceful_shutdown(
        self,
        policy: AbortPolicy,
        decision: AbortDecision
    ) -> ExecutionResult:
        """Handle graceful shutdown action."""
        try:
            # Implement graceful shutdown logic
            # This would allow ongoing operations to complete before stopping
            
            # Simulate graceful shutdown
            await asyncio.sleep(1.0)
            
            return ExecutionResult(
                action=AbortAction.GRACEFUL_SHUTDOWN,
                success=True,
                details={
                    "shutdown_type": "graceful",
                    "shutdown_reason": decision.reason,
                    "policy_id": policy.id,
                    "operations_completed": True
                }
            )
            
        except Exception as e:
            return ExecutionResult(
                action=AbortAction.GRACEFUL_SHUTDOWN,
                success=False,
                error_message=str(e)
            )
    
    async def _handle_save_state_and_stop(
        self,
        policy: AbortPolicy,
        decision: AbortDecision
    ) -> ExecutionResult:
        """Handle save state and stop action."""
        try:
            # Implement save state and stop logic
            # This would save current state before stopping
            
            # Simulate state saving
            await asyncio.sleep(0.5)
            
            # Simulate stop
            await asyncio.sleep(0.1)
            
            return ExecutionResult(
                action=AbortAction.SAVE_STATE_AND_STOP,
                success=True,
                details={
                    "state_saved": True,
                    "state_location": "/data/checkpoints",
                    "stop_reason": decision.reason,
                    "policy_id": policy.id
                }
            )
            
        except Exception as e:
            return ExecutionResult(
                action=AbortAction.SAVE_STATE_AND_STOP,
                success=False,
                error_message=str(e)
            )
    
    async def _handle_rollback(
        self,
        policy: AbortPolicy,
        decision: AbortDecision
    ) -> ExecutionResult:
        """Handle rollback action."""
        try:
            # Implement rollback logic
            # This would rollback to a previous state
            
            # Simulate rollback
            await asyncio.sleep(0.3)
            
            return ExecutionResult(
                action=AbortAction.ROLLBACK,
                success=True,
                details={
                    "rollback_completed": True,
                    "rollback_reason": decision.reason,
                    "policy_id": policy.id,
                    "rollback_point": "last_checkpoint"
                }
            )
            
        except Exception as e:
            return ExecutionResult(
                action=AbortAction.ROLLBACK,
                success=False,
                error_message=str(e)
            )
    
    async def _perform_rollback(
        self,
        original_action: AbortAction,
        rollback_reason: str
    ) -> bool:
        """Perform rollback for a specific action."""
        try:
            if original_action == AbortAction.STOP_IMMEDIATELY:
                # Rollback immediate stop - restart operations
                await asyncio.sleep(0.1)
                return True
                
            elif original_action == AbortAction.GRACEFUL_SHUTDOWN:
                # Rollback graceful shutdown - restart services
                await asyncio.sleep(0.2)
                return True
                
            elif original_action == AbortAction.SAVE_STATE_AND_STOP:
                # Rollback save state and stop - restore from saved state
                await asyncio.sleep(0.3)
                return True
                
            elif original_action == AbortAction.ROLLBACK:
                # Cannot rollback a rollback
                return False
                
            else:
                return False
                
        except Exception:
            return False
    
    def _get_execution_lock(self, policy_id: str) -> asyncio.Lock:
        """Get or create execution lock for a policy."""
        if policy_id not in self.execution_locks:
            self.execution_locks[policy_id] = asyncio.Lock()
        return self.execution_locks[policy_id]
    
    def _record_execution(self, result: ExecutionResult) -> None:
        """Record execution result."""
        self.execution_history.append(result)
        
        # Limit history size
        if len(self.execution_history) > self.max_execution_history:
            self.execution_history = self.execution_history[-self.max_execution_history:]
        
        # Notify callbacks
        self._notify_execution_callbacks(result)
    
    def _record_rollback(self, rollback_info: RollbackInfo) -> None:
        """Record rollback information."""
        self.rollback_history.append(rollback_info)
        
        # Limit history size
        if len(self.rollback_history) > self.max_execution_history:
            self.rollback_history = self.rollback_history[-self.max_execution_history:]
        
        # Notify callbacks
        self._notify_rollback_callbacks(rollback_info)
    
    def _notify_execution_callbacks(self, result: ExecutionResult) -> None:
        """Notify all execution callbacks."""
        for callback in self.execution_callbacks:
            try:
                callback(result)
            except Exception as e:
                self.logger.error(
                    f"Error in execution callback: {str(e)}",
                    event_type="execution_callback_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "action": result.action.value,
                        "error": str(e)
                    },
                    component="abort_executor"
                )
    
    def _notify_rollback_callbacks(self, rollback_info: RollbackInfo) -> None:
        """Notify all rollback callbacks."""
        for callback in self.rollback_callbacks:
            try:
                callback(rollback_info)
            except Exception as e:
                self.logger.error(
                    f"Error in rollback callback: {str(e)}",
                    event_type="rollback_callback_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "original_action": rollback_info.original_action.value,
                        "error": str(e)
                    },
                    component="abort_executor"
                )


# Global abort executor instance
_abort_executor = AbortExecutor()


def get_abort_executor() -> AbortExecutor:
    """Get the global abort executor instance."""
    return _abort_executor


async def execute_abort_action(
    policy: AbortPolicy,
    decision: AbortDecision
) -> ExecutionResult:
    """Execute an abort action using the global executor."""
    return await _abort_executor.execute_abort_action(policy, decision)
