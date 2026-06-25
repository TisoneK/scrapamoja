"""
Tests for Service Unavailability Handling (Story 4-2).

These tests validate the implementation of Story 4-2:
- Service availability detection with circuit breaker pattern
- Graceful degradation when service is unavailable
- Timeout handling with diagnostics
- Retry logic with exponential backoff
- Automatic service recovery detection

Tests cover:
- ServiceState transitions
- Circuit breaker behavior
- Retry with backoff
- Recovery detection
- Graceful degradation
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock

from src.selectors.adaptive.api_client import (
    AdaptiveAPIClient,
    AdaptiveAPIClientConfig,
    ServiceAvailability,
    ServiceState,
    DEFAULT_RECOVERY_TIMEOUT_SECONDS,
    DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
    DEFAULT_RETRY_BACKOFF_FACTOR,
)


class TestServiceAvailability:
    """Test suite for ServiceAvailability dataclass."""

    def test_initial_state_available(self):
        """Test that ServiceAvailability starts in AVAILABLE state."""
        availability = ServiceAvailability()
        assert availability.state == ServiceState.AVAILABLE
        assert availability.consecutive_failures == 0
        assert availability.last_failure_time is None
        assert availability.last_success_time is None

    def test_record_success(self):
        """Test recording a successful API call."""
        availability = ServiceAvailability()
        availability.consecutive_failures = 3
        availability.state = ServiceState.UNAVAILABLE

        availability.record_success()

        assert availability.state == ServiceState.AVAILABLE
        assert availability.consecutive_failures == 0
        assert availability.last_success_time is not None

    def test_record_failure_below_threshold(self):
        """Test recording failures below circuit breaker threshold."""
        availability = ServiceAvailability()
        threshold = DEFAULT_CIRCUIT_BREAKER_THRESHOLD

        for _ in range(threshold - 1):
            availability.record_failure(threshold)

        assert availability.state == ServiceState.AVAILABLE
        assert availability.consecutive_failures == threshold - 1

    def test_record_failure_at_threshold(self):
        """Test that failure at threshold marks service unavailable."""
        availability = ServiceAvailability()
        threshold = DEFAULT_CIRCUIT_BREAKER_THRESHOLD

        for _ in range(threshold):
            availability.record_failure(threshold)

        assert availability.state == ServiceState.UNAVAILABLE
        assert availability.consecutive_failures == threshold
        assert availability.last_failure_time is not None

    def test_should_attempt_recovery_when_available(self):
        """Test recovery check when service is available."""
        availability = ServiceAvailability()
        availability.state = ServiceState.AVAILABLE

        assert availability.should_attempt_recovery() is False

    def test_should_attempt_recovery_when_unavailable_but_timeout_not_reached(self):
        """Test recovery check when timeout not reached."""
        availability = ServiceAvailability()
        availability.state = ServiceState.UNAVAILABLE
        availability.last_failure_time = datetime.now(timezone.utc)

        # Should not attempt recovery if timeout not reached
        assert availability.should_attempt_recovery(recovery_timeout=60.0) is False

    def test_start_recovery(self):
        """Test starting recovery mode."""
        availability = ServiceAvailability()
        availability.state = ServiceState.UNAVAILABLE

        availability.start_recovery()

        assert availability.state == ServiceState.RECOVERING
        assert availability.recovery_attempt_count == 1

    def test_reset(self):
        """Test resetting availability state."""
        availability = ServiceAvailability()
        availability.state = ServiceState.UNAVAILABLE
        availability.consecutive_failures = 5
        availability.recovery_attempt_count = 3
        availability.last_failure_time = datetime.now(timezone.utc)
        availability.last_success_time = datetime.now(timezone.utc)

        availability.reset()

        assert availability.state == ServiceState.AVAILABLE
        assert availability.consecutive_failures == 0
        assert availability.last_failure_time is None
        assert availability.last_success_time is None
        assert availability.recovery_attempt_count == 0


class TestAdaptiveAPIClientAvailability:
    """Test suite for AdaptiveAPIClient service availability methods."""

    @pytest.fixture
    def client(self):
        """Create an AdaptiveAPIClient instance for testing."""
        # Reset singleton before each test
        AdaptiveAPIClient.reset_instance()
        client = AdaptiveAPIClient(
            base_url="http://localhost:8000",
            timeout=1.0,
            connect_timeout=0.5,
            max_retries=2,
            recovery_timeout=60.0,
            circuit_breaker_threshold=3,
            retry_backoff_factor=2.0,
        )
        return client

    def test_get_service_state_available(self, client):
        """Test getting service state when available."""
        state = client.get_service_state()
        assert state == ServiceState.AVAILABLE

    def test_is_service_available(self, client):
        """Test is_service_available returns True when available."""
        assert client.is_service_available() is True

    def test_get_availability_info(self, client):
        """Test getting availability info."""
        info = client.get_availability_info()

        assert "state" in info
        assert "consecutive_failures" in info
        assert "circuit_breaker_threshold" in info
        assert "recovery_timeout" in info
        assert "recovery_attempt_count" in info
        assert "last_failure_time" in info
        assert "last_success_time" in info
        assert "should_attempt_recovery" in info

    def test_reset_availability(self, client):
        """Test resetting availability state."""
        # Record some failures
        client._availability.record_failure(3)
        client._availability.record_failure(3)
        client._availability.record_failure(3)

        assert client._availability.state == ServiceState.UNAVAILABLE

        # Reset
        client.reset_availability()

        assert client._availability.state == ServiceState.AVAILABLE

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test health check when service is healthy."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await client.health_check()

            assert result is True
            assert client._availability.state == ServiceState.AVAILABLE

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check when service fails - circuit breaker opens after threshold."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            # Circuit breaker threshold is 3 - need 3 failures to open
            # First check: failure count = 1, state should still be AVAILABLE
            result = await client.health_check()
            assert result is False
            assert client._availability.state == ServiceState.AVAILABLE
            assert client._availability.consecutive_failures == 1

            # Second check: failure count = 2, state should still be AVAILABLE
            result = await client.health_check()
            assert result is False
            assert client._availability.state == ServiceState.AVAILABLE
            assert client._availability.consecutive_failures == 2

            # Third check: failure count = 3, circuit breaker should OPEN
            result = await client.health_check()
            assert result is False
            assert client._availability.state == ServiceState.UNAVAILABLE
            assert client._availability.consecutive_failures == 3

    @pytest.mark.asyncio
    async def test_health_check_exception(self, client):
        """Test health check when exception occurs."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Connection failed"))
            mock_get_client.return_value = mock_client

            result = await client.health_check()

            assert result is False


