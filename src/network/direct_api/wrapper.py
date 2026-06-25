"""Python API wrapper for Direct API HTTP client (SCR-001).

This module provides a convenient Python API wrapper that exposes all CLI
capabilities programmatically. It wraps AsyncHttpClient to provide a simple,
synchronous-friendly interface for making HTTP requests.

## Features

- HTTP methods: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- Request parameters: headers, body, json, params, timeout
- Authentication: bearer token, basic auth, cookie auth, auto_source
- Output formatting: json, text, raw, status
- Pretty printing and header inclusion options
- Verbose logging support

## Usage

```python
import asyncio
from src.network.direct_api import DirectApi

async def main():
    # Create API instance
    api = DirectApi()
    
    # Simple GET request
    result = await api.get("https://api.example.com/data")
    
    # POST with JSON body
    result = await api.post(
        "https://api.example.com/data",
        json={"name": "test", "value": 123}
    )
    
    # With authentication
    api = DirectApi(auth=DirectApi.auth(bearer="mytoken"))
    result = await api.get("https://api.example.com/protected")
    
    # With output formatting
    result = await api.get(
        "https://api.example.com/data",
        output="json",
        pretty=True,
        include_headers=True
    )

asyncio.run(main())
```

## Output Formats

- `json`: Returns dict with status_code, url, headers (if included), and body
- `text`: Returns just the response body as string
- `raw`: Returns raw httpx.Response object
- `status`: Returns just the status code as integer
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypedDict

import httpx

from src.network.direct_api.client import AsyncHttpClient
from src.network.direct_api.interfaces import AuthConfig
from src.network.direct_api.metadata import ResponseMetadata
from src.network.errors import NetworkError
from src.core.logging_config import JsonLoggingConfigurator


class OutputFormat(str, Enum):
    """Output format options for responses."""

    JSON = "json"
    TEXT = "text"
    RAW = "raw"
    STATUS = "status"


class OutputData(TypedDict, total=False):
    """Type for output data dictionary."""

    status_code: int
    url: str
    headers: dict[str, str]
    body: Any


@dataclass
class DirectApi:
    """Python API wrapper for Direct API HTTP client.

    Provides a convenient interface for making HTTP requests without a browser,
    with feature parity to the DirectCLI. Supports all HTTP methods, authentication
    options, and output formatting.

    Attributes:
        base_url: Optional base URL to prepend to all requests
        rate_limit: Requests per second per domain (default: 10)
        rate_capacity: Maximum tokens per domain (default: 10)
        auth: Authentication configuration
        timeout: Default timeout in seconds (default: 30)
        output: Default output format (default: json)
        pretty: Whether to pretty-print JSON output (default: False)
        include_headers: Whether to include headers in output (default: False)
        verbose: Whether to enable verbose logging (default: False)

    Example:
        >>> api = DirectApi()
        >>> result = await api.get("https://api.example.com")
        >>> print(result)
        {'status_code': 200, 'url': 'https://api.example.com', 'body': {...}}
    """

    base_url: str | None = None
    rate_limit: float = 10.0
    rate_capacity: float = 10.0
    auth: AuthConfig | None = None
    timeout: float = 30.0
    output: OutputFormat = OutputFormat.JSON
    pretty: bool = False
    include_headers: bool = False
    verbose: bool = False

    # Internal client instance
    _client: AsyncHttpClient | None = field(default=None, init=False, repr=False)

    @staticmethod
    def create_auth_config(
        bearer: str | None = None,
        basic: tuple[str, str] | None = None,
        cookie: dict[str, str] | None = None,
        auto_source: bool = True,
    ) -> AuthConfig:
        """Create authentication configuration.

        Args:
            bearer: Bearer token for authentication
            basic: Tuple of (username, password) for basic auth
            cookie: Dictionary of cookie key-value pairs
            auto_source: If True, auto-source credentials from env vars

        Returns:
            AuthConfig instance

        Example:
            >>> api = DirectApi(auth=DirectApi.create_auth_config(bearer="token123"))
            >>> api = DirectApi(auth=DirectApi.create_auth_config(basic=("user", "pass")))
        """
        return AuthConfig(
            bearer=bearer,
            basic=basic,
            cookie=cookie,
            auto_source=auto_source,
        )

    async def __aenter__(self) -> "DirectApi":
        """Enter async context manager."""
        # Setup verbose logging if enabled
        if self.verbose:
            JsonLoggingConfigurator.setup(verbose=True)

        # Create internal HTTP client
        self._client = AsyncHttpClient(
            base_url=self.base_url,
            rate_limit=self.rate_limit,
            rate_capacity=self.rate_capacity,
        )
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    def _get_client(self) -> AsyncHttpClient:
        """Get the internal HTTP client.

        Returns:
            AsyncHttpClient instance

        Raises:
            RuntimeError: If not used as context manager
        """
        if self._client is None:
            msg = (
                "DirectApi must be used as an async context manager: "
                "'async with DirectApi() as api:'"
            )
            raise RuntimeError(msg)
        return self._client

    def _apply_auth(self, builder: Any) -> Any:
        """Apply authentication to request builder.

        Args:
            builder: RequestBuilder instance

        Returns:
            Modified RequestBuilder with auth applied
        """
        # Use instance auth or default to auto_source
        auth = self.auth if self.auth else AuthConfig(auto_source=True)

        if auth.bearer:
            builder = builder.auth(bearer=auth.bearer)
        elif auth.basic:
            builder = builder.auth(basic=auth.basic)
        elif auth.cookie:
            builder = builder.auth(cookie=auth.cookie)

        return builder

    def _build_response_data(
        self,
        response: httpx.Response,
        metadata: ResponseMetadata,
        output_format: OutputFormat,
        include_headers: bool,
    ) -> Any:
        """Build response data based on output format.

        Args:
            response: HTTP response
            metadata: Response metadata
            output_format: Output format to use
            include_headers: Whether to include headers

        Returns:
            Formatted response data based on output_format
        """
        # Handle status-only output
        if output_format == OutputFormat.STATUS:
            return response.status_code

        # Build response data dict
        data: OutputData = {
            "status_code": response.status_code,
            "url": str(response.url),
        }

        # Include headers if requested
        if include_headers:
            data["headers"] = dict(response.headers)

        # Add body based on content type
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data["body"] = response.json()
            except Exception:
                data["body"] = response.text
        elif "text" in content_type:
            data["body"] = response.text
        else:
            # Binary or other content
            try:
                data["body"] = response.text
            except Exception:
                data["body"] = response.content.hex()

        # Handle different output formats
        if output_format == OutputFormat.TEXT:
            return data.get("body", "")
        elif output_format == OutputFormat.RAW:
            return response
        else:  # JSON
            return data

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | bytes | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
        auth_config: AuthConfig | None = None,
        output: OutputFormat | None = None,
        pretty: bool | None = None,
        include_headers: bool | None = None,
    ) -> Any:
        """Make an HTTP request with full configuration options.

        This is the core method that all HTTP method shortcuts use.
        Provides complete control over the request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
            url: URL to request
            headers: Dictionary of HTTP headers
            body: Request body content (string or bytes)
            json_data: JSON data to send (will set Content-Type to application/json)
            params: Query parameters dictionary
            timeout: Request timeout in seconds (default: from instance)
            auth_config: Authentication configuration (default: from instance)
            output: Output format (default: from instance)
            pretty: Pretty print JSON (default: from instance)
            include_headers: Include response headers (default: from instance)

        Returns:
            Response data in the specified output format

        Raises:
            NetworkError: If the request fails
            RuntimeError: If not used as context manager
        """
        client = self._get_client()

        # Resolve parameters with defaults
        timeout = timeout if timeout is not None else self.timeout
        output = output if output is not None else self.output
        pretty = pretty if pretty is not None else self.pretty
        include_headers = (
            include_headers if include_headers is not None else self.include_headers
        )
        auth_config = auth_config if auth_config is not None else self.auth

        # Create request builder
        method_lower = method.lower()
        builder = getattr(client, method_lower)(url)

        # Add headers
        if headers:
            for key, value in headers.items():
                builder = builder.header(key, value)

        # Add query params
        if params:
            for key, value in params.items():
                builder = builder.param(key, value)

        # Add body (json takes precedence over body)
        if json_data is not None:
            builder = builder.json(json_data)
        elif body is not None:
            builder = builder.body(body)

        # Apply authentication
        effective_auth = auth_config if auth_config else AuthConfig(auto_source=True)
        if effective_auth.bearer:
            builder = builder.auth(bearer=effective_auth.bearer)
        elif effective_auth.basic:
            builder = builder.auth(basic=effective_auth.basic)
        elif effective_auth.cookie:
            builder = builder.auth(cookie=effective_auth.cookie)

        # Set timeout
        builder = builder.timeout(timeout)

        # Execute request
        result = await builder.execute()

        # Handle NetworkError - return it directly for caller to handle
        if isinstance(result, NetworkError):
            return result

        response, metadata = result

        # Format and return response
        return self._build_response_data(
            response, metadata, output, include_headers
        )

    # HTTP method shortcuts

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
        auth_config: AuthConfig | None = None,
        output: OutputFormat | None = None,
        pretty: bool | None = None,
        include_headers: bool | None = None,
    ) -> Any:
        """Make a GET request.

        Args:
            url: URL to request
            headers: Dictionary of HTTP headers
            params: Query parameters dictionary
            timeout: Request timeout in seconds
            auth_config: Authentication configuration
            output: Output format
            pretty: Pretty print JSON
            include_headers: Include response headers

        Returns:
            Response data in the specified output format
        """
        return await self.request(
            method="GET",
            url=url,
            headers=headers,
            params=params,
            timeout=timeout,
            auth_config=auth_config,
            output=output,
            pretty=pretty,
            include_headers=include_headers,
        )

    async def post(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | bytes | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
        auth_config: AuthConfig | None = None,
        output: OutputFormat | None = None,
        pretty: bool | None = None,
        include_headers: bool | None = None,
    ) -> Any:
        """Make a POST request.

        Args:
            url: URL to request
            headers: Dictionary of HTTP headers
            body: Request body content
            json_data: JSON data to send
            params: Query parameters dictionary
            timeout: Request timeout in seconds
            auth_config: Authentication configuration
            output: Output format
            pretty: Pretty print JSON
            include_headers: Include response headers

        Returns:
            Response data in the specified output format
        """
        return await self.request(
            method="POST",
            url=url,
            headers=headers,
            body=body,
            json_data=json_data,
            params=params,
            timeout=timeout,
            auth_config=auth_config,
            output=output,
            pretty=pretty,
            include_headers=include_headers,
        )

    async def put(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | bytes | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
        auth_config: AuthConfig | None = None,
        output: OutputFormat | None = None,
        pretty: bool | None = None,
        include_headers: bool | None = None,
    ) -> Any:
        """Make a PUT request.

        Args:
            url: URL to request
            headers: Dictionary of HTTP headers
            body: Request body content
            json_data: JSON data to send
            params: Query parameters dictionary
            timeout: Request timeout in seconds
            auth_config: Authentication configuration
            output: Output format
            pretty: Pretty print JSON
            include_headers: Include response headers

        Returns:
            Response data in the specified output format
        """
        return await self.request(
            method="PUT",
            url=url,
            headers=headers,
            body=body,
            json_data=json_data,
            params=params,
            timeout=timeout,
            auth_config=auth_config,
            output=output,
            pretty=pretty,
            include_headers=include_headers,
        )

    async def delete(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
        auth_config: AuthConfig | None = None,
        output: OutputFormat | None = None,
        pretty: bool | None = None,
        include_headers: bool | None = None,
    ) -> Any:
        """Make a DELETE request.

        Args:
            url: URL to request
            headers: Dictionary of HTTP headers
            params: Query parameters dictionary
            timeout: Request timeout in seconds
            auth_config: Authentication configuration
            output: Output format
            pretty: Pretty print JSON
            include_headers: Include response headers

        Returns:
            Response data in the specified output format
        """
        return await self.request(
            method="DELETE",
            url=url,
            headers=headers,
            params=params,
            timeout=timeout,
            auth_config=auth_config,
            output=output,
            pretty=pretty,
            include_headers=include_headers,
        )

    async def patch(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | bytes | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
        auth_config: AuthConfig | None = None,
        output: OutputFormat | None = None,
        pretty: bool | None = None,
        include_headers: bool | None = None,
    ) -> Any:
        """Make a PATCH request.

        Args:
            url: URL to request
            headers: Dictionary of HTTP headers
            body: Request body content
            json_data: JSON data to send
            params: Query parameters dictionary
            timeout: Request timeout in seconds
            auth_config: Authentication configuration
            output: Output format
            pretty: Pretty print JSON
            include_headers: Include response headers

        Returns:
            Response data in the specified output format
        """
        return await self.request(
            method="PATCH",
            url=url,
            headers=headers,
            body=body,
            json_data=json_data,
            params=params,
            timeout=timeout,
            auth_config=auth_config,
            output=output,
            pretty=pretty,
            include_headers=include_headers,
        )

    async def head(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
        auth_config: AuthConfig | None = None,
        output: OutputFormat | None = None,
        pretty: bool | None = None,
        include_headers: bool | None = None,
    ) -> Any:
        """Make a HEAD request.

        Args:
            url: URL to request
            headers: Dictionary of HTTP headers
            params: Query parameters dictionary
            timeout: Request timeout in seconds
            auth_config: Authentication configuration
            output: Output format
            pretty: Pretty print JSON
            include_headers: Include response headers

        Returns:
            Response data in the specified output format
        """
        return await self.request(
            method="HEAD",
            url=url,
            headers=headers,
            params=params,
            timeout=timeout,
            auth_config=auth_config,
            output=output,
            pretty=pretty,
            include_headers=include_headers,
        )

    async def options(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
        auth_config: AuthConfig | None = None,
        output: OutputFormat | None = None,
        pretty: bool | None = None,
        include_headers: bool | None = None,
    ) -> Any:
        """Make an OPTIONS request.

        Args:
            url: URL to request
            headers: Dictionary of HTTP headers
            params: Query parameters dictionary
            timeout: Request timeout in seconds
            auth_config: Authentication configuration
            output: Output format
            pretty: Pretty print JSON
            include_headers: Include response headers

        Returns:
            Response data in the specified output format
        """
        return await self.request(
            method="OPTIONS",
            url=url,
            headers=headers,
            params=params,
            timeout=timeout,
            auth_config=auth_config,
            output=output,
            pretty=pretty,
            include_headers=include_headers,
        )


__all__ = [
    "DirectApi",
    "OutputFormat",
    "OutputData",
]
