"""
JSON Storage Backend

JSON file-based storage backend for telemetry data with compression,
indexing, and efficient querying capabilities.
"""

import json
import gzip
import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles
from collections import defaultdict

from ..interfaces import ITelemetryStorage
from ..models import TelemetryEvent
from ..configuration.telemetry_config import TelemetryConfiguration
from ..exceptions import TelemetryStorageError
from ..configuration.logging import get_logger


class JSONStorage(ITelemetryStorage):
    """
    JSON file-based storage backend for telemetry data.
    
    Provides efficient storage with compression, indexing, and
    querying capabilities for development and small-scale deployments.
    """
    
    def __init__(self, config: TelemetryConfiguration):
        """
        Initialize JSON storage backend.
        
        Args:
            config: Telemetry configuration
        """
        self.config = config
        self.logger = get_logger("json_storage")
        
        # Storage paths
        self.storage_path = Path(config.get_storage_path())
        self.events_dir = self.storage_path / "events"
        self.indexes_dir = self.storage_path / "indexes"
        self.backups_dir = self.storage_path / "backups"
        
        # Storage options
        self.compression_enabled = config.should_compress_storage()
        self.file_extension = ".json.gz" if self.compression_enabled else ".json"
        
        # Index caches
        self._selector_index: Dict[str, List[str]] = defaultdict(list)
        self._correlation_index: Dict[str, List[str]] = defaultdict(list)
        self._date_index: Dict[str, List[str]] = defaultdict(list)
        self._index_loaded = False
        
        # Initialize storage
        self._initialize_storage()
    
    def _initialize_storage(self) -> None:
        """Initialize storage directories and structure."""
        try:
            # Create directories
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self.events_dir.mkdir(parents=True, exist_ok=True)
            self.indexes_dir.mkdir(parents=True, exist_ok=True)
            self.backups_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(
                "JSON storage initialized",
                storage_path=str(self.storage_path),
                compression=self.compression_enabled
            )
            
        except Exception as e:
            raise TelemetryStorageError(
                f"Failed to initialize JSON storage: {e}",
                error_code="TEL-218"
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
            # Ensure index is loaded
            await self._ensure_index_loaded()
            
            # Generate file path based on date
            date_str = event.timestamp.strftime("%Y-%m-%d")
            file_path = self.events_dir / f"{date_str}{self.file_extension}"
            
            # Load existing events for the day
            events = await self._load_events_file(file_path)
            
            # Add new event
            events.append(event.dict())
            
            # Sort events by timestamp
            events.sort(key=lambda x: x["timestamp"])
            
            # Save events
            await self._save_events_file(file_path, events)
            
            # Update indexes
            await self._update_indexes(event, file_path.name)
            
            self.logger.debug(
                "Event stored",
                event_id=event.event_id,
                file_path=str(file_path)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to store event",
                event_id=getattr(event, 'event_id', 'unknown'),
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to store event: {e}",
                error_code="TEL-219"
            )
    
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
            # Ensure index is loaded
            await self._ensure_index_loaded()
            
            # Group events by date
            events_by_date = defaultdict(list)
            for event in events:
                date_str = event.timestamp.strftime("%Y-%m-%d")
                events_by_date[date_str].append(event)
            
            stored_count = 0
            
            # Store each date group
            for date_str, date_events in events_by_date.items():
                file_path = self.events_dir / f"{date_str}{self.file_extension}"
                
                # Load existing events
                existing_events = await self._load_events_file(file_path)
                
                # Add new events
                for event in date_events:
                    existing_events.append(event.dict())
                
                # Sort events by timestamp
                existing_events.sort(key=lambda x: x["timestamp"])
                
                # Save events
                await self._save_events_file(file_path, existing_events)
                
                # Update indexes
                for event in date_events:
                    await self._update_indexes(event, file_path.name)
                
                stored_count += len(date_events)
            
            self.logger.info(
                "Batch stored events",
                total_events=len(events),
                stored_count=stored_count,
                dates_processed=len(events_by_date)
            )
            
            return stored_count
            
        except Exception as e:
            self.logger.error(
                "Failed to store event batch",
                batch_size=len(events),
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to store event batch: {e}",
                error_code="TEL-220"
            )
    
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
            # Search through all event files
            for file_path in self._get_event_files():
                events = await self._load_events_file(file_path)
                
                for event_data in events:
                    if event_data.get("event_id") == event_id:
                        return TelemetryEvent(**event_data)
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve event",
                event_id=event_id,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve event {event_id}: {e}",
                error_code="TEL-221"
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
            # Ensure index is loaded
            await self._ensure_index_loaded()
            
            # Get relevant files from index
            relevant_files = self._selector_index.get(selector_name, [])
            
            events = []
            
            # Search through relevant files
            for file_name in relevant_files:
                file_path = self.events_dir / file_name
                
                if not file_path.exists():
                    continue
                
                file_events = await self._load_events_file(file_path)
                
                for event_data in file_events:
                    if event_data.get("selector_name") == selector_name:
                        # Filter by time range
                        if start_time or end_time:
                            event_time = datetime.fromisoformat(
                                event_data["timestamp"].replace("Z", "+00:00")
                            )
                            
                            if start_time and event_time < start_time:
                                continue
                            if end_time and event_time > end_time:
                                continue
                        
                        events.append(TelemetryEvent(**event_data))
                        
                        # Check limit
                        if limit and len(events) >= limit:
                            break
                
                if limit and len(events) >= limit:
                    break
            
            # Sort by timestamp
            events.sort(key=lambda x: x.timestamp)
            
            return events[:limit] if limit else events
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve events by selector",
                selector_name=selector_name,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve events for selector {selector_name}: {e}",
                error_code="TEL-222"
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
            # Ensure index is loaded
            await self._ensure_index_loaded()
            
            # Get relevant files from index
            relevant_files = self._correlation_index.get(correlation_id, [])
            
            events = []
            
            # Search through relevant files
            for file_name in relevant_files:
                file_path = self.events_dir / file_name
                
                if not file_path.exists():
                    continue
                
                file_events = await self._load_events_file(file_path)
                
                for event_data in file_events:
                    if event_data.get("correlation_id") == correlation_id:
                        events.append(TelemetryEvent(**event_data))
                        
                        # Check limit
                        if limit and len(events) >= limit:
                            break
                
                if limit and len(events) >= limit:
                    break
            
            # Sort by timestamp
            events.sort(key=lambda x: x.timestamp)
            
            return events[:limit] if limit else events
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve events by correlation",
                correlation_id=correlation_id,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve events for correlation {correlation_id}: {e}",
                error_code="TEL-223"
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
            # Get date range for files to check
            date_range = self._get_date_range(start_time, end_time)
            
            events = []
            
            # Search through date range
            for date_str in date_range:
                file_path = self.events_dir / f"{date_str}{self.file_extension}"
                
                if not file_path.exists():
                    continue
                
                file_events = await self._load_events_file(file_path)
                
                for event_data in file_events:
                    # Parse event time
                    event_time = datetime.fromisoformat(
                        event_data["timestamp"].replace("Z", "+00:00")
                    )
                    
                    # Check time range
                    if event_time < start_time or event_time > end_time:
                        continue
                    
                    # Apply filters
                    if selector_name and event_data.get("selector_name") != selector_name:
                        continue
                    
                    if operation_type and event_data.get("operation_type") != operation_type:
                        continue
                    
                    events.append(TelemetryEvent(**event_data))
                    
                    # Check limit
                    if limit and len(events) >= limit:
                        break
                
                if limit and len(events) >= limit:
                    break
            
            # Sort by timestamp
            events.sort(key=lambda x: x.timestamp)
            
            return events[:limit] if limit else events
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve events by time range",
                start_time=start_time,
                end_time=end_time,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve events for time range: {e}",
                error_code="TEL-224"
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
            # Get date range
            if start_time and end_time:
                date_range = self._get_date_range(start_time, end_time)
            else:
                date_range = self._get_all_dates()
            
            events = []
            
            # Search through date range
            for date_str in date_range:
                file_path = self.events_dir / f"{date_str}{self.file_extension}"
                
                if not file_path.exists():
                    continue
                
                file_events = await self._load_events_file(file_path)
                
                for event_data in file_events:
                    # Check time range
                    if start_time or end_time:
                        event_time = datetime.fromisoformat(
                            event_data["timestamp"].replace("Z", "+00:00")
                        )
                        
                        if start_time and event_time < start_time:
                            continue
                        if end_time and event_time > end_time:
                            continue
                    
                    # Check if event failed
                    if not event_data.get("quality_metrics", {}).get("success", True):
                        events.append(TelemetryEvent(**event_data))
                        
                        # Check limit
                        if limit and len(events) >= limit:
                            break
                
                if limit and len(events) >= limit:
                    break
            
            # Sort by timestamp
            events.sort(key=lambda x: x.timestamp)
            
            return events[:limit] if limit else events
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve failed events",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve failed events: {e}",
                error_code="TEL-225"
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
            # Get events for the time range
            events = await self.get_events_by_time_range(
                start_time or datetime.min,
                end_time or datetime.utcnow(),
                selector_name
            )
            
            if not events:
                return {}
            
            # Extract performance metrics
            metrics = []
            for event in events:
                if event.performance_metrics:
                    metrics.append(event.performance_metrics)
            
            if not metrics:
                return {}
            
            # Aggregate metrics
            result = {}
            
            for metric_name in ["resolution_time_ms", "strategy_execution_time_ms", "total_duration_ms"]:
                values = [m.get(metric_name, 0) for m in metrics if metric_name in m]
                
                if values:
                    if aggregation == "avg":
                        result[metric_name] = sum(values) / len(values)
                    elif aggregation == "min":
                        result[metric_name] = min(values)
                    elif aggregation == "max":
                        result[metric_name] = max(values)
                    elif aggregation == "sum":
                        result[metric_name] = sum(values)
                    elif aggregation == "count":
                        result[metric_name] = len(values)
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve performance metrics",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve performance metrics: {e}",
                error_code="TEL-226"
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
            # Get events for the time range
            events = await self.get_events_by_time_range(
                start_time or datetime.min,
                end_time or datetime.utcnow(),
                selector_name
            )
            
            if not events:
                return {}
            
            # Extract quality metrics
            metrics = []
            for event in events:
                if event.quality_metrics:
                    metrics.append(event.quality_metrics)
            
            if not metrics:
                return {}
            
            # Calculate summary
            total_events = len(metrics)
            successful_events = sum(1 for m in metrics if m.get("success", False))
            failed_events = total_events - successful_events
            
            confidence_scores = [m.get("confidence_score", 0) for m in metrics if "confidence_score" in m]
            
            result = {
                "total_events": total_events,
                "successful_events": successful_events,
                "failed_events": failed_events,
                "success_rate": successful_events / total_events if total_events > 0 else 0,
            }
            
            if confidence_scores:
                result.update({
                    "avg_confidence_score": sum(confidence_scores) / len(confidence_scores),
                    "min_confidence_score": min(confidence_scores),
                    "max_confidence_score": max(confidence_scores)
                })
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve quality metrics",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to retrieve quality metrics: {e}",
                error_code="TEL-227"
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
            # Search through all event files
            for file_path in self._get_event_files():
                events = await self._load_events_file(file_path)
                
                # Find and remove event
                updated_events = []
                event_found = False
                
                for event_data in events:
                    if event_data.get("event_id") == event_id:
                        event_found = True
                        continue
                    updated_events.append(event_data)
                
                if event_found:
                    # Save updated events
                    await self._save_events_file(file_path, updated_events)
                    
                    # Update indexes (rebuild for simplicity)
                    await self._rebuild_indexes()
                    
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(
                "Failed to delete event",
                event_id=event_id,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to delete event {event_id}: {e}",
                error_code="TEL-228"
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
            deleted_count = 0
            
            # Search through all event files
            for file_path in self._get_event_files():
                events = await self._load_events_file(file_path)
                
                # Filter events
                updated_events = []
                file_deleted = 0
                
                for event_data in events:
                    should_delete = (
                        event_data.get("selector_name") == selector_name and
                        (not before_time or self._event_before_time(event_data, before_time))
                    )
                    
                    if should_delete:
                        file_deleted += 1
                    else:
                        updated_events.append(event_data)
                
                if file_deleted > 0:
                    # Save updated events
                    await self._save_events_file(file_path, updated_events)
                    deleted_count += file_deleted
            
            if deleted_count > 0:
                # Rebuild indexes
                await self._rebuild_indexes()
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(
                "Failed to delete events by selector",
                selector_name=selector_name,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to delete events for selector {selector_name}: {e}",
                error_code="TEL-229"
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
            deleted_count = 0
            
            # Get date range
            date_range = self._get_date_range(start_time, end_time)
            
            # Search through date range
            for date_str in date_range:
                file_path = self.events_dir / f"{date_str}{self.file_extension}"
                
                if not file_path.exists():
                    continue
                
                events = await self._load_events_file(file_path)
                
                # Filter events
                updated_events = []
                file_deleted = 0
                
                for event_data in events:
                    event_time = datetime.fromisoformat(
                        event_data["timestamp"].replace("Z", "+00:00")
                    )
                    
                    if start_time <= event_time <= end_time:
                        file_deleted += 1
                    else:
                        updated_events.append(event_data)
                
                if file_deleted > 0:
                    # Save updated events
                    await self._save_events_file(file_path, updated_events)
                    deleted_count += file_deleted
            
            if deleted_count > 0:
                # Rebuild indexes
                await self._rebuild_indexes()
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(
                "Failed to delete events by time range",
                start_time=start_time,
                end_time=end_time,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to delete events for time range: {e}",
                error_code="TEL-230"
            )
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Storage statistics including total events, size, etc.
        """
        try:
            total_events = 0
            total_size = 0
            file_count = 0
            
            # Count events and files
            for file_path in self._get_event_files():
                file_size = file_path.stat().st_size
                total_size += file_size
                file_count += 1
                
                # Count events in file
                events = await self._load_events_file(file_path)
                total_events += len(events)
            
            return {
                "total_events": total_events,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "file_count": file_count,
                "compression_enabled": self.compression_enabled,
                "storage_path": str(self.storage_path),
                "index_loaded": self._index_loaded
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get storage statistics",
                error=str(e)
            )
            return {}
    
    async def is_available(self) -> bool:
        """
        Check if storage is available.
        
        Returns:
            True if storage is available
        """
        try:
            # Check if storage path is accessible
            return self.storage_path.exists() and os.access(self.storage_path, os.W_OK)
        except Exception:
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
            "cleanup_enabled": True
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
            
            # Delete old events
            deleted_count = await self.delete_events_by_time_range(
                datetime.min,
                cutoff_time
            )
            
            # Clean up empty files
            await self._cleanup_empty_files()
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(
                "Failed to apply retention policy",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to apply retention policy: {e}",
                error_code="TEL-231"
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
            import shutil
            
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy storage directory
            shutil.copytree(self.storage_path, backup_dir / "storage", dirs_exist_ok=True)
            
            self.logger.info(
                "Data backup completed",
                backup_path=backup_path
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to backup data",
                backup_path=backup_path,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to backup data: {e}",
                error_code="TEL-232"
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
            import shutil
            
            backup_dir = Path(backup_path)
            backup_storage = backup_dir / "storage"
            
            if not backup_storage.exists():
                raise TelemetryStorageError(
                    "Backup storage directory not found",
                    error_code="TEL-233"
                )
            
            # Count events before restore
            before_stats = await self.get_storage_statistics()
            
            # Restore storage directory
            shutil.copytree(backup_storage, self.storage_path, dirs_exist_ok=True)
            
            # Count events after restore
            after_stats = await self.get_storage_statistics()
            
            restored_count = after_stats.get("total_events", 0) - before_stats.get("total_events", 0)
            
            # Rebuild indexes
            await self._rebuild_indexes()
            
            self.logger.info(
                "Data restore completed",
                backup_path=backup_path,
                events_restored=restored_count
            )
            
            return restored_count
            
        except Exception as e:
            self.logger.error(
                "Failed to restore data",
                backup_path=backup_path,
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to restore data: {e}",
                error_code="TEL-234"
            )
    
    async def optimize_storage(self) -> Dict[str, Any]:
        """
        Optimize storage performance.
        
        Returns:
            Optimization results
        """
        try:
            results = {
                "files_optimized": 0,
                "space_saved": 0
            }
            
            # Rebuild indexes
            await self._rebuild_indexes()
            
            # Clean up empty files
            empty_files_removed = await self._cleanup_empty_files()
            results["empty_files_removed"] = empty_files_removed
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to optimize storage",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to optimize storage: {e}",
                error_code="TEL-235"
            )
    
    async def validate_storage_integrity(self) -> Dict[str, Any]:
        """
        Validate storage data integrity.
        
        Returns:
            Integrity validation results
        """
        try:
            results = {
                "files_validated": 0,
                "events_validated": 0,
                "invalid_events": 0,
                "errors": []
            }
            
            # Validate all event files
            for file_path in self._get_event_files():
                try:
                    events = await self._load_events_file(file_path)
                    results["files_validated"] += 1
                    
                    for event_data in events:
                        results["events_validated"] += 1
                        
                        try:
                            # Validate event structure
                            TelemetryEvent(**event_data)
                        except Exception as e:
                            results["invalid_events"] += 1
                            results["errors"].append({
                                "file": str(file_path),
                                "event_id": event_data.get("event_id", "unknown"),
                                "error": str(e)
                            })
                
                except Exception as e:
                    results["errors"].append({
                        "file": str(file_path),
                        "error": f"File validation failed: {e}"
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to validate storage integrity",
                error=str(e)
            )
            raise TelemetryStorageError(
                f"Failed to validate storage integrity: {e}",
                error_code="TEL-236"
            )
    
    # Private methods
    
    async def _load_events_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load events from a file."""
        if not file_path.exists():
            return []
        
        try:
            if self.compression_enabled:
                async with aiofiles.open(file_path, 'rb') as f:
                    content = await f.read()
                    decompressed = gzip.decompress(content).decode('utf-8')
                    return json.loads(decompressed)
            else:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    return json.loads(content)
        
        except Exception as e:
            self.logger.warning(
                "Failed to load events file",
                file_path=str(file_path),
                error=str(e)
            )
            return []
    
    async def _save_events_file(self, file_path: Path, events: List[Dict[str, Any]]) -> None:
        """Save events to a file."""
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize events
            content = json.dumps(events, indent=2, default=str)
            
            # Write file
            if self.compression_enabled:
                compressed = gzip.compress(content.encode('utf-8'))
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(compressed)
            else:
                async with aiofiles.open(file_path, 'w') as f:
                    await f.write(content)
        
        except Exception as e:
            raise TelemetryStorageError(
                f"Failed to save events file {file_path}: {e}",
                error_code="TEL-237"
            )
    
    async def _ensure_index_loaded(self) -> None:
        """Ensure indexes are loaded."""
        if not self._index_loaded:
            await self._load_indexes()
    
    async def _load_indexes(self) -> None:
        """Load indexes from disk."""
        try:
            index_file = self.indexes_dir / f"indexes{self.file_extension}"
            
            if index_file.exists():
                index_data = await self._load_events_file(index_file)
                
                self._selector_index = defaultdict(list, index_data.get("selector", {}))
                self._correlation_index = defaultdict(list, index_data.get("correlation", {}))
                self._date_index = defaultdict(list, index_data.get("date", {}))
            else:
                # Build indexes from scratch
                await self._rebuild_indexes()
            
            self._index_loaded = True
            
        except Exception as e:
            self.logger.warning(
                "Failed to load indexes, rebuilding",
                error=str(e)
            )
            await self._rebuild_indexes()
    
    async def _save_indexes(self) -> None:
        """Save indexes to disk."""
        try:
            index_file = self.indexes_dir / f"indexes{self.file_extension}"
            
            index_data = {
                "selector": dict(self._selector_index),
                "correlation": dict(self._correlation_index),
                "date": dict(self._date_index)
            }
            
            await self._save_events_file(index_file, [index_data])
            
        except Exception as e:
            self.logger.warning(
                "Failed to save indexes",
                error=str(e)
            )
    
    async def _update_indexes(self, event: TelemetryEvent, file_name: str) -> None:
        """Update indexes with new event."""
        # Update selector index
        if event.selector_name:
            if file_name not in self._selector_index[event.selector_name]:
                self._selector_index[event.selector_name].append(file_name)
        
        # Update correlation index
        if event.correlation_id:
            if file_name not in self._correlation_index[event.correlation_id]:
                self._correlation_index[event.correlation_id].append(file_name)
        
        # Update date index
        date_str = event.timestamp.strftime("%Y-%m-%d")
        if file_name not in self._date_index[date_str]:
            self._date_index[date_str].append(file_name)
    
    async def _rebuild_indexes(self) -> None:
        """Rebuild indexes from all event files."""
        self._selector_index.clear()
        self._correlation_index.clear()
        self._date_index.clear()
        
        for file_path in self._get_event_files():
            events = await self._load_events_file(file_path)
            
            for event_data in events:
                try:
                    event = TelemetryEvent(**event_data)
                    await self._update_indexes(event, file_path.name)
                except Exception:
                    continue  # Skip invalid events
        
        await self._save_indexes()
        self._index_loaded = True
    
    def _get_event_files(self) -> List[Path]:
        """Get all event files."""
        return list(self.events_dir.glob(f"*{self.file_extension}"))
    
    def _get_date_range(self, start_time: datetime, end_time: datetime) -> List[str]:
        """Get date strings for a time range."""
        date_range = []
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            date_range.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        return date_range
    
    def _get_all_dates(self) -> List[str]:
        """Get all available dates from files."""
        dates = []
        
        for file_path in self._get_event_files():
            # Extract date from filename
            date_str = file_path.stem
            if self.compression_enabled and date_str.endswith(".gz"):
                date_str = date_str[:-3]
            
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                dates.append(date_str)
            except ValueError:
                continue
        
        return sorted(dates)
    
    def _event_before_time(self, event_data: Dict[str, Any], before_time: datetime) -> bool:
        """Check if event is before specified time."""
        try:
            event_time = datetime.fromisoformat(
                event_data["timestamp"].replace("Z", "+00:00")
            )
            return event_time < before_time
        except Exception:
            return False
    
    async def _cleanup_empty_files(self) -> int:
        """Remove empty event files."""
        removed_count = 0
        
        for file_path in self._get_event_files():
            events = await self._load_events_file(file_path)
            
            if not events:
                file_path.unlink()
                removed_count += 1
        
        return removed_count
