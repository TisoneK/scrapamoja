"""Tests for CapturedResponse dataclass."""

import pytest

from src.network.interception import CapturedResponse


class TestCapturedResponse:
    """Tests for CapturedResponse dataclass."""

    def test_create_response_with_all_fields(self):
        """Test creating a CapturedResponse with all fields."""
        response = CapturedResponse(
            url="https://example.com/api/data",
            status=200,
            headers={"content-type": "application/json"},
            raw_bytes=b'{"key": "value"}',
        )
        assert response.url == "https://example.com/api/data"
        assert response.status == 200
        assert response.headers == {"content-type": "application/json"}
        assert response.raw_bytes == b'{"key": "value"}'

    def test_create_response_with_none_raw_bytes(self):
        """Test creating a CapturedResponse with raw_bytes as None."""
        response = CapturedResponse(
            url="https://example.com/api/data",
            status=404,
            headers={"content-type": "text/html"},
            raw_bytes=None,
        )
        assert response.raw_bytes is None

    def test_response_field_types(self):
        """Test that response fields have correct types."""
        response = CapturedResponse(
            url="https://example.com/api",
            status=200,
            headers={},
            raw_bytes=b"test",
        )
        assert isinstance(response.url, str)
        assert isinstance(response.status, int)
        assert isinstance(response.headers, dict)
        assert isinstance(response.raw_bytes, bytes) or response.raw_bytes is None

    def test_response_headers_are_strings(self):
        """Test that header keys and values are strings."""
        response = CapturedResponse(
            url="https://example.com/api",
            status=200,
            headers={
                "content-type": "application/json",
                "x-request-id": "abc123",
            },
            raw_bytes=b"{}",
        )
        for key, value in response.headers.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
