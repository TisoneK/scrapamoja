"""
Storage Usage Monitoring for Selector Telemetry System

This module provides comprehensive storage monitoring capabilities including
usage tracking, capacity planning, performance monitoring, and
alerting.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import uuid
from pathlib import Path
import json

from ..models.selector_models import SeverityLevel
from .logging import get_telemetry_logger


class MetricType(Enum):
    """Types of storage metrics"""
    CAPACITY = "capacity"
    USAGE = "usage"
    PERFORMANCE = "performance"
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class StorageMetric:
    """Storage metric data"""
    metric_id: str
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    source: str
    tags: Dict[str, str] = None


@dataclass
class StorageAlert:
    """Storage alert"""
    alert_id: str
    metric_type: MetricType
    severity: AlertSeverity
    title: str
    message: str
    threshold_value: float
    actual_value: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class CapacityForecast:
    """Storage capacity forecast"""
    forecast_id: str
    storage_path: str
    current_usage_gb: float
    total_capacity_gb: float
    projected_usage_gb: float
    days_until_full: int
    confidence: float
    forecast_date: datetime
    recommendations: List[str]


class StorageMonitoring:
    """
    Comprehensive storage monitoring system
    
    This class provides storage monitoring capabilities:
    - Real-time usage monitoring
    - Capacity planning and forecasting
    - Performance monitoring
    - Alerting and notifications
    - Trend analysis
    - Historical data tracking
    """
    
    def __init__(
        self,
        storage_manager,
        logger=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the storage monitoring system"""
        self.storage_manager = storage_manager
        self.logger = logger or get_telemetry_logger()
        self.config = config or {}
        
        # Metrics storage
        self._metrics = []
        self._alerts = {}
        self._forecasts = {}
        self._monitoring_lock = asyncio.Lock()
        
        # Monitoring thresholds
        self._thresholds = self._initialize_thresholds()
        
        # Monitoring statistics
        self._stats = {
            "metrics_collected": 0,
            "alerts_generated": 0,
            "forecasts_generated": 0,
            "last_collection": None,
            "last_alert": None
        }
        
        # Background monitoring
        self._monitoring_task = None
        self._running = False
    
    def _initialize_thresholds(self) -> Dict[MetricType, Dict[str, float]]:
        """Initialize monitoring thresholds"""
        return {
            MetricType.CAPACITY: {
                "warning": 0.8,    # 80% capacity
                "critical": 0.95   # 95% capacity
            },
            MetricType.USAGE: {
                "warning": 100.0,   # 100GB usage
                "critical": 500.0  # 500GB usage
            },
            MetricType.PERFORMANCE: {
                "warning": 100.0,   # 100ms response time
                "critical": 500.0  # 500ms response time
            },
            MetricType.ERROR_RATE: {
                "warning": 0.05,    # 5% error rate
                "critical": 0.10   # 10% error rate
            },
            MetricType.AVAILABILITY: {
                "warning": 0.99,    # 99% availability
                "critical": 0.95   # 95% availability
            }
        }
    
    async def collect_metrics(self, metric_types: Optional[List[MetricType]] = None) -> List[StorageMetric]:
        """
        Collect storage metrics
        
        Args:
            metric_types: Types of metrics to collect
            
        Returns:
            List[StorageMetric]: Collected metrics
        """
        if metric_types is None:
            metric_types = list(MetricType)
        
        metrics = []
        timestamp = datetime.now()
        
        for metric_type in metric_types:
            try:
                metric = await self._collect_metric(metric_type, timestamp)
                if metric:
                    metrics.append(metric)
            except Exception as e:
                self.logger.error(f"Error collecting {metric_type.value} metric: {e}")
        
        # Store metrics
        async with self._monitoring_lock:
            self._metrics.extend(metrics)
            self._stats["metrics_collected"] += len(metrics)
            self._stats["last_collection"] = timestamp
        
        # Check for alerts
        await self._check_alerts(metrics)
        
        return metrics
    
    async def _collect_metric(self, metric_type: MetricType, timestamp: datetime) -> Optional[StorageMetric]:
        """Collect a specific metric"""
        metric_id = str(uuid.uuid4())
        
        if metric_type == MetricType.CAPACITY:
            # Mock capacity metrics
            value = 0.75  # 75% capacity
            return StorageMetric(
                metric_id=metric_id,
                metric_type=metric_type,
                value=value,
                unit="percentage",
                timestamp=timestamp,
                source="storage_monitor",
                tags={"storage_type": "ssd"}
            )
        
        elif metric_type == MetricType.USAGE:
            # Mock usage metrics
            value = 250.0  # 250GB usage
            return StorageMetric(
                metric_id=metric_id,
                metric_type=metric_type,
                value=value,
                unit="gb",
                timestamp=timestamp,
                source="storage_monitor",
                tags={"storage_type": "ssd"}
            )
        
        elif metric_type == MetricType.PERFORMANCE:
            # Mock performance metrics
            value = 45.2  # 45.2ms response time
            return StorageMetric(
                metric_id=metric_id,
                metric_type=metric_type,
                value=value,
                unit="ms",
                timestamp=timestamp,
                source="storage_monitor",
                tags={"operation": "read"}
            )
        
        elif metric_type == MetricType.ERROR_RATE:
            # Mock error rate metrics
            value = 0.02  # 2% error rate
            return StorageMetric(
                metric_id=metric_id,
                metric_type=metric_type,
                value=value,
                unit="percentage",
                timestamp=timestamp,
                source="storage_monitor",
                tags={}
            )
        
        elif metric_type == MetricType.AVAILABILITY:
            # Mock availability metrics
            value = 0.998  # 99.8% availability
            return StorageMetric(
                metric_id=metric_id,
                metric_type=metric_type,
                value=value,
                unit="percentage",
                timestamp=timestamp,
                source="storage_monitor",
                tags={}
            )
        
        return None
    
    async def _check_alerts(self, metrics: List[StorageMetric]) -> None:
        """Check metrics against thresholds and generate alerts"""
        for metric in metrics:
            thresholds = self._thresholds.get(metric.metric_type, {})
            
            # Check warning threshold
            warning_threshold = thresholds.get("warning")
            if warning_threshold and metric.value >= warning_threshold:
                await self._create_alert(
                    metric, AlertSeverity.WARNING, warning_threshold
                )
            
            # Check critical threshold
            critical_threshold = thresholds.get("critical")
            if critical_threshold and metric.value >= critical_threshold:
                await self._create_alert(
                    metric, AlertSeverity.CRITICAL, critical_threshold
                )
    
    async def _create_alert(
        self,
        metric: StorageMetric,
        severity: AlertSeverity,
        threshold: float
    ) -> None:
        """Create a storage alert"""
        alert_id = str(uuid.uuid4())
        
        alert = StorageAlert(
            alert_id=alert_id,
            metric_type=metric.metric_type,
            severity=severity,
            title=f"{severity.value.title()}: {metric.metric_type.value.title()} Alert",
            message=f"{metric.metric_type.value} ({metric.value}{metric.unit}) exceeds {severity.value} threshold ({threshold}{metric.unit})",
            threshold_value=threshold,
            actual_value=metric.value,
            timestamp=metric.timestamp
        )
        
        async with self._monitoring_lock:
            self._alerts[alert_id] = alert
            self._stats["alerts_generated"] += 1
            self._stats["last_alert"] = metric.timestamp
        
        self.logger.warning(
            f"Storage alert generated: {alert.title}",
            alert_id=alert_id,
            severity=severity.value,
            metric_type=metric.metric_type.value,
            actual_value=metric.value,
            threshold=threshold
        )
    
    async def generate_capacity_forecast(
        self,
        storage_path: str,
        forecast_days: int = 30
    ) -> CapacityForecast:
        """
        Generate capacity forecast for storage
        
        Args:
            storage_path: Storage path to forecast
            forecast_days: Number of days to forecast
            
        Returns:
            CapacityForecast: Capacity forecast
        """
        forecast_id = str(uuid.uuid4())
        
        # Mock forecast calculation
        current_usage_gb = 250.0
        total_capacity_gb = 1000.0
        daily_growth_rate = 2.5  # 2.5GB per day
        
        projected_usage_gb = current_usage_gb + (daily_growth_rate * forecast_days)
        days_until_full = int((total_capacity_gb - current_usage_gb) / daily_growth_rate)
        
        forecast = CapacityForecast(
            forecast_id=forecast_id,
            storage_path=storage_path,
            current_usage_gb=current_usage_gb,
            total_capacity_gb=total_capacity_gb,
            projected_usage_gb=projected_usage_gb,
            days_until_full=days_until_full,
            confidence=0.85,
            forecast_date=datetime.now(),
            recommendations=[
                "Plan storage expansion in 300 days",
                "Implement data archiving to reduce usage",
                "Monitor growth trends regularly"
            ]
        )
        
        # Store forecast
        async with self._monitoring_lock:
            self._forecasts[forecast_id] = forecast
            self._stats["forecasts_generated"] += 1
        
        return forecast
    
    async def get_metrics(
        self,
        metric_type: Optional[MetricType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[StorageMetric]:
        """Get collected metrics with optional filtering"""
        async with self._monitoring_lock:
            metrics = self._metrics.copy()
        
        # Filter by metric type
        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]
        
        # Filter by time range
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]
        
        # Sort by timestamp (newest first) and limit
        metrics.sort(key=lambda x: x.timestamp, reverse=True)
        
        return metrics[:limit]
    
    async def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        resolved: Optional[bool] = None,
        limit: int = 100
    ) -> List[StorageAlert]:
        """Get storage alerts with optional filtering"""
        async with self._monitoring_lock:
            alerts = list(self._alerts.values())
        
        # Filter by severity
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Filter by resolved status
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        # Sort by timestamp (newest first) and limit
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return alerts[:limit]
    
    async def get_forecasts(self, storage_path: Optional[str] = None) -> List[CapacityForecast]:
        """Get capacity forecasts"""
        async with self._monitoring_lock:
            forecasts = list(self._forecasts.values())
        
        # Filter by storage path
        if storage_path:
            forecasts = [f for f in forecasts if f.storage_path == storage_path]
        
        # Sort by forecast date (newest first)
        forecasts.sort(key=lambda x: x.forecast_date, reverse=True)
        
        return forecasts
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a storage alert"""
        async with self._monitoring_lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                return False
            
            alert.resolved = True
            alert.resolved_at = datetime.now()
        
        self.logger.info(f"Resolved storage alert {alert_id}")
        return True
    
    async def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        async with self._monitoring_lock:
            active_alerts = len([a for a in self._alerts.values() if not a.resolved])
            total_metrics = len(self._metrics)
            total_alerts = len(self._alerts)
            total_forecasts = len(self._forecasts)
        
        return {
            **self._stats,
            "active_alerts": active_alerts,
            "total_metrics": total_metrics,
            "total_alerts": total_alerts,
            "total_forecasts": total_forecasts,
            "scheduler_running": self._running
        }
    
    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start background storage monitoring"""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval_seconds))
        
        self.logger.info(f"Started storage monitoring with {interval_seconds} second interval")
    
    async def stop_monitoring(self) -> None:
        """Stop background storage monitoring"""
        if not self._running:
            return
        
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Stopped storage monitoring")
    
    async def _monitoring_loop(self, interval_seconds: int) -> None:
        """Background monitoring loop"""
        while self._running:
            try:
                await self.collect_metrics()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying
