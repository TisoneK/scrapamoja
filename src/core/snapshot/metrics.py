"""
Monitoring and metrics collection for the snapshot system.

This module provides comprehensive performance monitoring, metrics collection,
and health tracking for the snapshot system.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
from pathlib import Path

from src.observability.logger import get_logger

from .models import SnapshotMetrics, SnapshotError, EnumEncoder

logger = get_logger(__name__)

@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    timestamp: datetime
    operation: str
    duration_ms: float
    success: bool
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: datetime
    metrics: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and manages snapshot system metrics."""
    
    def __init__(self, max_history_size: int = 10000):
        """Initialize metrics collector."""
        self.max_history_size = max_history_size
        self.metrics: deque = deque(maxlen=max_history_size)
        self.operation_stats: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.hourly_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._lock = threading.RLock()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_old_metrics, daemon=True)
        self._cleanup_thread.start()
    
    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric."""
        with self._lock:
            self.metrics.append(metric)
            
            # Update operation stats
            if metric.success:
                self.operation_stats[metric.operation].append(metric.duration_ms)
            else:
                self.error_counts[metric.error_type or "unknown"] += 1
            
            # Update hourly stats
            hour_key = metric.timestamp.strftime("%Y-%m-%d %H:00")
            self.hourly_stats[hour_key]["total_operations"] += 1
            if metric.success:
                self.hourly_stats[hour_key]["successful_operations"] += 1
            else:
                self.hourly_stats[hour_key]["failed_operations"] += 1
    
    def record_failure(self, failure_type: str, error_message: str, metadata: Optional[Dict[str, Any]] = None):
        """Record a failure metric."""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            operation=f"failure_{failure_type}",
            duration_ms=0.0,
            success=False,
            error_type=failure_type,
            metadata=metadata or {}
        )
        self.record_metric(metric)
    
    def start_operation_timer(self, operation: str) -> Callable:
        """Start timing an operation and return a stop function."""
        start_time = time.time()
        
        def stop_timer(success: bool = True, error_type: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
            duration_ms = (time.time() - start_time) * 1000
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                operation=operation,
                duration_ms=duration_ms,
                success=success,
                error_type=error_type,
                metadata=metadata or {}
            )
            self.record_metric(metric)
            return duration_ms
        
        return stop_timer
    
    def get_snapshot_metrics(self) -> SnapshotMetrics:
        """Get comprehensive snapshot metrics."""
        with self._lock:
            total_snapshots = len([m for m in self.metrics if "snapshot" in m.operation])
            successful_snapshots = len([m for m in self.metrics if "snapshot" in m.operation and m.success])
            failed_snapshots = total_snapshots - successful_snapshots
            
            # Calculate average capture time
            snapshot_durations = [m.duration_ms for m in self.metrics if "snapshot" in m.operation and m.success]
            average_capture_time = sum(snapshot_durations) / len(snapshot_durations) if snapshot_durations else 0.0
            
            # Calculate parallel vs sequential execution
            parallel_ops = len([m for m in self.metrics if "parallel" in m.operation])
            sequential_ops = len([m for m in self.metrics if "sequential" in m.operation])
            
            return SnapshotMetrics(
                total_snapshots=total_snapshots,
                successful_snapshots=successful_snapshots,
                failed_snapshots=failed_snapshots,
                average_capture_time=average_capture_time,
                parallel_executions=parallel_ops,
                sequential_executions=sequential_ops
            )
    
    def get_operation_statistics(self, operation: str, hours: int = 24) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [m for m in self.metrics if m.operation == operation and m.timestamp > cutoff_time]
            
            if not recent_metrics:
                return {"error": "No recent metrics found"}
            
            durations = [m.duration_ms for m in recent_metrics if m.success]
            successful_count = len(durations)
            failed_count = len(recent_metrics) - successful_count
            
            return {
                "operation": operation,
                "timeframe_hours": hours,
                "total_operations": len(recent_metrics),
                "successful_operations": successful_count,
                "failed_operations": failed_count,
                "success_rate": (successful_count / len(recent_metrics)) * 100 if recent_metrics else 0,
                "average_duration_ms": sum(durations) / len(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
                "p50_duration_ms": self._percentile(durations, 50) if durations else 0,
                "p95_duration_ms": self._percentile(durations, 95) if durations else 0,
                "p99_duration_ms": self._percentile(durations, 99) if durations else 0
            }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def get_error_breakdown(self, hours: int = 24) -> Dict[str, Any]:
        """Get breakdown of errors by type."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_errors = [m for m in self.metrics if not m.success and m.timestamp > cutoff_time]
            
            error_counts = defaultdict(int)
            for metric in recent_errors:
                error_type = metric.error_type or "unknown"
                error_counts[error_type] += 1
            
            total_errors = len(recent_errors)
            
            return {
                "timeframe_hours": hours,
                "total_errors": total_errors,
                "error_breakdown": dict(error_counts),
                "error_rates": {
                    error_type: (count / total_errors) * 100 
                    for error_type, count in error_counts.items()
                } if total_errors > 0 else {}
            }
    
    def get_hourly_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get hourly operation trends."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            hourly_data = {}
            
            for hour_key, stats in self.hourly_stats.items():
                hour_datetime = datetime.strptime(hour_key, "%Y-%m-%d %H:00")
                if hour_datetime > cutoff_time:
                    hourly_data[hour_key] = stats.copy()
                    # Calculate success rate
                    total = stats.get("total_operations", 0)
                    successful = stats.get("successful_operations", 0)
                    hourly_data[hour_key]["success_rate"] = (successful / total * 100) if total > 0 else 0
            
            return {
                "timeframe_hours": hours,
                "hourly_data": hourly_data,
                "peak_hour": max(hourly_data.items(), key=lambda x: x[1].get("total_operations", 0)) if hourly_data else None
            }
    
    def _cleanup_old_metrics(self):
        """Cleanup old metrics periodically."""
        while True:
            try:
                # Sleep for 1 hour
                time.sleep(3600)
                
                with self._lock:
                    cutoff_time = datetime.now() - timedelta(days=7)
                    
                    # Remove old metrics from deque (handled by maxlen)
                    # Clean up old hourly stats
                    old_hours = [
                        hour_key for hour_key in self.hourly_stats.keys()
                        if datetime.strptime(hour_key, "%Y-%m-%d %H:00") < cutoff_time
                    ]
                    
                    for hour_key in old_hours:
                        del self.hourly_stats[hour_key]
                    
                    # Limit operation stats size
                    for operation in self.operation_stats:
                        if len(self.operation_stats[operation]) > 1000:
                            self.operation_stats[operation] = self.operation_stats[operation][-1000:]
                    
            except Exception as e:
                logger.error("Error in metrics cleanup", error=str(e))


