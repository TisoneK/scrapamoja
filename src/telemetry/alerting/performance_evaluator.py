"""
Performance Threshold Evaluator

Specialized evaluator for performance metrics with statistical
analysis, trend detection, and adaptive threshold adjustment.
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics
import math

from ..interfaces import Alert, AlertSeverity
from ..models import PerformanceMetrics, TelemetryEvent
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryAlertingError
from ..configuration.logging import get_logger


class PerformanceMetricType(Enum):
    """Performance metric types."""
    RESOLUTION_TIME = "resolution_time_ms"
    STRATEGY_EXECUTION_TIME = "strategy_execution_time_ms"
    TOTAL_DURATION = "total_duration_ms"
    MEMORY_USAGE = "memory_usage_mb"
    CPU_USAGE = "cpu_usage_percent"
    NETWORK_REQUESTS = "network_requests_count"
    DOM_OPERATIONS = "dom_operations_count"


class ThresholdAdjustmentStrategy(Enum):
    """Threshold adjustment strategies."""
    PERCENTILE_BASED = "percentile_based"
    STATISTICAL_BASED = "statistical_based"
    TREND_BASED = "trend_based"
    HYBRID = "hybrid"


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    threshold_id: str
    metric_type: PerformanceMetricType
    threshold_value: float
    severity: AlertSeverity
    adjustment_strategy: ThresholdAdjustmentStrategy
    percentile_target: float = 95.0
    statistical_multiplier: float = 2.0
    trend_sensitivity: float = 0.1
    min_samples: int = 10
    evaluation_window_minutes: int = 30
    adaptive_enabled: bool = True
    last_adjusted: Optional[datetime] = None
    adjustment_count: int = 0


@dataclass
class PerformanceEvaluation:
    """Result of performance evaluation."""
    threshold_id: str
    metric_type: PerformanceMetricType
    current_value: float
    threshold_value: float
    triggered: bool
    severity: AlertSeverity
    exceedance_ratio: float
    statistical_context: Dict[str, float]
    trend_context: Dict[str, Any]
    evaluation_time: datetime
    samples_evaluated: int
    adaptive_adjustment: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceStatistics:
    """Performance statistics for a metric."""
    metric_type: PerformanceMetricType
    samples_count: int
    mean_value: float
    median_value: float
    std_deviation: float
    min_value: float
    max_value: float
    percentiles: Dict[str, float]
    trend_slope: float
    trend_direction: str
    last_updated: datetime


class PerformanceEvaluator:
    """
    Specialized evaluator for performance metrics with adaptive thresholds.
    
    Provides comprehensive performance evaluation with statistical analysis,
    trend detection, and adaptive threshold adjustment.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize performance evaluator.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("performance_evaluator")
        
        # Evaluator configuration
        self.enabled = config.get("performance_evaluation_enabled", True)
        self.max_samples_per_metric = config.get("max_performance_samples", 1000)
        self.default_evaluation_window = timedelta(minutes=config.get("performance_evaluation_window_minutes", 30))
        
        # Performance data storage
        self._performance_data: Dict[PerformanceMetricType, deque] = defaultdict(lambda: deque(maxlen=self.max_samples_per_metric))
        self._performance_stats: Dict[PerformanceMetricType, PerformanceStatistics] = {}
        self._thresholds: Dict[str, PerformanceThreshold] = {}
        self._evaluation_lock = asyncio.Lock()
        
        # Evaluation history
        self._evaluation_history: List[PerformanceEvaluation] = []
        self._max_evaluations = config.get("max_performance_evaluations", 10000)
        
        # Initialize default thresholds
        self._initialize_default_thresholds()
    
    async def evaluate_performance_event(self, event: TelemetryEvent) -> List[PerformanceEvaluation]:
        """
        Evaluate performance metrics from a telemetry event.
        
        Args:
            event: TelemetryEvent to evaluate
            
        Returns:
            List of performance evaluations
            
        Raises:
            TelemetryAlertingError: If evaluation fails
        """
        if not self.enabled or not event.performance_metrics:
            return []
        
        try:
            evaluations = []
            
            async with self._evaluation_lock:
                # Extract performance metrics
                metrics = self._extract_performance_metrics(event)
                
                # Store performance data
                for metric_type, value in metrics.items():
                    if value is not None:
                        self._performance_data[metric_type].append({
                            "value": value,
                            "timestamp": event.timestamp,
                            "selector_name": event.selector_name,
                            "correlation_id": event.correlation_id
                        })
                
                # Update statistics
                await self._update_performance_statistics()
                
                # Evaluate thresholds
                for threshold_id, threshold in self._thresholds.items():
                    if threshold.metric_type in metrics:
                        evaluation = await self._evaluate_threshold(
                            threshold,
                            metrics[threshold.metric_type],
                            event
                        )
                        
                        if evaluation:
                            evaluations.append(evaluation)
                            self._evaluation_history.append(evaluation)
                            
                            # Check for adaptive adjustment
                            if threshold.adaptive_enabled:
                                await self._check_adaptive_adjustment(threshold, evaluation)
                
                # Limit evaluation history
                if len(self._evaluation_history) > self._max_evaluations:
                    self._evaluation_history = self._evaluation_history[-self._max_evaluations:]
            
            return evaluations
            
        except Exception as e:
            self.logger.error(
                "Failed to evaluate performance event",
                event_id=event.event_id,
                error=str(e)
            )
            raise TelemetryAlertingError(
                f"Failed to evaluate performance event: {e}",
                error_code="TEL-807"
            )
    
    async def evaluate_threshold(
        self,
        threshold_id: str,
        current_value: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[PerformanceEvaluation]:
        """
        Evaluate a specific performance threshold.
        
        Args:
            threshold_id: Threshold ID to evaluate
            current_value: Current metric value
            context: Additional context
            
        Returns:
            Performance evaluation or None if threshold not found
        """
        try:
            async with self._evaluation_lock:
                if threshold_id not in self._thresholds:
                    return None
                
                threshold = self._thresholds[threshold_id]
                
                # Create mock event for evaluation
                mock_event = type('MockEvent', (), {
                    'timestamp': datetime.utcnow(),
                    'selector_name': context.get('selector_name', 'unknown') if context else 'unknown',
                    'correlation_id': context.get('correlation_id') if context else None
                })()
                
                evaluation = await self._evaluate_threshold(threshold, current_value, mock_event)
                
                if evaluation:
                    self._evaluation_history.append(evaluation)
                    
                    # Check for adaptive adjustment
                    if threshold.adaptive_enabled:
                        await self._check_adaptive_adjustment(threshold, evaluation)
                
                return evaluation
                
        except Exception as e:
            self.logger.error(
                "Failed to evaluate performance threshold",
                threshold_id=threshold_id,
                error=str(e)
            )
            return None
    
    async def add_threshold(self, threshold: PerformanceThreshold) -> bool:
        """
        Add a performance threshold.
        
        Args:
            threshold: Performance threshold to add
            
        Returns:
            True if successfully added
        """
        try:
            async with self._evaluation_lock:
                self._thresholds[threshold.threshold_id] = threshold
            
            self.logger.info(
                "Performance threshold added",
                threshold_id=threshold.threshold_id,
                metric_type=threshold.metric_type.value,
                threshold_value=threshold.threshold_value
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add performance threshold",
                threshold_id=threshold.threshold_id,
                error=str(e)
            )
            return False
    
    async def remove_threshold(self, threshold_id: str) -> bool:
        """
        Remove a performance threshold.
        
        Args:
            threshold_id: Threshold ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            async with self._evaluation_lock:
                if threshold_id in self._thresholds:
                    del self._thresholds[threshold_id]
                    
                    self.logger.info(
                        "Performance threshold removed",
                        threshold_id=threshold_id
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove performance threshold",
                threshold_id=threshold_id,
                error=str(e)
            )
            return False
    
    async def get_performance_statistics(
        self,
        metric_type: Optional[PerformanceMetricType] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Args:
            metric_type: Optional metric type filter
            time_window: Optional time window for statistics
            
        Returns:
            Performance statistics
        """
        try:
            async with self._evaluation_lock:
                stats = {}
                
                if metric_type:
                    if metric_type in self._performance_stats:
                        stats[metric_type.value] = self._statistics_to_dict(
                            self._performance_stats[metric_type]
                        )
                else:
                    for mt, stat in self._performance_stats.items():
                        stats[mt.value] = self._statistics_to_dict(stat)
                
                # Apply time window filter if specified
                if time_window:
                    cutoff_time = datetime.utcnow() - time_window
                    filtered_stats = {}
                    
                    for mt, stat_dict in stats.items():
                        metric_type = PerformanceMetricType(mt)
                        if metric_type in self._performance_data:
                            recent_samples = [
                                sample for sample in self._performance_data[metric_type]
                                if sample["timestamp"] >= cutoff_time
                            ]
                            
                            if recent_samples:
                                values = [sample["value"] for sample in recent_samples]
                                filtered_stats[mt] = {
                                    "recent_samples": len(recent_samples),
                                    "recent_mean": statistics.mean(values),
                                    "recent_median": statistics.median(values),
                                    "recent_min": min(values),
                                    "recent_max": max(values)
                                }
                    
                    stats.update(filtered_stats)
                
                return stats
                
        except Exception as e:
            self.logger.error(
                "Failed to get performance statistics",
                metric_type=metric_type.value if metric_type else None,
                error=str(e)
            )
            return {}
    
    async def get_evaluation_history(
        self,
        threshold_id: Optional[str] = None,
        metric_type: Optional[PerformanceMetricType] = None,
        triggered_only: bool = False,
        limit: Optional[int] = None,
        time_window: Optional[timedelta] = None
    ) -> List[PerformanceEvaluation]:
        """
        Get evaluation history with filtering.
        
        Args:
            threshold_id: Optional threshold ID filter
            metric_type: Optional metric type filter
            triggered_only: Filter for triggered evaluations only
            limit: Optional limit on number of evaluations
            time_window: Optional time window for evaluations
            
        Returns:
            List of performance evaluations
        """
        try:
            async with self._evaluation_lock:
                evaluations = self._evaluation_history.copy()
                
                # Apply filters
                if threshold_id:
                    evaluations = [e for e in evaluations if e.threshold_id == threshold_id]
                
                if metric_type:
                    evaluations = [e for e in evaluations if e.metric_type == metric_type]
                
                if triggered_only:
                    evaluations = [e for e in evaluations if e.triggered]
                
                if time_window:
                    cutoff_time = datetime.utcnow() - time_window
                    evaluations = [e for e in evaluations if e.evaluation_time >= cutoff_time]
                
                # Sort by timestamp (newest first)
                evaluations.sort(key=lambda x: x.evaluation_time, reverse=True)
                
                # Apply limit
                if limit:
                    evaluations = evaluations[:limit]
                
                return evaluations
                
        except Exception as e:
            self.logger.error(
                "Failed to get evaluation history",
                error=str(e)
            )
            return []
    
    async def adjust_threshold_adaptively(
        self,
        threshold_id: str,
        strategy: Optional[ThresholdAdjustmentStrategy] = None
    ) -> bool:
        """
        Adaptively adjust a threshold based on historical data.
        
        Args:
            threshold_id: Threshold ID to adjust
            strategy: Optional adjustment strategy override
            
        Returns:
            True if successfully adjusted
        """
        try:
            async with self._evaluation_lock:
                if threshold_id not in self._thresholds:
                    return False
                
                threshold = self._thresholds[threshold_id]
                
                if not threshold.adaptive_enabled:
                    return False
                
                # Use provided strategy or threshold's strategy
                adjustment_strategy = strategy or threshold.adjustment_strategy
                
                # Calculate new threshold value
                new_threshold = await self._calculate_adaptive_threshold(
                    threshold,
                    adjustment_strategy
                )
                
                if new_threshold is None:
                    return False
                
                old_threshold = threshold.threshold_value
                threshold.threshold_value = new_threshold
                threshold.last_adjusted = datetime.utcnow()
                threshold.adjustment_count += 1
                
                self.logger.info(
                    "Threshold adaptively adjusted",
                    threshold_id=threshold_id,
                    old_threshold=old_threshold,
                    new_threshold=new_threshold,
                    strategy=adjustment_strategy.value
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to adjust threshold adaptively",
                threshold_id=threshold_id,
                error=str(e)
            )
            return False
    
    async def get_all_thresholds(self) -> List[PerformanceThreshold]:
        """
        Get all performance thresholds.
        
        Returns:
            List of all performance thresholds
        """
        try:
            async with self._evaluation_lock:
                return list(self._thresholds.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get all thresholds",
                error=str(e)
            )
            return []
    
    # Private methods
    
    def _initialize_default_thresholds(self) -> None:
        """Initialize default performance thresholds."""
        default_thresholds = [
            PerformanceThreshold(
                threshold_id="resolution_time_warning",
                metric_type=PerformanceMetricType.RESOLUTION_TIME,
                threshold_value=5000.0,
                severity=AlertSeverity.WARNING,
                adjustment_strategy=ThresholdAdjustmentStrategy.PERCENTILE_BASED,
                percentile_target=90.0
            ),
            PerformanceThreshold(
                threshold_id="resolution_time_critical",
                metric_type=PerformanceMetricType.RESOLUTION_TIME,
                threshold_value=10000.0,
                severity=AlertSeverity.ERROR,
                adjustment_strategy=ThresholdAdjustmentStrategy.PERCENTILE_BASED,
                percentile_target=95.0
            ),
            PerformanceThreshold(
                threshold_id="strategy_execution_time_warning",
                metric_type=PerformanceMetricType.STRATEGY_EXECUTION_TIME,
                threshold_value=1000.0,
                severity=AlertSeverity.WARNING,
                adjustment_strategy=ThresholdAdjustmentStrategy.STATISTICAL_BASED,
                statistical_multiplier=2.0
            ),
            PerformanceThreshold(
                threshold_id="memory_usage_high",
                metric_type=PerformanceMetricType.MEMORY_USAGE,
                threshold_value=500.0,
                severity=AlertSeverity.WARNING,
                adjustment_strategy=ThresholdAdjustmentStrategy.TREND_BASED,
                trend_sensitivity=0.1
            ),
            PerformanceThreshold(
                threshold_id="cpu_usage_high",
                metric_type=PerformanceMetricType.CPU_USAGE,
                threshold_value=80.0,
                severity=AlertSeverity.WARNING,
                adjustment_strategy=ThresholdAdjustmentStrategy.STATISTICAL_BASED,
                statistical_multiplier=1.5
            )
        ]
        
        for threshold in default_thresholds:
            self._thresholds[threshold.threshold_id] = threshold
    
    def _extract_performance_metrics(self, event: TelemetryEvent) -> Dict[PerformanceMetricType, Optional[float]]:
        """Extract performance metrics from event."""
        metrics = {}
        
        if event.performance_metrics:
            perf = event.performance_metrics
            
            metrics[PerformanceMetricType.RESOLUTION_TIME] = perf.resolution_time_ms
            metrics[PerformanceMetricType.STRATEGY_EXECUTION_TIME] = perf.strategy_execution_time_ms
            metrics[PerformanceMetricType.TOTAL_DURATION] = perf.total_duration_ms
            metrics[PerformanceMetricType.MEMORY_USAGE] = perf.memory_usage_mb
            metrics[PerformanceMetricType.CPU_USAGE] = perf.cpu_usage_percent
            metrics[PerformanceMetricType.NETWORK_REQUESTS] = perf.network_requests_count
            metrics[PerformanceMetricType.DOM_OPERATIONS] = perf.dom_operations_count
        
        return metrics
    
    async def _update_performance_statistics(self) -> None:
        """Update performance statistics for all metrics."""
        for metric_type, data_deque in self._performance_data.items():
            if len(data_deque) < 2:
                continue
            
            values = [sample["value"] for sample in data_deque]
            timestamps = [sample["timestamp"] for sample in data_deque]
            
            # Calculate basic statistics
            mean_value = statistics.mean(values)
            median_value = statistics.median(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
            min_value = min(values)
            max_value = max(values)
            
            # Calculate percentiles
            sorted_values = sorted(values)
            n = len(sorted_values)
            
            percentiles = {
                "p50": sorted_values[int(n * 0.5)],
                "p75": sorted_values[int(n * 0.75)],
                "p90": sorted_values[int(n * 0.9)],
                "p95": sorted_values[int(n * 0.95)],
                "p99": sorted_values[int(n * 0.99)]
            }
            
            # Calculate trend
            trend_slope, trend_direction = self._calculate_trend(timestamps, values)
            
            # Update statistics
            self._performance_stats[metric_type] = PerformanceStatistics(
                metric_type=metric_type,
                samples_count=len(values),
                mean_value=mean_value,
                median_value=median_value,
                std_deviation=std_dev,
                min_value=min_value,
                max_value=max_value,
                percentiles=percentiles,
                trend_slope=trend_slope,
                trend_direction=trend_direction,
                last_updated=datetime.utcnow()
            )
    
    def _calculate_trend(self, timestamps: List[datetime], values: List[float]) -> Tuple[float, str]:
        """Calculate trend slope and direction."""
        if len(values) < 2:
            return 0.0, "stable"
        
        # Convert timestamps to numeric values (seconds since first timestamp)
        time_values = [(t - timestamps[0]).total_seconds() for t in timestamps]
        
        # Simple linear regression
        n = len(values)
        sum_x = sum(time_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(time_values, values))
        sum_x2 = sum(x * x for x in time_values)
        
        # Calculate slope
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Determine direction
        if abs(slope) < 0.001:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        return slope, direction
    
    async def _evaluate_threshold(
        self,
        threshold: PerformanceThreshold,
        current_value: float,
        event: TelemetryEvent
    ) -> Optional[PerformanceEvaluation]:
        """Evaluate a performance threshold."""
        try:
            # Get statistical context
            statistical_context = await self._get_statistical_context(threshold.metric_type)
            
            # Get trend context
            trend_context = await self._get_trend_context(threshold.metric_type)
            
            # Evaluate threshold
            triggered = current_value > threshold.threshold_value
            
            # Calculate exceedance ratio
            exceedance_ratio = current_value / threshold.threshold_value if threshold.threshold_value > 0 else 1.0
            
            return PerformanceEvaluation(
                threshold_id=threshold.threshold_id,
                metric_type=threshold.metric_type,
                current_value=current_value,
                threshold_value=threshold.threshold_value,
                triggered=triggered,
                severity=threshold.severity,
                exceedance_ratio=exceedance_ratio,
                statistical_context=statistical_context,
                trend_context=trend_context,
                evaluation_time=datetime.utcnow(),
                samples_evaluated=len(self._performance_data[threshold.metric_type])
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to evaluate threshold",
                threshold_id=threshold.threshold_id,
                error=str(e)
            )
            return None
    
    async def _get_statistical_context(self, metric_type: PerformanceMetricType) -> Dict[str, float]:
        """Get statistical context for a metric."""
        if metric_type not in self._performance_stats:
            return {}
        
        stats = self._performance_stats[metric_type]
        
        return {
            "mean": stats.mean_value,
            "median": stats.median_value,
            "std_deviation": stats.std_deviation,
            "min": stats.min_value,
            "max": stats.max_value,
            "p50": stats.percentiles.get("p50", 0),
            "p75": stats.percentiles.get("p75", 0),
            "p90": stats.percentiles.get("p90", 0),
            "p95": stats.percentiles.get("p95", 0),
            "p99": stats.percentiles.get("p99", 0)
        }
    
    async def _get_trend_context(self, metric_type: PerformanceMetricType) -> Dict[str, Any]:
        """Get trend context for a metric."""
        if metric_type not in self._performance_stats:
            return {}
        
        stats = self._performance_stats[metric_type]
        
        return {
            "slope": stats.trend_slope,
            "direction": stats.trend_direction,
            "last_updated": stats.last_updated.isoformat()
        }
    
    async def _check_adaptive_adjustment(self, threshold: PerformanceThreshold, evaluation: PerformanceEvaluation) -> None:
        """Check if adaptive adjustment is needed."""
        if not threshold.adaptive_enabled:
            return
        
        # Check if enough time has passed since last adjustment
        if threshold.last_adjusted:
            time_since_adjustment = datetime.utcnow() - threshold.last_adjusted
            if time_since_adjustment < timedelta(hours=1):  # Don't adjust too frequently
                return
        
        # Check if adjustment criteria are met
        if evaluation.triggered and evaluation.exceedance_ratio > 2.0:
            # High exceedance - consider adjustment
            await self.adjust_threshold_adaptively(threshold.threshold_id)
    
    async def _calculate_adaptive_threshold(
        self,
        threshold: PerformanceThreshold,
        strategy: ThresholdAdjustmentStrategy
    ) -> Optional[float]:
        """Calculate adaptive threshold value."""
        try:
            if threshold.metric_type not in self._performance_stats:
                return None
            
            stats = self._performance_stats[threshold.metric_type]
            
            if strategy == ThresholdAdjustmentStrategy.PERCENTILE_BASED:
                # Use percentile-based adjustment
                target_percentile = threshold.percentile_target / 100.0
                percentile_index = int(len(self._performance_data[threshold.metric_type]) * target_percentile)
                
                if percentile_index < len(self._performance_data[threshold.metric_type]):
                    sorted_values = sorted(
                        sample["value"] for sample in self._performance_data[threshold.metric_type]
                    )
                    return sorted_values[percentile_index]
            
            elif strategy == ThresholdAdjustmentStrategy.STATISTICAL_BASED:
                # Use statistical-based adjustment
                return stats.mean_value + (threshold.statistical_multiplier * stats.std_deviation)
            
            elif strategy == ThresholdAdjustmentStrategy.TREND_BASED:
                # Use trend-based adjustment
                if stats.trend_direction == "increasing" and abs(stats.trend_slope) > threshold.trend_sensitivity:
                    # Adjust upward for increasing trend
                    return threshold.threshold_value * 1.1
                elif stats.trend_direction == "decreasing" and abs(stats.trend_slope) > threshold.trend_sensitivity:
                    # Adjust downward for decreasing trend
                    return threshold.threshold_value * 0.9
            
            elif strategy == ThresholdAdjustmentStrategy.HYBRID:
                # Use hybrid approach
                percentile_value = None
                statistical_value = None
                
                # Calculate percentile-based value
                target_percentile = threshold.percentile_target / 100.0
                percentile_index = int(len(self._performance_data[threshold.metric_type]) * target_percentile)
                
                if percentile_index < len(self._performance_data[threshold.metric_type]):
                    sorted_values = sorted(
                        sample["value"] for sample in self._performance_data[threshold.metric_type]
                    )
                    percentile_value = sorted_values[percentile_index]
                
                # Calculate statistical-based value
                statistical_value = stats.mean_value + (threshold.statistical_multiplier * stats.std_deviation)
                
                # Combine approaches
                if percentile_value and statistical_value:
                    return (percentile_value + statistical_value) / 2
                elif percentile_value:
                    return percentile_value
                elif statistical_value:
                    return statistical_value
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to calculate adaptive threshold",
                threshold_id=threshold.threshold_id,
                strategy=strategy.value,
                error=str(e)
            )
            return None
    
    def _statistics_to_dict(self, stats: PerformanceStatistics) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            "metric_type": stats.metric_type.value,
            "samples_count": stats.samples_count,
            "mean_value": stats.mean_value,
            "median_value": stats.median_value,
            "std_deviation": stats.std_deviation,
            "min_value": stats.min_value,
            "max_value": stats.max_value,
            "percentiles": stats.percentiles,
            "trend_slope": stats.trend_slope,
            "trend_direction": stats.trend_direction,
            "last_updated": stats.last_updated.isoformat()
        }
