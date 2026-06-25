"""
Graceful Degradation Coordinator

Coordinates graceful degradation strategies when failures occur, ensuring that
partial data collection can continue even when individual components fail.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .models.failure_event import FailureEvent, FailureSeverity, FailureCategory, RecoveryAction
from .failure_handler import FailureHandler
from .tab_handler import TabHandler, TabProcessingResult
from .browser_recovery import BrowserRecoveryManager
from .logging.resilience_logger import get_logger
from .correlation import get_correlation_id, with_correlation_id
from .events import publish_failure_event, publish_recovery_event
from .config import get_configuration


class DegradationLevel(Enum):
    """Levels of graceful degradation."""
    NONE = "none"           # No degradation, full functionality
    MINIMAL = "minimal"       # Essential functionality only
    REDUCED = "reduced"       # Reduced feature set
    LIMITED = "limited"       # Limited operations
    EMERGENCY = "emergency"     # Emergency mode only


@dataclass
class DegradationStrategy:
    """Defines a degradation strategy for specific failure scenarios."""
    name: str
    description: str
    level: DegradationLevel
    triggers: List[str]  # Failure types that trigger this strategy
    actions: List[str]  # Actions to take when triggered
    recovery_conditions: List[str]  # Conditions for recovery
    max_duration: Optional[int] = None  # Maximum duration in seconds


@dataclass
class DegradationContext:
    """Context for degradation operations."""
    job_id: str
    current_level: DegradationLevel = DegradationLevel.NONE
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    active_strategies: List[DegradationStrategy] = field(default_factory=list)
    failure_count: int = 0
    recovery_count: int = 0
    degradation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def is_degraded(self) -> bool:
        """Check if system is currently degraded."""
        return self.current_level != DegradationLevel.NONE
    
    def can_recover(self) -> bool:
        """Check if system can recover from current degradation."""
        return self.is_degraded() and self.recovery_count > 0
    
    def mark_degradation(
        self,
        strategy: DegradationStrategy,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark degradation level change."""
        self.current_level = strategy.level
        self.degradation_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "strategy": strategy.name,
            "level": strategy.level.value,
            "reason": reason,
            "context": context or {}
        })
        
        # Add strategy to active strategies if not already present
        if strategy not in self.active_strategies:
            self.active_strategies.append(strategy)
    
    def mark_recovery(
        self,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark recovery from degradation."""
        self.recovery_count += 1
        self.degradation_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "recovery",
            "reason": reason,
            "context": context or {}
        })
        
        # Check if all strategies have recovery conditions met
        all_can_recover = all(
            self._check_recovery_conditions(strategy)
            for strategy in self.active_strategies
        )
        
        if all_can_recover:
            self.current_level = DegradationLevel.NONE
            self.end_time = datetime.utcnow()
            self.active_strategies.clear()


class GracefulDegradationCoordinator:
    """Coordinates graceful degradation strategies and recovery procedures."""
    
    def __init__(
        self,
        failure_handler: Optional[FailureHandler] = None,
        tab_handler: Optional[TabHandler] = None,
        browser_recovery: Optional[BrowserRecoveryManager] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize graceful degradation coordinator.
        
        Args:
            failure_handler: Failure handler instance
            tab_handler: Tab handler instance
            browser_recovery: Browser recovery manager instance
            config: Configuration dictionary
        """
        self.failure_handler = failure_handler
        self.tab_handler = tab_handler
        self.browser_recovery = browser_recovery
        self.config = config or get_configuration()
        self.logger = get_logger("degradation_coordinator")
        
        self.degradation_contexts: Dict[str, DegradationContext] = {}
        self.degradation_strategies: List[DegradationStrategy] = []
        self.active_degradations: Set[str] = []
        
        # Initialize default degradation strategies
        self._initialize_default_strategies()
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the degradation coordinator."""
        if self._initialized:
            return
        
        # Register with failure handler for degradation events
        if self.failure_handler:
            await self.failure_handler.register_failure_handler(
                "degradation",
                self._handle_degradation_failure
            )
        
        self._initialized = True
        
        self.logger.info(
            "Graceful degradation coordinator initialized",
            event_type="degradation_coordinator_initialized",
            correlation_id=get_correlation_id(),
            context={
                "strategies_count": len(self.degradation_strategies),
                "config": self.config
            },
            component="degradation_coordinator"
        )
    
    async def shutdown(self) -> None:
        """Shutdown the degradation coordinator gracefully."""
        if not self._initialized:
            return
        
        # Clear all active degradations
        self.active_degradations.clear()
        self.degradation_contexts.clear()
        
        self._initialized = False
        
        self.logger.info(
            "Graceful degradation coordinator shutdown",
            event_type="degradation_coordinator_shutdown",
            correlation_id=get_correlation_id(),
            component="degradation_coordinator"
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "initialized": self._initialized,
            "active_degradations": len(self.active_degradations),
            "degradation_contexts": len(self.degradation_contexts),
            "strategies_count": len(self.degradation_strategies)
        }
    
    async def register_job(
        self,
        job_id: str,
        initial_strategy: Optional[DegradationStrategy] = None
    ) -> str:
        """
        Register a job for degradation monitoring.
        
        Args:
            job_id: Job identifier
            initial_strategy: Initial degradation strategy
            
        Returns:
            Job registration ID
        """
        context = DegradationContext(job_id=job_id)
        
        if initial_strategy:
            context.mark_degradation(
                initial_strategy,
                "Initial registration"
            )
        
        self.degradation_contexts[job_id] = context
        
        self.logger.info(
            f"Job registered for degradation: {job_id}",
            event_type="job_registered_for_degradation",
            correlation_id=get_correlation_id(),
            context={
                "job_id": job_id,
                "initial_level": context.current_level.value,
                "strategies_count": len(context.active_strategies)
            },
            component="degradation_coordinator"
        )
        
        return job_id
    
    async def unregister_job(self, job_id: str) -> None:
        """
        Unregister a job from degradation monitoring.
        
        Args:
            job_id: Job identifier
        """
        if job_id in self.degradation_contexts:
            context = self.degradation_contexts[job_id]
            
            # Log final status
            self.logger.info(
                f"Job unregistered from degradation: {job_id} "
                f"(final level: {context.current_level.value})",
                event_type="job_unregistered_from_degradation",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": job_id,
                    "final_level": context.current_level.value,
                    "total_failures": context.failure_count,
                    "total_recoveries": context.recovery_count,
                    "duration": (
                        (context.end_time or datetime.utcnow()) - context.start_time
                    ).total_seconds() if context.end_time else None
                },
                component="degradation_coordinator"
            )
            
            del self.degradation_contexts[job_id]
    
    async def handle_failure_with_degradation(
        self,
        failure_event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a failure event with potential degradation.
        
        Args:
            failure_event: Failure event details
            context: Additional context
            
        Returns:
            Handling result with degradation actions taken
        """
        job_id = context.get("job_id")
        if not job_id:
            # No job context, cannot apply degradation
            return {
                "success": False,
                "action_taken": "no_job_context",
                "degradation_applied": False
            }
        
        degradation_context = self.degradation_contexts.get(job_id)
        if not degradation_context:
            # Job not registered for degradation
            return {
                "success": False,
                "action_taken": "job_not_registered",
                "degradation_applied": False
            }
        
        # Update failure count
        degradation_context.failure_count += 1
        
        # Check if degradation should be triggered
        strategy = self._evaluate_degradation_need(failure_event, degradation_context)
        
        if strategy:
            # Apply degradation
            degradation_context.mark_degradation(
                strategy,
                f"Failure count threshold reached: {degradation_context.failure_count}",
                context
            )
            
            # Execute degradation actions
            await self._execute_degradation_actions(
                job_id, strategy, failure_event, context
            )
            
            # Add to active degradations
            self.active_degradations.add(job_id)
            
            self.logger.warning(
                f"Degradation applied to job {job_id}: {strategy.name} "
                f"(level: {strategy.level.value})",
                event_type="degradation_applied",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": job_id,
                    "strategy": strategy.name,
                    "level": strategy.level.value,
                    "failure_count": degradation_context.failure_count,
                    "reason": strategy.description
                },
                component="degradation_coordinator"
            )
            
            return {
                "success": True,
                "action_taken": "degradation_applied",
                "degradation_level": strategy.level.value,
                "strategy_name": strategy.name,
                "degradation_applied": True
            }
        
        return {
            "success": False,
            "action_taken": "no_degradation_needed",
            "degradation_applied": False
        }
    
    async def check_recovery_conditions(
        self,
        job_id: str
    ) -> bool:
        """
        Check if recovery conditions are met for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if recovery conditions are met, False otherwise
        """
        degradation_context = self.degradation_contexts.get(job_id)
        if not degradation_context:
            return False
        
        if not degradation_context.is_degraded():
            return True
        
        # Check if all active strategies can recover
        all_can_recover = all(
            self._check_recovery_conditions(strategy)
            for strategy in degradation_context.active_strategies
        )
        
        return all_can_recover
    
    async def attempt_recovery(
        self,
        job_id: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Attempt to recover from degradation for a job.
        
        Args:
            job_id: Job identifier
            reason: Reason for recovery attempt
            context: Additional context
            
        Returns:
            True if recovery successful, False otherwise
        """
        degradation_context = self.degradation_contexts.get(job_id)
        if not degradation_context:
            return False
        
        if not degradation_context.can_recover():
            self.logger.warning(
                f"Recovery not possible for job {job_id}: "
                f"degraded: {degradation_context.current_level.value}, "
                f"attempts: {degradation_context.recovery_count}",
                event_type="recovery_not_possible",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": job_id,
                    "current_level": degradation_context.current_level.value,
                    "recovery_attempts": degradation_context.recovery_count
                },
                component="degradation_coordinator"
            )
            return False
        
        # Attempt recovery
        recovery_success = await self._execute_recovery_actions(
            job_id, degradation_context, reason, context
        )
        
        if recovery_success:
            # Remove from active degradations
            self.active_degradations.discard(job_id)
            
            self.logger.info(
                f"Recovery successful for job {job_id}",
                event_type="recovery_successful",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": job_id,
                    "reason": reason,
                    "recovery_attempts": degradation_context.recovery_count + 1
                },
                component="degradation_coordinator"
            )
        else:
            self.logger.error(
                f"Recovery failed for job {job_id}",
                event_type="recovery_failed",
                correlation_id=get_correlation_id(),
                context={
                    "job_id": job_id,
                    "reason": reason,
                    "recovery_attempts": degradation_context.recovery_count + 1
                },
                component="degradation_coordinator"
            )
        
        return recovery_success
    
    def get_degradation_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get degradation status for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Degradation status information
        """
        degradation_context = self.degradation_contexts.get(job_id)
        if not degradation_context:
            return {
                "job_id": job_id,
                "is_degraded": False,
                "current_level": "none",
                "active_strategies": [],
                "failure_count": 0,
                "recovery_count": 0,
                "degradation_history": []
            }
        
        return {
            "job_id": job_id,
            "is_degraded": degradation_context.is_degraded(),
            "current_level": degradation_context.current_level.value,
            "active_strategies": [
                {
                    "name": strategy.name,
                    "level": strategy.level.value,
                    "description": strategy.description
                }
                for strategy in degradation_context.active_strategies
            ],
            "failure_count": degradation_context.failure_count,
            "recovery_count": degradation_context.recovery_count,
            "degradation_history": degradation_context.degradation_history,
            "start_time": degradation_context.start_time.isoformat(),
            "end_time": degradation_context.end_time.isoformat() if degradation_context.end_time else None,
            "duration": (
                (degradation_context.end_time or datetime.utcnow()) - degradation_context.start_time
            ).total_seconds() if degradation_context.end_time else None
        }
    
    def get_all_degradation_status(self) -> Dict[str, Any]:
        """
        Get degradation status for all jobs.
        
        Returns:
            Dictionary mapping job IDs to degradation status
        """
        return {
            job_id: self.get_degradation_status(job_id)
            for job_id in self.degradation_contexts.keys()
        }
    
    def _initialize_default_strategies(self) -> None:
        """Initialize default degradation strategies."""
        # Network failure strategy
        network_strategy = DegradationStrategy(
            name="network_failure",
            description="Degrade to minimal network operations when network failures occur",
            level=DegradationLevel.MINIMAL,
            triggers=["network", "connection", "timeout"],
            actions=["reduce_concurrent_requests", "increase_timeouts", "disable_optional_features"],
            recovery_conditions=["network_stable_for_60s", "error_rate_below_5_percent"],
            max_duration=300
        )
        
        # Browser failure strategy
        browser_strategy = DegradationStrategy(
            name="browser_failure",
            description="Degrade to single browser instance when browser failures occur",
            level=DegradationLevel.REDUCED,
            triggers=["browser", "crash", "timeout"],
            actions=["reduce_concurrent_tabs", "disable_heavy_features", "increase_recovery_time"],
            recovery_conditions=["browser_stable_for_120s", "crash_count_below_2"],
            max_duration=600
        )
        
        # System resource strategy
        system_strategy = DegradationStrategy(
            name="system_resource",
            description="Degrade to minimal operations when system resources are constrained",
            level=DegradationLevel.LIMITED,
            triggers=["memory", "cpu", "disk", "resource"],
            actions=["pause_processing", "clear_caches", "reduce_batch_size"],
            recovery_conditions=["memory_below_80_percent", "cpu_below_80_percent"],
            max_duration=900
        )
        
        # High failure rate strategy
        high_failure_rate_strategy = DegradationStrategy(
            name="high_failure_rate",
            description="Enter emergency mode when failure rate is too high",
            level=DegradationLevel.EMERGENCY,
            triggers=["high_failure_rate", "cascade_failure"],
            actions=["pause_all_processing", "save_state", "notify_admin"],
            recovery_conditions=["failure_rate_below_20_percent", "no_failures_for_300s"],
            max_duration=1800
        )
        
        self.degradation_strategies.extend([
            network_strategy,
            browser_strategy,
            system_strategy,
            high_failure_rate_strategy
        ])
    
    def _evaluate_degradation_need(
        self,
        failure_event: Dict[str, Any],
        context: DegradationContext
    ) -> Optional[DegradationStrategy]:
        """
        Evaluate if degradation should be triggered.
        
        Args:
            failure_event: Failure event details
            context: Degradation context
            
        Returns:
            Appropriate degradation strategy or None
        """
        failure_type = failure_event.get("failure_type", "")
        failure_category = failure_event.get("category", "")
        
        # Check failure count thresholds
        if context.failure_count >= 10:
            return self._get_strategy_by_name("high_failure_rate")
        
        # Check specific failure types
        for strategy in self.degradation_strategies:
            if any(trigger in failure_type.lower() for trigger in strategy.triggers):
                if any(trigger in failure_category.lower() for trigger in strategy.triggers):
                    return strategy
        
        return None
    
    def _get_strategy_by_name(self, name: str) -> Optional[DegradationStrategy]:
        """Get strategy by name."""
        for strategy in self.degradation_strategies:
            if strategy.name == name:
                return strategy
        return None
    
    async def _execute_degradation_actions(
        self,
        job_id: str,
        strategy: DegradationStrategy,
        failure_event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> None:
        """
        Execute degradation actions for a strategy.
        
        Args:
            job_id: Job identifier
            strategy: Degradation strategy to execute
            failure_event: Failure event that triggered degradation
            context: Additional context
        """
        for action in strategy.actions:
            await self._execute_degradation_action(
                job_id, action, strategy, failure_event, context
            )
    
    async def _execute_degradation_action(
        self,
        job_id: str,
        action: str,
        strategy: DegradationStrategy,
        failure_event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> None:
        """
        Execute a specific degradation action.
        
        Args:
            job_id: Job identifier
            action: Action to execute
            strategy: Degradation strategy
            failure_event: Failure event that triggered degradation
            context: Additional context
        """
        self.logger.info(
            f"Executing degradation action: {action} for job {job_id}",
            event_type="degradation_action_executed",
            correlation_id=get_correlation_id(),
            context={
                "job_id": job_id,
                "strategy": strategy.name,
                "action": action,
                "failure_event": failure_event
            },
            component="degradation_coordinator"
        )
        
        # Execute specific actions based on action name
        if action == "reduce_concurrent_requests":
            await self._reduce_concurrent_requests(job_id, context)
        elif action == "increase_timeouts":
            await self._increase_timeouts(job_id, context)
        elif action == "disable_optional_features":
            await self._disable_optional_features(job_id, context)
        elif action == "reduce_concurrent_tabs":
            await self._reduce_concurrent_tabs(job_id, context)
        elif action == "disable_heavy_features":
            await self._disable_heavy_features(job_id, context)
        elif action == "increase_recovery_time":
            await self._increase_recovery_time(job_id, context)
        elif action == "pause_processing":
            await self._pause_processing(job_id, context)
        elif action == "clear_caches":
            await self._clear_caches(job_id, context)
        elif action == "reduce_batch_size":
            await self._reduce_batch_size(job_id, context)
        elif action == "save_state":
            await self._save_state(job_id, context)
        elif action == "notify_admin":
            await self._notify_admin(job_id, strategy, context)
    
    async def _reduce_concurrent_requests(
        self,
        job_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Reduce concurrent requests."""
        # Implementation would reduce concurrent request limits
        pass
    
    async def _increase_timeouts(
        self,
        job_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Increase timeout values."""
        # Implementation would increase timeout configurations
        pass
    
    async def _disable_optional_features(
        self,
        job_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Disable optional features."""
        # Implementation would disable non-essential features
        pass
    
    async def _reduce_concurrent_tabs(
        self,
        job_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Reduce concurrent tab processing."""
        if self.tab_handler:
            # Reduce max concurrent tabs
            self.tab_handler.max_concurrent_tabs = max(1, self.tab_handler.max_concurrent_tabs // 2)
    
    async def _disable_heavy_features(
        self,
        job_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Disable heavy features."""
        # Implementation would disable resource-intensive features
        pass
    
    async def _increase_recovery_time(
        self,
        job_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Increase recovery time between retries."""
        # Implementation would increase retry delays
        pass
    
    async def _pause_processing(
        self,
        job_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Pause processing temporarily."""
        # Implementation would pause job processing
        pass
    
    async def _clear_caches(
        self,
        job_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Clear caches and temporary data."""
        # Implementation would clear memory caches
        pass
    
    async def _reduce_batch_size(
        self,
        job_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Reduce batch processing size."""
        # Implementation would reduce batch sizes
        pass
    
    async def _save_state(
        self,
        job_id: str,
        context: Dict[str, Any]
    ) -> None:
        """Save current state."""
        # Implementation would save job state to checkpoint
        pass
    
    async def _notify_admin(
        self,
        job_id: str,
        strategy: DegradationStrategy,
        context: Dict[str, Any]
    ) -> None:
        """Notify administrator about degradation."""
        self.logger.critical(
            f"ADMIN NOTIFICATION: Job {job_id} degraded to {strategy.level.value} level "
            f"due to: {strategy.description}",
            event_type="admin_notification",
            correlation_id=get_correlation_id(),
            context={
                "job_id": job_id,
                "strategy": strategy.name,
                "level": strategy.level.value,
                "description": strategy.description,
                "failure_count": context.get("failure_count", 0),
                "recovery_count": context.get("recovery_count", 0)
            },
            component="degradation_coordinator"
        )
    
    def _check_recovery_conditions(
        self,
        strategy: DegradationStrategy
    ) -> bool:
        """Check if recovery conditions are met for a strategy."""
        # In a real implementation, this would check actual conditions
        # For now, return True to simulate recovery conditions
        return True
    
    async def _execute_recovery_actions(
        self,
        job_id: str,
        degradation_context: DegradationContext,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Execute recovery actions for a degradation context."""
        # Execute reverse actions for each active strategy
        recovery_success = True
        
        for strategy in degradation_context.active_strategies:
            try:
                # Execute reverse actions
                for action in strategy.actions:
                    await self._execute_recovery_action(
                        job_id, action, strategy, {}, context or {}
                    )
            except Exception as e:
                self.logger.error(
                    f"Recovery action failed: {action} for job {job_id} - {str(e)}",
                    event_type="recovery_action_failed",
                    correlation_id=get_correlation_id(),
                    context={
                        "job_id": job_id,
                        "action": action,
                        "error": str(e)
                    },
                    component="degradation_coordinator"
                )
                recovery_success = False
        
        return recovery_success


# Global degradation coordinator instance
_degradation_coordinator = GracefulDegradationCoordinator()


def get_degradation_coordinator() -> GracefulDegradationCoordinator:
    """Get the global degradation coordinator instance."""
    return _degradation_coordinator


async def register_job_for_degradation(
    job_id: str,
    initial_strategy: Optional[DegradationStrategy] = None
) -> str:
    """Register a job for degradation monitoring using the global coordinator."""
    return await _degradation_coordinator.register_job(job_id, initial_strategy)


async def handle_failure_with_degradation(
    failure_event: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle a failure with potential degradation using the global coordinator."""
    return await _degradation_coordinator.handle_failure_with_degradation(failure_event, context)
