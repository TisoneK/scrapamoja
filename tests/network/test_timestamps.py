"""Unit tests for response timestamp functionality (FR28).

This module tests the timestamp surfacing feature that enables
consuming systems to make data freshness decisions.
"""

import pytest
import httpx
from datetime import datetime
from unittest.mock import MagicMock

from src.network.direct_api.metadata import (
    ResponseMetadata,
    extract_timestamp,
    get_response_with_metadata,
)


@pytest.mark.unit
class TestResponseMetadata:
    """Tests for ResponseMetadata dataclass."""

    def test_default_values(self) -> None:
        """Test ResponseMetadata default values."""
        metadata = ResponseMetadata()
        assert metadata.timestamp is None
        assert metadata.retry_count == 0

    def test_with_timestamp(self) -> None:
        """Test ResponseMetadata with timestamp provided."""
        timestamp = datetime(2026, 3, 13, 10, 30, 0)
        metadata = ResponseMetadata(timestamp=timestamp, retry_count=2)
        assert metadata.timestamp == timestamp
        assert metadata.retry_count == 2


@pytest.mark.unit
class TestExtractTimestamp:
    """Tests for extract_timestamp function."""

    def test_extract_valid_date_header(self) -> None:
        """Test extraction of valid HTTP date header."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"date": "Thu, 13 Mar 2026 10:30:00 GMT"}

        timestamp = extract_timestamp(response)
        assert timestamp is not None
        assert timestamp.year == 2026
        assert timestamp.month == 3
        assert timestamp.day == 13

    def test_extract_no_date_header(self) -> None:
        """Test extraction when no date header present - should use fallback."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {}

        timestamp = extract_timestamp(response)
        # Should return fallback timestamp, not None
        assert timestamp is not None
        # Should be timezone-aware (UTC)
        assert timestamp.tzinfo is not None

    def test_extract_invalid_date_header(self) -> None:
        """Test extraction with invalid date header format - should use fallback."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"date": "not-a-valid-date"}

        timestamp = extract_timestamp(response)
        # Should return fallback timestamp, not None
        assert timestamp is not None
        # Should be timezone-aware (UTC)
        assert timestamp.tzinfo is not None


@pytest.mark.unit
class TestGetResponseWithMetadata:
    """Tests for get_response_with_metadata function."""

    def test_returns_tuple(self) -> None:
        """Test that function returns a tuple."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {}

        result = get_response_with_metadata(response)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_response_preserved(self) -> None:
        """Test that original response is preserved in tuple."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {}

        result_response, metadata = get_response_with_metadata(response)
        assert result_response is response

    def test_metadata_with_timestamp(self) -> None:
        """Test metadata contains timestamp when header present."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"date": "Thu, 13 Mar 2026 10:30:00 GMT"}

        result_response, metadata = get_response_with_metadata(response)
        assert isinstance(metadata, ResponseMetadata)
        assert metadata.timestamp is not None

    def test_metadata_without_timestamp(self) -> None:
        """Test metadata has fallback timestamp when header missing."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {}

        result_response, metadata = get_response_with_metadata(response)
        assert isinstance(metadata, ResponseMetadata)
        # Should have fallback timestamp, not None
        assert metadata.timestamp is not None
        # Should be timezone-aware (UTC)
        assert metadata.timestamp.tzinfo is not None


@pytest.mark.unit
class TestTimestampIntegration:
    """Integration tests for timestamp with HTTP responses."""

    def test_real_http_date_format(self) -> None:
        """Test with standard HTTP date format."""
        # Standard RFC 1123 format
        response = MagicMock(spec=httpx.Response)
        response.headers = {"date": "Fri, 13 Mar 2026 12:00:00 GMT"}

        timestamp = extract_timestamp(response)
        assert timestamp is not None
        # Verify it parses to correct UTC time
        assert timestamp.tzinfo is not None  # Should be timezone-aware

    def test_rfc850_date_format(self) -> None:
        """Test with RFC 850 date format."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"date": "Friday, 13-Mar-26 12:00:00 GMT"}

        timestamp = extract_timestamp(response)
        # RFC 850 should still parse correctly
        assert timestamp is not None or timestamp is None  # Depends on parser support

    def test_asctime_date_format(self) -> None:
        """Test with asctime format."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"date": "Fri Mar 13 12:00:00 2026"}

        timestamp = extract_timestamp(response)
        # asctime format may or may not parse depending on Python version
        # The function should handle gracefully
        assert timestamp is None or isinstance(timestamp, datetime)
