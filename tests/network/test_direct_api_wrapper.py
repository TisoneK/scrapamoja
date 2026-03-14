"""Unit tests for the Direct API Python wrapper."""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.network.direct_api import DirectApi, OutputFormat, AuthConfig
from src.network.errors import NetworkError


@pytest.mark.unit
class TestDirectApiAuth:
    """Tests for authentication configuration."""

    def test_auth_bearer(self) -> None:
        """Test bearer token authentication configuration."""
        auth = DirectApi.create_auth_config(bearer="mytoken")
        assert auth.bearer == "mytoken"
        assert auth.auto_source is True

    def test_auth_basic(self) -> None:
        """Test basic authentication configuration."""
        auth = DirectApi.create_auth_config(basic=("user", "pass"))
        assert auth.basic == ("user", "pass")
        assert auth.auto_source is True

    def test_auth_cookie(self) -> None:
        """Test cookie authentication configuration."""
        auth = DirectApi.create_auth_config(cookie={"session": "abc123"})
        assert auth.cookie == {"session": "abc123"}
        assert auth.auto_source is True

    def test_auth_auto_source_disabled(self) -> None:
        """Test auto_source can be disabled."""
        auth = DirectApi.create_auth_config(bearer="mytoken", auto_source=False)
        assert auth.bearer == "mytoken"
        assert auth.auto_source is False


@pytest.mark.unit
class TestDirectApiInitialization:
    """Tests for DirectApi initialization."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        api = DirectApi()
        assert api.base_url is None
        assert api.rate_limit == 10.0
        assert api.rate_capacity == 10.0
        assert api.timeout == 30.0
        assert api.output == OutputFormat.JSON
        assert api.pretty is False
        assert api.include_headers is False
        assert api.verbose is False

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        api = DirectApi(
            base_url="https://api.example.com",
            rate_limit=5.0,
            rate_capacity=5.0,
            timeout=60.0,
            output=OutputFormat.TEXT,
            pretty=True,
            include_headers=True,
            verbose=True,
        )
        assert api.base_url == "https://api.example.com"
        assert api.rate_limit == 5.0
        assert api.rate_capacity == 5.0
        assert api.timeout == 60.0
        assert api.output == OutputFormat.TEXT
        assert api.pretty is True
        assert api.include_headers is True
        assert api.verbose is True


@pytest.mark.unit
class TestDirectApiContextManager:
    """Tests for context manager behavior."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self) -> None:
        """Test async context manager enters and exits correctly."""
        api = DirectApi()
        async with api as entered_api:
            assert entered_api is api
            assert api._client is not None

    @pytest.mark.asyncio
    async def test_without_context_manager_raises_error(self) -> None:
        """Test using methods without context manager raises error."""
        api = DirectApi()
        with pytest.raises(RuntimeError, match="must be used as an async context manager"):
            await api.get("https://example.com")


