"""
Fallback-specific data models for selector fallback chain execution.

This module defines the data structures for fallback configuration,
fallback chain management, and failure event tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class FailureType(Enum):
    """Types of selector failures that can trigger fallback."""
    EMPTY_RESULT = "empty_result"
    EXCEPTION = "exception"
    LOW_CONFIDENCE = "low_confidence"
    VALIDATION_FAILED = "validation_failed"
    TIMEOUT = "timeout"


class FallbackStatus(Enum):
    """Status of a fallback attempt."""
    PENDING = "pending"
    EXECUTED = "executed"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FallbackConfig:
    """Configuration for a fallback selector."""
    selector_name: str
    priority: int = 1
    enabled: bool = True
    max_attempts: int = 1
    timeout_seconds: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate fallback configuration."""
        if self.priority < 1:
            raise ValueError("Fallback priority must be >= 1")
        if self.max_attempts < 1:
            raise ValueError("Max attempts must be >= 1")
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class FailureEvent:
    """Captured information about a selector failure."""
    selector_id: str
    url: str
    timestamp: datetime
    failure_type: FailureType
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None
    resolution_time: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert failure event to dictionary representation."""
        return {
            "selector_id": self.selector_id,
            "url": self.url,
            "timestamp": self.timestamp.isoformat(),
            "failure_type": self.failure_type.value,
            "error_message": self.error_message,
            "confidence_score": self.confidence_score,
            "resolution_time": self.resolution_time,
            "context": self.context
        }


@dataclass
class FallbackAttempt:
    """Information about a single fallback attempt."""
    fallback_selector: str
    status: FallbackStatus
    timestamp: datetime
    result: Optional[Any] = None
    error: Optional[str] = None
    resolution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert fallback attempt to dictionary representation."""
        return {
            "fallback_selector": self.fallback_selector,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "resolution_time": self.resolution_time
        }


@dataclass
class FallbackChain:
    """Container for a primary selector and its fallback chain."""
    primary_selector: str
    fallbacks: List[FallbackConfig]
    max_chain_duration: float = 5.0  # NFR1: Max 5 seconds for sync fallback

    def __post_init__(self):
        """Validate fallback chain configuration."""
        if not self.primary_selector:
            raise ValueError("Primary selector cannot be empty")
        if not self.fallbacks:
            raise ValueError("At least one fallback is required")
        if self.max_chain_duration <= 0:
            raise ValueError("Max chain duration must be positive")

        # Sort fallbacks by priority
        self.fallbacks.sort(key=lambda f: f.priority)

    def get_fallback_names(self) -> List[str]:
        """Get list of fallback selector names in priority order."""
        return [f.selector_name for f in self.fallbacks if f.enabled]

    def add_fallback(self, fallback: FallbackConfig) -> None:
        """Add a fallback to the chain."""
        self.fallbacks.append(fallback)
        self.fallbacks.sort(key=lambda f: f.priority)


@dataclass
class FallbackResult:
    """Result of fallback chain execution."""
    primary_selector: str
    primary_success: bool
    fallback_executed: bool
    fallback_success: bool
    final_result: Optional[Any]
    failure_event: Optional[FailureEvent] = None
    fallback_attempt: Optional[FallbackAttempt] = None
    chain_duration: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attempted_selectors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def overall_success(self) -> bool:
        """Check if the overall operation was successful."""
        return self.primary_success or (self.fallback_executed and self.fallback_success)

    def to_dict(self) -> Dict[str, Any]:
        """Convert fallback result to dictionary representation."""
        result = {
            "primary_selector": self.primary_selector,
            "primary_success": self.primary_success,
            "fallback_executed": self.fallback_executed,
            "fallback_success": self.fallback_success,
            "overall_success": self.overall_success,
            "chain_duration": self.chain_duration,
            "timestamp": self.timestamp.isoformat(),
            "attempted_selectors": self.attempted_selectors
        }
        if self.failure_event:
            result["failure_event"] = self.failure_event.to_dict()
        if self.fallback_attempt:
            result["fallback_attempt"] = self.fallback_attempt.to_dict()
        return result


@dataclass
class SelectorAttempt:
    """Information about a single selector attempt in the fallback chain."""
    name: str
    result: str  # "success" or "failure"
    reason: Optional[str] = None
    value: Optional[str] = None
    resolution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert selector attempt to dictionary."""
        return {
            "name": self.name,
            "result": self.result,
            "reason": self.reason,
            "value": self._redact_value(self.value) if self.value else None,
            "resolution_time_ms": self.resolution_time_ms
        }

    @staticmethod
    def _redact_value(value: Optional[str]) -> Optional[str]:
        """Redact potentially sensitive values from logs."""
        if value is None:
            return None
        # Redact common sensitive patterns
        sensitive_patterns = ['password', 'token', 'secret', 'key', 'auth']
        value_lower = value.lower()
        if any(pattern in value_lower for pattern in sensitive_patterns):
            return "[REDACTED]"
        # Truncate long values
        if len(value) > 100:
            return value[:100] + "..."
        return value


@dataclass
class FallbackAttemptLog:
    """Structured log entry for fallback attempt (AC1, AC2, AC3)."""
    selector_id: str
    page_url: str
    timestamp: datetime
    attempted_selectors: List[SelectorAttempt]
    final_result: str  # "success" or "failure"
    total_time_ms: float
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert fallback attempt log to dictionary representation."""
        return {
            "selector_id": self.selector_id,
            "page_url": self.page_url,
            "timestamp": self.timestamp.isoformat(),
            "attempted_selectors": [s.to_dict() for s in self.attempted_selectors],
            "final_result": self.final_result,
            "total_time_ms": self.total_time_ms,
            "correlation_id": self.correlation_id
        }

    @property
    def successful_selector(self) -> Optional[str]:
        """Get the selector that succeeded (AC2)."""
        for attempt in self.attempted_selectors:
            if attempt.result == "success":
                return attempt.name
        return None

    @property
    def failed_selectors(self) -> List[Dict[str, str]]:
        """Get all failed selectors with reasons (AC3)."""
        result: List[Dict[str, str]] = []
        for attempt in self.attempted_selectors:
            if attempt.result == "failure":
                result.append({"name": attempt.name, "reason": attempt.reason or "unknown"})
        return result
