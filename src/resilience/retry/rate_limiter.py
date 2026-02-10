"""
Rate Limiting Detection and Handling

Detects rate limiting scenarios and implements appropriate retry strategies
including exponential backoff, jitter, and adaptive retry patterns.
"""

import time
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from ..models.retry_policy import RetryPolicy, BackoffType, JitterType
from ..logging.resilience_logger import get_logger
from ..correlation import get_correlation_id
from ..events import publish_retry_event


class RateLimitType(Enum):
    """Types of rate limiting."""
    UNKNOWN = "unknown"
    HTTP_429 = "http_429"
    TIME_BASED = "time_based"
    QUOTA_EXCEEDED = "quota_exceeded"
    CONCURRENT_LIMIT = "concurrent_limit"
    BANDWIDTH_LIMIT = "bandwidth_limit"
    API_LIMIT = "api_limit"
    CUSTOM = "custom"


class RateLimitStrategy(Enum):
    """Rate limiting response strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    ADAPTIVE_BACKOFF = "adaptive_backoff"
    CIRCUIT_BREAK = "circuit_break"


@dataclass
class RateLimitInfo:
    """Information about detected rate limiting."""
    limit_type: RateLimitType
    strategy: RateLimitStrategy
    limit_value: Optional[int] = None
    window_seconds: Optional[int] = None
    retry_after: Optional[int] = None
    reset_time: Optional[datetime] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if rate limit has expired."""
        if self.reset_time:
            return datetime.utcnow() >= self.reset_time
        if self.retry_after:
            return datetime.utcnow() >= (self.detected_at + timedelta(seconds=self.retry_after))
        return False
    
    def get_wait_time(self) -> float:
        """Get time to wait before next retry."""
        if self.retry_after:
            elapsed = (datetime.utcnow() - self.detected_at).total_seconds()
            return max(0, self.retry_after - elapsed)
        
        if self.reset_time:
            return max(0, (self.reset_time - datetime.utcnow()).total_seconds())
        
        # Default wait time based on limit type
        if self.limit_type == RateLimitType.HTTP_429:
            return 60.0  # 1 minute default
        elif self.limit_type == RateLimitType.QUOTA_EXCEEDED:
            return 300.0  # 5 minutes default
        elif self.limit_type == RateLimitType.CONCURRENT_LIMIT:
            return 5.0  # 5 seconds default
        else:
            return 30.0  # 30 seconds default


