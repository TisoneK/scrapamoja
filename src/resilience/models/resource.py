"""
Resource Data Model

Defines the Resource entity and related enums for resource lifecycle control,
memory management, and browser restart policies with monitoring capabilities.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class ResourceType(Enum):
    """Types of resources that can be managed."""
    MEMORY = "memory"
    CPU = "cpu"
    DISK = "disk"
    NETWORK = "network"
    BROWSER = "browser"
    TAB = "tab"
    PROCESS = "process"
    CUSTOM = "custom"


class ResourceStatus(Enum):
    """Status of a resource."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"
    RESTARTING = "restarting"
    RECOVERING = "recovering"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ResourceAction(Enum):
    """Actions that can be taken on resources."""
    MONITOR = "monitor"
    THROTTLE = "throttle"
    RESTART = "restart"
    RECOVER = "recover"
    CLEANUP = "cleanup"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    TERMINATE = "terminate"
    CUSTOM = "custom"


class RestartPolicy(Enum):
    """Restart policies for resources."""
    NEVER = "never"
    ON_FAILURE = "on_failure"
    ON_THRESHOLD = "on_threshold"
    ON_SCHEDULE = "on_schedule"
    ADAPTIVE = "adaptive"
    CUSTOM = "custom"


@dataclass
class ResourceThreshold:
    """Threshold configuration for resource monitoring."""
    warning_threshold: float = 80.0
    critical_threshold: float = 90.0
    exhausted_threshold: float = 95.0
    restart_threshold: float = 85.0
    unit: str = "percent"
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "exhausted_threshold": self.exhausted_threshold,
            "restart_threshold": self.restart_threshold,
            "unit": self.unit,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceThreshold':
        """Create ResourceThreshold from dictionary."""
        return cls(
            warning_threshold=data.get("warning_threshold", 80.0),
            critical_threshold=data.get("critical_threshold", 90.0),
            exhausted_threshold=data.get("exhausted_threshold", 95.0),
            restart_threshold=data.get("restart_threshold", 85.0),
            unit=data.get("unit", "percent"),
            enabled=data.get("enabled", True)
        )


