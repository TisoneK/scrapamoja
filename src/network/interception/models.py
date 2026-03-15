"""Data models for network interception."""

from dataclasses import dataclass


@dataclass
class CapturedResponse:
    """Represents a captured network response.

    This dataclass stores the response data from captured network requests.

    Attributes:
        url: The full URL of the response
        status: HTTP status code
        headers: Response headers as dictionary
        raw_bytes: Raw response body as bytes, or None if not captured
    """

    url: str
    """The full URL of the response."""

    status: int
    """HTTP status code."""

    headers: dict[str, str]
    """Response headers as dictionary with lowercase keys."""

    raw_bytes: bytes | None
    """Raw response body as bytes, or None if not captured."""


# Backward compatibility: Keep old class name as alias
InterceptedResponse = CapturedResponse
"""Backward compatibility alias for CapturedResponse."""
