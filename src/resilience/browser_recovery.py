"""
Browser Crash Recovery Mechanisms

Handles browser crash detection, recovery procedures, and state restoration
to ensure resilience against browser failures during scraping operations.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .models.failure_event import FailureEvent, FailureSeverity, FailureCategory, RecoveryAction
from .failure_handler import FailureHandler
from .logging.resilience_logger import get_logger
from .correlation import get_correlation_id, with_correlation_id
from .events import publish_failure_event, publish_recovery_event


class BrowserState(Enum):
    """Browser state enumeration."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRASHED = "crashed"
    RECOVERING = "recovering"
    TERMINATED = "terminated"


@dataclass
class BrowserRecoveryContext:
    """Context for browser recovery operations."""
    browser_id: str
    session_id: str
    crash_time: datetime = field(default_factory=datetime.utcnow)
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    recovery_delay: float = 5.0  # Initial delay between recovery attempts
    last_recovery_time: Optional[datetime] = None
    crash_count: int = 0
    total_crashes: int = 0
    recovery_success: bool = False
    recovery_details: Dict[str, Any] = field(default_factory=dict)
    
    def can_recover(self) -> bool:
        """Check if browser can be recovered."""
        return (
            self.recovery_attempts < self.max_recovery_attempts and
            (self.last_recovery_time is None or
             (datetime.utcnow() - self.last_recovery_time).total_seconds() >= self.recovery_delay)
        )
    
    def increment_recovery_attempt(self) -> None:
        """Increment recovery attempt count."""
        self.recovery_attempts += 1
        self.last_recovery_time = datetime.utcnow()
        # Exponential backoff for recovery delay
        self.recovery_delay *= 2
    
    def mark_recovery_success(self, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark recovery as successful."""
        self.recovery_success = True
        if details:
            self.recovery_details.update(details)
    
    def mark_recovery_failed(self, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark recovery as failed."""
        self.recovery_success = False
        if details:
            self.recovery_details.update(details)


@dataclass
class BrowserHealthMetrics:
    """Health metrics for browser monitoring."""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_connections: int = 0
    response_time: float = 0.0
    error_rate: float = 0.0
    uptime: float = 0.0
    last_check: datetime = field(default_factory=datetime.utcnow)
    
    def is_healthy(self) -> bool:
        """Check if browser metrics indicate healthy state."""
        return (
            self.cpu_usage < 80.0 and
            self.memory_usage < 80.0 and
            self.error_rate < 5.0 and
            self.response_time < 10.0
        )


class BrowserRecoveryManager:
    """Manages browser crash detection and recovery procedures."""
    
    def __init__(
        self,
        failure_handler: Optional[FailureHandler] = None,
        health_check_interval: float = 30.0,
        crash_detection_timeout: float = 60.0
    ):
        """
        Initialize browser recovery manager.
        
        Args:
            failure_handler: Failure handler instance
            health_check_interval: Interval between health checks
            crash_detection_timeout: Timeout for crash detection
        """
        self.failure_handler = failure_handler
        self.health_check_interval = health_check_interval
        self.crash_detection_timeout = crash_detection_timeout
        self.logger = get_logger("browser_recovery")
        
        self.recovery_contexts: Dict[str, BrowserRecoveryContext] = {}
        self.browser_states: Dict[str, BrowserState] = {}
        self.health_metrics: Dict[str, BrowserHealthMetrics] = {}
        self.recovery_callbacks: Dict[str, List[Callable]] = {}
        
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize the browser recovery manager."""
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info(
            "Browser recovery manager initialized",
            event_type="recovery_manager_initialized",
            correlation_id=get_correlation_id(),
            context={
                "health_check_interval": self.health_check_interval,
                "crash_detection_timeout": self.crash_detection_timeout
            },
            component="browser_recovery"
        )
    
    async def shutdown(self) -> None:
        """Shutdown the browser recovery manager gracefully."""
        self._monitoring_active = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(
            "Browser recovery manager shutdown",
            event_type="recovery_manager_shutdown",
            correlation_id=get_correlation_id(),
            component="browser_recovery"
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        return {
            "status": "healthy" if self._monitoring_active else "unhealthy",
            "monitoring_active": self._monitoring_active,
            "tracked_browsers": len(self.recovery_contexts),
            "healthy_browsers": len([
                state for state in self.browser_states.values()
                if state == BrowserState.HEALTHY
            ]),
            "crashed_browsers": len([
                state for state in self.browser_states.values()
                if state == BrowserState.CRASHED
            ]),
            "recovery_contexts": len(self.recovery_contexts)
        }
    
    async def register_browser(
        self,
        browser_id: str,
        session_id: str,
        health_check_callback: Optional[Callable] = None
    ) -> None:
        """
        Register a browser for monitoring and recovery.
        
        Args:
            browser_id: Browser identifier
            session_id: Session identifier
            health_check_callback: Callback for health checks
        """
        # Initialize recovery context
        recovery_context = BrowserRecoveryContext(
            browser_id=browser_id,
            session_id=session_id
        )
        self.recovery_contexts[browser_id] = recovery_context
        
        # Initialize state
        self.browser_states[browser_id] = BrowserState.UNKNOWN
        self.health_metrics[browser_id] = BrowserHealthMetrics()
        
        # Register health check callback
        if health_check_callback:
            if browser_id not in self.recovery_callbacks:
                self.recovery_callbacks[browser_id] = []
            self.recovery_callbacks[browser_id].append(health_check_callback)
        
        self.logger.info(
            f"Browser registered for recovery: {browser_id}",
            event_type="browser_registered",
            correlation_id=get_correlation_id(),
            context={
                "browser_id": browser_id,
                "session_id": session_id
            },
            component="browser_recovery"
        )
    
    async def unregister_browser(self, browser_id: str) -> None:
        """
        Unregister a browser from monitoring.
        
        Args:
            browser_id: Browser identifier
        """
        if browser_id in self.recovery_contexts:
            del self.recovery_contexts[browser_id]
        
        if browser_id in self.browser_states:
            del self.browser_states[browser_id]
        
        if browser_id in self.health_metrics:
            del self.health_metrics[browser_id]
        
        if browser_id in self.recovery_callbacks:
            del self.recovery_callbacks[browser_id]
        
        self.logger.info(
            f"Browser unregistered from recovery: {browser_id}",
            event_type="browser_unregistered",
            correlation_id=get_correlation_id(),
            context={"browser_id": browser_id},
            component="browser_recovery"
        )
    
    async def report_browser_crash(
        self,
        browser_id: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Report a browser crash and initiate recovery.
        
        Args:
            browser_id: Browser identifier
            error: The crash error
            context: Additional context
            
        Returns:
            True if recovery initiated, False otherwise
        """
        if browser_id not in self.recovery_contexts:
            self.logger.warning(
                f"Browser crash reported for unregistered browser: {browser_id}",
                event_type="unregistered_browser_crash",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error": str(error)
                },
                component="browser_recovery"
            )
            return False
        
        recovery_context = self.recovery_contexts[browser_id]
        
        # Update crash information
        recovery_context.crash_count += 1
        recovery_context.total_crashes += 1
        recovery_context.crash_time = datetime.utcnow()
        
        # Update state
        self.browser_states[browser_id] = BrowserState.CRASHED
        
        # Create failure event
        failure_event = FailureEvent(
            severity=FailureSeverity.CRITICAL,
            category=FailureCategory.BROWSER,
            source="browser_recovery",
            message=f"Browser crash detected: {str(error)}",
            context={
                "browser_id": browser_id,
                "session_id": recovery_context.session_id,
                "crash_count": recovery_context.crash_count,
                "total_crashes": recovery_context.total_crashes,
                "error": str(error),
                **(context or {})
            }
        )
        
        # Log the crash
        self.logger.critical(
            f"Browser crash detected: {browser_id} - {str(error)}",
            event_type="browser_crash",
            correlation_id=get_correlation_id(),
            context={
                "browser_id": browser_id,
                "session_id": recovery_context.session_id,
                "crash_count": recovery_context.crash_count,
                "total_crashes": recovery_context.total_crashes
            },
            component="browser_recovery"
        )
        
        # Publish failure event
        await publish_failure_event(
            failure_type="browser",
            message=f"Browser crash: {browser_id}",
            severity="critical",
            job_id=recovery_context.session_id,
            context=failure_event.to_dict(),
            component="browser_recovery"
        )
        
        # Initiate recovery
        recovery_initiated = await self._initiate_browser_recovery(browser_id, error)
        
        return recovery_initiated
    
    async def _initiate_browser_recovery(
        self,
        browser_id: str,
        crash_error: Exception
    ) -> bool:
        """
        Initiate browser recovery process.
        
        Args:
            browser_id: Browser identifier
            crash_error: The crash error
            
        Returns:
            True if recovery initiated successfully
        """
        recovery_context = self.recovery_contexts.get(browser_id)
        if not recovery_context:
            return False
        
        if not recovery_context.can_recover():
            self.logger.error(
                f"Browser recovery not possible: {browser_id} "
                f"(attempts: {recovery_context.recovery_attempts}/{recovery_context.max_recovery_attempts})",
                event_type="recovery_not_possible",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "recovery_attempts": recovery_context.recovery_attempts,
                    "max_recovery_attempts": recovery_context.max_recovery_attempts
                },
                component="browser_recovery"
            )
            return False
        
        # Update state
        self.browser_states[browser_id] = BrowserState.RECOVERING
        
        self.logger.info(
            f"Initiating browser recovery: {browser_id} "
            f"(attempt {recovery_context.recovery_attempts + 1})",
            event_type="recovery_initiated",
            correlation_id=get_correlation_id(),
            context={
                "browser_id": browser_id,
                "recovery_attempts": recovery_context.recovery_attempts,
                "recovery_delay": recovery_context.recovery_delay
            },
            component="browser_recovery"
        )
        
        # Wait before recovery attempt
        await asyncio.sleep(recovery_context.recovery_delay)
        
        # Increment recovery attempt
        recovery_context.increment_recovery_attempt()
        
        try:
            # Attempt recovery
            recovery_success = await self._perform_browser_recovery(browser_id, crash_error)
            
            if recovery_success:
                recovery_context.mark_recovery_success({
                    "recovery_time": datetime.utcnow().isoformat(),
                    "recovery_attempts": recovery_context.recovery_attempts
                })
                
                # Update state
                self.browser_states[browser_id] = BrowserState.HEALTHY
                
                self.logger.info(
                    f"Browser recovery successful: {browser_id}",
                    event_type="recovery_successful",
                    correlation_id=get_correlation_id(),
                    context={
                        "browser_id": browser_id,
                        "recovery_attempts": recovery_context.recovery_attempts,
                        "recovery_details": recovery_context.recovery_details
                    },
                    component="browser_recovery"
                )
                
                # Publish recovery event
                await publish_recovery_event(
                    recovery_type="browser",
                    original_error=str(crash_error),
                    action_taken="browser_restart",
                    job_id=recovery_context.session_id,
                    context={
                        "browser_id": browser_id,
                        "recovery_attempts": recovery_context.recovery_attempts
                    },
                    component="browser_recovery"
                )
                
                # Notify callbacks
                await self._notify_recovery_callbacks(browser_id, "success")
                
                return True
            else:
                recovery_context.mark_recovery_failed({
                    "recovery_time": datetime.utcnow().isoformat(),
                    "recovery_attempts": recovery_context.recovery_attempts,
                    "error": "Recovery attempt failed"
                })
                
                # Update state
                self.browser_states[browser_id] = BrowserState.CRASHED
                
                self.logger.error(
                    f"Browser recovery failed: {browser_id}",
                    event_type="recovery_failed",
                    correlation_id=get_correlation_id(),
                    context={
                        "browser_id": browser_id,
                        "recovery_attempts": recovery_context.recovery_attempts,
                        "recovery_details": recovery_context.recovery_details
                    },
                    component="browser_recovery"
                )
                
                # Notify callbacks
                await self._notify_recovery_callbacks(browser_id, "failed")
                
                return False
                
        except Exception as e:
            recovery_context.mark_recovery_failed({
                "recovery_time": datetime.utcnow().isoformat(),
                "recovery_attempts": recovery_context.recovery_attempts,
                "error": str(e)
            })
            
            self.logger.error(
                f"Browser recovery error: {browser_id} - {str(e)}",
                event_type="recovery_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error": str(e),
                    "stack_trace": str(e.__traceback__) if hasattr(e, '__traceback__') else None
                },
                component="browser_recovery"
            )
            
            return False
    
    async def _perform_browser_recovery(
        self,
        browser_id: str,
        crash_error: Exception
    ) -> bool:
        """
        Perform the actual browser recovery.
        
        Args:
            browser_id: Browser identifier
            crash_error: The crash error
            
        Returns:
            True if recovery successful, False otherwise
        """
        # In a real implementation, this would:
        # 1. Terminate the crashed browser process
        # 2. Clean up resources
        # 3. Start a new browser instance
        # 4. Restore session state if available
        # 5. Validate browser health
        
        # For this implementation, we'll simulate the recovery process
        try:
            # Simulate browser termination
            await asyncio.sleep(1.0)
            
            # Simulate cleanup
            await asyncio.sleep(0.5)
            
            # Simulate browser restart
            await asyncio.sleep(2.0)
            
            # Simulate state restoration
            await asyncio.sleep(1.0)
            
            # Simulate health validation
            await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Browser recovery simulation failed: {browser_id} - {str(e)}",
                event_type="recovery_simulation_failed",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error": str(e)
                },
                component="browser_recovery"
            )
            return False
    
    async def _notify_recovery_callbacks(
        self,
        browser_id: str,
        status: str
    ) -> None:
        """
        Notify registered callbacks about recovery status.
        
        Args:
            browser_id: Browser identifier
            status: Recovery status ("success" or "failed")
        """
        callbacks = self.recovery_callbacks.get(browser_id, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(browser_id, status)
                else:
                    callback(browser_id, status)
            except Exception as e:
                self.logger.error(
                    f"Recovery callback error: {browser_id} - {str(e)}",
                    event_type="recovery_callback_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "browser_id": browser_id,
                        "callback_error": str(e)
                    },
                    component="browser_recovery"
                )
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for browser health checks."""
        while self._monitoring_active:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Browser monitoring error: {str(e)}",
                    event_type="monitoring_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "error": str(e)
                    },
                    component="browser_recovery"
                )
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered browsers."""
        for browser_id in list(self.recovery_contexts.keys()):
            try:
                await self._check_browser_health(browser_id)
            except Exception as e:
                self.logger.error(
                    f"Health check error for browser {browser_id}: {str(e)}",
                    event_type="health_check_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "browser_id": browser_id,
                        "error": str(e)
                    },
                    component="browser_recovery"
                )
    
    async def _check_browser_health(self, browser_id: str) -> None:
        """
        Check health of a specific browser.
        
        Args:
            browser_id: Browser identifier
        """
        if browser_id not in self.recovery_contexts:
            return
        
        # Get health metrics from callbacks
        metrics = self.health_metrics.get(browser_id, BrowserHealthMetrics())
        
        # Call registered health check callbacks
        callbacks = self.recovery_callbacks.get(browser_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    result = await callback(browser_id)
                else:
                    result = callback(browser_id)
                
                # Update metrics if callback returns them
                if isinstance(result, dict):
                    metrics.__dict__.update(result)
                    
            except Exception as e:
                self.logger.warning(
                    f"Health check callback error for browser {browser_id}: {str(e)}",
                    event_type="health_check_callback_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "browser_id": browser_id,
                        "error": str(e)
                    },
                    component="browser_recovery"
                )
        
        # Update metrics
        self.health_metrics[browser_id] = metrics
        metrics.last_check = datetime.utcnow()
        
        # Determine browser state
        current_state = self.browser_states.get(browser_id, BrowserState.UNKNOWN)
        
        if current_state == BrowserState.RECOVERING:
            # Don't change state during recovery
            pass
        elif metrics.is_healthy():
            if current_state != BrowserState.HEALTHY:
                self.browser_states[browser_id] = BrowserState.HEALTHY
                self.logger.info(
                    f"Browser health restored: {browser_id}",
                    event_type="browser_health_restored",
                    correlation_id=get_correlation_id(),
                    context={
                        "browser_id": browser_id,
                        "metrics": metrics.__dict__
                    },
                    component="browser_recovery"
                )
        else:
            if current_state != BrowserState.DEGRADED:
                self.browser_states[browser_id] = BrowserState.DEGRADED
                self.logger.warning(
                    f"Browser health degraded: {browser_id}",
                    event_type="browser_health_degraded",
                    correlation_id=get_correlation_id(),
                    context={
                        "browser_id": browser_id,
                        "metrics": metrics.__dict__
                    },
                    component="browser_recovery"
                )
    
    def get_browser_status(self, browser_id: str) -> Dict[str, Any]:
        """
        Get detailed status of a browser.
        
        Args:
            browser_id: Browser identifier
            
        Returns:
            Browser status information
        """
        recovery_context = self.recovery_contexts.get(browser_id)
        state = self.browser_states.get(browser_id, BrowserState.UNKNOWN)
        metrics = self.health_metrics.get(browser_id, BrowserHealthMetrics())
        
        return {
            "browser_id": browser_id,
            "state": state.value,
            "is_healthy": metrics.is_healthy(),
            "recovery_context": recovery_context.__dict__ if recovery_context else None,
            "health_metrics": metrics.__dict__,
            "last_check": metrics.last_check.isoformat() if metrics.last_check else None
        }
    
    def get_all_browser_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all tracked browsers.
        
        Returns:
            Dictionary mapping browser IDs to status information
        """
        return {
            browser_id: self.get_browser_status(browser_id)
            for browser_id in self.recovery_contexts.keys()
        }


# Global browser recovery manager instance
_browser_recovery_manager = BrowserRecoveryManager()


def get_browser_recovery_manager() -> BrowserRecoveryManager:
    """Get the global browser recovery manager instance."""
    return _browser_recovery_manager


async def register_browser_for_recovery(
    browser_id: str,
    session_id: str,
    health_check_callback: Optional[Callable] = None
) -> None:
    """Register a browser for recovery using the global manager."""
    await _browser_recovery_manager.register_browser(
        browser_id, session_id, health_check_callback
    )


async def report_browser_crash(
    browser_id: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """Report a browser crash using the global manager."""
    return await _browser_recovery_manager.report_browser_crash(
        browser_id, error, context
    )
