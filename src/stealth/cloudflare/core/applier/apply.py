"""Stealth profile applier implementation.

This module provides the StealthProfileApplier class which applies all stealth
configurations to Playwright browser contexts in the correct order.

Module: src.stealth.cloudflare.core.applier.apply

Classes:
    StealthProfileApplier: Applies all stealth configurations to browser contexts.
"""

from typing import Any, Optional, Set, TYPE_CHECKING

from src.observability.logger import get_logger
from src.stealth.cloudflare.models.config import CloudflareConfig

if TYPE_CHECKING:
    try:
        from playwright.async_api import BrowserContext
    except ImportError:
        BrowserContext = Any

logger = get_logger("cloudflare.applier")


class StealthProfileApplierError(Exception):
    """Exception raised when stealth profile application fails."""

    pass


class StealthProfileApplier:
    """Applies all stealth configurations to a Playwright browser context.

    This class orchestrates the application of all stealth components in the
    correct order:
    1. WebDriverMask (2.1) - Suppress navigator.webdriver
    2. CanvasFingerprintRandomizer (2.2) - Randomize canvas/WebGL
    3. UserAgentManager (2.3) - Set user agent
    4. ViewportNormalizer (2.4) - Set viewport dimensions

    All components are only applied if their corresponding feature flags
    are enabled in the CloudflareConfig.

    Attributes:
        config: The CloudflareConfig instance with feature flags.
        enabled: Whether any stealth component is enabled.

    Example:
        ```python
        from playwright.async_api import async_playwright
        from src.stealth.cloudflare.config import CloudflareConfig
        from src.stealth.cloudflare.core.applier import StealthProfileApplier

        async def main():
            config = CloudflareConfig(
                cloudflare_protected=True,
                webdriver_enabled=True,
                fingerprint_enabled=True,
                user_agent_enabled=True,
                viewport_enabled=True,
            )
            applier = StealthProfileApplier(config)
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context()
                await applier.apply(context)
                # Context now has all stealth configurations applied
        ```
    """

    def __init__(
        self,
        config: Optional[CloudflareConfig] = None,
    ) -> None:
        """Initialize the StealthProfileApplier.

        Args:
            config: Optional CloudflareConfig instance. If not provided,
                components will not be initialized until config is provided
                via apply() method.

        Raises:
            StealthProfileApplierError: If initialization fails.
        """
        self.config = config

        from src.stealth.cloudflare.core.webdriver import WebdriverMasker
        from src.stealth.cloudflare.core.fingerprint import CanvasFingerprintRandomizer
        from src.stealth.cloudflare.core.user_agent import UserAgentManager
        from src.stealth.cloudflare.core.viewport import ViewportNormalizer

        self._webdriver: Optional[WebdriverMasker] = None
        self._fingerprint: Optional[CanvasFingerprintRandomizer] = None
        self._user_agent: Optional[UserAgentManager] = None
        self._viewport: Optional[ViewportNormalizer] = None

        if config is not None and config.is_enabled():
            if config.webdriver_enabled:
                self._webdriver = WebdriverMasker()
            if config.fingerprint_enabled:
                self._fingerprint = CanvasFingerprintRandomizer()
            if config.user_agent_enabled:
                self._user_agent = UserAgentManager(config=config)
            if config.viewport_enabled:
                self._viewport = ViewportNormalizer(config=config)

        logger.info(
            "StealthProfileApplier initialized",
            extra={
                "config_provided": config is not None,
                "cloudflare_protected": config.is_enabled() if config else False,
                "webdriver_enabled": self._webdriver is not None,
                "fingerprint_enabled": self._fingerprint is not None,
                "user_agent_enabled": self._user_agent is not None,
                "viewport_enabled": self._viewport is not None,
            },
        )

    @property
    def enabled(self) -> bool:
        """Check if any stealth component is enabled.

        Returns:
            True if at least one component is enabled.
        """
        return any(
            [
                self._webdriver is not None,
                self._fingerprint is not None,
                self._user_agent is not None,
                self._viewport is not None,
            ]
        )

    async def apply(
        self,
        context: "BrowserContext",
    ) -> None:
        """Apply all enabled stealth configurations to the browser context.

        This method applies components in the correct order, checking each
        component's enabled state before application.

        Args:
            context: The Playwright browser context to modify.

        Raises:
            StealthProfileApplierError: If any component fails to apply.
        """
        if not self.enabled:
            logger.debug("All stealth components disabled, skipping application")
            return

        if self.config is None or not self.config.is_enabled():
            logger.debug("Cloudflare protection not enabled, skipping application")
            return

        errors: list[tuple[str, Exception]] = []

        if self._webdriver is not None:
            try:
                await self._webdriver.apply(context, enabled=True)
                logger.debug("WebDriver mask applied")
            except Exception as e:
                errors.append(("webdriver", e))
                logger.error(
                    "Failed to apply WebDriver mask",
                    extra={"error": str(e)},
                )

        if self._fingerprint is not None:
            try:
                await self._fingerprint.apply(context, enabled=True)
                logger.debug("Fingerprint randomization applied")
            except Exception as e:
                errors.append(("fingerprint", e))
                logger.error(
                    "Failed to apply fingerprint randomization",
                    extra={"error": str(e)},
                )

        if self._user_agent is not None:
            try:
                await self._user_agent.apply_to_context(context)
                logger.debug("User agent applied")
            except Exception as e:
                errors.append(("user_agent", e))
                logger.error(
                    "Failed to apply user agent",
                    extra={"error": str(e)},
                )

        if self._viewport is not None:
            try:
                await self._viewport.apply_viewport(context)
                logger.debug("Viewport normalization applied")
            except Exception as e:
                errors.append(("viewport", e))
                logger.error(
                    "Failed to apply viewport normalization",
                    extra={"error": str(e)},
                )

        if errors:
            error_messages = [f"{name}: {str(e)}" for name, e in errors]
            raise StealthProfileApplierError(
                f"Failed to apply stealth profile. Errors: {'; '.join(error_messages)}"
            )

        logger.info("Stealth profile applied successfully")

    async def __aenter__(self) -> "StealthProfileApplier":
        """Enter async context manager.

        Returns:
            Self for use in async with statement.
        """
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_val: Exception value if an exception was raised.
            exc_tb: Exception traceback if an exception was raised.
        """
        self._webdriver = None
        self._fingerprint = None
        self._user_agent = None
        self._viewport = None

    def __repr__(self) -> str:
        """Return a string representation of the applier.

        Returns:
            String representation showing enabled components.
        """
        return (
            f"StealthProfileApplier("
            f"webdriver={self._webdriver is not None}, "
            f"fingerprint={self._fingerprint is not None}, "
            f"user_agent={self._user_agent is not None}, "
            f"viewport={self._viewport is not None})"
        )
