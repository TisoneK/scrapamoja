"""User agent rotation implementation.

This module provides the UserAgentManager class which manages user agent
rotation for Playwright browser contexts, making each session appear to come
from different browsers.

Module: src.stealth.cloudflare.core.user_agent.manager

Classes:
    UserAgentManager: Manages user agent pool and selection logic.
"""

import random
from typing import Any, Optional, Set, TYPE_CHECKING, Union

if TYPE_CHECKING:
    # Import Playwright types only for type checking
    try:
        from playwright.async_api import BrowserContext
    except ImportError:
        BrowserContext = Any

from src.observability.logger import get_logger
from src.stealth.cloudflare.exceptions import UserAgentRotationError
from src.stealth.cloudflare.models.config import CloudflareConfig

# Initialize logger for this module
logger = get_logger("cloudflare.user_agent")

# Realistic user agent pool for current browser versions
USER_AGENT_POOL: list[str] = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0",
]

# Browser family weights for selection
BROWSER_WEIGHTS: dict[str, float] = {
    "chrome": 0.4,      # 40% Chrome
    "firefox": 0.3,     # 30% Firefox
    "safari": 0.2,      # 20% Safari
    "edge": 0.1,        # 10% Edge
}


class UserAgentManager:
    """Manages user agent rotation for Playwright browser contexts.

    This class provides functionality to select and apply realistic user agent
    strings to Playwright browser contexts, making each session appear to come
    from different browsers.

    Attributes:
        enabled: Whether the user agent manager is currently enabled.
        preferred_browser: Optional preferred browser family for selection.

    Example:
        ```python
        from playwright.async_api import async_playwright
        from src.stealth.cloudflare.core.user_agent import UserAgentManager

        async def main():
            manager = UserAgentManager()
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                user_agent = await manager.select_user_agent()
                context = await browser.new_context(user_agent=user_agent)
                # Context now has rotated user agent
        ```
    """

    def __init__(
        self,
        enabled: bool = True,
        preferred_browser: Optional[str] = None,
        config: Optional[CloudflareConfig] = None,
    ) -> None:
        """Initialize the UserAgentManager.

        Args:
            enabled: Whether user agent rotation is enabled.
            preferred_browser: Optional preferred browser family
                ("chrome", "firefox", "safari", "edge").
            config: Optional CloudflareConfig for integration with Epic 1 settings.

        Raises:
            UserAgentRotationError: If preferred_browser is invalid.
        """
        # Override enabled if config is provided and Cloudflare protection is disabled
        if config and not config.is_enabled():
            enabled = False
            
        self.enabled: bool = enabled
        # Validate and normalize preferred_browser
        if preferred_browser:
            if not isinstance(preferred_browser, str) or not preferred_browser.strip():
                raise UserAgentRotationError(
                    f"Invalid preferred_browser: {preferred_browser}. "
                    f"Must be a non-empty string."
                )
            preferred_browser = preferred_browser.strip().lower()
            if preferred_browser not in BROWSER_WEIGHTS:
                raise UserAgentRotationError(
                    f"Invalid preferred_browser: {preferred_browser}. "
                    f"Must be one of: {list(BROWSER_WEIGHTS.keys())}"
                )
        
        self.preferred_browser: Optional[str] = preferred_browser
        self.config: Optional[CloudflareConfig] = config

        logger.info(
            "UserAgentManager initialized",
            extra={
                "enabled": enabled,
                "preferred_browser": preferred_browser,
            },
        )

    async def select_user_agent(self) -> str:
        """Select a user agent string from the pool.

        Returns:
            A randomly selected user agent string based on browser weights
            and optional preferred browser preference.

        Raises:
            UserAgentRotationError: If user agent selection fails.
        """
        if not self.enabled:
            logger.debug("User agent rotation disabled, returning default")
            return USER_AGENT_POOL[0]  # Return first UA as default

        try:
            if self.preferred_browser:
                user_agent = self._select_preferred_browser_agent()
            else:
                user_agent = self._select_weighted_random_agent()

            logger.debug(
                "User agent selected",
                extra={
                    "user_agent": user_agent[:100] + "...",  # Truncate for logging
                    "preferred_browser": self.preferred_browser,
                },
            )
            return user_agent

        except Exception as e:
            logger.error(
                "Failed to select user agent",
                extra={
                    "error": str(e),
                    "preferred_browser": self.preferred_browser,
                },
            )
            raise UserAgentRotationError(f"Failed to select user agent: {e}") from e

    def _select_preferred_browser_agent(self) -> str:
        """Select a user agent from the preferred browser family.

        Returns:
            A user agent string from the preferred browser family.

        Raises:
            UserAgentRotationError: If no agents found for preferred browser.
        """
        preferred_agents = [
            ua for ua in USER_AGENT_POOL
            if self._detect_browser_family(ua) == self.preferred_browser.lower()
        ]

        if not preferred_agents:
            raise UserAgentRotationError(
                f"No user agents found for preferred browser: {self.preferred_browser}"
            )

        return random.choice(preferred_agents)

    def _select_weighted_random_agent(self) -> str:
        """Select a user agent using weighted random selection.

        Returns:
            A randomly selected user agent string based on browser weights.
        """
        # Group user agents by browser family
        browser_agents: dict[str, list[str]] = {}
        for ua in USER_AGENT_POOL:
            browser_family = self._detect_browser_family(ua)
            if browser_family not in browser_agents:
                browser_agents[browser_family] = []
            browser_agents[browser_family].append(ua)

        # Select browser family based on weights
        browser_families = list(browser_agents.keys())
        weights = [BROWSER_WEIGHTS.get(family, 0.1) for family in browser_families]
        selected_family = random.choices(browser_families, weights=weights)[0]

        # Select random agent from chosen family
        return random.choice(browser_agents[selected_family])

    def _detect_browser_family(self, user_agent: str) -> str:
        """Detect browser family from user agent string.

        Args:
            user_agent: The user agent string to analyze.

        Returns:
            The browser family ("chrome", "firefox", "safari", "edge").
            
        Raises:
            UserAgentRotationError: If user_agent is invalid.
        """
        if not user_agent or not isinstance(user_agent, str):
            raise UserAgentRotationError(
                f"Invalid user_agent parameter: {user_agent}. "
                f"Must be a non-empty string."
            )
            
        user_agent_lower = user_agent.lower()

        # Edge must be checked first since it also contains Chrome
        if "edg/" in user_agent_lower:
            return "edge"
        elif "chrome/" in user_agent_lower and "safari/" in user_agent_lower:
            return "chrome"
        elif "firefox/" in user_agent_lower:
            return "firefox"
        elif "safari/" in user_agent_lower and "chrome/" not in user_agent_lower:
            # Safari detection: must contain safari but not chrome, and typically contains version
            return "safari"
        else:
            # Default fallback - use chrome as it's most common
            return "chrome"

    async def apply_to_context(self, context: Union["BrowserContext", Any]) -> None:
        """Apply user agent to a Playwright browser context.

        Args:
            context: The Playwright browser context to modify.

        Raises:
            UserAgentRotationError: If application fails.
        """
        if not self.enabled:
            logger.debug("User agent rotation disabled, skipping application")
            return

        try:
            user_agent = await self.select_user_agent()
            
            # Note: Playwright contexts are created with user_agent parameter
            # This method is for future compatibility with context modification
            if hasattr(context, 'set_extra_http_headers'):
                # Set User-Agent header as fallback
                await context.set_extra_http_headers({
                    "User-Agent": user_agent
                })
            else:
                # Context doesn't support header modification - log warning but don't fail
                logger.warning(
                    "Context does not support header modification, "
                    "user agent application skipped"
                )
                return

            logger.info(
                "User agent applied to context",
                extra={
                    "user_agent": user_agent[:100] + "...",
                },
            )

        except Exception as e:
            logger.error(
                "Failed to apply user agent to context",
                extra={"error": str(e)},
            )
            raise UserAgentRotationError(f"Failed to apply user agent to context: {e}") from e

    def get_pool_size(self) -> int:
        """Get the size of the user agent pool.

        Returns:
            The number of user agents in the pool.
        """
        return len(USER_AGENT_POOL)

    def get_browser_distribution(self) -> dict[str, int]:
        """Get the distribution of browsers in the pool.

        Returns:
            A dictionary mapping browser families to their counts.
        """
        distribution: dict[str, int] = {}
        for ua in USER_AGENT_POOL:
            family = self._detect_browser_family(ua)
            distribution[family] = distribution.get(family, 0) + 1
        return distribution
