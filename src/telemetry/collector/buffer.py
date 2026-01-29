"""
Memory Buffer for Event Collection

High-performance memory buffer for telemetry events with overflow
protection, batching, and efficient memory management.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field
import weakref

from ..models import TelemetryEvent
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import (
    TelemetryCollectionError, BufferOverflowError,
    TelemetryValidationError
)
from ..configuration.logging import get_logger


@dataclass
class BufferStats:
    """Statistics for buffer operations."""
    events_added: int = 0
    events_removed: int = 0
    events_dropped: int = 0
    overflows: int = 0
    flushes: int = 0
    last_flush: Optional[datetime] = None
    peak_size: int = 0
    average_size: float = 0.0
    memory_usage_mb: float = 0.0


@dataclass
class BufferConfig:
    """Configuration for buffer behavior."""
    max_size: int = 1000
    overflow_strategy: str = "drop_oldest"  # drop_oldest, drop_newest, block, error
    batch_size: int = 100
    flush_interval: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    compression_threshold: float = 0.8  # Compress when 80% full
    memory_limit_mb: float = 100.0  # Maximum memory usage in MB


class TelemetryBuffer:
    """
    High-performance memory buffer for telemetry events.
    
    Provides efficient event buffering with overflow protection,
    automatic flushing, and memory management for high-volume
    telemetry collection.
    """
    
    def __init__(self, config: TelemetryConfiguration, flush_callback: Optional[Callable] = None):
        """
        Initialize telemetry buffer.
        
        Args:
            config: Telemetry configuration
            flush_callback: Optional callback for automatic flushing
        """
        self.config = config
        self.flush_callback = flush_callback
        self.logger = get_logger("telemetry_buffer")
        
        # Buffer configuration
        self.buffer_config = BufferConfig(
            max_size=config.get("buffer_size", 1000),
            overflow_strategy=config.get("overflow_strategy", "drop_oldest"),
            batch_size=config.get("max_batch_size", 100),
            flush_interval=config.get_flush_interval(),
            compression_threshold=config.get("compression_threshold", 0.8),
            memory_limit_mb=config.get("memory_limit_mb", 100.0)
        )
        
        # Buffer storage
        self._buffer: deque = deque(maxlen=self.buffer_config.max_size)
        self._buffer_lock = asyncio.Lock()
        
        # Buffer state
        self._enabled = True
        self._auto_flush_enabled = True
        self._flush_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self._stats = BufferStats()
        self._stats_lock = asyncio.Lock()
        
        # Memory tracking
        self._memory_samples: List[float] = []
        self._last_memory_check = datetime.utcnow()
        
        # Event callbacks
        self._add_callbacks: List[Callable] = []
        self._remove_callbacks: List[Callable] = []
        self._overflow_callbacks: List[Callable] = []
        self._flush_callbacks: List[Callable] = []
        
        # Start auto-flush if enabled
        if self._auto_flush_enabled and self.flush_callback:
            self._start_auto_flush()
    
    async def add_event(self, event: TelemetryEvent) -> bool:
        """
        Add an event to the buffer.
        
        Args:
            event: TelemetryEvent to add
            
        Returns:
            True if event was added, False if dropped
            
        Raises:
            TelemetryCollectionError: If buffer operation fails
        """
        if not self._enabled:
            return False
        
        try:
            async with self._buffer_lock:
                # Check if buffer is full
                if len(self._buffer) >= self.buffer_config.max_size:
                    await self._handle_overflow(event)
                    return False
                
                # Add event to buffer
                self._buffer.append(event)
                
                # Update statistics
                await self._update_stats_on_add()
                
                # Execute add callbacks
                await self._execute_callbacks(self._add_callbacks, event)
                
                # Check if we should flush
                if len(self._buffer) >= self.buffer_config.batch_size:
                    await self._trigger_flush()
                
                self.logger.debug(
                    "Event added to buffer",
                    event_id=event.event_id,
                    buffer_size=len(self._buffer),
                    max_size=self.buffer_config.max_size
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to add event to buffer",
                event_id=getattr(event, 'event_id', 'unknown'),
                error=str(e)
            )
            raise TelemetryCollectionError(
                f"Failed to add event to buffer: {e}",
                error_code="TEL-301"
            )
    
    async def add_events_batch(self, events: List[TelemetryEvent]) -> int:
        """
        Add multiple events to the buffer.
        
        Args:
            events: List of TelemetryEvents to add
            
        Returns:
            Number of events successfully added
        """
        if not events or not self._enabled:
            return 0
        
        added_count = 0
        
        for event in events:
            if await self.add_event(event):
                added_count += 1
            else:
                break  # Stop if buffer is full and overflow strategy prevents adding
        
        return added_count
    
    async def get_events(self, count: Optional[int] = None) -> List[TelemetryEvent]:
        """
        Get events from buffer without removing them.
        
        Args:
            count: Maximum number of events to get
            
        Returns:
            List of events from buffer
        """
        async with self._buffer_lock:
            if count is None:
                return list(self._buffer)
            else:
                return list(self._buffer)[:count]
    
    async def remove_events(self, count: Optional[int] = None) -> List[TelemetryEvent]:
        """
        Remove and return events from buffer.
        
        Args:
            count: Maximum number of events to remove
            
        Returns:
            List of removed events
        """
        async with self._buffer_lock:
            if count is None or count >= len(self._buffer):
                events = list(self._buffer)
                self._buffer.clear()
            else:
                events = []
                for _ in range(count):
                    if self._buffer:
                        events.append(self._buffer.popleft())
                    else:
                        break
            
            # Update statistics
            await self._update_stats_on_remove(len(events))
            
            # Execute remove callbacks
            for event in events:
                await self._execute_callbacks(self._remove_callbacks, event)
            
            return events
    
    async def flush(self) -> List[TelemetryEvent]:
        """
        Flush all events from buffer.
        
        Returns:
            List of all events that were in the buffer
        """
        events = await self.remove_events()
        
        if events and self.flush_callback:
            try:
                await self.flush_callback(events)
            except Exception as e:
                self.logger.error(
                    "Flush callback failed",
                    events_count=len(events),
                    error=str(e)
                )
        
        # Update statistics
        async with self._stats_lock:
            self._stats.flushes += 1
            self._stats.last_flush = datetime.utcnow()
        
        # Execute flush callbacks
        await self._execute_callbacks(self._flush_callbacks, events)
        
        self.logger.info(
            "Buffer flushed",
            events_count=len(events)
        )
        
        return events
    
    async def get_buffer_status(self) -> Dict[str, Any]:
        """
        Get current buffer status.
        
        Returns:
            Buffer status information
        """
        async with self._buffer_lock:
            current_size = len(self._buffer)
            max_size = self.buffer_config.max_size
            usage_percent = (current_size / max_size) * 100 if max_size > 0 else 0
            
            # Get memory usage
            memory_usage = await self._estimate_memory_usage()
            
            return {
                "current_size": current_size,
                "max_size": max_size,
                "usage_percent": usage_percent,
                "is_full": current_size >= max_size,
                "is_empty": current_size == 0,
                "memory_usage_mb": memory_usage,
                "memory_limit_mb": self.buffer_config.memory_limit_mb,
                "memory_usage_percent": (memory_usage / self.buffer_config.memory_limit_mb) * 100,
                "enabled": self._enabled,
                "auto_flush_enabled": self._auto_flush_enabled,
                "overflow_strategy": self.buffer_config.overflow_strategy
            }
    
    async def get_statistics(self) -> BufferStats:
        """
        Get buffer statistics.
        
        Returns:
            Buffer statistics
        """
        async with self._stats_lock:
            # Update average size
            if self._stats.events_added > 0:
                self._stats.average_size = self._stats.events_added / max(1, self._stats.events_added + self._stats.events_removed)
            
            # Update memory usage
            self._stats.memory_usage_mb = await self._estimate_memory_usage()
            
            return BufferStats(**self._stats.__dict__)
    
    async def clear(self) -> int:
        """
        Clear all events from buffer.
        
        Returns:
            Number of events cleared
        """
        async with self._buffer_lock:
            cleared_count = len(self._buffer)
            self._buffer.clear()
            
            # Update statistics
            async with self._stats_lock:
                self._stats.events_removed += cleared_count
            
            self.logger.info(
                "Buffer cleared",
                events_cleared=cleared_count
            )
            
            return cleared_count
    
    async def enable(self) -> None:
        """Enable the buffer."""
        self._enabled = True
        self.logger.info("Buffer enabled")
    
    async def disable(self) -> None:
        """Disable the buffer."""
        self._enabled = False
        self.logger.info("Buffer disabled")
    
    async def enable_auto_flush(self) -> None:
        """Enable automatic flushing."""
        if not self._auto_flush_enabled and self.flush_callback:
            self._auto_flush_enabled = True
            self._start_auto_flush()
    
    async def disable_auto_flush(self) -> None:
        """Disable automatic flushing."""
        self._auto_flush_enabled = False
        if self._flush_task:
            self._flush_task.cancel()
            self._flush_task = None
    
    def add_add_callback(self, callback: Callable) -> None:
        """Add callback for event addition."""
        self._add_callbacks.append(callback)
    
    def add_remove_callback(self, callback: Callable) -> None:
        """Add callback for event removal."""
        self._remove_callbacks.append(callback)
    
    def add_overflow_callback(self, callback: Callable) -> None:
        """Add callback for overflow events."""
        self._overflow_callbacks.append(callback)
    
    def add_flush_callback(self, callback: Callable) -> None:
        """Add callback for flush events."""
        self._flush_callbacks.append(callback)
    
    async def shutdown(self) -> None:
        """Shutdown the buffer and clean up resources."""
        # Disable buffer
        await self.disable()
        
        # Stop auto-flush
        await self.disable_auto_flush()
        
        # Flush remaining events
        remaining_events = await self.flush()
        
        self.logger.info(
            "Buffer shutdown completed",
            remaining_events=len(remaining_events)
        )
    
    # Private methods
    
    async def _handle_overflow(self, event: TelemetryEvent) -> None:
        """Handle buffer overflow based on strategy."""
        strategy = self.buffer_config.overflow_strategy
        
        async with self._stats_lock:
            self._stats.overflows += 1
        
        if strategy == "drop_oldest":
            # Remove oldest event and add new one
            if self._buffer:
                dropped_event = self._buffer.popleft()
                self._buffer.append(event)
                
                async with self._stats_lock:
                    self._stats.events_dropped += 1
                
                await self._execute_callbacks(self._overflow_callbacks, dropped_event)
                
                self.logger.warning(
                    "Buffer overflow - dropped oldest event",
                    dropped_event_id=dropped_event.event_id,
                    new_event_id=event.event_id
                )
        
        elif strategy == "drop_newest":
            # Drop the new event
            async with self._stats_lock:
                self._stats.events_dropped += 1
            
            await self._execute_callbacks(self._overflow_callbacks, event)
            
            self.logger.warning(
                "Buffer overflow - dropped new event",
                dropped_event_id=event.event_id
            )
        
        elif strategy == "block":
            # Wait for space to become available
            # This would need to be implemented with a condition variable
            pass
        
        elif strategy == "error":
            # Raise an error
            raise BufferOverflowError(
                self.buffer_config.max_size,
                len(self._buffer),
                correlation_id=event.correlation_id
            )
    
    async def _trigger_flush(self) -> None:
        """Trigger a flush if callback is available."""
        if self.flush_callback and self._auto_flush_enabled:
            try:
                events = await self.remove_events(self.buffer_config.batch_size)
                if events:
                    await self.flush_callback(events)
                    
                    async with self._stats_lock:
                        self._stats.flushes += 1
                        self._stats.last_flush = datetime.utcnow()
            except Exception as e:
                self.logger.error(
                    "Auto-flush failed",
                    error=str(e)
                )
    
    def _start_auto_flush(self) -> None:
        """Start the auto-flush task."""
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._auto_flush_loop())
    
    async def _auto_flush_loop(self) -> None:
        """Auto-flush loop."""
        while not self._shutdown_event.is_set() and self._auto_flush_enabled:
            try:
                # Wait for flush interval or shutdown
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.buffer_config.flush_interval.total_seconds()
                )
                
                if self._shutdown_event.is_set():
                    break
                
                # Check if we should flush
                async with self._buffer_lock:
                    if len(self._buffer) > 0:
                        await self._trigger_flush()
                
            except asyncio.TimeoutError:
                # Timeout - check if we should flush
                continue
            except Exception as e:
                self.logger.error(
                    "Auto-flush loop error",
                    error=str(e)
                )
                await asyncio.sleep(1.0)  # Brief pause before retrying
    
    async def _update_stats_on_add(self) -> None:
        """Update statistics when event is added."""
        async with self._stats_lock:
            self._stats.events_added += 1
            current_size = len(self._buffer)
            if current_size > self._stats.peak_size:
                self._stats.peak_size = current_size
    
    async def _update_stats_on_remove(self, count: int) -> None:
        """Update statistics when events are removed."""
        async with self._stats_lock:
            self._stats.events_removed += count
    
    async def _estimate_memory_usage(self) -> float:
        """Estimate current memory usage in MB."""
        try:
            # Sample memory usage periodically
            now = datetime.utcnow()
            if (now - self._last_memory_check).total_seconds() < 5:
                # Return cached value
                return sum(self._memory_samples) / len(self._memory_samples) if self._memory_samples else 0.0
            
            self._last_memory_check = now
            
            # Estimate memory usage based on buffer size
            async with self._buffer_lock:
                if not self._buffer:
                    return 0.0
                
                # Sample a few events to estimate size
                sample_size = min(10, len(self._buffer))
                sample_events = list(self._buffer)[:sample_size]
                
                # Estimate event size (rough approximation)
                total_sample_size = 0
                for event in sample_events:
                    # Convert to dict and measure string length
                    event_str = str(event.dict())
                    total_sample_size += len(event_str.encode('utf-8'))
                
                avg_event_size = total_sample_size / sample_size if sample_size > 0 else 0
                estimated_usage = (avg_event_size * len(self._buffer)) / (1024 * 1024)  # Convert to MB
                
                # Update samples
                self._memory_samples.append(estimated_usage)
                if len(self._memory_samples) > 10:  # Keep last 10 samples
                    self._memory_samples.pop(0)
                
                return estimated_usage
                
        except Exception:
            return 0.0
    
    async def _execute_callbacks(
        self,
        callbacks: List[Callable],
        event: TelemetryEvent,
        extra_data: Optional[Any] = None
    ) -> None:
        """Execute callbacks safely."""
        for callback in callbacks:
            try:
                if extra_data is not None:
                    await callback(event, extra_data)
                else:
                    await callback(event)
            except Exception as e:
                self.logger.warning(
                    "Buffer callback execution failed",
                    callback=callback.__name__,
                    error=str(e)
                )


class BufferManager:
    """
    Manager for multiple telemetry buffers.
    
    Provides coordinated management of multiple buffers with
    different configurations and purposes.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize buffer manager.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("buffer_manager")
        
        # Buffers
        self._buffers: Dict[str, TelemetryBuffer] = {}
        self._buffers_lock = asyncio.Lock()
    
    async def create_buffer(
        self,
        name: str,
        buffer_config: Optional[BufferConfig] = None,
        flush_callback: Optional[Callable] = None
    ) -> TelemetryBuffer:
        """
        Create a new buffer.
        
        Args:
            name: Buffer name
            buffer_config: Optional buffer configuration
            flush_callback: Optional flush callback
            
        Returns:
            Created buffer
        """
        async with self._buffers_lock:
            if name in self._buffers:
                raise TelemetryCollectionError(
                    f"Buffer {name} already exists",
                    error_code="TEL-302"
                )
            
            buffer = TelemetryBuffer(
                self.config,
                flush_callback
            )
            
            self._buffers[name] = buffer
            
            self.logger.info(
                "Buffer created",
                name=name,
                max_size=buffer.buffer_config.max_size
            )
            
            return buffer
    
    async def get_buffer(self, name: str) -> Optional[TelemetryBuffer]:
        """
        Get a buffer by name.
        
        Args:
            name: Buffer name
            
        Returns:
            Buffer or None if not found
        """
        async with self._buffers_lock:
            return self._buffers.get(name)
    
    async def remove_buffer(self, name: str) -> bool:
        """
        Remove a buffer.
        
        Args:
            name: Buffer name
            
        Returns:
            True if buffer was removed
        """
        async with self._buffers_lock:
            if name in self._buffers:
                buffer = self._buffers.pop(name)
                await buffer.shutdown()
                
                self.logger.info(
                    "Buffer removed",
                    name=name
                )
                
                return True
            
            return False
    
    async def get_all_buffer_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all buffers.
        
        Returns:
            Dictionary of buffer statuses
        """
        async with self._buffers_lock:
            status = {}
            
            for name, buffer in self._buffers.items():
                try:
                    status[name] = await buffer.get_buffer_status()
                except Exception as e:
                    status[name] = {"error": str(e)}
            
            return status
    
    async def get_all_statistics(self) -> Dict[str, BufferStats]:
        """
        Get statistics for all buffers.
        
        Returns:
            Dictionary of buffer statistics
        """
        async with self._buffers_lock:
            stats = {}
            
            for name, buffer in self._buffers.items():
                try:
                    stats[name] = await buffer.get_statistics()
                except Exception as e:
                    self.logger.warning(
                        "Failed to get buffer statistics",
                        name=name,
                        error=str(e)
                    )
            
            return stats
    
    async def shutdown_all(self) -> None:
        """Shutdown all buffers."""
        async with self._buffers_lock:
            for name, buffer in self._buffers.items():
                try:
                    await buffer.shutdown()
                except Exception as e:
                    self.logger.warning(
                        "Failed to shutdown buffer",
                        name=name,
                        error=str(e)
                    )
            
            self._buffers.clear()
            
            self.logger.info("All buffers shutdown")
