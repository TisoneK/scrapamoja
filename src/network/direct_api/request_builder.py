"""Chainable HTTP request builder.

This module provides the RequestBuilder class for building HTTP requests
using a fluent, chainable API.
"""

import json
from typing import TYPE_CHECKING, Any

import httpx

from src.network.direct_api.interfaces import AuthConfig
from src.network.direct_api.prepared_request import PreparedRequest

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

    def execute_sync(self) -> httpx.Response:
        """Execute the request synchronously and return the raw httpx.Response.

        This is the explicit sync wrapper - use this when you need to call
        from a synchronous context.
        """
        import asyncio
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
