"""
Monitoring and observability for template framework.

This module provides comprehensive monitoring, metrics collection, and observability
features for the template framework including performance tracking, health monitoring,
and operational insights.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json
import threading
import queue
from collections import defaultdict, deque
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str]
    unit: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class Alert:
    """Monitoring alert."""
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class HealthCheck:
    """Health check definition."""
    name: str
    check_function: Callable
    interval: int  # seconds
    timeout: int  # seconds
    healthy_threshold: int = 1
    unhealthy_threshold: int = 3


class MetricsCollector:
    """Metrics collection and aggregation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize metrics collector.
        
        Args:
            config: Collector configuration
        """
        self.config = config or {}
        
        # Metrics configuration
        self.metrics_config = {
            "retention_period": self.config.get("retention_period", 3600),  # 1 hour
            "max_points_per_metric": self.config.get("max_points_per_metric", 1000),
            "aggregation_interval": self.config.get("aggregation_interval", 60),  # 1 minute
            "enable_histograms": self.config.get("enable_histograms", True)
        }
        
        # Metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.metrics_config["max_points_per_metric"]))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        
        # Aggregation
        self.aggregated_metrics: Dict[str, Dict[str, float]] = {}
        self.aggregation_timer = None
        self._start_aggregation_timer()
        
        logger.info("MetricsCollector initialized")
    
    def record_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record counter metric.
        
        Args:
            name: Metric name
            value: Counter value
            labels: Metric labels
        """
        full_name = self._format_metric_name(name, labels)
        self.counters[full_name] += value
        
        metric_point = MetricPoint(
            name=full_name,
            value=self.counters[full_name],
            metric_type=MetricType.COUNTER,
            timestamp=datetime.now(),
            labels=labels or {}
        )
        
        self.metrics[full_name].append(metric_point)
    
    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record gauge metric.
        
        Args:
            name: Metric name
            value: Gauge value
            labels: Metric labels
        """
        full_name = self._format_metric_name(name, labels)
        self.gauges[full_name] = value
        
        metric_point = MetricPoint(
            name=full_name,
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            labels=labels or {}
        )
        
        self.metrics[full_name].append(metric_point)
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record histogram metric.
        
        Args:
            name: Metric name
            value: Histogram value
            labels: Metric labels
        """
        if not self.metrics_config["enable_histograms"]:
            return
        
        full_name = self._format_metric_name(name, labels)
        self.histograms[full_name].append(value)
        
        metric_point = MetricPoint(
            name=full_name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            timestamp=datetime.now(),
            labels=labels or {}
        )
        
        self.metrics[full_name].append(metric_point)
    
    def record_timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record timer metric.
        
        Args:
            name: Metric name
            duration: Duration in seconds
            labels: Metric labels
        """
        full_name = self._format_metric_name(name, labels)
        self.timers[full_name].append(duration)
        
        metric_point = MetricPoint(
            name=full_name,
            value=duration,
            metric_type=MetricType.TIMER,
            timestamp=datetime.now(),
            labels=labels or {},
            unit="seconds"
        )
        
        self.metrics[full_name].append(metric_point)
    
    def _format_metric_name(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Format metric name with labels."""
        if not labels:
            return name
        
        label_str = ",".join([f"{k}={v}" for k, v in sorted(labels.items())])
        return f"{name}[{label_str}]"
    
    def get_metric(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[List[MetricPoint]]:
        """
        Get metric data.
        
        Args:
            name: Metric name
            labels: Metric labels
            
        Returns:
            Optional[List[MetricPoint]]: Metric data points
        """
        full_name = self._format_metric_name(name, labels)
        return list(self.metrics.get(full_name, []))
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary.
        
        Returns:
            Dict[str, Any]: Metrics summary
        """
        summary = {
            "total_metrics": len(self.metrics),
            "total_points": sum(len(points) for points in self.metrics.values()),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {},
            "timers": {},
            "aggregated_metrics": self.aggregated_metrics
        }
        
        # Add histogram statistics
        for name, values in self.histograms.items():
            if values:
                summary["histograms"][name] = {
                    "count": len(values),
                    "sum": sum(values),
                    "min": min(values),
                    "max": max(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values)
                }
        
        # Add timer statistics
        for name, values in self.timers.items():
            if values:
                summary["timers"][name] = {
                    "count": len(values),
                    "sum": sum(values),
                    "min": min(values),
                    "max": max(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99)
                }
        
        return summary
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _start_aggregation_timer(self) -> None:
        """Start aggregation timer."""
        if self.aggregation_timer:
            self.aggregation_timer.cancel()
        
        self.aggregation_timer = threading.Timer(
            self.metrics_config["aggregation_interval"],
            self._aggregate_metrics
        )
        self.aggregation_timer.daemon = True
        self.aggregation_timer.start()
    
    def _aggregate_metrics(self) -> None:
        """Aggregate metrics."""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(seconds=self.metrics_config["retention_period"])
            
            # Clean old metrics
            for name, points in self.metrics.items():
                # Remove old points
                while points and points[0].timestamp < cutoff_time:
                    points.popleft()
                
                # Aggregate recent points
                if points:
                    recent_points = [p for p in points if p.timestamp >= current_time - timedelta(seconds=self.metrics_config["aggregation_interval"])]
                    if recent_points:
                        values = [p.value for p in recent_points]
                        self.aggregated_metrics[name] = {
                            "count": len(values),
                            "sum": sum(values),
                            "avg": statistics.mean(values),
                            "min": min(values),
                            "max": max(values),
                            "timestamp": current_time.isoformat()
                        }
            
            # Restart timer
            self._start_aggregation_timer()
        
        except Exception as e:
            logger.error(f"Error during metrics aggregation: {e}")
    
    def cleanup(self) -> None:
        """Cleanup metrics collector."""
        if self.aggregation_timer:
            self.aggregation_timer.cancel()
        
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.timers.clear()
        self.aggregated_metrics.clear()


class AlertManager:
    """Alert management and notification."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize alert manager.
        
        Args:
            config: Alert manager configuration
        """
        self.config = config or {}
        
        # Alert configuration
        self.alert_config = {
            "enable_alerts": self.config.get("enable_alerts", True),
            "alert_retention": self.config.get("alert_retention", 86400),  # 24 hours
            "max_alerts": self.config.get("max_alerts", 1000),
            "notification_channels": self.config.get("notification_channels", ["log"])
        }
        
        # Alert storage
        self.alerts: deque = deque(maxlen=self.alert_config["max_alerts"])
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_handlers: Dict[str, Callable] = {}
        
        logger.info("AlertManager initialized")
    
    def add_alert_rule(self, rule_name: str, condition: Callable, severity: AlertSeverity, 
                      message: str, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Add alert rule.
        
        Args:
            rule_name: Rule name
            condition: Alert condition function
            severity: Alert severity
            message: Alert message
            labels: Alert labels
        """
        self.alert_rules[rule_name] = {
            "condition": condition,
            "severity": severity,
            "message": message,
            "labels": labels or {},
            "enabled": True
        }
    
    def remove_alert_rule(self, rule_name: str) -> bool:
        """
        Remove alert rule.
        
        Args:
            rule_name: Rule name
            
        Returns:
            bool: True if rule was removed
        """
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            return True
        return False
    
    def check_alerts(self, metrics_collector: MetricsCollector) -> List[Alert]:
        """
        Check alert conditions.
        
        Args:
            metrics_collector: Metrics collector
            
        Returns:
            List[Alert]: Triggered alerts
        """
        if not self.alert_config["enable_alerts"]:
            return []
        
        triggered_alerts = []
        
        for rule_name, rule in self.alert_rules.items():
            if not rule["enabled"]:
                continue
            
            try:
                # Check condition
                if rule["condition"](metrics_collector):
                    alert = Alert(
                        alert_id=f"{rule_name}_{int(time.time())}",
                        name=rule_name,
                        severity=rule["severity"],
                        message=rule["message"],
                        timestamp=datetime.now(),
                        labels=rule["labels"]
                    )
                    
                    triggered_alerts.append(alert)
                    self.alerts.append(alert)
                    
                    # Send notification
                    self._send_notification(alert)
            
            except Exception as e:
                logger.error(f"Error checking alert rule {rule_name}: {e}")
        
        return triggered_alerts
    
    def _send_notification(self, alert: Alert) -> None:
        """Send alert notification."""
        for channel in self.alert_config["notification_channels"]:
            try:
                if channel == "log":
                    log_level = {
                        AlertSeverity.INFO: logging.INFO,
                        AlertSeverity.WARNING: logging.WARNING,
                        AlertSeverity.ERROR: logging.ERROR,
                        AlertSeverity.CRITICAL: logging.CRITICAL
                    }.get(alert.severity, logging.INFO)
                    
                    logger.log(log_level, f"ALERT [{alert.severity.value.upper()}] {alert.name}: {alert.message}")
                
                # Add other notification channels here (email, slack, etc.)
            
            except Exception as e:
                logger.error(f"Error sending alert notification via {channel}: {e}")
    
    def get_alerts(self, severity: Optional[AlertSeverity] = None, 
                   resolved: Optional[bool] = None) -> List[Alert]:
        """
        Get alerts.
        
        Args:
            severity: Filter by severity
            resolved: Filter by resolved status
            
        Returns:
            List[Alert]: Filtered alerts
        """
        alerts = list(self.alerts)
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        return alerts
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            bool: True if alert was resolved
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                return True
        return False


class HealthMonitor:
    """Health monitoring for template framework."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize health monitor.
        
        Args:
            config: Health monitor configuration
        """
        self.config = config or {}
        
        # Health configuration
        self.health_config = {
            "check_interval": self.config.get("check_interval", 30),  # 30 seconds
            "timeout": self.config.get("timeout", 10),  # 10 seconds
            "unhealthy_threshold": self.config.get("unhealthy_threshold", 3)
        }
        
        # Health checks
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_status: Dict[str, Dict[str, Any]] = {}
        self.check_timer = None
        
        logger.info("HealthMonitor initialized")
    
    def add_health_check(self, name: str, check_function: Callable, 
                        interval: Optional[int] = None, timeout: Optional[int] = None) -> None:
        """
        Add health check.
        
        Args:
            name: Check name
            check_function: Health check function
            interval: Check interval
            timeout: Check timeout
        """
        health_check = HealthCheck(
            name=name,
            check_function=check_function,
            interval=interval or self.health_config["check_interval"],
            timeout=timeout or self.health_config["timeout"]
        )
        
        self.health_checks[name] = health_check
        self.health_status[name] = {
            "healthy": True,
            "last_check": None,
            "consecutive_failures": 0,
            "error_message": None
        }
        
        logger.info(f"Added health check: {name}")
    
    def remove_health_check(self, name: str) -> bool:
        """
        Remove health check.
        
        Args:
            name: Check name
            
        Returns:
            bool: True if check was removed
        """
        if name in self.health_checks:
            del self.health_checks[name]
            del self.health_status[name]
            return True
        return False
    
    def start_monitoring(self) -> None:
        """Start health monitoring."""
        if self.check_timer:
            self.check_timer.cancel()
        
        self._run_health_checks()
        self._start_check_timer()
        
        logger.info("Health monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        if self.check_timer:
            self.check_timer.cancel()
            self.check_timer = None
        
        logger.info("Health monitoring stopped")
    
    def _start_check_timer(self) -> None:
        """Start health check timer."""
        if self.check_timer:
            self.check_timer.cancel()
        
        # Find minimum interval
        min_interval = min(check.interval for check in self.health_checks.values())
        
        self.check_timer = threading.Timer(min_interval, self._run_health_checks)
        self.check_timer.daemon = True
        self.check_timer.start()
    
    def _run_health_checks(self) -> None:
        """Run all health checks."""
        current_time = datetime.now()
        
        for name, health_check in self.health_checks.items():
            status = self.health_status[name]
            
            # Check if enough time has passed since last check
            if (status["last_check"] and 
                (current_time - status["last_check"]).seconds < health_check.interval):
                continue
            
            try:
                # Run health check with timeout
                result = self._run_check_with_timeout(health_check)
                
                if result:
                    status["healthy"] = True
                    status["consecutive_failures"] = 0
                    status["error_message"] = None
                else:
                    status["healthy"] = False
                    status["consecutive_failures"] += 1
                    status["error_message"] = "Health check returned False"
                
                status["last_check"] = current_time
            
            except Exception as e:
                status["healthy"] = False
                status["consecutive_failures"] += 1
                status["error_message"] = str(e)
                status["last_check"] = current_time
                
                logger.error(f"Health check {name} failed: {e}")
        
        # Restart timer
        self._start_check_timer()
    
    def _run_check_with_timeout(self, health_check: HealthCheck) -> bool:
        """Run health check with timeout."""
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(health_check.check_function)
            
            try:
                result = future.result(timeout=health_check.timeout)
                return bool(result)
            
            except concurrent.futures.TimeoutError:
                logger.error(f"Health check {health_check.name} timed out")
                return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status.
        
        Returns:
            Dict[str, Any]: Health status
        """
        total_checks = len(self.health_checks)
        healthy_checks = sum(1 for status in self.health_status.values() if status["healthy"])
        
        overall_health = "healthy"
        if healthy_checks == 0:
            overall_health = "unhealthy"
        elif healthy_checks < total_checks:
            overall_health = "degraded"
        
        return {
            "overall_health": overall_health,
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "unhealthy_checks": total_checks - healthy_checks,
            "health_percentage": (healthy_checks / total_checks * 100) if total_checks > 0 else 0,
            "checks": self.health_status.copy(),
            "last_updated": datetime.now().isoformat()
        }
    
    def get_check_status(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get status of specific health check.
        
        Args:
            name: Check name
            
        Returns:
            Optional[Dict[str, Any]]: Check status
        """
        return self.health_status.get(name)


class ObservabilityManager:
    """Main observability manager."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize observability manager.
        
        Args:
            config: Observability configuration
        """
        self.config = config or {}
        
        # Initialize components
        self.metrics_collector = MetricsCollector(config)
        self.alert_manager = AlertManager(config)
        self.health_monitor = HealthMonitor(config)
        
        # Observability configuration
        self.observability_config = {
            "enable_metrics": self.config.get("enable_metrics", True),
            "enable_alerts": self.config.get("enable_alerts", True),
            "enable_health_checks": self.config.get("enable_health_checks", True),
            "export_interval": self.config.get("export_interval", 300)  # 5 minutes
        }
        
        # Export timer
        self.export_timer = None
        
        # Setup default alert rules
        self._setup_default_alerts()
        
        # Setup default health checks
        self._setup_default_health_checks()
        
        logger.info("ObservabilityManager initialized")
    
    def _setup_default_alerts(self) -> None:
        """Setup default alert rules."""
        # High error rate alert
        self.alert_manager.add_alert_rule(
            "high_error_rate",
            lambda mc: self._get_error_rate(mc) > 0.1,  # 10% error rate
            AlertSeverity.WARNING,
            "High error rate detected (>10%)",
            {"component": "template_framework"}
        )
        
        # High memory usage alert
        self.alert_manager.add_alert_rule(
            "high_memory_usage",
            lambda mc: self._get_memory_usage(mc) > 0.8,  # 80% memory usage
            AlertSeverity.WARNING,
            "High memory usage detected (>80%)",
            {"component": "template_framework"}
        )
        
        # Template execution timeout alert
        self.alert_manager.add_alert_rule(
            "template_timeout",
            lambda mc: self._get_timeout_rate(mc) > 0.05,  # 5% timeout rate
            AlertSeverity.ERROR,
            "High template timeout rate detected (>5%)",
            {"component": "template_framework"}
        )
    
    def _setup_default_health_checks(self) -> None:
        """Setup default health checks."""
        # Metrics collector health check
        self.health_monitor.add_health_check(
            "metrics_collector",
            lambda: self._check_metrics_collector_health(),
            interval=60
        )
        
        # Alert manager health check
        self.health_monitor.add_health_check(
            "alert_manager",
            lambda: self._check_alert_manager_health(),
            interval=60
        )
        
        # Template framework health check
        self.health_monitor.add_health_check(
            "template_framework",
            lambda: self._check_template_framework_health(),
            interval=30
        )
    
    def _get_error_rate(self, metrics_collector: MetricsCollector) -> float:
        """Get error rate from metrics."""
        error_metrics = metrics_collector.get_metric("template_errors")
        total_metrics = metrics_collector.get_metric("template_executions")
        
        if not total_metrics or not error_metrics:
            return 0.0
        
        total_executions = sum(point.value for point in total_metrics)
        total_errors = sum(point.value for point in error_metrics)
        
        return total_errors / total_executions if total_executions > 0 else 0.0
    
    def _get_memory_usage(self, metrics_collector: MetricsCollector) -> float:
        """Get memory usage from metrics."""
        memory_metrics = metrics_collector.get_metric("memory_usage_bytes")
        
        if not memory_metrics:
            return 0.0
        
        latest_memory = memory_metrics[-1].value
        # Convert to percentage (assuming max 1GB)
        return latest_memory / (1024 * 1024 * 1024)
    
    def _get_timeout_rate(self, metrics_collector: MetricsCollector) -> float:
        """Get timeout rate from metrics."""
        timeout_metrics = metrics_collector.get_metric("template_timeouts")
        total_metrics = metrics_collector.get_metric("template_executions")
        
        if not total_metrics or not timeout_metrics:
            return 0.0
        
        total_executions = sum(point.value for point in total_metrics)
        total_timeouts = sum(point.value for point in timeout_metrics)
        
        return total_timeouts / total_executions if total_executions > 0 else 0.0
    
    def _check_metrics_collector_health(self) -> bool:
        """Check metrics collector health."""
        try:
            # Try to record a test metric
            self.metrics_collector.record_counter("health_check_test", 1)
            return True
        except Exception:
            return False
    
    def _check_alert_manager_health(self) -> bool:
        """Check alert manager health."""
        try:
            # Check if alert manager is responsive
            return len(self.alert_manager.alert_rules) > 0
        except Exception:
            return False
    
    def _check_template_framework_health(self) -> bool:
        """Check template framework health."""
        try:
            # This would check framework-specific health indicators
            return True
        except Exception:
            return False
    
    def start_monitoring(self) -> None:
        """Start all monitoring components."""
        if self.observability_config["enable_health_checks"]:
            self.health_monitor.start_monitoring()
        
        if self.observability_config["enable_metrics"]:
            self._start_export_timer()
        
        logger.info("Observability monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop all monitoring components."""
        self.health_monitor.stop_monitoring()
        
        if self.export_timer:
            self.export_timer.cancel()
            self.export_timer = None
        
        logger.info("Observability monitoring stopped")
    
    def _start_export_timer(self) -> None:
        """Start export timer."""
        if self.export_timer:
            self.export_timer.cancel()
        
        self.export_timer = threading.Timer(
            self.observability_config["export_interval"],
            self._export_metrics
        )
        self.export_timer.daemon = True
        self.export_timer.start()
    
    def _export_metrics(self) -> None:
        """Export metrics to external systems."""
        try:
            # This would export metrics to monitoring systems like Prometheus, etc.
            logger.debug("Metrics exported")
            
            # Restart timer
            self._start_export_timer()
        
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
    
    def get_observability_status(self) -> Dict[str, Any]:
        """
        Get observability status.
        
        Returns:
            Dict[str, Any]: Observability status
        """
        return {
            "metrics": {
                "enabled": self.observability_config["enable_metrics"],
                "summary": self.metrics_collector.get_metrics_summary()
            },
            "alerts": {
                "enabled": self.observability_config["enable_alerts"],
                "total_alerts": len(self.alert_manager.alerts),
                "active_alerts": len([a for a in self.alert_manager.alerts if not a.resolved]),
                "recent_alerts": [asdict(a) for a in list(self.alert_manager.alerts)[-10:]]
            },
            "health": {
                "enabled": self.observability_config["enable_health_checks"],
                "status": self.health_monitor.get_health_status()
            },
            "configuration": self.observability_config
        }
    
    def cleanup(self) -> None:
        """Cleanup observability manager."""
        self.stop_monitoring()
        self.metrics_collector.cleanup()


# Global observability manager instance
_global_observability_manager = None


def get_global_observability_manager(config: Optional[Dict[str, Any]] = None) -> ObservabilityManager:
    """Get global observability manager instance."""
    global _global_observability_manager
    if _global_observability_manager is None:
        _global_observability_manager = ObservabilityManager(config)
    return _global_observability_manager
