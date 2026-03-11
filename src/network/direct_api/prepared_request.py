"""Prepared request for concurrent HTTP execution.

This module provides the PreparedRequest class that represents
a request prepared for concurrent execution via gather().
"""

import httpx

from src.network.direct_api.interfaces import AuthConfig


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


# Forward reference type hint for type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.network.direct_api.client import AsyncHttpClient
