"""
Telemetry system lifecycle management.

This module provides comprehensive lifecycle management for the telemetry system
including initialization, startup, shutdown, and health monitoring.
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
import signal
import weakref

from ..interfaces.storage import ITelemetryStorage
from ..interfaces.collector import ITelemetryCollector
from ..interfaces.processor import ITelemetryProcessor
from ..interfaces.alert_engine import IAlertEngine
from ..interfaces.report_generator import IReportGenerator
from ..configuration.telemetry_config import TelemetryConfiguration
from ..configuration.validation import validate_configuration, apply_corrections
from ..error_handling import get_error_handler, ErrorContext
from ..optimization import get_performance_optimizer
from ..exceptions import TelemetryError, TelemetryConfigurationError

logger = logging.getLogger(__name__)


class SystemState(Enum):
    """Telemetry system states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class HealthStatus:
    """System health status."""
    healthy: bool
    component_status: Dict[str, bool] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    uptime_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    error_rate: float = 0.0


@dataclass
class LifecycleMetrics:
    """Lifecycle operation metrics."""
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    restart_count: int = 0
    last_restart: Optional[datetime] = None


class TelemetryLifecycleManager:
    """Manages telemetry system lifecycle."""
    
    def __init__(self):
        self.state = SystemState.UNINITIALIZED
        self.config: Optional[TelemetryConfiguration] = None
        self.components: Dict[str, Any] = {}
        self.health_status = HealthStatus(healthy=False)
        self.metrics = LifecycleMetrics()
        self._shutdown_event = asyncio.Event()
        self._health_check_task: Optional[asyncio.Task] = None
        self._startup_time: Optional[datetime] = None
        self._lock = asyncio.Lock()
        
        # Component dependencies
        self._component_order = [
            'storage',
            'collector', 
            'processor',
            'alert_engine',
            'report_generator'
        ]
        
        # Register signal handlers for graceful shutdown
        self._register_signal_handlers()
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize telemetry system with configuration."""
        async with self._lock:
            if self.state != SystemState.UNINITIALIZED:
                logger.warning(f"System already initialized, current state: {self.state}")
                return False
            
            self.state = SystemState.INITIALIZING
            
            try:
                # Validate and apply configuration
                validation_result = validate_configuration(config)
                if not validation_result.is_valid:
                    logger.error(f"Configuration validation failed: {validation_result.errors}")
                    self.state = SystemState.ERROR
                    return False
                
                # Apply automatic corrections
                corrected_config = apply_corrections(config, validation_result)
                if validation_result.corrected_values:
                    logger.info(f"Applied {len(validation_result.corrected_values)} configuration corrections")
                
                # Create configuration object
                self.config = TelemetryConfiguration.from_dict(corrected_config)
                
                # Initialize error handler
                error_handler = get_error_handler()
                
                # Initialize performance optimizer
                perf_optimizer = get_performance_optimizer()
                await perf_optimizer.start()
                
                # Initialize components in dependency order
                await self._initialize_components()
                
                # Update health status
                await self._update_health_status()
                
                self.state = SystemState.READY
                logger.info("Telemetry system initialized successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize telemetry system: {e}")
                self.state = SystemState.ERROR
                await self._cleanup_on_error()
                return False
    
    async def start(self) -> bool:
        """Start telemetry system."""
        async with self._lock:
            if self.state != SystemState.READY:
                logger.error(f"Cannot start system in state: {self.state}")
                return False
            
            self.state = SystemState.STARTING
            self._startup_time = datetime.now(timezone.utc)
            self.metrics.start_time = self._startup_time
            
            try:
                # Start components in dependency order
                await self._start_components()
                
                # Start health monitoring
                self._health_check_task = asyncio.create_task(self._health_check_loop())
                
                self.state = SystemState.RUNNING
                logger.info("Telemetry system started successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start telemetry system: {e}")
                self.state = SystemState.ERROR
                await self._stop_components()
                return False
    
    async def stop(self, graceful: bool = True) -> bool:
        """Stop telemetry system."""
        async with self._lock:
            if self.state not in [SystemState.RUNNING, SystemState.STARTING]:
                logger.warning(f"System not running, current state: {self.state}")
                return False
            
            self.state = SystemState.STOPPING
            self.metrics.stop_time = datetime.now(timezone.utc)
            
            try:
                # Stop health monitoring
                if self._health_check_task:
                    self._health_check_task.cancel()
                    try:
                        await self._health_check_task
                    except asyncio.CancelledError:
                        pass
                
                # Stop components in reverse dependency order
                await self._stop_components(graceful)
                
                self.state = SystemState.STOPPED
                logger.info("Telemetry system stopped successfully")
                return True
                
            except Exception as e:
                logger.error(f"Error during system stop: {e}")
                self.state = SystemState.ERROR
                return False
    
    async def shutdown(self) -> None:
        """Shutdown telemetry system completely."""
        async with self._lock:
            if self.state == SystemState.SHUTDOWN:
                return
            
            logger.info("Shutting down telemetry system")
            
            # Stop if running
            if self.state == SystemState.RUNNING:
                await self.stop()
            
            # Cleanup components
            await self._cleanup_components()
            
            # Stop performance optimizer
            perf_optimizer = get_performance_optimizer()
            await perf_optimizer.stop()
            
            # Clear error handler
            error_handler = get_error_handler()
            await error_handler.clear_old_errors(0)
            
            self.state = SystemState.SHUTDOWN
            logger.info("Telemetry system shutdown complete")
    
    async def restart(self) -> bool:
        """Restart telemetry system."""
        logger.info("Restarting telemetry system")
        
        if self.state == SystemState.RUNNING:
            await self.stop()
        
        self.metrics.restart_count += 1
        self.metrics.last_restart = datetime.now(timezone.utc)
        
        return await self.start()
    
    async def get_health_status(self) -> HealthStatus:
        """Get current system health status."""
        await self._update_health_status()
        return self.health_status
    
    async def get_system_metrics(self) -> LifecycleMetrics:
        """Get system lifecycle metrics."""
        # Update uptime if running
        if self.state == SystemState.RUNNING and self.metrics.start_time:
            self.metrics.uptime_seconds = (
                datetime.now(timezone.utc) - self.metrics.start_time
            ).total_seconds()
        
        return self.metrics
    
    def get_state(self) -> SystemState:
        """Get current system state."""
        return self.state
    
    async def _initialize_components(self) -> None:
        """Initialize all components."""
        for component_name in self._component_order:
            try:
                component = await self._create_component(component_name)
                if component:
                    await self._initialize_component(component_name, component)
                    self.components[component_name] = component
                    logger.info(f"Initialized component: {component_name}")
                else:
                    raise TelemetryError(f"Failed to create component: {component_name}")
                    
            except Exception as e:
                logger.error(f"Failed to initialize component {component_name}: {e}")
                raise
    
    async def _create_component(self, component_name: str) -> Optional[Any]:
        """Create component instance based on configuration."""
        if component_name == 'storage':
            storage_type = self.config.storage.type
            if storage_type == 'json':
                from ..storage.json_storage import JSONStorage
                return JSONStorage(self.config.storage.directory)
            elif storage_type == 'influxdb':
                from ..storage.influxdb_storage import InfluxDBStorage
                return InfluxDBStorage(
                    url=self.config.storage.influxdb.url,
                    token=self.config.storage.influxdb.token,
                    org=self.config.storage.influxdb.org,
                    bucket=self.config.storage.influxdb.bucket
                )
        
        elif component_name == 'collector':
            from ..collector.metrics_collector import MetricsCollector
            return MetricsCollector(self.components['storage'])
        
        elif component_name == 'processor':
            from ..processor.batch_processor import BatchProcessor
            return BatchProcessor(self.components['storage'])
        
        elif component_name == 'alert_engine':
            from ..alerting.alert_engine import AlertEngine
            return AlertEngine(self.config.alerting)
        
        elif component_name == 'report_generator':
            from ..reporting.report_generator import ReportGenerator
            return ReportGenerator(self.components['storage'])
        
        return None
    
    async def _initialize_component(self, component_name: str, component: Any) -> None:
        """Initialize individual component."""
        if hasattr(component, 'initialize'):
            await component.initialize()
    
    async def _start_components(self) -> None:
        """Start all components."""
        for component_name in self._component_order:
            if component_name in self.components:
                component = self.components[component_name]
                try:
                    if hasattr(component, 'start'):
                        await component.start()
                    logger.info(f"Started component: {component_name}")
                except Exception as e:
                    logger.error(f"Failed to start component {component_name}: {e}")
                    raise
    
    async def _stop_components(self, graceful: bool = True) -> None:
        """Stop all components in reverse order."""
        for component_name in reversed(self._component_order):
            if component_name in self.components:
                component = self.components[component_name]
                try:
                    if hasattr(component, 'stop'):
                        if graceful and hasattr(component, 'stop_gracefully'):
                            await component.stop_gracefully()
                        else:
                            await component.stop()
                    logger.info(f"Stopped component: {component_name}")
                except Exception as e:
                    logger.error(f"Error stopping component {component_name}: {e}")
    
    async def _cleanup_components(self) -> None:
        """Cleanup all components."""
        for component_name in self._component_order:
            if component_name in self.components:
                component = self.components[component_name]
                try:
                    if hasattr(component, 'close'):
                        await component.close()
                    elif hasattr(component, 'cleanup'):
                        await component.cleanup()
                    logger.info(f"Cleaned up component: {component_name}")
                except Exception as e:
                    logger.error(f"Error cleaning up component {component_name}: {e}")
        
        self.components.clear()
    
    async def _cleanup_on_error(self) -> None:
        """Cleanup after initialization error."""
        await self._cleanup_components()
        
        perf_optimizer = get_performance_optimizer()
        await perf_optimizer.stop()
    
    async def _update_health_status(self) -> None:
        """Update system health status."""
        try:
            # Check component health
            component_status = {}
            issues = []
            
            for name, component in self.components.items():
                try:
                    if hasattr(component, 'is_healthy'):
                        healthy = await component.is_healthy()
                    else:
                        healthy = True  # Assume healthy if no health check
                    
                    component_status[name] = healthy
                    
                    if not healthy:
                        issues.append(f"Component {name} is unhealthy")
                        
                except Exception as e:
                    component_status[name] = False
                    issues.append(f"Health check failed for {name}: {e}")
            
            # Calculate error rate
            error_handler = get_error_handler()
            error_summary = await error_handler.get_error_summary()
            error_rate = error_summary.get('recovery_rate', 1.0)
            
            # Get memory usage
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_usage_mb = process.memory_info().rss / 1024 / 1024
            
            # Update health status
            self.health_status = HealthStatus(
                healthy=len(issues) == 0,
                component_status=component_status,
                issues=issues,
                last_check=datetime.now(timezone.utc),
                uptime_seconds=self.metrics.uptime_seconds,
                memory_usage_mb=memory_usage_mb,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"Failed to update health status: {e}")
            self.health_status.healthy = False
            self.health_status.issues.append(f"Health check failed: {e}")
    
    async def _health_check_loop(self) -> None:
        """Background health monitoring loop."""
        while self.state == SystemState.RUNNING:
            try:
                await self._update_health_status()
                
                # Log health status if unhealthy
                if not self.health_status.healthy:
                    logger.warning(f"System health issues detected: {self.health_status.issues}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            asyncio.create_task(self.shutdown())
        
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except ValueError:
            # Signals not available in all environments
            pass


# Global lifecycle manager instance
_lifecycle_manager = None


def get_lifecycle_manager() -> TelemetryLifecycleManager:
    """Get global lifecycle manager instance."""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = TelemetryLifecycleManager()
    return _lifecycle_manager


@asynccontextmanager
async def telemetry_system(config: Dict[str, Any]):
    """Context manager for telemetry system lifecycle."""
    manager = get_lifecycle_manager()
    
    try:
        # Initialize and start
        await manager.initialize(config)
        await manager.start()
        
        yield manager
        
    finally:
        # Shutdown
        await manager.shutdown()


async def ensure_system_running() -> bool:
    """Ensure telemetry system is running."""
    manager = get_lifecycle_manager()
    
    if manager.state == SystemState.RUNNING:
        return True
    
    if manager.state == SystemState.READY:
        return await manager.start()
    
    logger.error(f"Cannot ensure system running, current state: {manager.state}")
    return False
