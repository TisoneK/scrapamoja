"""
Retry Policy Data Model

Defines the RetryPolicy entity and related enums for configurable retry
strategies including backoff types, jitter settings, and failure classification.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class BackoffType(Enum):
    """Types of backoff strategies."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_WITH_JITTER = "exponential_with_jitter"
    CUSTOM = "custom"


class JitterType(Enum):
    """Types of jitter for backoff calculations."""
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


class RetryCondition(Enum):
    """Conditions for triggering retries."""
    TRANSIENT_FAILURE = "transient_failure"
    SPECIFIC_ERROR_CODES = "specific_error_codes"
    TIME_BASED = "time_based"
    CUSTOM = "custom"


@dataclass
class RetryPolicy:
    """Configurable retry policy with backoff strategies and failure classification."""
    
    # Core identifiers
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Retry configuration
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 300.0  # Maximum delay in seconds
    multiplier: float = 2.0  # Backoff multiplier
    
    # Backoff strategy
    backoff_type: BackoffType = BackoffType.EXPONENTIAL
    jitter_type: JitterType = JitterType.FULL
    jitter_factor: float = 0.1  # Jitter factor (0.0-1.0)
    
    # Retry conditions
    retry_conditions: List[RetryCondition] = field(default_factory=list)
    retryable_error_codes: List[int] = field(default_factory=list)
    retryable_error_patterns: List[str] = field(default_factory=list)
    
    # Time-based retry configuration
    time_window: Optional[int] = None  # Time window in seconds
    max_retries_per_window: Optional[int] = None
    
    # Failure classification
    classify_failures: bool = True
    transient_failure_patterns: List[str] = field(default_factory=list)
    permanent_failure_patterns: List[str] = field(default_factory=list)
    
    # Circuit breaker configuration
    enable_circuit_breaker: bool = False
    circuit_breaker_threshold: int = 5  # Failures before opening circuit
    circuit_breaker_timeout: float = 60.0  # Seconds before attempting recovery
    
    # Additional configuration
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        if not self.name:
            self.name = f"retry_policy_{self.id[:8]}"
        
        # Ensure enums are valid
        if isinstance(self.backoff_type, str):
            self.backoff_type = BackoffType(self.backoff_type)
        
        if isinstance(self.jitter_type, str):
            self.jitter_type = JitterType(self.jitter_type)
        
        # Convert string conditions to enums
        retry_conditions = []
        for condition in self.retry_conditions:
            if isinstance(condition, str):
                retry_conditions.append(RetryCondition(condition))
            else:
                retry_conditions.append(condition)
        self.retry_conditions = retry_conditions
        
        # Set default retry conditions if none specified
        if not self.retry_conditions:
            self.retry_conditions = [RetryCondition.TRANSIENT_FAILURE]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "max_attempts": self.max_attempts,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "multiplier": self.multiplier,
            "backoff_type": self.backoff_type.value,
            "jitter_type": self.jitter_type.value,
            "jitter_factor": self.jitter_factor,
            "retry_conditions": [cond.value for cond in self.retry_conditions],
            "retryable_error_codes": self.retryable_error_codes,
            "retryable_error_patterns": self.retryable_error_patterns,
            "time_window": self.time_window,
            "max_retries_per_window": self.max_retries_per_window,
            "classify_failures": self.classify_failures,
            "transient_failure_patterns": self.transient_failure_patterns,
            "permanent_failure_patterns": self.permanent_failure_patterns,
            "enable_circuit_breaker": self.enable_circuit_breaker,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
            "circuit_breaker_timeout": self.circuit_breaker_timeout,
            "metadata": self.metadata,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetryPolicy':
        """Create RetryPolicy from dictionary."""
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
        
        # Handle enums
        backoff_type = BackoffType(data.get("backoff_type", "exponential"))
        jitter_type = JitterType(data.get("jitter_type", "full"))
        
        # Handle retry conditions
        retry_conditions = []
        for condition in data.get("retry_conditions", []):
            if isinstance(condition, str):
                retry_conditions.append(RetryCondition(condition))
            else:
                retry_conditions.append(condition)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            created_at=created_at,
            updated_at=updated_at,
            max_attempts=data.get("max_attempts", 3),
            base_delay=data.get("base_delay", 1.0),
            max_delay=data.get("max_delay", 300.0),
            multiplier=data.get("multiplier", 2.0),
            backoff_type=backoff_type,
            jitter_type=jitter_type,
            jitter_factor=data.get("jitter_factor", 0.1),
            retry_conditions=retry_conditions,
            retryable_error_codes=data.get("retryable_error_codes", []),
            retryable_error_patterns=data.get("retryable_error_patterns", []),
            time_window=data.get("time_window"),
            max_retries_per_window=data.get("max_retries_per_window"),
            classify_failures=data.get("classify_failures", True),
            transient_failure_patterns=data.get("transient_failure_patterns", []),
            permanent_failure_patterns=data.get("permanent_failure_patterns", []),
            enable_circuit_breaker=data.get("enable_circuit_breaker", False),
            circuit_breaker_threshold=data.get("circuit_breaker_threshold", 5),
            circuit_breaker_timeout=data.get("circuit_breaker_timeout", 60.0),
            metadata=data.get("metadata", {}),
            enabled=data.get("enabled", True)
        )
    
    def should_retry(
        self,
        attempt: int,
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if a retry should be attempted.
        
        Args:
            attempt: Current attempt number (1-based)
            error: The error that occurred
            context: Additional context
            
        Returns:
            True if retry should be attempted, False otherwise
        """
        # Check if policy is enabled
        if not self.enabled:
            return False
        
        # Check max attempts
        if attempt > self.max_attempts:
            return False
        
        # Check retry conditions
        if not self._check_retry_conditions(error, context):
            return False
        
        # Check time-based limits
        if not self._check_time_limits(context):
            return False
        
        # Check circuit breaker
        if self.enable_circuit_breaker and not self._check_circuit_breaker(context):
            return False
        
        return True
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the next retry attempt.
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        if self.backoff_type == BackoffType.FIXED:
            delay = self.base_delay
        elif self.backoff_type == BackoffType.LINEAR:
            delay = self.base_delay * attempt
        elif self.backoff_type == BackoffType.EXPONENTIAL:
            delay = self.base_delay * (self.multiplier ** (attempt - 1))
        elif self.backoff_type == BackoffType.EXPONENTIAL_WITH_JITTER:
            delay = self.base_delay * (self.multiplier ** (attempt - 1))
            delay = self._apply_jitter(delay)
        else:  # CUSTOM
            delay = self.base_delay
        
        # Apply maximum limit
        delay = min(delay, self.max_delay)
        
        # Apply jitter if not exponential with jitter
        if self.backoff_type != BackoffType.EXPONENTIAL_WITH_JITTER:
            delay = self._apply_jitter(delay)
        
        return delay
    
    def is_retryable_error(self, error: Exception) -> bool:
        """
        Check if an error is retryable according to this policy.
        
        Args:
            error: The error to check
            
        Returns:
            True if error is retryable, False otherwise
        """
        if not self.classify_failures:
            return True
        
        error_message = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Check transient failure patterns
        for pattern in self.transient_failure_patterns:
            if pattern.lower() in error_message or pattern.lower() in error_type_name:
                return True
        
        # Check permanent failure patterns
        for pattern in self.permanent_failure_patterns:
            if pattern.lower() in error_message or pattern.lower() in error_type_name:
                return False
        
        # Check error codes
        if hasattr(error, 'code') and error.code in self.retryable_error_codes:
            return True
        
        # Check error patterns
        for pattern in self.retryable_error_patterns:
            if pattern.lower() in error_message:
                return True
        
        # Default to retryable
        return True
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)
    
    def clone(self, **kwargs) -> 'RetryPolicy':
        """Create a clone of this policy with optional overrides."""
        policy_dict = self.to_dict()
        policy_dict.update(kwargs)
        return RetryPolicy.from_dict(policy_dict)
    
    def _check_retry_conditions(
        self,
        error: Optional[Exception],
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if retry conditions are met."""
        if not self.retry_conditions:
            return True
        
        for condition in self.retry_conditions:
            if condition == RetryCondition.TRANSIENT_FAILURE:
                if error and self.is_retryable_error(error):
                    return True
            elif condition == RetryCondition.SPECIFIC_ERROR_CODES:
                if error and hasattr(error, 'code') and error.code in self.retryable_error_codes:
                    return True
            elif condition == RetryCondition.TIME_BASED:
                if context and self._check_time_limits(context):
                    return True
            elif condition == RetryCondition.CUSTOM:
                # Custom logic would be implemented here
                if context and context.get("custom_retry_condition", False):
                    return True
        
        return False
    
    def _check_time_limits(self, context: Optional[Dict[str, Any]]) -> bool:
        """Check time-based retry limits."""
        if not self.time_window or not self.max_retries_per_window:
            return True
        
        if not context:
            return True
        
        # In a real implementation, this would check actual retry history
        # For now, return True to allow retries
        return True
    
    def _check_circuit_breaker(self, context: Optional[Dict[str, Any]]) -> bool:
        """Check circuit breaker state."""
        if not context:
            return True
        
        # In a real implementation, this would check actual circuit breaker state
        # For now, return True to allow retries
        return True
    
    def _apply_jitter(self, delay: float) -> float:
        """Apply jitter to delay value."""
        if self.jitter_type == JitterType.NONE:
            return delay
        
        if self.jitter_type == JitterType.FULL:
            # Full jitter: random between 0 and delay
            import random
            return delay * random.random()
        
        if self.jitter_type == JitterType.EQUAL:
            # Equal jitter: delay/2 ± delay/2 * jitter_factor
            import random
            half_delay = delay / 2
            jitter = half_delay * self.jitter_factor * (random.random() * 2 - 1)
            return half_delay + jitter
        
        if self.jitter_type == JitterType.DECORRELATED:
            # Decorrelated jitter: random between base_delay and delay * 3
            import random
            return min(self.max_delay, random.uniform(self.base_delay, delay * 3))
        
        return delay
    
    def __str__(self) -> str:
        """String representation of the retry policy."""
        return (
            f"RetryPolicy(id={self.id[:8]}, name='{self.name}', "
            f"max_attempts={self.max_attempts}, backoff={self.backoff_type.value})"
        )
    
    def __repr__(self) -> str:
        """Detailed string representation of the retry policy."""
        return (
            f"RetryPolicy(id='{self.id}', name='{self.name}', "
            f"description='{self.description}', max_attempts={self.max_attempts}, "
            f"base_delay={self.base_delay}, max_delay={self.max_delay}, "
            f"multiplier={self.multiplier}, backoff_type={self.backoff_type}, "
            f"jitter_type={self.jitter_type}, enabled={self.enabled})"
        )


# Default retry policies
DEFAULT_EXPONENTIAL_BACKOFF = RetryPolicy(
    name="default_exponential_backoff",
    description="Default exponential backoff with jitter",
    max_attempts=5,
    base_delay=1.0,
    max_delay=60.0,
    multiplier=2.0,
    backoff_type=BackoffType.EXPONENTIAL_WITH_JITTER,
    jitter_type=JitterType.FULL,
    jitter_factor=0.1
)

AGGRESSIVE_RETRY = RetryPolicy(
    name="aggressive_retry",
    description="Aggressive retry with short delays",
    max_attempts=10,
    base_delay=0.5,
    max_delay=30.0,
    multiplier=1.5,
    backoff_type=BackoffType.EXPONENTIAL_WITH_JITTER,
    jitter_type=JitterType.FULL,
    jitter_factor=0.2
)

CONSERVATIVE_RETRY = RetryPolicy(
    name="conservative_retry",
    description="Conservative retry with longer delays",
    max_attempts=3,
    base_delay=2.0,
    max_delay=120.0,
    multiplier=3.0,
    backoff_type=BackoffType.EXPONENTIAL,
    jitter_type=JitterType.EQUAL,
    jitter_factor=0.1
)

LINEAR_RETRY = RetryPolicy(
    name="linear_retry",
    description="Linear backoff without jitter",
    max_attempts=5,
    base_delay=1.0,
    max_delay=60.0,
    multiplier=1.0,
    backoff_type=BackoffType.LINEAR,
    jitter_type=JitterType.NONE
)

FIXED_RETRY = RetryPolicy(
    name="fixed_retry",
    description="Fixed delay retry",
    max_attempts=3,
    base_delay=5.0,
    max_delay=5.0,
    multiplier=1.0,
    backoff_type=BackoffType.FIXED,
    jitter_type=JitterType.NONE
)
