"""Unit tests for structured error handling in network module (Story 5.1).

Tests that HTTP errors are converted to structured NetworkError objects
with proper module, operation, URL, status_code, detail, and retryable fields.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from src.network.direct_api.client import AsyncHttpClient, RequestBuilder
from src.network.direct_api.prepared_request import PreparedRequest
from src.network.direct_api.concurrency import gather_requests
from src.network.errors import NetworkError, Retryable


@pytest.mark.unit
class TestRequestBuilderErrorHandling:
    """Tests for RequestBuilder error handling."""

    @pytest.mark.asyncio
    async def test_http_status_error_returns_network_error(self) -> None:
        """Test that HTTPStatusError (4xx, 5xx) returns NetworkError."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")

        # Mock httpx client to raise HTTPStatusError
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404

        error = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = error

            result = await builder.execute()

            assert isinstance(result, NetworkError)
            assert result.module == "direct_api"
            assert result.operation == "get"
            assert result.url == "https://example.com"
            assert result.status_code == 404
            assert result.detail is not None
            assert "404" in result.detail
            assert result.retryable == Retryable.TERMINAL

    @pytest.mark.asyncio
    async def test_connection_error_returns_network_error(self) -> None:
        """Test that connection errors return NetworkError with RETRYABLE."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")

        error = httpx.ConnectError("Connection failed")

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = error

            result = await builder.execute()

            assert isinstance(result, NetworkError)
            assert result.module == "direct_api"
            assert result.operation == "get"
            assert result.url == "https://example.com"
            assert result.status_code is None
            assert result.retryable == Retryable.RETRYABLE

    @pytest.mark.asyncio
    async def test_timeout_error_returns_network_error(self) -> None:
        """Test that timeout errors return NetworkError with RETRYABLE."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")

        error = httpx.TimeoutException("Request timed out")

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = error

            result = await builder.execute()

            assert isinstance(result, NetworkError)
            assert result.retryable == Retryable.RETRYABLE

    @pytest.mark.asyncio
    async def test_429_status_returns_retryable(self) -> None:
        """Test that 429 status code is classified as RETRYABLE."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429

        error = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = error

            result = await builder.execute()

            assert isinstance(result, NetworkError)
            assert result.status_code == 429
            assert result.retryable == Retryable.RETRYABLE

    @pytest.mark.asyncio
    async def test_503_status_returns_retryable(self) -> None:
        """Test that 503 status code is classified as RETRYABLE."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 503

        error = httpx.HTTPStatusError(
            "503 Service Unavailable",
            request=MagicMock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = error

            result = await builder.execute()

            assert isinstance(result, NetworkError)
            assert result.status_code == 503
            assert result.retryable == Retryable.RETRYABLE

    @pytest.mark.asyncio
    async def test_500_status_returns_terminal(self) -> None:
        """Test that 500 status code is classified as TERMINAL."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500

        error = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = error

            result = await builder.execute()

            assert isinstance(result, NetworkError)
            assert result.status_code == 500
            assert result.retryable == Retryable.TERMINAL


@pytest.mark.unit
class TestSyncErrorHandling:
    """Tests for synchronous error handling."""

    def test_sync_http_status_error_returns_network_error(self) -> None:
        """Test that HTTPStatusError in sync mode returns NetworkError."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404

        error = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = error

            result = builder.execute_sync()

            assert isinstance(result, NetworkError)
            assert result.status_code == 404


@pytest.mark.unit
class TestPreparedRequestErrorHandling:
    """Tests for PreparedRequest error handling."""

    @pytest.mark.asyncio
    async def test_prepared_request_http_error_returns_network_error(self) -> None:
        """Test that PreparedRequest returns NetworkError on HTTP errors."""
        client = AsyncHttpClient()
        prepared = PreparedRequest(
            client=client,
            method="POST",
            url="https://api.example.com/data",
            headers={"Content-Type": "application/json"},
            params={},
            auth=None,
            timeout=30.0,
            body='{"key": "value"}',
        )

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400

        error = httpx.HTTPStatusError(
            "400 Bad Request",
            request=MagicMock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = error

            result = await prepared.execute()

            assert isinstance(result, NetworkError)
            assert result.module == "direct_api"
            assert result.operation == "post"
            assert result.url == "https://api.example.com/data"
            assert result.status_code == 400


@pytest.mark.unit
class TestConcurrentErrorHandling:
    """Tests for concurrent request error handling."""

    @pytest.mark.asyncio
    async def test_gather_returns_network_error_on_failure(self) -> None:
        """Test that gather_requests returns NetworkError for failed requests."""
        client = AsyncHttpClient()

        # Create a prepared request that will fail
        prepared1 = PreparedRequest(
            client=client,
            method="GET",
            url="https://example.com/success",
            headers={},
            params={},
            auth=None,
            timeout=30.0,
            body=None,
        )
        prepared2 = PreparedRequest(
            client=client,
            method="GET",
            url="https://example.com/fail",
            headers={},
            params={},
            auth=None,
            timeout=30.0,
            body=None,
        )

        # Mock first request to succeed, second to fail
        success_response = MagicMock(spec=httpx.Response)
        success_response.status_code = 200

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500

        error = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=mock_response,
        )

        async def mock_request(*args, **kwargs):
            # Alternate between success and error
            if "success" in str(kwargs.get("url", "")):
                return success_response
            raise error

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock:
            mock.side_effect = mock_request

            results = await gather_requests(prepared1, prepared2)

            assert len(results) == 2
            # First should be response
            assert isinstance(results[0], httpx.Response)
            # Second should be NetworkError
            assert isinstance(results[1], NetworkError)
            assert results[1].status_code == 500
            assert results[1].retryable == Retryable.TERMINAL


@pytest.mark.unit
class TestErrorFields:
    """Tests for NetworkError field completeness."""

    @pytest.mark.asyncio
    async def test_error_contains_all_required_fields(self) -> None:
        """Test that NetworkError contains all required fields per AC."""
        client = AsyncHttpClient()
        builder = client.post("https://api.example.com/endpoint")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403

        error = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=mock_response,
        )

        with patch.object(client._client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = error

            result = await builder.execute()

            assert isinstance(result, NetworkError)
            # AC #1: module, operation, URL, status_code, detail
            assert result.module == "direct_api"
            assert result.operation == "post"
            assert result.url == "https://api.example.com/endpoint"
            assert result.status_code == 403
            assert result.detail is not None
            # AC #5: retryable field
            assert result.retryable is not None
            # AC #4: Can be parsed programmatically (Pydantic model)
            assert hasattr(result, "model_dump")
