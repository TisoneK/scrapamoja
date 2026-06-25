"""
Async Batch Processor

High-performance asynchronous batch processor for telemetry data
with configurable batching, parallel processing, and error handling.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import time

from ..interfaces import ITelemetryProcessor
from ..models import TelemetryEvent
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import (
    TelemetryProcessingError, TelemetryValidationError
)
from ..configuration.logging import get_logger


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int = 100
    max_wait_time: timedelta = field(default_factory=lambda: timedelta(seconds=10))
    max_concurrent_batches: int = 4
    retry_attempts: int = 3
    retry_delay: timedelta = field(default_factory=lambda: timedelta(seconds=1))
    compression_enabled: bool = True
    validation_enabled: bool = True


@dataclass
class BatchStats:
    """Statistics for batch processing."""
    batches_processed: int = 0
    events_processed: int = 0
    events_failed: int = 0
    processing_time_ms: float = 0.0
    average_batch_size: float = 0.0
    retry_count: int = 0
    last_processed: Optional[datetime] = None
    concurrent_batches: int = 0


class BatchProcessor(ITelemetryProcessor):
    """
    High-performance asynchronous batch processor for telemetry data.
    
    Provides efficient batch processing with configurable batching,
    parallel processing, and comprehensive error handling.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize batch processor.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("batch_processor")
        
        # Batch configuration
        self.batch_config = BatchConfig(
            batch_size=config.get("processing_batch_size", 100),
            max_wait_time=timedelta(seconds=config.get("processing_interval_seconds", 10)),
            max_concurrent_batches=config.get("max_concurrent_batches", 4),
            retry_attempts=config.get("retry_attempts", 3),
            validation_enabled=config.get("validation_enabled", True)
        )
        
        # Processing state
        self._enabled = True
        self._processing_semaphore = asyncio.Semaphore(self.batch_config.max_concurrent_batches)
        self._shutdown_event = asyncio.Event()
        
        # Batch queue
        self._batch_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._processing_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._stats = BatchStats()
        self._stats_lock = asyncio.Lock()
        
        # Processing callbacks
        self._pre_process_callbacks: List[Callable] = []
        self._post_process_callbacks: List[Callable] = []
        self._error_callbacks: List[Callable] = []
        
        # Start processing loop
        self._start_processing()
    
    async def process_event(self, event: TelemetryEvent) -> Dict[str, Any]:
        """
        Process a single telemetry event.
        
        Args:
            event: TelemetryEvent to process
            
        Returns:
            Processing results
            
        Raises:
            TelemetryProcessingError: If processing fails
        """
        return await self.process_events_batch([event])
    
    async def process_events_batch(self, events: List[TelemetryEvent]) -> Dict[str, Any]:
        """
        Process multiple telemetry events in batch.
        
        Args:
            events: List of TelemetryEvents to process
            
        Returns:
            Batch processing results
            
        Raises:
            TelemetryProcessingError: If processing fails
        """
        if not events:
            return {
                "processed_count": 0,
                "failed_count": 0,
                "processing_time_ms": 0.0,
                "results": []
            }
        
        if not self._enabled:
            raise TelemetryProcessingError(
                "Batch processor is disabled",
                error_code="TEL-401"
            )
        
        start_time = time.time()
        
        try:
            # Validate events if enabled
            if self.batch_config.validation_enabled:
                await self._validate_events_batch(events)
            
            # Execute pre-processing callbacks
            await self._execute_callbacks(self._pre_process_callbacks, events)
            
            # Process events
            results = await self._process_events_internal(events)
            
            # Execute post-processing callbacks
            await self._execute_callbacks(self._post_process_callbacks, events, results)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            # Update statistics
            await self._update_stats(len(events), processing_time)
            
            return {
                "processed_count": len(events),
                "failed_count": 0,
                "processing_time_ms": processing_time,
                "results": results
            }
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            
            # Update error statistics
            async with self._stats_lock:
                self._stats.events_failed += len(events)
                self._stats.retry_count += 1
            
            await self._execute_callbacks(self._error_callbacks, events, e)
            
            self.logger.error(
                "Batch processing failed",
                events_count=len(events),
                error=str(e)
            )
            
            raise TelemetryProcessingError(
                f"Batch processing failed: {e}",
                error_code="TEL-402"
            )
    
    async def aggregate_performance_metrics(
        self,
        events: List[TelemetryEvent],
        aggregation_type: str = "avg",
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate performance metrics from events.
        
        Args:
            events: List of TelemetryEvents
            aggregation_type: Type of aggregation (avg, min, max, sum, count)
            group_by: Field to group by (selector_name, operation_type, etc.)
            
        Returns:
            Aggregated performance metrics
            
        Raises:
            TelemetryProcessingError: If aggregation fails
        """
        try:
            if not events:
                return {}
            
            # Filter events with performance metrics
            events_with_metrics = [
                event for event in events
                if event.performance_metrics
            ]
            
            if not events_with_metrics:
                return {}
            
            # Group events if specified
            if group_by:
                groups = defaultdict(list)
                for event in events_with_metrics:
                    key = getattr(event, group_by, "unknown")
                    groups[key].append(event)
            else:
                groups = {"all": events_with_metrics}
            
            # Aggregate each group
            results = {}
            
            for group_key, group_events in groups.items():
                metrics = []
                
                for event in group_events:
                    if event.performance_metrics:
                        metrics.append(event.performance_metrics)
                
                if metrics:
                    group_result = self._aggregate_metrics_list(metrics, aggregation_type)
                    results[group_key] = group_result
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to aggregate performance metrics",
                events_count=len(events),
                aggregation_type=aggregation_type,
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to aggregate performance metrics: {e}",
                error_code="TEL-403"
            )
    
    async def aggregate_quality_metrics(
        self,
        events: List[TelemetryEvent],
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate quality metrics from events.
        
        Args:
            events: List of TelemetryEvents
            group_by: Field to group by (selector_name, operation_type, etc.)
            
        Returns:
            Aggregated quality metrics
            
        Raises:
            TelemetryProcessingError: If aggregation fails
        """
        try:
            if not events:
                return {}
            
            # Filter events with quality metrics
            events_with_metrics = [
                event for event in events
                if event.quality_metrics
            ]
            
            if not events_with_metrics:
                return {}
            
            # Group events if specified
            if group_by:
                groups = defaultdict(list)
                for event in events_with_metrics:
                    key = getattr(event, group_by, "unknown")
                    groups[key].append(event)
            else:
                groups = {"all": events_with_metrics}
            
            # Aggregate each group
            results = {}
            
            for group_key, group_events in groups.items():
                total_events = len(group_events)
                successful_events = sum(
                    1 for event in group_events
                    if event.quality_metrics and event.quality_metrics.success
                )
                
                confidence_scores = [
                    event.quality_metrics.confidence_score
                    for event in group_events
                    if event.quality_metrics and hasattr(event.quality_metrics, 'confidence_score')
                ]
                
                group_result = {
                    "total_events": total_events,
                    "successful_events": successful_events,
                    "failed_events": total_events - successful_events,
                    "success_rate": successful_events / total_events if total_events > 0 else 0,
                }
                
                if confidence_scores:
                    group_result.update({
                        "avg_confidence_score": sum(confidence_scores) / len(confidence_scores),
                        "min_confidence_score": min(confidence_scores),
                        "max_confidence_score": max(confidence_scores)
                    })
                
                results[group_key] = group_result
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to aggregate quality metrics",
                events_count=len(events),
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to aggregate quality metrics: {e}",
                error_code="TEL-404"
            )
    
    async def analyze_strategy_effectiveness(
        self,
        events: List[TelemetryEvent],
        selector_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze strategy effectiveness from events.
        
        Args:
            events: List of TelemetryEvents
            selector_name: Optional selector filter
            
        Returns:
            Strategy effectiveness analysis
            
        Raises:
            TelemetryProcessingError: If analysis fails
        """
        try:
            if not events:
                return {}
            
            # Filter events
            filtered_events = events
            if selector_name:
                filtered_events = [
                    event for event in events
                    if event.selector_name == selector_name
                ]
            
            # Filter events with strategy metrics
            events_with_strategies = [
                event for event in filtered_events
                if event.strategy_metrics
            ]
            
            if not events_with_strategies:
                return {}
            
            # Analyze strategy usage
            strategy_usage = defaultdict(int)
            strategy_success = defaultdict(int)
            strategy_timing = defaultdict(list)
            
            for event in events_with_strategies:
                if event.strategy_metrics:
                    # Primary strategy
                    primary = event.strategy_metrics.primary_strategy
                    strategy_usage[primary] += 1
                    
                    if event.quality_metrics and event.quality_metrics.success:
                        strategy_success[primary] += 1
                    
                    # Strategy timing
                    if event.strategy_metrics.strategy_timing_by_type:
                        for strategy, timing in event.strategy_metrics.strategy_timing_by_type.items():
                            strategy_timing[strategy].append(timing)
            
            # Calculate effectiveness metrics
            results = {}
            
            for strategy in strategy_usage:
                total_usage = strategy_usage[strategy]
                success_count = strategy_success[strategy]
                success_rate = success_count / total_usage if total_usage > 0 else 0
                
                timing_data = strategy_timing.get(strategy, [])
                avg_timing = sum(timing_data) / len(timing_data) if timing_data else 0
                
                results[strategy] = {
                    "usage_count": total_usage,
                    "success_count": success_count,
                    "success_rate": success_rate,
                    "average_timing_ms": avg_timing,
                    "timing_samples": len(timing_data)
                }
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to analyze strategy effectiveness",
                events_count=len(events),
                selector_name=selector_name,
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to analyze strategy effectiveness: {e}",
                error_code="TEL-405"
            )
    
    async def detect_anomalies(
        self,
        events: List[TelemetryEvent],
        anomaly_type: str = "performance"
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies in telemetry data.
        
        Args:
            events: List of TelemetryEvents
            anomaly_type: Type of anomaly to detect (performance, quality, usage)
            
        Returns:
            List of detected anomalies
            
        Raises:
            TelemetryProcessingError: If anomaly detection fails
        """
        try:
            anomalies = []
            
            if anomaly_type == "performance":
                anomalies.extend(await self._detect_performance_anomalies(events))
            elif anomaly_type == "quality":
                anomalies.extend(await self._detect_quality_anomalies(events))
            elif anomaly_type == "usage":
                anomalies.extend(await self._detect_usage_anomalies(events))
            
            return anomalies
            
        except Exception as e:
            self.logger.error(
                "Failed to detect anomalies",
                events_count=len(events),
                anomaly_type=anomaly_type,
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to detect anomalies: {e}",
                error_code="TEL-406"
            )
    
    async def calculate_trends(
        self,
        events: List[TelemetryEvent],
        metric: str,
        time_window: str = "1h"
    ) -> Dict[str, Any]:
        """
        Calculate trends for a specific metric.
        
        Args:
            events: List of TelemetryEvents
            metric: Metric to analyze (resolution_time, confidence_score, etc.)
            time_window: Time window for trend analysis
            
        Returns:
            Trend analysis results
            
        Raises:
            TelemetryProcessingError: If trend calculation fails
        """
        try:
            if not events:
                return {}
            
            # Extract metric values over time
            time_series = []
            
            for event in events:
                value = self._extract_metric_value(event, metric)
                if value is not None:
                    time_series.append({
                        "timestamp": event.timestamp,
                        "value": value,
                        "selector_name": event.selector_name
                    })
            
            if not time_series:
                return {}
            
            # Sort by timestamp
            time_series.sort(key=lambda x: x["timestamp"])
            
            # Calculate trend metrics
            values = [point["value"] for point in time_series]
            
            if len(values) < 2:
                return {
                    "trend": "insufficient_data",
                    "data_points": len(values),
                    "metric": metric
                }
            
            # Simple linear trend calculation
            first_value = values[0]
            last_value = values[-1]
            trend_direction = "increasing" if last_value > first_value else "decreasing" if last_value < first_value else "stable"
            
            # Calculate percentage change
            percent_change = ((last_value - first_value) / first_value) * 100 if first_value != 0 else 0
            
            return {
                "trend": trend_direction,
                "percent_change": percent_change,
                "first_value": first_value,
                "last_value": last_value,
                "data_points": len(values),
                "metric": metric,
                "time_window": time_window
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to calculate trends",
                events_count=len(events),
                metric=metric,
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to calculate trends: {e}",
                error_code="TEL-407"
            )
    
    async def generate_summary_statistics(
        self,
        events: List[TelemetryEvent]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics for events.
        
        Args:
            events: List of TelemetryEvents
            
        Returns:
            Summary statistics
            
        Raises:
            TelemetryProcessingError: If statistics generation fails
        """
        try:
            if not events:
                return {}
            
            # Basic counts
            total_events = len(events)
            successful_events = sum(
                1 for event in events
                if event.quality_metrics and event.quality_metrics.success
            )
            
            # Time range
            timestamps = [event.timestamp for event in events]
            time_range = {
                "start": min(timestamps),
                "end": max(timestamps),
                "duration_hours": (max(timestamps) - min(timestamps)).total_seconds() / 3600
            }
            
            # Selector distribution
            selector_counts = defaultdict(int)
            for event in events:
                selector_counts[event.selector_name] += 1
            
            # Operation type distribution
            operation_counts = defaultdict(int)
            for event in events:
                operation_counts[event.operation_type] += 1
            
            return {
                "total_events": total_events,
                "successful_events": successful_events,
                "failed_events": total_events - successful_events,
                "success_rate": successful_events / total_events if total_events > 0 else 0,
                "time_range": time_range,
                "selector_distribution": dict(selector_counts),
                "operation_type_distribution": dict(operation_counts),
                "unique_selectors": len(selector_counts),
                "events_per_hour": total_events / max(1, time_range["duration_hours"])
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to generate summary statistics",
                events_count=len(events),
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to generate summary statistics: {e}",
                error_code="TEL-408"
            )
    
    async def filter_events(
        self,
        events: List[TelemetryEvent],
        filters: Dict[str, Any]
    ) -> List[TelemetryEvent]:
        """
        Filter events based on criteria.
        
        Args:
            events: List of TelemetryEvents
            filters: Filter criteria
            
        Returns:
            Filtered list of events
            
        Raises:
            TelemetryProcessingError: If filtering fails
        """
        try:
            filtered_events = []
            
            for event in events:
                if self._event_matches_filters(event, filters):
                    filtered_events.append(event)
            
            return filtered_events
            
        except Exception as e:
            self.logger.error(
                "Failed to filter events",
                events_count=len(events),
                filters=filters,
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to filter events: {e}",
                error_code="TEL-409"
            )
    
    async def transform_events(
        self,
        events: List[TelemetryEvent],
        transformation: str
    ) -> List[Dict[str, Any]]:
        """
        Transform events to different format.
        
        Args:
            events: List of TelemetryEvents
            transformation: Type of transformation (flatten, denormalize, etc.)
            
        Returns:
            Transformed events
            
        Raises:
            TelemetryProcessingError: If transformation fails
        """
        try:
            if transformation == "flatten":
                return [self._flatten_event(event) for event in events]
            elif transformation == "denormalize":
                return [self._denormalize_event(event) for event in events]
            elif transformation == "summary":
                return [self._summarize_event(event) for event in events]
            else:
                raise TelemetryProcessingError(
                    f"Unknown transformation: {transformation}",
                    error_code="TEL-410"
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to transform events",
                events_count=len(events),
                transformation=transformation,
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to transform events: {e}",
                error_code="TEL-411"
            )
    
    async def validate_processing_rules(
        self,
        events: List[TelemetryEvent]
    ) -> Dict[str, Any]:
        """
        Validate events against processing rules.
        
        Args:
            events: List of TelemetryEvents
            
        Returns:
            Validation results
            
        Raises:
            TelemetryProcessingError: If validation fails
        """
        try:
            validation_results = {
                "total_events": len(events),
                "valid_events": 0,
                "invalid_events": 0,
                "validation_errors": []
            }
            
            for event in events:
                try:
                    # Basic validation
                    if not event.event_id or not event.selector_name:
                        validation_results["invalid_events"] += 1
                        validation_results["validation_errors"].append({
                            "event_id": event.event_id,
                            "error": "Missing required fields"
                        })
                    else:
                        validation_results["valid_events"] += 1
                        
                except Exception as e:
                    validation_results["invalid_events"] += 1
                    validation_results["validation_errors"].append({
                        "event_id": getattr(event, 'event_id', 'unknown'),
                        "error": str(e)
                    })
            
            return validation_results
            
        except Exception as e:
            self.logger.error(
                "Failed to validate processing rules",
                events_count=len(events),
                error=str(e)
            )
            raise TelemetryProcessingError(
                f"Failed to validate processing rules: {e}",
                error_code="TEL-412"
            )
    
    async def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Processing statistics including events processed, errors, etc.
        """
        async with self._stats_lock:
            return {
                "batches_processed": self._stats.batches_processed,
                "events_processed": self._stats.events_processed,
                "events_failed": self._stats.events_failed,
                "processing_time_ms": self._stats.processing_time_ms,
                "average_batch_size": self._stats.average_batch_size,
                "retry_count": self._stats.retry_count,
                "last_processed": self._stats.last_processed,
                "concurrent_batches": self._stats.concurrent_batches,
                "enabled": self._enabled,
                "batch_config": {
                    "batch_size": self.batch_config.batch_size,
                    "max_concurrent_batches": self.batch_config.max_concurrent_batches,
                    "validation_enabled": self.batch_config.validation_enabled
                }
            }
    
    async def is_processing_enabled(self) -> bool:
        """
        Check if processing is enabled.
        
        Returns:
            True if processing is enabled
        """
        return self._enabled
    
    async def enable_processing(self) -> None:
        """
        Enable processing.
        """
        self._enabled = True
        if not self._processing_task or self._processing_task.done():
            self._start_processing()
        
        self.logger.info("Batch processing enabled")
    
    async def disable_processing(self) -> None:
        """
        Disable processing.
        """
        self._enabled = False
        self.logger.info("Batch processing disabled")
    
    async def get_processor_health(self) -> Dict[str, Any]:
        """
        Get processor health status.
        
        Returns:
            Health status information
        """
        try:
            stats = await self.get_processing_statistics()
            
            # Calculate health metrics
            error_rate = (
                stats["events_failed"] / max(1, stats["events_processed"] + stats["events_failed"])
            )
            
            # Determine health status
            if error_rate > 0.1:  # > 10% error rate
                health_status = "unhealthy"
            elif error_rate > 0.05:  # > 5% error rate
                health_status = "warning"
            else:
                health_status = "healthy"
            
            return {
                "status": health_status,
                "error_rate": error_rate,
                "enabled": stats["enabled"],
                "concurrent_batches": stats["concurrent_batches"],
                "last_processed": stats["last_processed"],
                "queue_size": self._batch_queue.qsize()
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get processor health",
                error=str(e)
            )
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def reset_processor_statistics(self) -> None:
        """
        Reset processor statistics.
        """
        async with self._stats_lock:
            self._stats = BatchStats()
        
        self.logger.info("Processor statistics reset")
    
    async def configure_processor(self, config: Dict[str, Any]) -> None:
        """
        Configure processor settings.
        
        Args:
            config: Processor configuration
        """
        # Update batch configuration
        if "batch_size" in config:
            self.batch_config.batch_size = config["batch_size"]
        
        if "max_concurrent_batches" in config:
            self.batch_config.max_concurrent_batches = config["max_concurrent_batches"]
            self._processing_semaphore = asyncio.Semaphore(self.batch_config.max_concurrent_batches)
        
        if "validation_enabled" in config:
            self.batch_config.validation_enabled = config["validation_enabled"]
        
        self.logger.info("Processor configuration updated")
    
    # Private methods
    
    def _start_processing(self) -> None:
        """Start the processing loop."""
        if self._processing_task is None or self._processing_task.done():
            self._processing_task = asyncio.create_task(self._processing_loop())
    
    async def _processing_loop(self) -> None:
        """Main processing loop."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for batch or timeout
                try:
                    batch = await asyncio.wait_for(
                        self._batch_queue.get(),
                        timeout=self.batch_config.max_wait_time.total_seconds()
                    )
                except asyncio.TimeoutError:
                    # Timeout - check if we should process partial batch
                    continue
                
                # Process batch with semaphore
                async with self._processing_semaphore:
                    try:
                        await self.process_events_batch(batch)
                    except Exception as e:
                        self.logger.error(
                            "Batch processing failed in loop",
                            batch_size=len(batch),
                            error=str(e)
                        )
                
            except Exception as e:
                self.logger.error(
                    "Processing loop error",
                    error=str(e)
                )
                await asyncio.sleep(1.0)  # Brief pause before retrying
    
    async def _process_events_internal(self, events: List[TelemetryEvent]) -> List[Dict[str, Any]]:
        """Process events internally with retry logic."""
        results = []
        
        for attempt in range(self.batch_config.retry_attempts + 1):
            try:
                # Process events (placeholder for actual processing logic)
                for event in events:
                    result = {
                        "event_id": event.event_id,
                        "processed": True,
                        "timestamp": datetime.utcnow()
                    }
                    results.append(result)
                
                break  # Success, exit retry loop
                
            except Exception as e:
                if attempt == self.batch_config.retry_attempts:
                    # Last attempt failed
                    raise
                
                # Wait before retry
                await asyncio.sleep(self.batch_config.retry_delay.total_seconds())
                
                async with self._stats_lock:
                    self._stats.retry_count += 1
        
        return results
    
    async def _validate_events_batch(self, events: List[TelemetryEvent]) -> None:
        """Validate a batch of events."""
        from ..utils.validation import validate_telemetry_data
        
        for event in events:
            errors = validate_telemetry_data(event, "event")
            if errors:
                raise TelemetryValidationError(
                    f"Event validation failed: {'; '.join(errors)}",
                    validation_errors=errors,
                    correlation_id=event.correlation_id
                )
    
    async def _execute_callbacks(
        self,
        callbacks: List[Callable],
        events: List[TelemetryEvent],
        extra_data: Optional[Any] = None
    ) -> None:
        """Execute callbacks safely."""
        for callback in callbacks:
            try:
                if extra_data is not None:
                    await callback(events, extra_data)
                else:
                    await callback(events)
            except Exception as e:
                self.logger.warning(
                    "Callback execution failed",
                    callback=callback.__name__,
                    error=str(e)
                )
    
    async def _update_stats(self, event_count: int, processing_time: float) -> None:
        """Update processing statistics."""
        async with self._stats_lock:
            self._stats.batches_processed += 1
            self._stats.events_processed += event_count
            self._stats.processing_time_ms += processing_time
            self._stats.average_batch_size = (
                self._stats.events_processed / self._stats.batches_processed
            )
            self._stats.last_processed = datetime.utcnow()
            self._stats.concurrent_batches = self.batch_config.max_concurrent_batches - self._processing_semaphore._value
    
    def _aggregate_metrics_list(self, metrics_list: List[Dict[str, Any]], aggregation_type: str) -> Dict[str, Any]:
        """Aggregate a list of metrics dictionaries."""
        result = {}
        
        # Get all metric names
        all_metrics = set()
        for metrics in metrics_list:
            all_metrics.update(metrics.keys())
        
        # Aggregate each metric
        for metric_name in all_metrics:
            values = [
                metrics[metric_name]
                for metrics in metrics_list
                if metric_name in metrics and isinstance(metrics[metric_name], (int, float))
            ]
            
            if values:
                if aggregation_type == "avg":
                    result[metric_name] = sum(values) / len(values)
                elif aggregation_type == "min":
                    result[metric_name] = min(values)
                elif aggregation_type == "max":
                    result[metric_name] = max(values)
                elif aggregation_type == "sum":
                    result[metric_name] = sum(values)
                elif aggregation_type == "count":
                    result[metric_name] = len(values)
        
        return result
    
    async def _detect_performance_anomalies(self, events: List[TelemetryEvent]) -> List[Dict[str, Any]]:
        """Detect performance anomalies."""
        anomalies = []
        
        # Extract resolution times
        resolution_times = []
        for event in events:
            if event.performance_metrics and hasattr(event.performance_metrics, 'resolution_time_ms'):
                resolution_times.append({
                    "value": event.performance_metrics.resolution_time_ms,
                    "event_id": event.event_id,
                    "selector_name": event.selector_name,
                    "timestamp": event.timestamp
                })
        
        if len(resolution_times) < 10:
            return anomalies  # Not enough data for anomaly detection
        
        # Calculate statistics
        values = [item["value"] for item in resolution_times]
        mean_value = sum(values) / len(values)
        
        # Simple threshold-based anomaly detection (3 sigma rule)
        import math
        variance = sum((x - mean_value) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)
        
        threshold = mean_value + (3 * std_dev)
        
        for item in resolution_times:
            if item["value"] > threshold:
                anomalies.append({
                    "type": "performance",
                    "metric": "resolution_time_ms",
                    "value": item["value"],
                    "threshold": threshold,
                    "event_id": item["event_id"],
                    "selector_name": item["selector_name"],
                    "timestamp": item["timestamp"],
                    "severity": "high" if item["value"] > threshold * 2 else "medium"
                })
        
        return anomalies
    
    async def _detect_quality_anomalies(self, events: List[TelemetryEvent]) -> List[Dict[str, Any]]:
        """Detect quality anomalies."""
        anomalies = []
        
        # Look for sudden drops in confidence scores
        confidence_scores = []
        for event in events:
            if event.quality_metrics and hasattr(event.quality_metrics, 'confidence_score'):
                confidence_scores.append({
                    "value": event.quality_metrics.confidence_score,
                    "event_id": event.event_id,
                    "selector_name": event.selector_name,
                    "timestamp": event.timestamp
                })
        
        if len(confidence_scores) < 10:
            return anomalies
        
        # Sort by timestamp
        confidence_scores.sort(key=lambda x: x["timestamp"])
        
        # Look for significant drops
        for i in range(1, len(confidence_scores)):
            prev_score = confidence_scores[i-1]["value"]
            curr_score = confidence_scores[i]["value"]
            
            # Detect significant drop (>50% decrease)
            if prev_score > 0.5 and curr_score < prev_score * 0.5:
                anomalies.append({
                    "type": "quality",
                    "metric": "confidence_score",
                    "value": curr_score,
                    "previous_value": prev_score,
                    "drop_percentage": ((prev_score - curr_score) / prev_score) * 100,
                    "event_id": confidence_scores[i]["event_id"],
                    "selector_name": confidence_scores[i]["selector_name"],
                    "timestamp": confidence_scores[i]["timestamp"],
                    "severity": "high" if curr_score < 0.3 else "medium"
                })
        
        return anomalies
    
    async def _detect_usage_anomalies(self, events: List[TelemetryEvent]) -> List[Dict[str, Any]]:
        """Detect usage anomalies."""
        anomalies = []
        
        # Group by selector
        selector_counts = defaultdict(int)
        for event in events:
            selector_counts[event.selector_name] += 1
        
        if len(selector_counts) < 5:
            return anomalies
        
        # Calculate statistics
        counts = list(selector_counts.values())
        mean_count = sum(counts) / len(counts)
        
        # Detect outliers (simple threshold)
        threshold = mean_count * 3  # 3x mean usage
        
        for selector_name, count in selector_counts.items():
            if count > threshold:
                anomalies.append({
                    "type": "usage",
                    "metric": "event_count",
                    "value": count,
                    "threshold": threshold,
                    "selector_name": selector_name,
                    "severity": "medium"
                })
        
        return anomalies
    
    def _extract_metric_value(self, event: TelemetryEvent, metric: str) -> Optional[float]:
        """Extract metric value from event."""
        if metric == "resolution_time_ms":
            if event.performance_metrics and hasattr(event.performance_metrics, 'resolution_time_ms'):
                return event.performance_metrics.resolution_time_ms
        elif metric == "confidence_score":
            if event.quality_metrics and hasattr(event.quality_metrics, 'confidence_score'):
                return event.quality_metrics.confidence_score
        elif metric == "strategy_switches_count":
            if event.strategy_metrics and hasattr(event.strategy_metrics, 'strategy_switches_count'):
                return event.strategy_metrics.strategy_switches_count
        
        return None
    
    def _event_matches_filters(self, event: TelemetryEvent, filters: Dict[str, Any]) -> bool:
        """Check if event matches filter criteria."""
        for key, value in filters.items():
            if hasattr(event, key):
                event_value = getattr(event, key)
                if event_value != value:
                    return False
            else:
                return False
        
        return True
    
    def _flatten_event(self, event: TelemetryEvent) -> Dict[str, Any]:
        """Flatten event to dictionary."""
        result = event.dict()
        
        # Flatten nested objects
        if event.performance_metrics:
            result.update({f"performance_{k}": v for k, v in event.performance_metrics.items()})
        
        if event.quality_metrics:
            result.update({f"quality_{k}": v for k, v in event.quality_metrics.items()})
        
        return result
    
    def _denormalize_event(self, event: TelemetryEvent) -> Dict[str, Any]:
        """Denormalize event for analytics."""
        return {
            "event_id": event.event_id,
            "selector_name": event.selector_name,
            "timestamp": event.timestamp.isoformat(),
            "operation_type": event.operation_type,
            "correlation_id": event.correlation_id,
            "success": event.quality_metrics.success if event.quality_metrics else None,
            "confidence_score": event.quality_metrics.confidence_score if event.quality_metrics else None,
            "resolution_time_ms": event.performance_metrics.resolution_time_ms if event.performance_metrics else None,
            "primary_strategy": event.strategy_metrics.primary_strategy if event.strategy_metrics else None,
            "has_error": event.error_data is not None
        }
    
    def _summarize_event(self, event: TelemetryEvent) -> Dict[str, Any]:
        """Create event summary."""
        return {
            "event_id": event.event_id,
            "selector_name": event.selector_name,
            "operation_type": event.operation_type,
            "timestamp": event.timestamp.isoformat(),
            "success": event.quality_metrics.success if event.quality_metrics else None,
            "has_performance_metrics": event.performance_metrics is not None,
            "has_quality_metrics": event.quality_metrics is not None,
            "has_strategy_metrics": event.strategy_metrics is not None,
            "has_error_data": event.error_data is not None
        }
