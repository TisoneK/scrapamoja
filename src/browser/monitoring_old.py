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
        """Stop monitoring a browser session."""
        if session_id not in self._active_monitors:
            self._logger.warning(
                "monitoring_not_active",
                session_id=session_id
            )
            return
        
        self._logger.info(
            "stopping_resource_monitoring",
            session_id=session_id
        )
        
        task = self._active_monitors.pop(session_id)
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    async def get_current_metrics(self, session_id: str, process_id: int) -> ResourceMetrics:
        """Get current resource metrics for a session."""
        try:
            process = psutil.Process(process_id)
            
            # Get memory info
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Get CPU percent (non-blocking)
            cpu_percent = process.cpu_percent()
            
            # Get memory percent
            memory_percent = process.memory_percent()
            
            # Get other metrics
            try:
                num_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                num_fds = 0
            
            num_threads = process.num_threads()
            
            metrics = ResourceMetrics(
                session_id=session_id,
                process_id=process_id,
                memory_usage_mb=memory_mb,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                open_file_descriptors=num_fds,
                thread_count=num_threads
            )
            
            self._logger.debug(
                "resource_metrics_collected",
                session_id=session_id,
                memory_mb=round(memory_mb, 2),
                cpu_percent=round(cpu_percent, 2),
                memory_percent=round(memory_percent, 2)
            )
            
            return metrics
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self._logger.error(
                "process_monitoring_error",
                session_id=session_id,
                process_id=process_id,
                error=str(e)
            )
            return ResourceMetrics(session_id=session_id)
    
    async def _monitor_loop(self, session_id: str, process_id: int) -> None:
        """Main monitoring loop for a session."""
        self._logger.info(
            "resource_monitor_loop_started",
            session_id=session_id,
            process_id=process_id
        )
        
        try:
            while True:
                metrics = await self.get_current_metrics(session_id, process_id)
                
                # Log metrics at appropriate levels
                if metrics.memory_usage_mb > 500:  # High memory usage
                    self._logger.warning(
                        "high_memory_usage",
                        session_id=session_id,
                        memory_mb=round(metrics.memory_usage_mb, 2)
                    )
                
                if metrics.cpu_percent > 80:  # High CPU usage
                    self._logger.warning(
                        "high_cpu_usage",
                        session_id=session_id,
                        cpu_percent=round(metrics.cpu_percent, 2)
                    )
                
                # Sleep for monitoring interval
                await asyncio.sleep(5)  # 5 second monitoring interval
                
        except asyncio.CancelledError:
            self._logger.info(
                "resource_monitor_loop_cancelled",
                session_id=session_id
            )
            raise
        except Exception as e:
            self._logger.error(
                "resource_monitor_loop_error",
                session_id=session_id,
                error=str(e)
            )
    
    def get_active_sessions(self) -> list[str]:
        """Get list of currently monitored sessions."""
        return list(self._active_monitors.keys())
    
    async def cleanup_all(self) -> None:
        """Stop all active monitoring."""
        self._logger.info(
            "cleaning_up_all_monitors",
            active_count=len(self._active_monitors)
        )
        
        tasks = list(self._active_monitors.items())
        for session_id, task in tasks:
            await self.stop_monitoring(session_id)


# Global resource monitor instance
_resource_monitor = ResourceMonitor()


def get_resource_monitor() -> ResourceMonitor:
    """Get the global resource monitor instance."""
    return _resource_monitor
