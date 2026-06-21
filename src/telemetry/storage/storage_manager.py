"""
Storage Manager

Centralized storage management for telemetry data with multiple
backend support, retention policies, and data lifecycle management.
"""

import asyncio
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from pathlib import Path
from abc import ABC, abstractmethod

from ..interfaces import ITelemetryStorage
from ..models import TelemetryEvent
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import (
    TelemetryStorageError, TelemetryValidationError,
    StorageUnavailableError
)
from ..configuration.logging import get_logger


class StorageManager(ITelemetryStorage):
    """
    Centralized storage manager for telemetry data.
    
    Provides unified storage interface with multiple backend support,
    retention management, and data lifecycle operations.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize storage manager.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("storage_manager")
        
        # Storage backends
        self._primary_backend: Optional[ITelemetryStorage] = None
        self._fallback_backends: List[ITelemetryStorage] = []
        
        # Storage statistics
        self._storage_stats = {
            "events_stored": 0,
            "events_retrieved": 0,
            "storage_errors": 0,
            "fallback_usage": 0,
            "retention_cleanups": 0,
            "start_time": datetime.utcnow()
        }
        
        # Initialize backends
        self._initialize_backends()
    
    def _initialize_backends(self) -> None:
        """Initialize storage backends based on configuration."""
        storage_type = self.config.get("storage_type", "json")
        
        try:
            if storage_type == "json":
                from .json_storage import JSONStorage
                self._primary_backend = JSONStorage(self.config)
            elif storage_type == "influxdb":
                # InfluxDB backend would be implemented here
                self.logger.warning("InfluxDB backend not yet implemented, using JSON fallback")
                from .json_storage import JSONStorage
                self._primary_backend = JSONStorage(self.config)
            else:
                raise TelemetryStorageError(
                    f"Unsupported storage type: {storage_type}",
                    error_code="TEL-201"
                )
            
            # Add JSON storage as fallback
            if storage_type != "json":
                from .json_storage import JSONStorage
                fallback_config = TelemetryConfiguration({"storage_type": "json"})
                self._fallback_backends.append(JSONStorage(fallback_config))
            
            self.logger.info(
                "Storage backends initialized",
                primary=type(self._primary_backend).__name__,
                fallbacks=[type(b).__name__ for b in self._fallback_backends]
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize storage backends",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Storage initialization failed: {e}",
                error_code="TEL-202"
            )
    
    async def store_event(self, event: TelemetryEvent) -> bool:
        """
        Store a telemetry event.
        
        Args:
            event: TelemetryEvent to store
            
        Returns:
            True if successfully stored, False otherwise
            
        Raises:
            TelemetryStorageError: If storage fails
        """
        try:
            # Validate event
            await self._validate_event(event)
            
            # Try primary backend first
            if self._primary_backend:
                try:
                    success = await self._primary_backend.store_event(event)
                    if success:
                        self._storage_stats["events_stored"] += 1
                        return True
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    success = await backend.store_event(event)
                    if success:
                        self._storage_stats["events_stored"] += 1
                        self._storage_stats["fallback_usage"] += 1
                        self.logger.info(
                            "Event stored using fallback backend",
                            backend=type(backend).__name__
                        )
                        return True
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            # All backends failed
            self._storage_stats["storage_errors"] += 1
            raise StorageUnavailableError(
                f"All storage backends unavailable for event {event.event_id}",
                correlation_id=event.correlation_id
            )
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to store event",
                event_id=getattr(event, 'event_id', 'unknown'),
                error=str(e)
            )
            raise
    
    async def store_events_batch(self, events: List[TelemetryEvent]) -> int:
        """
        Store multiple telemetry events in batch.
        
        Args:
            events: List of TelemetryEvents to store
            
        Returns:
            Number of events successfully stored
            
        Raises:
            TelemetryStorageError: If storage fails
        """
        if not events:
            return 0
        
        try:
            # Validate all events
            for event in events:
                await self._validate_event(event)
            
            # Try primary backend first
            if self._primary_backend:
                try:
                    stored_count = await self._primary_backend.store_events_batch(events)
                    if stored_count > 0:
                        self._storage_stats["events_stored"] += stored_count
                        return stored_count
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for batch, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    stored_count = await backend.store_events_batch(events)
                    if stored_count > 0:
                        self._storage_stats["events_stored"] += stored_count
                        self._storage_stats["fallback_usage"] += 1
                        self.logger.info(
                            "Batch stored using fallback backend",
                            backend=type(backend).__name__,
                            stored_count=stored_count
                        )
                        return stored_count
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for batch",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            # All backends failed
            self._storage_stats["storage_errors"] += 1
            raise StorageUnavailableError(
                "All storage backends unavailable for batch storage"
            )
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to store event batch",
                batch_size=len(events),
                error=str(e)
            )
            raise
    
    async def get_event(self, event_id: str) -> Optional[TelemetryEvent]:
        """
        Retrieve a telemetry event by ID.
        
        Args:
            event_id: Unique event identifier
            
        Returns:
            TelemetryEvent if found, None otherwise
            
        Raises:
            TelemetryStorageError: If retrieval fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    event = await self._primary_backend.get_event(event_id)
                    if event:
                        self._storage_stats["events_retrieved"] += 1
                        return event
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for retrieval, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    event = await backend.get_event(event_id)
                    if event:
                        self._storage_stats["events_retrieved"] += 1
                        self._storage_stats["fallback_usage"] += 1
                        return event
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for retrieval",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            # Event not found in any backend
            return None
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to retrieve event",
                event_id=event_id,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve event {event_id}: {e}",
                error_code="TEL-203"
            )
    
    async def get_events_by_selector(
        self,
        selector_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[TelemetryEvent]:
        """
        Retrieve events for a specific selector.
        
        Args:
            selector_name: Name/identifier of the selector
            start_time: Start time for query range
            end_time: End time for query range
            limit: Maximum number of events to return
            
        Returns:
            List of TelemetryEvents
            
        Raises:
            TelemetryStorageError: If retrieval fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    events = await self._primary_backend.get_events_by_selector(
                        selector_name, start_time, end_time, limit
                    )
                    if events:
                        self._storage_stats["events_retrieved"] += len(events)
                        return events
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for selector query, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    events = await backend.get_events_by_selector(
                        selector_name, start_time, end_time, limit
                    )
                    if events:
                        self._storage_stats["events_retrieved"] += len(events)
                        self._storage_stats["fallback_usage"] += 1
                        return events
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for selector query",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            return []
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to retrieve events by selector",
                selector_name=selector_name,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve events for selector {selector_name}: {e}",
                error_code="TEL-204"
            )
    
    async def get_events_by_correlation(
        self,
        correlation_id: str,
        limit: Optional[int] = None
    ) -> List[TelemetryEvent]:
        """
        Retrieve events by correlation ID.
        
        Args:
            correlation_id: Correlation ID for operation tracking
            limit: Maximum number of events to return
            
        Returns:
            List of TelemetryEvents
            
        Raises:
            TelemetryStorageError: If retrieval fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    events = await self._primary_backend.get_events_by_correlation(
                        correlation_id, limit
                    )
                    if events:
                        self._storage_stats["events_retrieved"] += len(events)
                        return events
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for correlation query, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    events = await backend.get_events_by_correlation(correlation_id, limit)
                    if events:
                        self._storage_stats["events_retrieved"] += len(events)
                        self._storage_stats["fallback_usage"] += 1
                        return events
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for correlation query",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            return []
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to retrieve events by correlation",
                correlation_id=correlation_id,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve events for correlation {correlation_id}: {e}",
                error_code="TEL-205"
            )
    
    async def get_events_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        selector_name: Optional[str] = None,
        operation_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[TelemetryEvent]:
        """
        Retrieve events within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            selector_name: Optional selector filter
            operation_type: Optional operation type filter
            limit: Maximum number of events to return
            
        Returns:
            List of TelemetryEvents
            
        Raises:
            TelemetryStorageError: If retrieval fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    events = await self._primary_backend.get_events_by_time_range(
                        start_time, end_time, selector_name, operation_type, limit
                    )
                    if events:
                        self._storage_stats["events_retrieved"] += len(events)
                        return events
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for time range query, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    events = await backend.get_events_by_time_range(
                        start_time, end_time, selector_name, operation_type, limit
                    )
                    if events:
                        self._storage_stats["events_retrieved"] += len(events)
                        self._storage_stats["fallback_usage"] += 1
                        return events
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for time range query",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            return []
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to retrieve events by time range",
                start_time=start_time,
                end_time=end_time,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve events for time range: {e}",
                error_code="TEL-206"
            )
    
    async def get_failed_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[TelemetryEvent]:
        """
        Retrieve failed events.
        
        Args:
            start_time: Start time for query range
            end_time: End time for query range
            limit: Maximum number of events to return
            
        Returns:
            List of failed TelemetryEvents
            
        Raises:
            TelemetryStorageError: If retrieval fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    events = await self._primary_backend.get_failed_events(
                        start_time, end_time, limit
                    )
                    if events:
                        self._storage_stats["events_retrieved"] += len(events)
                        return events
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for failed events query, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    events = await backend.get_failed_events(start_time, end_time, limit)
                    if events:
                        self._storage_stats["events_retrieved"] += len(events)
                        self._storage_stats["fallback_usage"] += 1
                        return events
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for failed events query",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            return []
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to retrieve failed events",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve failed events: {e}",
                error_code="TEL-207"
            )
    
    async def get_performance_metrics(
        self,
        selector_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        aggregation: str = "avg"
    ) -> Dict[str, Any]:
        """
        Get aggregated performance metrics.
        
        Args:
            selector_name: Optional selector filter
            start_time: Start time for aggregation
            end_time: End time for aggregation
            aggregation: Aggregation type (avg, min, max, sum, count)
            
        Returns:
            Aggregated performance metrics
            
        Raises:
            TelemetryStorageError: If query fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    metrics = await self._primary_backend.get_performance_metrics(
                        selector_name, start_time, end_time, aggregation
                    )
                    if metrics:
                        return metrics
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for performance metrics, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    metrics = await backend.get_performance_metrics(
                        selector_name, start_time, end_time, aggregation
                    )
                    if metrics:
                        return metrics
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for performance metrics",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            return {}
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to retrieve performance metrics",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve performance metrics: {e}",
                error_code="TEL-208"
            )
    
    async def get_quality_metrics(
        self,
        selector_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get quality metrics summary.
        
        Args:
            selector_name: Optional selector filter
            start_time: Start time for query
            end_time: End time for query
            
        Returns:
            Quality metrics summary
            
        Raises:
            TelemetryStorageError: If query fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    metrics = await self._primary_backend.get_quality_metrics(
                        selector_name, start_time, end_time
                    )
                    if metrics:
                        return metrics
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for quality metrics, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    metrics = await backend.get_quality_metrics(
                        selector_name, start_time, end_time
                    )
                    if metrics:
                        return metrics
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for quality metrics",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            return {}
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to retrieve quality metrics",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve quality metrics: {e}",
                error_code="TEL-209"
            )
    
    async def delete_event(self, event_id: str) -> bool:
        """
        Delete a telemetry event.
        
        Args:
            event_id: Unique event identifier
            
        Returns:
            True if successfully deleted, False otherwise
            
        Raises:
            TelemetryStorageError: If deletion fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    success = await self._primary_backend.delete_event(event_id)
                    if success:
                        return True
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for deletion, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    success = await backend.delete_event(event_id)
                    if success:
                        return True
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for deletion",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            return False
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to delete event",
                event_id=event_id,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to delete event {event_id}: {e}",
                error_code="TEL-210"
            )
    
    async def delete_events_by_selector(
        self,
        selector_name: str,
        before_time: Optional[datetime] = None
    ) -> int:
        """
        Delete events for a selector.
        
        Args:
            selector_name: Name/identifier of the selector
            before_time: Delete events before this time
            
        Returns:
            Number of events deleted
            
        Raises:
            TelemetryStorageError: If deletion fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    deleted_count = await self._primary_backend.delete_events_by_selector(
                        selector_name, before_time
                    )
                    if deleted_count > 0:
                        return deleted_count
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for selector deletion, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    deleted_count = await backend.delete_events_by_selector(
                        selector_name, before_time
                    )
                    if deleted_count > 0:
                        return deleted_count
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for selector deletion",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            return 0
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to delete events by selector",
                selector_name=selector_name,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to delete events for selector {selector_name}: {e}",
                error_code="TEL-211"
            )
    
    async def delete_events_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """
        Delete events within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Number of events deleted
            
        Raises:
            TelemetryStorageError: If deletion fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    deleted_count = await self._primary_backend.delete_events_by_time_range(
                        start_time, end_time
                    )
                    if deleted_count > 0:
                        return deleted_count
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for time range deletion, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    deleted_count = await backend.delete_events_by_time_range(
                        start_time, end_time
                    )
                    if deleted_count > 0:
                        return deleted_count
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for time range deletion",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            return 0
            
        except Exception as e:
            self._storage_stats["storage_errors"] += 1
            self.logger.error(
                "Failed to delete events by time range",
                start_time=start_time,
                end_time=end_time,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to delete events for time range: {e}",
                error_code="TEL-212"
            )
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Storage statistics including total events, size, etc.
        """
        try:
            # Get primary backend stats
            primary_stats = {}
            if self._primary_backend:
                try:
                    primary_stats = await self._primary_backend.get_storage_statistics()
                except Exception as e:
                    self.logger.warning(
                        "Failed to get primary backend statistics",
                        error=str(e)
                    )
            
            # Combine with manager stats
            runtime = datetime.utcnow() - self._storage_stats["start_time"]
            
            return {
                **self._storage_stats,
                "runtime_seconds": runtime.total_seconds(),
                "events_per_second": (
                    self._storage_stats["events_stored"] / runtime.total_seconds()
                    if runtime.total_seconds() > 0 else 0
                ),
                "error_rate": (
                    self._storage_stats["storage_errors"] / 
                    max(1, self._storage_stats["events_stored"])
                ),
                "fallback_rate": (
                    self._storage_stats["fallback_usage"] / 
                    max(1, self._storage_stats["events_stored"])
                ),
                "primary_backend": type(self._primary_backend).__name__ if self._primary_backend else None,
                "fallback_backends": [type(b).__name__ for b in self._fallback_backends],
                "primary_backend_stats": primary_stats
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get storage statistics",
                error=str(e)
            )
            return self._storage_stats
    
    async def is_available(self) -> bool:
        """
        Check if storage is available.
        
        Returns:
            True if storage is available
        """
        # Check primary backend
        if self._primary_backend:
            try:
                return await self._primary_backend.is_available()
            except Exception:
                pass
        
        # Check fallback backends
        for backend in self._fallback_backends:
            try:
                if await backend.is_available():
                    return True
            except Exception:
                continue
        
        return False
    
    async def get_retention_info(self) -> Dict[str, Any]:
        """
        Get retention information.
        
        Returns:
            Retention policy information
        """
        retention_days = self.config.get("retention_days", 30)
        
        return {
            "retention_days": retention_days,
            "retention_period": timedelta(days=retention_days),
            "cleanup_enabled": True,
            "last_cleanup": self._storage_stats.get("last_cleanup"),
            "total_cleanups": self._storage_stats["retention_cleanups"]
        }
    
    async def apply_retention_policy(self) -> int:
        """
        Apply retention policy to clean up old data.
        
        Returns:
            Number of events cleaned up
        """
        try:
            retention_days = self.config.get("retention_days", 30)
            cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
            
            total_deleted = 0
            
            # Apply to primary backend
            if self._primary_backend:
                try:
                    deleted = await self._primary_backend.delete_events_by_time_range(
                        datetime.min, cutoff_time
                    )
                    total_deleted += deleted
                except Exception as e:
                    self.logger.warning(
                        "Failed to apply retention policy to primary backend",
                        error=str(e)
                    )
            
            # Apply to fallback backends
            for backend in self._fallback_backends:
                try:
                    deleted = await backend.delete_events_by_time_range(
                        datetime.min, cutoff_time
                    )
                    total_deleted += deleted
                except Exception as e:
                    self.logger.warning(
                        "Failed to apply retention policy to fallback backend",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
            
            # Update statistics
            self._storage_stats["retention_cleanups"] += 1
            self._storage_stats["last_cleanup"] = datetime.utcnow()
            
            self.logger.info(
                "Retention policy applied",
                retention_days=retention_days,
                events_deleted=total_deleted
            )
            
            return total_deleted
            
        except Exception as e:
            self.logger.error(
                "Failed to apply retention policy",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to apply retention policy: {e}",
                error_code="TEL-213"
            )
    
    async def backup_data(self, backup_path: str) -> bool:
        """
        Backup telemetry data.
        
        Args:
            backup_path: Path for backup file
            
        Returns:
            True if backup successful
            
        Raises:
            TelemetryStorageError: If backup fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    return await self._primary_backend.backup_data(backup_path)
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for backup, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    success = await backend.backup_data(backup_path)
                    if success:
                        return True
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for backup",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(
                "Failed to backup data",
                backup_path=backup_path,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to backup data: {e}",
                error_code="TEL-214"
            )
    
    async def restore_data(self, backup_path: str) -> int:
        """
        Restore telemetry data from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Number of events restored
            
        Raises:
            TelemetryStorageError: If restore fails
        """
        try:
            # Try primary backend first
            if self._primary_backend:
                try:
                    return await self._primary_backend.restore_data(backup_path)
                except Exception as e:
                    self.logger.warning(
                        "Primary storage backend failed for restore, trying fallbacks",
                        backend=type(self._primary_backend).__name__,
                        error=str(e)
                    )
            
            # Try fallback backends
            for backend in self._fallback_backends:
                try:
                    restored = await backend.restore_data(backup_path)
                    if restored > 0:
                        return restored
                except Exception as e:
                    self.logger.warning(
                        "Fallback storage backend failed for restore",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    continue
            
            return 0
            
        except Exception as e:
            self.logger.error(
                "Failed to restore data",
                backup_path=backup_path,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to restore data: {e}",
                error_code="TEL-215"
            )
    
    async def optimize_storage(self) -> Dict[str, Any]:
        """
        Optimize storage performance.
        
        Returns:
            Optimization results
        """
        try:
            results = {}
            
            # Optimize primary backend
            if self._primary_backend:
                try:
                    results["primary"] = await self._primary_backend.optimize_storage()
                except Exception as e:
                    self.logger.warning(
                        "Failed to optimize primary backend",
                        error=str(e)
                    )
                    results["primary"] = {"error": str(e)}
            
            # Optimize fallback backends
            results["fallbacks"] = []
            for backend in self._fallback_backends:
                try:
                    result = await backend.optimize_storage()
                    results["fallbacks"].append({
                        "backend": type(backend).__name__,
                        "result": result
                    })
                except Exception as e:
                    self.logger.warning(
                        "Failed to optimize fallback backend",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    results["fallbacks"].append({
                        "backend": type(backend).__name__,
                        "error": str(e)
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to optimize storage",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to optimize storage: {e}",
                error_code="TEL-216"
            )
    
    async def validate_storage_integrity(self) -> Dict[str, Any]:
        """
        Validate storage data integrity.
        
        Returns:
            Integrity validation results
        """
        try:
            results = {}
            
            # Validate primary backend
            if self._primary_backend:
                try:
                    results["primary"] = await self._primary_backend.validate_storage_integrity()
                except Exception as e:
                    self.logger.warning(
                        "Failed to validate primary backend integrity",
                        error=str(e)
                    )
                    results["primary"] = {"error": str(e)}
            
            # Validate fallback backends
            results["fallbacks"] = []
            for backend in self._fallback_backends:
                try:
                    result = await backend.validate_storage_integrity()
                    results["fallbacks"].append({
                        "backend": type(backend).__name__,
                        "result": result
                    })
                except Exception as e:
                    self.logger.warning(
                        "Failed to validate fallback backend integrity",
                        backend=type(backend).__name__,
                        error=str(e)
                    )
                    results["fallbacks"].append({
                        "backend": type(backend).__name__,
                        "error": str(e)
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to validate storage integrity",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to validate storage integrity: {e}",
                error_code="TEL-217"
            )
    
    # Private methods
    
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