@dataclass
class ResourceMetrics:
    """Current metrics for a resource."""
    current_value: float = 0.0
    peak_value: float = 0.0
    average_value: float = 0.0
    minimum_value: float = 0.0
    maximum_value: float = 100.0
    unit: str = "percent"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    samples_count: int = 0
    trend: str = "stable"  # increasing, decreasing, stable
    rate_of_change: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "current_value": self.current_value,
            "peak_value": self.peak_value,
            "average_value": self.average_value,
            "minimum_value": self.minimum_value,
            "maximum_value": self.maximum_value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "samples_count": self.samples_count,
            "trend": self.trend,
            "rate_of_change": self.rate_of_change
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceMetrics':
        """Create ResourceMetrics from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()
        
        return cls(
            current_value=data.get("current_value", 0.0),
            peak_value=data.get("peak_value", 0.0),
            average_value=data.get("average_value", 0.0),
            minimum_value=data.get("minimum_value", 0.0),
            maximum_value=data.get("maximum_value", 100.0),
            unit=data.get("unit", "percent"),
            timestamp=timestamp,
            samples_count=data.get("samples_count", 0),
            trend=data.get("trend", "stable"),
            rate_of_change=data.get("rate_of_change", 0.0)
        )


@dataclass
class ResourceConfiguration:
    """Configuration for resource management."""
    resource_type: ResourceType
    name: str
    description: str = ""
    thresholds: ResourceThreshold = field(default_factory=ResourceThreshold)
    restart_policy: RestartPolicy = RestartPolicy.ON_THRESHOLD
    monitoring_enabled: bool = True
    auto_recovery_enabled: bool = True
    cleanup_enabled: bool = True
    max_restarts_per_hour: int = 5
    restart_cooldown_minutes: int = 10
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "resource_type": self.resource_type.value,
            "name": self.name,
            "description": self.description,
            "thresholds": self.thresholds.to_dict(),
            "restart_policy": self.restart_policy.value,
            "monitoring_enabled": self.monitoring_enabled,
            "auto_recovery_enabled": self.auto_recovery_enabled,
            "cleanup_enabled": self.cleanup_enabled,
            "max_restarts_per_hour": self.max_restarts_per_hour,
            "restart_cooldown_minutes": self.restart_cooldown_minutes,
            "custom_settings": self.custom_settings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceConfiguration':
        """Create ResourceConfiguration from dictionary."""
        return cls(
            resource_type=ResourceType(data.get("resource_type", "memory")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            thresholds=ResourceThreshold.from_dict(data.get("thresholds", {})),
            restart_policy=RestartPolicy(data.get("restart_policy", "on_threshold")),
            monitoring_enabled=data.get("monitoring_enabled", True),
            auto_recovery_enabled=data.get("auto_recovery_enabled", True),
            cleanup_enabled=data.get("cleanup_enabled", True),
            max_restarts_per_hour=data.get("max_restarts_per_hour", 5),
            restart_cooldown_minutes=data.get("restart_cooldown_minutes", 10),
            custom_settings=data.get("custom_settings", {})
        )


@dataclass
class Resource:
    """Resource entity for lifecycle control and monitoring."""
    
    # Core identifiers
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    resource_type: ResourceType = ResourceType.MEMORY
    status: ResourceStatus = ResourceStatus.HEALTHY
    
    # Configuration and thresholds
    configuration: Optional[ResourceConfiguration] = None
    
    # Current metrics and state
    metrics: ResourceMetrics = field(default_factory=ResourceMetrics)
    last_restart: Optional[datetime] = None
    restart_count: int = 0
    last_action: Optional[ResourceAction] = None
    last_action_time: Optional[datetime] = None
    
    # Lifecycle management
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_monitored: Optional[datetime] = None
    
    # Additional information
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        if not self.name:
            raise ValueError("name is required")
        
        # Set default configuration if not provided
        if self.configuration is None:
            self.configuration = ResourceConfiguration(
                resource_type=self.resource_type,
                name=self.name
            )
        
        # Ensure enums are valid
        if isinstance(self.status, str):
            self.status = ResourceStatus(self.status)
        
        if isinstance(self.resource_type, str):
            self.resource_type = ResourceType(self.resource_type)
        
        if isinstance(self.last_action, str):
            self.last_action = ResourceAction(self.last_action)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "resource_type": self.resource_type.value,
            "status": self.status.value,
            "configuration": self.configuration.to_dict() if self.configuration else None,
            "metrics": self.metrics.to_dict(),
            "last_restart": self.last_restart.isoformat() if self.last_restart else None,
            "restart_count": self.restart_count,
            "last_action": self.last_action.value if self.last_action else None,
            "last_action_time": self.last_action_time.isoformat() if self.last_action_time else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_monitored": self.last_monitored.isoformat() if self.last_monitored else None,
            "description": self.description,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Resource':
        """Create Resource from dictionary."""
        # Handle timestamps
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.utcnow()
        
        last_restart = data.get("last_restart")
        if isinstance(last_restart, str):
            last_restart = datetime.fromisoformat(last_restart)
        
        last_action_time = data.get("last_action_time")
        if isinstance(last_action_time, str):
            last_action_time = datetime.fromisoformat(last_action_time)
        
        last_monitored = data.get("last_monitored")
        if isinstance(last_monitored, str):
            last_monitored = datetime.fromisoformat(last_monitored)
        
        # Handle enums
        status = ResourceStatus(data.get("status", "healthy"))
        resource_type = ResourceType(data.get("resource_type", "memory"))
        last_action = data.get("last_action")
        if last_action:
            last_action = ResourceAction(last_action)
        
        # Handle configuration
        config_data = data.get("configuration")
        configuration = ResourceConfiguration.from_dict(config_data) if config_data else None
        
        # Handle metrics
        metrics_data = data.get("metrics")
        metrics = ResourceMetrics.from_dict(metrics_data) if metrics_data else ResourceMetrics()
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            resource_type=resource_type,
            status=status,
            configuration=configuration,
            metrics=metrics,
            last_restart=last_restart,
            restart_count=data.get("restart_count", 0),
            last_action=last_action,
            last_action_time=last_action_time,
            created_at=created_at,
            updated_at=updated_at,
            last_monitored=last_monitored,
            description=data.get("description", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )
    
    def update_status(self, status: ResourceStatus) -> None:
        """Update resource status."""
        self.status = status
        self.updated_at = datetime.utcnow()
    
    def update_metrics(self, metrics: ResourceMetrics) -> None:
        """Update resource metrics."""
        self.metrics = metrics
        self.last_monitored = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Update status based on thresholds
        if self.configuration and self.configuration.thresholds.enabled:
            self._update_status_from_metrics()
    
    def record_action(self, action: ResourceAction) -> None:
        """Record an action taken on the resource."""
        self.last_action = action
        self.last_action_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if action == ResourceAction.RESTART:
            self.restart_count += 1
            self.last_restart = datetime.utcnow()
    
    def is_healthy(self) -> bool:
        """Check if resource is healthy."""
        return self.status in [ResourceStatus.HEALTHY, ResourceStatus.WARNING]
    
    def needs_restart(self) -> bool:
        """Check if resource needs restart based on thresholds."""
        if not self.configuration or not self.configuration.thresholds.enabled:
            return False
        
        return self.metrics.current_value >= self.configuration.thresholds.restart_threshold
    
    def can_restart(self) -> bool:
        """Check if resource can be restarted (cooldown and limits)."""
        if not self.configuration:
            return True
        
        # Check cooldown
        if self.last_restart:
            cooldown_minutes = self.configuration.restart_cooldown_minutes
            time_since_restart = (datetime.utcnow() - self.last_restart).total_seconds() / 60
            if time_since_restart < cooldown_minutes:
                return False
        
        # Check restart limits
        max_restarts = self.configuration.max_restarts_per_hour
        if self.restart_count >= max_restarts:
            return False
        
        return True
    
    def get_age_seconds(self) -> float:
        """Get the age of the resource in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    def get_age_minutes(self) -> float:
        """Get the age of the resource in minutes."""
        return self.get_age_seconds() / 60.0
    
    def get_age_hours(self) -> float:
        """Get the age of the resource in hours."""
        return self.get_age_minutes() / 60.0
    
    def get_time_since_last_restart(self) -> float:
        """Get time since last restart in minutes."""
        if not self.last_restart:
            return float('inf')
        return (datetime.utcnow() - self.last_restart).total_seconds() / 60.0
    
    def _update_status_from_metrics(self) -> None:
        """Update status based on current metrics and thresholds."""
        if not self.configuration or not self.configuration.thresholds.enabled:
            return
        
        thresholds = self.configuration.thresholds
        current_value = self.metrics.current_value
        
        if current_value >= thresholds.exhausted_threshold:
            self.status = ResourceStatus.EXHAUSTED
        elif current_value >= thresholds.critical_threshold:
            self.status = ResourceStatus.CRITICAL
        elif current_value >= thresholds.warning_threshold:
            self.status = ResourceStatus.WARNING
        else:
            self.status = ResourceStatus.HEALTHY
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the resource."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the resource."""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if resource has a specific tag."""
        return tag in self.tags
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)
    
    def clone(self, **kwargs) -> 'Resource':
        """Create a clone of this resource with optional overrides."""
        resource_dict = self.to_dict()
        resource_dict.update(kwargs)
        return Resource.from_dict(resource_dict)
    
    def __str__(self) -> str:
        """String representation of the resource."""
        return (
            f"Resource(id={self.id[:8]}, name={self.name}, "
            f"type={self.resource_type.value}, status={self.status.value})"
        )
    
    def __repr__(self) -> str:
        """Detailed string representation of the resource."""
        return (
            f"Resource(id='{self.id}', name='{self.name}', "
            f"type={self.resource_type.value}, status={self.status.value}, "
            f"current_value={self.metrics.current_value}, restart_count={self.restart_count})"
        )


@dataclass
class ResourceSummary:
    """Summary information about resources."""
    total_resources: int = 0
    healthy_resources: int = 0
    warning_resources: int = 0
    critical_resources: int = 0
    exhausted_resources: int = 0
    restarting_resources: int = 0
    recovering_resources: int = 0
    failed_resources: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_resources": self.total_resources,
            "healthy_resources": self.healthy_resources,
            "warning_resources": self.warning_resources,
            "critical_resources": self.critical_resources,
            "exhausted_resources": self.exhausted_resources,
            "restarting_resources": self.restarting_resources,
            "recovering_resources": self.recovering_resources,
            "failed_resources": self.failed_resources,
            "unhealthy_resources": (
                self.warning_resources + self.critical_resources + 
                self.exhausted_resources + self.failed_resources
            )
        }


# Default resource configurations
DEFAULT_MEMORY_CONFIG = ResourceConfiguration(
    resource_type=ResourceType.MEMORY,
    name="default_memory",
    description="Default memory resource configuration",
    thresholds=ResourceThreshold(
        warning_threshold=70.0,
        critical_threshold=85.0,
        exhausted_threshold=95.0,
        restart_threshold=80.0
    ),
    restart_policy=RestartPolicy.ON_THRESHOLD,
    max_restarts_per_hour=3,
    restart_cooldown_minutes=15
)

DEFAULT_BROWSER_CONFIG = ResourceConfiguration(
    resource_type=ResourceType.BROWSER,
    name="default_browser",
    description="Default browser resource configuration",
    thresholds=ResourceThreshold(
        warning_threshold=75.0,
        critical_threshold=90.0,
        exhausted_threshold=95.0,
        restart_threshold=85.0
    ),
    restart_policy=RestartPolicy.ON_THRESHOLD,
    max_restarts_per_hour=5,
    restart_cooldown_minutes=10
)

DEFAULT_CPU_CONFIG = ResourceConfiguration(
    resource_type=ResourceType.CPU,
    name="default_cpu",
    description="Default CPU resource configuration",
    thresholds=ResourceThreshold(
        warning_threshold=80.0,
        critical_threshold=90.0,
        exhausted_threshold=95.0,
        restart_threshold=85.0
    ),
    restart_policy=RestartPolicy.ON_THRESHOLD,
    max_restarts_per_hour=2,
    restart_cooldown_minutes=20
)
