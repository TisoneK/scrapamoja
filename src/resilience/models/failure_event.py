"""
Failure Event Data Model

Defines the FailureEvent entity and related enums for capturing detailed
information about failures including context, stack traces, and recovery actions.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class FailureSeverity(Enum):
    """Severity levels for failure events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FailureCategory(Enum):
    """Categories of failures."""
    NETWORK = "network"
    BROWSER = "browser"
    SYSTEM = "system"
    APPLICATION = "application"
    EXTERNAL = "external"


class RecoveryAction(Enum):
    """Types of recovery actions taken."""
    RETRY = "retry"
    RESTART = "restart"
    SKIP = "skip"
    ABORT = "abort"
    MANUAL = "manual"


@dataclass
class FailureEvent:
    """Captures detailed information about failures including context, stack traces, and recovery actions."""
    
    # Core identifiers
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    
    # Failure classification
    severity: FailureSeverity = FailureSeverity.MEDIUM
    category: FailureCategory = FailureCategory.APPLICATION
    source: str = "resilience"
    message: str = ""
    
    # Context and details
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    
    # Recovery information
    recovery_action: Optional[RecoveryAction] = None
    resolution_time: Optional[float] = None  # Time to resolution in seconds
    resolved: bool = False
    
    # Additional metadata
    job_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        if self.correlation_id is None:
            # Generate correlation ID if not provided
            import uuid
            self.correlation_id = str(uuid.uuid4())
        
        # Ensure severity and category are valid enums
        if isinstance(self.severity, str):
            self.severity = FailureSeverity(self.severity)
        
        if isinstance(self.category, str):
            self.category = FailureCategory(self.category)
        
        if isinstance(self.recovery_action, str):
            self.recovery_action = RecoveryAction(self.recovery_action)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "severity": self.severity.value,
            "category": self.category.value,
            "source": self.source,
            "message": self.message,
            "context": self.context,
            "stack_trace": self.stack_trace,
            "recovery_action": self.recovery_action.value if self.recovery_action else None,
            "resolution_time": self.resolution_time,
            "resolved": self.resolved,
            "job_id": self.job_id,
            "component": self.component,
            "operation": self.operation
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FailureEvent':
        """Create FailureEvent from dictionary."""
        # Handle timestamp
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()
        
        # Handle enums
        severity = FailureSeverity(data.get("severity", "medium"))
        category = FailureCategory(data.get("category", "application"))
        
        recovery_action = data.get("recovery_action")
        if recovery_action:
            recovery_action = RecoveryAction(recovery_action)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            timestamp=timestamp,
            correlation_id=data.get("correlation_id"),
            severity=severity,
            category=category,
            source=data.get("source", "resilience"),
            message=data.get("message", ""),
            context=data.get("context", {}),
            stack_trace=data.get("stack_trace"),
            recovery_action=recovery_action,
            resolution_time=data.get("resolution_time"),
            resolved=data.get("resolved", False),
            job_id=data.get("job_id"),
            component=data.get("component"),
            operation=data.get("operation")
        )
    
    def mark_resolved(
        self,
        recovery_action: RecoveryAction,
        resolution_time: Optional[float] = None
    ) -> None:
        """Mark the failure as resolved."""
        self.recovery_action = recovery_action
        self.resolved = True
        
        if resolution_time is None:
            # Calculate resolution time from creation
            resolution_time = (datetime.utcnow() - self.timestamp).total_seconds()
        
        self.resolution_time = resolution_time
    
    def add_context(self, key: str, value: Any) -> None:
        """Add context information to the failure event."""
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context information from the failure event."""
        return self.context.get(key, default)
    
    def is_critical(self) -> bool:
        """Check if this is a critical failure."""
        return self.severity == FailureSeverity.CRITICAL
    
    def is_network_related(self) -> bool:
        """Check if this is a network-related failure."""
        return self.category == FailureCategory.NETWORK
    
    def is_browser_related(self) -> bool:
        """Check if this is a browser-related failure."""
        return self.category == FailureCategory.BROWSER
    
    def is_system_related(self) -> bool:
        """Check if this is a system-related failure."""
        return self.category == FailureCategory.SYSTEM
    
    def is_application_related(self) -> bool:
        """Check if this is an application-related failure."""
        return self.category == FailureCategory.APPLICATION
    
    def is_external_related(self) -> bool:
        """Check if this is an external service-related failure."""
        return self.category == FailureCategory.EXTERNAL
    
    def get_age_seconds(self) -> float:
        """Get the age of the failure event in seconds."""
        return (datetime.utcnow() - self.timestamp).total_seconds()
    
    def get_age_minutes(self) -> float:
        """Get the age of the failure event in minutes."""
        return self.get_age_seconds() / 60.0
    
    def __str__(self) -> str:
        """String representation of the failure event."""
        return (
            f"FailureEvent(id={self.id}, severity={self.severity.value}, "
            f"category={self.category.value}, source={self.source}, "
            f"message='{self.message}', resolved={self.resolved})"
        )
    
    def __repr__(self) -> str:
        """Detailed string representation of the failure event."""
        return (
            f"FailureEvent(id='{self.id}', timestamp='{self.timestamp.isoformat()}', "
            f"correlation_id='{self.correlation_id}', severity={self.severity}, "
            f"category={self.category}, source='{self.source}', "
            f"message='{self.message}', resolved={self.resolved})"
        )
