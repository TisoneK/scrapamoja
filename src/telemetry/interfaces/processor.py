"""
Telemetry Processor Interface

Abstract interface for processing and analyzing telemetry data
following the contract specification.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models import TelemetryEvent


class ITelemetryProcessor(ABC):
    """
    Interface for processing and analyzing telemetry data.
    
    This interface defines the contract for telemetry data processing,
    including batch processing, aggregation, and analysis.
    """
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Processing statistics including events processed, errors, etc.
        """
        pass
    
    @abstractmethod
    async def is_processing_enabled(self) -> bool:
        """
        Check if processing is enabled.
        
        Returns:
            True if processing is enabled
        """
        pass
    
    @abstractmethod
    async def enable_processing(self) -> None:
        """
        Enable processing.
        """
        pass
    
    @abstractmethod
    async def disable_processing(self) -> None:
        """
        Disable processing.
        """
        pass
    
    @abstractmethod
    async def get_processor_health(self) -> Dict[str, Any]:
        """
        Get processor health status.
        
        Returns:
            Health status information
        """
        pass
    
    @abstractmethod
    async def reset_processor_statistics(self) -> None:
        """
        Reset processor statistics.
        """
        pass
    
    @abstractmethod
    async def configure_processor(self, config: Dict[str, Any]) -> None:
        """
        Configure processor settings.
        
        Args:
            config: Processor configuration
        """
        pass