class TestAdaptiveAPIClientGracefulDegradation:
    """Test suite for graceful degradation behavior."""

    @pytest.fixture
    def client(self):
        """Create an AdaptiveAPIClient instance for testing."""
        AdaptiveAPIClient.reset_instance()
        client = AdaptiveAPIClient(
            base_url="http://localhost:8000",
            timeout=1.0,
            connect_timeout=0.5,
            max_retries=2,
            circuit_breaker_threshold=3,
        )
        return client

    @pytest.mark.asyncio
    async def test_get_alternatives_service_unavailable(self, client):
        """Test get_alternatives returns empty when service unavailable."""
        # Force service to be unavailable
        client._availability.state = ServiceState.UNAVAILABLE
        client._availability.consecutive_failures = 3

        response = await client.get_alternatives(
            selector_id="test-selector",
            page_url="https://example.com",
        )

        assert response.success is False
        assert len(response.alternatives) == 0
        assert "unavailable" in response.error.lower()

    @pytest.mark.asyncio
    async def test_get_alternatives_service_recovering(self, client):
        """Test get_alternatives attempts request when service is recovering."""
        # Force service to be recovering
        client._availability.state = ServiceState.RECOVERING
        client._availability.recovery_attempt_count = 1

        with patch.object(client, "_make_request_with_retry") as mock_retry:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"alternatives": []}
            mock_response.raise_for_status = MagicMock()
            mock_retry.return_value = mock_response

            response = await client.get_alternatives(
                selector_id="test-selector",
                page_url="https://example.com",
            )

            # Should attempt the request when recovering
            mock_retry.assert_called_once()


class TestAdaptiveAPIClientRetryLogic:
    """Test suite for retry logic with exponential backoff."""

    @pytest.fixture
    def client(self):
        """Create an AdaptiveAPIClient instance for testing."""
        AdaptiveAPIClient.reset_instance()
        client = AdaptiveAPIClient(
            base_url="http://localhost:8000",
            timeout=1.0,
            connect_timeout=0.5,
            max_retries=3,
            retry_backoff_factor=2.0,
        )
        return client

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, client):
        """Test retry logic on connection error."""
        import httpx
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Must raise httpx.ConnectError for retry logic to trigger
                raise httpx.ConnectError("Connection failed")
            # Return success on third attempt
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"alternatives": []}
            mock_response.raise_for_status = MagicMock()
            return mock_response

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_get_client.return_value = mock_client

            response = await client.get_alternatives(
                selector_id="test-selector",
                page_url="https://example.com",
            )

            assert response.success is True

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, client):
        """Test retry logic on timeout."""
        import httpx
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # Must raise httpx.TimeoutException for retry logic to trigger
                raise httpx.TimeoutException("Request timeout")
            # Return success on second attempt
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"alternatives": []}
            mock_response.raise_for_status = MagicMock()
            return mock_response

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request = mock_request
            mock_get_client.return_value = mock_client

            response = await client.get_alternatives(
                selector_id="test-selector",
                page_url="https://example.com",
            )

            assert response.success is True


class TestAdaptiveAPIClientConfig:
    """Test suite for AdaptiveAPIClientConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AdaptiveAPIClientConfig()

        assert config.base_url == "http://localhost:8000"
        assert config.timeout == 30.0
        assert config.connect_timeout == 10.0
        assert config.max_retries == 3
        assert config.recovery_timeout == DEFAULT_RECOVERY_TIMEOUT_SECONDS
        assert config.circuit_breaker_threshold == DEFAULT_CIRCUIT_BREAKER_THRESHOLD
        assert config.retry_backoff_factor == DEFAULT_RETRY_BACKOFF_FACTOR

    def test_custom_config(self):
        """Test custom configuration values."""
        config = AdaptiveAPIClientConfig(
            base_url="http://custom:9000",
            timeout=60.0,
            connect_timeout=15.0,
            max_retries=5,
            recovery_timeout=120.0,
            circuit_breaker_threshold=5,
            retry_backoff_factor=3.0,
        )

        assert config.base_url == "http://custom:9000"
        assert config.timeout == 60.0
        assert config.connect_timeout == 15.0
        assert config.max_retries == 5
        assert config.recovery_timeout == 120.0
        assert config.circuit_breaker_threshold == 5
        assert config.retry_backoff_factor == 3.0

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = AdaptiveAPIClientConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "base_url" in config_dict
        assert "timeout" in config_dict
        assert "recovery_timeout" in config_dict
        assert "circuit_breaker_threshold" in config_dict
        assert "retry_backoff_factor" in config_dict


# Run with: pytest tests/selectors/adaptive/test_service_unavailability.py -v