class HealthMonitor:
    """Monitors system health and performs health checks."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize health monitor."""
        self.metrics_collector = metrics_collector
        self.health_checks: List[Callable[[], HealthCheck]] = []
        self.last_health_check: Optional[HealthCheck] = None
        
        # Register default health checks
        self._register_default_health_checks()
    
    def _register_default_health_checks(self):
        """Register default health checks."""
        self.health_checks.extend([
            self._check_snapshot_success_rate,
            self._check_average_capture_time,
            self._check_error_rate,
            self._check_metrics_collection
        ])
    
    def _check_snapshot_success_rate(self) -> HealthCheck:
        """Check snapshot success rate."""
        metrics = self.metrics_collector.get_snapshot_metrics()
        success_rate = metrics.success_rate
        
        if success_rate >= 95.0:
            status = "healthy"
            message = f"Snapshot success rate is {success_rate:.1f}%"
        elif success_rate >= 80.0:
            status = "degraded"
            message = f"Snapshot success rate is {success_rate:.1f}% - below optimal"
        else:
            status = "unhealthy"
            message = f"Snapshot success rate is {success_rate:.1f}% - critically low"
        
        return HealthCheck(
            name="snapshot_success_rate",
            status=status,
            message=message,
            timestamp=datetime.now(),
            metrics={"success_rate": success_rate}
        )
    
    def _check_average_capture_time(self) -> HealthCheck:
        """Check average snapshot capture time."""
        metrics = self.metrics_collector.get_snapshot_metrics()
        avg_time = metrics.average_capture_time
        
        if avg_time <= 1000:  # 1 second
            status = "healthy"
            message = f"Average capture time is {avg_time:.0f}ms"
        elif avg_time <= 3000:  # 3 seconds
            status = "degraded"
            message = f"Average capture time is {avg_time:.0f}ms - slower than optimal"
        else:
            status = "unhealthy"
            message = f"Average capture time is {avg_time:.0f}ms - critically slow"
        
        return HealthCheck(
            name="average_capture_time",
            status=status,
            message=message,
            timestamp=datetime.now(),
            metrics={"average_capture_time_ms": avg_time}
        )
    
    def _check_error_rate(self) -> HealthCheck:
        """Check overall error rate."""
        error_breakdown = self.metrics_collector.get_error_breakdown(hours=1)
        total_operations = sum(
            m for m in self.metrics_collector.metrics 
            if m.timestamp > datetime.now() - timedelta(hours=1)
        )
        total_errors = error_breakdown.get("total_errors", 0)
        
        error_rate = (total_errors / total_operations * 100) if total_operations > 0 else 0
        
        if error_rate <= 5.0:
            status = "healthy"
            message = f"Error rate is {error_rate:.1f}%"
        elif error_rate <= 15.0:
            status = "degraded"
            message = f"Error rate is {error_rate:.1f}% - elevated"
        else:
            status = "unhealthy"
            message = f"Error rate is {error_rate:.1f}% - critically high"
        
        return HealthCheck(
            name="error_rate",
            status=status,
            message=message,
            timestamp=datetime.now(),
            metrics={"error_rate": error_rate, "total_errors": total_errors}
        )
    
    def _check_metrics_collection(self) -> HealthCheck:
        """Check metrics collection health."""
        recent_metrics = len([
            m for m in self.metrics_collector.metrics 
            if m.timestamp > datetime.now() - timedelta(minutes=5)
        ])
        
        if recent_metrics > 0:
            status = "healthy"
            message = f"Metrics collection active - {recent_metrics} metrics in last 5 minutes"
        else:
            status = "degraded"
            message = "No metrics collected in last 5 minutes"
        
        return HealthCheck(
            name="metrics_collection",
            status=status,
            message=message,
            timestamp=datetime.now(),
            metrics={"recent_metrics_count": recent_metrics}
        )
    
    def run_health_checks(self) -> List[HealthCheck]:
        """Run all registered health checks."""
        results = []
        
        for check_func in self.health_checks:
            try:
                result = check_func()
                results.append(result)
            except Exception as e:
                results.append(HealthCheck(
                    name=check_func.__name__,
                    status="unhealthy",
                    message=f"Health check failed: {e}",
                    timestamp=datetime.now()
                ))
        
        # Update last health check (overall status)
        if results:
            unhealthy_count = sum(1 for r in results if r.status == "unhealthy")
            degraded_count = sum(1 for r in results if r.status == "degraded")
            
            if unhealthy_count > 0:
                overall_status = "unhealthy"
            elif degraded_count > 0:
                overall_status = "degraded"
            else:
                overall_status = "healthy"
            
            self.last_health_check = HealthCheck(
                name="overall_system_health",
                status=overall_status,
                message=f"System health: {unhealthy_count} unhealthy, {degraded_count} degraded checks",
                timestamp=datetime.now(),
                metrics={
                    "total_checks": len(results),
                    "healthy_checks": len(results) - unhealthy_count - degraded_count,
                    "degraded_checks": degraded_count,
                    "unhealthy_checks": unhealthy_count
                }
            )
        
        return results
    
    def get_system_health(self) -> Optional[HealthCheck]:
        """Get overall system health."""
        if self.last_health_check is None:
            self.run_health_checks()
        return self.last_health_check
    
    def register_health_check(self, check_func: Callable[[], HealthCheck]):
        """Register a custom health check."""
        self.health_checks.append(check_func)


