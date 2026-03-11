"""Unit tests for the direct API HTTP client (SCR-001)."""

import asyncio

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from src.network.direct_api.client import (
    AsyncHttpClient,
    RequestBuilder,
    TokenBucket,
    RateLimiter,
    PreparedRequest,
    gather_requests,
)
from src.network.direct_api.interfaces import AuthConfig
from src.network.errors import NetworkError


@pytest.mark.unit
class TestAsyncHttpClient:
    """Tests for AsyncHttpClient class."""

    def test_get_returns_request_builder(self) -> None:
        """Test that .get() returns a RequestBuilder for chaining."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")
        assert isinstance(builder, RequestBuilder)

    def test_post_returns_request_builder(self) -> None:
        """Test that .post() returns a RequestBuilder for chaining."""
        client = AsyncHttpClient()
        builder = client.post("https://example.com")
        assert isinstance(builder, RequestBuilder)

    def test_put_returns_request_builder(self) -> None:
        """Test that .put() returns a RequestBuilder for chaining."""
        client = AsyncHttpClient()
        builder = client.put("https://example.com")
        assert isinstance(builder, RequestBuilder)

    def test_delete_returns_request_builder(self) -> None:
        """Test that .delete() returns a RequestBuilder for chaining."""
        client = AsyncHttpClient()
        builder = client.delete("https://example.com")
        assert isinstance(builder, RequestBuilder)

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Test async context manager enters and exits correctly."""
        async with AsyncHttpClient() as client:
            assert client._client is not None


@pytest.mark.unit
class TestHttpMethodVerbs:
    """Tests verifying each HTTP method sends the correct verb."""

    @pytest.mark.asyncio
    async def test_get_sends_correct_verb(self) -> None:
        """Test that GET method sends 'GET' verb."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")
        assert builder._method == "GET"

    @pytest.mark.asyncio
    async def test_post_sends_correct_verb(self) -> None:
        """Test that POST method sends 'POST' verb."""
        client = AsyncHttpClient()
        builder = client.post("https://example.com")
        assert builder._method == "POST"

    @pytest.mark.asyncio
    async def test_put_sends_correct_verb(self) -> None:
        """Test that PUT method sends 'PUT' verb."""
        client = AsyncHttpClient()
        builder = client.put("https://example.com")
        assert builder._method == "PUT"

    @pytest.mark.asyncio
    async def test_delete_sends_correct_verb(self) -> None:
        """Test that DELETE method sends 'DELETE' verb."""
        client = AsyncHttpClient()
        builder = client.delete("https://example.com")
        assert builder._method == "DELETE"


@pytest.mark.unit
class TestRequestBuilder:
    """Tests for RequestBuilder chainable interface."""

    def test_header_returns_builder(self) -> None:
        """Test that .header() returns builder for chaining."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")
        result = builder.header("Content-Type", "application/json")
        assert result is builder

    def test_param_returns_builder(self) -> None:
        """Test that .param() returns builder for chaining."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")
        result = builder.param("page", "1")
        assert result is builder

    def test_auth_bearer_returns_builder(self) -> None:
        """Test that .auth(bearer=) returns builder for chaining."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")
        result = builder.auth(bearer="my-token")
        assert result is builder

    def test_auth_basic_returns_builder(self) -> None:
        """Test that .auth(basic=) returns builder for chaining."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")
        result = builder.auth(basic=("user", "pass"))
        assert result is builder

    def test_auth_cookie_returns_builder(self) -> None:
        """Test that .auth(cookie=) returns builder for chaining.

        This is critical for SCR-007 (intercepted API mode) compatibility.
        """
        client = AsyncHttpClient()
        builder = client.get("https://example.com")
        result = builder.auth(cookie={"session": "abc123"})
        assert result is builder

    def test_timeout_returns_builder(self) -> None:
        """Test that .timeout() returns builder for chaining."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")
        result = builder.timeout(30.0)
        assert result is builder

    def test_full_chain_returns_builder(self) -> None:
        """Test full chain: .get().header().param().auth().timeout()"""
        client = AsyncHttpClient()
        builder = (
            client.get("https://example.com")
            .header("Accept", "application/json")
            .param("page", "1")
            .auth(bearer="token")
            .timeout(30.0)
        )
        assert isinstance(builder, RequestBuilder)

    def test_body_returns_builder(self) -> None:
        """Test that .body() returns builder for chaining."""
        client = AsyncHttpClient()
        builder = client.post("https://example.com")
        result = builder.body("test content")
        assert result is builder
        assert builder._body == "test content"

    def test_body_with_bytes(self) -> None:
        """Test that .body() accepts bytes content."""
        client = AsyncHttpClient()
        builder = client.post("https://example.com")
        result = builder.body(b"binary data")
        assert result is builder
        assert builder._body == b"binary data"

    def test_json_returns_builder(self) -> None:
        """Test that .json() returns builder for chaining and sets Content-Type."""
        client = AsyncHttpClient()
        builder = client.post("https://example.com")
        result = builder.json({"key": "value"})
        assert result is builder
        assert builder._body == '{"key": "value"}'
        assert builder._headers.get("Content-Type") == "application/json"

    def test_full_chain_with_body(self) -> None:
        """Test full chain with body: .post().body().header().timeout()"""
        client = AsyncHttpClient()
        builder = (
            client.post("https://example.com")
            .body("request body")
            .header("Accept", "application/json")
            .timeout(30.0)
        )
        assert isinstance(builder, RequestBuilder)
        assert builder._body == "request body"

    def test_full_chain_with_json(self) -> None:
        """Test full chain with json: .post().json().auth().timeout()"""
        client = AsyncHttpClient()
        builder = (
            client.post("https://example.com")
            .json({"name": "test", "value": 123})
            .auth(bearer="token")
            .timeout(30.0)
        )
        assert isinstance(builder, RequestBuilder)
        assert builder._headers.get("Content-Type") == "application/json"


