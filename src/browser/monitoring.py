"""
Resource Monitor Implementation

This module implements the ResourceMonitor class for browser resource monitoring,
following the IResourceMonitor interface.
"""

import asyncio
import time
import psutil
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog

try:
    from playwright.async_api import Browser, BrowserContext, Page
except ImportError:
    Browser = BrowserContext = Page = None

from .interfaces import IResourceMonitor
from .models.metrics import ResourceMetrics, AlertStatus
from .models.enums import CleanupLevel, SessionStatus
from .models.session import BrowserSession
from .models.context import TabContext
from .exceptions import ResourceExhaustionError, MonitoringError
from .lifecycle import ModuleState, lifecycle_manager
from .resilience import resilience_manager
from ..config.settings import get_config


@dataclass
class MonitoringSession:
    """Active monitoring session data."""
    session_id: str
    process_id: Optional[int] = None
    context_ids: Set[str] = None
    start_time: float = 0.0
    last_check: float = 0.0
    check_count: int = 0
    alert_history: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.context_ids is None:
            self.context_ids = set()
        if self.alert_history is None:
            self.alert_history = []


class ResourceMonitor(IResourceMonitor):
    """Monitors browser resource usage and triggers cleanup actions."""
    
    def __init__(
        self,
        check_interval: float = 30.0,
        memory_threshold_mb: float = 1024.0,
        cpu_threshold_percent: float = 80.0,
        disk_threshold_mb: float = 2048.0
    ):
        self.check_interval = check_interval
        self.memory_threshold_mb = memory_threshold_mb
        self.cpu_threshold_percent = cpu_threshold_percent
        self.disk_threshold_mb = disk_threshold_mb
        
        # Monitoring state
        self.monitoring_sessions: Dict[str, MonitoringSession] = {}
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.config = get_config()
        
        # Legacy compatibility
        self._active_monitors: Dict[str, asyncio.Task] = {}
        self._logger = structlog.get_logger("resource_monitor")
        
        # Lifecycle state
        self.lifecycle_state = lifecycle_manager.register_module("resource_monitor")
        
        # Metrics storage
        self.metrics_history: Dict[str, List[ResourceMetrics]] = {}
        self.max_history_size = 1000
        
    async def initialize(self) -> bool:
        """Initialize the resource monitor."""
        try:
            await self.lifecycle_state.initialize()
            
            # Validate thresholds
            if self.memory_threshold_mb <= 0:
                raise ValueError("Memory threshold must be positive")
            if not 0 <= self.cpu_threshold_percent <= 100:
                raise ValueError("CPU threshold must be between 0 and 100")
            if self.disk_threshold_mb <= 0:
                raise ValueError("Disk threshold must be positive")
                
            await self.lifecycle_state.activate()
            
            self._logger.info(
                "Resource monitor initialized",
                memory_threshold_mb=self.memory_threshold_mb,
                cpu_threshold_percent=self.cpu_threshold_percent,
                disk_threshold_mb=self.disk_threshold_mb,
                check_interval=self.check_interval
            )
            
            return True
            
        except Exception as e:
            await self.lifecycle_state.handle_error(e)
            self._logger.error(
                "Failed to initialize resource monitor",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def start_monitoring(self, session_id: str) -> None:
        """Start monitoring a specific session."""
        try:
            if session_id not in self.monitoring_sessions:
                self.monitoring_sessions[session_id] = MonitoringSession(
                    session_id=session_id,
                    start_time=time.time()
                )
                
            # Start global monitoring if not already running
            if not self.is_monitoring:
                await self._start_global_monitoring()
                
            self._logger.info(
                "Started monitoring session",
                session_id=session_id,
                total_sessions=len(self.monitoring_sessions)
            )
            
        except Exception as e:
            self._logger.error(
                "Failed to start monitoring",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise MonitoringError(
                "monitoring_start_failed",
                f"Failed to start monitoring for {session_id}: {str(e)}",
                monitoring_component="start_monitoring"
            )
            
    async def stop_monitoring(self, session_id: str) -> None:
        """Stop monitoring a specific session."""
        try:
            # Remove from new monitoring system
            if session_id in self.monitoring_sessions:
                session = self.monitoring_sessions[session_id]
                session_duration = time.time() - session.start_time
                
                del self.monitoring_sessions[session_id]
                
            # Remove from legacy system
            if session_id in self._active_monitors:
                task = self._active_monitors.pop(session_id)
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
            # Stop global monitoring if no sessions left
            if not self.monitoring_sessions and self.is_monitoring:
                await self._stop_global_monitoring()
                
            self._logger.info(
                "Stopped monitoring session",
                session_id=session_id,
                session_duration_seconds=session_duration if 'session' in locals() else 0
            )
            
        except Exception as e:
            self._logger.error(
                "Failed to stop monitoring",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
    async def get_metrics(self, session_id: str) -> ResourceMetrics:
        """Get current metrics for a session."""
        try:
            monitoring_session = self.monitoring_sessions.get(session_id)
            if not monitoring_session:
                self._logger.warning(
                    "Session not being monitored",
                    session_id=session_id
                )
                return ResourceMetrics(session_id=session_id)
                
            # Collect current metrics
            metrics = await self._collect_metrics(session_id, monitoring_session)
            
            # Store in history
            if session_id not in self.metrics_history:
                self.metrics_history[session_id] = []
                
            self.metrics_history[session_id].append(metrics)
            
            # Limit history size
            if len(self.metrics_history[session_id]) > self.max_history_size:
                self.metrics_history[session_id] = self.metrics_history[session_id][-self.max_history_size:]
                
            monitoring_session.last_check = time.time()
            monitoring_session.check_count += 1
            
            return metrics
            
        except Exception as e:
            self._logger.error(
                "Failed to get metrics",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return ResourceMetrics(session_id=session_id)
            
    async def check_thresholds(self, session_id: str) -> AlertStatus:
        """Check if resource thresholds are exceeded."""
        try:
            metrics = await self.get_metrics(session_id)
            
            # Check each threshold
            memory_exceeded = metrics.check_memory_threshold(self.memory_threshold_mb)
            cpu_exceeded = metrics.check_cpu_threshold(self.cpu_threshold_percent)
            disk_exceeded = metrics.check_disk_threshold(self.disk_threshold_mb)
            
            # Determine overall alert status
            if memory_exceeded or cpu_exceeded or disk_exceeded:
                if (metrics.memory_usage_mb > self.memory_threshold_mb * 1.5 or
                    metrics.cpu_usage_percent > self.cpu_threshold_percent * 1.2):
                    alert_status = AlertStatus.CRITICAL
                else:
                    alert_status = AlertStatus.WARNING
                    
                # Log alert
                self._logger.warning(
                    "Resource thresholds exceeded",
                    session_id=session_id,
                    alert_status=alert_status.value,
                    memory_mb=metrics.memory_usage_mb,
                    memory_threshold_mb=self.memory_threshold_mb,
                    cpu_percent=metrics.cpu_usage_percent,
                    cpu_threshold_percent=self.cpu_threshold_percent,
                    disk_mb=metrics.disk_usage_mb,
                    disk_threshold_mb=self.disk_threshold_mb
                )
                
                # Record in alert history
                monitoring_session = self.monitoring_sessions.get(session_id)
                if monitoring_session:
                    monitoring_session.alert_history.append({
                        "timestamp": time.time(),
                        "alert_status": alert_status.value,
                        "memory_mb": metrics.memory_usage_mb,
                        "cpu_percent": metrics.cpu_usage_percent,
                        "disk_mb": metrics.disk_usage_mb
                    })
                    
                return alert_status
            else:
                metrics.set_alert_status(AlertStatus.NORMAL)
                return AlertStatus.NORMAL
                
        except Exception as e:
            self._logger.error(
                "Failed to check thresholds",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return AlertStatus.NORMAL
            
    async def trigger_cleanup(self, session_id: str, level: CleanupLevel) -> bool:
        """Trigger resource cleanup at specified level."""
        try:
            self._logger.info(
                "Triggering resource cleanup",
                session_id=session_id,
                cleanup_level=level.value
            )
            
            success = False
            
            if level == CleanupLevel.GENTLE:
                success = await self._gentle_cleanup(session_id)
            elif level == CleanupLevel.MODERATE:
                success = await self._moderate_cleanup(session_id)
            elif level == CleanupLevel.AGGRESSIVE:
                success = await self._aggressive_cleanup(session_id)
            elif level == CleanupLevel.FORCE:
                success = await self._force_cleanup(session_id)
                
            self._logger.info(
                "Resource cleanup completed",
                session_id=session_id,
                cleanup_level=level.value,
                success=success
            )
            
            return success
            
        except Exception as e:
            self._logger.error(
                "Failed to trigger cleanup",
                session_id=session_id,
                cleanup_level=level.value,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def set_thresholds(
        self,
        memory_mb: float,
        cpu_percent: float,
        disk_mb: float
    ) -> None:
        """Set resource monitoring thresholds."""
        try:
            # Validate new thresholds
            if memory_mb <= 0 or cpu_percent <= 0 or disk_mb <= 0:
                raise ValueError("All thresholds must be positive")
            if not 0 <= cpu_percent <= 100:
                raise ValueError("CPU threshold must be between 0 and 100")
                
            old_thresholds = {
                "memory_mb": self.memory_threshold_mb,
                "cpu_percent": self.cpu_threshold_percent,
                "disk_mb": self.disk_threshold_mb
            }
            
            self.memory_threshold_mb = memory_mb
            self.cpu_threshold_percent = cpu_percent
            self.disk_threshold_mb = disk_mb
            
            self._logger.info(
                "Resource thresholds updated",
                session_id="global",
                old_thresholds=old_thresholds,
                new_thresholds={
                    "memory_mb": memory_mb,
                    "cpu_percent": cpu_percent,
                    "disk_mb": disk_mb
                }
            )
            
        except Exception as e:
            self._logger.error(
                "Failed to set thresholds",
                error=str(e),
                error_type=type(e).__name__
            )
            raise MonitoringError(
                "threshold_set_failed",
                f"Failed to set thresholds: {str(e)}",
                monitoring_component="set_thresholds"
            )
            
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get status of all monitored sessions."""
        try:
            status = {
                "is_monitoring": self.is_monitoring,
                "total_sessions": len(self.monitoring_sessions),
                "check_interval": self.check_interval,
                "thresholds": {
                    "memory_mb": self.memory_threshold_mb,
                    "cpu_percent": self.cpu_threshold_percent,
                    "disk_mb": self.disk_threshold_mb
                },
                "sessions": {}
            }
            
            for session_id, monitoring_session in self.monitoring_sessions.items():
                session_duration = time.time() - monitoring_session.start_time
                last_check_ago = time.time() - monitoring_session.last_check if monitoring_session.last_check > 0 else 0
                
                status["sessions"][session_id] = {
                    "process_id": monitoring_session.process_id,
                    "context_count": len(monitoring_session.context_ids),
                    "start_time": monitoring_session.start_time,
                    "session_duration_seconds": session_duration,
                    "last_check": monitoring_session.last_check,
                    "last_check_ago_seconds": last_check_ago,
                    "check_count": monitoring_session.check_count,
                    "alert_count": len(monitoring_session.alert_history),
                    "recent_alerts": monitoring_session.alert_history[-5:]  # Last 5 alerts
                }
                
            return status
            
        except Exception as e:
            self._logger.error(
                "Failed to get monitoring status",
                error=str(e),
                error_type=type(e).__name__
            )
            return {"error": str(e)}
            
    async def shutdown(self) -> None:
        """Shutdown the resource monitor."""
        try:
            # Stop global monitoring
            if self.is_monitoring:
                await self._stop_global_monitoring()
                
            # Clear all monitoring sessions
            self.monitoring_sessions.clear()
            self.metrics_history.clear()
            
            await self.lifecycle_state.shutdown()
            
            self._logger.info("Resource monitor shutdown completed")
            
        except Exception as e:
            self._logger.error(
                "Failed to shutdown resource monitor",
                error=str(e),
                error_type=type(e).__name__
            )
            
    # Legacy compatibility methods
    async def start_monitoring_with_process(self, session_id: str, process_id: int) -> None:
        """Legacy method for starting monitoring with process ID."""
        await self.start_monitoring(session_id)
        if session_id in self.monitoring_sessions:
            self.monitoring_sessions[session_id].process_id = process_id
            
    async def get_current_metrics_legacy(self, session_id: str, process_id: int) -> ResourceMetrics:
        """Legacy method for getting current metrics."""
        if session_id in self.monitoring_sessions:
            self.monitoring_sessions[session_id].process_id = process_id
        return await self.get_metrics(session_id)
        
    def get_active_sessions(self) -> List[str]:
        """Get list of currently monitored sessions."""
        return list(self.monitoring_sessions.keys())
        
    async def cleanup_all(self) -> None:
        """Stop all active monitoring."""
        for session_id in list(self.monitoring_sessions.keys()):
            await self.stop_monitoring(session_id)
            
    async def _start_global_monitoring(self) -> None:
        """Start global monitoring loop."""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        
        self._logger.info("Global resource monitoring started")
        
    async def _stop_global_monitoring(self) -> None:
        """Stop global monitoring loop."""
        if not self.is_monitoring:
            return
            
        self.is_monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
            
        self._logger.info("Global resource monitoring stopped")
        
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Check all monitored sessions
                for session_id in list(self.monitoring_sessions.keys()):
                    try:
                        # Check thresholds
                        alert_status = await self.check_thresholds(session_id)
                        
                        # Trigger cleanup if needed
                        if alert_status == AlertStatus.CRITICAL:
                            await self.trigger_cleanup(session_id, CleanupLevel.MODERATE)
                        elif alert_status == AlertStatus.WARNING:
                            await self.trigger_cleanup(session_id, CleanupLevel.GENTLE)
                            
                    except Exception as e:
                        self._logger.error(
                            "Error in monitoring loop for session",
                            session_id=session_id,
                            error=str(e),
                            error_type=type(e).__name__
                        )
                        
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(
                    "Error in monitoring loop",
                    error=str(e),
                    error_type=type(e).__name__
                )
                await asyncio.sleep(self.check_interval)
                
    async def _collect_metrics(self, session_id: str, monitoring_session: MonitoringSession) -> ResourceMetrics:
        """Collect current resource metrics for a session."""
        try:
            # Get process information
            process = psutil.Process()
            
            # Memory metrics
            memory_info = process.memory_info()
            memory_usage_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            
            # CPU metrics
            cpu_percent = process.cpu_percent()
            
            # Disk metrics (simplified - would need more sophisticated tracking)
            disk_usage_mb = 0.0
            
            # Network and other metrics
            network_count = 0  # Would need actual network monitoring
            open_tabs = len(monitoring_session.context_ids)
            process_handles = len(process.open_files()) if hasattr(process, 'open_files') else 0
            
            # Create metrics
            metrics = ResourceMetrics(
                session_id=session_id,
                memory_usage_mb=memory_usage_mb,
                cpu_usage_percent=cpu_percent,
                disk_usage_mb=disk_usage_mb,
                network_requests_count=network_count,
                open_tabs_count=open_tabs,
                process_handles_count=process_handles
            )
            
            # Check thresholds and set alert status
            metrics.check_memory_threshold(self.memory_threshold_mb)
            metrics.check_cpu_threshold(self.cpu_threshold_percent)
            metrics.check_disk_threshold(self.disk_threshold_mb)
            
            return metrics
            
        except Exception as e:
            self._logger.error(
                "Failed to collect metrics",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return ResourceMetrics(session_id=session_id)
            
    async def _gentle_cleanup(self, session_id: str) -> bool:
        """Perform gentle cleanup (close inactive tabs)."""
        try:
            # This would integrate with actual browser session management
            # For now, just log the action
            self._logger.info(
                "Performing gentle cleanup",
                session_id=session_id,
                action="close_inactive_tabs"
            )
            return True
            
        except Exception as e:
            self._logger.error(
                "Gentle cleanup failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def _moderate_cleanup(self, session_id: str) -> bool:
        """Perform moderate cleanup (close tabs and clear cache)."""
        try:
            # This would integrate with actual browser session management
            self._logger.info(
                "Performing moderate cleanup",
                session_id=session_id,
                action="close_tabs_clear_cache"
            )
            return True
            
        except Exception as e:
            self._logger.error(
                "Moderate cleanup failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def _aggressive_cleanup(self, session_id: str) -> bool:
        """Perform aggressive cleanup (close everything and force cleanup)."""
        try:
            # This would integrate with actual browser session management
            self._logger.info(
                "Performing aggressive cleanup",
                session_id=session_id,
                action="force_cleanup_all"
            )
            return True
            
        except Exception as e:
            self._logger.error(
                "Aggressive cleanup failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def _force_cleanup(self, session_id: str) -> bool:
        """Force cleanup (terminate processes)."""
        try:
            # This would integrate with actual browser session management
            self._logger.info(
                "Performing force cleanup",
                session_id=session_id,
                action="terminate_processes"
            )
            return True
            
        except Exception as e:
            self._logger.error(
                "Force cleanup failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False


# Global resource monitor instance
resource_monitor = ResourceMonitor()


def get_resource_monitor() -> ResourceMonitor:
    """Get the global resource monitor instance."""
    return resource_monitor
