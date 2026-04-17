"""
Synchronous adapter for the AdaptiveAPIClient.

This module provides a synchronous wrapper around the async AdaptiveAPIClient
for use in contexts where async/await is not available.

Story: 4-1 - Adaptive REST API Integration
Story: 4-2 - Service Unavailability Handling
"""

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type

import httpx


# Default configuration values (per NFR4 and NFR5)
DEFAULT_TIMEOUT_SECONDS: float = 30.0
DEFAULT_CONNECT_TIMEOUT: float = 10.0
DEFAULT_POOL_LIMITS: httpx.Limits = httpx.Limits(
    max_keepalive_connections=20,
    max_connections=100,
    keepalive_expiry=30.0,
)

# Service availability configuration (Story 4-2)
DEFAULT_RECOVERY_TIMEOUT_SECONDS: float = 60.0
DEFAULT_CIRCUIT_BREAKER_THRESHOLD: int = 3
DEFAULT_RETRY_BACKOFF_FACTOR: float = 2.0


class ServiceState(Enum):
    """Service connection state for graceful degradation."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RECOVERING = "recovering"


@dataclass
class ServiceAvailability:
    """Tracks service availability state for graceful degradation."""

    state: ServiceState = ServiceState.AVAILABLE
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    recovery_attempt_count: int = 0

    def record_success(self) -> None:
        """Record a successful API call."""
        self.state = ServiceState.AVAILABLE
        self.consecutive_failures = 0
        self.last_success_time = datetime.now(timezone.utc)
        self.recovery_attempt_count = 0

    def record_failure(self, threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD) -> None:
        """Record a failed API call."""
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.consecutive_failures >= threshold:
            self.state = ServiceState.UNAVAILABLE

    def should_attempt_recovery(
        self, recovery_timeout: float = DEFAULT_RECOVERY_TIMEOUT_SECONDS
    ) -> bool:
        """Check if we should attempt to recover from unavailability."""
        if self.state != ServiceState.UNAVAILABLE:
            return False

        # If last_failure_time is None but we're UNAVAILABLE, don't auto-recover
        # This prevents immediate recovery after manual state setting without failures
        if self.last_failure_time is None:
            return False

        time_since_failure = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return time_since_failure >= recovery_timeout

    def start_recovery(self) -> None:
        """Mark service as recovering."""
        self.state = ServiceState.RECOVERING
        self.recovery_attempt_count += 1

    def reset(self) -> None:
        """Reset availability state."""
        self.state = ServiceState.AVAILABLE
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.recovery_attempt_count = 0


@dataclass
class AlternativeSelector:
    """Represents an alternative selector from the API (sync version)."""

    selector: str
    strategy: str
    confidence: float
    reason: Optional[str] = None


@dataclass
class SyncAPIResponse:
    """Response from the adaptive API (sync version)."""

    success: bool
    selector_id: str
    page_url: str
    alternatives: List[AlternativeSelector]
    error: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class SyncAdaptiveAPIClient:
    """
    Synchronous HTTP client for the adaptive selector API.

    This client wraps the async AdaptiveAPIClient functionality in a synchronous
    interface using threading. It's designed for use cases where async/await
    is not available.

    The client implements:
    - Singleton pattern for connection pooling (per NFR5)
    - Configurable timeout (default 30s per NFR4)
    - Graceful handling of empty alternatives
    - Service availability tracking with circuit breaker pattern (Story 4-2)
    - Retry logic with exponential backoff (Story 4-2)
    - Automatic service recovery detection (Story 4-2)

    Usage:
        client = SyncAdaptiveAPIClient()
        alternatives = client.get_alternatives("selector_id", "https://example.com")
    """

    _instance: Optional["SyncAdaptiveAPIClient"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        max_retries: int = 3,
        pool_limits: Optional[httpx.Limits] = None,
        recovery_timeout: float = DEFAULT_RECOVERY_TIMEOUT_SECONDS,
        circuit_breaker_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        retry_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR,
    ) -> None:
        """
        Initialize the synchronous AdaptiveAPIClient.

        Args:
            base_url: Base URL of the adaptive API (default: http://localhost:8000)
            timeout: Default request timeout in seconds (default: 30s per NFR4)
            connect_timeout: Connection timeout in seconds (default: 10s)
            max_retries: Maximum number of retry attempts (default: 3)
            pool_limits: Connection pool limits (default: 20 keepalive, 100 max)
            recovery_timeout: Time in seconds to wait before attempting recovery (default: 60s)
            circuit_breaker_threshold: Number of consecutive failures before marking unavailable (default: 3)
            retry_backoff_factor: Exponential backoff factor for retries (default: 2.0)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self._pool_limits = pool_limits
        self._client: Optional[httpx.Client] = None
        self._logger = self._get_logger()

        # Service availability tracking (Story 4-2)
        self._availability = ServiceAvailability()
        self.recovery_timeout = recovery_timeout
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.retry_backoff_factor = retry_backoff_factor

    @classmethod
    def get_instance(
        cls,
        base_url: str = "http://localhost:8000",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        max_retries: int = 3,
        pool_limits: Optional[httpx.Limits] = None,
        recovery_timeout: float = DEFAULT_RECOVERY_TIMEOUT_SECONDS,
        circuit_breaker_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        retry_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR,
    ) -> "SyncAdaptiveAPIClient":
        """
        Get or create the singleton instance of SyncAdaptiveAPIClient.

        This ensures a single connection pool is shared across all usage.

        Args:
            base_url: Base URL of the adaptive API
            timeout: Default request timeout in seconds
            connect_timeout: Connection timeout in seconds
            max_retries: Maximum number of retry attempts
            pool_limits: Connection pool limits
            recovery_timeout: Time in seconds to wait before attempting recovery
            circuit_breaker_threshold: Number of consecutive failures before marking unavailable
            retry_backoff_factor: Exponential backoff factor for retries

        Returns:
            The singleton SyncAdaptiveAPIClient instance
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(
                    base_url=base_url,
                    timeout=timeout,
                    connect_timeout=connect_timeout,
                    max_retries=max_retries,
                    pool_limits=pool_limits,
                    recovery_timeout=recovery_timeout,
                    circuit_breaker_threshold=circuit_breaker_threshold,
                    retry_backoff_factor=retry_backoff_factor,
                )
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        with cls._lock:
            cls._instance = None

    def _get_logger(self) -> Any:
        """Get structured logger for API operations."""
        try:
            from src.observability.logger import get_logger

            return get_logger("sync_adaptive_api_client")
        except ImportError:
            import logging

            return logging.getLogger("sync_adaptive_api_client")

    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        return f"{self.base_url}{path}"

    def _get_client(self) -> httpx.Client:
        """
        Get or create the synchronous HTTP client with connection pooling.

        Returns:
            Configured httpx.Client with connection pooling
        """
        if self._client is None:
            pool_cfg = self._pool_limits or DEFAULT_POOL_LIMITS
            self._client = httpx.Client(
                limits=pool_cfg,
                timeout=httpx.Timeout(
                    connect=self.connect_timeout,
                    read=self.timeout,
                    write=self.timeout,
                    pool=self.timeout,
                ),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "SyncAdaptiveAPIClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def get_alternatives(
        self,
        selector_id: str,
        page_url: str,
    ) -> SyncAPIResponse:
        """
        Get alternative selectors from the adaptive API (synchronous).

        This is the main method for AC1: Given a failed primary selector,
        when calling the adaptive REST API, a request is sent with selector_id
        and page_url, and alternative selectors are returned if available.

        This method implements:
        - Service availability detection (Story 4-2 Task 1)
        - Graceful degradation when service is unavailable (Story 4-2 Task 2)
        - Timeout handling with diagnostics (Story 4-2 Task 3)
        - Retry logic with exponential backoff (Story 4-2 Task 4)
        - Automatic recovery detection (Story 4-2 Task 5)

        Args:
            selector_id: The ID of the selector that failed
            page_url: The URL of the page where the selector failed

        Returns:
            SyncAPIResponse containing alternatives or empty list (graceful degradation)
        """
        # AC1: Check service availability first
        if not self.is_service_available():
            state = self.get_service_state()

            # AC4: If recovering, attempt the request anyway
            if state == ServiceState.RECOVERING:
                self._logger.info(
                    "sync_adaptive_api_recovering_attempt",
                    extra={
                        "selector_id": selector_id,
                        "page_url": page_url,
                        "recovery_attempt": self._availability.recovery_attempt_count,
                    },
                )
            else:
                # AC1: Service is unavailable - log warning and return empty response
                self._logger.warning(
                    "sync_adaptive_api_service_unavailable",
                    extra={
                        "selector_id": selector_id,
                        "page_url": page_url,
                        "service_state": state.value,
                        "consecutive_failures": self._availability.consecutive_failures,
                        "last_failure": (
                            self._availability.last_failure_time.isoformat()
                            if self._availability.last_failure_time
                            else None
                        ),
                    },
                )
                # Return empty response for graceful degradation
                return SyncAPIResponse(
                    success=False,
                    selector_id=selector_id,
                    page_url=page_url,
                    alternatives=[],
                    error="Adaptive service unavailable - continuing with primary selectors",
                    timestamp=datetime.now(timezone.utc),
                )

        params = {
            "selector_id": selector_id,
            "page_url": page_url,
        }

        self._logger.info(
            "sync_adaptive_api_request",
            extra={
                "selector_id": selector_id,
                "page_url": page_url,
                "endpoint": "/api/alternatives",
                "service_state": self.get_service_state().value,
            },
        )

        try:
            # Use retry logic with exponential backoff (AC3)
            response = self._make_request_with_retry(
                "GET",
                self._build_url("/api/alternatives"),
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            # Parse alternatives (AC3: Handle empty alternatives gracefully)
            alternatives: List[AlternativeSelector] = []
            if data.get("alternatives"):
                for alt in data["alternatives"]:
                    alternatives.append(
                        AlternativeSelector(
                            selector=alt.get("selector", ""),
                            strategy=alt.get("strategy", "unknown"),
                            confidence=alt.get("confidence", 0.0),
                            reason=alt.get("reason"),
                        )
                    )

            api_response = SyncAPIResponse(
                success=True,
                selector_id=selector_id,
                page_url=page_url,
                alternatives=alternatives,
                timestamp=datetime.now(timezone.utc),
            )

            self._logger.info(
                "sync_adaptive_api_response",
                extra={
                    "selector_id": selector_id,
                    "alternatives_count": len(alternatives),
                    "success": True,
                },
            )

            return api_response

        except httpx.TimeoutException as e:
            # AC2: Log timeout diagnostics with selector_id and page_url
            self._logger.warning(
                "sync_adaptive_api_timeout",
                extra={
                    "selector_id": selector_id,
                    "page_url": page_url,
                    "timeout": self.timeout,
                    "error": str(e),
                },
            )
            # Track failure for circuit breaker
            self._availability.record_failure(self.circuit_breaker_threshold)
            # Return empty response instead of raising (graceful degradation)
            return SyncAPIResponse(
                success=False,
                selector_id=selector_id,
                page_url=page_url,
                alternatives=[],
                error=f"Timeout after {self.timeout}s",
                timestamp=datetime.now(timezone.utc),
            )

        except httpx.HTTPStatusError as e:
            self._logger.error(
                "sync_adaptive_api_http_error",
                extra={
                    "selector_id": selector_id,
                    "page_url": page_url,
                    "status_code": e.response.status_code,
                    "error": str(e),
                },
            )
            # Track failure for circuit breaker (only for 5xx errors)
            if e.response.status_code >= 500:
                self._availability.record_failure(self.circuit_breaker_threshold)
            # Return empty response instead of raising (graceful degradation)
            return SyncAPIResponse(
                success=False,
                selector_id=selector_id,
                page_url=page_url,
                alternatives=[],
                error=f"HTTP {e.response.status_code}: {str(e)}",
                timestamp=datetime.now(timezone.utc),
            )

        except httpx.ConnectError as e:
            # AC1: Handle complete service unavailability - connection error
            self._logger.warning(
                "sync_adaptive_api_connection_error",
                extra={
                    "selector_id": selector_id,
                    "page_url": page_url,
                    "error": str(e),
                },
            )
            # Track failure for circuit breaker
            self._availability.record_failure(self.circuit_breaker_threshold)
            # Return empty response for graceful degradation
            return SyncAPIResponse(
                success=False,
                selector_id=selector_id,
                page_url=page_url,
                alternatives=[],
                error=f"Connection error: {str(e)}",
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as e:
            self._logger.error(
                "sync_adaptive_api_error",
                extra={
                    "selector_id": selector_id,
                    "page_url": page_url,
                    "error": str(e),
                },
            )
            # Track failure for circuit breaker
            self._availability.record_failure(self.circuit_breaker_threshold)
            # Return empty response instead of raising (graceful degradation)
            return SyncAPIResponse(
                success=False,
                selector_id=selector_id,
                page_url=page_url,
                alternatives=[],
                error=str(e),
                timestamp=datetime.now(timezone.utc),
            )

    def health_check(self) -> bool:
        """
        Check if the adaptive API is available (synchronous).

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            client = self._get_client()
            response = client.get(self._build_url("/health"))
            is_healthy = response.status_code == 200

            if is_healthy:
                self._availability.record_success()
                self._logger.info(
                    "sync_adaptive_api_healthy",
                    extra={"base_url": self.base_url},
                )
            else:
                self._availability.record_failure(self.circuit_breaker_threshold)
                self._logger.warning(
                    "sync_adaptive_api_unhealthy",
                    extra={
                        "base_url": self.base_url,
                        "status_code": response.status_code,
                    },
                )

            return is_healthy
        except Exception as e:
            self._availability.record_failure(self.circuit_breaker_threshold)
            self._logger.warning(
                "sync_adaptive_api_health_check_failed",
                extra={
                    "base_url": self.base_url,
                    "error": str(e),
                },
            )
            return False

    def get_service_state(self) -> ServiceState:
        """
        Get the current service availability state.

        Returns:
            ServiceState enum indicating current state
        """
        # Check if we should attempt recovery
        if (
            self._availability.state == ServiceState.UNAVAILABLE
            and self._availability.should_attempt_recovery(self.recovery_timeout)
        ):
            self._availability.start_recovery()

        return self._availability.state

    def is_service_available(self) -> bool:
        """
        Check if the service is available for requests.

        Returns:
            True if service is available or recovering, False if unavailable
        """
        state = self.get_service_state()
        return state in (ServiceState.AVAILABLE, ServiceState.RECOVERING)

    def _make_request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """
        Make an HTTP request with retry logic and exponential backoff.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            **kwargs: Additional arguments to pass to httpx request

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPError: If all retries fail
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                client = self._get_client()
                response = client.request(method, url, **kwargs)

                # On success, record it and return
                self._availability.record_success()
                return response

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                self._availability.record_failure(self.circuit_breaker_threshold)

                # Log the failure
                self._logger.warning(
                    "sync_adaptive_api_request_failed",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": self.max_retries,
                        "error": str(e),
                    },
                )

                # If this is the last attempt, don't wait
                if attempt >= self.max_retries - 1:
                    break

                # Calculate backoff time with exponential backoff
                backoff_time = self.retry_backoff_factor**attempt
                self._logger.info(
                    "sync_adaptive_api_retry_backoff",
                    extra={
                        "attempt": attempt + 1,
                        "backoff_seconds": backoff_time,
                    },
                )
                time.sleep(backoff_time)

            except httpx.HTTPStatusError as e:
                # For 5xx errors, retry; for 4xx errors, don't retry
                if e.response.status_code >= 500:
                    last_exception = e
                    self._availability.record_failure(self.circuit_breaker_threshold)

                    if attempt >= self.max_retries - 1:
                        break

                    backoff_time = self.retry_backoff_factor**attempt
                    time.sleep(backoff_time)
                else:
                    # Don't retry client errors
                    raise

        # All retries failed - raise the last exception
        if last_exception:
            raise last_exception

        raise httpx.HTTPError("All retries failed")

    def get_availability_info(self) -> Dict[str, Any]:
        """
        Get service availability information for diagnostics.

        Returns:
            Dictionary with availability state and diagnostic information
        """
        return {
            "state": self._availability.state.value,
            "consecutive_failures": self._availability.consecutive_failures,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
            "recovery_timeout": self.recovery_timeout,
            "recovery_attempt_count": self._availability.recovery_attempt_count,
            "last_failure_time": (
                self._availability.last_failure_time.isoformat()
                if self._availability.last_failure_time
                else None
            ),
            "last_success_time": (
                self._availability.last_success_time.isoformat()
                if self._availability.last_success_time
                else None
            ),
            "should_attempt_recovery": self._availability.should_attempt_recovery(
                self.recovery_timeout
            ),
        }

    def reset_availability(self) -> None:
        """
        Reset service availability state (useful for testing or manual recovery).
        """
        self._availability.reset()
        self._logger.info("sync_adaptive_api_availability_reset")


class SyncAdaptiveAPIClientConfig:
    """
    Configuration dataclass for SyncAdaptiveAPIClient.

    This provides a clean way to configure the sync client with all options.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        max_retries: int = 3,
        max_keepalive_connections: int = 20,
        max_connections: int = 100,
        keepalive_expiry: float = 30.0,
        recovery_timeout: float = DEFAULT_RECOVERY_TIMEOUT_SECONDS,
        circuit_breaker_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        retry_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR,
    ) -> None:
        """Initialize configuration with defaults."""
        self.base_url = base_url
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self.max_keepalive_connections = max_keepalive_connections
        self.max_connections = max_connections
        self.keepalive_expiry = keepalive_expiry
        self.recovery_timeout = recovery_timeout
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.retry_backoff_factor = retry_backoff_factor

    def to_limits(self) -> httpx.Limits:
        """Convert to httpx.Limits for connection pooling."""
        return httpx.Limits(
            max_keepalive_connections=self.max_keepalive_connections,
            max_connections=self.max_connections,
            keepalive_expiry=self.keepalive_expiry,
        )

    def to_timeout(self) -> httpx.Timeout:
        """Convert to httpx.Timeout configuration."""
        return httpx.Timeout(
            connect=self.connect_timeout,
            read=self.timeout,
            write=self.timeout,
            pool=self.timeout,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "connect_timeout": self.connect_timeout,
            "max_retries": self.max_retries,
            "max_keepalive_connections": self.max_keepalive_connections,
            "max_connections": self.max_connections,
            "keepalive_expiry": self.keepalive_expiry,
            "recovery_timeout": self.recovery_timeout,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
            "retry_backoff_factor": self.retry_backoff_factor,
        }
