"""Async HTTP client implementation with chainable request builder (SCR-001).

This module provides the core async HTTP client that can make requests
without launching a browser, achieving millisecond-level latency.
"""

from typing import Any, Optional

import httpx

from src.network.direct_api.rate_limiting import RateLimiter, TokenBucket
from src.network.direct_api.request_builder import RequestBuilder
from src.network.direct_api.concurrency import gather_requests
from src.network.direct_api.prepared_request import PreparedRequest
from src.network.credentials import check_verbose_logging_warning


class AsyncHttpClient:
    """Async HTTP client for making requests without browser.

    Supports chainable request building with .get(), .post(), .put(), .delete()
    methods that return builders for method chaining.

    Example:
        async with AsyncHttpClient(base_url="https://api.example.com") as client:
            response = await client.get("/endpoint").execute()
    """

    def __init__(
        self,
        base_url: str | None = None,
        rate_limit: float = 10.0,
        rate_capacity: float = 10.0
    ) -> None:
        """Initialize the async HTTP client.

        Args:
            base_url: Optional base URL to prepend to all requests
            rate_limit: Default requests per second per domain (default: 10)
            rate_capacity: Default maximum tokens per domain (default: 10)
        """
        self._base_url = base_url
        self._client = httpx.AsyncClient()
        self._rate_limiter = RateLimiter(rate=rate_limit, capacity=rate_capacity)
        
        # Check for verbose logging and warn about potential credential exposure
        check_verbose_logging_warning()

    async def __aenter__(self) -> "AsyncHttpClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self._client.aclose()

    def get(self, url: str) -> RequestBuilder:
        """Create a GET request builder."""
        return RequestBuilder(self, "GET", url)

    def post(self, url: str) -> RequestBuilder:
        """Create a POST request builder."""
        return RequestBuilder(self, "POST", url)

    def put(self, url: str) -> RequestBuilder:
        """Create a PUT request builder."""
        return RequestBuilder(self, "PUT", url)

    def delete(self, url: str) -> RequestBuilder:
        """Create a DELETE request builder."""
        return RequestBuilder(self, "DELETE", url)


# Re-export for backwards compatibility and clean imports
__all__ = [
    "AsyncHttpClient",
    "PreparedRequest",
    "gather_requests",
    "TokenBucket",
    "RateLimiter",
    "RequestBuilder",
]
