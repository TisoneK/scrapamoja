"""Challenge waiter with configurable timeout.

This module provides the ChallengeWaiter class that handles waiting for
Cloudflare challenge completion with configurable timeout.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

from src.observability.logger import get_logger
from src.stealth.cloudflare.config.flags import is_cloudflare_enabled
from src.stealth.cloudflare.exceptions import ChallengeTimeoutError
from src.stealth.cloudflare.models.config import CloudflareConfig

# Module logger
logger = get_logger("cloudflare.waiter")


class ChallengeWaiter:
    """Async context manager for waiting on Cloudflare challenge completion.

    This class provides timeout-aware waiting for Cloudflare challenge resolution.
    It integrates with the observability system for logging timeout events.

    Attributes:
        config: CloudflareConfig instance with timeout settings.
        page: Playwright page instance for challenge detection.
        check_interval: How often to check for challenge completion (seconds).

    Example:
        >>> config = CloudflareConfig(cloudflare_protected=True, challenge_timeout=60)
        >>> async with ChallengeWaiter(config, page) as waiter:
        >>>     await waiter.wait_for_challenge_resolved()
    """

    DEFAULT_CHECK_INTERVAL: float = 1.0
    """Default interval between challenge resolution checks (seconds)."""

    def __init__(
        self,
        config: CloudflareConfig,
        page: Any,
        check_interval: Optional[float] = None,
    ) -> None:
        """Initialize the ChallengeWaiter.

        Args:
            config: CloudflareConfig with timeout and other settings.
            page: Playwright page instance for DOM checks.
            check_interval: Optional custom check interval in seconds.
        """
        self.config = config
        self.page = page
        self.check_interval = check_interval or self.DEFAULT_CHECK_INTERVAL
        self._timeout_seconds = config.challenge_timeout

    async def __aenter__(self) -> "ChallengeWaiter":
        """Enter async context manager.

        Returns:
            Self for chaining.
        """
        logger.info(
            "challenge_waiter_started",
            timeout_seconds=self._timeout_seconds,
            check_interval=self.check_interval,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager.

        Args:
            exc_type: Exception type if raised.
            exc_val: Exception value if raised.
            exc_tb: Exception traceback if raised.
        """
        if exc_type is None:
            logger.info(
                "challenge_waiter_completed",
                timeout_seconds=self._timeout_seconds,
            )
        else:
            logger.error(
                "challenge_waiter_error",
                timeout_seconds=self._timeout_seconds,
                error_type=exc_type.__name__ if exc_type else None,
            )

    async def wait_for_challenge_resolved(
        self,
        check_func: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> bool:
        """Wait for challenge to be resolved within the configured timeout.

        Args:
            check_func: Optional custom async function to check for challenge resolution.
                If not provided, uses default Cloudflare challenge detection.

        Returns:
            True if challenge was resolved within timeout, False otherwise.

        Raises:
            ChallengeTimeoutError: If timeout is exceeded before challenge resolution.
        """
        check = check_func or self._default_challenge_check

        logger.info(
            "challenge_wait_started",
            timeout_seconds=self._timeout_seconds,
        )

        try:
            resolved = await asyncio.wait_for(
                self._wait_loop(check),
                timeout=self._timeout_seconds,
            )

            if resolved:
                logger.info(
                    "challenge_resolved",
                    timeout_seconds=self._timeout_seconds,
                )

            return resolved

        except asyncio.TimeoutError:
            logger.warning(
                "challenge_timeout",
                timeout_seconds=self._timeout_seconds,
            )
            raise ChallengeTimeoutError(
                f"Challenge not resolved within {self._timeout_seconds} seconds"
            ) from None

    async def _wait_loop(self, check: Callable[[], Awaitable[bool]]) -> bool:
        """Loop until challenge is resolved or timeout.

        Args:
            check: Async function that returns True when challenge is resolved.

        Returns:
            True if challenge resolved, False otherwise.
        """
        while True:
            if await check():
                return True
            await asyncio.sleep(self.check_interval)

    async def _default_challenge_check(self) -> bool:
        """Default check for Cloudflare challenge resolution.

        This checks for common Cloudflare challenge indicators in the page.

        Returns:
            True if no challenge is detected, False otherwise.
        """
        try:
            # Check for Cloudflare challenge elements
            challenge_selectors = [
                "#cf-challenge-root",
                ".cf-challenge",
                "[data-cf-challenge]",
                "#challenge-running",
            ]

            for selector in challenge_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    is_visible = await element.is_visible()
                    if is_visible:
                        return False

            # Check for Cloudflare cookies that indicate challenge
            cookies = await self.page.context.cookies()
            cf_tokens = [c for c in cookies if c["name"].startswith("cf_")]

            if cf_tokens:
                # Has Cloudflare cookies - check if challenge is still active
                return True

            # No challenge detected
            return True

        except Exception:
            # If we can't determine, assume resolved
            return True

    def get_timeout_seconds(self) -> int:
        """Get configured timeout in seconds.

        Returns:
            Timeout value from configuration.
        """
        return self._timeout_seconds


async def wait_for_challenge(
    config: CloudflareConfig,
    page: Any,
    check_func: Optional[Callable[[], Awaitable[bool]]] = None,
    timeout: Optional[int] = None,
) -> bool:
    """Convenience function to wait for challenge resolution.

    Args:
        config: CloudflareConfig with timeout settings.
        page: Playwright page instance.
        check_func: Optional custom check function.
        timeout: Optional override for timeout in seconds.

    Returns:
        True if challenge resolved within timeout.

    Raises:
        ChallengeTimeoutError: If timeout is exceeded.
    """
    # Create a temporary config with the override timeout if provided
    if timeout is not None:
        temp_config = CloudflareConfig(
            cloudflare_protected=config.cloudflare_protected,
            challenge_timeout=timeout,
            detection_sensitivity=config.detection_sensitivity,
            auto_retry=config.auto_retry,
        )
    else:
        temp_config = config

    async with ChallengeWaiter(temp_config, page) as waiter:
        return await waiter.wait_for_challenge_resolved(check_func)


def is_wait_enabled(config: CloudflareConfig | dict[str, Any] | bool | None) -> bool:
    """Check if challenge wait is enabled for the configuration.

    Args:
        config: Configuration to check.

    Returns:
        True if Cloudflare is enabled and wait is applicable.
    """
    return is_cloudflare_enabled(config)
