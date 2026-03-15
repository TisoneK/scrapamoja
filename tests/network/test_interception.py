"""Tests for network interception module.

Tests for SCR-002 - Network Response Interception.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.network.interception import (
    InterceptionConfig,
    InterceptedResponse,
    NetworkListener,
    create_network_error,
)
from src.network.errors import Retryable


class TestInterceptionConfig:
    """Tests for InterceptionConfig."""

    def test_default_config_matches_all_urls(self):
        """Default config with no patterns should match all URLs."""
        config = InterceptionConfig()
        assert config.matches("https://example.com/api/data")
        assert config.matches("https://other.com/anything")

    def test_config_with_patterns_matches(self):
        """Config with patterns should match matching URLs."""
        config = InterceptionConfig(
            url_patterns=[r".*api.*\.json$", r".*\.php$"]
        )
        assert config.matches("https://example.com/api/data.json")
        assert config.matches("https://example.com/endpoint.php")
        assert not config.matches("https://example.com/api/data.xml")
        assert not config.matches("https://example.com/page.html")

    def test_config_compiles_patterns(self):
        """Config should compile regex patterns on init."""
        config = InterceptionConfig(url_patterns=[r"^https://api\..+"])
        assert len(config._compiled_patterns) == 1
        assert config._compiled_patterns[0].pattern == r"^https://api\..+"

    def test_empty_patterns_list_matches_all(self):
        """Empty patterns list should match all URLs."""
        config = InterceptionConfig(url_patterns=[])
        assert config.matches("https://example.com/any")

    def test_capture_settings(self):
        """Config should store capture settings."""
        config = InterceptionConfig(
            url_patterns=[r".*api.*"],
            capture_body=False,
            capture_headers=True,
        )
        assert config.capture_body is False
        assert config.capture_headers is True


class TestInterceptedResponse:
    """Tests for InterceptedResponse dataclass."""

    def test_create_response(self):
        """Test creating an InterceptedResponse."""
        response = InterceptedResponse(
            url="https://example.com/api/data",
            status=200,
            headers={"content-type": "application/json"},
            raw_bytes=b'{"key": "value"}',
        )
        assert response.url == "https://example.com/api/data"
        assert response.status == 200
        assert response.headers == {"content-type": "application/json"}
        assert response.raw_bytes == b'{"key": "value"}'

    def test_response_with_string_body(self):
        """Test creating response with string body."""
        response = InterceptedResponse(
            url="https://example.com/api/data",
            status=200,
            headers={},
            raw_bytes=b"string response",
        )
        assert response.raw_bytes == b"string response"

    def test_response_with_timing(self):
        """Test creating response with timing."""
        response = InterceptedResponse(
            url="https://example.com/api/data",
            status=200,
            headers={},
            raw_bytes=b"response body",
        )
        # Note: timing is not supported in the new CapturedResponse model
        # This test is kept for backward compatibility but timing is not stored
        assert response.url == "https://example.com/api/data"
        assert response.status == 200


class TestNetworkListener:
    """Tests for NetworkListener."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return InterceptionConfig(
            url_patterns=[r".*api.*\.json$"],
            capture_body=True,
            capture_headers=True,
        )

    @pytest.fixture
    def listener(self, config):
        """Create listener instance."""
        return NetworkListener(config)

    @pytest.mark.asyncio
    async def test_attach_to_page(self, listener):
        """Test attaching listener to Playwright page."""
        mock_page = MagicMock()
        mock_handler = MagicMock()
        mock_page.on = mock_handler

        await listener.attach(mock_page)

        # Verify handler was registered for 'response' event
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        assert call_args[0][0] == "response"  # Event name
        assert callable(call_args[0][1])  # Callback is callable
        assert listener._page == mock_page

    @pytest.mark.asyncio
    async def test_get_captured_responses_empty(self, listener):
        """Test getting captured responses when none captured."""
        responses = listener.get_captured_responses()
        assert responses == []

    @pytest.mark.asyncio
    async def test_clear_captured_responses(self, listener):
        """Test clearing captured responses."""
        # Manually add a response
        listener._captured_responses.append(
            InterceptedResponse(
                url="https://example.com/api",
                status=200,
                headers={},
                raw_bytes=b"response body",
            )
        )
        assert len(listener.get_captured_responses()) == 1

        listener.clear_captured_responses()
        assert listener.get_captured_responses() == []

    @pytest.mark.asyncio
    async def test_detach(self, listener):
        """Test detaching listener."""
        mock_page = MagicMock()
        await listener.attach(mock_page)

        await listener.detach()

        assert listener._page is None
        assert listener._captured_responses == []


class TestCreateNetworkError:
    """Tests for create_network_error helper."""

    def test_create_basic_error(self):
        """Test creating basic network error."""
        error = create_network_error(
            operation="fetch",
            detail="Connection refused",
        )
        assert error.module == "interception"
        assert error.operation == "fetch"
        assert error.detail == "Connection refused"
        assert error.url is None
        assert error.status_code is None
        assert error.retryable == Retryable.TERMINAL

    def test_create_error_with_url(self):
        """Test creating error with URL."""
        error = create_network_error(
            operation="fetch",
            detail="Not found",
            url="https://example.com/api",
            status_code=404,
        )
        assert error.url == "https://example.com/api"
        assert error.status_code == 404

    def test_create_retryable_error(self):
        """Test creating retryable error."""
        error = create_network_error(
            operation="fetch",
            detail="Timeout",
            retryable=Retryable.RETRYABLE,
        )
        assert error.retryable == Retryable.RETRYABLE

    def test_create_error_with_partial_data(self):
        """Test creating error with partial data."""
        error = create_network_error(
            operation="fetch",
            detail="Connection lost",
            partial_data={"partial": "data"},
        )
        assert error.partial_data == {"partial": "data"}
