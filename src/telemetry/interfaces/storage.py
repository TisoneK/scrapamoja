"""
Telemetry Storage Interface

Abstract interface for storing and retrieving telemetry data
following the contract specification.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models import TelemetryEvent


class ITelemetryStorage(ABC):
    """
    Interface for storing and retrieving telemetry data.
    
    This interface defines the contract for telemetry data storage,
    including event persistence, querying, and lifecycle management.
    """
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Storage statistics including total events, size, etc.
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if storage is available.
        
        Returns:
            True if storage is available
        """
        pass
    
    @abstractmethod
    async def get_retention_info(self) -> Dict[str, Any]:
        """
        Get retention information.
        
        Returns:
            Retention policy information
        """
        pass
    
    @abstractmethod
    async def apply_retention_policy(self) -> int:
        """
        Apply retention policy to clean up old data.
        
        Returns:
            Number of events cleaned up
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def optimize_storage(self) -> Dict[str, Any]:
        """
        Optimize storage performance.
        
        Returns:
            Optimization results
        """
        pass
    
    @abstractmethod
    async def validate_storage_integrity(self) -> Dict[str, Any]:
        """
        Validate storage data integrity.
        
        Returns:
            Integrity validation results
        """
        pass
