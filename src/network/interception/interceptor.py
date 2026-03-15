"""NetworkInterceptor for capturing network responses based on URL patterns.

This module contains the NetworkInterceptor class for network interception
with pattern matching capabilities.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from src.network.interception.models import CapturedResponse

# Import for runtime use
from src.network.interception.exceptions import PatternError, TimingError
from src.network.interception.models import CapturedResponse
from src.network.interception.patterns import match_url

# Initialize logger
logger = structlog.get_logger(__name__)


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
        # Response handler can be async for async operations like body capture
        self._response_handler: Callable[[Any], Any] | None = None

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
                    f"invalid regex pattern at index {i}: {pattern!r} - {e}. "
                    "Check for: unescaped special characters, unmatched brackets, or invalid quantifiers."
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

        Timing validation uses Option D (FR10):
        1. Fast path: Check page.url - if not about:blank/about:blank#blocked, raise TimingError
        2. Confirmation: Check document.readyState via page.evaluate() - if not "loading", raise TimingError

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

        # Option D Timing Validation (FR10): Dual check for navigation status

        # Fast path: Check page.url - if not about:blank or about:blank#blocked,
        # the page has already navigated
        page_url = page.url if hasattr(page, "url") else str(page)
        if page_url not in ("about:blank", "about:blank#blocked"):
            raise TimingError(
                "attach() must be called before page.goto(). "
                "Call attach() first, then navigate."
            )

        # Confirmation: Check document.readyState via page.evaluate()
        # If not "loading", the page has already loaded/navigated
        # Note: page.evaluate() returns a coroutine in Playwright, so we await it
        try:
            ready_state: str = await page.evaluate("() => document.readyState")
        except Exception:
            # If we can't evaluate (e.g., page closed, error), assume navigation occurred
            raise TimingError(
                "attach() must be called before page.goto(). "
                "Call attach() first, then navigate."
            )

        if ready_state != "loading":
            raise TimingError(
                "attach() must be called before page.goto(). "
                "Call attach() first, then navigate."
            )

        # Also check if _has_navigated flag is set (from previous request events)
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
        # Register response listener (Story 2.2)
        self._response_handler = self._handle_response
        page.on("response", self._response_handler)

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
        """Detach the interceptor from the page and clean up resources.

        This method removes the event handlers and resets the interceptor state.
        It is safe to call multiple times (idempotent) and handles late detach
        scenarios gracefully where the page may have already been closed.

        Late detach handling:
        - Never raises exceptions even if page is closed
        - Silently handles already-removed listeners
        - Logs warning if detach called without prior attach (when dev_logging enabled)

        After calling detach(), the interceptor can be attached to a different page.
        """
        # Check if we were ever attached (for warning logging)
        was_attached = self._page is not None or self._request_handler is not None

        # Remove the event handlers if page is attached - with try/except for late detach
        if self._page is not None:
            try:
                # Remove request handler (may already be removed - that's fine)
                if self._request_handler is not None:
                    self._page.off("request", self._request_handler)

                # Remove response handler (may already be removed - that's fine)
                if self._response_handler is not None:
                    self._page.off("response", self._response_handler)
            except Exception:
                # Page closed or invalid - silently handle late detach scenario
                # Don't raise - resources will be cleaned up below
                pass
        elif self._request_handler is not None or self._response_handler is not None:
            # Edge case: handlers exist but page is None - shouldn't happen in normal flow
            # but handle gracefully without raising
            if self._dev_logging:
                logger.warning(
                    "detach_called_with_handlers_but_no_page",
                    has_request_handler=self._request_handler is not None,
                    has_response_handler=self._response_handler is not None,
                )

        # Log warning if detach called without prior attach (when dev logging enabled)
        if not was_attached and self._dev_logging:
            logger.info(
                "detach_called_without_attach",
                message="detach() called without prior attach() - no-op",
            )

        # Reset state - ready for potential reattach
        # Note: patterns and handler are set at construction and persist for reattach
        self._page = None
        self._has_navigated = False
        self._request_handler = None
        self._response_handler: Callable[[Any], Any] | None = None

        # Log cleanup completion when dev logging enabled
        if self._dev_logging:
            logger.info("interceptor_detached", message="Resources cleaned up")

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

    async def _handle_response(self, response: Any) -> None:
        """Handle Playwright response event.

        This callback is registered with Playwright's 'response' event
        to capture matched network responses.

        Args:
            response: Playwright Response object.
        """
        # 1. Match URL against patterns
        response_url = response.url if hasattr(response, "url") else str(response)
        matched = match_url(self._patterns, response_url)

        if not matched:
            return

        # 2. Capture raw bytes (handle edge cases: 204, 301, 304, race conditions)
        raw_bytes: bytes | None = None
        try:
            body = await response.body()
            raw_bytes = body if body else None
        except Exception as e:
            # Bodyless response (204, 301, 304) or race condition - raw_bytes stays None
            if self._dev_logging:
                logger.warning(
                    "response_body_capture_failed",
                    url=response_url,
                    status=getattr(response, "status", 0),
                    error=str(e),
                )
            raw_bytes = None

        # 3. Construct CapturedResponse with full data
        # Convert headers to dict (Playwright headers are case-insensitive)
        headers: dict[str, str] = {}
        if hasattr(response, "headers"):
            headers = dict(response.headers)

        captured = CapturedResponse(
            url=response_url,
            status=response.status if hasattr(response, "status") else 0,
            headers=headers,
            raw_bytes=raw_bytes,
        )

        # 4. Await async handler callback
        await self._handler(captured)


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
