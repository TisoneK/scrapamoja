"""Async HTTP client implementation with chainable request builder (SCR-001).

This module provides the core async HTTP client that can make requests
without launching a browser, achieving millisecond-level latency.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.network.direct_api.interfaces import AuthConfig
from src.network.errors import NetworkError, Retryable


@dataclass
class TokenBucket:
    """Token bucket rate limiter for per-domain rate limiting.

    Implements a simple token bucket algorithm for rate limiting
    requests to individual domains.

    Attributes:
        rate: Number of tokens added per second (default: 10)
        capacity: Maximum number of tokens in the bucket (default: 10)
    """

    rate: float = 10.0  # requests per second
    capacity: float = 10.0  # maximum tokens
    tokens: float = field(default=10.0)
    last_update: float = field(default_factory=time.monotonic)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


@dataclass
class RateLimiter:
    """Per-domain rate limiter using token bucket.

    Supports configurable rate and capacity per domain.
    """

    _buckets: dict[str, TokenBucket] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    default_rate: float = 10.0
    default_capacity: float = 10.0

    def __init__(self, rate: float = 10.0, capacity: float = 10.0) -> None:
        """Initialize rate limiter with custom defaults.

        Args:
            rate: Default number of requests per second per domain
            capacity: Default maximum tokens per domain
        """
        self._buckets = {}
        self._lock = asyncio.Lock()
        self.default_rate = rate
        self.default_capacity = capacity

    async def acquire(self, domain: str) -> None:
        """Acquire rate limit token for the given domain."""
        async with self._lock:
            if domain not in self._buckets:
                self._buckets[domain] = TokenBucket(
                    rate=self.default_rate,
                    capacity=self.default_capacity
                )
            bucket = self._buckets[domain]

        await bucket.acquire()


class RequestBuilder:
    """Chainable request builder for HTTP requests.

    Allows building complex requests using method chaining:
    .get(url).header(k,v).param(k,v).auth(bearer='token').timeout(30).execute()
    """

    def __init__(
        self,
        client: "AsyncHttpClient",
        method: str,
        url: str,
    ) -> None:
        self._client = client
        self._method = method
        # Prepend base_url if available
        if client._base_url:
            self._url = client._base_url.rstrip("/") + "/" + url.lstrip("/")
        else:
            self._url = url
        self._headers: dict[str, str] = {}
        self._params: dict[str, str] = {}
        self._auth: AuthConfig | None = None
        self._timeout: float = 30.0
        self._body: str | bytes | None = None

    def header(self, key: str, value: str) -> "RequestBuilder":
        """Add a header to the request."""
        self._headers[key] = value
        return self

    def param(self, key: str, value: str) -> "RequestBuilder":
        """Add a query parameter to the request."""
        self._params[key] = value
        return self

    def auth(
        self,
        bearer: str | None = None,
        basic: tuple[str, str] | None = None,
        cookie: dict[str, str] | None = None,
    ) -> "RequestBuilder":
        """Set authentication for the request."""
        self._auth = AuthConfig(bearer=bearer, basic=basic, cookie=cookie)
        return self

    def timeout(self, seconds: float) -> "RequestBuilder":
        """Set request timeout in seconds."""
        self._timeout = seconds
        return self

    def body(self, content: str | bytes) -> "RequestBuilder":
        """Set the request body content.

        Args:
            content: Body content as string or bytes
        """
        self._body = content
        return self

    def json(self, data: Any) -> "RequestBuilder":
        """Set JSON body content and Content-Type header.

        Args:
            data: Data to be serialized as JSON
        """
        import json
        self._body = json.dumps(data)
        self._headers["Content-Type"] = "application/json"
        return self

    def prepare(self) -> "PreparedRequest":
        """Prepare this request for concurrent execution with gather().

        Returns a PreparedRequest that can be passed to gather()
        for concurrent execution.

        Returns:
            PreparedRequest: A request ready for gather() execution
        """
        return PreparedRequest(
            client=self._client,
            method=self._method,
            url=self._url,
            headers=self._headers.copy(),
            params=self._params.copy(),
            auth=self._auth,
            timeout=self._timeout,
            body=self._body,
        )

    def execute_sync(self) -> httpx.Response:
        """Execute the request synchronously and return the raw httpx.Response.

        This is the explicit sync wrapper - use this when you need to call
        from a synchronous context.
        """
        return asyncio.run(self._execute_async())

    async def execute(self) -> httpx.Response:
        """Execute the request asynchronously and return the raw httpx.Response.

        This is the primary interface for async contexts.
        """
        return await self._execute_async()

    async def _execute_async(self) -> httpx.Response:
        """Execute the request asynchronously."""
        # Apply auth to headers if set
        if self._auth:
            self._auth.apply_to_headers(self._headers)

        # Get domain for rate limiting
        parsed_url = httpx.URL(self._url)
        domain = parsed_url.host or ""

        # Acquire rate limit token
        await self._client._rate_limiter.acquire(domain)

        # Prepare request kwargs
        request_kwargs = {
            "method": self._method,
            "url": self._url,
            "headers": self._headers,
            "params": self._params,
            "timeout": self._timeout,
        }

        # Add body if set
        if self._body is not None:
            request_kwargs["content"] = self._body

        # Make the request
        response = await self._client._client.request(**request_kwargs)

        return response


class PreparedRequest:
    """A prepared request ready for concurrent execution via gather().

    This class represents a request that has been prepared (via RequestBuilder.prepare())
    and is ready to be executed concurrently with other requests using gather().
    """

    def __init__(
        self,
        client: "AsyncHttpClient",
        method: str,
        url: str,
        headers: dict[str, str],
        params: dict[str, str],
        auth: AuthConfig | None,
        timeout: float,
        body: str | bytes | None,
    ) -> None:
        self._client = client
        self._method = method
        self._url = url
        self._headers = headers
        self._params = params
        self._auth = auth
        self._timeout = timeout
        self._body = body

    async def execute(self) -> httpx.Response:
        """Execute this prepared request and return raw httpx.Response."""
        # Apply auth to headers if set
        headers = self._headers.copy()
        if self._auth:
            self._auth.apply_to_headers(headers)

        # Get domain for rate limiting
        parsed_url = httpx.URL(self._url)
        domain = parsed_url.host or ""

        # Acquire rate limit token
        await self._client._rate_limiter.acquire(domain)

        # Prepare request kwargs
        request_kwargs = {
            "method": self._method,
            "url": self._url,
            "headers": headers,
            "params": self._params,
            "timeout": self._timeout,
        }

        # Add body if set
        if self._body is not None:
            request_kwargs["content"] = self._body

        # Make the request
        response = await self._client._client.request(**request_kwargs)

        return response


async def gather_requests(
    *requests: PreparedRequest,
) -> list[httpx.Response | NetworkError]:
    """Execute multiple requests concurrently using asyncio.gather().

    This function executes all provided PreparedRequest objects concurrently,
    respecting per-domain rate limiting across all requests.

    Args:
        *requests: Variable number of PreparedRequest objects to execute

    Returns:
        list[httpx.Response | NetworkError]: List of responses in the same order
            as the input requests. If a request fails, the corresponding position
            contains a NetworkError model instance rather than raising an exception.
            This allows partial success handling - some requests may succeed while
            others fail.

    Note:
        If the calling task is cancelled, in-flight requests will continue running
        to completion rather than being cancelled immediately.
    """
    if not requests:
        return []

    async def execute_with_error_handling(
        request: PreparedRequest,
        index: int,
    ) -> tuple[int, httpx.Response | NetworkError]:
        """Execute a single request with error handling, returning index and result."""
        try:
            response = await request.execute()
            return (index, response)
        except asyncio.CancelledError:
            # Don't convert CancelledError to NetworkError - let it propagate
            # so the caller knows the request was cancelled
            raise
        except httpx.HTTPError as e:
            # Extract status code if available (use getattr for type safety)
            status_code = None
            response = getattr(e, "response", None)
            if response is not None:
                status_code = response.status_code
            # Create NetworkError for HTTP errors
            error = NetworkError(
                module="direct_api",
                operation=request._method.lower(),
                url=request._url,
                status_code=status_code,
                detail=str(e),
                retryable=Retryable.RETRYABLE,
            )
            return (index, error)
        except Exception as e:
            # Create NetworkError for other errors
            error = NetworkError(
                module="direct_api",
                operation=request._method.lower(),
                url=request._url,
                detail=str(e),
                retryable=Retryable.TERMINAL,
            )
            return (index, error)

    # Execute all requests concurrently with return_exceptions=True to handle
    # partial failures gracefully (but not CancelledError - we want that to propagate)
    results = await asyncio.gather(
        *[execute_with_error_handling(req, i) for i, req in enumerate(requests)],
        return_exceptions=True,
    )

    # Process results - convert any unexpected exceptions to NetworkError
    processed_results: list[tuple[int, httpx.Response | NetworkError]] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Handle any unexpected exceptions (shouldn't happen due to error handling above)
            if isinstance(result, asyncio.CancelledError):
                # Re-raise CancelledError to signal cancellation to caller
                raise result
            error = NetworkError(
                module="direct_api",
                operation="gather",
                url=None,
                detail=str(result),
                retryable=Retryable.TERMINAL,
            )
            processed_results.append((i, error))
        elif isinstance(result, tuple):
            processed_results.append(result)

    # Sort by index to maintain original order
    processed_results.sort(key=lambda x: x[0])

    # Return just the results (not indices)
    return [result for _, result in processed_results]


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
