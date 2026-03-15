"""NetworkInterceptor for capturing network responses based on URL patterns.

This module contains the NetworkInterceptor class for network interception
with pattern matching capabilities.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.network.interception.models import CapturedResponse

from src.network.interception.exceptions import PatternError, TimingError
from src.network.interception.patterns import match_url


class NetworkInterceptor:
    """Network interceptor for capturing network responses based on URL patterns.

    This class matches network responses against specified URL patterns and
    invokes a handler callback for each matched response.

    Attributes:
        _patterns: List of URL patterns to match against
        _handler: Async callback invoked for each matched response
        _dev_logging: Enable verbose logging for debugging
        _compiled_patterns: Pre-compiled regex patterns for efficiency

    Example:
        >>> async def handle_response(response: CapturedResponse) -> None:
        ...     print(f"Captured: {response.url}")
        ...
        >>> interceptor = NetworkInterceptor(
        ...     patterns=["https://api.example.com/.*"],
        ...     handler=handle_response,
        ... )
    """

    def __init__(
        self,
        patterns: list[str],
        handler: Callable[[CapturedResponse], Awaitable[None]],
        dev_logging: bool = False,
    ) -> None:
        """Initialize NetworkInterceptor with patterns and handler.

        Args:
            patterns: List of URL patterns to match against network responses.
                Each pattern is a regex pattern that will be matched against response URLs.
            handler: Async callback invoked for each matched response.
                The handler receives a CapturedResponse object.
            dev_logging: Enable verbose logging for debugging (default: False).

        Raises:
            PatternError: If patterns list is empty, contains empty strings,
                or contains invalid regex patterns.

        Example:
            >>> async def handler(response: CapturedResponse):
            ...     print(response.url)
            >>>
            >>> interceptor = NetworkInterceptor(
            ...     patterns=["https://api.example.com/v1/.*"],
            ...     handler=handler,
            ...     dev_logging=True,
            ... )
        """
        # Validate patterns at construction time
        self._validate_patterns(patterns)

        # Store parameters
        self._patterns: list[str] = list(patterns)  # Store a copy
        self._handler: Callable[[CapturedResponse], Awaitable[None]] = handler
        self._dev_logging: bool = dev_logging

        # Pattern matching is now handled by patterns.py module
        # This allows for independent unit testing of matching logic

        # Attach state - initialized in __init__
        self._page: Any | None = None
        self._has_navigated: bool = False
        self._request_handler: Callable[[Any], None] | None = None

    def _validate_patterns(self, patterns: list[str]) -> None:
        """Validate the provided patterns list.

        Args:
            patterns: List of pattern strings to validate.

        Raises:
            PatternError: If patterns list is empty, contains empty strings,
                or contains invalid regex patterns.
        """
        # Validate non-empty list
        if not patterns:
            raise PatternError("patterns list cannot be empty")

        # Validate each pattern
        for i, pattern in enumerate(patterns):
            # Check for empty string
            if not pattern:
                raise PatternError(f"pattern at index {i} cannot be empty string")

            # Validate all patterns as regex to catch invalid syntax
            # This catches both ^-prefixed patterns and plain string patterns
            # that happen to contain invalid regex characters
            try:
                re.compile(pattern)
            except re.error as e:
                raise PatternError(
                    f"invalid regex pattern at index {i}: {pattern!r} - {e}"
                ) from None

    @property
    def patterns(self) -> list[str]:
        """Get the list of URL patterns.

        Returns:
            List of URL pattern strings.
        """
        return list(self._patterns)

    @property
    def handler(self) -> Callable[[CapturedResponse], Awaitable[None]]:
        """Get the handler callback.

        Returns:
            The async handler callback.
        """
        return self._handler

    @property
    def dev_logging(self) -> bool:
        """Get the dev_logging flag.

        Returns:
            True if dev logging is enabled, False otherwise.
        """
        return self._dev_logging

    @property
    def is_attached(self) -> bool:
        """Check if interceptor is currently attached to a page.

        Returns:
            True if attached to a page, False otherwise.
        """
        return self._page is not None

    async def attach(self, page: Any) -> None:
        """Attach the interceptor to a Playwright page.

        This method must be called BEFORE page.goto() to ensure the interceptor
        can capture all network responses from the start of navigation.

        Args:
            page: Playwright page object to attach to.

        Raises:
            RuntimeError: If interceptor is already attached to a page.
            TimingError: If page has already navigated (page.goto() was called
                before attach()). Call attach() first, then navigate.

        Example:
            >>> interceptor = NetworkInterceptor(
            ...     patterns=["https://api.example.com/.*"],
            ...     handler=handle_response,
            ... )
            >>> await interceptor.attach(page)  # Must be BEFORE page.goto()
            >>> await page.goto("https://example.com")
        """
        # Check if already attached
        if self._page is not None:
            raise RuntimeError("Interceptor already attached. Call detach() first.")

        # Check if page has already navigated (timing validation)
        if self._has_navigated:
            raise TimingError(
                "attach() must be called before page.goto(). "
                "Call attach() first, then navigate."
            )

        # Register for navigation detection
        self._page = page
        self._has_navigated = False
        self._request_handler = self._on_request
        page.on("request", self._request_handler)

    def _on_request(self, request: Any) -> None:
        """Handle incoming request to detect navigation.

        This callback is registered with Playwright's 'request' event
        to detect when navigation occurs. The first non-about:blank
        request indicates navigation has started.

        Args:
            request: Playwright request object.
        """
        # Ignore about:blank and data: URLs - these are not navigation
        url = request.url if hasattr(request, "url") else str(request)
        if url in ("about:blank", "") or url.startswith("data:"):
            return

        # First request indicates navigation has occurred
        if not self._has_navigated:
            self._has_navigated = True

    async def detach(self) -> None:
        """Detach the interceptor from the page.

        This method removes the event handler and resets the interceptor
        state. After calling detach(), the interceptor can be attached
        to a different page.
        """
        if self._page is not None and self._request_handler is not None:
            # Remove the event handler
            self._page.off("request", self._request_handler)

        # Reset state
        self._page = None
        self._has_navigated = False
        self._request_handler = None

    def _matches(self, url: str) -> bool:
        """Check if URL matches any registered pattern.

        Uses patterns.py matching functions for isolated testing.

        Matching order:
        1. String prefix matching (URL starts with pattern) - DEFAULT
        2. String substring matching (URL contains pattern) - FALLBACK
        3. Regex matching (if pattern starts with ^) - OPTIONAL

        Args:
            url: URL to check

        Returns:
            True if URL matches any pattern
        """
        return match_url(self._patterns, url)


# Backward compatibility: Keep old class names


@dataclass
class InterceptionConfig:
    """Configuration for network interception (backward compatibility).

    This is a backward-compatible class that mirrors the old InterceptionConfig.

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
    """Network response listener for Playwright browser sessions (backward compatibility).

    This is a backward-compatible class that mirrors the old NetworkListener.
    """

    def __init__(
        self,
        config: InterceptionConfig,
        on_response: Callable[[CapturedResponse], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize network listener.

        Args:
            config: Interception configuration
            on_response: Optional async callback for each captured response
        """
        self.config = config
        self._on_response = on_response
        self._captured_responses: list[CapturedResponse] = []
        self._page = None
        self._handlers: list[Any] = []

    def get_captured_responses(self) -> list[CapturedResponse]:
        """Get all captured responses."""
        return list(self._captured_responses)

    def clear_captured_responses(self) -> None:
        """Clear captured responses list."""
        self._captured_responses.clear()

    async def attach(self, page: Any) -> None:
        """Attach network listener to Playwright page."""
        self._page = page

    async def detach(self) -> None:
        """Detach listener from page and clean up."""
        self._captured_responses.clear()
        self._handlers.clear()
        self._page = None


def create_network_error(
    operation: str,
    detail: str,
    url: str | None = None,
    status_code: int | None = None,
    partial_data: Any = None,
    retryable: Any = None,
) -> Any:
    """Create a structured network error (backward compatibility)."""
    from src.network.errors import NetworkError, Retryable

    if retryable is None:
        retryable = Retryable.TERMINAL

    return NetworkError(
        module="interception",
        operation=operation,
        url=url,
        status_code=status_code,
        detail=detail,
        partial_data=partial_data,
        retryable=retryable,
    )
