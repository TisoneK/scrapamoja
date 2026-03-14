"""Chainable HTTP request builder.

This module provides the RequestBuilder class for building HTTP requests
using a fluent, chainable API.

## Raw Response Pattern

This module returns raw httpx.Response objects - never decoded, never wrapped.
The caller decides how to handle the content:

- `.content` - raw bytes
- `.text` - decoded string  
- `.json()` - parse as JSON
- `.headers` - response headers
- `.url` - final URL after redirects
- `.status_code` - HTTP status code
"""

import json
import os
from typing import TYPE_CHECKING, Any

import httpx

from src.network.errors import NetworkError, Retryable
from src.network.direct_api.interfaces import AuthConfig
from src.network.direct_api.prepared_request import PreparedRequest
from src.network.direct_api.metadata import ResponseMetadata, get_response_with_metadata
from src.network.redactor import format_request_for_log, format_response_for_log

# Import structlog for logging - it's optional
try:
    import structlog
except ImportError:
    structlog = None

if TYPE_CHECKING:
    from src.network.direct_api.client import AsyncHttpClient


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
        self._body = json.dumps(data)
        self._headers["Content-Type"] = "application/json"
        return self

    def prepare(self) -> PreparedRequest:
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

    def execute_sync(self) -> tuple[httpx.Response, ResponseMetadata] | NetworkError:
        """Execute the request synchronously and return the response with metadata, or NetworkError on failure.

        This is the explicit sync wrapper - use this when you need to call
        from a synchronous context.
        """
        import asyncio
        return asyncio.run(self._execute_async())

    async def execute(self) -> tuple[httpx.Response, ResponseMetadata] | NetworkError:
        """Execute the request asynchronously and return the response with metadata, or NetworkError on failure.

        This is the primary interface for async contexts.
        Returns (httpx.Response, ResponseMetadata) on success, NetworkError on failure.
        """
        return await self._execute_async()

    async def _execute_async(self) -> tuple[httpx.Response, ResponseMetadata] | NetworkError:
        """Execute the request asynchronously, returning (Response, Metadata) or NetworkError."""
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

        # Log request with redaction (if logging is enabled)
        self._log_request()

        # Add body if set
        if self._body is not None:
            request_kwargs["content"] = self._body

        # Make the request with error handling
        try:
            response = await self._client._client.request(**request_kwargs)
        except httpx.HTTPStatusError as e:
            # HTTP errors (4xx, 5xx) - extract status code
            status_code = e.response.status_code if e.response else None
            return NetworkError(
                module="direct_api",
                operation=self._method.lower(),
                url=str(self._url),
                status_code=status_code,
                detail=str(e),
                retryable=self._classify_error(status_code),
            )
        except httpx.HTTPError as e:
            # Other HTTP errors (connection errors, timeouts, etc.)
            return NetworkError(
                module="direct_api",
                operation=self._method.lower(),
                url=str(self._url),
                detail=str(e),
                retryable=Retryable.RETRYABLE,
            )
        except Exception as e:
            # Unexpected errors - treat as terminal
            return NetworkError(
                module="direct_api",
                operation=self._method.lower(),
                url=str(self._url),
                detail=str(e),
                retryable=Retryable.TERMINAL,
            )

        # Log response with redaction
        self._log_response(response)

        # Attach metadata with timestamp
        return get_response_with_metadata(response)

    def _classify_error(self, status_code: int | None) -> Retryable:
        """Classify error as retryable or terminal based on HTTP status code.

        Args:
            status_code: HTTP status code if available

        Returns:
            Retryable enum value - RETRYABLE for 429/503, TERMINAL for other errors
        """
        if status_code is None:
            return Retryable.RETRYABLE
        # 429 (Too Many Requests) and 503 (Service Unavailable) are retryable
        if status_code in (429, 503):
            return Retryable.RETRYABLE
        return Retryable.TERMINAL

    def _log_request(self) -> None:
        """Log request details with redaction of sensitive values."""
        if structlog is None:
            return
        
        try:
            verbose_enabled = os.environ.get("SCRAPAMOJA_VERBOSE", "false").lower()
            if verbose_enabled not in ("true", "1", "yes"):
                return
            
            log = structlog.get_logger()
            log.debug(
                "http_request",
                **format_request_for_log(
                    method=self._method,
                    url=self._url,
                    headers=self._headers,
                    params=self._params,
                )
            )
        except Exception:
            # Silently fail if logging fails
            pass

    def _log_response(self, response: httpx.Response) -> None:
        """Log response details with redaction of sensitive values."""
        if structlog is None:
            return
        
        try:
            verbose_enabled = os.environ.get("SCRAPAMOJA_VERBOSE", "false").lower()
            if verbose_enabled not in ("true", "1", "yes"):
                return
            
            log = structlog.get_logger()
            log.debug(
                "http_response",
                **format_response_for_log(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )
            )
        except Exception:
            # Silently fail if logging fails
            pass
