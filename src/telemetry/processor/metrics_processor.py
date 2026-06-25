"""
Metrics Processor

Advanced metrics processing engine for telemetry data with
aggregation, analysis, and reporting capabilities.
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics
import json

from ..models import TelemetryEvent, PerformanceMetrics, QualityMetrics, StrategyMetrics, ErrorData, ContextData
from ..interfaces import ITelemetryProcessor
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryProcessingError
from ..configuration.logging import get_logger


class AggregationType(Enum):
    """Aggregation type enumeration."""
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    RATE = "rate"
    TREND = "trend"


class TimeWindow(Enum):
    """Time window enumeration."""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_6 = "6h"
    HOUR_12 = "12h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1m"


@dataclass
class MetricDefinition:
    """Definition for a metric to be processed."""
    metric_name: str
    source_field: str
    data_type: str  # "numeric", "categorical", "boolean"
    aggregation_types: List[AggregationType]
    time_windows: List[TimeWindow]
    enabled: bool = True
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class ProcessedMetric:
    """Result of metric processing."""
    metric_name: str
    aggregation_type: AggregationType
    time_window: TimeWindow
    value: Union[float, int, str]
    timestamp: datetime
    sample_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingStatistics:
    """Statistics for metrics processing."""
    total_events_processed: int = 0
    total_metrics_generated: int = 0
    processing_time_ms: float = 0.0
    average_processing_time_ms: float = 0.0
    metrics_by_type: Dict[str, int] = field(default_factory=dict)
    metrics_by_window: Dict[str, int] = field(default_factory=dict)
    last_processed: Optional[datetime] = None
    error_count: int = 0


class MetricsProcessor(ITelemetryProcessor):
    """
    Advanced metrics processor for telemetry data.
    
    Provides comprehensive metrics processing with aggregation,
    analysis, and reporting capabilities.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize metrics processor.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("metrics_processor")
        
        # Processor configuration
        self.enabled = config.get("metrics_processing_enabled", True)
        self.max_events_in_memory = config.get("max_events_in_memory", 10000)
        self.batch_size = config.get("metrics_batch_size", 100)
        self.processing_interval_seconds = config.get("metrics_processing_interval_seconds", 60)
        
        # Metric definitions
        self._metric_definitions: Dict[str, MetricDefinition] = {}
        self._processed_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._processing_lock = asyncio.Lock()
        
        # Event storage
        self._event_buffer: deque = deque(maxlen=self.max_events_in_memory)
        
        # Statistics
        self._statistics = ProcessingStatistics()
        
        # Background processing
        self._processing_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Initialize default metric definitions
        self._initialize_default_metrics()
        
        # Start background processing
        if self.enabled:
            self._start_background_processing()
    
    async def process_event(self, event: TelemetryEvent) -> List[ProcessedMetric]:
        """
        Process a single telemetry event.
        
        Args:
            event: TelemetryEvent to process
            
        Returns:
            List of processed metrics
            
        Raises:
            TelemetryProcessingError: If processing fails
        """
        if not self.enabled:
            return []
        
        try:
            start_time = datetime.utcnow()
            
            # Add event to buffer
            self._event_buffer.append(event)
            
            # Process metrics for this event
            processed_metrics = await self._process_event_metrics(event)
            
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_processing_statistics(processing_time, len(processed_metrics))
            
            # Store processed metrics
            for metric in processed_metrics:
                self._processed_metrics[metric.metric_name].append(metric)
            
            self.logger.debug(
                "Event processed",
                event_id=event.event_id,
                metrics_count=len(processed_metrics),
                processing_time_ms=processing_time
            )
            
            return processed_metrics
            
        except Exception as e:
            self._statistics.error_count += 1
            self.logger.error(
                "Failed to process event",
                event_id=event.event_id,
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to process event: {e}",
                error_code="TEL-1001",
                processing_point="event_processing"
            )
    
    async def process_events_batch(self, events: List[TelemetryEvent]) -> List[ProcessedMetric]:
        """
        Process multiple telemetry events in batch.
        
        Args:
            events: List of TelemetryEvents to process
            
        Returns:
            List of processed metrics
        """
        if not self.enabled or not events:
            return []
        
        try:
            start_time = datetime.utcnow()
            all_metrics = []
            
            # Add events to buffer
            self._event_buffer.extend(events)
            
            # Process each event
            for event in events:
                event_metrics = await self._process_event_metrics(event)
                all_metrics.extend(event_metrics)
            
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_processing_statistics(processing_time, len(all_metrics))
            
            # Store processed metrics
            for metric in all_metrics:
                self._processed_metrics[metric.metric_name].append(metric)
            
            self.logger.info(
                "Events batch processed",
                events_count=len(events),
                metrics_count=len(all_metrics),
                processing_time_ms=processing_time
            )
            
            return all_metrics
            
        except Exception as e:
            self._statistics.error_count += 1
            self.logger.error(
                "Failed to process events batch",
                events_count=len(events),
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to process events batch: {e}",
                error_code="TEL-1002",
                processing_point="batch_processing"
            )
    
    async def get_metrics(
        self,
        metric_names: Optional[List[str]] = None,
        time_window: Optional[TimeWindow] = None,
        aggregation_type: Optional[AggregationType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ProcessedMetric]:
        """
        Get processed metrics with filtering.
        
        Args:
            metric_names: Optional list of metric names to filter
            time_window: Optional time window to filter
            aggregation_type: Optional aggregation type to filter
            start_time: Optional start time for filtering
            end_time: Optional end time for filtering
            
        Returns:
            List of processed metrics
        """
        try:
            async with self._processing_lock:
                metrics = []
                
                # Filter by metric names
                if metric_names:
                    for metric_name in metric_names:
                        if metric_name in self._processed_metrics:
                            metric_deque = self._processed_metrics[metric_name]
                            metrics.extend(list(metric_deque))
                else:
                    for metric_deque in self._processed_metrics.values():
                        metrics.extend(list(metric_deque))
                
                # Apply filters
                if time_window:
                    cutoff_time = self._get_cutoff_time(time_window)
                    metrics = [m for m in metrics if m.timestamp >= cutoff_time]
                
                if aggregation_type:
                    metrics = [m for m in metrics if m.aggregation_type == aggregation_type]
                
                if start_time:
                    metrics = [m for m in metrics if m.timestamp >= start_time]
                
                if end_time:
                    metrics = [m for m in metrics if m.timestamp <= end_time]
                
                # Sort by timestamp (newest first)
                metrics.sort(key=lambda x: x.timestamp, reverse=True)
                
                return metrics
                
        except Exception as e:
            self.logger.error(
                "Failed to get metrics",
                error=str(e)
            )
            return []
    
    async def aggregate_metrics(
        self,
        metric_name: str,
        aggregation_type: AggregationType,
        time_window: TimeWindow,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Optional[ProcessedMetric]:
        """
        Aggregate metrics for a specific time window.
        
        Args:
            metric_name: Name of the metric to aggregate
            aggregation_type: Type of aggregation to perform
            time_window: Time window for aggregation
            start_time: Optional start time (overrides time_window)
            end_time: Optional end time (overrides time_window)
            
        Returns:
            Aggregated metric or None if no data
        """
        try:
            # Get time range
            if start_time and end_time:
                actual_start = start_time
                actual_end = end_time
            else:
                actual_end = datetime.utcnow()
                actual_start = self._get_cutoff_time(time_window)
            
            # Get metrics in time range
            metrics = await self.get_metrics(
                metric_names=[metric_name],
                start_time=actual_start,
                end_time=actual_end
            )
            
            if not metrics:
                return None
            
            # Perform aggregation
            values = [m.value for m in metrics if isinstance(m.value, (int, float))]
            
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
                time_span = (actual_end - actual_start).total_seconds()
                if time_span > 0:
                    aggregated_value = len(values) / time_span
                else:
                    aggregated_value = 0
            elif aggregation_type == AggregationType.TREND:
                # Simple linear trend
                aggregated_value = self._calculate_trend(values, actual_start, actual_end)
            else:
                self.logger.warning(f"Unsupported aggregation type: {aggregation_type.value}")
                return None
            
            return ProcessedMetric(
                metric_name=metric_name,
                aggregation_type=aggregation_type,
                time_window=time_window,
                value=aggregated_value,
                timestamp=actual_end,
                sample_count=len(values),
                metadata={
                    "start_time": actual_start.isoformat(),
                    "end_time": actual_end.isoformat(),
                    "time_span_seconds": (actual_end - actual_start).total_seconds()
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to aggregate metrics",
                metric_name=metric_name,
                aggregation_type=aggregation_type.value,
                error=str(e)
            )
            return None
    
    async def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Processing statistics
        """
        try:
            async with self._processing_lock:
                return {
                    "enabled": self.enabled,
                    "total_events_processed": self._statistics.total_events_processed,
                    "total_metrics_generated": self._statistics.total_metrics_generated,
                    "processing_time_ms": self._statistics.processing_time_ms,
                    "average_processing_time_ms": self._statistics.average_processing_time_ms,
                    "metrics_by_type": dict(self._statistics.metrics_by_type),
                    "metrics_by_window": dict(self._statistics.metrics_by_window),
                    "last_processed": self._statistics.last_processed,
                    "error_count": self._statistics.error_count,
                    "event_buffer_size": len(self._event_buffer),
                    "max_events_in_memory": self.max_events_in_memory,
                    "batch_size": self.batch_size,
                    "processing_interval_seconds": self.processing_interval_seconds,
                    "metric_definitions_count": len(self._metric_definitions),
                    "processed_metrics_count": len(self._processed_metrics)
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get processing statistics",
                error=str(e)
            )
            return {}
    
    async def add_metric_definition(self, definition: MetricDefinition) -> bool:
        """
        Add a metric definition.
        
        Args:
            definition: Metric definition to add
            
        Returns:
            True if successfully added
        """
        try:
            async with self._processing_lock:
                self._metric_definitions[definition.metric_name] = definition
            
            self.logger.info(
                "Metric definition added",
                metric_name=definition.metric_name,
                source_field=definition.source_field
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to add metric definition",
                metric_name=definition.metric_name,
                error=str(e)
            )
            return False
    
    async def remove_metric_definition(self, metric_name: str) -> bool:
        """
        Remove a metric definition.
        
        Args:
            metric_name: Name of metric to remove
            
        Returns:
            True if successfully removed
        """
        try:
            async with self._processing_lock:
                if metric_name in self._metric_definitions:
                    del self._metric_definitions[metric_name]
                    
                    # Clean up processed metrics
                    if metric_name in self._processed_metrics:
                        del self._processed_metrics[metric_name]
                    
                    self.logger.info(
                        "Metric definition removed",
                        metric_name=metric_name
                    )
                    
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to remove metric definition",
                metric_name=metric_name,
                error=str(e)
            )
            return False
    
    async def get_metric_definitions(self) -> List[MetricDefinition]:
        """
        Get all metric definitions.
        
        Returns:
            List of metric definitions
        """
        try:
            async with self._processing_lock:
                return list(self._metric_definitions.values())
                
        except Exception as e:
            self.logger.error(
                "Failed to get metric definitions",
                error=str(e)
            )
            return []
    
    async def enable_processing(self) -> None:
        """Enable metrics processing."""
        self.enabled = True
        if not self._processing_task or self._processing_task.done():
            self._start_background_processing()
        
        self.logger.info("Metrics processing enabled")
    
    async def disable_processing(self) -> None:
        """Disable metrics processing."""
        self.enabled = False
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
        
        self.logger.info("Metrics processing disabled")
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._shutdown_event.set()
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
    
    # Private methods
    
    def _initialize_default_metrics(self) -> None:
        """Initialize default metric definitions."""
        default_metrics = [
            # Performance metrics
            MetricDefinition(
                metric_name="resolution_time_ms",
                source_field="performance_metrics.resolution_time_ms",
                data_type="numeric",
                aggregation_types=[
                    AggregationType.AVERAGE, AggregationType.MIN, AggregationType.MAX,
                    AggregationType.PERCENTILE, AggregationType.TREND
                ],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1, TimeWindow.HOUR_6
                ],
                description="Selector resolution time in milliseconds"
            ),
            MetricDefinition(
                metric_name="strategy_execution_time_ms",
                source_field="performance_metrics.strategy_execution_time_ms",
                data_type="numeric",
                aggregation_types=[
                    AggregationType.AVERAGE, AggregationType.MIN, AggregationType.MAX,
                    AggregationType.PERCENTILE
                ],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1
                ],
                description="Strategy execution time in milliseconds"
            ),
            MetricDefinition(
                metric_name="total_duration_ms",
                source_field="performance_metrics.total_duration_ms",
                data_type="numeric",
                aggregation_types=[
                    AggregationType.AVERAGE, AggregationType.MIN, AggregationType.MAX,
                    AggregationType.PERCENTILE, AggregationType.TREND
                ],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1, TimeWindow.HOUR_6
                ],
                description="Total operation duration in milliseconds"
            ),
            MetricDefinition(
                metric_name="memory_usage_mb",
                source_field="performance_metrics.memory_usage_mb",
                data_type="numeric",
                aggregation_types=[
                    AggregationType.AVERAGE, AggregationType.MAX, AggregationType.PERCENTILE
                ],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1
                ],
                description="Memory usage in megabytes"
            ),
            MetricDefinition(
                metric_name="cpu_usage_percent",
                source_field="performance_metrics.cpu_usage_percent",
                data_type="numeric",
                aggregation_types=[
                    AggregationType.AVERAGE, AggregationType.MAX, AggregationType.PERCENTILE
                ],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1
                ],
                description="CPU usage percentage"
            ),
            # Quality metrics
            MetricDefinition(
                metric_name="confidence_score",
                source_field="quality_metrics.confidence_score",
                data_type="numeric",
                aggregation_types=[
                    AggregationType.AVERAGE, AggregationType.MIN, AggregationType.MAX,
                    AggregationType.PERCENTILE
                ],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1, TimeWindow.HOUR_6
                ],
                description="Confidence score (0-1)"
            ),
            MetricDefinition(
                metric_name="success_rate",
                source_field="quality_metrics.success",
                data_type="boolean",
                aggregation_types=[AggregationType.RATE],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1, TimeWindow.HOUR_6
                ],
                description="Success rate (0-1)"
            ),
            MetricDefinition(
                metric_name="elements_found",
                source_field="quality_metrics.elements_found",
                data_type="numeric",
                aggregation_types=[
                    AggregationType.AVERAGE, AggregationType.MIN, AggregationType.MAX,
                    AggregationType.SUM
                ],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1
                ],
                description="Number of elements found"
            ),
            # Strategy metrics
            MetricDefinition(
                metric_name="strategy_switches_count",
                source_field="strategy_metrics.strategy_switches_count",
                data_type="numeric",
                aggregation_types=[
                    AggregationType.AVERAGE, AggregationType.MAX, AggregationType.SUM,
                    AggregationType.COUNT
                ],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1
                ],
                description="Number of strategy switches"
            ),
            MetricDefinition(
                metric_name="strategy_success_rate",
                source_field="strategy_metrics.strategy_success_rate",
                data_type="numeric",
                aggregation_types=[
                    AggregationType.AVERAGE, AggregationType.MIN, AggregationType.MAX,
                    AggregationType.PERCENTILE
                ],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1
                ],
                description="Strategy success rate (0-1)"
            ),
            # Error metrics
            MetricDefinition(
                metric_name="error_rate",
                source_field="error_data",
                data_type="boolean",
                aggregation_types=[AggregationType.RATE],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1, TimeWindow.HOUR_6
                ],
                description="Error rate (0-1)"
            ),
            MetricDefinition(
                metric_name="retry_attempts",
                source_field="error_data.retry_attempts",
                data_type="numeric",
                aggregation_types=[
                    AggregationType.AVERAGE, AggregationType.MAX, AggregationType.SUM
                ],
                time_windows=[
                    TimeWindow.MINUTE_1, TimeWindow.MINUTE_5, TimeWindow.MINUTE_15,
                    TimeWindow.MINUTE_30, TimeWindow.HOUR_1
                ],
                description="Number of retry attempts"
            )
        ]
        
        for metric in default_metrics:
            self._metric_definitions[metric.metric_name] = metric
    
    def _start_background_processing(self) -> None:
        """Start background processing."""
        if self._processing_task is None or self._processing_task.done():
            self._processing_task = asyncio.create_task(self._background_processing_loop())
    
    async def _background_processing_loop(self) -> None:
        """Background loop for periodic processing."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for processing interval or shutdown
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.processing_interval_seconds
                )
                
                if self._shutdown_event.is_set():
                    break
                
                # Process buffered events
                await self._process_buffered_events()
                
            except asyncio.TimeoutError:
                # Timeout - continue with next iteration
                continue
            except Exception as e:
                self.logger.error(
                    "Background processing loop error",
                    error=str(e)
                )
                await asyncio.sleep(10.0)  # Brief pause before retrying
    
    async def _process_buffered_events(self) -> None:
        """Process events in the buffer."""
        try:
            if not self._event_buffer:
                return
            
            # Take a batch of events
            events_to_process = []
            for _ in range(min(self.batch_size, len(self._event_buffer))):
                events_to_process.append(self._event_buffer.popleft())
            
            if events_to_process:
                await self.process_events_batch(events_to_process)
                
        except Exception as e:
            self.logger.error(
                "Failed to process buffered events",
                error=str(e)
            )
    
    async def _process_event_metrics(self, event: TelemetryEvent) -> List[ProcessedMetric]:
        """Process metrics for a single event."""
        metrics = []
        
        # Extract metric values from event
        event_data = self._extract_event_data(event)
        
        # Process each defined metric
        for metric_name, definition in self._metric_definitions.items():
            if not definition.enabled:
                continue
            
            # Get value from event data
            value = self._get_value_from_event_data(event_data, definition.source_field)
            
            if value is not None:
                # Create processed metrics for each aggregation type and time window
                for aggregation_type in definition.aggregation_types:
                    for time_window in definition.time_windows:
                        metric = ProcessedMetric(
                            metric_name=metric_name,
                            aggregation_type=aggregation_type,
                            time_window=time_window,
                            value=value,
                            timestamp=event.timestamp,
                            sample_count=1,
                            metadata={
                                "event_id": event.event_id,
                                }
                        )
                        metrics.append(metric)
        
        return metrics
    
    def _extract_event_data(self, event: TelemetryEvent) -> Dict[str, Any]:
        """Extract all data from telemetry event."""
        data = {
            "event_id": event.event_id,
            "selector_name": event.selector_name,
            "operation_type": event.operation_type,
            "correlation_id": event.correlation_id,
            "timestamp": event.timestamp
        }
        
        # Extract performance metrics
        if event.performance_metrics:
            data.update({
                "performance_metrics.resolution_time_ms": event.performance_metrics.resolution_time_ms,
                "performance_metrics.strategy_execution_time_ms": event.performance_metrics.strategy_execution_time_ms,
                "performance_metrics.total_duration_ms": event.performance_metrics.total_duration_ms,
                "performance_metrics.memory_usage_mb": event.performance_metrics.memory_usage_mb,
                "performance_metrics.cpu_usage_percent": event.performance_metrics.cpu_usage_percent,
                "performance_metrics.network_requests_count": event.performance_metrics.network_requests_count,
                "performance_metrics.dom_operations_count": event.performance_metrics.dom_operations_count
            })
        
        # Extract quality metrics
        if event.quality_metrics:
            data.update({
                "quality_metrics.confidence_score": event.quality_metrics.confidence_score,
                "quality_metrics.success": event.quality_metrics.success,
                "quality_metrics.elements_found": event.quality_metrics.elements_found,
                "quality_metrics.strategy_success_rate": event.quality_metrics.strategy_success_rate,
                "quality_metrics.drift_detected": event.quality_metrics.drift_detected,
                "quality_metrics.fallback_used": event.quality_metrics.fallback_used,
                "quality_metrics.validation_passed": event.quality_metrics.validation_passed
            })
        
        # Extract strategy metrics
        if event.strategy_metrics:
            data.update({
                "strategy_metrics.primary_strategy": event.strategy_metrics.primary_strategy,
                "strategy_metrics.secondary_strategies": event.strategy_metrics.secondary_strategies,
                "strategy_metrics.strategy_execution_order": event.strategy_metrics.strategy_execution_order,
                "strategy_metrics.strategy_success_by_type": event.strategy_metrics.strategy_success_by_type,
                "strategy_metrics.strategy_timing_by_type": event.strategy_metrics.strategy_timing_by_type,
                "strategy_metrics.strategy_switches_count": event.strategy_metrics.strategy_switches_count
            })
        
        # Extract error data
        if event.error_data:
            data.update({
                "error_data.error_type": event.error_data.error_type,
                "error_data.error_message": event.error_data.error_message,
                "error_data.retry_attempts": event.error_data.retry_attempts,
                "error_data.fallback_attempts": event.error_data.fallback_attempts,
                "error_data.recovery_successful": event.error_data.recovery_successful
            })
        
        # Extract context data
        if event.context_data:
            data.update({
                "context_data.browser_session_id": event.context_data.browser_session_id,
                "context_data.tab_context_id": event.context_data.tab_context_id,
                "context_data.page_url": event.context_data.page_url,
                "context_data.user_agent": event.context_data.user_agent,
                "context_data.viewport_size": event.context_data.viewport_size
            })
        
        return data
    
    def _get_value_from_event_data(self, event_data: Dict[str, Any], source_field: str) -> Any:
        """Get value from event data by source field path."""
        try:
            # Split field path by dots
            field_parts = source_field.split(".")
            current_value = event_data
            
            # Navigate through the field path
            for part in field_parts:
                if isinstance(current_value, dict) and part in current_value:
                    current_value = current_value[part]
                else:
                    return None
            
            return current_value
            
        except Exception:
            return None
    
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
    
    def _update_processing_statistics(self, processing_time_ms: float, metrics_count: int) -> None:
        """Update processing statistics."""
        self._statistics.total_events_processed += 1
        self._statistics.total_metrics_generated += metrics_count
        self._statistics.processing_time_ms += processing_time_ms
        self._statistics.last_processed = datetime.utcnow()
        
        # Update average processing time
        total_events = self._statistics.total_events_processed
        if total_events > 0:
            self._statistics.average_processing_time_ms = (
                self._statistics.processing_time_ms / total_events
            )
