"""
Alert Engine Interface

Abstract interface for monitoring telemetry data and generating alerts
following the contract specification.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from ..models import TelemetryEvent


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Alert types."""
    PERFORMANCE = "performance"
    QUALITY = "quality"
    HEALTH = "health"
    USAGE = "usage"


class Alert:
    """Alert data structure."""
    
    def __init__(
        self,
        alert_id: str,
        alert_type: AlertType,
        severity: AlertSeverity,
        selector_name: str,
        threshold_name: str,
        threshold_value: float,
        actual_value: float,
        timestamp: datetime,
        description: str,
        correlation_id: Optional[str] = None,
        acknowledged: bool = False,
        resolved: bool = False
    ):
        self.alert_id = alert_id
        self.alert_type = alert_type
        self.severity = severity
        self.selector_name = selector_name
        self.threshold_name = threshold_name
        self.threshold_value = threshold_value
        self.actual_value = actual_value
        self.timestamp = timestamp
        self.description = description
        self.correlation_id = correlation_id
        self.acknowledged = acknowledged
        self.resolved = resolved


class IAlertEngine(ABC):
    """
    Interface for monitoring telemetry data and generating alerts.
    
    This interface defines the contract for alert generation,
    threshold monitoring, and alert management.
    """
    
    @abstractmethod
    async def evaluate_thresholds(self, event: TelemetryEvent) -> List[Alert]:
        """
        Evaluate thresholds against a telemetry event.
        
        Args:
            event: TelemetryEvent to evaluate
            
        Returns:
            List of generated alerts
            
        Raises:
            TelemetryAlertingError: If evaluation fails
        """
        pass
    
    @abstractmethod
    async def generate_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        selector_name: str,
        threshold_name: str,
        threshold_value: float,
        actual_value: float,
        description: str,
        correlation_id: Optional[str] = None
    ) -> Alert:
        """
        Generate a new alert.
        
        Args:
            alert_type: Type of alert
            severity: Alert severity
            selector_name: Name of selector
            threshold_name: Name of threshold
            threshold_value: Threshold value
            actual_value: Actual value that triggered alert
            description: Alert description
            correlation_id: Optional correlation ID
            
        Returns:
            Generated Alert
            
        Raises:
            TelemetryAlertingError: If alert generation fails
        """
        pass
    
    @abstractmethod
    async def store_alert(self, alert: Alert) -> bool:
        """
        Store an alert.
        
        Args:
            alert: Alert to store
            
        Returns:
            True if successfully stored, False otherwise
            
        Raises:
            TelemetryAlertingError: If storage fails
        """
        pass
    
    @abstractmethod
    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """
        Retrieve an alert by ID.
        
        Args:
            alert_id: Unique alert identifier
            
        Returns:
            Alert if found, None otherwise
            
        Raises:
            TelemetryAlertingError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def get_active_alerts(
        self,
        alert_type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None,
        selector_name: Optional[str] = None
    ) -> List[Alert]:
        """
        Get active (unresolved) alerts.
        
        Args:
            alert_type: Optional alert type filter
            severity: Optional severity filter
            selector_name: Optional selector filter
            
        Returns:
            List of active alerts
            
        Raises:
            TelemetryAlertingError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def get_alerts_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        alert_type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """
        Get alerts within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            alert_type: Optional alert type filter
            severity: Optional severity filter
            
        Returns:
            List of alerts
            
        Raises:
            TelemetryAlertingError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Unique alert identifier
            
        Returns:
            True if successfully acknowledged, False otherwise
            
        Raises:
            TelemetryAlertingError: If acknowledgment fails
        """
        pass
    
    @abstractmethod
    async def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: Unique alert identifier
            
        Returns:
            True if successfully resolved, False otherwise
            
        Raises:
            TelemetryAlertingError: If resolution fails
        """
        pass
    
    @abstractmethod
    async def set_threshold(
        self,
        threshold_name: str,
        threshold_value: float,
        alert_type: AlertType,
        severity: AlertSeverity,
        description: str,
        selector_name: Optional[str] = None
    ) -> bool:
        """
        Set a monitoring threshold.
        
        Args:
            threshold_name: Name of threshold
            threshold_value: Threshold value
            alert_type: Type of alert for this threshold
            severity: Alert severity when threshold is exceeded
            description: Threshold description
            selector_name: Optional selector-specific threshold
            
        Returns:
            True if successfully set, False otherwise
            
        Raises:
            TelemetryAlertingError: If threshold setting fails
        """
        pass
    
    @abstractmethod
    async def get_threshold(
        self,
        threshold_name: str,
        selector_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a threshold configuration.
        
        Args:
            threshold_name: Name of threshold
            selector_name: Optional selector name
            
        Returns:
            Threshold configuration or None if not found
            
        Raises:
            TelemetryAlertingError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def get_all_thresholds(self) -> List[Dict[str, Any]]:
        """
        Get all threshold configurations.
        
        Returns:
            List of threshold configurations
            
        Raises:
            TelemetryAlertingError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def remove_threshold(
        self,
        threshold_name: str,
        selector_name: Optional[str] = None
    ) -> bool:
        """
        Remove a threshold configuration.
        
        Args:
            threshold_name: Name of threshold
            selector_name: Optional selector name
            
        Returns:
            True if successfully removed, False otherwise
            
        Raises:
            TelemetryAlertingError: If removal fails
        """
        pass
    
    @abstractmethod
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """
        Get alerting statistics.
        
        Returns:
            Alert statistics including counts by type, severity, etc.
        """
        pass
    
    @abstractmethod
    async def is_alerting_enabled(self) -> bool:
        """
        Check if alerting is enabled.
        
        Returns:
            True if alerting is enabled
        """
        pass
    
    @abstractmethod
    async def enable_alerting(self) -> None:
        """
        Enable alerting.
        """
        pass
    
    @abstractmethod
    async def disable_alerting(self) -> None:
        """
        Disable alerting.
        """
        pass
    
    @abstractmethod
    async def get_alert_engine_health(self) -> Dict[str, Any]:
        """
        Get alert engine health status.
        
        Returns:
            Health status information
        """
        pass
    
    @abstractmethod
    async def configure_alert_engine(self, config: Dict[str, Any]) -> None:
        """
        Configure alert engine settings.
        
        Args:
            config: Alert engine configuration
        """
        pass
    
    @abstractmethod
    async def test_threshold(
        self,
        threshold_name: str,
        test_value: float,
        selector_name: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Test a threshold with a test value.
        
        Args:
            threshold_name: Name of threshold to test
            test_value: Test value to evaluate
            selector_name: Optional selector name
            
        Returns:
            Test alert if threshold would be triggered, None otherwise
            
        Raises:
            TelemetryAlertingError: If test fails
        """
        pass
