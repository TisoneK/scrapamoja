"""
Plugin telemetry and monitoring system.

This module provides comprehensive telemetry collection, monitoring, and analysis
for plugin operations, including performance metrics, health monitoring, and
operational insights.
"""

import asyncio
import time
import threading
import psutil
import json
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import weakref

from .plugin_interface import IPlugin, PluginContext, PluginResult, PluginStatus, HookType


class MetricType(Enum):
    """Metric type enumeration."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class TelemetryLevel(Enum):
    """Telemetry level enumeration."""
    BASIC = "basic"
    STANDARD = "standard"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


@dataclass
class MetricValue:
    """Metric value with metadata."""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None
    description: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics for a plugin."""
    plugin_id: str
    execution_count: int = 0
    total_execution_time_ms: float = 0.0
    average_execution_time_ms: float = 0.0
    min_execution_time_ms: float = float('inf')
    max_execution_time_ms: float = 0.0
    last_execution_time_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0
    timeout_count: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HealthMetrics:
    """Health metrics for a plugin."""
    plugin_id: str
    status: PluginStatus
    uptime_seconds: float = 0.0
    last_activity: Optional[datetime] = None
    error_rate: float = 0.0
    response_time_ms: float = 0.0
    resource_usage: Dict[str, float] = field(default_factory=dict)
    health_score: float = 100.0
    warnings: List[str] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TelemetryReport:
    """Telemetry report for analysis."""
    report_id: str
    plugin_id: Optional[str]
    time_range: Dict[str, datetime]
    performance_metrics: PerformanceMetrics
    health_metrics: HealthMetrics
    custom_metrics: List[MetricValue]
    insights: List[str]
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class PluginTelemetry:
    """Plugin telemetry collector and analyzer."""
    
    def __init__(self, telemetry_level: TelemetryLevel = TelemetryLevel.STANDARD):
        """Initialize plugin telemetry."""
        self.telemetry_level = telemetry_level
        
        # Metrics storage
        self._metrics: Dict[str, List[MetricValue]] = defaultdict(list)
        self._performance_metrics: Dict[str, PerformanceMetrics] = {}
        self._health_metrics: Dict[str, HealthMetrics] = {}
        
        # Time series data
        self._time_series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Aggregation
        self._aggregation_interval = timedelta(minutes=5)
        self._aggregated_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Monitoring
        self._monitoring_active = False
        self._monitoring_interval = timedelta(seconds=30)
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Event listeners
        self._metric_listeners: List[Callable] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'total_metrics': 0,
            'metrics_by_type': {},
            'plugins_monitored': 0,
            'collection_time_ms': 0.0,
            'last_collection': None
        }
        
        # Initialize system monitoring
        self._process = psutil.Process()
    
    def start_monitoring(self) -> None:
        """Start background monitoring."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._monitoring_active = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
    
    def record_metric(self, plugin_id: str, name: str, value: Union[int, float],
                     metric_type: MetricType = MetricType.GAUGE,
                     labels: Optional[Dict[str, str]] = None,
                     unit: Optional[str] = None,
                     description: Optional[str] = None) -> None:
        """
        Record a metric value.
        
        Args:
            plugin_id: Plugin ID
            name: Metric name
            value: Metric value
            metric_type: Metric type
            labels: Metric labels
            unit: Metric unit
            description: Metric description
        """
        metric = MetricValue(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels or {},
            unit=unit,
            description=description
        )
        
        with self._lock:
            # Store metric
            self._metrics[plugin_id].append(metric)
            
            # Update time series
            series_key = f"{plugin_id}:{name}"
            self._time_series[series_key].append({
                'timestamp': metric.timestamp,
                'value': metric.value
            })
            
            # Update statistics
            self._stats['total_metrics'] += 1
            self._stats['metrics_by_type'][metric_type.value] = (
                self._stats['metrics_by_type'].get(metric_type.value, 0) + 1
            )
            
            # Update plugin count
            if plugin_id not in self._performance_metrics:
                self._stats['plugins_monitored'] += 1
        
        # Notify listeners
        self._notify_metric_listeners(metric)
    
    def record_execution(self, plugin_id: str, execution_time_ms: float,
                        success: bool, error: Optional[str] = None) -> None:
        """
        Record plugin execution metrics.
        
        Args:
            plugin_id: Plugin ID
            execution_time_ms: Execution time in milliseconds
            success: Whether execution was successful
            error: Error message if execution failed
        """
        with self._lock:
            # Get or create performance metrics
            if plugin_id not in self._performance_metrics:
                self._performance_metrics[plugin_id] = PerformanceMetrics(plugin_id=plugin_id)
            
            metrics = self._performance_metrics[plugin_id]
            
            # Update execution metrics
            metrics.execution_count += 1
            metrics.total_execution_time_ms += execution_time_ms
            metrics.average_execution_time_ms = (
                metrics.total_execution_time_ms / metrics.execution_count
            )
            metrics.min_execution_time_ms = min(metrics.min_execution_time_ms, execution_time_ms)
            metrics.max_execution_time_ms = max(metrics.max_execution_time_ms, execution_time_ms)
            metrics.last_execution_time_ms = execution_time_ms
            
            if success:
                metrics.success_count += 1
            else:
                metrics.error_count += 1
            
            # Record individual metrics
            self.record_metric(
                plugin_id,
                "execution_time_ms",
                execution_time_ms,
                MetricType.HISTOGRAM,
                unit="ms",
                description="Plugin execution time"
            )
            
            self.record_metric(
                plugin_id,
                "execution_count",
                1,
                MetricType.COUNTER,
                description="Plugin execution count"
            )
            
            if success:
                self.record_metric(
                    plugin_id,
                    "success_count",
                    1,
                    MetricType.COUNTER,
                    description="Plugin success count"
                )
            else:
                self.record_metric(
                    plugin_id,
                    "error_count",
                    1,
                    MetricType.COUNTER,
                    description="Plugin error count"
                )
    
    def update_health_metrics(self, plugin_id: str, status: PluginStatus,
                            resource_usage: Optional[Dict[str, float]] = None,
                            warnings: Optional[List[str]] = None,
                            critical_issues: Optional[List[str]] = None) -> None:
        """
        Update health metrics for a plugin.
        
        Args:
            plugin_id: Plugin ID
            status: Plugin status
            resource_usage: Resource usage data
            warnings: Health warnings
            critical_issues: Critical health issues
        """
        with self._lock:
            # Get or create health metrics
            if plugin_id not in self._health_metrics:
                self._health_metrics[plugin_id] = HealthMetrics(plugin_id=plugin_id)
            
            health = self._health_metrics[plugin_id]
            
            # Update basic metrics
            health.status = status
            health.last_activity = datetime.utcnow()
            health.warnings = warnings or []
            health.critical_issues = critical_issues or []
            
            # Update resource usage
            if resource_usage:
                health.resource_usage.update(resource_usage)
            
            # Calculate health score
            health.health_score = self._calculate_health_score(health)
            
            # Calculate error rate
            if plugin_id in self._performance_metrics:
                perf = self._performance_metrics[plugin_id]
                if perf.execution_count > 0:
                    health.error_rate = perf.error_count / perf.execution_count
            
            # Record health metrics
            self.record_metric(
                plugin_id,
                "health_score",
                health.health_score,
                MetricType.GAUGE,
                unit="score",
                description="Plugin health score"
            )
            
            self.record_metric(
                plugin_id,
                "error_rate",
                health.error_rate,
                MetricType.GAUGE,
                unit="rate",
                description="Plugin error rate"
            )
    
    def get_metrics(self, plugin_id: str, metric_name: Optional[str] = None,
                   since: Optional[datetime] = None,
                   limit: Optional[int] = None) -> List[MetricValue]:
        """
        Get metrics for a plugin.
        
        Args:
            plugin_id: Plugin ID
            metric_name: Optional metric name filter
            since: Optional start time filter
            limit: Optional result limit
            
        Returns:
            List of metric values
        """
        with self._lock:
            metrics = self._metrics.get(plugin_id, [])
            
            # Filter by name
            if metric_name:
                metrics = [m for m in metrics if m.name == metric_name]
            
            # Filter by time
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            
            # Limit results
            if limit:
                metrics = metrics[-limit:]
            
            return metrics.copy()
    
    def get_performance_metrics(self, plugin_id: str) -> Optional[PerformanceMetrics]:
        """Get performance metrics for a plugin."""
        with self._lock:
            return self._performance_metrics.get(plugin_id)
    
    def get_health_metrics(self, plugin_id: str) -> Optional[HealthMetrics]:
        """Get health metrics for a plugin."""
        with self._lock:
            return self._health_metrics.get(plugin_id)
    
    def get_time_series(self, plugin_id: str, metric_name: str,
                       since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get time series data for a metric.
        
        Args:
            plugin_id: Plugin ID
            metric_name: Metric name
            since: Optional start time filter
            
        Returns:
            Time series data
        """
        series_key = f"{plugin_id}:{metric_name}"
        
        with self._lock:
            series = list(self._time_series.get(series_key, []))
            
            # Filter by time
            if since:
                series = [point for point in series if point['timestamp'] >= since]
            
            return series
    
    def generate_report(self, plugin_id: Optional[str] = None,
                       time_range_hours: int = 24) -> TelemetryReport:
        """
        Generate telemetry report.
        
        Args:
            plugin_id: Optional plugin ID filter
            time_range_hours: Time range in hours
            
        Returns:
            Telemetry report
        """
        now = datetime.utcnow()
        time_range = {
            'start': now - timedelta(hours=time_range_hours),
            'end': now
        }
        
        # Collect metrics
        if plugin_id:
            perf_metrics = self.get_performance_metrics(plugin_id) or PerformanceMetrics(plugin_id=plugin_id)
            health_metrics = self.get_health_metrics(plugin_id) or HealthMetrics(plugin_id=plugin_id)
            custom_metrics = self.get_metrics(plugin_id, since=time_range['start'])
        else:
            # Aggregate across all plugins
            perf_metrics = self._aggregate_performance_metrics(time_range['start'])
            health_metrics = self._aggregate_health_metrics(time_range['start'])
            custom_metrics = []
            for pid in list(self._metrics.keys()):
                custom_metrics.extend(self.get_metrics(pid, since=time_range['start']))
        
        # Generate insights and recommendations
        insights = self._generate_insights(perf_metrics, health_metrics, custom_metrics)
        recommendations = self._generate_recommendations(perf_metrics, health_metrics, custom_metrics)
        
        return TelemetryReport(
            report_id=f"telemetry_{int(now.timestamp())}",
            plugin_id=plugin_id,
            time_range=time_range,
            performance_metrics=perf_metrics,
            health_metrics=health_metrics,
            custom_metrics=custom_metrics,
            insights=insights,
            recommendations=recommendations
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get telemetry statistics."""
        with self._lock:
            stats = self._stats.copy()
            
            # Add current monitoring status
            stats['monitoring_active'] = self._monitoring_active
            stats['monitoring_interval_seconds'] = self._monitoring_interval.total_seconds()
            
            # Add metric counts by plugin
            stats['metrics_by_plugin'] = {
                plugin_id: len(metrics) for plugin_id, metrics in self._metrics.items()
            }
            
            # Add time series statistics
            stats['time_series_count'] = len(self._time_series)
            stats['total_time_series_points'] = sum(len(series) for series in self._time_series.values())
            
            return stats
    
    def export_metrics(self, plugin_id: Optional[str] = None,
                       format: str = "json") -> Dict[str, Any]:
        """
        Export metrics data.
        
        Args:
            plugin_id: Optional plugin ID filter
            format: Export format
            
        Returns:
            Exported metrics data
        """
        data = {
            'exported_at': datetime.utcnow().isoformat(),
            'telemetry_level': self.telemetry_level.value,
            'plugins': {}
        }
        
        plugins_to_export = [plugin_id] if plugin_id else list(self._metrics.keys())
        
        for pid in plugins_to_export:
            plugin_data = {
                'metrics': [
                    {
                        'name': m.name,
                        'value': m.value,
                        'type': m.metric_type.value,
                        'timestamp': m.timestamp.isoformat(),
                        'labels': m.labels,
                        'unit': m.unit,
                        'description': m.description
                    }
                    for m in self.get_metrics(pid)
                ],
                'performance_metrics': None,
                'health_metrics': None
            }
            
            # Add performance metrics
            perf = self.get_performance_metrics(pid)
            if perf:
                plugin_data['performance_metrics'] = {
                    'execution_count': perf.execution_count,
                    'total_execution_time_ms': perf.total_execution_time_ms,
                    'average_execution_time_ms': perf.average_execution_time_ms,
                    'min_execution_time_ms': perf.min_execution_time_ms,
                    'max_execution_time_ms': perf.max_execution_time_ms,
                    'last_execution_time_ms': perf.last_execution_time_ms,
                    'success_count': perf.success_count,
                    'error_count': perf.error_count,
                    'timeout_count': perf.timeout_count,
                    'memory_usage_mb': perf.memory_usage_mb,
                    'cpu_usage_percent': perf.cpu_usage_percent,
                    'timestamp': perf.timestamp.isoformat()
                }
            
            # Add health metrics
            health = self.get_health_metrics(pid)
            if health:
                plugin_data['health_metrics'] = {
                    'status': health.status.value,
                    'uptime_seconds': health.uptime_seconds,
                    'last_activity': health.last_activity.isoformat() if health.last_activity else None,
                    'error_rate': health.error_rate,
                    'response_time_ms': health.response_time_ms,
                    'resource_usage': health.resource_usage,
                    'health_score': health.health_score,
                    'warnings': health.warnings,
                    'critical_issues': health.critical_issues,
                    'timestamp': health.timestamp.isoformat()
                }
            
            data['plugins'][pid] = plugin_data
        
        return data
    
    def clear_metrics(self, plugin_id: Optional[str] = None,
                     before: Optional[datetime] = None) -> int:
        """
        Clear metrics data.
        
        Args:
            plugin_id: Optional plugin ID filter
            before: Optional time filter
            
        Returns:
            Number of metrics cleared
        """
        cleared_count = 0
        
        with self._lock:
            if plugin_id:
                # Clear metrics for specific plugin
                if plugin_id in self._metrics:
                    if before:
                        original_count = len(self._metrics[plugin_id])
                        self._metrics[plugin_id] = [
                            m for m in self._metrics[plugin_id] if m.timestamp >= before
                        ]
                        cleared_count = original_count - len(self._metrics[plugin_id])
                    else:
                        cleared_count = len(self._metrics[plugin_id])
                        del self._metrics[plugin_id]
                
                # Clear performance and health metrics
                if plugin_id in self._performance_metrics:
                    del self._performance_metrics[plugin_id]
                
                if plugin_id in self._health_metrics:
                    del self._health_metrics[plugin_id]
                
                # Clear time series
                keys_to_remove = [key for key in self._time_series.keys() if key.startswith(f"{plugin_id}:")]
                for key in keys_to_remove:
                    cleared_count += len(self._time_series[key])
                    del self._time_series[key]
            else:
                # Clear all metrics
                if before:
                    for pid in list(self._metrics.keys()):
                        original_count = len(self._metrics[pid])
                        self._metrics[pid] = [
                            m for m in self._metrics[pid] if m.timestamp >= before
                        ]
                        cleared_count += original_count - len(self._metrics[pid])
                        
                        # Remove empty lists
                        if not self._metrics[pid]:
                            del self._metrics[pid]
                else:
                    for metrics in self._metrics.values():
                        cleared_count += len(metrics)
                    self._metrics.clear()
                    self._performance_metrics.clear()
                    self._health_metrics.clear()
                    self._time_series.clear()
        
        return cleared_count
    
    def add_metric_listener(self, listener: Callable[[MetricValue], None]) -> None:
        """Add a metric listener."""
        self._metric_listeners.append(listener)
    
    def remove_metric_listener(self, listener: Callable[[MetricValue], None]) -> bool:
        """Remove a metric listener."""
        try:
            self._metric_listeners.remove(listener)
            return True
        except ValueError:
            return False
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self._monitoring_interval.total_seconds())
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue monitoring
                pass
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-level metrics."""
        try:
            # Get process metrics
            memory_info = self._process.memory_info()
            cpu_percent = self._process.cpu_percent()
            
            # Record system metrics
            self.record_metric(
                "system",
                "memory_usage_mb",
                memory_info.rss / 1024 / 1024,
                MetricType.GAUGE,
                unit="MB",
                description="System memory usage"
            )
            
            self.record_metric(
                "system",
                "cpu_usage_percent",
                cpu_percent,
                MetricType.GAUGE,
                unit="%",
                description="System CPU usage"
            )
            
            # Update statistics
            self._stats['last_collection'] = datetime.utcnow()
            
        except Exception:
            # Ignore collection errors
            pass
    
    def _calculate_health_score(self, health: HealthMetrics) -> float:
        """Calculate health score for a plugin."""
        score = 100.0
        
        # Deduct for errors
        score -= health.error_rate * 50  # Max 50 points deduction for errors
        
        # Deduct for critical issues
        score -= len(health.critical_issues) * 20  # 20 points per critical issue
        
        # Deduct for warnings
        score -= len(health.warnings) * 5  # 5 points per warning
        
        # Deduct for high resource usage
        for resource, usage in health.resource_usage.items():
            if usage > 90:  # High usage
                score -= 10
            elif usage > 80:  # Medium usage
                score -= 5
        
        return max(0.0, score)
    
    def _aggregate_performance_metrics(self, since: datetime) -> PerformanceMetrics:
        """Aggregate performance metrics across all plugins."""
        total_execution_count = 0
        total_execution_time = 0.0
        total_success_count = 0
        total_error_count = 0
        min_time = float('inf')
        max_time = 0.0
        
        for perf in self._performance_metrics.values():
            total_execution_count += perf.execution_count
            total_execution_time += perf.total_execution_time_ms
            total_success_count += perf.success_count
            total_error_count += perf.error_count
            min_time = min(min_time, perf.min_execution_time_ms)
            max_time = max(max_time, perf.max_execution_time_ms)
        
        return PerformanceMetrics(
            plugin_id="all",
            execution_count=total_execution_count,
            total_execution_time_ms=total_execution_time,
            average_execution_time_ms=total_execution_time / total_execution_count if total_execution_count > 0 else 0,
            min_execution_time_ms=min_time,
            max_execution_time_ms=max_time,
            success_count=total_success_count,
            error_count=total_error_count
        )
    
    def _aggregate_health_metrics(self, since: datetime) -> HealthMetrics:
        """Aggregate health metrics across all plugins."""
        total_plugins = len(self._health_metrics)
        if total_plugins == 0:
            return HealthMetrics(plugin_id="all")
        
        total_health_score = sum(health.health_score for health in self._health_metrics.values())
        avg_health_score = total_health_score / total_plugins
        
        all_warnings = []
        all_critical_issues = []
        
        for health in self._health_metrics.values():
            all_warnings.extend(health.warnings)
            all_critical_issues.extend(health.critical_issues)
        
        return HealthMetrics(
            plugin_id="all",
            health_score=avg_health_score,
            warnings=list(set(all_warnings)),  # Remove duplicates
            critical_issues=list(set(all_critical_issues))  # Remove duplicates
        )
    
    def _generate_insights(self, perf: PerformanceMetrics, health: HealthMetrics,
                          metrics: List[MetricValue]) -> List[str]:
        """Generate insights from metrics."""
        insights = []
        
        # Performance insights
        if perf.execution_count > 0:
            if perf.error_rate > 0.1:  # 10% error rate
                insights.append(f"High error rate detected: {perf.error_rate:.1%}")
            
            if perf.average_execution_time_ms > 1000:  # 1 second
                insights.append(f"Slow average execution time: {perf.average_execution_time_ms:.1f}ms")
            
            if perf.max_execution_time_ms > perf.average_execution_time_ms * 5:
                insights.append("High execution time variance detected")
        
        # Health insights
        if health.health_score < 80:
            insights.append(f"Low health score: {health.health_score:.1f}")
        
        if len(health.critical_issues) > 0:
            insights.append(f"{len(health.critical_issues)} critical issues detected")
        
        # Custom metrics insights
        metric_counts = defaultdict(int)
        for metric in metrics:
            metric_counts[metric.name] += 1
        
        if metric_counts:
            most_common = max(metric_counts.items(), key=lambda x: x[1])
            insights.append(f"Most common metric: {most_common[0]} ({most_common[1]} occurrences)")
        
        return insights
    
    def _generate_recommendations(self, perf: PerformanceMetrics, health: HealthMetrics,
                               metrics: List[MetricValue]) -> List[str]:
        """Generate recommendations from metrics."""
        recommendations = []
        
        # Performance recommendations
        if perf.error_rate > 0.05:  # 5% error rate
            recommendations.append("Investigate and fix frequent errors to improve reliability")
        
        if perf.average_execution_time_ms > 500:  # 500ms
            recommendations.append("Optimize plugin performance to reduce execution time")
        
        # Health recommendations
        if health.health_score < 90:
            recommendations.append("Address health issues to improve plugin stability")
        
        if len(health.warnings) > 5:
            recommendations.append("Review and resolve warnings to prevent future issues")
        
        # Resource recommendations
        for resource, usage in health.resource_usage.items():
            if usage > 85:
                recommendations.append(f"Optimize {resource} usage to prevent resource exhaustion")
        
        return recommendations
    
    def _notify_metric_listeners(self, metric: MetricValue) -> None:
        """Notify metric listeners."""
        for listener in self._metric_listeners:
            try:
                listener(metric)
            except Exception:
                # Don't let listener errors break metric collection
                pass


# Global plugin telemetry instance
_plugin_telemetry = PluginTelemetry()


# Convenience functions
def record_metric(plugin_id: str, name: str, value: Union[int, float],
                metric_type: MetricType = MetricType.GAUGE,
                labels: Optional[Dict[str, str]] = None,
                unit: Optional[str] = None,
                description: Optional[str] = None) -> None:
    """Record a metric value."""
    _plugin_telemetry.record_metric(plugin_id, name, value, metric_type, labels, unit, description)


def record_execution(plugin_id: str, execution_time_ms: float,
                   success: bool, error: Optional[str] = None) -> None:
    """Record plugin execution metrics."""
    _plugin_telemetry.record_execution(plugin_id, execution_time_ms, success, error)


def update_health_metrics(plugin_id: str, status: PluginStatus,
                         resource_usage: Optional[Dict[str, float]] = None,
                         warnings: Optional[List[str]] = None,
                         critical_issues: Optional[List[str]] = None) -> None:
    """Update health metrics for a plugin."""
    _plugin_telemetry.update_health_metrics(plugin_id, status, resource_usage, warnings, critical_issues)


def get_metrics(plugin_id: str, metric_name: Optional[str] = None,
               since: Optional[datetime] = None,
               limit: Optional[int] = None) -> List[MetricValue]:
    """Get metrics for a plugin."""
    return _plugin_telemetry.get_metrics(plugin_id, metric_name, since, limit)


def generate_report(plugin_id: Optional[str] = None,
                   time_range_hours: int = 24) -> TelemetryReport:
    """Generate telemetry report."""
    return _plugin_telemetry.generate_report(plugin_id, time_range_hours)


def get_telemetry_statistics() -> Dict[str, Any]:
    """Get telemetry statistics."""
    return _plugin_telemetry.get_statistics()


def start_monitoring() -> None:
    """Start background monitoring."""
    _plugin_telemetry.start_monitoring()


def stop_monitoring() -> None:
    """Stop background monitoring."""
    _plugin_telemetry.stop_monitoring()


def get_plugin_telemetry() -> PluginTelemetry:
    """Get the global plugin telemetry instance."""
    return _plugin_telemetry
