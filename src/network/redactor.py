"""Log redaction utility for sensitive authentication values.

This module provides functionality to redact authentication values from
logs to prevent credential leakage.

Security requirements (NFRs):
- NFR5: Cookies, bearer tokens, and harvested session data must never appear in logs
- NFR6: Request URL, status code, and headers with auth values redacted - not raw tokens
- NFR9: Redact anything in auth headers and cookie values by default
- NFR10: Opt-in verbose logging must explicitly warn about potential credential exposure
"""

from __future__ import annotations

import re
from typing import Any, Optional


# Marker for redacted values
REDACTED = "[REDACTED]"

# Headers that contain authentication data
AUTH_HEADERS = {
    "authorization",
    "www-authenticate",
    "proxy-authenticate",
    "proxy-authorization",
    "cookie",
    "set-cookie",
}

# Header values that might contain sensitive data
SENSITIVE_HEADERS = {
    "authorization",
    "www-authenticate",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "x-access-token",
    "x-secret",
    "x-password",
    "x-csrf-token",
    "x-xsrf-token",
}


def is_sensitive_header(header_name: str) -> bool:
    """Check if a header name is sensitive and should be redacted.

    Args:
        header_name: Name of the header (case-insensitive)

    Returns:
        True if the header contains sensitive data, False otherwise
    """
    return header_name.lower() in SENSITIVE_HEADERS


def is_auth_header(header_name: str) -> bool:
    """Check if a header is specifically an authentication header.

    Args:
        header_name: Name of the header (case-insensitive)

    Returns:
        True if the header is an auth header, False otherwise
    """
    return header_name.lower() in AUTH_HEADERS


def redact_header_value(header_name: str, value: str) -> str:
    """Redact sensitive values from a header.

    Args:
        header_name: Name of the header
        value: Original header value

    Returns:
        Redacted header value
    """
    header_lower = header_name.lower()

    if header_lower == "cookie" or header_lower == "set-cookie":
        # For cookies, redact only the values, keep the names
        return redact_cookie_header(value)

    if header_lower == "authorization":
        # For auth headers, redact the token but keep the scheme (Bearer, Basic, etc.)
        return redact_authorization_header(value)

    # For other sensitive headers, redact the entire value
    return REDACTED


def redact_authorization_header(value: str) -> str:
    """Redact authorization header but preserve the auth scheme.

    Examples:
        "Bearer abc123" -> "Bearer [REDACTED]"
        "Basic dXNlcjpwYXNz" -> "Basic [REDACTED]"
        "Digest username=..." -> "Digest [REDACTED]"

    Args:
        value: The authorization header value

    Returns:
        Redacted authorization header value
    """
    # Split on first space to separate scheme from credentials
    parts = value.split(" ", 1)
    if len(parts) == 2:
        scheme, credentials = parts
        return f"{scheme} {REDACTED}"
    return REDACTED


def redact_cookie_header(value: str) -> str:
    """Redact cookie values but preserve cookie names.

    Example:
        "session=abc123; user=john" -> "session=[REDACTED]; user=[REDACTED]"

    Args:
        value: The cookie header value

    Returns:
        Redacted cookie header value
    """
    parts = value.split(";")
    redacted_parts = []

    for part in parts:
        part = part.strip()
        if "=" in part:
            name, _ = part.split("=", 1)
            redacted_parts.append(f"{name}={REDACTED}")
        else:
            redacted_parts.append(part)

    return "; ".join(redacted_parts)


def redact_dict_values(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive values from a dictionary (e.g., headers or params).

    Args:
        data: Dictionary containing header or parameter key-value pairs

    Returns:
        New dictionary with sensitive values redacted
    """
    result = {}

    for key, value in data.items():
        if is_sensitive_header(key):
            if isinstance(value, str):
                result[key] = redact_header_value(key, value)
            else:
                result[key] = REDACTED
        else:
            result[key] = value

    return result


def redact_url(url: str) -> str:
    """Redact sensitive query parameters from URL.

    Args:
        url: The URL to redact

    Returns:
        URL with sensitive query parameters redacted
    """
    # Common sensitive query parameter names
    sensitive_params = {
        "token",
        "key",
        "secret",
        "password",
        "auth",
        "api_key",
        "apikey",
        "access_token",
        "session_id",
    }

    try:
        if "?" not in url:
            return url

        base_url, query_string = url.split("?", 1)

        if not query_string:
            return url

        params = query_string.split("&")
        redacted_params = []

        for param in params:
            if "=" in param:
                name, value = param.split("=", 1)
                if name.lower() in sensitive_params:
                    redacted_params.append(f"{name}={REDACTED}")
                else:
                    redacted_params.append(param)
            else:
                redacted_params.append(param)

        return f"{base_url}?{'&'.join(redacted_params)}"
    except Exception:
        # If parsing fails, return URL as-is
        return url


def format_headers_for_log(headers: dict[str, str]) -> dict[str, str]:
    """Format headers for logging, redacting sensitive values.

    Args:
        headers: Dictionary of headers

    Returns:
        Dictionary with sensitive header values redacted
    """
    return redact_dict_values(headers)


def format_request_for_log(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Format HTTP request details for logging with redaction.

    Args:
        method: HTTP method
        url: Request URL
        headers: Optional request headers
        params: Optional query parameters

    Returns:
        Dictionary suitable for logging with sensitive values redacted
    """
    result = {
        "method": method,
        "url": redact_url(url) if url else url,
    }

    if headers:
        result["headers"] = format_headers_for_log(headers)

    if params:
        result["params"] = redact_dict_values(params)

    return result


def format_response_for_log(
    status_code: int,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Format HTTP response details for logging with redaction.

    Args:
        status_code: HTTP status code
        headers: Optional response headers

    Returns:
        Dictionary suitable for logging with sensitive values redacted
    """
    result = {"status_code": status_code}

    if headers:
        result["headers"] = format_headers_for_log(headers)

    return result