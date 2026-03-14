"""Prepared request for concurrent HTTP execution.

This module provides the PreparedRequest class that represents
a request prepared for concurrent execution via gather().
"""

import httpx

from src.network.errors import NetworkError, Retryable
from src.network.direct_api.interfaces import AuthConfig
from src.network.direct_api.metadata import ResponseMetadata, get_response_with_metadata


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

    async def execute(self) -> tuple[httpx.Response, ResponseMetadata] | NetworkError:
        """Execute this prepared request and return response with metadata, or NetworkError on failure."""""
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


# Forward reference type hint for type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.network.direct_api.client import AsyncHttpClient
