"""
Abort Policy Data Model

Defines abort policies for intelligent failure detection and automatic shutdown.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class AbortTrigger(Enum):
    FAILURE_RATE = "failure_rate"
    ERROR_THRESHOLD = "error_threshold"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CRITICAL_ERROR = "critical_error"
    MANUAL = "manual"


class AbortAction(Enum):
    STOP_IMMEDIATELY = "stop_immediately"
    GRACEFUL_SHUTDOWN = "graceful_shutdown"
    SAVE_STATE_AND_STOP = "save_state_and_stop"
    ROLLBACK = "rollback"


class AbortSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AbortStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRIGGERED = "triggered"
    DISABLED = "disabled"


@dataclass
class AbortCondition:
    trigger_type: AbortTrigger
    threshold: float
    time_window_seconds: int = 300
    severity: AbortSeverity = AbortSeverity.MEDIUM
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger_type": self.trigger_type.value,
            "threshold": self.threshold,
            "time_window_seconds": self.time_window_seconds,
            "severity": self.severity.value,
            "description": self.description
        }


@dataclass
class AbortMetrics:
    total_operations: int = 0
    failed_operations: int = 0
    error_count: int = 0
    failure_rate: float = 0.0
    error_rate: float = 0.0
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_operations": self.total_operations,
            "failed_operations": self.failed_operations,
            "error_count": self.error_count,
            "failure_rate": self.failure_rate,
            "error_rate": self.error_rate,
            "consecutive_failures": self.consecutive_failures,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


@dataclass
class AbortPolicy:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: AbortStatus = AbortStatus.ACTIVE
    conditions: List[AbortCondition] = field(default_factory=list)
    action: AbortAction = AbortAction.STOP_IMMEDIATELY
    enabled: bool = True
    priority: int = 0
    cooldown_seconds: int = 300
    max_aborts_per_hour: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    abort_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "conditions": [c.to_dict() for c in self.conditions],
            "action": self.action.value,
            "enabled": self.enabled,
            "priority": self.priority,
            "cooldown_seconds": self.cooldown_seconds,
            "max_aborts_per_hour": self.max_aborts_per_hour,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "abort_count": self.abort_count,
            "tags": self.tags,
            "metadata": self.metadata
        }


# Default abort policies
DEFAULT_FAILURE_RATE_POLICY = AbortPolicy(
    name="high_failure_rate",
    description="Abort when failure rate exceeds 50% over 10 operations",
    conditions=[
        AbortCondition(
            trigger_type=AbortTrigger.FAILURE_RATE,
            threshold=0.5,
            time_window_seconds=600,
            severity=AbortSeverity.HIGH,
            description="Failure rate > 50% over 10 minutes"
        )
    ],
    action=AbortAction.SAVE_STATE_AND_STOP,
    priority=100
)

DEFAULT_ERROR_THRESHOLD_POLICY = AbortPolicy(
    name="error_threshold",
    description="Abort when error count exceeds threshold",
    conditions=[
        AbortCondition(
            trigger_type=AbortTrigger.ERROR_THRESHOLD,
            threshold=10,
            time_window_seconds=300,
            severity=AbortSeverity.MEDIUM,
            description="Error count > 10 in 5 minutes"
        )
    ],
    action=AbortAction.GRACEFUL_SHUTDOWN,
    priority=90
)
