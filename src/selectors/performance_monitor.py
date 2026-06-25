"""
Performance monitoring infrastructure for selector operations.

This module provides performance monitoring, metrics collection, and analysis
for YAML selector loading, validation, and registration operations.
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric."""
    
    operation: str
    duration_ms: float
    timestamp: datetime
    selector_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            "operation": self.operation,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "selector_id": self.selector_id,
            "metadata": self.metadata,
            "success": self.success,
            "error_message": self.error_message
        }


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    
    operation: str
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0
    operations_per_second: float = 0.0
    error_rate: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def update(self, metrics: List[PerformanceMetric]):
        """Update statistics with new metrics."""
        if not metrics:
            return
        
        self.total_operations += len(metrics)
        
        durations = [m.duration_ms for m in metrics]
        self.total_duration_ms += sum(durations)
        self.min_duration_ms = min(self.min_duration_ms, min(durations))
        self.max_duration_ms = max(self.max_duration_ms, max(durations))
        self.avg_duration_ms = self.total_duration_ms / self.total_operations
        
        # Calculate percentiles
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        if n > 0:
            self.p95_duration_ms = sorted_durations[int(n * 0.95)] if n >= 20 else sorted_durations[-1]
            self.p99_duration_ms = sorted_durations[int(n * 0.99)] if n >= 100 else sorted_durations[-1]
        
        # Update success/failure counts
        successful = sum(1 for m in metrics if m.success)
        failed = sum(1 for m in metrics if not m.success)
        self.successful_operations += successful
        self.failed_operations += failed
        
        # Calculate rates
        if self.total_operations > 0:
            self.error_rate = (self.failed_operations / self.total_operations) * 100
        
        # Calculate operations per second (last minute)
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        recent_metrics = [m for m in metrics if m.timestamp >= one_minute_ago]
        if recent_metrics:
            time_window = 60.0  # 1 minute
            self.operations_per_second = len(recent_metrics) / time_window
        
        self.last_updated = now
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "operation": self.operation,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "total_duration_ms": self.total_duration_ms,
            "min_duration_ms": self.min_duration_ms if self.min_duration_ms != float('inf') else 0,
            "max_duration_ms": self.max_duration_ms,
            "avg_duration_ms": self.avg_duration_ms,
            "p95_duration_ms": self.p95_duration_ms,
            "p99_duration_ms": self.p99_duration_ms,
            "operations_per_second": self.operations_per_second,
            "error_rate": self.error_rate,
            "last_updated": self.last_updated.isoformat()
        }


class PerformanceMonitor:
    """Performance monitor for selector operations."""
    
    def __init__(self, max_history_size: int = 10000, enable_system_metrics: bool = True):
        """Initialize performance monitor."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.max_history_size = max_history_size
        self.enable_system_metrics = enable_system_metrics
        
        # Metrics storage
        self._metrics: deque = deque(maxlen=max_history_size)
        self._stats: Dict[str, PerformanceStats] = defaultdict(PerformanceStats)
        self._lock = threading.Lock()
        
        # Performance thresholds
        self.thresholds = {
            "selector_loading": 1000.0,  # ms
            "selector_validation": 100.0,  # ms
            "selector_registration": 50.0,  # ms
            "selector_resolution": 500.0,  # ms
        }
        
        # System metrics
        self._system_metrics_enabled = enable_system_metrics
        self._process = psutil.Process() if enable_system_metrics else None
        
        self.logger.info(f"Performance monitor initialized (max_history={max_history_size}, "
                        f"system_metrics={enable_system_metrics})")
    
    def record_metric(self, operation: str, duration_ms: float, 
                     selector_id: Optional[str] = None, 
                     metadata: Optional[Dict[str, Any]] = None,
                     success: bool = True, error_message: Optional[str] = None) -> None:
        """Record a performance metric."""
        metric = PerformanceMetric(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            selector_id=selector_id,
            metadata=metadata or {},
            success=success,
            error_message=error_message
        )
        
        with self._lock:
            self._metrics.append(metric)
            
            # Update statistics
            if operation not in self._stats:
                self._stats[operation] = PerformanceStats(operation=operation)
            self._stats[operation].update([metric])
        
        # Check performance thresholds
        self._check_thresholds(metric)
        
        # Log if enabled
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Recorded metric: {operation}={duration_ms:.2f}ms "
                            f"{'✓' if success else '✗'}")
    
    def time_operation(self, operation: str, selector_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> Callable:
        """Decorator to time operations."""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error_message = None
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_message = str(e)
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    self.record_metric(
                        operation=operation,
                        duration_ms=duration_ms,
                        selector_id=selector_id,
                        metadata=metadata,
                        success=success,
                        error_message=error_message
                    )
            
            return wrapper
        return decorator
    
    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        with self._lock:
            if operation:
                if operation in self._stats:
                    return self._stats[operation].to_dict()
                else:
                    return {}
            else:
                return {op: stats.to_dict() for op, stats in self._stats.items()}
    
    def get_metrics(self, operation: Optional[str] = None, 
                   limit: Optional[int] = None,
                   since: Optional[datetime] = None) -> List[PerformanceMetric]:
        """Get performance metrics."""
        with self._lock:
            metrics = list(self._metrics)
            
            # Filter by operation
            if operation:
                metrics = [m for m in metrics if m.operation == operation]
            
            # Filter by time
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            
            # Limit results
            if limit:
                metrics = metrics[-limit:]
            
            return metrics
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        if not self._system_metrics_enabled or not self._process:
            return {}
        
        try:
            # CPU and memory usage
            cpu_percent = self._process.cpu_percent()
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            # Thread count
            thread_count = self._process.num_threads()
            
            # File descriptors (if available)
            try:
                fd_count = self._process.num_fds()
            except (AttributeError, psutil.AccessDenied):
                fd_count = None
            
            return {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "thread_count": thread_count,
                "fd_count": fd_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {str(e)}")
            return {}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_metrics": len(self._metrics),
            "operations": list(self._stats.keys()),
            "stats": self.get_stats(),
            "system_metrics": self.get_system_metrics(),
            "threshold_violations": self._get_recent_violations()
        }
        
        return summary
    
    def reset_stats(self, operation: Optional[str] = None) -> None:
        """Reset performance statistics."""
        with self._lock:
            if operation:
                if operation in self._stats:
                    del self._stats[operation]
                    self.logger.info(f"Reset stats for operation: {operation}")
            else:
                self._stats.clear()
                self.logger.info("Reset all performance statistics")
    
    def set_threshold(self, operation: str, threshold_ms: float) -> None:
        """Set performance threshold for an operation."""
        self.thresholds[operation] = threshold_ms
        self.logger.info(f"Set threshold for {operation}: {threshold_ms}ms")
    
    def get_thresholds(self) -> Dict[str, float]:
        """Get all performance thresholds."""
        return self.thresholds.copy()
    
    def _check_thresholds(self, metric: PerformanceMetric) -> None:
        """Check if metric exceeds performance thresholds."""
        if metric.operation in self.thresholds:
            threshold = self.thresholds[metric.operation]
            if metric.duration_ms > threshold:
                self.logger.warning(
                    f"Performance threshold exceeded: {metric.operation} "
                    f"took {metric.duration_ms:.2f}ms (threshold: {threshold}ms)"
                )
    
    def _get_recent_violations(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent threshold violations."""
        violations = []
        
        with self._lock:
            for metric in reversed(self._metrics):
                if metric.operation in self.thresholds:
                    threshold = self.thresholds[metric.operation]
                    if metric.duration_ms > threshold:
                        violations.append({
                            "operation": metric.operation,
                            "duration_ms": metric.duration_ms,
                            "threshold_ms": threshold,
                            "timestamp": metric.timestamp.isoformat(),
                            "selector_id": metric.selector_id
                        })
                        
                        if len(violations) >= count:
                            break
        
        return violations
    
    def export_metrics(self, file_path: str, format: str = "json") -> bool:
        """Export metrics to file."""
        try:
            import json
            
            data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "metrics": [m.to_dict() for m in self._metrics],
                "stats": self.get_stats(),
                "thresholds": self.thresholds
            }
            
            export_path = Path(file_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            self.logger.info(f"Exported {len(self._metrics)} metrics to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export metrics: {str(e)}")
            return False
    
    def cleanup_old_metrics(self, days: int = 7) -> int:
        """Clean up metrics older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with self._lock:
            initial_count = len(self._metrics)
            
            # Filter old metrics
            filtered_metrics = deque(
                (m for m in self._metrics if m.timestamp >= cutoff_date),
                maxlen=self.max_history_size
            )
            
            self._metrics = filtered_metrics
            removed_count = initial_count - len(self._metrics)
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old metrics (older than {days} days)")
            
            return removed_count


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor(max_history_size: int = 10000, 
                           enable_system_metrics: bool = True) -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(max_history_size, enable_system_metrics)
    return _performance_monitor


def record_metric(operation: str, duration_ms: float, 
                 selector_id: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 success: bool = True, error_message: Optional[str] = None) -> None:
    """Record a performance metric using the global monitor."""
    get_performance_monitor().record_metric(
        operation=operation,
        duration_ms=duration_ms,
        selector_id=selector_id,
        metadata=metadata,
        success=success,
        error_message=error_message
    )


def time_operation(operation: str, selector_id: Optional[str] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> Callable:
    """Decorator to time operations using the global monitor."""
    return get_performance_monitor().time_operation(operation, selector_id, metadata)


def get_performance_stats(operation: Optional[str] = None) -> Dict[str, Any]:
    """Get performance statistics using the global monitor."""
    return get_performance_monitor().get_stats(operation)


def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary using the global monitor."""
    return get_performance_monitor().get_performance_summary()
