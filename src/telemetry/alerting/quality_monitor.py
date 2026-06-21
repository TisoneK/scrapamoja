"""
Quality Monitor

Specialized monitor for quality metrics with degradation detection,
trend analysis, and confidence score monitoring.
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
from ..models import QualityMetrics, TelemetryEvent
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryAlertingError
from ..configuration.logging import get_logger


class QualityMetricType(Enum):
    """Quality metric types."""
    CONFIDENCE_SCORE = "confidence_score"
    SUCCESS_RATE = "success_rate"
    ELEMENTS_FOUND = "elements_found"
    STRATEGY_SUCCESS_RATE = "strategy_success_rate"
    VALIDATION_PASSED = "validation_passed"


class DegradationSeverity(Enum):
    """Quality degradation severity levels."""
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


@dataclass
class QualityThreshold:
    """Quality threshold configuration."""
    threshold_id: str
    metric_type: QualityMetricType
    warning_threshold: float
    error_threshold: float
    critical_threshold: float
    evaluation_window_minutes: int = 30
    min_samples: int = 10
    degradation_detection_enabled: bool = True
    trend_analysis_enabled: bool = True
    adaptive_thresholds: bool = True
    last_evaluation: Optional[datetime] = None
    evaluation_count: int = 0


@dataclass
class QualityEvaluation:
    """Result of quality evaluation."""
    threshold_id: str
    metric_type: QualityMetricType
    current_value: float
    warning_threshold: float
    error_threshold: float
    critical_threshold: float
    degradation_severity: DegradationSeverity
    alert_severity: AlertSeverity
    trend_direction: str
    trend_slope: float
    statistical_context: Dict[str, float]
    evaluation_time: datetime
    samples_evaluated: int
    degradation_detected: bool = False
    confidence_trend: Optional[Dict[str, Any]] = None


@dataclass
class QualityStatistics:
    """Quality statistics for a metric."""
    metric_type: QualityMetricType
    samples_count: int
    mean_value: float
    median_value: float
    std_deviation: float
    min_value: float
    max_value: float
    percentiles: Dict[str, float]
    trend_slope: float
    trend_direction: str
    degradation_score: float
    last_updated: datetime


class QualityMonitor:
    """
    Specialized monitor for quality metrics with degradation detection.
    
    Provides comprehensive quality monitoring with trend analysis,
    degradation detection, and adaptive threshold adjustment.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize quality monitor.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("quality_monitor")
        
        # Monitor configuration
        self.enabled = config.get("quality_monitoring_enabled", True)
        self.max_samples_per_metric = config.get("max_quality_samples", 1000)
        self.default_evaluation_window = timedelta(minutes=config.get("quality_evaluation_window_minutes", 30))
        
        # Quality data storage
        self._quality_data: Dict[QualityMetricType, deque] = defaultdict(lambda: deque(maxlen=self.max_samples_per_metric))
        self._quality_stats: Dict[QualityMetricType, QualityStatistics] = {}
        self._thresholds: Dict[str, QualityThreshold] = {}
        self._monitor_lock = asyncio.Lock()
        
        # Evaluation history
        self._evaluation_history: List[QualityEvaluation] = []
        self._max_evaluations = config.get("max_quality_evaluations", 10000)
        
        # Degradation tracking
        self._degradation_history: Dict[str, List[datetime]] = defaultdict(list)
        
        # Initialize default thresholds
        self._initialize_default_thresholds()
    
    async def evaluate_quality_event(self, event: TelemetryEvent) -> List[QualityEvaluation]:
        """
        Evaluate quality metrics from a telemetry event.
        
        Args:
            event: TelemetryEvent to evaluate
            
        Returns:
            List of quality evaluations
            
        Raises:
            TelemetryAlertingError: If evaluation fails
        """
        if not self.enabled or not event.quality_metrics:
            return []
        
        try:
            evaluations = []
            
            async with self._monitor_lock:
                # Extract quality metrics
                metrics = self._extract_quality_metrics(event)
                
                # Store quality data
                for metric_type, value in metrics.items():
                    if value is not None:
                        self._quality_data[metric_type].append({
                            "value": value,
                            "timestamp": event.timestamp,
                            "selector_name": event.selector_name,
                            "correlation_id": event.correlation_id
                        })
                
                # Update statistics
                await self._update_quality_statistics()
                
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
                            
                            # Track degradation
                            if evaluation.degradation_detected:
                                self._degradation_history[threshold_id].append(evaluation.evaluation_time)
                
                # Limit evaluation history
                if len(self._evaluation_history) > self._max_evaluations:
                    self._evaluation_history = self._evaluation_history[-self._max_evaluations:]
            
            return evaluations
            
        except Exception as e:
            self.logger.error(
                "Failed to evaluate quality event",
                event_id=event.event_id,
                error=str(e)
            )
            raise TelemetryAlertingError(
                f"Failed to evaluate quality event: {e}",
                error_code="TEL-808"
            )
    
    async def evaluate_threshold(
        self,
        threshold_id: str,
        current_value: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[QualityEvaluation]:
        """
        Evaluate a specific quality threshold.
        
        Args:
            threshold_id: Threshold ID to evaluate
            current_value: Current metric value
            context: Additional context
            
        Returns:
            Quality evaluation or None if threshold not found
        """
        try:
            async with self._monitor_lock:
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
                    
                    # Track degradation
                    if evaluation.degradation_detected:
                        self._degradation_history[threshold_id].append(evaluation.evaluation_time)
                
                return evaluation
                
        except Exception as e:
            self.logger.error(
                "Failed to evaluate quality threshold",
                threshold_id=threshold_id,
                error=str(e)
            )
            return None
    
    async def detect_quality_degradation(
        self,
        metric_type: QualityMetricType,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Detect quality degradation for a specific metric.
        
        Args:
            metric_type: Quality metric type to analyze
            time_window: Optional time window for analysis
            
        Returns:
            Degradation analysis results
        """
        try:
            if metric_type not in self._quality_data:
                return {"degradation_detected": False, "reason": "No data available"}
            
            time_window = time_window or self.default_evaluation_window
            cutoff_time = datetime.utcnow() - time_window
            
            # Get recent data
            recent_data = [
                sample for sample in self._quality_data[metric_type]
                if sample["timestamp"] >= cutoff_time
            ]
            
            if len(recent_data) < 10:
                return {"degradation_detected": False, "reason": "Insufficient data"}
            
            # Analyze degradation
            values = [sample["value"] for sample in recent_data]
            timestamps = [sample["timestamp"] for sample in recent_data]
            
            # Calculate trend
            trend_slope, trend_direction = self._calculate_trend(timestamps, values)
            
            # Calculate statistical measures
            mean_value = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
            
            # Compare with historical baseline
            historical_data = [
                sample for sample in self._quality_data[metric_type]
                if sample["timestamp"] < cutoff_time
            ]
            
            degradation_detected = False
            degradation_severity = DegradationSeverity.NONE
            degradation_reasons = []
            
            if historical_data:
                historical_values = [sample["value"] for sample in historical_data]
                historical_mean = statistics.mean(historical_values)
                
                # Check for significant drop
                if mean_value < historical_mean * 0.8:  # 20% drop
                    degradation_detected = True
                    degradation_severity = DegradationSeverity.MODERATE
                    degradation_reasons.append(f"Mean value dropped {((historical_mean - mean_value) / historical_mean) * 100:.1f}%")
                
                # Check for negative trend
                if trend_direction == "decreasing" and abs(trend_slope) > 0.01:
                    degradation_detected = True
                    if abs(trend_slope) > 0.05:
                        degradation_severity = DegradationSeverity.SEVERE
                    else:
                        degradation_severity = DegradationSeverity.MILD
                    degradation_reasons.append(f"Negative trend detected (slope: {trend_slope:.4f})")
                
                # Check for high volatility
                if std_dev > historical_mean * 0.3:  # High volatility
                    degradation_detected = True
                    if degradation_severity.value < DegradationSeverity.MODERATE.value:
                        degradation_severity = DegradationSeverity.MODERATE
                    degradation_reasons.append(f"High volatility detected (std_dev: {std_dev:.3f})")
            
            return {
                "degradation_detected": degradation_detected,
                "severity": degradation_severity.value,
                "reasons": degradation_reasons,
                "current_mean": mean_value,
                "historical_mean": historical_mean if historical_data else None,
                "trend_slope": trend_slope,
                "trend_direction": trend_direction,
                "samples_analyzed": len(recent_data),
                "time_window_minutes": time_window.total_seconds() / 60
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to detect quality degradation",
                metric_type=metric_type.value,
                error=str(e)
            )
            return {"degradation_detected": False, "error": str(e)}
    
    async def analyze_confidence_trends(
        self,
        selector_name: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Analyze confidence score trends.
        
        Args:
            selector_name: Optional selector filter
            time_window: Optional time window for analysis
            
        Returns:
            Confidence trend analysis
        """
        try:
            if QualityMetricType.CONFIDENCE_SCORE not in self._quality_data:
                return {"trend": "no_data"}
            
            time_window = time_window or self.default_evaluation_window
            cutoff_time = datetime.utcnow() - time_window
            
            # Get recent confidence data
            recent_data = [
                sample for sample in self._quality_data[QualityMetricType.CONFIDENCE_SCORE]
                if sample["timestamp"] >= cutoff_time
            ]
            
            if selector_name:
                recent_data = [
                    sample for sample in recent_data
                    if sample.get("selector_name") == selector_name
                ]
            
            if len(recent_data) < 5:
                return {"trend": "insufficient_data", "samples": len(recent_data)}
            
            # Analyze trends
            values = [sample["value"] for sample in recent_data]
            timestamps = [sample["timestamp"] for sample in recent_data]
            
            # Calculate trend
            trend_slope, trend_direction = self._calculate_trend(timestamps, values)
            
            # Calculate statistics
            mean_confidence = statistics.mean(values)
            median_confidence = statistics.median(values)
            min_confidence = min(values)
            max_confidence = max(values)
            
            # Calculate confidence distribution
            distribution = {
                "very_low": len([v for v in values if v < 0.2]),
                "low": len([v for v in values if 0.2 <= v < 0.4]),
                "medium": len([v for v in values if 0.4 <= v < 0.6]),
                "high": len([v for v in values if 0.6 <= v < 0.8]),
                "very_high": len([v for v in values if v >= 0.8])
            }
            
            # Determine trend category
            if abs(trend_slope) < 0.01:
                trend_category = "stable"
            elif trend_slope > 0:
                trend_category = "improving"
            else:
                trend_category = "degrading"
            
            return {
                "trend": trend_category,
                "trend_slope": trend_slope,
                "trend_direction": trend_direction,
                "statistics": {
                    "mean": mean_confidence,
                    "median": median_confidence,
                    "min": min_confidence,
                    "max": max_confidence
                },
                "distribution": distribution,
                "samples_analyzed": len(recent_data),
                "time_window_minutes": time_window.total_seconds() / 60,
                "selector_name": selector_name
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to analyze confidence trends",
                selector_name=selector_name,
                error=str(e)
            )
            return {"trend": "error", "error": str(e)}
    
    async def get_quality_statistics(
        self,
        metric_type: Optional[QualityMetricType] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get quality statistics.
        
        Args:
            metric_type: Optional metric type filter
            time_window: Optional time window for statistics
            
        Returns:
            Quality statistics
        """
        try:
            async with self._monitor_lock:
                stats = {}
                
                if metric_type:
                    if metric_type in self._quality_stats:
                        stats[metric_type.value] = self._statistics_to_dict(
                            self._quality_stats[metric_type]
                        )
                else:
                    for mt, stat in self._quality_stats.items():
                        stats[mt.value] = self._statistics_to_dict(stat)
                
                # Apply time window filter if specified
                if time_window:
                    cutoff_time = datetime.utcnow() - time_window
                    filtered_stats = {}
                    
                    for mt, stat_dict in stats.items():
                        metric_type = QualityMetricType(mt)
                        if metric_type in self._quality_data:
                            recent_samples = [
                                sample for sample in self._quality_data[metric_type]
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
                "Failed to get quality statistics",
                metric_type=metric_type.value if metric_type else None,
                error=str(e)
            )
            return {}
    
    async def get_degradation_history(
        self,
        threshold_id: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, List[datetime]]:
        """
        Get degradation history.
        
        Args:
            threshold_id: Optional threshold ID filter
            time_window: Optional time window for history
            
        Returns:
            Degradation history by threshold ID
        """
        try:
            async with self._monitor_lock:
                history = {}
                
                for tid, timestamps in self._degradation_history.items():
                    if threshold_id and tid != threshold_id:
                        continue
                    
                    if time_window:
                        cutoff_time = datetime.utcnow() - time_window
                        filtered_timestamps = [
                            ts for ts in timestamps
                            if ts >= cutoff_time
                        ]
                        history[tid] = filtered_timestamps
                    else:
                        history[tid] = timestamps
                
                return history
                
        except Exception as e:
            self.logger.error(
                "Failed to get degradation history",
                threshold_id=threshold_id,
                error=str(e)
            )
            return {}
    
    async def add_threshold(self, threshold: QualityThreshold) -> bool:
        """
        Add a quality threshold.
        
        Args:
            threshold: Quality threshold to add
            
        Returns:
            True if successfully added
        """
        try:
            async with self._monitor_lock:
                self._thresholds[threshold.threshold_id] = threshold
            
            self.logger.info(
                "Quality threshold added",
                threshold_id=threshold.threshold_id,
                metric_type=threshold.metric_type.value
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add quality threshold",
                threshold_id=threshold.threshold_id,
                error=str(e)
            )
            return False
    
    async def remove_threshold(self, threshold_id: str) -> bool:
        """
        Remove a quality threshold.
        
        Args:
            threshold_id: Threshold ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            async with self._monitor_lock:
                if threshold_id in self._thresholds:
                    del self._thresholds[threshold_id]
                    
                    # Clean up degradation history
                    if threshold_id in self._degradation_history:
                        del self._degradation_history[threshold_id]
                    
                    self.logger.info(
                        "Quality threshold removed",
                        threshold_id=threshold_id
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove quality threshold",
                threshold_id=threshold_id,
                error=str(e)
            )
            return False
    
    async def get_all_thresholds(self) -> List[QualityThreshold]:
        """
        Get all quality thresholds.
        
        Returns:
            List of all quality thresholds
        """
        try:
            async with self._monitor_lock:
                return list(self._thresholds.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get all thresholds",
                error=str(e)
            )
            return []
    
    # Private methods
    
    def _initialize_default_thresholds(self) -> None:
        """Initialize default quality thresholds."""
        default_thresholds = [
            QualityThreshold(
                threshold_id="confidence_score_warning",
                metric_type=QualityMetricType.CONFIDENCE_SCORE,
                warning_threshold=0.6,
                error_threshold=0.4,
                critical_threshold=0.2
            ),
            QualityThreshold(
                threshold_id="success_rate_warning",
                metric_type=QualityMetricType.SUCCESS_RATE,
                warning_threshold=0.8,
                error_threshold=0.6,
                critical_threshold=0.4
            ),
            QualityThreshold(
                threshold_id="elements_found_low",
                metric_type=QualityMetricType.ELEMENTS_FOUND,
                warning_threshold=1.0,
                error_threshold=0.0,
                critical_threshold=0.0
            ),
            QualityThreshold(
                threshold_id="strategy_success_rate_warning",
                metric_type=QualityMetricType.STRATEGY_SUCCESS_RATE,
                warning_threshold=0.7,
                error_threshold=0.5,
                critical_threshold=0.3
            )
        ]
        
        for threshold in default_thresholds:
            self._thresholds[threshold.threshold_id] = threshold
    
    def _extract_quality_metrics(self, event: TelemetryEvent) -> Dict[QualityMetricType, Optional[float]]:
        """Extract quality metrics from event."""
        metrics = {}
        
        if event.quality_metrics:
            quality = event.quality_metrics
            
            metrics[QualityMetricType.CONFIDENCE_SCORE] = quality.confidence_score
            metrics[QualityMetricType.SUCCESS_RATE] = 1.0 if quality.success else 0.0
            metrics[QualityMetricType.ELEMENTS_FOUND] = float(quality.elements_found) if quality.elements_found is not None else None
            metrics[QualityMetricType.STRATEGY_SUCCESS_RATE] = quality.strategy_success_rate
            metrics[QualityMetricType.VALIDATION_PASSED] = 1.0 if quality.validation_passed else 0.0
        
        return metrics
    
    async def _update_quality_statistics(self) -> None:
        """Update quality statistics for all metrics."""
        for metric_type, data_deque in self._quality_data.items():
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
                "p10": sorted_values[int(n * 0.1)],
                "p25": sorted_values[int(n * 0.25)],
                "p50": sorted_values[int(n * 0.5)],
                "p75": sorted_values[int(n * 0.75)],
                "p90": sorted_values[int(n * 0.9)]
            }
            
            # Calculate trend
            trend_slope, trend_direction = self._calculate_trend(timestamps, values)
            
            # Calculate degradation score
            degradation_score = self._calculate_degradation_score(values, trend_slope)
            
            # Update statistics
            self._quality_stats[metric_type] = QualityStatistics(
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
                degradation_score=degradation_score,
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
        denominator = (n * sum_x2 - sum_x * sum_x)
        if denominator == 0:
            slope = 0.0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Determine direction
        if abs(slope) < 0.001:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        return slope, direction
    
    def _calculate_degradation_score(self, values: List[float], trend_slope: float) -> float:
        """Calculate degradation score (0-1, higher means more degraded)."""
        if len(values) < 2:
            return 0.0
        
        # Factors for degradation score
        trend_factor = max(0, -trend_slope * 10)  # Negative trend increases score
        volatility_factor = statistics.stdev(values) if len(values) > 1 else 0
        low_value_factor = max(0, (0.5 - statistics.mean(values)) * 2)  # Low values increase score
        
        # Combine factors
        degradation_score = min(1.0, (trend_factor + volatility_factor + low_value_factor) / 3)
        
        return degradation_score
    
    async def _evaluate_threshold(
        self,
        threshold: QualityThreshold,
        current_value: float,
        event: TelemetryEvent
    ) -> Optional[QualityEvaluation]:
        """Evaluate a quality threshold."""
        try:
            # Get statistical context
            statistical_context = await self._get_statistical_context(threshold.metric_type)
            
            # Get trend context
            trend_context = await self._get_trend_context(threshold.metric_type)
            
            # Determine degradation severity and alert severity
            degradation_severity, alert_severity = self._determine_severity(
                threshold,
                current_value
            )
            
            # Detect degradation
            degradation_detected = await self._detect_degradation_for_threshold(
                threshold,
                current_value,
                trend_context
            )
            
            return QualityEvaluation(
                threshold_id=threshold.threshold_id,
                metric_type=threshold.metric_type,
                current_value=current_value,
                warning_threshold=threshold.warning_threshold,
                error_threshold=threshold.error_threshold,
                critical_threshold=threshold.critical_threshold,
                degradation_severity=degradation_severity,
                alert_severity=alert_severity,
                trend_direction=trend_context.get("direction", "stable"),
                trend_slope=trend_context.get("slope", 0.0),
                statistical_context=statistical_context,
                evaluation_time=datetime.utcnow(),
                samples_evaluated=len(self._quality_data[threshold.metric_type]),
                degradation_detected=degradation_detected
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to evaluate threshold",
                threshold_id=threshold.threshold_id,
                error=str(e)
            )
            return None
    
    def _determine_severity(
        self,
        threshold: QualityThreshold,
        current_value: float
    ) -> Tuple[DegradationSeverity, AlertSeverity]:
        """Determine degradation and alert severity."""
        if current_value <= threshold.critical_threshold:
            return DegradationSeverity.CRITICAL, AlertSeverity.CRITICAL
        elif current_value <= threshold.error_threshold:
            return DegradationSeverity.SEVERE, AlertSeverity.ERROR
        elif current_value <= threshold.warning_threshold:
            return DegradationSeverity.MODERATE, AlertSeverity.WARNING
        else:
            return DegradationSeverity.NONE, AlertSeverity.INFO
    
    async def _detect_degradation_for_threshold(
        self,
        threshold: QualityThreshold,
        current_value: float,
        trend_context: Dict[str, Any]
    ) -> bool:
        """Detect degradation for a specific threshold."""
        if not threshold.degradation_detection_enabled:
            return False
        
        # Check if current value is below warning threshold
        if current_value < threshold.warning_threshold:
            return True
        
        # Check for negative trend
        if threshold.trend_analysis_enabled:
            trend_direction = trend_context.get("direction", "stable")
            trend_slope = trend_context.get("slope", 0.0)
            
            if trend_direction == "decreasing" and abs(trend_slope) > 0.01:
                return True
        
        return False
    
    async def _get_statistical_context(self, metric_type: QualityMetricType) -> Dict[str, float]:
        """Get statistical context for a metric."""
        if metric_type not in self._quality_stats:
            return {}
        
        stats = self._quality_stats[metric_type]
        
        return {
            "mean": stats.mean_value,
            "median": stats.median_value,
            "std_deviation": stats.std_deviation,
            "min": stats.min_value,
            "max": stats.max_value,
            "p10": stats.percentiles.get("p10", 0),
            "p25": stats.percentiles.get("p25", 0),
            "p50": stats.percentiles.get("p50", 0),
            "p75": stats.percentiles.get("p75", 0),
            "p90": stats.percentiles.get("p90", 0)
        }
    
    async def _get_trend_context(self, metric_type: QualityMetricType) -> Dict[str, Any]:
        """Get trend context for a metric."""
        if metric_type not in self._quality_stats:
            return {}
        
        stats = self._quality_stats[metric_type]
        
        return {
            "slope": stats.trend_slope,
            "direction": stats.trend_direction,
            "degradation_score": stats.degradation_score,
            "last_updated": stats.last_updated.isoformat()
        }
    
    def _statistics_to_dict(self, stats: QualityStatistics) -> Dict[str, Any]:
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
            "degradation_score": stats.degradation_score,
            "last_updated": stats.last_updated.isoformat()
        }
