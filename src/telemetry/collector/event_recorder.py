"""
Event Recorder

Specialized recorder for telemetry events with high-performance
batching and async processing capabilities.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque

from ..models import TelemetryEvent
from ..configuration.telemetry_config import TelemetryConfiguration
from ..utils import TimingMeasurement
from ..exceptions import (
    TelemetryCollectionError, TelemetryValidationError,
    StorageUnavailableError
)
from ..configuration.logging import get_logger


@dataclass
class RecordingStats:
    """Statistics for event recording."""
    events_recorded: int = 0
    events_processed: int = 0
    recording_errors: int = 0
    processing_errors: int = 0
    batch_size: int = 0
    processing_time_ms: float = 0.0
    last_processed: Optional[datetime] = None


class EventRecorder:
    """
    High-performance event recorder with batching and async processing.
    
    Provides efficient event recording with configurable batching,
    compression, and error handling for high-volume telemetry.
    """
    
    def __init__(
        self,
        config: TelemetryConfiguration,
        storage_backend=None,
        batch_processor=None
    ):
        """
        Initialize event recorder.
        
        Args:
            config: Telemetry configuration
            storage_backend: Storage backend for direct storage
            batch_processor: Batch processor for async processing
        """
        self.config = config
        self.storage_backend = storage_backend
        self.batch_processor = batch_processor
        self.logger = get_logger("event_recorder")
        
        # Event queue for high-throughput recording
        self._event_queue: asyncio.Queue = asyncio.Queue(
            maxsize=config.get("max_queue_size", 10000)
        )
        
        # Processing configuration
        self._batch_size = config.get("max_batch_size", 100)
        self._flush_interval = config.get_flush_interval()
        self._compression_enabled = config.should_compress_storage()
        
        # Recording state
        self._recording_enabled = True
        self._processing_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self._stats = RecordingStats()
        self._stats_lock = asyncio.Lock()
        
        # Event callbacks
        self._pre_record_callbacks: List[Callable] = []
        self._post_record_callbacks: List[Callable] = []
        self._error_callbacks: List[Callable] = []
    
    async def start(self) -> None:
        """
        Start the event recorder processing loop.
        """
        if self._processing_task and not self._processing_task.done():
            return
        
        self._shutdown_event.clear()
        self._processing_task = asyncio.create_task(self._processing_loop())
        
        self.logger.info("Event recorder started")
    
    async def stop(self) -> None:
        """
        Stop the event recorder and process remaining events.
        """
        if not self._processing_task:
            return
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for processing to complete
        try:
            await asyncio.wait_for(self._processing_task, timeout=30.0)
        except asyncio.TimeoutError:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        # Process any remaining events
        await self._flush_remaining_events()
        
        self.logger.info("Event recorder stopped")
    
    async def record_event(self, event: TelemetryEvent) -> bool:
        """
        Record a telemetry event.
        
        Args:
            event: TelemetryEvent to record
            
        Returns:
            True if successfully queued for recording
            
        Raises:
            TelemetryCollectionError: If recording fails
        """
        if not self._recording_enabled:
            return False
        
        try:
            # Pre-record callbacks
            await self._execute_callbacks(self._pre_record_callbacks, event)
            
            # Validate event
            await self._validate_event(event)
            
            # Add to queue
            await self._event_queue.put(event)
            
            # Update statistics
            async with self._stats_lock:
                self._stats.events_recorded += 1
            
            self.logger.debug(
                "Event queued for recording",
                event_id=event.event_id,
                queue_size=self._event_queue.qsize()
            )
            
            # Post-record callbacks
            await self._execute_callbacks(self._post_record_callbacks, event)
            
            return True
            
        except Exception as e:
            async with self._stats_lock:
                self._stats.recording_errors += 1
            
            await self._execute_callbacks(self._error_callbacks, event, e)
            
            self.logger.error(
                "Failed to record event",
                event_id=getattr(event, 'event_id', 'unknown'),
                error=str(e)
            )
            
            raise TelemetryCollectionError(
                f"Failed to record event: {e}",
                error_code="TEL-314",
                correlation_id=getattr(event, 'correlation_id', None)
            )
    
    async def record_events_batch(self, events: List[TelemetryEvent]) -> int:
        """
        Record multiple events in batch.
        
        Args:
            events: List of TelemetryEvents to record
            
        Returns:
            Number of events successfully recorded
            
        Raises:
            TelemetryCollectionError: If batch recording fails
        """
        if not events:
            return 0
        
        recorded_count = 0
        errors = []
        
        for event in events:
            try:
                await self.record_event(event)
                recorded_count += 1
            except Exception as e:
                errors.append(str(e))
        
        if errors:
            self.logger.warning(
                "Some events failed to record",
                total_events=len(events),
                recorded_count=recorded_count,
                errors=len(errors)
            )
        
        return recorded_count
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status.
        
        Returns:
            Queue status information
        """
        queue_size = self._event_queue.qsize()
        max_size = self._event_queue._maxsize
        
        return {
            "current_size": queue_size,
            "max_size": max_size,
            "usage_percent": (queue_size / max_size) * 100 if max_size > 0 else 0,
            "is_full": queue_size >= max_size,
            "recording_enabled": self._recording_enabled,
            "processing_active": self._processing_task and not self._processing_task.done()
        }
    
    async def get_recording_statistics(self) -> RecordingStats:
        """
        Get recording statistics.
        
        Returns:
            Recording statistics
        """
        async with self._stats_lock:
            return RecordingStats(**self._stats.__dict__)
    
    async def enable_recording(self) -> None:
        """Enable event recording."""
        self._recording_enabled = True
        self.logger.info("Event recording enabled")
    
    async def disable_recording(self) -> None:
        """Disable event recording."""
        self._recording_enabled = False
        self.logger.info("Event recording disabled")
    
    async def flush_queue(self) -> int:
        """
        Flush the event queue immediately.
        
        Returns:
            Number of events processed
        """
        events_to_process = []
        
        # Get all events from queue
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                events_to_process.append(event)
            except asyncio.QueueEmpty:
                break
        
        if events_to_process:
            await self._process_events_batch(events_to_process)
        
        return len(events_to_process)
    
    def add_pre_record_callback(self, callback: Callable) -> None:
        """
        Add a pre-record callback.
        
        Args:
            callback: Callback function to execute before recording
        """
        self._pre_record_callbacks.append(callback)
    
    def add_post_record_callback(self, callback: Callable) -> None:
        """
        Add a post-record callback.
        
        Args:
            callback: Callback function to execute after recording
        """
        self._post_record_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable) -> None:
        """
        Add an error callback.
        
        Args:
            callback: Callback function to execute on errors
        """
        self._error_callbacks.append(callback)
    
    # Private methods
    
    async def _processing_loop(self) -> None:
        """Main processing loop for event recording."""
        batch = []
        last_flush = datetime.utcnow()
        
        while not self._shutdown_event.is_set():
            try:
                # Wait for events or timeout
                try:
                    timeout = self._flush_interval.total_seconds()
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=timeout
                    )
                    batch.append(event)
                except asyncio.TimeoutError:
                    # Timeout - flush current batch
                    pass
                
                # Check if we should flush
                current_time = datetime.utcnow()
                should_flush = (
                    len(batch) >= self._batch_size or
                    (batch and (current_time - last_flush) >= self._flush_interval)
                )
                
                if should_flush and batch:
                    await self._process_events_batch(batch.copy())
                    batch.clear()
                    last_flush = current_time
                
            except Exception as e:
                self.logger.error(
                    "Error in processing loop",
                    error=str(e)
                )
                await asyncio.sleep(1.0)  # Brief pause before retrying
        
        # Process remaining events on shutdown
        if batch:
            await self._process_events_batch(batch)
    
    async def _process_events_batch(self, events: List[TelemetryEvent]) -> None:
        """
        Process a batch of events.
        
        Args:
            events: List of events to process
        """
        if not events:
            return
        
        start_time = datetime.utcnow()
        processed_count = 0
        
        try:
            # Use batch processor if available
            if self.batch_processor:
                result = await self.batch_processor.process_events_batch(events)
                processed_count = result.get("processed_count", len(events))
            else:
                # Use storage backend directly
                if self.storage_backend:
                    processed_count = await self.storage_backend.store_events_batch(events)
                else:
                    # No storage - just count as processed
                    processed_count = len(events)
            
            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            async with self._stats_lock:
                self._stats.events_processed += processed_count
                self._stats.batch_size = len(events)
                self._stats.processing_time_ms = processing_time
                self._stats.last_processed = datetime.utcnow()
            
            self.logger.debug(
                "Processed event batch",
                batch_size=len(events),
                processed_count=processed_count,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            async with self._stats_lock:
                self._stats.processing_errors += 1
            
            self.logger.error(
                "Failed to process event batch",
                batch_size=len(events),
                error=str(e)
            )
    
    async def _flush_remaining_events(self) -> None:
        """Flush remaining events during shutdown."""
        remaining_events = []
        
        # Get all remaining events
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                remaining_events.append(event)
            except asyncio.QueueEmpty:
                break
        
        if remaining_events:
            self.logger.info(
                "Processing remaining events on shutdown",
                count=len(remaining_events)
            )
            
            try:
                await self._process_events_batch(remaining_events)
            except Exception as e:
                self.logger.error(
                    "Failed to process remaining events",
                    error=str(e)
                )
    
    async def _validate_event(self, event: TelemetryEvent) -> None:
        """Validate a telemetry event."""
        from ..utils.validation import validate_telemetry_data
        
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
        event: TelemetryEvent,
        error: Optional[Exception] = None
    ) -> None:
        """
        Execute callbacks safely.
        
        Args:
            callbacks: List of callback functions
            event: Telemetry event
            error: Optional error for error callbacks
        """
        for callback in callbacks:
            try:
                if error:
                    await callback(event, error)
                else:
                    await callback(event)
            except Exception as e:
                self.logger.warning(
                    "Callback execution failed",
                    callback=callback.__name__,
                    error=str(e)
                )
