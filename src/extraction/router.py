"""Extraction mode router/factory implementation.

This module implements the extraction mode routing factory that selects
the appropriate extraction handler based on site configuration.

Following Pattern 1: Protocol-Based Interface - uses duck typing instead of inheritance.
"""

from typing import Any, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from src.network.direct_api import AsyncHttpClient
    from src.network.interception import NetworkListener
    from src.network.session import SessionPackage, SessionValidator

# Import SessionValidator for use in HybridExtractionHandler
from src.network.session import SessionValidator

from src.extraction.exceptions import (
    ExtractionModeNotSupportedError,
    InvalidExtractionModeError,
)
from src.extraction.interfaces import ExtractionHandlerProtocol
from src.sites.base.site_config import ExtractionMode, SiteConfig

# Valid extraction modes
VALID_EXTRACTION_MODES = {mode.value for mode in ExtractionMode}


class ExtractionModeRouter:
    """Router for selecting extraction mode handler based on configuration.

    This factory creates the appropriate extraction handler based on the
    extraction_mode specified in the site configuration.

    Example:
        from src.sites.base import SiteConfigLoader
        from src.extraction import ExtractionModeRouter

        config = SiteConfigLoader("flashscore").load()
        router = ExtractionModeRouter(config)
        handler = router.get_handler()

        # Use handler for extraction
        result = await handler.extract(...)
    """

    def __init__(self, config: SiteConfig) -> None:
        """Initialize the router with site configuration.

        Args:
            config: SiteConfig instance containing extraction mode setting
        """
        self._config = config

    @property
    def config(self) -> SiteConfig:
        """Get the site configuration."""
        return self._config

    @property
    def extraction_mode(self) -> str:
        """Get the extraction mode from configuration.

        Returns:
            The extraction mode string (e.g., 'raw', 'intercepted')
        """
        # Pydantic's use_enum_values=True converts enums to strings automatically
        # so get_extraction_mode() already returns a string
        return self._config.get_extraction_mode()

    def _validate_mode(self) -> None:
        """Validate that the extraction mode is valid.

        Raises:
            InvalidExtractionModeError: If mode is not recognized
        """
        mode = self.extraction_mode

        if mode not in VALID_EXTRACTION_MODES:
            raise InvalidExtractionModeError(mode)

    def get_handler(self) -> ExtractionHandlerProtocol:
        """Get the appropriate extraction handler for the configured mode.

        This method implements the routing logic based on the extraction_mode
        specified in the site configuration.

        Returns:
            ExtractionHandlerProtocol: Handler for the configured mode

        Raises:
            InvalidExtractionModeError: If mode is not recognized
            ExtractionModeNotSupportedError: If mode is not yet implemented
        """
        self._validate_mode()
        mode = self.extraction_mode

        # Route to appropriate handler based on mode
        if mode in (ExtractionMode.RAW.value, "direct"):
            return self._create_raw_handler()
        elif mode == ExtractionMode.INTERCEPTED.value:
            return self._create_intercepted_handler()
        elif mode == ExtractionMode.HYBRID.value:
            return self._create_hybrid_handler()
        elif mode == ExtractionMode.PLAYWRIGHT.value:
            return self._create_playwright_handler()
        else:
            raise ExtractionModeNotSupportedError(mode)

    def _create_raw_handler(self) -> "RawExtractionHandler":
        """Create handler for raw (Direct API) mode.

        Returns:
            RawExtractionHandler: Handler using Epic 1 HTTP transport
        """
        return RawExtractionHandler(
            endpoint=self._config.endpoint,
            timeout=self._config.timeout,
            rate_limit=self._config.rate_limit,
        )

    def _create_intercepted_handler(self) -> "InterceptedExtractionHandler":
        """Create handler for intercepted mode.

        Returns:
            InterceptedExtractionHandler: Handler for network capture mode
        """
        # Get interception config from site config
        intercepted_config = self._config.get_intercepted_config()
        url_patterns = None
        capture_body = True
        capture_headers = True
        browser_config = None

        if intercepted_config:
            url_patterns = intercepted_config.url_patterns
            capture_body = intercepted_config.capture_body
            capture_headers = intercepted_config.capture_headers
            browser_config = getattr(intercepted_config, 'browser_config', None)

        return InterceptedExtractionHandler(
            endpoint=self._config.endpoint,
            site_name=self._config.site_name,
            url_patterns=url_patterns,
            capture_body=capture_body,
            capture_headers=capture_headers,
            browser_config=browser_config,
        )

    def _create_hybrid_handler(self) -> "HybridExtractionHandler":
        """Create handler for hybrid mode.

        Returns:
            HybridExtractionHandler: Handler combining browser + HTTP
        """
        return HybridExtractionHandler(
            endpoint=self._config.endpoint,
            site_name=self._config.site_name,
        )

    def _create_playwright_handler(self) -> "PlaywrightExtractionHandler":
        """Create handler for DOM/Playwright mode.

        Returns:
            PlaywrightExtractionHandler: Handler using browser automation
        """
        return PlaywrightExtractionHandler(
            endpoint=self._config.endpoint,
            site_name=self._config.site_name,
        )