@pytest.mark.unit
class TestAuthConfig:
    """Tests for AuthConfig class."""

    def test_apply_bearer_auth(self) -> None:
        """Test bearer token is applied to headers."""
        auth = AuthConfig(bearer="my-token")
        headers = {}
        result = auth.apply_to_headers(headers)
        assert result["Authorization"] == "Bearer my-token"

    def test_apply_basic_auth(self) -> None:
        """Test basic auth is applied to headers."""
        auth = AuthConfig(basic=("user", "pass"))
        headers = {}
        result = auth.apply_to_headers(headers)
        assert result["Authorization"].startswith("Basic ")

    def test_apply_cookie_auth(self) -> None:
        """Test cookie auth is applied to headers.

        This is critical for SCR-007 (intercepted API mode) compatibility.
        """
        auth = AuthConfig(cookie={"session": "abc123", "user": "john"})
        headers = {}
        result = auth.apply_to_headers(headers)
        assert "session=abc123" in result["Cookie"]
        assert "user=john" in result["Cookie"]


@pytest.mark.unit
class TestTokenBucket:
    """Tests for TokenBucket rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_token(self) -> None:
        """Test acquiring a token from the bucket."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        # Should not raise - just acquire a token
        await bucket.acquire()

    @pytest.mark.asyncio
    async def test_multiple_acquires(self) -> None:
        """Test multiple token acquisitions."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        for _ in range(5):
            await bucket.acquire()
        # Should complete without error


@pytest.mark.integration
class TestAsyncHttpClientIntegration:
    """Integration tests for AsyncHttpClient - these make actual HTTP requests."""

    @pytest.mark.asyncio
    async def test_get_request_to_httpbin(self) -> None:
        """Test actual GET request to httpbin.org."""
        async with AsyncHttpClient() as client:
            response = await client.get("https://httpbin.org/get").execute()
            assert response.status_code == 200
            data = response.json()
            assert "url" in data

    @pytest.mark.asyncio
    async def test_post_request_with_json(self) -> None:
        """Test POST request with JSON body."""
        async with AsyncHttpClient() as client:
            response = await client.post("https://httpbin.org/post")\
                .header("Content-Type", "application/json")\
                .param("test", "value")\
                .execute()
            assert response.status_code == 200
            data = response.json()
            assert data["headers"]["Content-Type"] == "application/json"
            assert data["args"] == {"test": "value"}

    @pytest.mark.asyncio
    async def test_bearer_auth(self) -> None:
        """Test bearer token authentication."""
        async with AsyncHttpClient() as client:
            response = await client.get("https://httpbin.org/headers")\
                .auth(bearer="test-token-123")\
                .execute()
            assert response.status_code == 200
            data = response.json()
            assert data["headers"]["Authorization"] == "Bearer test-token-123"

    @pytest.mark.asyncio
    async def test_custom_rate_limiter(self) -> None:
        """Test that custom rate limiter settings work."""
        client = AsyncHttpClient(rate_limit=5.0, rate_capacity=5.0)
        assert client._rate_limiter.default_rate == 5.0
        assert client._rate_limiter.default_capacity == 5.0


@pytest.mark.integration
class TestHttpMethodErrorHandling:
    """Integration tests for HTTP method error handling."""

    @pytest.mark.asyncio
    async def test_get_error_handling_404(self) -> None:
        """Test GET error handling for 404 response."""
        async with AsyncHttpClient() as client:
            response = await client.get("https://httpbin.org/status/404").execute()
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_post_error_handling_404(self) -> None:
        """Test POST error handling for 404 response."""
        async with AsyncHttpClient() as client:
            response = await client.post("https://httpbin.org/status/404").execute()
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_put_error_handling_404(self) -> None:
        """Test PUT error handling for 404 response."""
        async with AsyncHttpClient() as client:
            response = await client.put("https://httpbin.org/status/404").execute()
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_error_handling_404(self) -> None:
        """Test DELETE error handling for 404 response."""
        async with AsyncHttpClient() as client:
            response = await client.delete("https://httpbin.org/status/404").execute()
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_timeout_handling(self) -> None:
        """Test GET timeout handling."""
        async with AsyncHttpClient() as client:
            # Very short timeout should cause timeout error
            with pytest.raises(httpx.TimeoutException):
                await client.get("https://httpbin.org/delay/10").timeout(0.001).execute()

    @pytest.mark.asyncio
    async def test_post_error_handling_500(self) -> None:
        """Test POST error handling for 500 server error."""
        async with AsyncHttpClient() as client:
            response = await client.post("https://httpbin.org/status/500").execute()
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_put_error_handling_500(self) -> None:
        """Test PUT error handling for 500 server error."""
        async with AsyncHttpClient() as client:
            response = await client.put("https://httpbin.org/status/500").execute()
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_delete_error_handling_500(self) -> None:
        """Test DELETE error handling for 500 server error."""
        async with AsyncHttpClient() as client:
            response = await client.delete("https://httpbin.org/status/500").execute()
            assert response.status_code == 500


@pytest.mark.unit
class TestPreparedRequest:
    """Tests for PreparedRequest class."""

    def test_prepare_returns_prepared_request(self) -> None:
        """Test that .prepare() returns a PreparedRequest."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com")
        prepared = builder.prepare()
        assert isinstance(prepared, PreparedRequest)

    def test_prepare_copies_headers(self) -> None:
        """Test that .prepare() copies headers from builder."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com").header("X-Test", "value")
        prepared = builder.prepare()
        assert prepared._headers["X-Test"] == "value"

    def test_prepare_copies_params(self) -> None:
        """Test that .prepare() copies params from builder."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com").param("page", "1")
        prepared = builder.prepare()
        assert prepared._params["page"] == "1"

    def test_prepare_copies_auth(self) -> None:
        """Test that .prepare() copies auth from builder."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com").auth(bearer="token")
        prepared = builder.prepare()
        assert prepared._auth is not None
        assert prepared._auth.bearer == "token"

    def test_prepare_copies_timeout(self) -> None:
        """Test that .prepare() copies timeout from builder."""
        client = AsyncHttpClient()
        builder = client.get("https://example.com").timeout(60.0)
        prepared = builder.prepare()
        assert prepared._timeout == 60.0

    def test_prepare_copies_body(self) -> None:
        """Test that .prepare() copies body from builder."""
        client = AsyncHttpClient()
        builder = client.post("https://example.com").body("test body")
        prepared = builder.prepare()
        assert prepared._body == "test body"


@pytest.mark.unit
class TestGatherRequests:
    """Tests for gather_requests function."""

    @pytest.mark.asyncio
    async def test_gather_empty_returns_empty_list(self) -> None:
        """Test that gather with no requests returns empty list."""
        results = await gather_requests()
        assert results == []

    @pytest.mark.asyncio
    async def test_gather_single_request(self) -> None:
        """Test gather with a single prepared request."""
        client = AsyncHttpClient()
        prepared = client.get("https://example.com").prepare()

        # Mock the httpx client
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        client._client.request = AsyncMock(return_value=mock_response)

        results = await gather_requests(prepared)
        assert len(results) == 1
        assert isinstance(results[0], httpx.Response)

    @pytest.mark.asyncio
    async def test_gather_multiple_requests_same_order(self) -> None:
        """Test that gather returns results in same order as input."""
        client = AsyncHttpClient()
        prepared1 = client.get("https://example1.com").prepare()
        prepared2 = client.get("https://example2.com").prepare()
        prepared3 = client.get("https://example3.com").prepare()

        # Mock responses
        mock_response1 = MagicMock(spec=httpx.Response)
        mock_response1.status_code = 200
        mock_response2 = MagicMock(spec=httpx.Response)
        mock_response2.status_code = 201
        mock_response3 = MagicMock(spec=httpx.Response)
        mock_response3.status_code = 202

        async def mock_request(**kwargs):
            url = kwargs.get("url", "")
            if "example1" in url:
                return mock_response1
            elif "example2" in url:
                return mock_response2
            return mock_response3

        client._client.request = AsyncMock(side_effect=mock_request)

        results = await gather_requests(prepared1, prepared2, prepared3)

        assert len(results) == 3
        assert results[0].status_code == 200
        assert results[1].status_code == 201
        assert results[2].status_code == 202

    @pytest.mark.asyncio
    async def test_gather_partial_failure_returns_network_error(self) -> None:
        """Test that gather returns NetworkError for failed requests."""
        client = AsyncHttpClient()
        prepared1 = client.get("https://example1.com").prepare()
        prepared2 = client.get("https://example2.com").prepare()
        prepared3 = client.get("https://example3.com").prepare()

        # First succeeds, second fails, third succeeds
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        async def mock_request(**kwargs):
            url = kwargs.get("url", "")
            if "example2" in url:
                raise httpx.HTTPError("Connection failed")
            return mock_response

        client._client.request = AsyncMock(side_effect=mock_request)

        results = await gather_requests(prepared1, prepared2, prepared3)

        assert len(results) == 3
        assert isinstance(results[0], httpx.Response)
        assert isinstance(results[1], NetworkError)
        assert results[1].module == "direct_api"
        assert results[1].operation == "get"
        assert isinstance(results[2], httpx.Response)

    @pytest.mark.asyncio
    async def test_gather_respects_rate_limiting(self) -> None:
        """Test that gather respects per-domain rate limiting."""
        client = AsyncHttpClient(rate_limit=10.0, rate_capacity=10.0)
        prepared1 = client.get("https://example.com/page1").prepare()
        prepared2 = client.get("https://example.com/page2").prepare()

        # Mock responses
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        client._client.request = AsyncMock(return_value=mock_response)

        # Execute gather - this should work with rate limiting
        results = await gather_requests(prepared1, prepared2)

        assert len(results) == 2
        # Rate limiter should have been used
        assert client._rate_limiter._buckets.get("example.com") is not None

    @pytest.mark.asyncio
    async def test_gather_different_domains_no_rate_limit_interference(self) -> None:
        """Test that gather to different domains doesn't interfere with rate limiting."""
        client = AsyncHttpClient(rate_limit=10.0, rate_capacity=10.0)
        prepared1 = client.get("https://example1.com/").prepare()
        prepared2 = client.get("https://example2.com/").prepare()

        # Mock responses
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        client._client.request = AsyncMock(return_value=mock_response)

        results = await gather_requests(prepared1, prepared2)

        assert len(results) == 2
        # Both domains should have their own rate limiter buckets
        assert "example1.com" in client._rate_limiter._buckets
        assert "example2.com" in client._rate_limiter._buckets


@pytest.mark.unit
class TestGatherConcurrency:
    """Tests for concurrent execution behavior of gather."""

    @pytest.mark.asyncio
    async def test_gather_executes_concurrently(self) -> None:
        """Test that gather executes requests concurrently."""
        client = AsyncHttpClient()

        # Track execution order
        execution_times: list[float] = []

        async def mock_request(**kwargs):
            import time
            execution_times.append(time.monotonic())
            # Simulate some work
            await asyncio.sleep(0.1)
            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 200
            return mock_response

        client._client.request = AsyncMock(side_effect=mock_request)

        # Create 5 prepared requests
        prepared = [client.get(f"https://example{i}.com/").prepare() for i in range(5)]

        import time
        start = time.monotonic()
        results = await gather_requests(*prepared)
        elapsed = time.monotonic() - start

        # If executed concurrently: 5 requests × 0.1s each = ~0.1s total (parallel)
        # If executed sequentially: 5 requests × 0.1s each = ~0.5s total
        # We assert < 0.4s to verify concurrent execution (0.5s sequential would fail)
        assert elapsed < 0.4, f"Requests took {elapsed}s, expected < 0.4s for concurrent execution"
        assert len(results) == 5
