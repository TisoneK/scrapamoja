"""Network interception module for capturing browser network traffic.

This module provides network response interception capabilities using Playwright.
It captures network responses that match configured URL patterns.

Following Pattern 1: Protocol-Based Interface - uses duck typing instead of inheritance.
Following Pattern 2: Error Structure - {module, operation, url, status_code, detail, partial_data}
Following Pattern 4: Config Model Structure - Pydantic model defined inside the module.

AC covered: #1, #2, #4, #5
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import structlog

from src.network.errors import NetworkError, Retryable

logger = structlog.get_logger(__name__)


@dataclass
class InterceptedResponse:
    """Represents a captured network response.

    Attributes:
        url: The full URL of the response
        status: HTTP status code
        status_text: HTTP status text
        headers: Response headers as dictionary
        body: Response body (bytes or str)
        timing: Timing information when response was captured
    """

    url: str
    status: int
    status_text: str
    headers: dict[str, str]
    body: bytes | str | None = None
    timing: float | None = None


@dataclass
class InterceptionConfig:
    """Configuration for network interception.

    Attributes:
        url_patterns: List of regex patterns to match URLs for capture
        capture_body: Whether to capture response body (default True)
        capture_headers: Whether to capture response headers (default True)
        ignore_nonmatching: Whether to silently ignore non-matching responses (default True)
    """

    url_patterns: list[str] = field(default_factory=list)
    capture_body: bool = True
    capture_headers: bool = True
    ignore_nonmatching: bool = True

    def __post_init__(self) -> None:
        """Compile regex patterns for efficiency."""
        self._compiled_patterns: list[re.Pattern[str]] = [
            re.compile(pattern) for pattern in self.url_patterns
        ]

    def matches(self, url: str) -> bool:
        """Check if URL matches any configured pattern.

        Args:
            url: URL to check

        Returns:
            True if URL matches any pattern, False otherwise
        """
        if not self._compiled_patterns:
            # If no patterns configured, capture all
            return True
        return any(pattern.match(url) for pattern in self._compiled_patterns)


class NetworkListener:
    """Network response listener for Playwright browser sessions.

    This listener attaches to a Playwright page and captures network responses
    that match configured URL patterns.

    Example:
        config = InterceptionConfig(url_patterns=[r".*api.*\\.json$"])
        listener = NetworkListener(config)

        # Attach to Playwright page before navigation
        await listener.attach(page)

        # Navigate to page - responses will be captured
        await page.goto("https://example.com")

        # Get captured responses
        responses = listener.get_captured_responses()
    """

    def __init__(
        self,
        config: InterceptionConfig,
        on_response: Callable[[InterceptedResponse], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize network listener.

        Args:
            config: Interception configuration
            on_response: Optional async callback for each captured response
        """
        self.config = config
        self._on_response = on_response
        self._captured_responses: list[InterceptedResponse] = []
        self._page = None
        self._handlers: list[Any] = []
        self._lock = asyncio.Lock()

    async def attach(self, page: Any) -> None:
        """Attach network listener to Playwright page.

        Must be called BEFORE navigation to ensure all responses are captured.

        Args:
            page: Playwright page object
        """
        self._page = page

        # Register response handler
        async def handle_response(response: Any) -> None:
            await self._handle_response(response)

        self._handlers.append(handle_response)
        page.on("response", handle_response)

        logger.info(
            "network_listener_attached",
            patterns=self.config.url_patterns,
            capture_body=self.config.capture_body,
        )

    async def _handle_response(self, response: Any) -> None:
        """Handle a network response event.

        Args:
            response: Playwright response object
        """
        url = response.url
        status = response.status

        # Check if URL matches patterns
        if not self.config.matches(url):
            if self.config.ignore_nonmatching:
                return
            # Log but don't capture non-matching
            logger.debug("network_response_ignored", url=url, status=status)
            return

        # Build headers
        headers: dict[str, str] = {}
        if self.config.capture_headers:
            try:
                headers = dict(response.headers)
            except Exception as e:
                logger.warning("failed_to_capture_headers", url=url, error=str(e))

        # Build response object
        intercepted = InterceptedResponse(
            url=url,
            status=status,
            status_text=response.status_text,
            headers=headers,
            timing=None,  # Playwright doesn't provide easy timing in response
        )

        # Capture body if requested
        if self.config.capture_body:
            try:
                body = await response.body()
                intercepted.body = body
            except Exception as e:
                logger.warning("failed_to_capture_body", url=url, error=str(e))

        # Store response
        async with self._lock:
            self._captured_responses.append(intercepted)

        # Call callback if set
        if self._on_response:
            try:
                await self._on_response(intercepted)
            except Exception as e:
                logger.warning("response_callback_failed", url=url, error=str(e))

        logger.debug(
            "network_response_captured",
            url=url,
            status=status,
            body_size=len(intercepted.body) if intercepted.body else 0,
        )

    def get_captured_responses(self) -> list[InterceptedResponse]:
        """Get all captured responses.

        Returns:
            List of captured InterceptedResponse objects
        """
        return list(self._captured_responses)

    def clear_captured_responses(self) -> None:
        """Clear captured responses list."""
        self._captured_responses.clear()

    async def detach(self) -> None:
        """Detach listener from page and clean up."""
        self._captured_responses.clear()
        self._handlers.clear()
        self._page = None

        logger.info("network_listener_detached")


def create_network_error(
    operation: str,
    detail: str,
    url: str | None = None,
    status_code: int | None = None,
    partial_data: Any = None,
    retryable: Retryable = Retryable.TERMINAL,
) -> NetworkError:
    """Create a structured network error for interception operations.

    Args:
        operation: The operation that failed
        detail: Human-readable error detail
        url: Optional URL being accessed
        status_code: Optional HTTP status code
        partial_data: Optional partial data retrieved before failure
        retryable: Whether the error is retryable

    Returns:
        NetworkError with all details
    """
    return NetworkError(
        module="interception",
        operation=operation,
        url=url,
        status_code=status_code,
        detail=detail,
        partial_data=partial_data,
        retryable=retryable,
    )
