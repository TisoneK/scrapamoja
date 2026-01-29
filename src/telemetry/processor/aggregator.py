"""
Aggregator

Advanced data aggregation engine for telemetry metrics with
multi-dimensional aggregation, time-based grouping, and
statistical analysis capabilities.
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics
import json

from ..models import TelemetryEvent
from ..interfaces import ITelemetryProcessor
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryProcessingError
from ..configuration.logging import get_logger
from .metrics_processor import ProcessedMetric, AggregationType, TimeWindow


class GroupingType(Enum):
    """Grouping type enumeration."""
    TIME_BASED = "time_based"
    SELECTOR_BASED = "selector_based"
    OPERATION_BASED = "operation_based"
    STRATEGY_BASED = "strategy_based"
    SEVERITY_BASED = "severity_based"
    CUSTOM = "custom"


class AggregationLevel(Enum):
    """Aggregation level enumeration."""
    RAW = "raw"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class AggregationRule:
    """Rule for metric aggregation."""
    rule_id: str
    name: str
    metric_name: str
    grouping_type: GroupingType
    aggregation_type: AggregationType
    aggregation_level: AggregationLevel
    time_windows: List[TimeWindow]
    enabled: bool = True
    custom_grouping_function: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AggregatedMetric:
    """Result of metric aggregation."""
    aggregation_id: str
    rule_id: str
    metric_name: str
    grouping_type: GroupingType
    aggregation_type: AggregationType
    aggregation_level: AggregationLevel
    time_window: TimeWindow
    group_key: str
    value: Union[float, int, str]
    sample_count: int
    timestamp: datetime
    start_time: datetime
    end_time: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregationStatistics:
    """Statistics for aggregation operations."""
    total_aggregations: int = 0
    aggregations_by_type: Dict[str, int] = field(default_factory=dict)
    aggregations_by_level: Dict[str, int] = field(default_factory=dict)
    aggregations_by_grouping: Dict[str, int] = field(default_factory=dict)
    average_aggregation_time_ms: float = 0.0
    last_aggregation: Optional[datetime] = None
    error_count: int = 0


class Aggregator(ITelemetryProcessor):
    """
    Advanced aggregator for telemetry metrics.
    
    Provides comprehensive aggregation capabilities with multi-dimensional
    grouping, time-based analysis, and statistical operations.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize aggregator.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("aggregator")
        
        # Aggregator configuration
        self.enabled = config.get("aggregation_enabled", True)
        self.max_aggregated_metrics = config.get("max_aggregated_metrics", 50000)
        self.batch_size = config.get("aggregation_batch_size", 1000)
        self.aggregation_interval_seconds = config.get("aggregation_interval_seconds", 300)
        
        # Storage
        self._aggregation_rules: Dict[str, AggregationRule] = {}
        self._aggregated_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_aggregated_metrics))
        self._aggregation_lock = asyncio.Lock()
        
        # Statistics
        self._statistics = AggregationStatistics()
        
        # Background aggregation
        self._aggregation_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Initialize default aggregation rules
        self._initialize_default_rules()
        
        # Start background aggregation
        if self.enabled:
            self._start_background_aggregation()
    
    async def aggregate_metrics(
        self,
        metrics: List[ProcessedMetric],
        rules: Optional[List[AggregationRule]] = None
    ) -> List[AggregatedMetric]:
        """
        Aggregate processed metrics according to rules.
        
        Args:
            metrics: List of processed metrics to aggregate
            rules: Optional list of aggregation rules to use
            
        Returns:
            List of aggregated metrics
        """
        if not self.enabled or not metrics:
            return []
        
        try:
            start_time = datetime.utcnow()
            
            # Use provided rules or default rules
            rules_to_use = rules if rules else list(self._aggregation_rules.values())
            
            # Filter enabled rules
            rules_to_use = [rule for rule in rules_to_use if rule.enabled]
            
            aggregated_metrics = []
            
            # Process each rule
            for rule in rules_to_use:
                # Filter metrics for this rule
                rule_metrics = [m for m in metrics if m.metric_name == rule.metric_name]
                
                if not rule_metrics:
                    continue
                
                # Group metrics according to rule
                grouped_metrics = self._group_metrics(rule_metrics, rule)
                
                # Aggregate each group
                for group_key, group_metrics in grouped_metrics.items():
                    aggregated_metric = await self._aggregate_group(rule, group_key, group_metrics)
                    if aggregated_metric:
                        aggregated_metrics.append(aggregated_metric)
            
            # Update statistics
            aggregation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_aggregation_statistics(aggregation_time, len(aggregated_metrics))
            
            # Store aggregated metrics
            for metric in aggregated_metrics:
                self._aggregated_metrics[metric.metric_name].append(metric)
            
            self.logger.debug(
                "Metrics aggregated",
                input_metrics_count=len(metrics),
                rules_count=len(rules_to_use),
                aggregated_count=len(aggregated_metrics),
                aggregation_time_ms=aggregation_time
            )
            
            return aggregated_metrics
            
        except Exception as e:
            self._statistics.error_count += 1
            self.logger.error(
                "Failed to aggregate metrics",
                input_metrics_count=len(metrics),
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to aggregate metrics: {e}",
                error_code="TEL-1003",
                processing_point="aggregation"
            )
    
    async def get_aggregated_metrics(
        self,
        metric_name: Optional[str] = None,
        grouping_type: Optional[GroupingType] = None,
        aggregation_level: Optional[AggregationLevel] = None,
        time_window: Optional[TimeWindow] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[AggregatedMetric]:
        """
        Get aggregated metrics with filtering.
        
        Args:
            metric_name: Optional metric name filter
            grouping_type: Optional grouping type filter
            aggregation_level: Optional aggregation level filter
            time_window: Optional time window filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Optional limit on number of results
            
        Returns:
            List of aggregated metrics
        """
        try:
            async with self._aggregation_lock:
                metrics = []
                
                # Filter by metric name
                if metric_name:
                    if metric_name in self._aggregated_metrics:
                        metrics.extend(list(self._aggregated_metrics[metric_name]))
                else:
                    for metric_deque in self._aggregated_metrics.values():
                        metrics.extend(list(metric_deque))
                
                # Apply filters
                if grouping_type:
                    metrics = [m for m in metrics if m.grouping_type == grouping_type]
                
                if aggregation_level:
                    metrics = [m for m in metrics if m.aggregation_level == aggregation_level]
                
                if time_window:
                    cutoff_time = self._get_cutoff_time(time_window)
                    metrics = [m for m in metrics if m.timestamp >= cutoff_time]
                
                if start_time:
                    metrics = [m for m in metrics if m.start_time >= start_time]
                
                if end_time:
                    metrics = [m for m in metrics if m.end_time <= end_time]
                
                # Sort by timestamp (newest first)
                metrics.sort(key=lambda x: x.timestamp, reverse=True)
                
                # Apply limit
                if limit:
                    metrics = metrics[:limit]
                
                return metrics
                
        except Exception as e:
            self.logger.error(
                "Failed to get aggregated metrics",
                error=str(e)
            )
            return []
    
    async def aggregate_by_time_window(
        self,
        metric_name: str,
        aggregation_type: AggregationType,
        time_window: TimeWindow,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Optional[AggregatedMetric]:
        """
        Aggregate metrics by time window.
        
        Args:
            metric_name: Name of metric to aggregate
            aggregation_type: Type of aggregation
            time_window: Time window for aggregation
            start_time: Optional start time (overrides time_window)
            end_time: Optional end time (overrides time_window)
            
        Returns:
            Aggregated metric or None if no data
        """
        try:
            # Get metrics in time range
            metrics = await self.get_aggregated_metrics(
                metric_name=metric_name,
                time_window=time_window,
                start_time=start_time,
                end_time=end_time
            )
            
            if not metrics:
                return None
            
            # Filter by aggregation type
            filtered_metrics = [m for m in metrics if m.aggregation_type == aggregation_type]
            
            if not filtered_metrics:
                return None
            
            # Aggregate all values
            values = [m.value for m in filtered_metrics if isinstance(m.value, (int, float))]
            
            if not values:
                return None
            
            # Calculate aggregated value
            if aggregation_type == AggregationType.SUM:
                aggregated_value = sum(values)
            elif aggregation_type == AggregationType.AVERAGE:
                aggregated_value = statistics.mean(values)
            elif aggregation_type == AggregationType.MIN:
                aggregated_value = min(values)
            elif aggregation_type == AggregationType.MAX:
                aggregated_value = max(values)
            elif aggregation_type == AggregationType.COUNT:
                aggregated_value = len(values)
            elif aggregation_type == AggregationType.MEDIAN:
                aggregated_value = statistics.median(values)
            elif aggregation_type == AggregationType.PERCENTILE:
                # Default to 95th percentile
                aggregated_value = self._calculate_percentile(values, 95)
            elif aggregation_type == AggregationType.RATE:
                # Calculate rate per second
                time_span = (filtered_metrics[-1].end_time - filtered_metrics[0].start_time).total_seconds()
                if time_span > 0:
                    aggregated_value = sum(values) / time_span
                else:
                    aggregated_value = 0
            elif aggregation_type == AggregationType.TREND:
                # Simple linear trend
                aggregated_value = self._calculate_trend(values, filtered_metrics[0].start_time, filtered_metrics[-1].end_time)
            else:
                self.logger.warning(f"Unsupported aggregation type: {aggregation_type.value}")
                return None
            
            # Create aggregated metric
            return AggregatedMetric(
                aggregation_id=f"agg_{metric_name}_{aggregation_type.value}_{time_window.value}_{int(datetime.utcnow().timestamp())}",
                rule_id="time_based",
                metric_name=metric_name,
                grouping_type=GroupingType.TIME_BASED,
                aggregation_type=aggregation_type,
                aggregation_level=self._get_level_from_window(time_window),
                time_window=time_window,
                group_key="time_based",
                value=aggregated_value,
                sample_count=len(values),
                timestamp=filtered_metrics[-1].timestamp,
                start_time=filtered_metrics[0].start_time,
                end_time=filtered_metrics[-1].end_time,
                metadata={
                    "aggregated_count": len(filtered_metrics),
                    "time_span_seconds": (filtered_metrics[-1].end_time - filtered_metrics[0].start_time).total_seconds()
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to aggregate by time window",
                metric_name=metric_name,
                aggregation_type=aggregation_type.value,
                error=str(e)
            )
            return None
    
    async def add_aggregation_rule(self, rule: AggregationRule) -> bool:
        """
        Add an aggregation rule.
        
        Args:
            rule: Aggregation rule to add
            
        Returns:
            True if successfully added
        """
        try:
            async with self._aggregation_lock:
                self._aggregation_rules[rule.rule_id] = rule
            
            self.logger.info(
                "Aggregation rule added",
                rule_id=rule.rule_id,
                metric_name=rule.metric_name,
                grouping_type=rule.grouping_type.value
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add aggregation rule",
                rule_id=rule.rule_id,
                error=str(e)
            )
            return False
    
    async def remove_aggregation_rule(self, rule_id: str) -> bool:
        """
        Remove an aggregation rule.
        
        Args:
            rule_id: Rule ID to remove
            
        Returns:
            True if successfully removed
        """
        try:
            async with self._aggregation_lock:
                if rule_id in self._aggregation_rules:
                    del self._aggregation_rules[rule_id]
                    
                    self.logger.info(
                        "Aggregation rule removed",
                        rule_id=rule_id
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove aggregation rule",
                rule_id=rule_id,
                error=str(e)
            )
            return False
    
    async def get_aggregation_rules(self) -> List[AggregationRule]:
        """
        Get all aggregation rules.
        
        Returns:
            List of aggregation rules
        """
        try:
            async with self._aggregation_lock:
                return list(self._aggregation_rules.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get aggregation rules",
                error=str(e)
            )
            return []
    
    async def get_aggregation_statistics(self) -> Dict[str, Any]:
        """
        Get aggregation statistics.
        
        Returns:
            Aggregation statistics
        """
        try:
            async with self._aggregation_lock:
                return {
                    "enabled": self.enabled,
                    "total_aggregations": self._statistics.total_aggregations,
                    "aggregations_by_type": dict(self._statistics.aggregations_by_type),
                    "aggregations_by_level": dict(self._statistics.aggregations_by_level),
                    "aggregations_by_grouping": dict(self._statistics.aggregations_by_grouping),
                    "average_aggregation_time_ms": self._statistics.average_aggregation_time_ms,
                    "last_aggregation": self._statistics.last_aggregation,
                    "error_count": self._statistics.error_count,
                    "aggregation_rules_count": len(self._aggregation_rules),
                    "aggregated_metrics_count": len(self._aggregated_metrics),
                    "max_aggregated_metrics": self.max_aggregated_metrics,
                    "batch_size": self.batch_size,
                    "aggregation_interval_seconds": self.aggregation_interval_seconds
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get aggregation statistics",
                error=str(e)
            )
            return []
    
    async def enable_aggregation(self) -> None:
        """Enable aggregation."""
        self.enabled = True
        if not self._aggregation_task or self._aggregation_task.done():
            self._start_background_aggregation()
        
        self.logger.info("Aggregation enabled")
    
    async def disable_aggregation(self) -> None:
        """Disable aggregation."""
        self.enabled = False
        
        if self._aggregation_task:
            self._aggregation_task.cancel()
            try:
                await self._aggregation_task
            except asyncio.CancelledError:
                pass
            self._aggregation_task = None
        
        self.logger.info("Aggregation disabled")
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._shutdown_event.set()
        
        if self._aggregation_task:
            self._aggregation_task.cancel()
            try:
                await self._aggregation_task
            except asyncio.CancelledError:
                pass
            self._aggregation_task = None
    
    # Private methods
    
    def _initialize_default_rules(self) -> None:
        """Initialize default aggregation rules."""
        default_rules = [
            # Time-based rules
            AggregationRule(
                rule_id="resolution_time_1m_avg",
                name="Resolution Time 1 Minute Average",
                metric_name="resolution_time_ms",
                grouping_type=GroupingType.TIME_BASED,
                aggregation_type=AggregationType.AVERAGE,
                aggregation_level=AggregationLevel.MINUTE,
                time_windows=[TimeWindow.MINUTE_1],
                description="Average resolution time over 1 minute"
            ),
            AggregationRule(
                rule_id="resolution_time_5m_avg",
                name="Resolution Time 5 Minute Average",
                metric_name="resolution_time_ms",
                grouping_type=GroupingType.TIME_BASED,
                aggregation_type=AggregationType.AVERAGE,
                aggregation_level=AggregationLevel.MINUTE,
                time_windows=[TimeWindow.MINUTE_5],
                description="Average resolution time over 5 minutes"
            ),
            AggregationRule(
                rule_id="resolution_time_1h_avg",
                name="Resolution Time 1 Hour Average",
                metric_name="resolution_time_ms",
                grouping_type=GroupingType.TIME_BASED,
                aggregation_type=AggregationType.AVERAGE,
                aggregation_level=AggregationLevel.HOUR,
                time_windows=[TimeWindow.HOUR_1],
                description="Average resolution time over 1 hour"
            ),
            AggregationRule(
                rule_id="resolution_time_1d_avg",
                name="Resolution Time 1 Day Average",
                metric_name="resolution_time_ms",
                grouping_type=GroupingType.TIME_BASED,
                aggregation_type=AggregationType.AVERAGE,
                aggregation_level=AggregationLevel.DAY,
                time_windows=[TimeWindow.DAY_1],
                description="Average resolution time over 1 day"
            ),
            # Selector-based rules
            AggregationRule(
                rule_id="resolution_time_selector_avg",
                name="Resolution Time by Selector Average",
                metric_name="resolution_time_ms",
                grouping_type=GroupingType.SELECTOR_BASED,
                aggregation_type=AggregationType.AVERAGE,
                aggregation_level=AggregationLevel.MINUTE,
                time_windows=[TimeWindow.MINUTE_5, TimeWindow.MINUTE_15, TimeWindow.MINUTE_30],
                description="Average resolution time by selector"
            ),
            AggregationRule(
                rule_id="confidence_score_selector_avg",
                name="Confidence Score by Selector Average",
                metric_name="confidence_score",
                grouping_type=GroupingType.SELECTOR_BASED,
                aggregation_type=AggregationType.AVERAGE,
                aggregation_level=AggregationLevel.MINUTE,
                time_windows=[TimeWindow.MINUTE_5, TimeWindow.MINUTE_15, TimeWindow.MINUTE_30],
                description="Average confidence score by selector"
            ),
            # Operation-based rules
            AggregationRule(
                rule_id="resolution_time_operation_avg",
                name="Resolution Time by Operation Average",
                metric_name="resolution_time_ms",
                grouping_type=GroupingType.OPERATION_BASED,
                aggregation_type=AggregationType.AVERAGE,
                aggregation_level=AggregationLevel.MINUTE,
                time_windows=[TimeWindow.MINUTE_5, TimeWindow.MINUTE_15, TimeWindow.MINUTE_30],
                description="Average resolution time by operation"
            ),
            # Strategy-based rules
            AggregationRule(
                rule_id="strategy_switches_strategy_count",
                name="Strategy Switches by Strategy Count",
                metric_name="strategy_switches_count",
                grouping_type=GroupingType.STRATEGY_BASED,
                aggregation_type=AggregationType.AVERAGE,
                aggregation_level=AggregationLevel.MINUTE,
                time_windows=[TimeWindow.MINUTE_5, TimeWindow.MINUTE_15, TimeWindow.MINUTE_30],
                description="Average strategy switches by strategy"
            )
        ]
        
        for rule in default_rules:
            self._aggregation_rules[rule.rule_id] = rule
    
    def _start_background_aggregation(self) -> None:
        """Start background aggregation."""
        if self._aggregation_task is None or self._aggregation_task.done():
            self._aggregation_task = asyncio.create_task(self._background_aggregation_loop())
    
    async def _background_aggregation_loop(self) -> None:
        """Background loop for periodic aggregation."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for aggregation interval or shutdown
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.aggregation_interval_seconds
                )
                
                if self._shutdown_event.is_set():
                    break
                
                # Perform aggregation
                await self._perform_periodic_aggregation()
                
            except asyncio.TimeoutError:
                # Timeout - continue with next iteration
                continue
            except Exception as e:
                self.logger.error(
                    "Background aggregation loop error",
                    error=str(e)
                )
                await asyncio.sleep(10.0)  # Brief pause before retrying
    
    async def _perform_periodic_aggregation(self) -> None:
        """Perform periodic aggregation of buffered metrics."""
        try:
            # This would typically aggregate metrics from the metrics processor
            # For now, we'll log that periodic aggregation occurred
            self.logger.debug("Periodic aggregation completed")
            
        except Exception as e:
            self.logger.error(
                "Failed to perform periodic aggregation",
                error=str(e)
            )
    
    def _group_metrics(self, metrics: List[ProcessedMetric], rule: AggregationRule) -> Dict[str, List[ProcessedMetric]]:
        """Group metrics according to rule."""
        grouped = defaultdict(list)
        
        if rule.grouping_type == GroupingType.TIME_BASED:
            # Group by time window
            for metric in metrics:
                time_window = self._get_time_window_from_metric(metric)
                if time_window in rule.time_windows:
                    group_key = f"time_{time_window.value}"
                    grouped[group_key].append(metric)
        
        elif rule.grouping_type == GroupingType.SELECTOR_BASED:
            # Group by selector name
            for metric in metrics:
                selector_name = metric.metadata.get("selector_name", "unknown")
                group_key = f"selector_{selector_name}"
                grouped[group_key].append(metric)
        
        elif rule.grouping_type == GroupingType.OPERATION_BASED:
            # Group by operation type
            for metric in metrics:
                operation_type = metric.metadata.get("operation_type", "unknown")
                group_key = f"operation_{operation_type}"
                grouped[group_key].append(metric)
        
        elif rule.grouping_type == GroupingType.STRATEGY_BASED:
            # Group by strategy name
            for metric in metrics:
                strategy_name = metric.metadata.get("strategy_name", "unknown")
                group_key = f"strategy_{strategy_name}"
                grouped[group_key].append(metric)
        
        elif rule.grouping_type == GroupingType.SEVERITY_BASED:
            # Group by severity
            for metric in metrics:
                severity = metric.metadata.get("severity", "unknown")
                group_key = f"severity_{severity}"
                grouped[group_key].append(metric)
        
        elif rule.grouping_type == GroupingType.CUSTOM:
            # Use custom grouping function
            if rule.custom_grouping_function:
                for metric in metrics:
                    # This would call a custom function
                    # For now, group by event_id
                    event_id = metric.metadata.get("event_id", "unknown")
                    group_key = f"custom_{event_id}"
                    grouped[group_key].append(metric)
        
        return dict(grouped)
    
    async def _aggregate_group(self, rule: AggregationRule, group_key: str, group_metrics: List[ProcessedMetric]) -> Optional[AggregatedMetric]:
        """Aggregate a group of metrics."""
        try:
            if not group_metrics:
                return None
            
            # Get time range for this group
            timestamps = [m.timestamp for m in group_metrics]
            start_time = min(timestamps)
            end_time = max(timestamps)
            
            # Determine aggregation level from time span
            time_span = end_time - start_time
            aggregation_level = self._get_level_from_time_span(time_span)
            
            # Extract values
            values = [m.value for m in group_metrics if isinstance(m.value, (int, float))]
            
            if not values:
                return None
            
            # Calculate aggregated value
            if rule.aggregation_type == AggregationType.SUM:
                aggregated_value = sum(values)
            elif rule.aggregation_type == AggregationType.AVERAGE:
                aggregated_value = statistics.mean(values)
            elif rule.aggregation_type == AggregationType.MIN:
                aggregated_value = min(values)
            elif rule.aggregation_type == AggregationType.MAX:
                aggregated_value = max(values)
            elif rule.aggregation_type == AggregationType.COUNT:
                aggregated_value = len(values)
            elif rule.aggregation_type == AggregationType.MEDIAN:
                aggregated_value = statistics.median(values)
            elif rule.aggregation_type == AggregationType.PERCENTILE:
                # Default to 95th percentile
                aggregated_value = self._calculate_percentile(values, 95)
            elif rule.aggregation_type == AggregationType.RATE:
                # Calculate rate per second
                if time_span.total_seconds() > 0:
                    aggregated_value = len(values) / time_span.total_seconds()
                else:
                    aggregated_value = 0
            elif rule.aggregation_type == AggregationType.TREND:
                # Simple linear trend
                aggregated_value = self._calculate_trend(values, start_time, end_time)
            else:
                self.logger.warning(f"Unsupported aggregation type: {rule.aggregation_type.value}")
                return None
            
            return AggregatedMetric(
                aggregation_id=f"agg_{rule.rule_id}_{group_key}_{int(datetime.utcnow().timestamp())}",
                rule_id=rule.rule_id,
                metric_name=rule.metric_name,
                grouping_type=rule.grouping_type,
                aggregation_type=rule.aggregation_type,
                aggregation_level=aggregation_level,
                time_window=rule.time_windows[0],  # Use first time window
                group_key=group_key,
                value=aggregated_value,
                sample_count=len(group_metrics),
                timestamp=end_time,
                start_time=start_time,
                end_time=end_time,
                metadata={
                    "rule_name": rule.name,
                    "group_count": len(group_metrics),
                    "time_span_seconds": time_span.total_seconds()
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to aggregate group",
                rule_id=rule.rule_id,
                group_key=group_key,
                error=str(e)
            )
            return None
    
    def _get_time_window_from_metric(self, metric: ProcessedMetric) -> TimeWindow:
        """Get time window from metric timestamp."""
        # Simple heuristic based on timestamp
        now = datetime.utcnow()
        time_diff = now - metric.timestamp
        
        if time_diff <= timedelta(minutes=1):
            return TimeWindow.MINUTE_1
        elif time_diff <= timedelta(minutes=5):
            return TimeWindow.MINUTE_5
        elif time_diff <= timedelta(minutes=15):
            return TimeWindow.MINUTE_15
        elif time_diff <= timedelta(minutes=30):
            return TimeWindow.MINUTE_30
        elif time_diff <= timedelta(hours=1):
            return TimeWindow.HOUR_1
        elif time_diff <= timedelta(hours=6):
            return TimeWindow.HOUR_6
        elif time_diff <= timedelta(hours=12):
            return TimeWindow.HOUR_12
        elif time_diff <= timedelta(days=1):
            return TimeWindow.DAY_1
        elif time_diff <= timedelta(weeks=1):
            return TimeWindow.WEEK_1
        elif time_diff <= timedelta(days=30):
            return TimeWindow.MONTH_1
        else:
            return TimeWindow.MONTH_1
    
    def _get_level_from_window(self, time_window: TimeWindow) -> AggregationLevel:
        """Get aggregation level from time window."""
        if time_window in [TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15, TimeWindow.MINUTE_30]:
            return AggregationLevel.MINUTE
        elif time_window in [TimeWindow.HOUR_1, TimeWindow.HOUR_6, TimeWindow.HOUR_12]:
            return AggregationLevel.HOUR
        elif time_window in [TimeWindow.DAY_1]:
            return AggregationLevel.DAY
        elif time_window in [TimeWindow.WEEK_1]:
            return AggregationLevel.WEEK
        elif time_window in [TimeWindow.MONTH_1]:
            return AggregationLevel.MONTH
        else:
            return AggregationLevel.MINUTE
    
    def _get_level_from_time_span(self, time_span: timedelta) -> AggregationLevel:
        """Get aggregation level from time span."""
        if time_span <= timedelta(minutes=30):
            return AggregationLevel.MINUTE
        elif time_span <= timedelta(hours=1):
            return AggregationLevel.MINUTE
        elif time_span <= timedelta(hours=6):
            return AggregationLevel.HOUR
        elif time_span <= timedelta(hours=12):
            return AggregationLevel.HOUR
        elif time_span <= timedelta(days=1):
            return AggregationLevel.DAY
        elif time_span <= timedelta(days=7):
            return AggregationLevel.WEEK
        elif time_span <= timedelta(days=30):
            return AggregationLevel.MONTH
        else:
            return AggregationLevel.MONTH
    
    def _get_cutoff_time(self, time_window: TimeWindow) -> datetime:
        """Get cutoff time for time window."""
        now = datetime.utcnow()
        
        if time_window == TimeWindow.MINUTE_1:
            return now - timedelta(minutes=1)
        elif time_window == TimeWindow.MINUTE_5:
            return now - timedelta(minutes=5)
        elif time_window == TimeWindow.MINUTE_15:
            return now - timedelta(minutes=15)
        elif time_window == TimeWindow.MINUTE_30:
            return now - timedelta(minutes=30)
        elif time_window == TimeWindow.HOUR_1:
            return now - timedelta(hours=1)
        elif time_window == TimeWindow.HOUR_6:
            return now - timedelta(hours=6)
        elif time_window == TimeWindow.HOUR_12:
            return now - timedelta(hours=12)
        elif time_window == TimeWindow.DAY_1:
            return now - timedelta(days=1)
        elif time_window == TimeWindow.WEEK_1:
            return now - timedelta(weeks=1)
        elif time_window == TimeWindow.MONTH_1:
            return now - timedelta(days=30)
        else:
            return now - timedelta(minutes=1)  # Default to 1 minute
    
    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        
        return sorted_values[index]
    
    def _calculate_trend(self, values: List[float], start_time: datetime, end_time: datetime) -> float:
        """Calculate simple linear trend."""
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression
        n = len(values)
        sum_y = sum(values)
        
        # Calculate slope (simplified)
        if n > 1:
            # Calculate average change per time unit
            time_span = (end_time - start_time).total_seconds()
            if time_span > 0:
                # Calculate trend as average change per second
                first_half = values[:n//2]
                second_half = values[n//2:]
                
                if first_half and second_half:
                    first_avg = statistics.mean(first_half)
                    second_avg = statistics.mean(second_half)
                    trend = (second_avg - first_avg) / (time_span / 2) if time_span > 0 else 0
                    return trend
        
        return 0.0
    
    def _update_aggregation_statistics(self, aggregation_time_ms: float, aggregated_count: int) -> None:
        """Update aggregation statistics."""
        self._statistics.total_aggregations += 1
        self._statistics.last_aggregation = datetime.utcnow()
        
        # Update average aggregation time
        total_aggregations = self._statistics.total_aggregations
        if total_aggregations > 0:
            self._statistics.average_aggregation_time_ms = (
                self._statistics.average_aggregation_time_ms * (total_aggregations - 1) + aggregation_time
            ) / total_aggregations
