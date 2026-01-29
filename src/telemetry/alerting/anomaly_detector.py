"""
Anomaly Detection Algorithms

Advanced anomaly detection with multiple algorithms including
statistical, machine learning, and pattern-based detection.
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics
import math
import numpy as np

from ..interfaces import Alert, AlertSeverity
from ..models import TelemetryEvent, PerformanceMetrics, QualityMetrics
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryAlertingError
from ..configuration.logging import get_logger


class AnomalyType(Enum):
    """Anomaly type enumeration."""
    STATISTICAL_OUTLIER = "statistical_outlier"
    TREND_ANOMALY = "trend_anomaly"
    PATTERN_ANOMALY = "pattern_anomaly"
    SEASONAL_ANOMALY = "seasonal_anomaly"
    CLUSTER_ANOMALY = "cluster_anomaly"
    PERFORMANCE_ANOMALY = "performance_anomaly"
    QUALITY_ANOMALY = "quality_anomaly"


class DetectionAlgorithm(Enum):
    """Detection algorithm types."""
    Z_SCORE = "z_score"
    IQR = "iqr"
    ISOLATION_FOREST = "isolation_forest"
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    SEASONAL_DECOMPOSITION = "seasonal_decomposition"
    CLUSTERING = "clustering"


@dataclass
class AnomalyDetectionConfig:
    """Configuration for anomaly detection."""
    config_id: str
    name: str
    description: str
    metric_name: str
    algorithm: DetectionAlgorithm
    sensitivity: float = 2.0  # Higher = more sensitive
    min_samples: int = 30
    window_size: int = 100
    seasonal_period: Optional[int] = None
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""
    config_id: str
    metric_name: str
    algorithm: DetectionAlgorithm
    anomaly_type: AnomalyType
    severity: AlertSeverity
    confidence: float
    value: float
    expected_value: float
    deviation: float
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    related_anomalies: List[str] = field(default_factory=list)


@dataclass
class AnomalyStatistics:
    """Statistics for anomaly detection."""
    total_detections: int = 0
    anomalies_by_type: Dict[str, int] = field(default_factory=dict)
    anomalies_by_algorithm: Dict[str, int] = field(default_factory=dict)
    anomalies_by_severity: Dict[str, int] = field(default_factory=dict)
    average_confidence: float = 0.0
    most_common_type: str = ""
    most_common_algorithm: str = ""
    last_detection: Optional[datetime] = None


class AnomalyDetector:
    """
    Advanced anomaly detection with multiple algorithms.
    
    Provides comprehensive anomaly detection using statistical,
    machine learning, and pattern-based approaches.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize anomaly detector.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("anomaly_detector")
        
        # Detector configuration
        self.enabled = config.get("anomaly_detection_enabled", True)
        self.max_samples_per_metric = config.get("max_anomaly_samples", 1000)
        self.default_sensitivity = config.get("anomaly_sensitivity", 2.0)
        
        # Data storage
        self._metric_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_samples_per_metric))
        self._detection_configs: Dict[str, AnomalyDetectionConfig] = {}
        self._detection_lock = asyncio.Lock()
        
        # Detection history
        self._detection_history: List[AnomalyResult] = []
        self._max_detections = config.get("max_anomaly_detections", 10000)
        
        # Statistics
        self._statistics = AnomalyStatistics()
        
        # Initialize default configurations
        self._initialize_default_configs()
    
    async def detect_anomalies(
        self,
        event: TelemetryEvent,
        custom_configs: Optional[List[AnomalyDetectionConfig]] = None
    ) -> List[AnomalyResult]:
        """
        Detect anomalies in a telemetry event.
        
        Args:
            event: TelemetryEvent to analyze
            custom_configs: Optional custom detection configurations
            
        Returns:
            List of detected anomalies
            
        Raises:
            TelemetryAlertingError: If detection fails
        """
        if not self.enabled:
            return []
        
        try:
            anomalies = []
            
            async with self._detection_lock:
                # Extract metrics from event
                metrics = self._extract_metrics(event)
                
                # Store metric data
                for metric_name, value in metrics.items():
                    if value is not None:
                        self._metric_data[metric_name].append({
                            "value": value,
                            "timestamp": event.timestamp,
                            "selector_name": event.selector_name,
                            "correlation_id": event.correlation_id
                        })
                
                # Get configurations to use
                configs_to_use = []
                
                # Add default configs
                for config in self._detection_configs.values():
                    if config.enabled and config.metric_name in metrics:
                        configs_to_use.append(config)
                
                # Add custom configs
                if custom_configs:
                    configs_to_use.extend(custom_configs)
                
                # Run anomaly detection
                for config in configs_to_use:
                    if config.metric_name in metrics:
                        metric_data = list(self._metric_data[config.metric_name])
                        
                        if len(metric_data) >= config.min_samples:
                            anomaly = await self._detect_anomaly_with_config(
                                config,
                                metrics[config.metric_name],
                                metric_data,
                                event
                            )
                            
                            if anomaly:
                                anomalies.append(anomaly)
                                self._detection_history.append(anomaly)
                                self._update_statistics(anomaly)
                
                # Limit detection history
                if len(self._detection_history) > self._max_detections:
                    self._detection_history = self._detection_history[-self._max_detections:]
            
            return anomalies
            
        except Exception as e:
            self.logger.error(
                "Failed to detect anomalies",
                event_id=event.event_id,
                error=str(e)
            )
            raise TelemetryAlertingError(
                f"Failed to detect anomalies: {e}",
                error_code="TEL-809"
            )
    
    async def detect_anomaly(
        self,
        metric_name: str,
        current_value: float,
        config_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[AnomalyResult]:
        """
        Detect anomaly for a specific metric.
        
        Args:
            metric_name: Name of the metric
            current_value: Current metric value
            config_id: Optional configuration ID to use
            context: Additional context
            
        Returns:
            Anomaly result or None if no anomaly detected
        """
        try:
            async with self._detection_lock:
                if metric_name not in self._metric_data:
                    return None
                
                metric_data = list(self._metric_data[metric_name])
                
                # Get configuration to use
                config = None
                if config_id:
                    config = self._detection_configs.get(config_id)
                else:
                    # Find first matching config
                    for c in self._detection_configs.values():
                        if c.enabled and c.metric_name == metric_name:
                            config = c
                            break
                
                if not config:
                    return None
                
                if len(metric_data) < config.min_samples:
                    return None
                
                # Create mock event
                mock_event = type('MockEvent', (), {
                    'timestamp': datetime.utcnow(),
                    'selector_name': context.get('selector_name', 'unknown') if context else 'unknown',
                    'correlation_id': context.get('correlation_id') if context else None
                })()
                
                anomaly = await self._detect_anomaly_with_config(
                    config,
                    current_value,
                    metric_data,
                    mock_event
                )
                
                if anomaly:
                    self._detection_history.append(anomaly)
                    self._update_statistics(anomaly)
                
                return anomaly
                
        except Exception as e:
            self.logger.error(
                "Failed to detect anomaly",
                metric_name=metric_name,
                error=str(e)
            )
            return None
    
    async def add_detection_config(self, config: AnomalyDetectionConfig) -> bool:
        """
        Add an anomaly detection configuration.
        
        Args:
            config: Detection configuration to add
            
        Returns:
            True if successfully added
        """
        try:
            async with self._detection_lock:
                self._detection_configs[config.config_id] = config
            
            self.logger.info(
                "Anomaly detection config added",
                config_id=config.config_id,
                metric_name=config.metric_name,
                algorithm=config.algorithm.value
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add detection config",
                config_id=config.config_id,
                error=str(e)
            )
            return False
    
    async def remove_detection_config(self, config_id: str) -> bool:
        """
        Remove an anomaly detection configuration.
        
        Args:
            config_id: Configuration ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            async with self._detection_lock:
                if config_id in self._detection_configs:
                    del self._detection_configs[config_id]
                    
                    self.logger.info(
                        "Anomaly detection config removed",
                        config_id=config_id
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove detection config",
                config_id=config_id,
                error=str(e)
            )
            return False
    
    async def get_anomaly_statistics(self) -> Dict[str, Any]:
        """
        Get anomaly detection statistics.
        
        Returns:
            Anomaly detection statistics
        """
        try:
            async with self._detection_lock:
                return {
                    "total_detections": self._statistics.total_detections,
                    "anomalies_by_type": dict(self._statistics.anomalies_by_type),
                    "anomalies_by_algorithm": dict(self._statistics.anomalies_by_algorithm),
                    "anomalies_by_severity": dict(self._statistics.anomalies_by_severity),
                    "average_confidence": self._statistics.average_confidence,
                    "most_common_type": self._statistics.most_common_type,
                    "most_common_algorithm": self._statistics.most_common_algorithm,
                    "last_detection": self._statistics.last_detection,
                    "active_configs": len([c for c in self._detection_configs.values() if c.enabled]),
                    "total_configs": len(self._detection_configs),
                    "metrics_tracked": len(self._metric_data)
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get anomaly statistics",
                error=str(e)
            )
            return {}
    
    async def get_detection_history(
        self,
        anomaly_type: Optional[AnomalyType] = None,
        algorithm: Optional[DetectionAlgorithm] = None,
        severity: Optional[AlertSeverity] = None,
        limit: Optional[int] = None,
        time_window: Optional[timedelta] = None
    ) -> List[AnomalyResult]:
        """
        Get anomaly detection history with filtering.
        
        Args:
            anomaly_type: Optional anomaly type filter
            algorithm: Optional algorithm filter
            severity: Optional severity filter
            limit: Optional limit on number of results
            time_window: Optional time window for results
            
        Returns:
            List of anomaly results
        """
        try:
            async with self._detection_lock:
                results = self._detection_history.copy()
                
                # Apply filters
                if anomaly_type:
                    results = [r for r in results if r.anomaly_type == anomaly_type]
                
                if algorithm:
                    results = [r for r in results if r.algorithm == algorithm]
                
                if severity:
                    results = [r for r in results if r.severity == severity]
                
                if time_window:
                    cutoff_time = datetime.utcnow() - time_window
                    results = [r for r in results if r.timestamp >= cutoff_time]
                
                # Sort by timestamp (newest first)
                results.sort(key=lambda x: x.timestamp, reverse=True)
                
                # Apply limit
                if limit:
                    results = results[:limit]
                
                return results
                
        except Exception as e:
            self.logger.error(
                "Failed to get detection history",
                error=str(e)
            )
            return []
    
    async def get_all_configs(self) -> List[AnomalyDetectionConfig]:
        """
        Get all anomaly detection configurations.
        
        Returns:
            List of all configurations
        """
        try:
            async with self._detection_lock:
                return list(self._detection_configs.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get all configs",
                error=str(e)
            )
            return []
    
    # Private methods
    
    def _initialize_default_configs(self) -> None:
        """Initialize default anomaly detection configurations."""
        default_configs = [
            AnomalyDetectionConfig(
                config_id="resolution_time_zscore",
                name="Resolution Time Z-Score",
                description="Detect outliers in resolution time using Z-score",
                metric_name="resolution_time_ms",
                algorithm=DetectionAlgorithm.Z_SCORE,
                sensitivity=2.5,
                min_samples=30
            ),
            AnomalyDetectionConfig(
                config_id="confidence_score_iqr",
                name="Confidence Score IQR",
                description="Detect outliers in confidence score using IQR",
                metric_name="confidence_score",
                algorithm=DetectionAlgorithm.IQR,
                sensitivity=1.5,
                min_samples=20
            ),
            AnomalyDetectionConfig(
                config_id="performance_moving_average",
                name="Performance Moving Average",
                description="Detect anomalies using moving average",
                metric_name="total_duration_ms",
                algorithm=DetectionAlgorithm.MOVING_AVERAGE,
                sensitivity=2.0,
                min_samples=50,
                parameters={"window_size": 20}
            ),
            AnomalyDetectionConfig(
                config_id="strategy_switches_isolation",
                name="Strategy Switches Isolation Forest",
                description="Detect anomalies in strategy switching patterns",
                metric_name="strategy_switches_count",
                algorithm=DetectionAlgorithm.ISOLATION_FOREST,
                sensitivity=2.0,
                min_samples=100
            )
        ]
        
        for config in default_configs:
            self._detection_configs[config.config_id] = config
    
    def _extract_metrics(self, event: TelemetryEvent) -> Dict[str, Optional[float]]:
        """Extract metrics from telemetry event."""
        metrics = {}
        
        # Performance metrics
        if event.performance_metrics:
            perf = event.performance_metrics
            metrics["resolution_time_ms"] = perf.resolution_time_ms
            metrics["strategy_execution_time_ms"] = perf.strategy_execution_time_ms
            metrics["total_duration_ms"] = perf.total_duration_ms
            metrics["memory_usage_mb"] = perf.memory_usage_mb
            metrics["cpu_usage_percent"] = perf.cpu_usage_percent
            metrics["network_requests_count"] = perf.network_requests_count
            metrics["dom_operations_count"] = perf.dom_operations_count
        
        # Quality metrics
        if event.quality_metrics:
            quality = event.quality_metrics
            metrics["confidence_score"] = quality.confidence_score
            metrics["success_rate"] = 1.0 if quality.success else 0.0
            metrics["elements_found"] = float(quality.elements_found) if quality.elements_found is not None else None
            metrics["strategy_success_rate"] = quality.strategy_success_rate
        
        # Strategy metrics
        if event.strategy_metrics:
            strategy = event.strategy_metrics
            metrics["strategy_switches_count"] = float(strategy.strategy_switches_count)
        
        return metrics
    
    async def _detect_anomaly_with_config(
        self,
        config: AnomalyDetectionConfig,
        current_value: float,
        metric_data: List[Dict[str, Any]],
        event: TelemetryEvent
    ) -> Optional[AnomalyResult]:
        """Detect anomaly using specific configuration."""
        try:
            # Extract values from data
            values = [sample["value"] for sample in metric_data]
            
            # Run detection algorithm
            if config.algorithm == DetectionAlgorithm.Z_SCORE:
                return await self._detect_z_score_anomaly(config, current_value, values, event)
            elif config.algorithm == DetectionAlgorithm.IQR:
                return await self._detect_iqr_anomaly(config, current_value, values, event)
            elif config.algorithm == DetectionAlgorithm.MOVING_AVERAGE:
                return await self._detect_moving_average_anomaly(config, current_value, values, event)
            elif config.algorithm == DetectionAlgorithm.ISOLATION_FOREST:
                return await self._detect_isolation_forest_anomaly(config, current_value, values, event)
            elif config.algorithm == DetectionAlgorithm.EXPONENTIAL_SMOOTHING:
                return await self._detect_exponential_smoothing_anomaly(config, current_value, values, event)
            else:
                self.logger.warning(f"Unsupported algorithm: {config.algorithm.value}")
                return None
                
        except Exception as e:
            self.logger.error(
                "Failed to detect anomaly with config",
                config_id=config.config_id,
                error=str(e)
            )
            return None
    
    async def _detect_z_score_anomaly(
        self,
        config: AnomalyDetectionConfig,
        current_value: float,
        values: List[float],
        event: TelemetryEvent
    ) -> Optional[AnomalyResult]:
        """Detect anomaly using Z-score algorithm."""
        if len(values) < 3:
            return None
        
        mean_value = statistics.mean(values)
        std_dev = statistics.stdev(values)
        
        if std_dev == 0:
            return None
        
        z_score = abs(current_value - mean_value) / std_dev
        
        if z_score > config.sensitivity:
            # Determine severity based on Z-score
            if z_score > 4:
                severity = AlertSeverity.CRITICAL
            elif z_score > 3:
                severity = AlertSeverity.ERROR
            else:
                severity = AlertSeverity.WARNING
            
            return AnomalyResult(
                config_id=config.config_id,
                metric_name=config.metric_name,
                algorithm=config.algorithm,
                anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                severity=severity,
                confidence=min(1.0, z_score / 4.0),
                value=current_value,
                expected_value=mean_value,
                deviation=z_score,
                timestamp=event.timestamp,
                context={
                    "selector_name": event.selector_name,
                    "correlation_id": event.correlation_id
                },
                explanation=f"Z-score of {z_score:.2f} exceeds threshold {config.sensitivity}"
            )
        
        return None
    
    async def _detect_iqr_anomaly(
        self,
        config: AnomalyDetectionConfig,
        current_value: float,
        values: List[float],
        event: TelemetryEvent
    ) -> Optional[AnomalyResult]:
        """Detect anomaly using IQR algorithm."""
        if len(values) < 4:
            return None
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        q1 = sorted_values[n // 4]
        q3 = sorted_values[3 * n // 4]
        iqr = q3 - q1
        
        if iqr == 0:
            return None
        
        lower_bound = q1 - (config.sensitivity * iqr)
        upper_bound = q3 + (config.sensitivity * iqr)
        
        if current_value < lower_bound or current_value > upper_bound:
            # Calculate deviation
            if current_value < lower_bound:
                deviation = (lower_bound - current_value) / iqr
            else:
                deviation = (current_value - upper_bound) / iqr
            
            # Determine severity
            if deviation > 3:
                severity = AlertSeverity.CRITICAL
            elif deviation > 2:
                severity = AlertSeverity.ERROR
            else:
                severity = AlertSeverity.WARNING
            
            return AnomalyResult(
                config_id=config.config_id,
                metric_name=config.metric_name,
                algorithm=config.algorithm,
                anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                severity=severity,
                confidence=min(1.0, deviation / 3.0),
                value=current_value,
                expected_value=(q1 + q3) / 2,
                deviation=deviation,
                timestamp=event.timestamp,
                context={
                    "selector_name": event.selector_name,
                    "correlation_id": event.correlation_id
                },
                explanation=f"Value {current_value} outside IQR bounds [{lower_bound:.2f}, {upper_bound:.2f}]"
            )
        
        return None
    
    async def _detect_moving_average_anomaly(
        self,
        config: AnomalyDetectionConfig,
        current_value: float,
        values: List[float],
        event: TelemetryEvent
    ) -> Optional[AnomalyResult]:
        """Detect anomaly using moving average algorithm."""
        window_size = config.parameters.get("window_size", 20)
        
        if len(values) < window_size + 1:
            return None
        
        # Calculate moving average of historical values (excluding current)
        historical_values = values[:-1]
        moving_avg = statistics.mean(historical_values[-window_size:])
        moving_std = statistics.stdev(historical_values[-window_size:])
        
        if moving_std == 0:
            return None
        
        # Calculate deviation
        deviation = abs(current_value - moving_avg) / moving_std
        
        if deviation > config.sensitivity:
            # Determine severity
            if deviation > 4:
                severity = AlertSeverity.CRITICAL
            elif deviation > 3:
                severity = AlertSeverity.ERROR
            else:
                severity = AlertSeverity.WARNING
            
            return AnomalyResult(
                config_id=config.config_id,
                metric_name=config.metric_name,
                algorithm=config.algorithm,
                anomaly_type=AnomalyType.TREND_ANOMALY,
                severity=severity,
                confidence=min(1.0, deviation / 4.0),
                value=current_value,
                expected_value=moving_avg,
                deviation=deviation,
                timestamp=event.timestamp,
                context={
                    "selector_name": event.selector_name,
                    "correlation_id": event.correlation_id,
                    "window_size": window_size
                },
                explanation=f"Deviation of {deviation:.2f} from moving average {moving_avg:.2f}"
            )
        
        return None
    
    async def _detect_isolation_forest_anomaly(
        self,
        config: AnomalyDetectionConfig,
        current_value: float,
        values: List[float],
        event: TelemetryEvent
    ) -> Optional[AnomalyResult]:
        """Detect anomaly using simplified isolation forest approach."""
        if len(values) < 50:
            return None
        
        # Simplified isolation forest using statistical approach
        # In a real implementation, you would use scikit-learn's IsolationForest
        
        # Calculate isolation score based on local density
        recent_values = values[-50:]  # Last 50 values
        sorted_values = sorted(recent_values)
        
        # Find position of current value in sorted distribution
        try:
            position = sorted_values.index(current_value)
        except ValueError:
            # Current value not in recent values, find insertion point
            position = bisect.bisect_left(sorted_values, current_value)
        
        # Calculate percentile
        percentile = position / len(sorted_values)
        
        # Values in extreme percentiles are more anomalous
        anomaly_score = min(percentile, 1 - percentile) * 2
        
        if anomaly_score > (1.0 / config.sensitivity):
            # Determine severity
            if anomaly_score > 0.8:
                severity = AlertSeverity.CRITICAL
            elif anomaly_score > 0.6:
                severity = AlertSeverity.ERROR
            else:
                severity = AlertSeverity.WARNING
            
            return AnomalyResult(
                config_id=config.config_id,
                metric_name=config.metric_name,
                algorithm=config.algorithm,
                anomaly_type=AnomalyType.CLUSTER_ANOMALY,
                severity=severity,
                confidence=anomaly_score,
                value=current_value,
                expected_value=statistics.median(recent_values),
                deviation=anomaly_score,
                timestamp=event.timestamp,
                context={
                    "selector_name": event.selector_name,
                    "correlation_id": event.correlation_id,
                    "percentile": percentile
                },
                explanation=f"Isolation score {anomaly_score:.3f} indicates anomaly"
            )
        
        return None
    
    async def _detect_exponential_smoothing_anomaly(
        self,
        config: AnomalyDetectionConfig,
        current_value: float,
        values: List[float],
        event: TelemetryEvent
    ) -> Optional[AnomalyResult]:
        """Detect anomaly using exponential smoothing."""
        if len(values) < 10:
            return None
        
        alpha = config.parameters.get("alpha", 0.3)
        
        # Calculate exponential smoothing forecast
        forecast = values[0]
        for value in values[1:]:
            forecast = alpha * value + (1 - alpha) * forecast
        
        # Calculate forecast error
        error = abs(current_value - forecast)
        
        # Calculate mean absolute error of historical forecasts
        mae_values = []
        temp_forecast = values[0]
        for i in range(1, len(values)):
            prev_forecast = temp_forecast
            temp_forecast = alpha * values[i] + (1 - alpha) * temp_forecast
            mae_values.append(abs(values[i] - prev_forecast))
        
        if mae_values:
            mae = statistics.mean(mae_values)
            
            if mae > 0:
                error_ratio = error / mae
                
                if error_ratio > config.sensitivity:
                    # Determine severity
                    if error_ratio > 4:
                        severity = AlertSeverity.CRITICAL
                    elif error_ratio > 3:
                        severity = AlertSeverity.ERROR
                    else:
                        severity = AlertSeverity.WARNING
                    
                    return AnomalyResult(
                        config_id=config.config_id,
                        metric_name=config.metric_name,
                        algorithm=config.algorithm,
                        anomaly_type=AnomalyType.TREND_ANOMALY,
                        severity=severity,
                        confidence=min(1.0, error_ratio / 4.0),
                        value=current_value,
                        expected_value=forecast,
                        deviation=error_ratio,
                        timestamp=event.timestamp,
                        context={
                            "selector_name": event.selector_name,
                            "correlation_id": event.correlation_id,
                            "alpha": alpha
                        },
                        explanation=f"Error ratio {error_ratio:.2f} exceeds threshold {config.sensitivity}"
                    )
        
        return None
    
    def _update_statistics(self, anomaly: AnomalyResult) -> None:
        """Update anomaly detection statistics."""
        self._statistics.total_detections += 1
        self._statistics.last_detection = anomaly.timestamp
        
        # Update by type
        type_name = anomaly.anomaly_type.value
        if type_name not in self._statistics.anomalies_by_type:
            self._statistics.anomalies_by_type[type_name] = 0
        self._statistics.anomalies_by_type[type_name] += 1
        
        # Update by algorithm
        algo_name = anomaly.algorithm.value
        if algo_name not in self._statistics.anomalies_by_algorithm:
            self._statistics.anomalies_by_algorithm[algo_name] = 0
        self._statistics.anomalies_by_algorithm[algo_name] += 1
        
        # Update by severity
        severity_name = anomaly.severity.value
        if severity_name not in self._statistics.anomalies_by_severity:
            self._statistics.anomalies_by_severity[severity_name] = 0
        self._statistics.anomalies_by_severity[severity_name] += 1
        
        # Update average confidence
        total_anomalies = self._statistics.total_detections
        current_avg = self._statistics.average_confidence
        new_avg = ((current_avg * (total_anomalies - 1)) + anomaly.confidence) / total_anomalies
        self._statistics.average_confidence = new_avg
        
        # Update most common
        if self._statistics.anomalies_by_type:
            self._statistics.most_common_type = max(
                self._statistics.anomalies_by_type,
                key=self._statistics.anomalies_by_type.get
            )
        
        if self._statistics.anomalies_by_algorithm:
            self._statistics.most_common_algorithm = max(
                self._statistics.anomalies_by_algorithm,
                key=self._statistics.anomalies_by_algorithm.get
            )


# Import bisect for isolation forest
import bisect
