"""
Performance tests for AdaptiveAPIClient.

Story: 4-1 - Adaptive REST API Integration
NFR1: Fallback resolution must complete within ≤5 seconds

Tests:
- Latency test: Verify fallback resolution ≤5s
- Timeout behavior test: Verify timeout handling
- Connection pooling test: Verify connection reuse
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.selectors.adaptive.api_client import (
    AdaptiveAPIClient,
    AdaptiveAPIClientConfig,
    AlternativeSelector,
    APIResponse,
    DEFAULT_TIMEOUT_SECONDS,
)


class TestAdaptiveAPIClientPerformance:
    """Performance tests for AdaptiveAPIClient."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_fallback_resolution_latency_under_5s(self):
        """
        Test that fallback resolution completes within 5 seconds (NFR1).

        This test verifies that when calling get_alternatives, the total
        time including API call and processing is under 5 seconds.
        """
        client = AdaptiveAPIClient(base_url="http://localhost:8000", timeout=30.0)

        # Reset singleton for test
        AdaptiveAPIClient.reset_instance()

        mock_response_data = {
            "alternatives": [
                {
                    "selector": ".primary-selector",
                    "strategy": "css",
                    "confidence": 0.95,
                },
                {
                    "selector": "//xpath/alternate",
                    "strategy": "xpath",
                    "confidence": 0.85,
                },
            ]
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            start_time = time.time()

            response = await client.get_alternatives(
                selector_id="match_overview_title",
                page_url="https://flashscore.com/match/team-vs-team",
            )

            elapsed_time = time.time() - start_time

            # NFR1: Fallback resolution must be ≤5 seconds
            assert elapsed_time <= 5.0, f"Fallback resolution took {elapsed_time:.2f}s, exceeds 5s threshold"
            assert response.success is True
            assert len(response.alternatives) == 2

        await client.close()

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_timeout_behavior(self):
        """
        Test timeout behavior when API is slow or unresponsive.

        Verifies that:
        - Timeout is properly configured
        - Graceful degradation when timeout occurs
        - Empty alternatives returned on timeout
        """
        client = AdaptiveAPIClient(base_url="http://localhost:8000", timeout=1.0)

        # Reset singleton for test
        AdaptiveAPIClient.reset_instance()

        import httpx

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            # Simulate timeout - use request method since that's what the code uses
            mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
            mock_get_client.return_value = mock_client

            response = await client.get_alternatives(
                selector_id="test_selector",
                page_url="https://example.com",
            )

            # Verify graceful degradation - empty alternatives, no exception
            assert response.success is False
            assert len(response.alternatives) == 0
            assert response.error is not None
            assert "timeout" in response.error.lower()

        await client.close()

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_connection_pooling(self):
        """
        Test that connection pooling is properly configured.

        Verifies:
        - Single client instance is reused (singleton pattern)
        - Connection limits are properly set
        """
        # Reset singleton
        AdaptiveAPIClient.reset_instance()

        # Get instance twice - should be same instance
        client1 = await AdaptiveAPIClient.get_instance(
            base_url="http://localhost:8000",
            timeout=30.0,
        )

        client2 = await AdaptiveAPIClient.get_instance(
            base_url="http://localhost:8000",
            timeout=30.0,
        )

        # Same instance due to singleton pattern
        assert client1 is client2

        # Verify connection pool settings
        assert client1.timeout == 30.0
        assert client1.connect_timeout == 10.0

        await client1.close()


class TestAdaptiveAPIClientConfig:
    """Tests for AdaptiveAPIClientConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AdaptiveAPIClientConfig()

        assert config.base_url == "http://localhost:8000"
        assert config.timeout == DEFAULT_TIMEOUT_SECONDS
        assert config.connect_timeout == 10.0
        assert config.max_keepalive_connections == 20
        assert config.max_connections == 100
        assert config.keepalive_expiry == 30.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = AdaptiveAPIClientConfig(
            base_url="https://api.example.com",
            timeout=60.0,
            connect_timeout=15.0,
            max_keepalive_connections=50,
            max_connections=200,
            keepalive_expiry=60.0,
        )

        assert config.base_url == "https://api.example.com"
        assert config.timeout == 60.0
        assert config.connect_timeout == 15.0
        assert config.max_keepalive_connections == 50
        assert config.max_connections == 200
        assert config.keepalive_expiry == 60.0

    def test_to_limits(self):
        """Test conversion to httpx.Limits."""
        config = AdaptiveAPIClientConfig(
            max_keepalive_connections=30,
            max_connections=150,
            keepalive_expiry=45.0,
        )

        limits = config.to_limits()

        assert limits.max_keepalive_connections == 30
        assert limits.max_connections == 150
        assert limits.keepalive_expiry == 45.0


class TestAlternativeSelector:
    """Tests for AlternativeSelector dataclass."""

    def test_alternative_selector_creation(self):
        """Test creating an AlternativeSelector."""
        alt = AlternativeSelector(
            selector=".primary-selector",
            strategy="css",
            confidence=0.95,
            reason="Primary selector failed",
        )

        assert alt.selector == ".primary-selector"
        assert alt.strategy == "css"
        assert alt.confidence == 0.95
        assert alt.reason == "Primary selector failed"

    def test_alternative_selector_optional_reason(self):
        """Test AlternativeSelector with optional reason."""
        alt = AlternativeSelector(
            selector=".fallback-selector",
            strategy="xpath",
            confidence=0.80,
        )

        assert alt.selector == ".fallback-selector"
        assert alt.reason is None


class TestAPIResponse:
    """Tests for APIResponse dataclass."""

    def test_api_response_creation(self):
        """Test creating an APIResponse."""
        alternatives = [
            AlternativeSelector(selector=".alt1", strategy="css", confidence=0.9),
            AlternativeSelector(selector=".alt2", strategy="xpath", confidence=0.8),
        ]

        response = APIResponse(
            success=True,
            selector_id="test_selector",
            page_url="https://example.com",
            alternatives=alternatives,
        )

        assert response.success is True
        assert response.selector_id == "test_selector"
        assert response.page_url == "https://example.com"
        assert len(response.alternatives) == 2
        assert response.timestamp is not None

    def test_api_response_empty_alternatives(self):
        """Test APIResponse with empty alternatives (AC3)."""
        response = APIResponse(
            success=False,
            selector_id="test_selector",
            page_url="https://example.com",
            alternatives=[],
            error="No alternatives available",
        )

        assert len(response.alternatives) == 0
        assert response.error == "No alternatives available"
        # No error should be raised for empty alternatives

    def test_api_response_with_error(self):
        """Test APIResponse with error information."""
        response = APIResponse(
            success=False,
            selector_id="test_selector",
            page_url="https://example.com",
            alternatives=[],
            error="HTTP 500: Internal Server Error",
        )

        assert response.success is False
        assert "500" in response.error


# Run performance benchmarks
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
