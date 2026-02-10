"""
Performance monitoring for component loading and execution.

This module provides comprehensive performance monitoring capabilities for
components, including loading times, execution metrics, memory usage,
and performance optimization recommendations.
"""

import time
import threading
import psutil
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import weakref
import json

from .component_interface import IComponent, ComponentContext, ComponentResult


class PerformanceMetricType(Enum):
    """Performance metric type enumeration."""
    LOADING_TIME = "loading_time"
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    CACHE_HIT_RATE = "cache_hit_rate"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    CONCURRENCY = "concurrency"


class PerformanceLevel(Enum):
    """Performance level enumeration."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Performance metric data point."""
    component_id: str
    metric_type: PerformanceMetricType
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentPerformanceProfile:
    """Performance profile for a component."""
    component_id: str
    loading_time_ms: float = 0.0
    average_execution_time_ms: float = 0.0
    min_execution_time_ms: float = float('inf')
    max_execution_time_ms: float = 0.0
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0
    throughput_per_second: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    performance_level: PerformanceLevel = PerformanceLevel.EXCELLENT
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PerformanceAlert:
    """Performance alert notification."""
    alert_id: str
    component_id: str
    alert_type: str
    severity: str
    message: str
    threshold: float
    current_value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComponentPerformanceMonitor:
    """Performance monitor for components."""
    
    def __init__(self, monitoring_interval: float = 30.0):
        """Initialize the performance monitor."""
        self.monitoring_interval = monitoring_interval
        
        # Performance data storage
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._profiles: Dict[str, ComponentPerformanceProfile] = {}
        self._alerts: deque = deque(maxlen=100)
        
        # Performance thresholds
        self._thresholds = {
            PerformanceMetricType.LOADING_TIME: 1000.0,  # ms
            PerformanceMetricType.EXECUTION_TIME: 500.0,  # ms
            PerformanceMetricType.MEMORY_USAGE: 100.0,  # MB
            PerformanceMetricType.CPU_USAGE: 80.0,  # %
            PerformanceMetricType.ERROR_RATE: 0.05,  # 5%
            PerformanceMetricType.CACHE_HIT_RATE: 0.8,  # 80%
        }
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._lock = threading.RLock()
        
        # Event listeners
        self._metric_listeners: List[Callable] = []
        self._alert_listeners: List[Callable] = []
        
        # Statistics
        self._stats = {
            'total_metrics': 0,
            'total_alerts': 0,
            'monitoring_uptime': 0.0,
            'components_monitored': 0,
            'last_collection': None
        }
        
        # Process monitoring
        self._process = psutil.Process()
        self._start_time = datetime.utcnow()
    
    def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                await self._collect_system_metrics()
                await self._update_performance_profiles()
                await self._check_performance_alerts()
                
                # Update statistics
                self._stats['monitoring_uptime'] = (datetime.utcnow() - self._start_time).total_seconds()
                self._stats['last_collection'] = datetime.utcnow()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue monitoring
                print(f"Monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    def record_component_loading(self, component_id: str, loading_time_ms: float) -> None:
        """Record component loading time."""
        metric = PerformanceMetric(
            component_id=component_id,
            metric_type=PerformanceMetricType.LOADING_TIME,
            value=loading_time_ms,
            unit="ms",
            metadata={"operation": "component_loading"}
        )
        
        self._add_metric(metric)
        
        # Update profile
        with self._lock:
            if component_id not in self._profiles:
                self._profiles[component_id] = ComponentPerformanceProfile(component_id=component_id)
            
            self._profiles[component_id].loading_time_ms = loading_time_ms
            self._profiles[component_id].last_updated = datetime.utcnow()
    
    def record_component_execution(self, component_id: str, execution_time_ms: float,
                                  success: bool, memory_usage_mb: Optional[float] = None) -> None:
        """Record component execution metrics."""
        # Record execution time
        execution_metric = PerformanceMetric(
            component_id=component_id,
            metric_type=PerformanceMetricType.EXECUTION_TIME,
            value=execution_time_ms,
            unit="ms",
            metadata={"success": success}
        )
        self._add_metric(execution_metric)
        
        # Record memory usage if provided
        if memory_usage_mb is not None:
            memory_metric = PerformanceMetric(
                component_id=component_id,
                metric_type=PerformanceMetricType.MEMORY_USAGE,
                value=memory_usage_mb,
                unit="MB",
                metadata={"operation": "execution"}
            )
            self._add_metric(memory_metric)
        
        # Update profile
        with self._lock:
            if component_id not in self._profiles:
                self._profiles[component_id] = ComponentPerformanceProfile(component_id=component_id)
            
            profile = self._profiles[component_id]
            profile.total_executions += 1
            
            if success:
                profile.successful_executions += 1
            else:
                profile.failed_executions += 1
            
            # Update execution time statistics
            profile.average_execution_time_ms = (
                (profile.average_execution_time_ms * (profile.total_executions - 1) + execution_time_ms) /
                profile.total_executions
            )
            profile.min_execution_time_ms = min(profile.min_execution_time_ms, execution_time_ms)
            profile.max_execution_time_ms = max(profile.max_execution_time_ms, execution_time_ms)
            
            # Update error rate
            profile.error_rate = profile.failed_executions / profile.total_executions
            
            # Update memory usage
            if memory_usage_mb is not None:
                profile.memory_usage_mb = memory_usage_mb
            
            profile.last_updated = datetime.utcnow()
    
    def record_cache_hit(self, component_id: str, hit: bool) -> None:
        """Record cache hit/miss for component."""
        # This would be called by the caching system
        pass  # Implementation would require integration with cache system
    
    def get_component_profile(self, component_id: str) -> Optional[ComponentPerformanceProfile]:
        """Get performance profile for a component."""
        with self._lock:
            return self._profiles.get(component_id)
    
    def get_all_profiles(self) -> Dict[str, ComponentPerformanceProfile]:
        """Get all component performance profiles."""
        with self._lock:
            return self._profiles.copy()
    
    def get_metrics(self, component_id: Optional[str] = None,
                   metric_type: Optional[PerformanceMetricType] = None,
                   since: Optional[datetime] = None) -> List[PerformanceMetric]:
        """Get performance metrics."""
        metrics = []
        
        with self._lock:
            if component_id:
                if component_id in self._metrics:
                    component_metrics = list(self._metrics[component_id])
                    
                    if metric_type:
                        component_metrics = [m for m in component_metrics if m.metric_type == metric_type]
                    
                    if since:
                        component_metrics = [m for m in component_metrics if m.timestamp >= since]
                    
                    metrics.extend(component_metrics)
            else:
                for comp_id, comp_metrics in self._metrics.items():
                    if metric_type:
                        comp_metrics = [m for m in comp_metrics if m.metric_type == metric_type]
                    
                    if since:
                        comp_metrics = [m for m in comp_metrics if m.timestamp >= since]
                    
                    metrics.extend(comp_metrics)
        
        return metrics
    
    def get_alerts(self, component_id: Optional[str] = None,
                  severity: Optional[str] = None,
                  since: Optional[datetime] = None) -> List[PerformanceAlert]:
        """Get performance alerts."""
        alerts = list(self._alerts)
        
        if component_id:
            alerts = [a for a in alerts if a.component_id == component_id]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if since:
            alerts = [a for a in alerts if a.timestamp >= since]
        
        return alerts
    
    def set_threshold(self, metric_type: PerformanceMetricType, threshold: float) -> None:
        """Set performance threshold for a metric type."""
        self._thresholds[metric_type] = threshold
    
    def get_threshold(self, metric_type: PerformanceMetricType) -> float:
        """Get performance threshold for a metric type."""
        return self._thresholds.get(metric_type, float('inf'))
    
    def get_performance_summary(self, component_id: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary."""
        with self._lock:
            profiles = self._profiles if component_id is None else {component_id: self._profiles.get(component_id)}
            
            summary = {
                "total_components": len(profiles),
                "performance_levels": {},
                "average_metrics": {},
                "recommendations": [],
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Count performance levels
            level_counts = defaultdict(int)
            total_metrics = defaultdict(list)
            
            for profile in profiles.values():
                if profile:
                    level_counts[profile.performance_level.value] += 1
                    
                    total_metrics["loading_time"].append(profile.loading_time_ms)
                    total_metrics["execution_time"].append(profile.average_execution_time_ms)
                    total_metrics["memory_usage"].append(profile.memory_usage_mb)
                    total_metrics["error_rate"].append(profile.error_rate)
                    
                    summary["recommendations"].extend(profile.recommendations)
            
            summary["performance_levels"] = dict(level_counts)
            
            # Calculate averages
            for metric_name, values in total_metrics.items():
                if values:
                    summary["average_metrics"][metric_name] = sum(values) / len(values)
            
            # Remove duplicate recommendations
            summary["recommendations"] = list(set(summary["recommendations"]))
            
            return summary
    
    def add_metric_listener(self, listener: Callable[[PerformanceMetric], None]) -> None:
        """Add a metric event listener."""
        self._metric_listeners.append(listener)
    
    def add_alert_listener(self, listener: Callable[[PerformanceAlert], None]) -> None:
        """Add an alert event listener."""
        self._alert_listeners.append(listener)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        with self._lock:
            stats = self._stats.copy()
            stats['monitoring_active'] = self._monitoring_active
            stats['components_monitored'] = len(self._profiles)
            stats['total_alerts'] = len(self._alerts)
            stats['thresholds'] = {k.value: v for k, v in self._thresholds.items()}
            return stats
    
    def export_performance_data(self, component_id: Optional[str] = None,
                             format: str = "json") -> str:
        """Export performance data."""
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "monitoring_interval": self.monitoring_interval,
            "profiles": {},
            "metrics": [],
            "alerts": [],
            "statistics": self.get_statistics()
        }
        
        # Export profiles
        profiles = self.get_all_profiles() if component_id is None else {component_id: self.get_component_profile(component_id)}
        for comp_id, profile in profiles.items():
            if profile:
                data["profiles"][comp_id] = {
                    "component_id": profile.component_id,
                    "loading_time_ms": profile.loading_time_ms,
                    "average_execution_time_ms": profile.average_execution_time_ms,
                    "min_execution_time_ms": profile.min_execution_time_ms,
                    "max_execution_time_ms": profile.max_execution_time_ms,
                    "total_executions": profile.total_executions,
                    "successful_executions": profile.successful_executions,
                    "failed_executions": profile.failed_executions,
                    "memory_usage_mb": profile.memory_usage_mb,
                    "cpu_usage_percent": profile.cpu_usage_percent,
                    "cache_hit_rate": profile.cache_hit_rate,
                    "error_rate": profile.error_rate,
                    "throughput_per_second": profile.throughput_per_second,
                    "performance_level": profile.performance_level.value,
                    "recommendations": profile.recommendations,
                    "last_updated": profile.last_updated.isoformat()
                }
        
        # Export metrics
        metrics = self.get_metrics(component_id)
        data["metrics"] = [
            {
                "component_id": m.component_id,
                "metric_type": m.metric_type.value,
                "value": m.value,
                "unit": m.unit,
                "timestamp": m.timestamp.isoformat(),
                "metadata": m.metadata
            }
            for m in metrics
        ]
        
        # Export alerts
        alerts = self.get_alerts(component_id)
        data["alerts"] = [
            {
                "alert_id": a.alert_id,
                "component_id": a.component_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "message": a.message,
                "threshold": a.threshold,
                "current_value": a.current_value,
                "timestamp": a.timestamp.isoformat(),
                "metadata": a.metadata
            }
            for a in alerts
        ]
        
        if format.lower() == "json":
            return json.dumps(data, indent=2)
        else:
            return str(data)
    
    def _add_metric(self, metric: PerformanceMetric) -> None:
        """Add a performance metric."""
        with self._lock:
            self._metrics[metric.component_id].append(metric)
            self._stats['total_metrics'] += 1
        
        # Notify listeners
        for listener in self._metric_listeners:
            try:
                listener(metric)
            except Exception:
                pass  # Don't let listener errors break monitoring
    
    def _add_alert(self, alert: PerformanceAlert) -> None:
        """Add a performance alert."""
        with self._lock:
            self._alerts.append(alert)
            self._stats['total_alerts'] += 1
        
        # Notify listeners
        for listener in self._alert_listeners:
            try:
                listener(alert)
            except Exception:
                pass  # Don't let listener errors break monitoring
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-level performance metrics."""
        try:
            # Get process metrics
            memory_info = self._process.memory_info()
            cpu_percent = self._process.cpu_percent()
            
            # Record system metrics
            system_metric = PerformanceMetric(
                component_id="system",
                metric_type=PerformanceMetricType.CPU_USAGE,
                value=cpu_percent,
                unit="%",
                metadata={"operation": "system_monitoring"}
            )
            self._add_metric(system_metric)
            
            memory_metric = PerformanceMetric(
                component_id="system",
                metric_type=PerformanceMetricType.MEMORY_USAGE,
                value=memory_info.rss / 1024 / 1024,  # Convert to MB
                unit="MB",
                metadata={"operation": "system_monitoring"}
            )
            self._add_metric(memory_metric)
            
        except Exception:
            pass  # Ignore system metric collection errors
    
    async def _update_performance_profiles(self) -> None:
        """Update performance profiles and calculate performance levels."""
        with self._lock:
            for profile in self._profiles.values():
                if profile:
                    # Calculate performance level
                    profile.performance_level = self._calculate_performance_level(profile)
                    
                    # Generate recommendations
                    profile.recommendations = self._generate_recommendations(profile)
    
    async def _check_performance_alerts(self) -> None:
        """Check for performance alerts based on thresholds."""
        with self._lock:
            for profile in self._profiles.values():
                if profile:
                    # Check loading time
                    if profile.loading_time_ms > self._thresholds[PerformanceMetricType.LOADING_TIME]:
                        alert = PerformanceAlert(
                            alert_id=f"loading_time_{profile.component_id}_{int(time.time())}",
                            component_id=profile.component_id,
                            alert_type="loading_time_high",
                            severity="warning",
                            message=f"Component loading time is high: {profile.loading_time_ms:.2f}ms",
                            threshold=self._thresholds[PerformanceMetricType.LOADING_TIME],
                            current_value=profile.loading_time_ms
                        )
                        self._add_alert(alert)
                    
                    # Check execution time
                    if profile.average_execution_time_ms > self._thresholds[PerformanceMetricType.EXECUTION_TIME]:
                        alert = PerformanceAlert(
                            alert_id=f"execution_time_{profile.component_id}_{int(time.time())}",
                            component_id=profile.component_id,
                            alert_type="execution_time_high",
                            severity="warning",
                            message=f"Component execution time is high: {profile.average_execution_time_ms:.2f}ms",
                            threshold=self._thresholds[PerformanceMetricType.EXECUTION_TIME],
                            current_value=profile.average_execution_time_ms
                        )
                        self._add_alert(alert)
                    
                    # Check error rate
                    if profile.error_rate > self._thresholds[PerformanceMetricType.ERROR_RATE]:
                        alert = PerformanceAlert(
                            alert_id=f"error_rate_{profile.component_id}_{int(time.time())}",
                            component_id=profile.component_id,
                            alert_type="error_rate_high",
                            severity="critical",
                            message=f"Component error rate is high: {profile.error_rate:.2%}",
                            threshold=self._thresholds[PerformanceMetricType.ERROR_RATE],
                            current_value=profile.error_rate
                        )
                        self._add_alert(alert)
                    
                    # Check memory usage
                    if profile.memory_usage_mb > self._thresholds[PerformanceMetricType.MEMORY_USAGE]:
                        alert = PerformanceAlert(
                            alert_id=f"memory_usage_{profile.component_id}_{int(time.time())}",
                            component_id=profile.component_id,
                            alert_type="memory_usage_high",
                            severity="warning",
                            message=f"Component memory usage is high: {profile.memory_usage_mb:.2f}MB",
                            threshold=self._thresholds[PerformanceMetricType.MEMORY_USAGE],
                            current_value=profile.memory_usage_mb
                        )
                        self._add_alert(alert)
    
    def _calculate_performance_level(self, profile: ComponentPerformanceProfile) -> PerformanceLevel:
        """Calculate performance level for a component."""
        score = 100.0
        
        # Deduct points for high loading time
        if profile.loading_time_ms > 2000:
            score -= 30
        elif profile.loading_time_ms > 1000:
            score -= 15
        
        # Deduct points for high execution time
        if profile.average_execution_time_ms > 1000:
            score -= 30
        elif profile.average_execution_time_ms > 500:
            score -= 15
        
        # Deduct points for high error rate
        if profile.error_rate > 0.1:  # 10%
            score -= 40
        elif profile.error_rate > 0.05:  # 5%
            score -= 20
        
        # Deduct points for high memory usage
        if profile.memory_usage_mb > 200:
            score -= 20
        elif profile.memory_usage_mb > 100:
            score -= 10
        
        # Determine performance level
        if score >= 90:
            return PerformanceLevel.EXCELLENT
        elif score >= 75:
            return PerformanceLevel.GOOD
        elif score >= 60:
            return PerformanceLevel.ACCEPTABLE
        elif score >= 40:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL
    
    def _generate_recommendations(self, profile: ComponentPerformanceProfile) -> List[str]:
        """Generate performance recommendations for a component."""
        recommendations = []
        
        # Loading time recommendations
        if profile.loading_time_ms > 1000:
            recommendations.append("Consider optimizing component initialization to reduce loading time")
        
        # Execution time recommendations
        if profile.average_execution_time_ms > 500:
            recommendations.append("Consider optimizing component execution logic for better performance")
        
        # Error rate recommendations
        if profile.error_rate > 0.05:
            recommendations.append("Investigate and fix component errors to improve reliability")
        
        # Memory usage recommendations
        if profile.memory_usage_mb > 100:
            recommendations.append("Consider optimizing memory usage in the component")
        
        # Execution count recommendations
        if profile.total_executions == 0:
            recommendations.append("Component has not been executed - consider if it's still needed")
        
        return recommendations


# Global performance monitor instance
_performance_monitor = ComponentPerformanceMonitor()


# Convenience functions
def start_performance_monitoring() -> None:
    """Start performance monitoring."""
    _performance_monitor.start_monitoring()


def stop_performance_monitoring() -> None:
    """Stop performance monitoring."""
    _performance_monitor.stop_monitoring()


def record_component_loading(component_id: str, loading_time_ms: float) -> None:
    """Record component loading time."""
    _performance_monitor.record_component_loading(component_id, loading_time_ms)


def record_component_execution(component_id: str, execution_time_ms: float,
                             success: bool, memory_usage_mb: Optional[float] = None) -> None:
    """Record component execution metrics."""
    _performance_monitor.record_component_execution(component_id, execution_time_ms, success, memory_usage_mb)


def get_component_profile(component_id: str) -> Optional[ComponentPerformanceProfile]:
    """Get performance profile for a component."""
    return _performance_monitor.get_component_profile(component_id)


def get_performance_summary(component_id: Optional[str] = None) -> Dict[str, Any]:
    """Get performance summary."""
    return _performance_monitor.get_performance_summary(component_id)


def get_performance_monitor() -> ComponentPerformanceMonitor:
    """Get the global performance monitor."""
    return _performance_monitor


# Decorator for automatic performance monitoring
def monitor_performance(component_id: Optional[str] = None):
    """Decorator to automatically monitor component performance."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                comp_id = component_id or func.__name__
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    execution_time_ms = (time.time() - start_time) * 1000
                    
                    # Record successful execution
                    record_component_execution(comp_id, execution_time_ms, True)
                    
                    return result
                    
                except Exception as e:
                    execution_time_ms = (time.time() - start_time) * 1000
                    
                    # Record failed execution
                    record_component_execution(comp_id, execution_time_ms, False)
                    
                    raise e
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                comp_id = component_id or func.__name__
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    execution_time_ms = (time.time() - start_time) * 1000
                    
                    # Record successful execution
                    record_component_execution(comp_id, execution_time_ms, True)
                    
                    return result
                    
                except Exception as e:
                    execution_time_ms = (time.time() - start_time) * 1000
                    
                    # Record failed execution
                    record_component_execution(comp_id, execution_time_ms, False)
                    
                    raise e
            
            return sync_wrapper
    
    return decorator
