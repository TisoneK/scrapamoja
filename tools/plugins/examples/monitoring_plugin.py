"""
Example monitoring plugin for the plugin system.

This plugin demonstrates how to create a monitoring plugin that can track
plugin performance, system health, and provide real-time insights.
"""

import asyncio
import time
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

from src.sites.base.plugin_interface import (
    BasePlugin, PluginContext, PluginResult, PluginMetadata, 
    PluginType, HookType, register_plugin
)
from src.sites.base.plugin_telemetry import record_metric, get_plugin_telemetry


class MonitoringPlugin(BasePlugin):
    """Example monitoring plugin for system and plugin monitoring."""
    
    def __init__(self):
        """Initialize monitoring plugin."""
        super().__init__()
        
        # Monitoring configuration
        self._monitoring_interval = 30  # seconds
        self._history_size = 1000
        self._alert_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'error_rate': 0.1,
            'response_time': 5000.0  # ms
        }
        
        # Data storage
        self._system_metrics = deque(maxlen=self._history_size)
        self._plugin_metrics = defaultdict(lambda: deque(maxlen=self._history_size))
        self._alerts = deque(maxlen=100)
        self._performance_summary = {}
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task = None
        self._start_time = datetime.utcnow()
        
        # Statistics
        self._stats = {
            'metrics_collected': 0,
            'alerts_generated': 0,
            'monitoring_uptime': 0.0,
            'last_collection': None
        }
    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            id="monitoring_plugin",
            name="System Monitoring Plugin",
            version="1.0.0",
            description="Monitors system performance and plugin health",
            author="Scorewise Team",
            plugin_type=PluginType.MONITORING,
            dependencies=[],
            permissions=["data_access", "system_access"],
            hooks=[
                HookType.BEFORE_SCRAPE,
                HookType.AFTER_SCRAPE,
                HookType.ERROR_OCCURRED,
                HookType.COMPONENT_LOADED
            ],
            configuration_schema={
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "default": True,
                        "description": "Enable monitoring"
                    },
                    "monitoring_interval": {
                        "type": "integer",
                        "default": 30,
                        "minimum": 5,
                        "maximum": 300,
                        "description": "Monitoring interval in seconds"
                    },
                    "alert_thresholds": {
                        "type": "object",
                        "properties": {
                            "cpu_usage": {"type": "number", "minimum": 0, "maximum": 100},
                            "memory_usage": {"type": "number", "minimum": 0, "maximum": 100},
                            "error_rate": {"type": "number", "minimum": 0, "maximum": 1},
                            "response_time": {"type": "number", "minimum": 0}
                        }
                    },
                    "enable_alerts": {
                        "type": "boolean",
                        "default": True,
                        "description": "Enable alert generation"
                    },
                    "history_size": {
                        "type": "integer",
                        "default": 1000,
                        "minimum": 100,
                        "maximum": 10000,
                        "description": "Number of historical data points to keep"
                    }
                }
            },
            tags=["monitoring", "performance", "health", "example"]
        )
    
    async def _on_initialize(self, context: PluginContext) -> bool:
        """Initialize the monitoring plugin."""
        try:
            # Load configuration
            config = context.configuration
            
            self._enabled = config.get('enabled', True)
            self._monitoring_interval = config.get('monitoring_interval', 30)
            self._enable_alerts = config.get('enable_alerts', True)
            self._history_size = config.get('history_size', 1000)
            
            # Update alert thresholds
            alert_thresholds = config.get('alert_thresholds', {})
            self._alert_thresholds.update(alert_thresholds)
            
            # Initialize data structures with new size
            self._system_metrics = deque(maxlen=self._history_size)
            self._plugin_metrics = defaultdict(lambda: deque(maxlen=self._history_size))
            self._alerts = deque(maxlen=100)
            
            # Get system process
            self._process = psutil.Process()
            
            self._logger.info(f"Monitoring plugin initialized - Interval: {self._monitoring_interval}s, Alerts: {self._enable_alerts}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize monitoring plugin: {str(e)}")
            return False
    
    async def _on_execute(self, context: PluginContext, hook_type: HookType, **kwargs) -> PluginResult:
        """Execute the monitoring plugin."""
        if not self._enabled:
            return PluginResult(
                success=True,
                plugin_id=self.metadata.id,
                hook_type=hook_type,
                data={"skipped": True, "reason": "monitoring_disabled"}
            )
        
        try:
            if hook_type == HookType.BEFORE_SCRAPE:
                return await self._monitor_before_scrape(context, **kwargs)
            elif hook_type == HookType.AFTER_SCRAPE:
                return await self._monitor_after_scrape(context, **kwargs)
            elif hook_type == HookType.ERROR_OCCURRED:
                return await self._monitor_error(context, **kwargs)
            elif hook_type == HookType.COMPONENT_LOADED:
                return await self._monitor_component_loaded(context, **kwargs)
            else:
                return PluginResult(
                    success=True,
                    plugin_id=self.metadata.id,
                    hook_type=hook_type,
                    data={"skipped": True, "reason": "unsupported_hook"}
                )
                
        except Exception as e:
            self._logger.error(f"Monitoring plugin execution failed: {str(e)}")
            return PluginResult(
                success=False,
                plugin_id=self.metadata.id,
                hook_type=hook_type,
                errors=[str(e)]
            )
    
    async def _monitor_before_scrape(self, context: PluginContext, **kwargs) -> PluginResult:
        """Monitor before scraping starts."""
        start_time = time.time()
        
        # Collect system metrics
        system_metrics = await self._collect_system_metrics()
        
        # Record metrics
        record_metric(
            self.metadata.id,
            "scrape_start_count",
            1,
            description="Number of scrape operations started"
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return PluginResult(
            success=True,
            plugin_id=self.metadata.id,
            hook_type=HookType.BEFORE_SCRAPE,
            data={
                "system_metrics": system_metrics,
                "scrape_id": kwargs.get('scrape_id'),
                "monitoring_time_ms": execution_time_ms
            },
            execution_time_ms=execution_time_ms
        )
    
    async def _monitor_after_scrape(self, context: PluginContext, **kwargs) -> PluginResult:
        """Monitor after scraping completes."""
        start_time = time.time()
        
        # Collect system metrics
        system_metrics = await self._collect_system_metrics()
        
        # Get scrape results
        scrape_results = kwargs.get('scrape_results', {})
        execution_time = kwargs.get('execution_time_ms', 0)
        
        # Record metrics
        record_metric(
            self.metadata.id,
            "scrape_complete_count",
            1,
            description="Number of scrape operations completed"
        )
        
        record_metric(
            self.metadata.id,
            "scrape_execution_time_ms",
            execution_time,
            description="Scrape execution time"
        )
        
        if scrape_results:
            record_metric(
                self.metadata.id,
                "items_extracted",
                len(scrape_results) if isinstance(scrape_results, (list, dict)) else 1,
                description="Number of items extracted"
            )
        
        # Check for alerts
        alerts = []
        if self._enable_alerts:
            alerts = await self._check_alerts(system_metrics, execution_time)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return PluginResult(
            success=True,
            plugin_id=self.metadata.id,
            hook_type=HookType.AFTER_SCRAPE,
            data={
                "system_metrics": system_metrics,
                "scrape_results": scrape_results,
                "execution_time_ms": execution_time,
                "alerts": alerts,
                "monitoring_time_ms": execution_time_ms
            },
            execution_time_ms=execution_time_ms
        )
    
    async def _monitor_error(self, context: PluginContext, **kwargs) -> PluginResult:
        """Monitor error occurrences."""
        start_time = time.time()
        
        error = kwargs.get('error')
        error_type = kwargs.get('error_type', 'unknown')
        
        # Record error metrics
        record_metric(
            self.metadata.id,
            "error_count",
            1,
            description="Number of errors encountered"
        )
        
        record_metric(
            self.metadata.id,
            f"error_{error_type}_count",
            1,
            description=f"Number of {error_type} errors"
        )
        
        # Collect system metrics during error
        system_metrics = await self._collect_system_metrics()
        
        # Generate alert for error
        if self._enable_alerts:
            alert = {
                'type': 'error',
                'severity': 'high',
                'message': f"Error occurred: {error_type}",
                'details': str(error) if error else 'Unknown error',
                'timestamp': datetime.utcnow().isoformat(),
                'system_metrics': system_metrics
            }
            self._alerts.append(alert)
            self._stats['alerts_generated'] += 1
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return PluginResult(
            success=True,
            plugin_id=self.metadata.id,
            hook_type=HookType.ERROR_OCCURRED,
            data={
                "error_type": error_type,
                "system_metrics": system_metrics,
                "alert_generated": self._enable_alerts,
                "monitoring_time_ms": execution_time_ms
            },
            execution_time_ms=execution_time_ms
        )
    
    async def _monitor_component_loaded(self, context: PluginContext, **kwargs) -> PluginResult:
        """Monitor component loading."""
        start_time = time.time()
        
        component_type = kwargs.get('component_type', 'unknown')
        component_id = kwargs.get('component_id', 'unknown')
        
        # Record component metrics
        record_metric(
            self.metadata.id,
            "component_loaded_count",
            1,
            description="Number of components loaded"
        )
        
        record_metric(
            self.metadata.id,
            f"component_{component_type}_count",
            1,
            description=f"Number of {component_type} components loaded"
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return PluginResult(
            success=True,
            plugin_id=self.metadata.id,
            hook_type=HookType.COMPONENT_LOADED,
            data={
                "component_type": component_type,
                "component_id": component_id,
                "monitoring_time_ms": execution_time_ms
            },
            execution_time_ms=execution_time_ms
        )
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            process_memory = self._process.memory_info()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Process metrics
            process = self._process
            process_cpu = process.cpu_percent()
            process_memory_mb = process_memory.rss / 1024 / 1024
            process_threads = process.num_threads()
            process_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
            
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'process_percent': process_cpu
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'process_mb': process_memory_mb
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'process': {
                    'pid': process.pid,
                    'memory_mb': process_memory_mb,
                    'cpu_percent': process_cpu,
                    'threads': process_threads,
                    'fds': process_fds,
                    'create_time': process.create_time()
                }
            }
            
            # Store in history
            self._system_metrics.append(metrics)
            self._stats['metrics_collected'] += 1
            self._stats['last_collection'] = datetime.utcnow()
            
            # Record to telemetry
            record_metric(
                self.metadata.id,
                "system_cpu_percent",
                cpu_percent,
                unit="%",
                description="System CPU usage percentage"
            )
            
            record_metric(
                self.metadata.id,
                "system_memory_percent",
                memory.percent,
                unit="%",
                description="System memory usage percentage"
            )
            
            record_metric(
                self.metadata.id,
                "process_memory_mb",
                process_memory_mb,
                unit="MB",
                description="Process memory usage in MB"
            )
            
            return metrics
            
        except Exception as e:
            self._logger.error(f"Failed to collect system metrics: {str(e)}")
            return {}
    
    async def _check_alerts(self, system_metrics: Dict[str, Any], 
                          execution_time_ms: float) -> List[Dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []
        
        if not system_metrics:
            return alerts
        
        # CPU alert
        cpu_usage = system_metrics.get('cpu', {}).get('percent', 0)
        if cpu_usage > self._alert_thresholds['cpu_usage']:
            alert = {
                'type': 'performance',
                'severity': 'warning' if cpu_usage < 95 else 'critical',
                'message': f"High CPU usage: {cpu_usage:.1f}%",
                'threshold': self._alert_thresholds['cpu_usage'],
                'current_value': cpu_usage,
                'timestamp': datetime.utcnow().isoformat()
            }
            alerts.append(alert)
            self._alerts.append(alert)
            self._stats['alerts_generated'] += 1
        
        # Memory alert
        memory_usage = system_metrics.get('memory', {}).get('percent', 0)
        if memory_usage > self._alert_thresholds['memory_usage']:
            alert = {
                'type': 'performance',
                'severity': 'warning' if memory_usage < 95 else 'critical',
                'message': f"High memory usage: {memory_usage:.1f}%",
                'threshold': self._alert_thresholds['memory_usage'],
                'current_value': memory_usage,
                'timestamp': datetime.utcnow().isoformat()
            }
            alerts.append(alert)
            self._alerts.append(alert)
            self._stats['alerts_generated'] += 1
        
        # Response time alert
        if execution_time_ms > self._alert_thresholds['response_time']:
            alert = {
                'type': 'performance',
                'severity': 'warning',
                'message': f"Slow response time: {execution_time_ms:.1f}ms",
                'threshold': self._alert_thresholds['response_time'],
                'current_value': execution_time_ms,
                'timestamp': datetime.utcnow().isoformat()
            }
            alerts.append(alert)
            self._alerts.append(alert)
            self._stats['alerts_generated'] += 1
        
        return alerts
    
    async def start_monitoring(self) -> None:
        """Start continuous monitoring."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._logger.info("Continuous monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
        
        self._logger.info("Continuous monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                # Collect metrics
                await self._collect_system_metrics()
                
                # Update monitoring uptime
                uptime = (datetime.utcnow() - self._start_time).total_seconds()
                self._stats['monitoring_uptime'] = uptime
                
                # Wait for next interval
                await asyncio.sleep(self._monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Monitoring loop error: {str(e)}")
                await asyncio.sleep(self._monitoring_interval)
    
    def get_monitoring_data(self, time_range_minutes: int = 60) -> Dict[str, Any]:
        """Get monitoring data for analysis."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_range_minutes)
        
        # Filter system metrics
        recent_system_metrics = [
            m for m in self._system_metrics 
            if datetime.fromisoformat(m['timestamp']) >= cutoff_time
        ]
        
        # Filter alerts
        recent_alerts = [
            a for a in self._alerts 
            if datetime.fromisoformat(a['timestamp']) >= cutoff_time
        ]
        
        # Calculate performance summary
        performance_summary = self._calculate_performance_summary(recent_system_metrics)
        
        return {
            'time_range_minutes': time_range_minutes,
            'system_metrics': recent_system_metrics,
            'alerts': recent_alerts,
            'performance_summary': performance_summary,
            'statistics': self._get_statistics(),
            'monitoring_active': self._monitoring_active,
            'monitoring_interval': self._monitoring_interval
        }
    
    def _calculate_performance_summary(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance summary from metrics."""
        if not metrics:
            return {}
        
        cpu_values = [m.get('cpu', {}).get('percent', 0) for m in metrics]
        memory_values = [m.get('memory', {}).get('percent', 0) for m in metrics]
        process_memory_values = [m.get('process', {}).get('memory_mb', 0) for m in metrics]
        
        return {
            'cpu': {
                'average': sum(cpu_values) / len(cpu_values),
                'min': min(cpu_values),
                'max': max(cpu_values),
                'current': cpu_values[-1] if cpu_values else 0
            },
            'memory': {
                'average': sum(memory_values) / len(memory_values),
                'min': min(memory_values),
                'max': max(memory_values),
                'current': memory_values[-1] if memory_values else 0
            },
            'process_memory': {
                'average': sum(process_memory_values) / len(process_memory_values),
                'min': min(process_memory_values),
                'max': max(process_memory_values),
                'current': process_memory_values[-1] if process_memory_values else 0
            },
            'sample_count': len(metrics),
            'time_span_minutes': len(metrics) * self._monitoring_interval / 60
        }
    
    def _get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        stats = self._stats.copy()
        
        # Add current status
        stats['monitoring_active'] = self._monitoring_active
        stats['monitoring_uptime_hours'] = stats['monitoring_uptime'] / 3600
        stats['alerts_per_hour'] = (
            stats['alerts_generated'] / max(stats['monitoring_uptime'] / 3600, 1)
        )
        stats['metrics_per_hour'] = (
            stats['metrics_collected'] / max(stats['monitoring_uptime'] / 3600, 1)
        )
        
        return stats
    
    async def _on_validate_configuration(self, configuration: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        # Check configuration structure
        if not isinstance(configuration, dict):
            return False
        
        # Validate monitoring interval
        interval = configuration.get('monitoring_interval', 30)
        if not isinstance(interval, int) or interval < 5 or interval > 300:
            return False
        
        # Validate alert thresholds
        thresholds = configuration.get('alert_thresholds', {})
        for key, value in thresholds.items():
            if key in ['cpu_usage', 'memory_usage'] and (not isinstance(value, (int, float)) or value < 0 or value > 100):
                return False
            elif key in ['error_rate'] and (not isinstance(value, (int, float)) or value < 0 or value > 1):
                return False
            elif key in ['response_time'] and (not isinstance(value, (int, float)) or value < 0):
                return False
        
        return True
    
    async def _register_hooks(self) -> None:
        """Register plugin hooks."""
        self.add_hook(HookType.BEFORE_SCRAPE, self._execute)
        self.add_hook(HookType.AFTER_SCRAPE, self._execute)
        self.add_hook(HookType.ERROR_OCCURRED, self._execute)
        self.add_hook(HookType.COMPONENT_LOADED, self._execute)
    
    async def _on_cleanup(self, context: PluginContext) -> bool:
        """Clean up plugin resources."""
        # Stop monitoring
        await self.stop_monitoring()
        
        # Clear data
        self._system_metrics.clear()
        self._plugin_metrics.clear()
        self._alerts.clear()
        
        return True
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Get plugin telemetry data."""
        telemetry = super().get_telemetry()
        
        # Add monitoring-specific telemetry
        telemetry.update({
            'monitoring_statistics': self._get_statistics(),
            'monitoring_active': self._monitoring_active,
            'monitoring_interval': self._monitoring_interval,
            'alert_thresholds': self._alert_thresholds,
            'history_size': self._history_size,
            'current_alerts_count': len(self._alerts),
            'system_metrics_count': len(self._system_metrics),
            'plugin_metrics_count': len(self._plugin_metrics)
        })
        
        return telemetry


# Register the plugin
register_plugin(MonitoringPlugin())


# Convenience function for creating monitoring plugin instances
def create_monitoring_plugin(config: Optional[Dict[str, Any]] = None) -> MonitoringPlugin:
    """Create a monitoring plugin instance with optional configuration."""
    plugin = MonitoringPlugin()
    
    if config:
        # Update plugin configuration
        plugin._config.update(config)
    
    return plugin


# Example usage function
async def example_usage():
    """Example usage of the monitoring plugin."""
    # Create plugin instance
    plugin = create_monitoring_plugin({
        'enabled': True,
        'monitoring_interval': 10,  # 10 seconds for demo
        'enable_alerts': True,
        'alert_thresholds': {
            'cpu_usage': 70.0,
            'memory_usage': 80.0,
            'response_time': 2000.0
        }
    })
    
    # Create mock context
    from src.sites.base.plugin_interface import PluginContext
    context = PluginContext(
        plugin_id="monitoring_plugin",
        plugin_metadata=plugin.metadata,
        framework_context=None,
        configuration=plugin._config
    )
    
    # Initialize plugin
    success = await plugin.initialize(context)
    print(f"Plugin initialized: {success}")
    
    # Start monitoring
    await plugin.start_monitoring()
    print("Monitoring started")
    
    # Simulate some activity
    for i in range(3):
        print(f"\n--- Simulating scrape operation {i+1} ---")
        
        # Before scrape
        result = await plugin.execute(context, HookType.BEFORE_SCRAPE, scrape_id=f"scrape_{i+1}")
        print(f"Before scrape: {result.success}")
        
        # Simulate work
        await asyncio.sleep(2)
        
        # After scrape
        result = await plugin.execute(
            context, 
            HookType.AFTER_SCRAPE,
            scrape_id=f"scrape_{i+1}",
            scrape_results={'title': f'Test Article {i+1}', 'content': f'Content {i+1}'},
            execution_time_ms=1500 + i * 500
        )
        print(f"After scrape: {result.success}")
        
        # Get monitoring data
        monitoring_data = plugin.get_monitoring_data(time_range_minutes=1)
        print(f"Recent metrics: {len(monitoring_data['system_metrics'])} points")
        print(f"Recent alerts: {len(monitoring_data['alerts'])}")
    
    # Stop monitoring
    await plugin.stop_monitoring()
    print("Monitoring stopped")
    
    # Get final statistics
    stats = plugin.get_statistics()
    print(f"Final statistics: {stats}")
    
    # Get telemetry
    telemetry = plugin.get_telemetry()
    print(f"Telemetry: {telemetry['monitoring_statistics']}")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
