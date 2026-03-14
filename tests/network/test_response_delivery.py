"""Unit tests for raw response delivery (Story 4.1).

This module verifies that SCR-001 returns raw httpx.Response objects
without decoding or wrapping, allowing the calling layer to decide
how to handle the content.

AC: #1 - Given an HTTP response, When SCR-001 returns, Then the raw httpx.Response is returned
AC: #2 - Given synchronous context, When `.execute_sync()` is called, Then raw httpx.Response is returned
AC: #3 - Given prepared requests for concurrent execution, When `gather_requests()` returns, Then raw httpx.Response objects are returned
AC: #4 - Given any calling module, When they receive the response, Then they can access .content, .text, .json, .headers directly
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import httpx

from src.network.direct_api.client import AsyncHttpClient, gather_requests
from src.network.direct_api.interfaces import HttpResponseProtocol


def verify_protocol_compliance(response: httpx.Response) -> None:
    """Verify that a response object satisfies HttpResponseProtocol.
    
    This performs structural type checking to ensure the response
    has all properties required by the protocol.
    """
    # Check all required protocol properties exist and are accessible
    assert hasattr(response, "status_code"), "Missing: status_code"
    assert hasattr(response, "headers"), "Missing: headers"
    assert hasattr(response, "content"), "Missing: content"
    assert hasattr(response, "text"), "Missing: text"
    assert hasattr(response, "json"), "Missing: json"
    assert hasattr(response, "url"), "Missing: url"
    assert hasattr(response, "request"), "Missing: request"
    assert hasattr(response, "raise_for_status"), "Missing: raise_for_status"


@pytest.mark.unit
class TestRawResponseDelivery:
    """Tests verifying raw httpx.Response is returned from execute methods."""

    @pytest.mark.asyncio
    async def test_execute_returns_httpx_response(self) -> None:
        """Test that async execute() returns raw httpx.Response (AC #1)."""
        client = AsyncHttpClient()

        # Create a mock httpx.Response
        mock_response = httpx.Response(
            status_code=200,
            content=b'{"message": "success"}',
            headers={"Content-Type": "application/json"},
            request=httpx.Request("GET", "https://example.com"),
        )

        # Mock the underlying httpx client
        client._client.request = AsyncMock(return_value=mock_response)

        # Execute the request
        response = await client.get("https://example.com").execute()

        # Verify we get the raw httpx.Response
        assert isinstance(response, httpx.Response)
        verify_protocol_compliance(response)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_sync_returns_httpx_response(self) -> None:
        """Test that sync execute_sync() returns raw httpx.Response (AC #2)."""
        # This test runs in an async context, but execute_sync uses asyncio.run()
        # which fails in a running event loop. We test this by checking the signature
        # and by running in a separate thread to avoid event loop conflict.
        import threading

        result_holder: list[httpx.Response | None] = [None]
        exception_holder: list[Exception | None] = [None]

        def run_sync_test() -> None:
            try:
                client = AsyncHttpClient()

                # Create a mock httpx.Response
                mock_response = httpx.Response(
                    status_code=200,
                    content=b'{"message": "success"}',
                    headers={"Content-Type": "application/json"},
                    request=httpx.Request("GET", "https://example.com"),
                )

                # Mock the underlying httpx client
                client._client.request = AsyncMock(return_value=mock_response)

                # Execute the request synchronously
                response = client.get("https://example.com").execute_sync()
                result_holder[0] = response
            except Exception as e:
                exception_holder[0] = e

        # Run in a separate thread to avoid event loop conflict
        thread = threading.Thread(target=run_sync_test)
        thread.start()
        thread.join()

        # Check for exceptions
        if exception_holder[0]:
            pytest.fail(f"execute_sync() raised: {exception_holder[0]}")

        # Verify we get the raw httpx.Response
        response = result_holder[0]
        assert response is not None, "execute_sync() returned None"
        assert isinstance(response, httpx.Response)
        verify_protocol_compliance(response)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_response_has_required_properties(self) -> None:
        """Test that response has all required properties for calling modules (AC #4)."""
        client = AsyncHttpClient()

        # Create a mock httpx.Response with JSON content
        json_content = {"key": "value", "nested": {"data": 123}}
        mock_response = httpx.Response(
            status_code=200,
            content=b'{"key": "value", "nested": {"data": 123}}',
            headers={"Content-Type": "application/json", "X-Custom": "header"},
            request=httpx.Request("GET", "https://example.com/api"),
        )

        client._client.request = AsyncMock(return_value=mock_response)

        response = await client.get("https://example.com/api").execute()

        # Verify all required properties are accessible (AC #4)
        assert response.status_code == 200
        assert b"key" in response.content
        assert "application/json" in response.headers.get("Content-Type", "")
        assert "X-Custom" in response.headers
        assert response.url == httpx.URL("https://example.com/api")
        assert response.request.method == "GET"

        # Verify .json() works (caller can parse)
        parsed = response.json()
        assert parsed["key"] == "value"
        assert parsed["nested"]["data"] == 123


@pytest.mark.unit
class TestConcurrentResponseDelivery:
    """Tests verifying raw httpx.Response is returned from concurrent execution."""

    @pytest.mark.asyncio
    async def test_gather_returns_httpx_response_objects(self) -> None:
        """Test that gather_requests() returns raw httpx.Response objects (AC #3)."""
        client = AsyncHttpClient()

        # Create prepared requests
        prepared1 = client.get("https://example1.com").prepare()
        prepared2 = client.get("https://example2.com").prepare()

        # Create mock responses
        mock_response1 = httpx.Response(
            status_code=200,
            content=b"response 1",
            request=httpx.Request("GET", "https://example1.com"),
        )
        mock_response2 = httpx.Response(
            status_code=201,
            content=b"response 2",
            request=httpx.Request("GET", "https://example2.com"),
        )

        async def mock_request(**kwargs):
            url = kwargs.get("url", "")
            if "example1" in url:
                return mock_response1
            return mock_response2

        client._client.request = AsyncMock(side_effect=mock_request)

        # Execute gather
        results = await gather_requests(prepared1, prepared2)

        # Verify we get raw httpx.Response objects
        assert len(results) == 2
        assert isinstance(results[0], httpx.Response)
        assert isinstance(results[1], httpx.Response)
        verify_protocol_compliance(results[0])
        verify_protocol_compliance(results[1])
        assert results[0].status_code == 200
        assert results[1].status_code == 201

    @pytest.mark.asyncio
    async def test_gather_response_content_accessible(self) -> None:
        """Test that gathered responses allow direct content access (AC #4)."""
        client = AsyncHttpClient()

        prepared = client.get("https://api.example.com/data").prepare()

        mock_response = httpx.Response(
            status_code=200,
            content=b'{"data": "test"}',
            headers={"Content-Type": "application/json"},
            request=httpx.Request("GET", "https://api.example.com/data"),
        )

        client._client.request = AsyncMock(return_value=mock_response)

        results = await gather_requests(prepared)

        assert len(results) == 1
        response = results[0]

        # gather_requests returns httpx.Response | NetworkError
        # Network errors are tested separately - ensure we got a response here
        assert isinstance(response, httpx.Response), "Expected httpx.Response, got NetworkError"

        # Verify caller can access all properties directly
        assert response.status_code == 200
        assert b"data" in response.content
        assert response.text == '{"data": "test"}'
        assert response.json() == {"data": "test"}
        assert "Content-Type" in response.headers


@pytest.mark.unit
class TestHttpResponseProtocolAlignment:
    """Tests verifying httpx.Response satisfies HttpResponseProtocol (AC #4)."""

    def test_httpx_response_satisfies_protocol(self) -> None:
        """Test that httpx.Response implements HttpResponseProtocol."""
        # Create a real httpx.Response
        response = httpx.Response(
            status_code=200,
            content=b"test content",
            headers={"Content-Type": "text/plain"},
            request=httpx.Request("GET", "https://example.com"),
        )

        # Verify it satisfies the protocol via structural check
        verify_protocol_compliance(response)

        # Verify all protocol properties are accessible
        assert response.status_code == 200
        assert response.headers is not None
        assert response.content == b"test content"
        assert response.text == "test content"
        assert response.url == httpx.URL("https://example.com")
        assert response.request is not None
        assert callable(response.raise_for_status)

    def test_protocol_properties_return_correct_types(self) -> None:
        """Test that protocol properties return correct types."""
        response = httpx.Response(
            status_code=404,
            content=b"Not Found",
            headers={"X-Custom": "value"},
            request=httpx.Request("POST", "https://example.com"),
        )

        # Verify types match protocol
        assert isinstance(response.status_code, int)
        assert isinstance(response.headers, httpx.Headers)
        assert isinstance(response.content, bytes)
        assert isinstance(response.text, str)
        assert isinstance(response.url, httpx.URL)
        assert isinstance(response.request, httpx.Request)

    def test_response_json_parsing(self) -> None:
        """Test that .json() method works on raw response."""
        json_data = {"users": [{"id": 1}, {"id": 2}]}
        response = httpx.Response(
            status_code=200,
            content=b'{"users": [{"id": 1}, {"id": 2}]}',
            headers={"Content-Type": "application/json"},
            request=httpx.Request("GET", "https://api.example.com"),
        )

        # Verify json() works - caller decides how to parse
        parsed = response.json()
        assert parsed == json_data
        assert len(parsed["users"]) == 2

    def test_response_raise_for_status(self) -> None:
        """Test that raise_for_status() works on raw response."""
        # Test successful response
        success_response = httpx.Response(
            status_code=200,
            content=b"OK",
            request=httpx.Request("GET", "https://example.com"),
        )
        # Should not raise
        success_response.raise_for_status()

        # Test error response
        error_response = httpx.Response(
            status_code=404,
            content=b"Not Found",
            request=httpx.Request("GET", "https://example.com"),
        )
        # Should raise httpx.HTTPStatusError
        with pytest.raises(httpx.HTTPStatusError):
            error_response.raise_for_status()
