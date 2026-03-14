"""Response metadata for HTTP responses.

This module provides the ResponseMetadata class that accompanies
httpx.Response objects to provide additional information about the response,
such as timestamps for data freshness decisions.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ResponseMetadata:
    """Metadata accompanying HTTP responses.

    This class provides supplementary information about HTTP responses
    without modifying the raw httpx.Response object. This maintains
    the raw response pattern while enabling additional functionality
    like timestamp surfacing for data freshness decisions.

    Attributes:
        timestamp: The HTTP date header parsed as datetime, or fallback timestamp
            if the date header is not available.
        retry_count: Number of retries attempted for this request (for future
            resilience integration).
    """

    timestamp: Optional[datetime] = None
    retry_count: int = 0


def extract_timestamp(response: httpx.Response) -> Optional[datetime]:
    """Extract timestamp from HTTP response headers.

    Attempts to extract the 'date' header from the response and parse it
    as a datetime. If the header is not present, falls back to the current UTC time.

    Args:
        response: The HTTP response to extract timestamp from

    Returns:
        Optional[datetime]: The parsed date header as datetime, or fallback
            timestamp if not available
    """
    from datetime import timezone
    from email.parser import Parser
    from email.utils import parsedate_to_datetime

    date_header = response.headers.get("date")
    if date_header:
        try:
            # Parse HTTP-date format from date header
            return parsedate_to_datetime(date_header)
        except (ValueError, TypeError):
            # If parsing fails, fall through to fallback
            pass
    
    # Fallback: Current UTC time as last resort
    return datetime.now(timezone.utc)


def get_response_with_metadata(
    response: httpx.Response,
) -> tuple[httpx.Response, ResponseMetadata]:
    """Attach metadata to an HTTP response.

    Creates a ResponseMetadata object with timestamp extracted from the
    response headers.

    Args:
        response: The HTTP response to attach metadata to

    Returns:
        tuple[httpx.Response, ResponseMetadata]: The original response
            paired with its metadata
    """
    timestamp = extract_timestamp(response)
    metadata = ResponseMetadata(timestamp=timestamp)
    return response, metadata


# Import httpx at module level for type hints
import httpx
