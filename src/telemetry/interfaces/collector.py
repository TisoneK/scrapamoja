"""
Telemetry Collector Interface

Abstract interface for collecting telemetry data from selector operations
following the contract specification.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models import TelemetryEvent


class ITelemetryCollector(ABC):
    """
    Interface for collecting telemetry data from selector operations.
    
    This interface defines the contract for telemetry data collection,
    including event recording, metrics gathering, and data validation.
    """
    
    @abstractmethod
    async def collect_event(
        self,
        selector_name: str,
        operation_type: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> TelemetryEvent:
        """
        Collect a telemetry event from a selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            operation_type: Type of operation (resolution, validation, execution, cleanup)
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional event data
            
        Returns:
            Collected TelemetryEvent
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        pass
    
    @abstractmethod
    async def record_event(self, event: TelemetryEvent) -> bool:
        """
        Record a telemetry event for storage.
        
        Args:
            event: TelemetryEvent to record
            
        Returns:
            True if successfully recorded, False otherwise
            
        Raises:
            TelemetryCollectionError: If recording fails
        """
        pass
    
    @abstractmethod
    async def collect_performance_metrics(
        self,
        selector_name: str,
        resolution_time_ms: float,
        strategy_execution_time_ms: float,
        total_duration_ms: float,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect performance metrics for a selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            resolution_time_ms: Time taken for selector resolution
            strategy_execution_time_ms: Time for strategy execution
            total_duration_ms: Total operation duration
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional performance data
            
        Returns:
            Performance metrics dictionary
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        pass
    
    @abstractmethod
    async def collect_quality_metrics(
        self,
        selector_name: str,
        confidence_score: float,
        success: bool,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect quality metrics for a selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            confidence_score: Confidence score (0.0-1.0)
            success: Whether the operation succeeded
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional quality data
            
        Returns:
            Quality metrics dictionary
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        pass
    
    @abstractmethod
    async def collect_strategy_metrics(
        self,
        selector_name: str,
        primary_strategy: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect strategy metrics for a selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            primary_strategy: Primary strategy used
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional strategy data
            
        Returns:
            Strategy metrics dictionary
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        pass
    
    @abstractmethod
    async def collect_error_data(
        self,
        selector_name: str,
        error_type: str,
        error_message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect error data for a failed selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            error_type: Type of error
            error_message: Error message
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional error data
            
        Returns:
            Error data dictionary
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        pass
    
    @abstractmethod
    async def collect_context_data(
        self,
        selector_name: str,
        browser_session_id: str,
        tab_context_id: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect context data for a selector operation.
        
        Args:
            selector_name: Name/identifier of the selector
            browser_session_id: Browser session identifier
            tab_context_id: Tab context identifier
            correlation_id: Correlation ID for operation tracking
            **kwargs: Additional context data
            
        Returns:
            Context data dictionary
            
        Raises:
            TelemetryCollectionError: If collection fails
        """
        pass
    
    @abstractmethod
    async def get_buffer_status(self) -> Dict[str, Any]:
        """
        Get current buffer status.
        
        Returns:
            Buffer status information including size, usage, and health
        """
        pass
    
    @abstractmethod
    async def flush_buffer(self) -> int:
        """
        Flush the event buffer to storage.
        
        Returns:
            Number of events flushed
            
        Raises:
            TelemetryCollectionError: If flush fails
        """
        pass
    
    @abstractmethod
    async def is_enabled(self) -> bool:
        """
        Check if telemetry collection is enabled.
        
        Returns:
            True if collection is enabled
        """
        pass
    
    @abstractmethod
    async def enable_collection(self) -> None:
        """
        Enable telemetry collection.
        """
        pass
    
    @abstractmethod
    async def disable_collection(self) -> None:
        """
        Disable telemetry collection.
        """
        pass
    
    @abstractmethod
    async def get_collection_statistics(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Collection statistics including events collected, errors, etc.
        """
        pass
    
    @abstractmethod
    async def validate_event(self, event: TelemetryEvent) -> List[str]:
        """
        Validate a telemetry event.
        
        Args:
            event: TelemetryEvent to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        pass
    
    @abstractmethod
    async def start_collection_session(self, session_id: str) -> None:
        """
        Start a collection session.
        
        Args:
            session_id: Unique session identifier
        """
        pass
    
    @abstractmethod
    async def end_collection_session(self, session_id: str) -> Dict[str, Any]:
        """
        End a collection session and get session statistics.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session statistics
        """
        pass