class RawExtractionHandler:
    """Handler for raw (Direct API) mode.

    Uses the Epic 1 HTTP transport for making requests without browser.
    """

    def __init__(
        self,
        endpoint: str,
        timeout: int = 30,
        rate_limit: float | None = None,
    ) -> None:
        """Initialize raw extraction handler.

        Args:
            endpoint: Base URL endpoint
            timeout: Request timeout in seconds
            rate_limit: Optional rate limit in requests per second
        """
        self.endpoint = endpoint
        self.timeout = timeout
        self.rate_limit = rate_limit
        self._client = None

    async def _get_client(self):
        """Get or create the HTTP client (reuses existing client)."""
        if self._client is None:
            from src.network.direct_api import AsyncHttpClient
            self._client = AsyncHttpClient(
                base_url=self.endpoint,
                rate_limit=self.rate_limit or 10.0,
            )
        return self._client

    async def extract(self, url: str, **kwargs: Any) -> Any:
        """Extract data using Direct API mode.

        Args:
            url: URL to fetch
            **kwargs: Additional request parameters

        Returns:
            Response from HTTP client
        """
        client = await self._get_client()
        async with client:
            response = await client.get(url).execute()
            return response

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None

    def __repr__(self) -> str:
        return f"RawExtractionHandler(endpoint={self.endpoint!r})"


class InterceptedExtractionHandler:
    """Handler for intercepted API mode.

    Network capture mode using Playwright network interception.
    Captures network responses that match configured URL patterns.
    """

    def __init__(
        self,
        endpoint: str,
        site_name: str,
        url_patterns: list[str] | None = None,
        capture_body: bool = True,
        capture_headers: bool = True,
        browser_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize intercepted extraction handler.

        Args:
            endpoint: Base URL endpoint
            site_name: Name of the site
            url_patterns: List of regex patterns to match URLs for capture
            capture_body: Whether to capture response body
            capture_headers: Whether to capture response headers
            browser_config: Optional browser launch configuration
                - headless: bool (default True)
                - stealth: bool (default False)
                - user_agent: str (optional)
                - viewport: dict with width/height (optional)
        """
        self.endpoint = endpoint
        self.site_name = site_name
        self._url_patterns = url_patterns or []
        self._capture_body = capture_body
        self._capture_headers = capture_headers
        self._browser_config = browser_config or {"headless": True}
        self._listener = None
        self._page = None

    def _create_listener(self) -> "NetworkListener":
        """Create network listener with configuration."""
        from src.network.interception import InterceptionConfig, NetworkListener

        config = InterceptionConfig(
            url_patterns=self._url_patterns,
            capture_body=self._capture_body,
            capture_headers=self._capture_headers,
        )
        return NetworkListener(config)

    async def extract(
        self,
        url: str | None = None,
        page: Any | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        """Extract data using intercepted API mode.

        Args:
            url: URL to navigate to (if no page provided)
            page: Optional Playwright page to use for extraction
            **kwargs: Additional parameters

        Returns:
            List of captured network responses
        """
        if page is None and url is None:
            raise ValueError("Either page or url must be provided")

        # Create listener
        self._listener = self._create_listener()

        # If page provided, attach listener to it
        if page is not None:
            self._page = page
            await self._listener.attach(page)
            return []

        # Otherwise, create a browser session and navigate
        from playwright.async_api import async_playwright

        # Use configurable browser settings
        browser_kwargs = {}
        if self._browser_config.get("headless", True):
            browser_kwargs["headless"] = True
        if self._browser_config.get("stealth", False):
            # Stealth mode requires additional setup
            browser_kwargs["args"] = ["--disable-blink-features=AutomationControlled"]

        async with async_playwright() as p:
            browser = await p.chromium.launch(**browser_kwargs)

            # Configure page with optional settings
            page_options = {}
            if "viewport" in self._browser_config:
                page_options["viewport"] = self._browser_config["viewport"]
            if "user_agent" in self._browser_config:
                page_options["user_agent"] = self._browser_config["user_agent"]

            page = await browser.new_page(**page_options)
            self._page = page

            # Attach listener BEFORE navigation
            await self._listener.attach(page)

            # Navigate to URL
            await page.goto(url)

            # Wait for network to settle
            await page.wait_for_load_state("networkidle")

            # Get captured responses
            responses = self._listener.get_captured_responses()

            await browser.close()

            return responses

    def get_captured_responses(self) -> list[Any]:
        """Get captured network responses.

        Returns:
            List of InterceptedResponse objects
        """
        if self._listener is None:
            return []
        return self._listener.get_captured_responses()

    async def close(self) -> None:
        """Close the handler and clean up resources."""
        if self._listener is not None:
            await self._listener.detach()
            self._listener = None
        if self._page is not None:
            await self._page.close()
            self._page = None

    def __repr__(self) -> str:
        return f"InterceptedExtractionHandler(site_name={self.site_name!r})"


class HybridExtractionHandler:
    """Handler for hybrid mode (Session Bootstrap).

    Combines browser session with HTTP requests in a two-phase flow:
    - Phase 1 (Bootstrap): Launch browser, navigate to site, harvest session,
      close browser
    - Phase 2 (Extract): Use harvested credentials for direct HTTP calls

    This handler follows ExtractionHandlerProtocol for consistency.
    """

    def __init__(
        self,
        endpoint: str,
        site_name: str,
        session_ttl: int | None = None,
        browser_config: dict[str, Any] | None = None,
        force_bootstrap: bool = False,
    ) -> None:
        """Initialize hybrid extraction handler.

        Args:
            endpoint: Base URL endpoint
            site_name: Name of the site
            session_ttl: Optional session time-to-live in seconds
            browser_config: Optional browser launch configuration
                - headless: bool (default True)
                - stealth: bool (default False)
                - user_agent: str (optional)
                - viewport: dict with width/height (optional)
            force_bootstrap: If True, always perform fresh bootstrap
        """
        self.endpoint = endpoint
        self.site_name = site_name
        self._session_ttl = session_ttl
        self._browser_config = browser_config or {"headless": True}
        self._force_bootstrap = force_bootstrap

        # Session state
        self._session: SessionPackage | None = None
        self._client: AsyncHttpClient | None = None

        # Validator for session freshness
        self._validator = SessionValidator(session_ttl=session_ttl)

        # Track if bootstrap is needed
        self._needs_bootstrap = True

    async def _bootstrap(self) -> SessionPackage:
        """Perform browser bootstrap to harvest session.

        Returns:
            SessionPackage with harvested credentials
        """
        from playwright.async_api import async_playwright

        from src.network.session import SessionHarvester

        # Configure browser launch
        browser_kwargs = {}
        if self._browser_config.get("headless", True):
            browser_kwargs["headless"] = True
        if self._browser_config.get("stealth", False):
            browser_kwargs["args"] = ["--disable-blink-features=AutomationControlled"]

        async with async_playwright() as p:
            browser = await p.chromium.launch(**browser_kwargs)

            # Configure page with optional settings
            page_options = {}
            if "viewport" in self._browser_config:
                page_options["viewport"] = self._browser_config["viewport"]
            if "user_agent" in self._browser_config:
                page_options["user_agent"] = self._browser_config["user_agent"]

            page = await browser.new_page(**page_options)

            # Navigate to the endpoint (use the base URL for initial navigation)
            await page.goto(self.endpoint)

            # Wait for page to be fully loaded
            await page.wait_for_load_state("networkidle")

            # Harvest session from the page
            harvester = SessionHarvester()
            session = await harvester.harvest(page, site_name=self.site_name)

            # Close browser after harvesting (AC #6: no browser process remaining)
            await browser.close()

            return session

    async def _ensure_client(self) -> "AsyncHttpClient":
        """Get or create HTTP client with harvested session credentials.

        Returns:
            Configured AsyncHttpClient
        """
        from src.network.direct_api import AsyncHttpClient

        if self._client is None:
            # Create client with base URL
            rate_limit = self._browser_config.get("rate_limit", 10.0)
            self._client = AsyncHttpClient(
                base_url=self.endpoint,
                rate_limit=rate_limit,
            )

        return self._client

    def _build_request(self, url: str):
        """Build a request with session credentials applied.

        Args:
            url: URL to request

        Returns:
            RequestBuilder with credentials applied
        """
        # Get the request builder
        client = self._client  # Already created in _ensure_client
        builder = client.get(url)

        # Apply session cookies if available
        if self._session and self._session.cookies:
            cookie_header = self._session.to_cookie_header()
            builder = builder.header("Cookie", cookie_header)

        # Apply auth headers if available
        if self._session:
            # Apply Bearer token if present
            bearer = self._session.get_bearer_token()
            if bearer:
                builder = builder.auth(bearer=bearer)

            # Apply other auth headers
            for header in self._session.headers:
                if header.is_auth_header:
                    builder = builder.header(header.name, header.value)

        # Set user agent if available
        if self._session and self._session.user_agent:
            builder = builder.header("User-Agent", self._session.user_agent)

        return builder

    async def _bootstrap_if_needed(self) -> None:
        """Bootstrap session if needed (lazy initialization).

        This implements the two-phase flow: bootstrap once, then extract.
        """
        if self._needs_bootstrap or self._force_bootstrap:
            # Phase 1: Bootstrap - harvest session from browser
            self._session = await self._bootstrap()
            self._needs_bootstrap = False

            # Reset auth failure count after successful bootstrap
            self._validator.reset_auth_failures()

    async def extract(self, url: str, **kwargs: Any) -> Any:
        """Extract data using hybrid mode.

        Implements two-phase flow:
        1. First call: Launch browser, harvest session, close browser
        2. Subsequent calls: Use harvested credentials for direct HTTP

        Args:
            url: URL to fetch
            **kwargs: Additional request parameters

        Returns:
            Response from HTTP client
        """
        # Phase 1: Bootstrap if needed (first call or forced)
        await self._bootstrap_if_needed()

        # Phase 2: Use harvested session for HTTP requests
        try:
            client = await self._ensure_client()
            async with client:
                # Build request with session credentials
                builder = self._build_request(url)
                response = await builder.execute()
                return response
        except Exception as e:
            # Check if this is an auth error that requires re-bootstrap
            # NetworkError has status_code attribute
            error_status = getattr(e, "status_code", None)
            if error_status and self._validator.is_auth_error(error_status):
                # Trigger re-bootstrap
                self._needs_bootstrap = True
                self._client = None  # Reset client

                # Check if we've hit max failures
                if self._validator.record_auth_failure():
                    # Attempt re-bootstrap once
                    await self._bootstrap_if_needed()

                    # Try again with fresh session
                    client = await self._ensure_client()
                    async with client:
                        builder = self._build_request(url)
                        response = await builder.execute()
                        return response

            raise

    async def close(self) -> None:
        """Close the handler and clean up resources."""
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None
        self._session = None
        self._needs_bootstrap = True

    def get_session(self) -> SessionPackage | None:
        """Get the current session package.

        Returns:
            Current SessionPackage if available, None otherwise
        """
        return self._session

    def is_bootstrap_needed(self) -> bool:
        """Check if bootstrap is needed.

        Returns:
            True if next extract() call will trigger bootstrap
        """
        return self._needs_bootstrap

    def __repr__(self) -> str:
        return f"HybridExtractionHandler(site_name={self.site_name!r})"


class PlaywrightExtractionHandler:
    """Handler for DOM/Playwright mode.

    Uses browser automation for extraction - placeholder for future implementation.
    """

    def __init__(self, endpoint: str, site_name: str) -> None:
        """Initialize playwright extraction handler.

        Args:
            endpoint: Base URL endpoint
            site_name: Name of the site
        """
        self.endpoint = endpoint
        self.site_name = site_name

    async def extract(self, url: str, **kwargs: Any) -> Any:
        """Extract data using Playwright/DOM mode.

        Note: This is a placeholder - DOM Mode is handled by existing scraper.

        Args:
            url: URL to fetch
            **kwargs: Additional parameters

        Returns:
            Placeholder return
        """
        raise NotImplementedError(
            "Playwright/DOM Mode is not yet implemented in extraction router. "
            "Use site-specific scraper classes for DOM extraction."
        )

    async def close(self) -> None:
        """Close the handler and clean up resources."""
        pass

    def __repr__(self) -> str:
        return f"PlaywrightExtractionHandler(site_name={self.site_name!r})"


# Convenience function for creating router from config
def create_extraction_router(config: SiteConfig) -> ExtractionModeRouter:
    """Create an extraction mode router from site configuration.

    Args:
        config: SiteConfig instance

    Returns:
        Configured ExtractionModeRouter instance
    """
    return ExtractionModeRouter(config)