class RateLimitDetector:
    """Detects rate limiting from errors and responses."""
    
    def __init__(self):
        """Initialize rate limit detector."""
        self.logger = get_logger("rate_limit_detector")
        
        # HTTP 429 patterns
        self.http_429_patterns = [
            r"429.*too.*many.*requests",
            r"too.*many.*requests",
            r"rate.*limit.*exceeded",
            r"rate.*limit.*reached",
            r"quota.*exceeded",
            r"quota.*reached",
            r"request.*limit.*exceeded",
            r"api.*limit.*exceeded",
            r"throttled",
            r"throttling",
            r"request.*throttled",
            r"api.*throttled"
        ]
        
        # Time-based rate limiting patterns
        self.time_based_patterns = [
            r"try.*again.*in.*\d+.*second",
            r"try.*again.*in.*\d+.*minute",
            r"try.*again.*after.*\d+.*second",
            r"try.*again.*after.*\d+.*minute",
            r"retry.*after.*\d+.*second",
            r"retry.*after.*\d+.*minute",
            r"wait.*\d+.*second",
            r"wait.*\d+.*minute"
        ]
        
        # Quota exceeded patterns
        self.quota_patterns = [
            r"quota.*exceeded",
            r"quota.*reached",
            r"daily.*quota.*exceeded",
            r"monthly.*quota.*exceeded",
            r"api.*quota.*exceeded",
            r"usage.*limit.*exceeded",
            r"limit.*exceeded.*per.*day",
            r"limit.*exceeded.*per.*hour"
        ]
        
        # Concurrent limit patterns
        self.concurrent_patterns = [
            r"concurrent.*limit.*exceeded",
            r"too.*many.*concurrent.*requests",
            r"max.*concurrent.*requests",
            r"connection.*limit.*exceeded",
            r"simultaneous.*limit.*exceeded"
        ]
        
        # Bandwidth limit patterns
        self.bandwidth_patterns = [
            r"bandwidth.*limit.*exceeded",
            r"data.*limit.*exceeded",
            r"size.*limit.*exceeded",
            r"payload.*too.*large",
            r"request.*too.*large",
            r"413.*payload.*too.*large"
        ]
        
        # Compile regex patterns
        self.compiled_http_429 = [re.compile(pattern, re.IGNORECASE) for pattern in self.http_429_patterns]
        self.compiled_time_based = [re.compile(pattern, re.IGNORECASE) for pattern in self.time_based_patterns]
        self.compiled_quota = [re.compile(pattern, re.IGNORECASE) for pattern in self.quota_patterns]
        self.compiled_concurrent = [re.compile(pattern, re.IGNORECASE) for pattern in self.concurrent_patterns]
        self.compiled_bandwidth = [re.compile(pattern, re.IGNORECASE) for pattern in self.bandwidth_patterns]
    
    def detect_rate_limit(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[RateLimitInfo]:
        """
        Detect if an error indicates rate limiting.
        
        Args:
            error: The exception to analyze
            context: Additional context information
            
        Returns:
            RateLimitInfo if rate limiting detected, None otherwise
        """
        error_message = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Check HTTP status code
        status_code = self._extract_status_code(error, context)
        
        # Check for HTTP 429
        if status_code == 429 or self._matches_patterns(error_message, self.compiled_http_429):
            return self._create_rate_limit_info(
                RateLimitType.HTTP_429,
                error,
                context,
                status_code
            )
        
        # Check for time-based rate limiting
        if self._matches_patterns(error_message, self.compiled_time_based):
            return self._create_rate_limit_info(
                RateLimitType.TIME_BASED,
                error,
                context,
                status_code
            )
        
        # Check for quota exceeded
        if self._matches_patterns(error_message, self.compiled_quota):
            return self._create_rate_limit_info(
                RateLimitType.QUOTA_EXCEEDED,
                error,
                context,
                status_code
            )
        
        # Check for concurrent limits
        if self._matches_patterns(error_message, self.compiled_concurrent):
            return self._create_rate_limit_info(
                RateLimitType.CONCURRENT_LIMIT,
                error,
                context,
                status_code
            )
        
        # Check for bandwidth limits
        if self._matches_patterns(error_message, self.compiled_bandwidth):
            return self._create_rate_limit_info(
                RateLimitType.BANDWIDTH_LIMIT,
                error,
                context,
                status_code
            )
        
        return None
    
    def _matches_patterns(self, text: str, patterns: List[re.Pattern]) -> bool:
        """Check if text matches any of the patterns."""
        return any(pattern.search(text) for pattern in patterns)
    
    def _extract_status_code(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> Optional[int]:
        """Extract HTTP status code from error or context."""
        # Check context first
        if context:
            status_code = context.get("status_code")
            if status_code is not None:
                return int(status_code)
        
        # Check error message for status codes
        status_match = re.search(r'\b([4-5]\d{2})\b', str(error))
        if status_match:
            return int(status_match.group(1))
        
        # Check error attributes
        if hasattr(error, 'status_code'):
            return error.status_code
        if hasattr(error, 'code'):
            return error.code
        
        return None
    
    def _create_rate_limit_info(
        self,
        limit_type: RateLimitType,
        error: Exception,
        context: Optional[Dict[str, Any]],
        status_code: Optional[int]
    ) -> RateLimitInfo:
        """Create RateLimitInfo from detected rate limit."""
        error_message = str(error)
        
        # Extract retry-after header if available
        retry_after = self._extract_retry_after(error, context)
        
        # Extract limit values from error message
        limit_value = self._extract_limit_value(error_message)
        window_seconds = self._extract_window_seconds(error_message)
        
        # Determine strategy
        strategy = self._determine_strategy(limit_type, retry_after, window_seconds)
        
        # Calculate reset time
        reset_time = None
        if retry_after:
            reset_time = datetime.utcnow() + timedelta(seconds=retry_after)
        elif window_seconds:
            reset_time = datetime.utcnow() + timedelta(seconds=window_seconds)
        
        return RateLimitInfo(
            limit_type=limit_type,
            strategy=strategy,
            limit_value=limit_value,
            window_seconds=window_seconds,
            retry_after=retry_after,
            reset_time=reset_time,
            context={
                "error_message": error_message,
                "status_code": status_code,
                "error_type": type(error).__name__,
                **(context or {})
            }
        )
    
    def _extract_retry_after(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> Optional[int]:
        """Extract retry-after value from error or context."""
        # Check context for retry-after header
        if context:
            retry_after = context.get("retry_after")
            if retry_after is not None:
                return int(retry_after)
            
            headers = context.get("headers", {})
            if headers and "retry-after" in headers:
                return int(headers["retry-after"])
        
        # Check error message for retry-after patterns
        error_message = str(error).lower()
        
        # Look for "retry after X seconds/minutes"
        retry_match = re.search(r'retry.*after.*(\d+).*second', error_message)
        if retry_match:
            return int(retry_match.group(1))
        
        retry_match = re.search(r'retry.*after.*(\d+).*minute', error_message)
        if retry_match:
            return int(retry_match.group(1)) * 60
        
        # Look for "try again in X seconds/minutes"
        retry_match = re.search(r'try.*again.*in.*(\d+).*second', error_message)
        if retry_match:
            return int(retry_match.group(1))
        
        retry_match = re.search(r'try.*again.*in.*(\d+).*minute', error_message)
        if retry_match:
            return int(retry_match.group(1)) * 60
        
        return None
    
    def _extract_limit_value(self, error_message: str) -> Optional[int]:
        """Extract limit value from error message."""
        # Look for patterns like "limit: 1000", "max 1000", etc.
        limit_match = re.search(r'limit[:\s]+(\d+)', error_message.lower())
        if limit_match:
            return int(limit_match.group(1))
        
        limit_match = re.search(r'max[:\s]+(\d+)', error_message.lower())
        if limit_match:
            return int(limit_match.group(1))
        
        return None
    
    def _extract_window_seconds(self, error_message: str) -> Optional[int]:
        """Extract time window from error message."""
        # Look for patterns like "per hour", "per day", etc.
        if "per second" in error_message:
            return 1
        elif "per minute" in error_message:
            return 60
        elif "per hour" in error_message:
            return 3600
        elif "per day" in error_message:
            return 86400
        elif "per month" in error_message:
            return 2592000  # 30 days
        
        return None
    
    def _determine_strategy(
        self,
        limit_type: RateLimitType,
        retry_after: Optional[int],
        window_seconds: Optional[int]
    ) -> RateLimitStrategy:
        """Determine the best strategy for handling rate limiting."""
        if limit_type == RateLimitType.HTTP_429:
            if retry_after and retry_after > 300:  # 5 minutes
                return RateLimitStrategy.EXPONENTIAL_BACKOFF
            else:
                return RateLimitStrategy.FIXED_DELAY
        
        elif limit_type == RateLimitType.QUOTA_EXCEEDED:
            return RateLimitStrategy.LINEAR_BACKOFF
        
        elif limit_type == RateLimitType.CONCURRENT_LIMIT:
            return RateLimitStrategy.FIXED_DELAY
        
        elif limit_type == RateLimitType.BANDWIDTH_LIMIT:
            return RateLimitStrategy.EXPONENTIAL_BACKOFF
        
        else:
            return RateLimitStrategy.ADAPTIVE_BACKOFF


class RateLimitHandler:
    """Handles rate limiting scenarios with appropriate retry strategies."""
    
    def __init__(self):
        """Initialize rate limit handler."""
        self.logger = get_logger("rate_limit_handler")
        self.detector = RateLimitDetector()
        self.active_limits: Dict[str, RateLimitInfo] = {}
    
    async def handle_rate_limit(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        policy_id: Optional[str] = None
    ) -> Tuple[bool, Optional[RetryPolicy]]:
        """
        Handle rate limiting error.
        
        Args:
            error: The error that occurred
            context: Additional context information
            policy_id: Optional policy ID to modify
            
        Returns:
            Tuple of (should_retry, modified_policy)
        """
        # Detect rate limiting
        rate_limit_info = self.detector.detect_rate_limit(error, context)
        
        if not rate_limit_info:
            return False, None
        
        # Store active rate limit
        key = self._get_limit_key(context)
        self.active_limits[key] = rate_limit_info
        
        # Log rate limiting detection
        self.logger.warning(
            f"Rate limiting detected: {rate_limit_info.limit_type.value}",
            event_type="rate_limit_detected",
            correlation_id=get_correlation_id(),
            context={
                "limit_type": rate_limit_info.limit_type.value,
                "strategy": rate_limit_info.strategy.value,
                "limit_value": rate_limit_info.limit_value,
                "retry_after": rate_limit_info.retry_after,
                "window_seconds": rate_limit_info.window_seconds
            },
            component="rate_limit_handler"
        )
        
        # Create appropriate retry policy
        retry_policy = self._create_retry_policy(rate_limit_info, policy_id)
        
        # Publish retry event
        await publish_retry_event(
            operation="rate_limit_handling",
            attempt=1,
            max_attempts=retry_policy.max_attempts,
            delay=retry_policy.base_delay,
            job_id=context.get("job_id") if context else None,
            context={
                "rate_limit_type": rate_limit_info.limit_type.value,
                "strategy": rate_limit_info.strategy.value,
                "wait_time": rate_limit_info.get_wait_time()
            },
            component="rate_limit_handler"
        )
        
        return True, retry_policy
    
    def is_rate_limited(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if currently rate limited.
        
        Args:
            context: Context information to identify the client/service
            
        Returns:
            True if currently rate limited, False otherwise
        """
        key = self._get_limit_key(context)
        rate_limit_info = self.active_limits.get(key)
        
        if not rate_limit_info:
            return False
        
        # Check if limit has expired
        if rate_limit_info.is_expired():
            del self.active_limits[key]
            return False
        
        return True
    
    def get_wait_time(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Get time to wait before next retry.
        
        Args:
            context: Context information to identify the client/service
            
        Returns:
            Time to wait in seconds
        """
        key = self._get_limit_key(context)
        rate_limit_info = self.active_limits.get(key)
        
        if not rate_limit_info:
            return 0.0
        
        # Check if limit has expired
        if rate_limit_info.is_expired():
            del self.active_limits[key]
            return 0.0
        
        return rate_limit_info.get_wait_time()
    
    def clear_rate_limit(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Clear rate limit for a context.
        
        Args:
            context: Context information to identify the client/service
            
        Returns:
            True if limit was cleared, False if not found
        """
        key = self._get_limit_key(context)
        if key in self.active_limits:
            del self.active_limits[key]
            return True
        return False
    
    def _get_limit_key(self, context: Optional[Dict[str, Any]]) -> str:
        """Get key for identifying rate limit context."""
        if not context:
            return "default"
        
        # Use combination of client ID and service ID if available
        client_id = context.get("client_id", "default")
        service_id = context.get("service_id", "default")
        endpoint = context.get("endpoint", "default")
        
        return f"{client_id}:{service_id}:{endpoint}"
    
    def _create_retry_policy(
        self,
        rate_limit_info: RateLimitInfo,
        base_policy_id: Optional[str] = None
    ) -> RetryPolicy:
        """Create retry policy based on rate limit information."""
        if rate_limit_info.strategy == RateLimitStrategy.FIXED_DELAY:
            return RetryPolicy(
                name=f"rate_limit_fixed_{rate_limit_info.limit_type.value}",
                description=f"Fixed delay retry for {rate_limit_info.limit_type.value}",
                max_attempts=5,
                base_delay=rate_limit_info.get_wait_time(),
                max_delay=rate_limit_info.get_wait_time() * 2,
                backoff_type=BackoffType.FIXED,
                jitter_type=JitterType.FULL,
                jitter_factor=0.1,
                retry_conditions=[],
                retryable_error_patterns=[r"rate.*limit", r"429", r"too.*many.*requests"]
            )
        
        elif rate_limit_info.strategy == RateLimitStrategy.LINEAR_BACKOFF:
            return RetryPolicy(
                name=f"rate_limit_linear_{rate_limit_info.limit_type.value}",
                description=f"Linear backoff retry for {rate_limit_info.limit_type.value}",
                max_attempts=8,
                base_delay=max(1.0, rate_limit_info.get_wait_time() / 4),
                max_delay=rate_limit_info.get_wait_time() * 3,
                multiplier=1.5,
                backoff_type=BackoffType.LINEAR,
                jitter_type=JitterType.EQUAL,
                jitter_factor=0.2,
                retry_conditions=[],
                retryable_error_patterns=[r"rate.*limit", r"429", r"too.*many.*requests"]
            )
        
        elif rate_limit_info.strategy == RateLimitStrategy.EXPONENTIAL_BACKOFF:
            return RetryPolicy(
                name=f"rate_limit_exponential_{rate_limit_info.limit_type.value}",
                description=f"Exponential backoff retry for {rate_limit_info.limit_type.value}",
                max_attempts=10,
                base_delay=max(1.0, rate_limit_info.get_wait_time() / 8),
                max_delay=rate_limit_info.get_wait_time() * 5,
                multiplier=2.0,
                backoff_type=BackoffType.EXPONENTIAL_WITH_JITTER,
                jitter_type=JitterType.FULL,
                jitter_factor=0.3,
                retry_conditions=[],
                retryable_error_patterns=[r"rate.*limit", r"429", r"too.*many.*requests"]
            )
        
        else:  # ADAPTIVE_BACKOFF
            return RetryPolicy(
                name=f"rate_limit_adaptive_{rate_limit_info.limit_type.value}",
                description=f"Adaptive backoff retry for {rate_limit_info.limit_type.value}",
                max_attempts=12,
                base_delay=max(1.0, rate_limit_info.get_wait_time() / 6),
                max_delay=rate_limit_info.get_wait_time() * 4,
                multiplier=1.8,
                backoff_type=BackoffType.EXPONENTIAL_WITH_JITTER,
                jitter_type=JitterType.FULL,
                jitter_factor=0.25,
                retry_conditions=[],
                retryable_error_patterns=[r"rate.*limit", r"429", r"too.*many.*requests"]
            )
    
    def get_active_limits(self) -> Dict[str, Dict[str, Any]]:
        """Get all active rate limits."""
        return {
            key: {
                "limit_type": info.limit_type.value,
                "strategy": info.strategy.value,
                "limit_value": info.limit_value,
                "window_seconds": info.window_seconds,
                "retry_after": info.retry_after,
                "wait_time": info.get_wait_time(),
                "detected_at": info.detected_at.isoformat(),
                "reset_time": info.reset_time.isoformat() if info.reset_time else None,
                "is_expired": info.is_expired()
            }
            for key, info in self.active_limits.items()
        }


# Global rate limit handler instance
_rate_limit_handler = RateLimitHandler()


def get_rate_limit_handler() -> RateLimitHandler:
    """Get the global rate limit handler instance."""
    return _rate_limit_handler


async def handle_rate_limit(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    policy_id: Optional[str] = None
) -> Tuple[bool, Optional[RetryPolicy]]:
    """Handle rate limiting using the global handler."""
    return await _rate_limit_handler.handle_rate_limit(error, context, policy_id)


def is_rate_limited(context: Optional[Dict[str, Any]] = None) -> bool:
    """Check if currently rate limited using the global handler."""
    return _rate_limit_handler.is_rate_limited(context)


def get_rate_limit_wait_time(context: Optional[Dict[str, Any]] = None) -> float:
    """Get time to wait before next retry using the global handler."""
    return _rate_limit_handler.get_wait_time(context)
