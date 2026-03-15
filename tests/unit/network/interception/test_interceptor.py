"""Tests for NetworkInterceptor constructor, attach, and pattern validation."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from collections.abc import Awaitable, Callable

from src.network.interception import NetworkInterceptor, CapturedResponse, PatternError, TimingError


class TestNetworkInterceptorConstructor:
    """Tests for NetworkInterceptor.__init__ method."""

    @pytest.fixture
    def valid_handler(self) -> Callable[[CapturedResponse], Awaitable[None]]:
        """Create a valid async handler for testing."""

        async def handler(response: CapturedResponse) -> None:
            pass

        return handler

    def test_constructor_valid_patterns(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test that constructor creates interceptor with valid patterns."""
        patterns = [r"https://example\.com/api/.*", r"https://api\.example\.com/v1/.*"]

        interceptor = NetworkInterceptor(
            patterns=patterns,
            handler=valid_handler,
        )

        assert interceptor._patterns == patterns
        assert interceptor._handler is valid_handler
        assert interceptor._dev_logging is False

    def test_constructor_single_pattern(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test constructor with single pattern."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        assert interceptor._patterns == [r"https://example\.com/.*"]

    def test_constructor_empty_patterns_raises_error(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test that empty patterns list raises PatternError."""
        with pytest.raises(PatternError) as exc_info:
            NetworkInterceptor(
                patterns=[],
                handler=valid_handler,
            )

        assert "empty" in str(exc_info.value).lower()

    def test_constructor_empty_string_pattern_raises_error(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test that empty string in patterns raises PatternError."""
        with pytest.raises(PatternError) as exc_info:
            NetworkInterceptor(
                patterns=["https://example.com/", "", "https://api.example.com/"],
                handler=valid_handler,
            )

        assert "empty" in str(exc_info.value).lower()

    def test_constructor_invalid_regex_raises_error(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test that invalid regex pattern (with ^ prefix) raises PatternError."""
        # Only patterns starting with ^ are validated as regex
        with pytest.raises(PatternError) as exc_info:
            NetworkInterceptor(
                patterns=[r"^https://example\.com/[unclosed"],
                handler=valid_handler,
            )

        assert (
            "regex" in str(exc_info.value).lower()
            or "pattern" in str(exc_info.value).lower()
        )

    def test_constructor_invalid_regex_bracket_error(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test that invalid regex with unclosed bracket (with ^ prefix) raises PatternError."""
        # Only patterns starting with ^ are validated as regex
        with pytest.raises(PatternError) as exc_info:
            NetworkInterceptor(
                patterns=["^[invalid"],
                handler=valid_handler,
            )

        assert (
            "regex" in str(exc_info.value).lower()
            or "pattern" in str(exc_info.value).lower()
        )

    def test_constructor_dev_logging_default_false(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test that dev_logging defaults to False."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        assert interceptor._dev_logging is False

    def test_constructor_dev_logging_true(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test that dev_logging can be set to True."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
            dev_logging=True,
        )

        assert interceptor._dev_logging is True

    def test_constructor_stores_handler(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test that handler is stored correctly."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        assert interceptor._handler is valid_handler

    def test_constructor_stores_patterns(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test that patterns are stored correctly."""
        patterns = [r"https://api\.example\.com/v1/", r"https://api\.example\.com/v2/"]
        interceptor = NetworkInterceptor(
            patterns=patterns,
            handler=valid_handler,
        )

        assert interceptor._patterns == patterns

    def test_constructor_patterns_are_copied(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test that patterns list is stored (not referenced)."""
        original_patterns = [r"https://example\.com/.*"]
        interceptor = NetworkInterceptor(
            patterns=original_patterns,
            handler=valid_handler,
        )

        # Modify original list after construction
        original_patterns.append(r"https://other.com/.*")

        # Interceptor should still have original patterns
        assert len(interceptor._patterns) == 1
        assert interceptor._patterns[0] == r"https://example\.com/.*"


class TestNetworkInterceptorAttach:
    """Tests for NetworkInterceptor.attach() method."""

    @pytest.fixture
    def valid_handler(self) -> Callable[[CapturedResponse], Awaitable[None]]:
        """Create a valid async handler for testing."""

        async def handler(response: CapturedResponse) -> None:
            pass

        return handler

    @pytest.fixture
    def mock_page(self) -> MagicMock:
        """Create a mock Playwright page object."""
        page = MagicMock()
        # Set up event handlers storage
        page._event_handlers = {}

        def mock_on(event: str, handler: Callable) -> None:
            page._event_handlers[event] = handler

        def mock_off(event: str, handler: Callable) -> None:
            page._event_handlers.pop(event, None)

        page.on = mock_on
        page.off = mock_off
        return page

    @pytest.mark.asyncio
    async def test_attach_success_before_navigation(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]], mock_page: MagicMock
    ) -> None:
        """Test that attach() succeeds when called before navigation."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        # Should not raise
        await interceptor.attach(mock_page)

        # Verify page is attached
        assert interceptor._page is mock_page
        assert interceptor.is_attached is True
        assert interceptor._has_navigated is False

    @pytest.mark.asyncio
    async def test_attach_registers_request_handler(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]], mock_page: MagicMock
    ) -> None:
        """Test that attach() registers the request handler."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        await interceptor.attach(mock_page)

        # Verify handler was registered
        assert "request" in mock_page._event_handlers
        assert mock_page._event_handlers["request"] is not None

    @pytest.mark.asyncio
    async def test_attach_raises_when_already_attached(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]], mock_page: MagicMock
    ) -> None:
        """Test that attach() raises RuntimeError when already attached."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        # First attach should succeed
        await interceptor.attach(mock_page)

        # Second attach should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            await interceptor.attach(mock_page)

        assert "already attached" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_attach_raises_timing_error_after_navigation(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]], mock_page: MagicMock
    ) -> None:
        """Test that attach() raises TimingError when page has already navigated."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        # Simulate that navigation has already occurred
        interceptor._has_navigated = True

        # attach() should raise TimingError
        with pytest.raises(TimingError) as exc_info:
            await interceptor.attach(mock_page)

        assert "attach() must be called before page.goto()" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_attach_timing_error_exact_message(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]], mock_page: MagicMock
    ) -> None:
        """Test that attach() raises TimingError with exact required message."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        # Simulate that navigation has already occurred
        interceptor._has_navigated = True

        # attach() should raise TimingError with exact message
        with pytest.raises(TimingError) as exc_info:
            await interceptor.attach(mock_page)

        expected_msg = "attach() must be called before page.goto(). Call attach() first, then navigate."
        assert str(exc_info.value) == expected_msg


class TestNetworkInterceptorDetach:
    """Tests for NetworkInterceptor.detach() method."""

    @pytest.fixture
    def valid_handler(self) -> Callable[[CapturedResponse], Awaitable[None]]:
        """Create a valid async handler for testing."""

        async def handler(response: CapturedResponse) -> None:
            pass

        return handler

    @pytest.fixture
    def mock_page(self) -> MagicMock:
        """Create a mock Playwright page object."""
        page = MagicMock()
        page._event_handlers = {}

        def mock_on(event: str, handler: Callable) -> None:
            page._event_handlers[event] = handler

        def mock_off(event: str, handler: Callable) -> None:
            page._event_handlers.pop(event, None)

        page.on = mock_on
        page.off = mock_off
        return page

    @pytest.mark.asyncio
    async def test_detach_removes_handler(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]], mock_page: MagicMock
    ) -> None:
        """Test that detach() removes the request handler."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        # Attach first
        await interceptor.attach(mock_page)
        assert "request" in mock_page._event_handlers

        # Detach
        await interceptor.detach()

        # Handler should be removed
        assert "request" not in mock_page._event_handlers

    @pytest.mark.asyncio
    async def test_detach_resets_state(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]], mock_page: MagicMock
    ) -> None:
        """Test that detach() resets interceptor state."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        # Attach and simulate navigation
        await interceptor.attach(mock_page)
        interceptor._has_navigated = True

        # Detach
        await interceptor.detach()

        # State should be reset
        assert interceptor._page is None
        assert interceptor._has_navigated is False
        assert interceptor._request_handler is None
        assert interceptor.is_attached is False


class TestNetworkInterceptorOnRequest:
    """Tests for NetworkInterceptor._on_request navigation detection."""

    @pytest.fixture
    def valid_handler(self) -> Callable[[CapturedResponse], Awaitable[None]]:
        """Create a valid async handler for testing."""

        async def handler(response: CapturedResponse) -> None:
            pass

        return handler

    @pytest.fixture
    def mock_page(self) -> MagicMock:
        """Create a mock Playwright page object."""
        page = MagicMock()
        page._event_handlers = {}

        def mock_on(event: str, handler: Callable) -> None:
            page._event_handlers[event] = handler

        def mock_off(event: str, handler: Callable) -> None:
            page._event_handlers.pop(event, None)

        page.on = mock_on
        page.off = mock_off
        return page

    def test_on_request_sets_navigated(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]], mock_page: MagicMock
    ) -> None:
        """Test that _on_request sets _has_navigated to True on first request."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        # Attach to page
        interceptor._page = mock_page
        interceptor._has_navigated = False

        # Simulate request
        mock_request = MagicMock()
        mock_request.url = "https://example.com/page"

        interceptor._on_request(mock_request)

        # Navigation should be detected
        assert interceptor._has_navigated is True

    def test_on_request_ignores_about_blank(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]], mock_page: MagicMock
    ) -> None:
        """Test that _on_request ignores about:blank URLs."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        interceptor._page = mock_page
        interceptor._has_navigated = False

        # Simulate about:blank request
        mock_request = MagicMock()
        mock_request.url = "about:blank"

        interceptor._on_request(mock_request)

        # Navigation should NOT be detected
        assert interceptor._has_navigated is False

    def test_on_request_ignores_data_url(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]], mock_page: MagicMock
    ) -> None:
        """Test that _on_request ignores data: URLs."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        interceptor._page = mock_page
        interceptor._has_navigated = False

        # Simulate data: URL request
        mock_request = MagicMock()
        mock_request.url = "data:text/html,<html></html>"

        interceptor._on_request(mock_request)

        # Navigation should NOT be detected
        assert interceptor._has_navigated is False

    def test_on_request_navigation_only_triggers_once(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]], mock_page: MagicMock
    ) -> None:
        """Test that navigation detection only triggers on first request."""
        interceptor = NetworkInterceptor(
            patterns=[r"https://example\.com/.*"],
            handler=valid_handler,
        )

        interceptor._page = mock_page
        interceptor._has_navigated = False

        # First request triggers navigation
        mock_request1 = MagicMock()
        mock_request1.url = "https://example.com/page1"
        interceptor._on_request(mock_request1)
        assert interceptor._has_navigated is True

        # Second request should not change state
        mock_request2 = MagicMock()
        mock_request2.url = "https://example.com/page2"
        interceptor._on_request(mock_request2)
        assert interceptor._has_navigated is True

    def test_constructor_stores_compiled_patterns(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test that patterns are stored and can be matched using patterns.py."""
        patterns = ["https://example.com/api/v1", "https://api.example.com/data"]
        interceptor = NetworkInterceptor(
            patterns=patterns,
            handler=valid_handler,
        )

        # Check that patterns are stored
        assert hasattr(interceptor, "_patterns")
        assert len(interceptor._patterns) == 2

        # Verify matching works via _matches method (uses patterns.py)
        assert interceptor._matches("https://example.com/api/v1/users") is True
        assert interceptor._matches("https://api.example.com/data/123") is True
        assert interceptor._matches("https://other.com") is False

    def test_constructor_with_special_regex_chars(
        self, valid_handler: Callable[[CapturedResponse], Awaitable[None]]
    ) -> None:
        """Test constructor with patterns containing special regex characters."""
        patterns = [
            r"https://example\.com/api\?foo=bar&baz=qux",
            r"https://api\.example\.com/v1/.*\.json$",
        ]

        interceptor = NetworkInterceptor(
            patterns=patterns,
            handler=valid_handler,
        )

        assert interceptor._patterns == patterns
