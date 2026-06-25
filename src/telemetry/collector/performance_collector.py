"""
Performance Timing Collector

Specialized collector for performance timing metrics with
high-precision measurement and timing analysis capabilities.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from statistics import mean, median, stdev

from ..models import PerformanceMetrics
from ..configuration.telemetry_config import TelemetryConfiguration
from ..utils import TimingMeasurement
from ..exceptions import TelemetryCollectionError
from ..configuration.logging import get_logger


@dataclass
class TimingStats:
    """Statistics for timing measurements."""
    total_measurements: int = 0
    average_time_ms: float = 0.0
    median_time_ms: float = 0.0
    min_time_ms: float = 0.0
    max_time_ms: float = 0.0
    std_deviation_ms: float = 0.0
    percentiles: Dict[str, float] = None
    last_measurement: Optional[datetime] = None
    
    def __post_init__(self):
        if self.percentiles is None:
            self.percentiles = {}


class PerformanceCollector:
    """
    Specialized collector for performance timing metrics.
    
    Provides high-precision timing measurement, statistical analysis,
    and performance trend tracking for selector operations.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize performance collector.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("performance_collector")
        
        # Timing configuration
        self.precision_ms = config.get("timing_precision_ms", 0.1)
        self.max_samples = config.get("max_timing_samples", 10000)
        self.aggregation_window = timedelta(minutes=config.get("aggregation_window_minutes", 5))
        
        # Timing storage
        self._timing_samples: List[Dict[str, Any]] = []
        self._timing_stats: Dict[str, TimingStats] = {}
        self._stats_lock = asyncio.Lock()
        
        # Performance thresholds
        self._thresholds = {
            "resolution_time_ms": config.get("resolution_time_threshold_ms", 5000),
            "strategy_execution_time_ms": config.get("strategy_time_threshold_ms", 1000),
            "total_duration_ms": config.get("total_duration_threshold_ms", 10000)
        }
        
        # Collection state
        self._enabled = True
        self._collection_count = 0
        self._error_count = 0
    
    async def collect_timing_metrics(
        self,
        selector_name: str,
        operation_type: str,
        start_time: datetime,
        end_time: datetime,
        strategy_name: Optional[str] = None,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> PerformanceMetrics:
        """
        Collect timing metrics for an operation.
        
        Args:
            selector_name: Name of selector
            operation_type: Type of operation
            start_time: Start time of operation
            end_time: End time of operation
            strategy_name: Optional strategy name
            additional_metrics: Additional timing metrics
            
        Returns:
            PerformanceMetrics instance
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        try:
            if not self._enabled:
                raise TelemetryCollectionError(
                    "Performance collector is disabled",
                    error_code="TEL-301"
                )
            
            # Calculate timing metrics
            total_duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Create performance metrics
            metrics = PerformanceMetrics(
                resolution_time_ms=additional_metrics.get("resolution_time_ms", 0) if additional_metrics else 0,
                strategy_execution_time_ms=additional_metrics.get("strategy_execution_time_ms", 0) if additional_metrics else 0,
                total_duration_ms=total_duration_ms,
                memory_usage_mb=additional_metrics.get("memory_usage_mb") if additional_metrics else None,
                cpu_usage_percent=additional_metrics.get("cpu_usage_percent") if additional_metrics else None,
                network_requests_count=additional_metrics.get("network_requests_count") if additional_metrics else None,
                dom_operations_count=additional_metrics.get("dom_operations_count") if additional_metrics else None
            )
            
            # Store timing sample
            await self._store_timing_sample(
                selector_name,
                operation_type,
                strategy_name,
                metrics,
                start_time,
                end_time
            )
            
            # Update statistics
            await self._update_statistics(selector_name, metrics)
            
            self._collection_count += 1
            
            self.logger.debug(
                "Timing metrics collected",
                selector_name=selector_name,
                operation_type=operation_type,
                total_duration_ms=total_duration_ms
            )
            
            return metrics
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(
                "Failed to collect timing metrics",
                selector_name=selector_name,
                operation_type=operation_type,
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to collect timing metrics: {e}",
                error_code="TEL-302"
            )
    
    async def measure_operation(
        self,
        selector_name: str,
        operation_type: str,
        strategy_name: Optional[str] = None,
        additional_metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for measuring operation timing.
        
        Args:
            selector_name: Name of selector
            operation_type: Type of operation
            strategy_name: Optional strategy name
            additional_metrics: Additional timing metrics
            
        Returns:
            Context manager for timing measurement
        """
        return PerformanceMeasurementContext(
            self,
            selector_name,
            operation_type,
            strategy_name,
            additional_metrics
        )
    
    async def get_timing_statistics(
        self,
        selector_name: Optional[str] = None,
        operation_type: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get timing statistics.
        
        Args:
            selector_name: Optional selector filter
            operation_type: Optional operation type filter
            time_window: Optional time window for statistics
            
        Returns:
            Timing statistics
        """
        try:
            async with self._stats_lock:
                if selector_name:
                    return self._get_selector_stats(selector_name, time_window)
                elif operation_type:
                    return self._get_operation_type_stats(operation_type, time_window)
                else:
                    return self._get_overall_stats(time_window)
                    
        except Exception as e:
            self.logger.error(
                "Failed to get timing statistics",
                selector_name=selector_name,
                operation_type=operation_type,
                error=str(e)
            )
            return {}
    
    async def detect_performance_anomalies(
        self,
        selector_name: Optional[str] = None,
        threshold_multiplier: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Detect performance anomalies based on historical data.
        
        Args:
            selector_name: Optional selector filter
            threshold_multiplier: Multiplier for anomaly threshold
            
        Returns:
            List of detected anomalies
        """
        try:
            anomalies = []
            
            # Get relevant samples
            samples = await self._get_filtered_samples(selector_name)
            
            if len(samples) < 10:
                return anomalies  # Not enough data for anomaly detection
            
            # Group by metric type
            metrics_data = self._group_samples_by_metric(samples)
            
            for metric_name, values in metrics_data.items():
                if len(values) < 10:
                    continue
                
                # Calculate statistics
                mean_value = mean(values)
                std_dev = stdev(values) if len(values) > 1 else 0
                
                # Detect anomalies (values beyond threshold * std_dev)
                threshold = mean_value + (threshold_multiplier * std_dev)
                
                anomalous_samples = [
                    sample for sample in samples
                    if sample.get("metrics", {}).get(metric_name, 0) > threshold
                ]
                
                for sample in anomalous_samples:
                    value = sample["metrics"][metric_name]
                    anomalies.append({
                        "selector_name": sample["selector_name"],
                        "operation_type": sample["operation_type"],
                        "metric_name": metric_name,
                        "value": value,
                        "threshold": threshold,
                        "timestamp": sample["end_time"],
                        "severity": "high" if value > threshold * 1.5 else "medium",
                        "deviation": (value - mean_value) / std_dev if std_dev > 0 else 0
                    })
            
            return anomalies
            
        except Exception as e:
            self.logger.error(
                "Failed to detect performance anomalies",
                selector_name=selector_name,
                error=str(e)
            )
            return []
    
    async def get_performance_trends(
        self,
        selector_name: Optional[str] = None,
        time_window: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """
        Analyze performance trends over time.
        
        Args:
            selector_name: Optional selector filter
            time_window: Time window for trend analysis
            
        Returns:
            Performance trend analysis
        """
        try:
            # Get samples within time window
            cutoff_time = datetime.utcnow() - time_window
            samples = [
                sample for sample in self._timing_samples
                if sample["end_time"] >= cutoff_time and
                (not selector_name or sample["selector_name"] == selector_name)
            ]
            
            if len(samples) < 2:
                return {"trend": "insufficient_data"}
            
            # Analyze trends by metric
            trends = {}
            
            for metric_name in ["resolution_time_ms", "strategy_execution_time_ms", "total_duration_ms"]:
                values = [
                    sample["metrics"].get(metric_name, 0)
                    for sample in samples
                    if metric_name in sample.get("metrics", {})
                ]
                
                if len(values) >= 2:
                    trend = self._calculate_trend(values, samples)
                    trends[metric_name] = trend
            
            return {
                "time_window_hours": time_window.total_seconds() / 3600,
                "samples_analyzed": len(samples),
                "trends": trends
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get performance trends",
                selector_name=selector_name,
                error=str(e)
            )
            return {}
    
    async def optimize_performance_thresholds(self) -> Dict[str, Any]:
        """
        Optimize performance thresholds based on historical data.
        
        Returns:
            Optimized thresholds
        """
        try:
            optimized_thresholds = {}
            
            # Get overall statistics
            overall_stats = await self.get_timing_statistics()
            
            for metric_name, current_threshold in self._thresholds.items():
                # Get percentile-based threshold (95th percentile)
                percentile_95 = overall_stats.get("percentiles", {}).get("p95", {}).get(metric_name, current_threshold)
                
                # Calculate optimized threshold (current + 20% of 95th percentile)
                optimized_threshold = current_threshold + (percentile_95 - current_threshold) * 0.2
                
                optimized_thresholds[metric_name] = {
                    "current": current_threshold,
                    "optimized": optimized_threshold,
                    "percentile_95": percentile_95,
                    "recommendation": "increase" if optimized_threshold > current_threshold else "decrease"
                }
            
            return optimized_thresholds
            
        except Exception as e:
            self.logger.error(
                "Failed to optimize performance thresholds",
                error=str(e)
            )
            return {}
    
    async def get_collection_statistics(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Collection statistics
        """
        return {
            "total_collections": self._collection_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(1, self._collection_count),
            "samples_stored": len(self._timing_samples),
            "selectors_tracked": len(set(s["selector_name"] for s in self._timing_samples)),
            "enabled": self._enabled,
            "precision_ms": self.precision_ms,
            "max_samples": self.max_samples
        }
    
    async def enable_collection(self) -> None:
        """Enable performance collection."""
        self._enabled = True
        self.logger.info("Performance collection enabled")
    
    async def disable_collection(self) -> None:
        """Disable performance collection."""
        self._enabled = False
        self.logger.info("Performance collection disabled")
    
    async def clear_samples(self, selector_name: Optional[str] = None) -> int:
        """
        Clear timing samples.
        
        Args:
            selector_name: Optional selector filter
            
        Returns:
            Number of samples cleared
        """
        async with self._stats_lock:
            if selector_name:
                original_count = len(self._timing_samples)
                self._timing_samples = [
                    sample for sample in self._timing_samples
                    if sample["selector_name"] != selector_name
                ]
                cleared_count = original_count - len(self._timing_samples)
                
                # Clear selector statistics
                if selector_name in self._timing_stats:
                    del self._timing_stats[selector_name]
            else:
                cleared_count = len(self._timing_samples)
                self._timing_samples.clear()
                self._timing_stats.clear()
            
            self.logger.info(
                "Timing samples cleared",
                selector_name=selector_name or "all",
                cleared_count=cleared_count
            )
            
            return cleared_count
    
    # Private methods
    
    async def _store_timing_sample(
        self,
        selector_name: str,
        operation_type: str,
        strategy_name: Optional[str],
        metrics: PerformanceMetrics,
        start_time: datetime,
        end_time: datetime
    ) -> None:
        """Store timing sample."""
        sample = {
            "selector_name": selector_name,
            "operation_type": operation_type,
            "strategy_name": strategy_name,
            "metrics": metrics.to_dict(),
            "start_time": start_time,
            "end_time": end_time,
            "timestamp": datetime.utcnow()
        }
        
        async with self._stats_lock:
            self._timing_samples.append(sample)
            
            # Limit sample size
            if len(self._timing_samples) > self.max_samples:
                self._timing_samples = self._timing_samples[-self.max_samples:]
    
    async def _update_statistics(self, selector_name: str, metrics: PerformanceMetrics) -> None:
        """Update timing statistics for selector."""
        async with self._stats_lock:
            if selector_name not in self._timing_stats:
                self._timing_stats[selector_name] = TimingStats()
            
            stats = self._timing_stats[selector_name]
            
            # Update basic stats
            stats.total_measurements += 1
            stats.last_measurement = datetime.utcnow()
            
            # Update with new measurement
            self._recalculate_stats(selector_name)
    
    async def _recalculate_stats(self, selector_name: str) -> None:
        """Recalculate statistics for selector."""
        selector_samples = [
            sample for sample in self._timing_samples
            if sample["selector_name"] == selector_name
        ]
        
        if not selector_samples:
            return
        
        # Extract total duration values
        durations = [
            sample["metrics"]["total_duration_ms"]
            for sample in selector_samples
            if "total_duration_ms" in sample["metrics"]
        ]
        
        if not durations:
            return
        
        stats = self._timing_stats[selector_name]
        
        # Calculate statistics
        stats.average_time_ms = mean(durations)
        stats.median_time_ms = median(durations)
        stats.min_time_ms = min(durations)
        stats.max_time_ms = max(durations)
        
        if len(durations) > 1:
            stats.std_deviation_ms = stdev(durations)
            
            # Calculate percentiles
            sorted_durations = sorted(durations)
            n = len(sorted_durations)
            
            stats.percentiles = {
                "p50": sorted_durations[int(n * 0.5)],
                "p90": sorted_durations[int(n * 0.9)],
                "p95": sorted_durations[int(n * 0.95)],
                "p99": sorted_durations[int(n * 0.99)]
            }
    
    def _get_selector_stats(self, selector_name: str, time_window: Optional[timedelta]) -> Dict[str, Any]:
        """Get statistics for specific selector."""
        # Use asyncio.run to handle async lock in sync context
        loop = asyncio.get_event_loop()
        
        async def _get_stats_async():
            async with self._stats_lock:
                if selector_name not in self._timing_stats:
                    return {}
                
                stats = self._timing_stats[selector_name]
                
                result = {
                    "selector_name": selector_name,
                    "total_measurements": stats.total_measurements,
                    "average_time_ms": stats.average_time_ms,
                    "median_time_ms": stats.median_time_ms,
                    "min_time_ms": stats.min_time_ms,
                    "max_time_ms": stats.max_time_ms,
                    "std_deviation_ms": stats.std_deviation_ms,
                    "percentiles": stats.percentiles,
                    "last_measurement": stats.last_measurement
                }
                
                # Filter by time window if specified
                if time_window:
                    cutoff_time = datetime.utcnow() - time_window
                    recent_samples = [
                        sample for sample in self._timing_samples
                        if sample["selector_name"] == selector_name and
                        sample["end_time"] >= cutoff_time
                    ]
                    
                    if recent_samples:
                        durations = [
                            sample["metrics"]["total_duration_ms"]
                            for sample in recent_samples
                            if "total_duration_ms" in sample["metrics"]
                        ]
                        
                        if durations:
                            result["recent_average"] = mean(durations)
                            result["recent_count"] = len(durations)
                    else:
                        result["recent_average"] = 0
                        result["recent_count"] = 0
                
                return result
        
        return loop.run_until_complete(_get_stats_async())
    
    def _get_operation_type_stats(self, operation_type: str, time_window: Optional[timedelta]) -> Dict[str, Any]:
        """Get statistics for specific operation type."""
        samples = [
            sample for sample in self._timing_samples
            if sample["operation_type"] == operation_type
        ]
        
        if time_window:
            cutoff_time = datetime.utcnow() - time_window
            samples = [
                sample for sample in samples
                if sample["end_time"] >= cutoff_time
            ]
        
        if not samples:
            return {}
        
        # Extract durations
        durations = [
            sample["metrics"]["total_duration_ms"]
            for sample in samples
            if "total_duration_ms" in sample["metrics"]
        ]
        
        if not durations:
            return {}
        
        return {
            "operation_type": operation_type,
            "total_measurements": len(samples),
            "average_time_ms": mean(durations),
            "median_time_ms": median(durations),
            "min_time_ms": min(durations),
            "max_time_ms": max(durations),
            "std_deviation_ms": stdev(durations) if len(durations) > 1 else 0
        }
    
    def _get_overall_stats(self, time_window: Optional[timedelta]) -> Dict[str, Any]:
        """Get overall statistics."""
        samples = self._timing_samples
        
        if time_window:
            cutoff_time = datetime.utcnow() - time_window
            samples = [
                sample for sample in samples
                if sample["end_time"] >= cutoff_time
            ]
        
        if not samples:
            return {}
        
        # Extract durations
        durations = [
            sample["metrics"]["total_duration_ms"]
            for sample in samples
            if "total_duration_ms" in sample["metrics"]
        ]
        
        if not durations:
            return {}
        
        # Calculate percentiles
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        
        return {
            "total_measurements": len(samples),
            "average_time_ms": mean(durations),
            "median_time_ms": median(durations),
            "min_time_ms": min(durations),
            "max_time_ms": max(durations),
            "std_deviation_ms": stdev(durations) if len(durations) > 1 else 0,
            "percentiles": {
                "p50": sorted_durations[int(n * 0.5)],
                "p90": sorted_durations[int(n * 0.9)],
                "p95": sorted_durations[int(n * 0.95)],
                "p99": sorted_durations[int(n * 0.99)]
            }
        }
    
    async def _get_filtered_samples(self, selector_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get filtered timing samples."""
        if selector_name:
            return [
                sample for sample in self._timing_samples
                if sample["selector_name"] == selector_name
            ]
        else:
            return self._timing_samples.copy()
    
    def _group_samples_by_metric(self, samples: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Group samples by metric type."""
        metrics_data = {
            "resolution_time_ms": [],
            "strategy_execution_time_ms": [],
            "total_duration_ms": []
        }
        
        for sample in samples:
            metrics = sample.get("metrics", {})
            for metric_name in metrics_data:
                if metric_name in metrics:
                    metrics_data[metric_name].append(metrics[metric_name])
        
        return metrics_data
    
    def _calculate_trend(self, values: List[float], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trend for a series of values."""
        if len(values) < 2:
            return {"trend": "insufficient_data"}
        
        # Simple linear trend calculation
        first_value = values[0]
        last_value = values[-1]
        
        if first_value == 0:
            return {"trend": "stable"}
        
        percent_change = ((last_value - first_value) / first_value) * 100
        
        # Determine trend direction
        if abs(percent_change) < 5:
            trend_direction = "stable"
        elif percent_change > 0:
            trend_direction = "increasing"
        else:
            trend_direction = "decreasing"
        
        return {
            "trend": trend_direction,
            "percent_change": percent_change,
            "first_value": first_value,
            "last_value": last_value,
            "sample_count": len(values)
        }


class PerformanceMeasurementContext:
    """
    Context manager for automatic performance measurement.
    
    Provides automatic timing collection and metric recording
    for selector operations.
    """
    
    def __init__(
        self,
        collector: PerformanceCollector,
        selector_name: str,
        operation_type: str,
        strategy_name: Optional[str] = None,
        additional_metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize performance measurement context.
        
        Args:
            collector: Performance collector instance
            selector_name: Name of selector
            operation_type: Type of operation
            strategy_name: Optional strategy name
            additional_metrics: Additional timing metrics
        """
        self.collector = collector
        self.selector_name = selector_name
        self.operation_type = operation_type
        self.strategy_name = strategy_name
        self.additional_metrics = additional_metrics or {}
        
        # Measurement state
        self.start_time = None
        self.end_time = None
        self.metrics = None
    
    def __aenter__(self):
        """Enter context and start timing."""
        self.start_time = datetime.utcnow()
        return self
    
    def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context and complete timing."""
        self.end_time = datetime.utcnow()
        
        # This needs to be awaited, but __aexit__ can't be async
        # We'll need to handle this differently
        try:
            # Create a task to collect metrics
            loop = asyncio.get_event_loop()
            task = loop.create_task(self.collector.collect_timing_metrics(
                self.selector_name,
                self.operation_type,
                self.start_time,
                self.end_time,
                self.strategy_name,
                self.additional_metrics
            ))
            
            # Store the task result when it completes
            def store_result(task):
                try:
                    self.metrics = task.result()
                except Exception as e:
                    if hasattr(self.collector, 'logger'):
                        self.collector.logger.error(
                            "Failed to collect timing metrics in context",
                            selector_name=self.selector_name,
                            error=str(e)
                        )
            
            task.add_done_callback(store_result)
            
        except Exception as e:
            # Log error but don't raise to avoid masking original exception
            if hasattr(self.collector, 'logger'):
                self.collector.logger.error(
                    "Failed to collect timing metrics in context",
                    selector_name=self.selector_name,
                    error=str(e)
                )
    
    def get_metrics(self) -> Optional[PerformanceMetrics]:
        """Get collected metrics."""
        return self.metrics
    
    def get_duration_ms(self) -> Optional[float]:
        """Get operation duration in milliseconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None
