"""
Performance monitoring and metrics collection for navigation components

Provides comprehensive performance monitoring, metrics collection, and health checks
for all navigation components with real-time monitoring and alerting.
"""

import time
import asyncio
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
from pathlib import Path

from .logging_config import get_navigation_logger


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    component: str
    operation: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HealthCheck:
    """Health check result"""
    component: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: datetime
    metrics: Dict[str, float]
    response_time: float


@dataclass
class PerformanceAlert:
    """Performance alert"""
    alert_type: str
    component: str
    severity: str  # "info", "warning", "critical"
    message: str
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold: float


class PerformanceMonitor:
    """Performance monitoring system for navigation components"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize performance monitor"""
        self.logger = get_navigation_logger("performance_monitor")
        self.config = config or {}
        
        # Metrics storage
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._alerts: deque = deque(maxlen=100)
        self._health_checks: Dict[str, HealthCheck] = {}
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Configuration
        self.collection_interval = self.config.get("collection_interval", 30)  # seconds
        self.health_check_interval = self.config.get("health_check_interval", 60)  # seconds
        self.metrics_retention_hours = self.config.get("metrics_retention_hours", 24)
        self.enable_system_metrics = self.config.get("enable_system_metrics", True)
        
        # Thresholds
        self.thresholds = self.config.get("thresholds", {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "response_time": 5.0,
            "error_rate": 10.0,
            "success_rate": 90.0
        })
        
        # Component-specific metrics
        self._component_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        self.logger.info(
            "Performance monitor initialized",
            collection_interval=self.collection_interval,
            health_check_interval=self.health_check_interval
        )
    
    def start_monitoring(self) -> None:
        """Start performance monitoring"""
        if self._monitoring_active:
            self.logger.warning("Performance monitoring already active")
            return
        
        self._monitoring_active = True
        self._stop_event.clear()
        
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self._monitoring_thread.start()
        
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        self._stop_event.set()
        
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        
        self.logger.info("Performance monitoring stopped")
    
    def record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        component: str,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            component=component,
            operation=operation,
            metadata=metadata
        )
        
        # Store metric
        metric_key = f"{component}.{name}"
        self._metrics[metric_key].append(metric)
        
        # Update component metrics
        self._component_metrics[component][name] = {
            "latest_value": value,
            "latest_timestamp": metric.timestamp,
            "unit": unit
        }
        
        # Check for alerts
        self._check_alerts(metric)
        
        self.logger.debug(
            "Metric recorded",
            name=name,
            value=value,
            unit=unit,
            component=component
        )
    
    def record_operation_time(
        self,
        component: str,
        operation: str,
        duration: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record operation timing"""
        # Record duration
        self.record_metric(
            name="operation_duration",
            value=duration,
            unit="seconds",
            component=component,
            operation=operation,
            metadata={**(metadata or {}), "success": success}
        )
        
        # Record success/failure
        self.record_metric(
            name="operation_success",
            value=1.0 if success else 0.0,
            unit="boolean",
            component=component,
            operation=operation
        )
        
        # Update operation statistics
        op_key = f"{component}.{operation}"
        if "operations" not in self._component_metrics[component]:
            self._component_metrics[component]["operations"] = {}
        
        if op_key not in self._component_metrics[component]["operations"]:
            self._component_metrics[component]["operations"][op_key] = {
                "total_count": 0,
                "success_count": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
                "success_rate": 0.0
            }
        
        stats = self._component_metrics[component]["operations"][op_key]
        stats["total_count"] += 1
        stats["total_duration"] += duration
        
        if success:
            stats["success_count"] += 1
        
        stats["avg_duration"] = stats["total_duration"] / stats["total_count"]
        stats["success_rate"] = (stats["success_count"] / stats["total_count"]) * 100
    
    def get_metrics(
        self,
        component: Optional[str] = None,
        metric_name: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[PerformanceMetric]:
        """Get metrics with optional filtering"""
        metrics = []
        
        for key, metric_deque in self._metrics.items():
            if component and not key.startswith(f"{component}."):
                continue
            
            if metric_name and not key.endswith(f".{metric_name}"):
                continue
            
            for metric in metric_deque:
                if since and metric.timestamp < since:
                    continue
                
                metrics.append(metric)
        
        return sorted(metrics, key=lambda m: m.timestamp)
    
    def get_component_metrics(self, component: str) -> Dict[str, Any]:
        """Get all metrics for a specific component"""
        return dict(self._component_metrics.get(component, {}))
    
    def get_system_metrics(self) -> Dict[str, float]:
        """Get system-level metrics"""
        if not self.enable_system_metrics:
            return {}
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_total_mb = memory.total / (1024 * 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_total_gb = disk.total / (1024 * 1024 * 1024)
            
            # Network metrics
            network = psutil.net_io_counters()
            bytes_sent = network.bytes_sent
            bytes_recv = network.bytes_recv
            
            return {
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "memory_percent": memory_percent,
                "memory_used_mb": memory_used_mb,
                "memory_total_mb": memory_total_mb,
                "disk_percent": disk_percent,
                "disk_used_gb": disk_used_gb,
                "disk_total_gb": disk_total_gb,
                "network_bytes_sent": bytes_sent,
                "network_bytes_recv": bytes_recv
            }
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return {}
    
    def get_health_status(self) -> Dict[str, HealthCheck]:
        """Get health status for all components"""
        return dict(self._health_checks)
    
    def get_alerts(
        self,
        severity: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[PerformanceAlert]:
        """Get alerts with optional filtering"""
        alerts = []
        
        for alert in self._alerts:
            if severity and alert.severity != severity:
                continue
            
            if since and alert.timestamp < since:
                continue
            
            alerts.append(alert)
        
        return sorted(alerts, key=lambda a: a.timestamp)
    
    def register_health_check(
        self,
        component: str,
        check_function: Callable[[], Dict[str, Any]]
    ) -> None:
        """Register health check function for component"""
        self._component_metrics[component]["health_check"] = check_function
    
    def run_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks"""
        results = {}
        
        for component, metrics in self._component_metrics.items():
            if "health_check" not in metrics:
                continue
            
            try:
                start_time = time.time()
                check_result = metrics["health_check"]()
                response_time = time.time() - start_time
                
                # Determine health status
                status = "healthy"
                message = "Component operating normally"
                
                if check_result.get("error"):
                    status = "unhealthy"
                    message = f"Error: {check_result['error']}"
                elif check_result.get("warnings"):
                    status = "degraded"
                    message = f"Warnings: {', '.join(check_result['warnings'])}"
                
                health_check = HealthCheck(
                    component=component,
                    status=status,
                    message=message,
                    timestamp=datetime.utcnow(),
                    metrics=check_result.get("metrics", {}),
                    response_time=response_time
                )
                
                results[component] = health_check
                self._health_checks[component] = health_check
                
            except Exception as e:
                health_check = HealthCheck(
                    component=component,
                    status="unhealthy",
                    message=f"Health check failed: {str(e)}",
                    timestamp=datetime.utcnow(),
                    metrics={},
                    response_time=0.0
                )
                
                results[component] = health_check
                self._health_checks[component] = health_check
                
                self.logger.error(
                    f"Health check failed for {component}: {e}"
                )
        
        return results
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring_active": self._monitoring_active,
            "components": {},
            "system_metrics": self.get_system_metrics(),
            "health_status": {name: check.status for name, check in self._health_checks.items()},
            "recent_alerts": len([a for a in self._alerts if (datetime.utcnow() - a.timestamp).seconds < 3600])
        }
        
        # Component summaries
        for component, metrics in self._component_metrics.items():
            component_summary = {
                "metrics_count": len([k for k in metrics.keys() if k != "operations"]),
                "operations_count": len(metrics.get("operations", {})),
                "latest_metrics": {}
            }
            
            # Add latest metric values
            for key, value in metrics.items():
                if key != "operations" and isinstance(value, dict) and "latest_value" in value:
                    component_summary["latest_metrics"][key] = value["latest_value"]
            
            summary["components"][component] = component_summary
        
        return summary
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        self.logger.info("Monitoring loop started")
        
        while not self._stop_event.wait(self.collection_interval):
            try:
                # Collect system metrics
                if self.enable_system_metrics:
                    system_metrics = self.get_system_metrics()
                    for name, value in system_metrics.items():
                        self.record_metric(
                            name=name,
                            value=value,
                            unit=self._get_metric_unit(name),
                            component="system"
                        )
                
                # Run health checks
                if (datetime.utcnow() - self._last_health_check()).seconds >= self.health_check_interval:
                    self.run_health_checks()
                
                # Clean up old metrics
                self._cleanup_old_metrics()
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
        
        self.logger.info("Monitoring loop stopped")
    
    def _check_alerts(self, metric: PerformanceMetric) -> None:
        """Check if metric triggers any alerts"""
        # Define alert rules
        alert_rules = {
            "cpu_usage": (self.thresholds["cpu_usage"], "warning"),
            "memory_usage": (self.thresholds["memory_usage"], "critical"),
            "operation_duration": (self.thresholds["response_time"], "warning"),
            "operation_success": (self.thresholds["success_rate"], "warning")  # Inverted for success rate
        }
        
        if metric.name in alert_rules:
            threshold, severity = alert_rules[metric.name]
            
            # Special handling for success rate (higher is better)
            if metric.name == "operation_success":
                if metric.value * 100 < threshold:
                    self._create_alert(
                        alert_type="low_success_rate",
                        component=metric.component,
                        severity=severity,
                        message=f"Low success rate: {metric.value * 100:.1f}%",
                        metric_name=metric.name,
                        current_value=metric.value * 100,
                        threshold=threshold
                    )
            else:
                if metric.value > threshold:
                    self._create_alert(
                        alert_type="high_metric_value",
                        component=metric.component,
                        severity=severity,
                        message=f"High {metric.name}: {metric.value}{metric.unit}",
                        metric_name=metric.name,
                        current_value=metric.value,
                        threshold=threshold
                    )
    
    def _create_alert(
        self,
        alert_type: str,
        component: str,
        severity: str,
        message: str,
        metric_name: str,
        current_value: float,
        threshold: float
    ) -> None:
        """Create performance alert"""
        alert = PerformanceAlert(
            alert_type=alert_type,
            component=component,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold
        )
        
        self._alerts.append(alert)
        
        self.logger.warning(
            "Performance alert created",
            alert_type=alert_type,
            component=component,
            severity=severity,
            message=message
        )
    
    def _get_metric_unit(self, metric_name: str) -> str:
        """Get unit for system metric"""
        unit_map = {
            "cpu_percent": "percent",
            "memory_percent": "percent",
            "memory_used_mb": "MB",
            "memory_total_mb": "MB",
            "disk_percent": "percent",
            "disk_used_gb": "GB",
            "disk_total_gb": "GB",
            "network_bytes_sent": "bytes",
            "network_bytes_recv": "bytes"
        }
        
        return unit_map.get(metric_name, "unknown")
    
    def _last_health_check(self) -> datetime:
        """Get timestamp of last health check"""
        if not self._health_checks:
            return datetime.utcnow() - timedelta(hours=1)
        
        latest = max(check.timestamp for check in self._health_checks.values())
        return latest
    
    def _cleanup_old_metrics(self) -> None:
        """Clean up old metrics based on retention policy"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.metrics_retention_hours)
        
        for key, metric_deque in self._metrics.items():
            # Remove old metrics
            while metric_deque and metric_deque[0].timestamp < cutoff_time:
                metric_deque.popleft()


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor(config: Optional[Dict[str, Any]] = None) -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(config)
    
    return _performance_monitor


def start_performance_monitoring(config: Optional[Dict[str, Any]] = None) -> None:
    """Start global performance monitoring"""
    monitor = get_performance_monitor(config)
    monitor.start_monitoring()


def stop_performance_monitoring() -> None:
    """Stop global performance monitoring"""
    global _performance_monitor
    
    if _performance_monitor:
        _performance_monitor.stop_monitoring()


def record_performance_metric(
    name: str,
    value: float,
    unit: str,
    component: str,
    operation: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Record performance metric using global monitor"""
    monitor = get_performance_monitor()
    monitor.record_metric(name, value, unit, component, operation, metadata)


def record_operation_performance(
    component: str,
    operation: str,
    duration: float,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Record operation performance using global monitor"""
    monitor = get_performance_monitor()
    monitor.record_operation_time(component, operation, duration, success, metadata)
