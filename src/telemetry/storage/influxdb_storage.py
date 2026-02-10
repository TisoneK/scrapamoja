"""
InfluxDB storage backend for telemetry data.

This module provides InfluxDB integration for high-performance time-series storage
of telemetry data with optimized batching and query capabilities.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from dataclasses import asdict

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
    from influxdb_client.client.query_api import QueryApi
    INFLUXDB_AVAILABLE = True
except ImportError:
    INFLUXDB_AVAILABLE = False

from ..interfaces.storage import ITelemetryStorage
from ..models.telemetry_event import TelemetryEvent
from ..models.performance_metrics import PerformanceMetrics
from ..models.quality_metrics import QualityMetrics
from ..models.strategy_metrics import StrategyMetrics
from ..models.error_data import ErrorData
from ..exceptions import TelemetryStorageError

logger = logging.getLogger(__name__)


class InfluxDBStorage(ITelemetryStorage):
    """InfluxDB storage backend for telemetry data."""
    
    def __init__(self, 
                 url: str,
                 token: str,
                 org: str,
                 bucket: str,
                 batch_size: int = 100,
                 flush_interval: float = 1.0):
        """
        Initialize InfluxDB storage.
        
        Args:
            url: InfluxDB server URL
            token: Authentication token
            org: Organization name
            bucket: Bucket name
            batch_size: Batch size for writes
            flush_interval: Flush interval in seconds
        """
        if not INFLUXDB_AVAILABLE:
            raise TelemetryStorageError("InfluxDB client not available. Install with: pip install influxdb-client")
        
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        self.query_api: Optional[QueryApi] = None
        self._write_buffer: List[Point] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self) -> None:
        """Initialize InfluxDB connection."""
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            
            # Use asynchronous write API for better performance
            self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Test connection
            health = self.client.health()
            if health.status != "pass":
                raise TelemetryStorageError(f"InfluxDB health check failed: {health.message}")
            
            self._running = True
            self._flush_task = asyncio.create_task(self._flush_loop())
            
            logger.info(f"InfluxDB storage initialized: {self.url}")
            
        except Exception as e:
            raise TelemetryStorageError(f"Failed to initialize InfluxDB: {e}")
    
    async def store_event(self, event: TelemetryEvent) -> None:
        """Store telemetry event."""
        point = self._event_to_point(event)
        
        async with self._buffer_lock:
            self._write_buffer.append(point)
            
            if len(self._write_buffer) >= self.batch_size:
                await self._flush_buffer()
    
    async def store_events(self, events: List[TelemetryEvent]) -> None:
        """Store multiple telemetry events."""
        points = [self._event_to_point(event) for event in events]
        
        async with self._buffer_lock:
            self._write_buffer.extend(points)
            
            if len(self._write_buffer) >= self.batch_size:
                await self._flush_buffer()
    
    async def get_events(self, 
                        selector_id: Optional[str] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        limit: Optional[int] = None) -> List[TelemetryEvent]:
        """Query telemetry events."""
        if not self.query_api:
            raise TelemetryStorageError("Query API not initialized")
        
        # Build query
        query = self._build_events_query(selector_id, start_time, end_time, limit)
        
        try:
            result = self.query_api.query(query, org=self.org)
            events = []
            
            for table in result:
                for record in table.records:
                    event = self._record_to_event(record)
                    if event:
                        events.append(event)
            
            return events
            
        except Exception as e:
            raise TelemetryStorageError(f"Failed to query events: {e}")
    
    async def get_metrics(self,
                         selector_id: Optional[str] = None,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get aggregated metrics."""
        if not self.query_api:
            raise TelemetryStorageError("Query API not initialized")
        
        # Build aggregation query
        query = self._build_metrics_query(selector_id, start_time, end_time)
        
        try:
            result = self.query_api.query(query, org=self.org)
            metrics = {}
            
            for table in result:
                for record in table.records:
                    field_name = record.get_field()
                    value = record.get_value()
                    metrics[field_name] = value
            
            return metrics
            
        except Exception as e:
            raise TelemetryStorageError(f"Failed to get metrics: {e}")
    
    async def delete_events(self,
                           selector_id: Optional[str] = None,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None) -> int:
        """Delete telemetry events."""
        # Note: InfluxDB 2.x doesn't support direct deletion via client
        # This would require using the InfluxDB API directly
        logger.warning("Event deletion not implemented for InfluxDB storage")
        return 0
    
    async def cleanup(self, retention_days: int = 30) -> int:
        """Clean up old telemetry data."""
        # Note: InfluxDB handles retention through bucket policies
        # This method could update bucket retention policies
        logger.info(f"InfluxDB cleanup handled by bucket retention policies")
        return 0
    
    async def close(self) -> None:
        """Close InfluxDB connection."""
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining buffer
        await self._flush_buffer()
        
        if self.write_api:
            self.write_api.close()
        
        if self.client:
            self.client.close()
        
        logger.info("InfluxDB storage closed")
    
    def _event_to_point(self, event: TelemetryEvent) -> Point:
        """Convert telemetry event to InfluxDB point."""
        point = Point("telemetry_event") \
            .tag("selector_id", event.selector_id) \
            .tag("strategy", event.strategy) \
            .tag("correlation_id", event.correlation_id) \
            .field("confidence_score", event.confidence_score) \
            .field("resolution_time_ms", event.resolution_time_ms) \
            .field("success", event.success) \
            .time(event.timestamp)
        
        # Add performance metrics
        if event.performance_metrics:
            perf = event.performance_metrics
            point = point \
                .field("strategy_time_ms", perf.strategy_time_ms) \
                .field("validation_time_ms", perf.validation_time_ms) \
                .field("total_time_ms", perf.total_time_ms) \
                .field("memory_usage_mb", perf.memory_usage_mb)
        
        # Add quality metrics
        if event.quality_metrics:
            quality = event.quality_metrics
            point = point \
                .field("text_similarity", quality.text_similarity) \
                .field("structural_match", quality.structural_match) \
                .field("context_relevance", quality.context_relevance)
        
        # Add strategy metrics
        if event.strategy_metrics:
            strategy = event.strategy_metrics
            point = point \
                .field("strategy_confidence", strategy.confidence) \
                .field("execution_time_ms", strategy.execution_time_ms) \
                .field("elements_matched", strategy.elements_matched)
        
        # Add error data
        if event.error_data:
            error = event.error_data
            point = point \
                .field("error_code", error.error_code) \
                .field("error_message", error.error_message) \
                .field("retry_count", error.retry_count) \
                .field("fallback_used", error.fallback_used)
        
        return point
    
    def _record_to_event(self, record) -> Optional[TelemetryEvent]:
        """Convert InfluxDB record to telemetry event."""
        try:
            values = record.values
            
            # Extract basic fields
            selector_id = values.get("selector_id")
            strategy = values.get("strategy")
            correlation_id = values.get("correlation_id")
            timestamp = record.get_time()
            
            # Create event
            event = TelemetryEvent(
                selector_id=selector_id,
                strategy=strategy,
                correlation_id=correlation_id,
                timestamp=timestamp,
                confidence_score=values.get("confidence_score", 0.0),
                resolution_time_ms=values.get("resolution_time_ms", 0),
                success=values.get("success", False)
            )
            
            # Add performance metrics if available
            perf_fields = ["strategy_time_ms", "validation_time_ms", "total_time_ms", "memory_usage_mb"]
            if any(field in values for field in perf_fields):
                event.performance_metrics = PerformanceMetrics(
                    strategy_time_ms=values.get("strategy_time_ms", 0),
                    validation_time_ms=values.get("validation_time_ms", 0),
                    total_time_ms=values.get("total_time_ms", 0),
                    memory_usage_mb=values.get("memory_usage_mb", 0)
                )
            
            return event
            
        except Exception as e:
            logger.error(f"Failed to convert record to event: {e}")
            return None
    
    def _build_events_query(self,
                           selector_id: Optional[str],
                           start_time: Optional[datetime],
                           end_time: Optional[datetime],
                           limit: Optional[int]) -> str:
        """Build query for events."""
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: {self._format_time(start_time)}, stop: {self._format_time(end_time)})
        |> filter(fn: (r) => r["_measurement"] == "telemetry_event")
        '''
        
        if selector_id:
            query += f'|> filter(fn: (r) => r["selector_id"] == "{selector_id}")\n'
        
        if limit:
            query += f'|> limit(n: {limit})\n'
        
        return query
    
    def _build_metrics_query(self,
                            selector_id: Optional[str],
                            start_time: Optional[datetime],
                            end_time: Optional[datetime]) -> str:
        """Build aggregation query for metrics."""
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: {self._format_time(start_time)}, stop: {self._format_time(end_time)})
        |> filter(fn: (r) => r["_measurement"] == "telemetry_event")
        '''
        
        if selector_id:
            query += f'|> filter(fn: (r) => r["selector_id"] == "{selector_id}")\n'
        
        query += '''
        |> group(columns: ["_field"])
        |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
        |> yield(name: "mean")
        '''
        
        return query
    
    def _format_time(self, dt: Optional[datetime]) -> str:
        """Format datetime for InfluxDB query."""
        if dt is None:
            return "0"
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    async def _flush_loop(self) -> None:
        """Background flush loop."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Flush loop error: {e}")
    
    async def _flush_buffer(self) -> None:
        """Flush write buffer to InfluxDB."""
        if not self.write_api or not self._write_buffer:
            return
        
        async with self._buffer_lock:
            if not self._write_buffer:
                return
            
            points = self._write_buffer.copy()
            self._write_buffer.clear()
        
        try:
            self.write_api.write(bucket=self.bucket, record=points)
            logger.debug(f"Flushed {len(points)} points to InfluxDB")
        except Exception as e:
            logger.error(f"Failed to flush points to InfluxDB: {e}")
            # Re-add points to buffer for retry
            async with self._buffer_lock:
                self._write_buffer.extend(points)


class InfluxDBStorageFactory:
    """Factory for creating InfluxDB storage instances."""
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> InfluxDBStorage:
        """Create InfluxDB storage from configuration."""
        required_fields = ['url', 'token', 'org', 'bucket']
        for field in required_fields:
            if field not in config:
                raise TelemetryStorageError(f"Missing required field: {field}")
        
        return InfluxDBStorage(
            url=config['url'],
            token=config['token'],
            org=config['org'],
            bucket=config['bucket'],
            batch_size=config.get('batch_size', 100),
            flush_interval=config.get('flush_interval', 1.0)
        )