@pytest.mark.unit
class TestDirectApiOutputFormats:
    """Tests for output format handling."""

    @pytest.mark.asyncio
    async def test_output_format_json_default(self) -> None:
        """Test default JSON output format."""
        api = DirectApi(output=OutputFormat.JSON)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"key": "value"}
        mock_response.text = '{"key": "value"}'

        mock_metadata = MagicMock()
        mock_metadata.timestamp = None

        with patch.object(
            api, "_get_client", return_value=AsyncMock()
        ) as mock_get_client:
            client = mock_get_client.return_value
            client.get.return_value = MagicMock()

            # Manually test the output formatting
            api._client = client
            result = api._build_response_data(
                mock_response, mock_metadata, OutputFormat.JSON, False
            )

            assert result["status_code"] == 200
            assert result["url"] == "https://example.com"
            assert result["body"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_output_format_status(self) -> None:
        """Test status-only output format."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_metadata = MagicMock()

        api = DirectApi()
        result = api._build_response_data(
            mock_response, mock_metadata, OutputFormat.STATUS, False
        )

        assert result == 404

    @pytest.mark.asyncio
    async def test_output_format_text(self) -> None:
        """Test text output format."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "Hello World"

        mock_metadata = MagicMock()

        api = DirectApi()
        result = api._build_response_data(
            mock_response, mock_metadata, OutputFormat.TEXT, False
        )

        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_output_format_raw(self) -> None:
        """Test raw output format returns httpx.Response."""
        import httpx

        mock_response = httpx.Response(
            status_code=200,
            content=b"test content",
            request=httpx.Request("GET", "https://example.com"),
        )

        mock_metadata = MagicMock()

        api = DirectApi()
        result = api._build_response_data(
            mock_response, mock_metadata, OutputFormat.RAW, False
        )

        assert result is mock_response


@pytest.mark.unit
class TestDirectApiMethods:
    """Tests for HTTP method shortcuts."""

    @pytest.mark.asyncio
    async def test_post_with_json(self) -> None:
        """Test POST request with JSON data."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.url = "https://example.com"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"id": 123}

        mock_metadata = MagicMock()

        mock_builder = MagicMock()
        mock_builder.execute = AsyncMock(
            return_value=(mock_response, mock_metadata)
        )
        mock_builder.json = MagicMock(return_value=mock_builder)
        mock_builder.timeout = MagicMock(return_value=mock_builder)
        mock_builder.auth = MagicMock(return_value=mock_builder)
        mock_builder.header = MagicMock(return_value=mock_builder)
        mock_builder.param = MagicMock(return_value=mock_builder)

        mock_client = MagicMock()
        mock_client.post = MagicMock(return_value=mock_builder)

        api = DirectApi()
        api._client = mock_client

        result = await api.post(
            "https://example.com", json_data={"name": "test"}
        )

        mock_builder.json.assert_called_once_with({"name": "test"})
        assert result["status_code"] == 201

    @pytest.mark.asyncio
    async def test_auth_bearer_applied(self) -> None:
        """Test bearer authentication is applied to request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {}

        mock_metadata = MagicMock()

        mock_builder = MagicMock()
        mock_builder.execute = AsyncMock(
            return_value=(mock_response, mock_metadata)
        )
        mock_builder.timeout = MagicMock(return_value=mock_builder)
        mock_builder.auth = MagicMock(return_value=mock_builder)

        mock_client = MagicMock()
        mock_client.get = MagicMock(return_value=mock_builder)

        api = DirectApi(auth=DirectApi.create_auth_config(bearer="mytoken"))
        api._client = mock_client

        await api.get("https://example.com")

        mock_builder.auth.assert_called_once_with(bearer="mytoken")

    @pytest.mark.asyncio
    async def test_timeout_parameter(self) -> None:
        """Test custom timeout is applied."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {}

        mock_metadata = MagicMock()

        mock_builder = MagicMock()
        mock_builder.execute = AsyncMock(
            return_value=(mock_response, mock_metadata)
        )
        mock_builder.timeout = MagicMock(return_value=mock_builder)

        mock_client = MagicMock()
        mock_client.get = MagicMock(return_value=mock_builder)

        api = DirectApi()
        api._client = mock_client

        await api.get("https://example.com", timeout=60.0)

        mock_builder.timeout.assert_called_once_with(60.0)


@pytest.mark.unit
class TestDirectApiIncludeHeaders:
    """Tests for include_headers option."""

    @pytest.mark.asyncio
    async def test_include_headers_true(self) -> None:
        """Test including response headers in output."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.headers = {"content-type": "application/json", "x-custom": "value"}
        mock_response.json.return_value = {"data": "test"}

        mock_metadata = MagicMock()

        mock_builder = MagicMock()
        mock_builder.execute = AsyncMock(
            return_value=(mock_response, mock_metadata)
        )
        mock_builder.header = MagicMock(return_value=mock_builder)
        mock_builder.param = MagicMock(return_value=mock_builder)
        mock_builder.auth = MagicMock(return_value=mock_builder)
        mock_builder.timeout = MagicMock(return_value=mock_builder)

        mock_client = MagicMock()
        mock_client.get = MagicMock(return_value=mock_builder)

        api = DirectApi()
        api._client = mock_client

        result = await api.get("https://example.com", include_headers=True)

        assert "headers" in result
        assert result["headers"]["x-custom"] == "value"


@pytest.mark.unit
class TestDirectApiPrettyPrint:
    """Tests for pretty print option."""

    @pytest.mark.asyncio
    async def test_pretty_print_json(self) -> None:
        """Test pretty print affects JSON output."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"key": "value", "nested": {"a": 1}}

        mock_metadata = MagicMock()

        mock_builder = MagicMock()
        mock_builder.execute = AsyncMock(
            return_value=(mock_response, mock_metadata)
        )
        mock_builder.header = MagicMock(return_value=mock_builder)
        mock_builder.param = MagicMock(return_value=mock_builder)
        mock_builder.auth = MagicMock(return_value=mock_builder)
        mock_builder.timeout = MagicMock(return_value=mock_builder)

        mock_client = MagicMock()
        mock_client.get = MagicMock(return_value=mock_builder)

        api = DirectApi()
        api._client = mock_client

        result = await api.get("https://example.com", pretty=True)

        # With pretty=True, the response should still contain the data
        assert result["body"] == {"key": "value", "nested": {"a": 1}}


@pytest.mark.unit
class TestDirectApiErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_network_error_returned(self) -> None:
        """Test NetworkError is returned on failed requests."""
        error = NetworkError(
            module="direct_api",
            operation="get",
            url="https://example.com",
            status_code=500,
            detail="Internal Server Error",
        )

        mock_builder = MagicMock()
        mock_builder.execute = AsyncMock(return_value=error)
        mock_builder.header = MagicMock(return_value=mock_builder)
        mock_builder.param = MagicMock(return_value=mock_builder)
        mock_builder.auth = MagicMock(return_value=mock_builder)
        mock_builder.timeout = MagicMock(return_value=mock_builder)

        mock_client = MagicMock()
        mock_client.get = MagicMock(return_value=mock_builder)

        api = DirectApi()
        api._client = mock_client

        result = await api.get("https://example.com")

        assert isinstance(result, NetworkError)
        assert result.status_code == 500


@pytest.mark.unit
class TestDirectApiOutputFormatEnum:
    """Tests for OutputFormat enum."""

    def test_output_format_values(self) -> None:
        """Test OutputFormat enum has correct values."""
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.TEXT.value == "text"
        assert OutputFormat.RAW.value == "raw"
        assert OutputFormat.STATUS.value == "status"
