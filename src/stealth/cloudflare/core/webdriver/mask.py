"""Webdriver automation signal suppression implementation.

This module provides the WebdriverMasker class which suppresses navigator.webdriver
and other automation detection signals in Playwright browser contexts.

Module: src.stealth.cloudflare.core.webdriver.mask

Classes:
    WebdriverMasker: Suppresses automation signals in browser contexts.
"""

from typing import Any, Optional

from src.observability.logger import get_logger

# Initialize logger for this module
logger = get_logger("cloudflare.webdriver")


class WebdriverMasker:
    """Suppresses navigator.webdriver and other automation signals in browser contexts.

    This class injects JavaScript into Playwright browser contexts to mask
    automation detection signals, making the browser appear as a regular user browser.

    Attributes:
        enabled: Whether the masker is currently enabled.

    Example:
        ```python
        from playwright.async_api import async_playwright
        from src.stealth.cloudflare.core.webdriver import WebdriverMasker

        async def main():
            masker = WebdriverMasker()
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context()
                await masker.apply(context)
                # Context now has automation signals suppressed
        ```
    """

    # JavaScript injection script to suppress automation signals
    SUPPRESSION_SCRIPT: str = """
    (function() {
        // Suppress navigator.webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: function() { return undefined; },
            configurable: false
        });

        // Remove common automation detection properties from window
        const automationProps = [
            '$cdc_adoQpoasnfa76pfcZLmcfl_Array',
            '$cdc_adoQpoasnfa76pfcZLmcfl_Object',
            '$cdc_adoQpoasnfa76pfcZLmcfl_Promise',
            '$cdc_adoQpoasnfa76pfcZLmcfl_Symbol'
        ];

        automationProps.forEach(function(prop) {
            try {
                if (window.hasOwnProperty(prop)) {
                    delete window[prop];
                }
            } catch (e) {
                // Ignore errors when deleting properties
            }
        });

        // Override Chrome runtime detection
        if (window.chrome) {
            window.chrome.runtime = undefined;
        }

        // Mask automation-related functions
        const originalAttachShadow = Element.prototype.attachShadow;
        if (originalAttachShadow) {
            Element.prototype.attachShadow = function(options) {
                return originalAttachShadow.call(this, options);
            };
        }
    })();
    """

    def __init__(self) -> None:
        """Initialize the WebdriverMasker."""
        self._enabled: bool = False
        self._applied_count: int = 0
        logger.info(
            "webdriver_masker_initialized",
            component="webdriver_masker",
        )

    @property
    def enabled(self) -> bool:
        """Check if the masker is currently enabled.

        Returns:
            True if the masker has been applied to at least one context.
        """
        return self._enabled

    @property
    def applied_count(self) -> int:
        """Get the number of contexts this masker has been applied to.

        Returns:
            Number of times apply() has been called successfully.
        """
        return self._applied_count

    def get_suppression_script(self) -> str:
        """Get the JavaScript suppression script.

        Returns:
            The JavaScript code used to suppress automation signals.
        """
        return self.SUPPRESSION_SCRIPT

    async def apply(
        self,
        context: Any,
        *,
        enabled: bool = True,
    ) -> None:
        """Apply automation signal suppression to a Playwright browser context.

        This method injects JavaScript into the browser context that suppresses
        navigator.webdriver and other automation detection signals.

        Args:
            context: A Playwright browser context (BrowserContext or similar).
            enabled: Whether to enable suppression (default: True).

        Raises:
            TypeError: If the context doesn't support add_init_script.
        """
        if not enabled:
            logger.debug(
                "webdriver_masker_disabled_skipping",
                component="webdriver_masker",
            )
            return

        try:
            # Add the initialization script to the context
            # This script runs before any page loads
            await context.add_init_script(self.SUPPRESSION_SCRIPT)

            self._enabled = True
            self._applied_count += 1

            logger.info(
                "webdriver_masker_applied",
                component="webdriver_masker",
                applied_count=self._applied_count,
            )

        except AttributeError as e:
            logger.error(
                "webdriver_masker_apply_failed",
                component="webdriver_masker",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise TypeError("Context must support add_init_script() method") from e
        except Exception as e:
            logger.error(
                "webdriver_masker_apply_error",
                component="webdriver_masker",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def remove(self, context: Any) -> None:
        """Remove automation signal suppression from a context.

        Note: This does not fully remove the init script as Playwright
        doesn't support removal of init scripts. This is primarily for
        logging and state management purposes.

        Args:
            context: A Playwright browser context.
        """
        logger.info(
            "webdriver_masker_remove_requested",
            component="webdriver_masker",
            note="init_script_removal_not_supported",
        )
        # Note: We keep _enabled state as removing init scripts is not supported
        # The masker will remain enabled for this instance

    def reset_state(self) -> None:
        """Reset the masker state.

        This resets the enabled state and counter. Use with caution
        as it doesn't affect already applied contexts.
        """
        self._enabled = False
        self._applied_count = 0
        logger.info(
            "webdriver_masker_state_reset",
            component="webdriver_masker",
        )

    def __repr__(self) -> str:
        """Return a string representation of the masker.

        Returns:
            String representation showing enabled state and application count.
        """
        return (
            f"WebdriverMasker(enabled={self._enabled}, "
            f"applied_count={self._applied_count})"
        )
