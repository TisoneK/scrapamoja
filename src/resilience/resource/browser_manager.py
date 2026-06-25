"""
Browser Manager

Specialized management for browser resources with automatic restart policies,
tab cleanup, memory management, and lifecycle control.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from ..models.resource import Resource, ResourceMetrics, ResourceStatus, ResourceType, ResourceAction
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_resource_event


class BrowserState(Enum):
    """Browser lifecycle states."""
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    RESTARTING = "restarting"
    SHUTTING_DOWN = "shutting_down"
    CRASHED = "crashed"
    UNKNOWN = "unknown"


@dataclass
class BrowserMetrics:
    """Metrics specific to browser resources."""
    state: BrowserState = BrowserState.UNKNOWN
    tab_count: int = 0
    active_tab_count: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    page_load_time_avg: float = 0.0
    error_count: int = 0
    crash_count: int = 0
    uptime_seconds: float = 0.0
    last_activity: Optional[datetime] = None
    resource_utilization: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "state": self.state.value,
            "tab_count": self.tab_count,
            "active_tab_count": self.active_tab_count,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "page_load_time_avg": self.page_load_time_avg,
            "error_count": self.error_count,
            "crash_count": self.crash_count,
            "uptime_seconds": self.uptime_seconds,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "resource_utilization": self.resource_utilization
        }


@dataclass
class BrowserConfiguration:
    """Configuration for browser management."""
    max_tabs: int = 50
    max_memory_mb: float = 2048.0
    max_cpu_percent: float = 80.0
    idle_timeout_minutes: int = 30
    restart_on_crash: bool = True
    restart_on_memory_threshold: bool = True
    restart_on_error_threshold: bool = True
    max_errors_per_hour: int = 10
    auto_cleanup_tabs: bool = True
    cleanup_idle_tabs: bool = True
    cleanup_interval_minutes: int = 15
    restart_cooldown_minutes: int = 5
    health_check_interval_seconds: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "max_tabs": self.max_tabs,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "idle_timeout_minutes": self.idle_timeout_minutes,
            "restart_on_crash": self.restart_on_crash,
            "restart_on_memory_threshold": self.restart_on_memory_threshold,
            "restart_on_error_threshold": self.restart_on_error_threshold,
            "max_errors_per_hour": self.max_errors_per_hour,
            "auto_cleanup_tabs": self.auto_cleanup_tabs,
            "cleanup_idle_tabs": self.cleanup_idle_tabs,
            "cleanup_interval_minutes": self.cleanup_interval_minutes,
            "restart_cooldown_minutes": self.restart_cooldown_minutes,
            "health_check_interval_seconds": self.health_check_interval_seconds
        }


class BrowserManager:
    """Manages browser resources with lifecycle control and automatic restarts."""
    
    def __init__(self):
        """Initialize browser manager."""
        self.logger = get_logger("browser_manager")
        
        # Browser instances
        self.browsers: Dict[str, Resource] = {}
        self.browser_metrics: Dict[str, BrowserMetrics] = {}
        self.browser_configurations: Dict[str, BrowserConfiguration] = {}
        
        # State tracking
        self.browser_states: Dict[str, BrowserState] = {}
        self.browser_start_times: Dict[str, datetime] = {}
        self.error_history: Dict[str, List[datetime]] = {}
        self.restart_history: Dict[str, List[datetime]] = {}
        
        # Callbacks
        self.browser_callbacks: List[Callable[[str, BrowserMetrics], None]] = []
        
        # Tasks
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.cleanup_tasks: Dict[str, asyncio.Task] = {}
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the browser manager."""
        if self._initialized:
            return
        
        self._initialized = True
        
        self.logger.info(
            "Browser manager initialized",
            event_type="browser_manager_initialized",
            correlation_id=get_correlation_id(),
            context={},
            component="browser_manager"
        )
    
    async def shutdown(self) -> None:
        """Shutdown the browser manager gracefully."""
        if not self._initialized:
            return
        
        # Cancel all monitoring tasks
        for browser_id, task in self.monitoring_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Cancel all cleanup tasks
        for browser_id, task in self.cleanup_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Shutdown all browsers
        for browser_id in list(self.browsers.keys()):
            await self.shutdown_browser(browser_id)
        
        self.monitoring_tasks.clear()
        self.cleanup_tasks.clear()
        self.browsers.clear()
        self.browser_metrics.clear()
        self.browser_configurations.clear()
        self.browser_states.clear()
        self.browser_start_times.clear()
        self.error_history.clear()
        self.restart_history.clear()
        
        self._initialized = False
        
        self.logger.info(
            "Browser manager shutdown",
            event_type="browser_manager_shutdown",
            correlation_id=get_correlation_id(),
            component="browser_manager"
        )
    
    async def create_browser(
        self,
        browser_id: str,
        configuration: Optional[BrowserConfiguration] = None,
        description: str = ""
    ) -> bool:
        """
        Create a new browser instance.
        
        Args:
            browser_id: Unique browser identifier
            configuration: Browser configuration
            description: Browser description
            
        Returns:
            True if created successfully, False if already exists
        """
        if browser_id in self.browsers:
            return False
        
        try:
            # Create browser resource
            browser = Resource(
                name=browser_id,
                resource_type=ResourceType.BROWSER,
                description=description
            )
            
            # Set configuration
            config = configuration or BrowserConfiguration()
            self.browser_configurations[browser_id] = config
            
            # Initialize metrics
            metrics = BrowserMetrics(state=BrowserState.STARTING)
            self.browser_metrics[browser_id] = metrics
            
            # Initialize state tracking
            self.browser_states[browser_id] = BrowserState.STARTING
            self.browser_start_times[browser_id] = datetime.utcnow()
            self.error_history[browser_id] = []
            self.restart_history[browser_id] = []
            
            # Add to resources
            self.browsers[browser_id] = browser
            
            # Start browser (placeholder - actual browser initialization would go here)
            await self._start_browser_instance(browser_id)
            
            # Start monitoring
            await self._start_browser_monitoring(browser_id)
            
            # Start cleanup task
            if config.auto_cleanup_tabs:
                await self._start_browser_cleanup(browser_id)
            
            # Publish event
            await publish_resource_event(
                action="created",
                resource_id=browser_id,
                resource_type=ResourceType.BROWSER.value,
                context={
                    "configuration": config.to_dict()
                },
                component="browser_manager"
            )
            
            self.logger.info(
                f"Browser created: {browser_id}",
                event_type="browser_created",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "configuration": config.to_dict()
                },
                component="browser_manager"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to create browser {browser_id}: {str(e)}",
                event_type="browser_creation_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error": str(e)
                },
                component="browser_manager"
            )
            return False
    
    async def shutdown_browser(self, browser_id: str) -> bool:
        """
        Shutdown a browser instance.
        
        Args:
            browser_id: Browser identifier
            
        Returns:
            True if shutdown successfully, False if not found
        """
        if browser_id not in self.browsers:
            return False
        
        try:
            # Update state
            self.browser_states[browser_id] = BrowserState.SHUTTING_DOWN
            
            # Stop monitoring
            if browser_id in self.monitoring_tasks:
                self.monitoring_tasks[browser_id].cancel()
                try:
                    await self.monitoring_tasks[browser_id]
                except asyncio.CancelledError:
                    pass
                del self.monitoring_tasks[browser_id]
            
            # Stop cleanup task
            if browser_id in self.cleanup_tasks:
                self.cleanup_tasks[browser_id].cancel()
                try:
                    await self.cleanup_tasks[browser_id]
                except asyncio.CancelledError:
                    pass
                del self.cleanup_tasks[browser_id]
            
            # Shutdown browser instance (placeholder)
            await self._shutdown_browser_instance(browser_id)
            
            # Update state
            self.browser_states[browser_id] = BrowserState.UNKNOWN
            
            # Remove from resources
            del self.browsers[browser_id]
            del self.browser_metrics[browser_id]
            del self.browser_configurations[browser_id]
            del self.browser_states[browser_id]
            del self.browser_start_times[browser_id]
            del self.error_history[browser_id]
            del self.restart_history[browser_id]
            
            # Publish event
            await publish_resource_event(
                action="shutdown",
                resource_id=browser_id,
                resource_type=ResourceType.BROWSER.value,
                context={},
                component="browser_manager"
            )
            
            self.logger.info(
                f"Browser shutdown: {browser_id}",
                event_type="browser_shutdown",
                correlation_id=get_correlation_id(),
                context={"browser_id": browser_id},
                component="browser_manager"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to shutdown browser {browser_id}: {str(e)}",
                event_type="browser_shutdown_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error": str(e)
                },
                component="browser_manager"
            )
            return False
    
    async def restart_browser(
        self,
        browser_id: str,
        reason: str = "manual"
    ) -> bool:
        """
        Restart a browser instance.
        
        Args:
            browser_id: Browser identifier
            reason: Reason for restart
            
        Returns:
            True if restarted successfully, False if not found or not allowed
        """
        if browser_id not in self.browsers:
            return False
        
        browser = self.browsers[browser_id]
        config = self.browser_configurations[browser_id]
        
        # Check if restart is allowed (cooldown)
        if not self._can_restart_browser(browser_id):
            self.logger.warning(
                f"Browser restart not allowed: {browser_id}",
                event_type="browser_restart_blocked",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "reason": reason,
                    "restart_count": browser.restart_count,
                    "last_restart": browser.last_restart.isoformat() if browser.last_restart else None
                },
                component="browser_manager"
            )
            return False
        
        try:
            # Update state
            self.browser_states[browser_id] = BrowserState.RESTARTING
            browser.update_status(ResourceStatus.RESTARTING)
            browser.record_action(ResourceAction.RESTART)
            
            # Record restart
            self.restart_history[browser_id].append(datetime.utcnow())
            
            # Perform restart
            await self._restart_browser_instance(browser_id)
            
            # Update state
            self.browser_states[browser_id] = BrowserState.RUNNING
            browser.update_status(ResourceStatus.HEALTHY)
            
            # Reset metrics
            metrics = self.browser_metrics[browser_id]
            metrics.crash_count = 0
            metrics.error_count = 0
            metrics.uptime_seconds = 0
            
            # Publish event
            await publish_resource_event(
                action="restarted",
                resource_id=browser_id,
                resource_type=ResourceType.BROWSER.value,
                context={
                    "reason": reason,
                    "restart_count": browser.restart_count
                },
                component="browser_manager"
            )
            
            self.logger.info(
                f"Browser restarted: {browser_id} ({reason})",
                event_type="browser_restarted",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "reason": reason,
                    "restart_count": browser.restart_count
                },
                component="browser_manager"
            )
            
            return True
            
        except Exception as e:
            self.browser_states[browser_id] = BrowserState.CRASHED
            browser.update_status(ResourceStatus.FAILED)
            
            self.logger.error(
                f"Failed to restart browser {browser_id}: {str(e)}",
                event_type="browser_restart_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "reason": reason,
                    "error": str(e)
                },
                component="browser_manager"
            )
            
            return False
    
    async def get_browser_metrics(self, browser_id: str) -> Optional[BrowserMetrics]:
        """
        Get current metrics for a browser.
        
        Args:
            browser_id: Browser identifier
            
        Returns:
            BrowserMetrics or None if not found
        """
        return self.browser_metrics.get(browser_id)
    
    async def update_browser_metrics(
        self,
        browser_id: str,
        metrics: BrowserMetrics
    ) -> bool:
        """
        Update metrics for a browser.
        
        Args:
            browser_id: Browser identifier
            metrics: New metrics
            
        Returns:
            True if updated successfully, False if not found
        """
        if browser_id not in self.browsers:
            return False
        
        try:
            # Update metrics
            self.browser_metrics[browser_id] = metrics
            
            # Update resource metrics
            resource_metrics = ResourceMetrics(
                current_value=metrics.memory_usage_mb,
                peak_value=metrics.memory_usage_mb,  # Would need to track over time
                average_value=metrics.memory_usage_mb,  # Would need to calculate from history
                minimum_value=0.0,
                maximum_value=self.browser_configurations[browser_id].max_memory_mb,
                unit="mb",
                timestamp=datetime.utcnow(),
                samples_count=1,
                trend="stable"
            )
            
            browser = self.browsers[browser_id]
            browser.update_metrics(resource_metrics)
            
            # Check for automatic actions
            await self._check_browser_health(browser_id, metrics)
            
            # Notify callbacks
            self._notify_browser_callbacks(browser_id, metrics)
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to update browser metrics {browser_id}: {str(e)}",
                event_type="browser_metrics_update_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error": str(e)
                },
                component="browser_manager"
            )
            return False
    
    async def record_browser_error(
        self,
        browser_id: str,
        error_message: str
    ) -> bool:
        """
        Record an error for a browser.
        
        Args:
            browser_id: Browser identifier
            error_message: Error message
            
        Returns:
            True if recorded successfully, False if not found
        """
        if browser_id not in self.browsers:
            return False
        
        try:
            # Record error
            self.error_history[browser_id].append(datetime.utcnow())
            
            # Update metrics
            metrics = self.browser_metrics[browser_id]
            metrics.error_count += 1
            
            # Check for automatic restart based on error threshold
            config = self.browser_configurations[browser_id]
            if config.restart_on_error_threshold:
                await self._check_error_threshold(browser_id)
            
            # Publish event
            await publish_resource_event(
                action="error_recorded",
                resource_id=browser_id,
                resource_type=ResourceType.BROWSER.value,
                context={
                    "error_message": error_message,
                    "error_count": metrics.error_count
                },
                component="browser_manager"
            )
            
            self.logger.warning(
                f"Browser error recorded: {browser_id} - {error_message}",
                event_type="browser_error_recorded",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error_message": error_message,
                    "error_count": metrics.error_count
                },
                component="browser_manager"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to record browser error {browser_id}: {str(e)}",
                event_type="browser_error_recording_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error_message": error_message,
                    "error": str(e)
                },
                component="browser_manager"
            )
            return False
    
    async def cleanup_browser_tabs(self, browser_id: str) -> int:
        """
        Clean up idle or excess tabs in a browser.
        
        Args:
            browser_id: Browser identifier
            
        Returns:
            Number of tabs cleaned up
        """
        if browser_id not in self.browsers:
            return 0
        
        try:
            config = self.browser_configurations[browser_id]
            metrics = self.browser_metrics[browser_id]
            
            cleaned_count = 0
            
            # Clean up idle tabs
            if config.cleanup_idle_tabs:
                idle_cleaned = await self._cleanup_idle_tabs(browser_id)
                cleaned_count += idle_cleaned
            
            # Clean up excess tabs
            if metrics.tab_count > config.max_tabs:
                excess_cleaned = await self._cleanup_excess_tabs(browser_id, config.max_tabs)
                cleaned_count += excess_cleaned
            
            if cleaned_count > 0:
                # Update metrics
                metrics.tab_count -= cleaned_count
                
                # Publish event
                await publish_resource_event(
                    action="tabs_cleaned",
                    resource_id=browser_id,
                    resource_type=ResourceType.BROWSER.value,
                    context={
                        "cleaned_count": cleaned_count,
                        "remaining_tabs": metrics.tab_count
                    },
                    component="browser_manager"
                )
                
                self.logger.info(
                    f"Browser tabs cleaned: {browser_id} - {cleaned_count} tabs",
                    event_type="browser_tabs_cleaned",
                    correlation_id=get_correlation_id(),
                    context={
                        "browser_id": browser_id,
                        "cleaned_count": cleaned_count,
                        "remaining_tabs": metrics.tab_count
                    },
                    component="browser_manager"
                )
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(
                f"Failed to cleanup browser tabs {browser_id}: {str(e)}",
                event_type="browser_tab_cleanup_error",
                correlation_id=get_correlation_id(),
                context={
                    "browser_id": browser_id,
                    "error": str(e)
                },
                component="browser_manager"
            )
            return 0
    
    def add_browser_callback(self, callback: Callable[[str, BrowserMetrics], None]) -> None:
        """
        Add a browser metrics callback.
        
        Args:
            callback: Function that receives (browser_id, BrowserMetrics)
        """
        self.browser_callbacks.append(callback)
    
    def remove_browser_callback(self, callback: Callable) -> bool:
        """
        Remove a browser metrics callback.
        
        Args:
            callback: Callback function to remove
            
        Returns:
            True if removed, False if not found
        """
        if callback in self.browser_callbacks:
            self.browser_callbacks.remove(callback)
            return True
        return False
    
    async def _start_browser_instance(self, browser_id: str) -> None:
        """Start a browser instance (placeholder)."""
        # This would contain actual browser initialization logic
        # For now, just update state
        self.browser_states[browser_id] = BrowserState.RUNNING
        
        # Initialize metrics
        metrics = self.browser_metrics[browser_id]
        metrics.state = BrowserState.RUNNING
        metrics.uptime_seconds = 0
        metrics.last_activity = datetime.utcnow()
    
    async def _shutdown_browser_instance(self, browser_id: str) -> None:
        """Shutdown a browser instance (placeholder)."""
        # This would contain actual browser shutdown logic
        # For now, just update state
        pass
    
    async def _restart_browser_instance(self, browser_id: str) -> None:
        """Restart a browser instance (placeholder)."""
        # This would contain actual browser restart logic
        # For now, just update state and start time
        self.browser_start_times[browser_id] = datetime.utcnow()
        
        metrics = self.browser_metrics[browser_id]
        metrics.state = BrowserState.RUNNING
        metrics.uptime_seconds = 0
        metrics.last_activity = datetime.utcnow()
    
    async def _start_browser_monitoring(self, browser_id: str) -> None:
        """Start monitoring for a browser."""
        if browser_id in self.monitoring_tasks:
            return
        
        config = self.browser_configurations[browser_id]
        task = asyncio.create_task(self._monitor_browser(browser_id, config.health_check_interval_seconds))
        self.monitoring_tasks[browser_id] = task
    
    async def _start_browser_cleanup(self, browser_id: str) -> None:
        """Start cleanup task for a browser."""
        if browser_id in self.cleanup_tasks:
            return
        
        config = self.browser_configurations[browser_id]
        task = asyncio.create_task(self._cleanup_browser_loop(browser_id, config.cleanup_interval_minutes))
        self.cleanup_tasks[browser_id] = task
    
    async def _monitor_browser(self, browser_id: str, interval_seconds: int) -> None:
        """Monitor a browser instance."""
        while browser_id in self.browsers:
            try:
                # Get current metrics (placeholder - would get actual browser metrics)
                metrics = await self._get_current_browser_metrics(browser_id)
                
                # Update metrics
                await self.update_browser_metrics(browser_id, metrics)
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error monitoring browser {browser_id}: {str(e)}",
                    event_type="browser_monitoring_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "browser_id": browser_id,
                        "error": str(e)
                    },
                    component="browser_manager"
                )
                await asyncio.sleep(interval_seconds)
    
    async def _cleanup_browser_loop(self, browser_id: str, interval_minutes: int) -> None:
        """Cleanup loop for a browser."""
        while browser_id in self.browsers:
            try:
                # Perform cleanup
                await self.cleanup_browser_tabs(browser_id)
                
                # Wait for next interval
                await asyncio.sleep(interval_minutes * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error in browser cleanup loop {browser_id}: {str(e)}",
                    event_type="browser_cleanup_loop_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "browser_id": browser_id,
                        "error": str(e)
                    },
                    component="browser_manager"
                )
                await asyncio.sleep(interval_minutes * 60)
    
    async def _get_current_browser_metrics(self, browser_id: str) -> BrowserMetrics:
        """Get current browser metrics (placeholder)."""
        # This would contain actual browser metrics collection
        # For now, return placeholder metrics
        start_time = self.browser_start_times.get(browser_id, datetime.utcnow())
        uptime = (datetime.utcnow() - start_time).total_seconds()
        
        return BrowserMetrics(
            state=self.browser_states.get(browser_id, BrowserState.UNKNOWN),
            tab_count=10,  # Placeholder
            active_tab_count=5,  # Placeholder
            memory_usage_mb=512.0,  # Placeholder
            cpu_usage_percent=25.0,  # Placeholder
            page_load_time_avg=2.5,  # Placeholder
            error_count=self.browser_metrics.get(browser_id, BrowserMetrics()).error_count,
            crash_count=self.browser_metrics.get(browser_id, BrowserMetrics()).crash_count,
            uptime_seconds=uptime,
            last_activity=datetime.utcnow()
        )
    
    async def _check_browser_health(self, browser_id: str, metrics: BrowserMetrics) -> None:
        """Check browser health and take action if needed."""
        config = self.browser_configurations[browser_id]
        browser = self.browsers[browser_id]
        
        # Check memory threshold
        if config.restart_on_memory_threshold and metrics.memory_usage_mb > config.max_memory_mb:
            if self._can_restart_browser(browser_id):
                await self.restart_browser(browser_id, "memory_threshold_exceeded")
                return
        
        # Check CPU threshold
        if metrics.cpu_usage_percent > config.max_cpu_percent:
            browser.update_status(ResourceStatus.WARNING)
        else:
            browser.update_status(ResourceStatus.HEALTHY)
        
        # Check for crash
        if metrics.state == BrowserState.CRASHED:
            if config.restart_on_crash and self._can_restart_browser(browser_id):
                await self.restart_browser(browser_id, "browser_crashed")
    
    async def _check_error_threshold(self, browser_id: str) -> None:
        """Check if error threshold is exceeded."""
        config = self.browser_configurations[browser_id]
        error_history = self.error_history[browser_id]
        
        # Count errors in the last hour
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        recent_errors = [error_time for error_time in error_history if error_time >= cutoff_time]
        
        if len(recent_errors) >= config.max_errors_per_hour:
            if self._can_restart_browser(browser_id):
                await self.restart_browser(browser_id, "error_threshold_exceeded")
    
    def _can_restart_browser(self, browser_id: str) -> bool:
        """Check if browser can be restarted (cooldown)."""
        config = self.browser_configurations[browser_id]
        restart_history = self.restart_history[browser_id]
        
        # Check cooldown
        if restart_history:
            last_restart = restart_history[-1]
            time_since_restart = (datetime.utcnow() - last_restart).total_seconds() / 60
            if time_since_restart < config.restart_cooldown_minutes:
                return False
        
        return True
    
    async def _cleanup_idle_tabs(self, browser_id: str) -> int:
        """Clean up idle tabs (placeholder)."""
        # This would contain actual idle tab cleanup logic
        # For now, return placeholder count
        return 2
    
    async def _cleanup_excess_tabs(self, browser_id: str, max_tabs: int) -> int:
        """Clean up excess tabs (placeholder)."""
        # This would contain actual excess tab cleanup logic
        # For now, return placeholder count
        metrics = self.browser_metrics[browser_id]
        excess = metrics.tab_count - max_tabs
        return max(0, excess)
    
    def _notify_browser_callbacks(self, browser_id: str, metrics: BrowserMetrics) -> None:
        """Notify all browser callbacks."""
        for callback in self.browser_callbacks:
            try:
                callback(browser_id, metrics)
            except Exception as e:
                self.logger.error(
                    f"Error in browser callback: {str(e)}",
                    event_type="browser_callback_error",
                    correlation_id=get_correlation_id(),
                    context={
                        "browser_id": browser_id,
                        "error": str(e)
                    },
                    component="browser_manager"
                )


# Global browser manager instance
_browser_manager = BrowserManager()


def get_browser_manager() -> BrowserManager:
    """Get the global browser manager instance."""
    return _browser_manager


async def create_browser(
    browser_id: str,
    configuration: Optional[BrowserConfiguration] = None,
    description: str = ""
) -> bool:
    """Create a browser using the global manager."""
    return await _browser_manager.create_browser(browser_id, configuration, description)


async def get_browser_metrics(browser_id: str) -> Optional[BrowserMetrics]:
    """Get browser metrics using the global manager."""
    return await _browser_manager.get_browser_metrics(browser_id)
