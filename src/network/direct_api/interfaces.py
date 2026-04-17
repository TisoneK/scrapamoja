"""Interfaces and protocols for the direct API HTTP client (SCR-001).

This module defines the contracts for dependency injection and
the output protocol for the HTTP client.
"""

from __future__ import annotations

import base64
from typing import Any, Optional, Protocol, Self, TYPE_CHECKING, Tuple, Union

import httpx

from src.network.credentials import CredentialsManager
from src.network.direct_api.metadata import ResponseMetadata
from src.network.errors import NetworkError

if TYPE_CHECKING:
    from src.network.direct_api.client import PreparedRequest


class HttpResponseProtocol(Protocol):
    """Protocol for HTTP response objects.

    This defines the interface that SCR-001 returns to callers.
    The caller decides what to do with the response - never decoded,
    never wrapped.
    """

    @property
    def status_code(self) -> int: ...

    @property
    def headers(self) -> httpx.Headers: ...

    @property
    def content(self) -> bytes: ...

    @property
    def text(self) -> str: ...

    @property
    def json(self) -> Any: ...

    @property
    def url(self) -> httpx.URL: ...

    @property
    def request(self) -> httpx.Request: ...

    def raise_for_status(self) -> None: ...


class AuthConfig:
    """Authentication configuration for HTTP requests.

    Supports bearer tokens, basic auth, and cookie-based authentication.
    Also supports auto-sourcing credentials from environment variables
    and secrets files.
    """

    def __init__(
        self,
        bearer: str | None = None,
        basic: tuple[str, str] | None = None,
        cookie: dict[str, str] | None = None,
        auto_source: bool = True,
        site_prefix: str | None = None,
    ) -> None:
        """Initialize AuthConfig.

        Args:
            bearer: Bearer token (if not auto-sourcing from env vars)
            basic: Tuple of (username, password) for basic auth
            cookie: Dictionary of cookie key-value pairs
            auto_source: If True, auto-source credentials from env vars/secrets file
            site_prefix: Optional site prefix for env var names (e.g., 'aiscore')
        """
        # Validate that only one auth type is provided
        auth_types = [bearer is not None, basic is not None, cookie is not None]
        if sum(auth_types) > 1:
            msg = "Only one authentication type can be specified at a time"
            raise ValueError(msg)

        # Validate bearer token
        if bearer is not None and not bearer:
            msg = "Bearer token cannot be empty"
            raise ValueError(msg)

        # Validate basic auth credentials
        if basic is not None:
            if not basic[0] or not basic[1]:
                msg = "Basic auth username and password cannot be empty"
                raise ValueError(msg)

        # Validate cookie dict
        if cookie is not None and not cookie:
            msg = "Cookie dict cannot be empty"
            raise ValueError(msg)

        self.bearer = bearer
        self.basic = basic
        self.cookie = cookie
        self.auto_source = auto_source
        self.site_prefix = site_prefix
        self._credentials_manager: CredentialsManager | None = None

    def _get_credentials_manager(self) -> CredentialsManager:
        """Get or create CredentialsManager instance.
        
        Returns:
            CredentialsManager configured with site_prefix
        """
        if self._credentials_manager is None:
            self._credentials_manager = CredentialsManager(
                site_prefix=self.site_prefix
            )
        return self._credentials_manager

    def _resolve_credentials(self) -> None:
        """Resolve credentials from environment variables or secrets file if auto_source is enabled."""
        if not self.auto_source:
            return
        
        # If explicit credentials provided, don't override them
        if self.bearer or self.basic or self.cookie:
            return
        
        # Auto-source from env vars
        manager = self._get_credentials_manager()
        
        # Try bearer token first
        token = manager.get_bearer_token()
        if token:
            self.bearer = token
            return
        
        # Try basic auth
        basic_creds = manager.get_basic_auth()
        if basic_creds:
            self.basic = basic_creds
            return
        
        # Try cookie
        cookie = manager.get_cookie()
        if cookie:
            self.cookie = cookie

    def apply_to_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Apply authentication to request headers.
        
        If auto_source is enabled, will resolve credentials from environment
        variables or secrets file if not explicitly provided.
        """
        # Resolve credentials from env vars if auto_source enabled
        self._resolve_credentials()
        
        if self.bearer:
            headers["Authorization"] = f"Bearer {self.bearer}"
        if self.basic:
            auth_string = f"{self.basic[0]}:{self.basic[1]}"
            encoded = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        if self.cookie:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookie.items())
            headers["Cookie"] = cookie_str
        return headers


class RequestBuilderProtocol(Protocol):
    """Protocol for chainable request builder.

    Defines the interface for building HTTP requests with method chaining.
    
    Note: execute() and execute_sync() return tuple[httpx.Response, ResponseMetadata]
    on success, or NetworkError on failure. This maintains the raw response pattern
    while surfacing timestamp metadata for data freshness decisions (FR28).
    """

    def get(self, url: str) -> Self: ...
    def post(self, url: str) -> Self: ...
    def put(self, url: str) -> Self: ...
    def delete(self, url: str) -> Self: ...

    def header(self, key: str, value: str) -> Self: ...
    def param(self, key: str, value: str) -> Self: ...

    def auth(
        self,
        bearer: str | None = None,
        basic: tuple[str, str] | None = None,
        cookie: dict[str, str] | None = None,
    ) -> Self: ...

    def timeout(self, seconds: float) -> Self: ...

    def prepare(self) -> PreparedRequest: ...

    async def execute(self) -> tuple[httpx.Response, ResponseMetadata] | NetworkError: ...

    def execute_sync(self) -> tuple[httpx.Response, ResponseMetadata] | NetworkError: ...
