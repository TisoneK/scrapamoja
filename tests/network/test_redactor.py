"""Unit tests for log redaction utility."""

import pytest

from src.network.redactor import (
    REDACTED,
    is_auth_header,
    is_sensitive_header,
    redact_authorization_header,
    redact_cookie_header,
    redact_dict_values,
    redact_header_value,
    redact_url,
    format_headers_for_log,
    format_request_for_log,
    format_response_for_log,
)


@pytest.mark.unit
class TestIsSensitiveHeader:
    """Tests for is_sensitive_header function."""

    def test_authorization_is_sensitive(self) -> None:
        """Test that Authorization header is sensitive."""
        assert is_sensitive_header("Authorization") is True

    def test_authorization_lowercase_is_sensitive(self) -> None:
        """Test that authorization header (lowercase) is sensitive."""
        assert is_sensitive_header("authorization") is True

    def test_cookie_is_sensitive(self) -> None:
        """Test that Cookie header is sensitive."""
        assert is_sensitive_header("Cookie") is True

    def test_x_api_key_is_sensitive(self) -> None:
        """Test that X-API-Key header is sensitive."""
        assert is_sensitive_header("X-API-Key") is True

    def test_content_type_is_not_sensitive(self) -> None:
        """Test that Content-Type header is not sensitive."""
        assert is_sensitive_header("Content-Type") is False

    def test_accept_is_not_sensitive(self) -> None:
        """Test that Accept header is not sensitive."""
        assert is_sensitive_header("Accept") is False


@pytest.mark.unit
class TestIsAuthHeader:
    """Tests for is_auth_header function."""

    def test_authorization_is_auth_header(self) -> None:
        """Test that Authorization is identified as auth header."""
        assert is_auth_header("Authorization") is True

    def test_cookie_is_auth_header(self) -> None:
        """Test that Cookie is identified as auth header."""
        assert is_auth_header("Cookie") is True


@pytest.mark.unit
class TestRedactAuthorizationHeader:
    """Tests for redact_authorization_header function."""

    def test_bearer_token_redacted(self) -> None:
        """Test that Bearer token is redacted but scheme is preserved."""
        result = redact_authorization_header("Bearer abc123token")
        assert result == "Bearer [REDACTED]"

    def test_basic_auth_redacted(self) -> None:
        """Test that Basic auth is redacted but scheme is preserved."""
        result = redact_authorization_header("Basic dXNlcjpwYXNz")
        assert result == "Basic [REDACTED]"

    def test_digest_auth_redacted(self) -> None:
        """Test that Digest auth is redacted but scheme is preserved."""
        result = redact_authorization_header("Digest username=user")
        assert result == "Digest [REDACTED]"


@pytest.mark.unit
class TestRedactCookieHeader:
    """Tests for redact_cookie_header function."""

    def test_single_cookie_redacted(self) -> None:
        """Test that single cookie value is redacted."""
        result = redact_cookie_header("session=abc123")
        assert result == "session=[REDACTED]"

    def test_multiple_cookies_redacted(self) -> None:
        """Test that multiple cookie values are redacted."""
        result = redact_cookie_header("session=abc123; user=john")
        assert result == "session=[REDACTED]; user=[REDACTED]"


@pytest.mark.unit
class TestRedactHeaderValue:
    """Tests for redact_header_value function."""

    def test_authorization_header_redacted(self) -> None:
        """Test that Authorization header value is redacted."""
        result = redact_header_value("Authorization", "Bearer mytoken")
        assert result == "Bearer [REDACTED]"

    def test_cookie_header_redacted(self) -> None:
        """Test that Cookie header value is redacted."""
        result = redact_header_value("Cookie", "session=abc;user=john")
        assert result == "session=[REDACTED]; user=[REDACTED]"


@pytest.mark.unit
class TestRedactDictValues:
    """Tests for redact_dict_values function."""

    def test_authorization_header_redacted_in_dict(self) -> None:
        """Test that Authorization header in dict is redacted."""
        headers = {"Authorization": "Bearer token123", "Content-Type": "application/json"}
        result = redact_dict_values(headers)
        assert result["Authorization"] == "Bearer [REDACTED]"
        assert result["Content-Type"] == "application/json"

    def test_cookie_header_redacted_in_dict(self) -> None:
        """Test that Cookie header in dict is redacted."""
        cookies = {"Cookie": "session=abc", "Accept": "text/html"}
        result = redact_dict_values(cookies)
        assert result["Cookie"] == "session=[REDACTED]"


@pytest.mark.unit
class TestRedactUrl:
    """Tests for redact_url function."""

    def test_url_with_token_param_redacted(self) -> None:
        """Test that token param in URL is redacted."""
        result = redact_url("https://api.example.com/data?token=secret123")
        assert "token=[REDACTED]" in result

    def test_url_with_api_key_param_redacted(self) -> None:
        """Test that api_key param in URL is redacted."""
        result = redact_url("https://api.example.com?api_key=mykey")
        assert "api_key=[REDACTED]" in result

    def test_url_without_sensitive_params_unchanged(self) -> None:
        """Test that URL without sensitive params is unchanged."""
        result = redact_url("https://api.example.com/page?page=1")
        assert result == "https://api.example.com/page?page=1"


@pytest.mark.unit
class TestFormatHeadersForLog:
    """Tests for format_headers_for_log function."""

    def test_sensitive_headers_redacted(self) -> None:
        """Test that sensitive headers are redacted when formatting for log."""
        headers = {
            "Authorization": "Bearer mytoken",
            "Content-Type": "application/json",
            "Cookie": "session=abc123",
        }
        result = format_headers_for_log(headers)
        assert result["Authorization"] == "Bearer [REDACTED]"
        assert result["Content-Type"] == "application/json"
        assert result["Cookie"] == "session=[REDACTED]"


@pytest.mark.unit
class TestFormatRequestForLog:
    """Tests for format_request_for_log function."""

    def test_request_formatted_with_redaction(self) -> None:
        """Test that request is formatted with proper redaction."""
        result = format_request_for_log(
            "GET",
            "https://api.example.com/data?token=secret",
            headers={"Authorization": "Bearer mytoken"},
            params={"page": "1"},
        )
        assert result["method"] == "GET"
        assert "token=[REDACTED]" in result["url"]
        assert result["headers"]["Authorization"] == "Bearer [REDACTED]"


@pytest.mark.unit
class TestFormatResponseForLog:
    """Tests for format_response_for_log function."""

    def test_response_formatted_with_redaction(self) -> None:
        """Test that response is formatted with proper redaction."""
        result = format_response_for_log(
            200,
            headers={"Content-Type": "application/json", "Set-Cookie": "session=abc"},
        )
        assert result["status_code"] == 200
        assert result["headers"]["Content-Type"] == "application/json"
        assert result["headers"]["Set-Cookie"] == "session=[REDACTED]"