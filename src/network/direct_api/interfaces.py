"""Interfaces and protocols for the direct API HTTP client (SCR-001).

This module defines the contracts for dependency injection and
the output protocol for the HTTP client.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any, Protocol, Self

import httpx

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
    """

    def __init__(
        self,
        bearer: str | None = None,
        basic: tuple[str, str] | None = None,
        cookie: dict[str, str] | None = None,
    ) -> None:
        self.bearer = bearer
        self.basic = basic
        self.cookie = cookie

    def apply_to_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Apply authentication to request headers."""
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

    async def execute(self) -> HttpResponseProtocol: ...

    def execute_sync(self) -> HttpResponseProtocol: ...
