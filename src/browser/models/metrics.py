"""
Resource Metrics Entity

This module defines the ResourceMetrics entity for browser resource monitoring.
"""

import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import structlog

from .enums import AlertStatus


@dataclass
class ResourceMetrics:
    """Real-time monitoring data for browser resource consumption."""
    session_id: str
    context_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    disk_usage_mb: float = 0.0
    network_requests_count: int = 0
    open_tabs_count: int = 0
    process_handles_count: int = 0
    alert_status: AlertStatus = AlertStatus.NORMAL
    
    # Additional metrics for detailed monitoring
    private_memory_mb: float = 0.0
    shared_memory_mb: float = 0.0
    virtual_memory_mb: float = 0.0
    gpu_memory_mb: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_received: int = 0
    javascript_heap_size_mb: float = 0.0
    javascript_heap_used_mb: float = 0.0
    
    def __post_init__(self):
        """Validate metrics after initialization."""
        self.logger = structlog.get_logger("browser.metrics")
        
        # Validate numeric values
        if self.memory_usage_mb < 0:
            self.logger.warning(
                "Invalid memory usage detected",
                session_id=self.session_id,
                memory_usage=self.memory_usage_mb
            )
            self.memory_usage_mb = 0.0
            
        if not 0 <= self.cpu_usage_percent <= 100:
            self.logger.warning(
                "Invalid CPU usage detected",
                session_id=self.session_id,
                cpu_usage=self.cpu_usage_percent
            )
            self.cpu_usage_percent = max(0, min(100, self.cpu_usage_percent))
            
        if self.disk_usage_mb < 0:
            self.logger.warning(
                "Invalid disk usage detected",
                session_id=self.session_id,
                disk_usage=self.disk_usage_mb
            )
            self.disk_usage_mb = 0.0
            
    def update_timestamp(self) -> None:
        """Update the timestamp to current time."""
        self.timestamp = time.time()
        
    def set_alert_status(self, status: AlertStatus) -> None:
        """Set the alert status."""
        if self.alert_status != status:
            old_status = self.alert_status
            self.alert_status = status
            self.logger.info(
                "Resource alert status changed",
                session_id=self.session_id,
                context_id=self.context_id,
                old_status=old_status.value,
                new_status=status.value,
                memory_mb=self.memory_usage_mb,
                cpu_percent=self.cpu_usage_percent
            )
            
    def check_memory_threshold(self, threshold_mb: float) -> bool:
        """Check if memory usage exceeds threshold."""
        exceeds = self.memory_usage_mb > threshold_mb
        if exceeds:
            if self.alert_status == AlertStatus.NORMAL:
                self.set_alert_status(AlertStatus.WARNING)
            elif self.memory_usage_mb > threshold_mb * 1.5:
                self.set_alert_status(AlertStatus.CRITICAL)
        return exceeds
        
    def check_cpu_threshold(self, threshold_percent: float) -> bool:
        """Check if CPU usage exceeds threshold."""
        exceeds = self.cpu_usage_percent > threshold_percent
        if exceeds:
            if self.alert_status == AlertStatus.NORMAL:
                self.set_alert_status(AlertStatus.WARNING)
            elif self.cpu_usage_percent > threshold_percent * 1.2:
                self.set_alert_status(AlertStatus.CRITICAL)
        return exceeds
        
    def check_disk_threshold(self, threshold_mb: float) -> bool:
        """Check if disk usage exceeds threshold."""
        exceeds = self.disk_usage_mb > threshold_mb
        if exceeds and self.alert_status == AlertStatus.NORMAL:
            self.set_alert_status(AlertStatus.WARNING)
        return exceeds
        
    def get_memory_efficiency(self) -> float:
        """Calculate memory efficiency (tabs per MB)."""
        if self.memory_usage_mb > 0 and self.open_tabs_count > 0:
            return self.open_tabs_count / self.memory_usage_mb
        return 0.0
        
    def get_network_efficiency(self) -> float:
        """Calculate network efficiency (requests per MB sent)."""
        if self.network_bytes_sent > 0 and self.network_requests_count > 0:
            return self.network_requests_count / (self.network_bytes_sent / (1024 * 1024))
        return 0.0
        
    def is_critical(self) -> bool:
        """Check if any metrics are in critical state."""
        return self.alert_status == AlertStatus.CRITICAL
        
    def is_warning(self) -> bool:
        """Check if any metrics are in warning state."""
        return self.alert_status == AlertStatus.WARNING
        
    def is_healthy(self) -> bool:
        """Check if all metrics are healthy."""
        return self.alert_status == AlertStatus.NORMAL
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "context_id": self.context_id,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "disk_usage_mb": self.disk_usage_mb,
            "network_requests_count": self.network_requests_count,
            "open_tabs_count": self.open_tabs_count,
            "process_handles_count": self.process_handles_count,
            "alert_status": self.alert_status.value,
            "private_memory_mb": self.private_memory_mb,
            "shared_memory_mb": self.shared_memory_mb,
            "virtual_memory_mb": self.virtual_memory_mb,
            "gpu_memory_mb": self.gpu_memory_mb,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_received": self.network_bytes_received,
            "javascript_heap_size_mb": self.javascript_heap_size_mb,
            "javascript_heap_used_mb": self.javascript_heap_used_mb,
            "memory_efficiency": self.get_memory_efficiency(),
            "network_efficiency": self.get_network_efficiency(),
            "is_critical": self.is_critical(),
            "is_warning": self.is_warning(),
            "is_healthy": self.is_healthy()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceMetrics":
        """Create ResourceMetrics from dictionary."""
        # Convert alert_status string back to enum
        if "alert_status" in data and isinstance(data["alert_status"], str):
            data["alert_status"] = AlertStatus(data["alert_status"])
            
        # Remove derived fields that shouldn't be stored
        derived_fields = [
            "datetime", "memory_efficiency", "network_efficiency",
            "is_critical", "is_warning", "is_healthy"
        ]
        for field in derived_fields:
            data.pop(field, None)
            
        return cls(**data)
        
    def __str__(self) -> str:
        """String representation."""
        return (f"ResourceMetrics(session={self.session_id}, "
                f"memory={self.memory_usage_mb:.1f}MB, "
                f"cpu={self.cpu_usage_percent:.1f}%, "
                f"status={self.alert_status.value})")
        
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"ResourceMetrics(session_id={self.session_id}, "
                f"context_id={self.context_id}, "
                f"memory_usage_mb={self.memory_usage_mb}, "
                f"cpu_usage_percent={self.cpu_usage_percent}, "
                f"disk_usage_mb={self.disk_usage_mb}, "
                f"network_requests_count={self.network_requests_count}, "
                f"open_tabs_count={self.open_tabs_count}, "
                f"alert_status={self.alert_status.value})")