class MonitoringDashboard:
    """Provides monitoring dashboard data."""
    
    def __init__(self, metrics_collector: MetricsCollector, health_monitor: HealthMonitor):
        """Initialize monitoring dashboard."""
        self.metrics_collector = metrics_collector
        self.health_monitor = health_monitor
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        return {
            "timestamp": datetime.now().isoformat(),
            "snapshot_metrics": self.metrics_collector.get_snapshot_metrics().to_dict() if hasattr(self.metrics_collector.get_snapshot_metrics(), 'to_dict') else self._metrics_to_dict(self.metrics_collector.get_snapshot_metrics()),
            "system_health": self.health_monitor.get_system_health().__dict__ if self.health_monitor.get_system_health() else None,
            "recent_operations": self._get_recent_operations(),
            "error_breakdown": self.metrics_collector.get_error_breakdown(),
            "hourly_trends": self.metrics_collector.get_hourly_trends(),
            "health_checks": [check.__dict__ for check in self.health_monitor.run_health_checks()]
        }
    
    def _metrics_to_dict(self, metrics) -> Dict[str, Any]:
        """Convert metrics object to dictionary."""
        return {
            "total_snapshots": metrics.total_snapshots,
            "successful_snapshots": metrics.successful_snapshots,
            "failed_snapshots": metrics.failed_snapshots,
            "average_capture_time": metrics.average_capture_time,
            "success_rate": metrics.success_rate,
            "deduplication_rate": metrics.deduplication_rate,
            "parallel_execution_rate": metrics.parallel_execution_rate
        }
    
    def _get_recent_operations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent operations."""
        recent = list(self.metrics_collector.metrics)[-limit:]
        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "operation": m.operation,
                "duration_ms": m.duration_ms,
                "success": m.success,
                "error_type": m.error_type
            }
            for m in recent
        ]
    
    def export_metrics(self, filepath: str, hours: int = 24):
        """Export metrics to file."""
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "timeframe_hours": hours,
            "dashboard_data": self.get_dashboard_data(),
            "operation_statistics": {
                operation: self.metrics_collector.get_operation_statistics(operation, hours)
                for operation in set(m.operation for m in self.metrics_collector.metrics)
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, cls=EnumEncoder)
