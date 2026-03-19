# Blind Hunter Review - Story 2-1 Automation Signal Suppression

**Review Type:** Adversarial General (Diff Only - No Project Context)

## Diff Content Under Review

```diff
diff --git a/src/stealth/cloudflare/core/webdriver/__init__.py b/src/stealth/cloudflare/core/webdriver/__init__.py
new file mode 100644
index 0000000..5df82de
--- /dev/null
+++ b/src/stealth/cloudflare/core/webdriver/__init__.py
@@ -0,0 +1,14 @@
+"""Webdriver automation signal suppression module.
+
+This module provides functionality to suppress navigator.webdriver and other
+automation detection signals in Playwright browser contexts.
+
+Module: src.stealth.cloudflare.core.webdriver
+
+Classes:
+    WebdriverMasker: Suppresses automation signals in browser contexts.
+"""
+
+from src.stealth.cloudflare.core.webdriver.mask import WebdriverMasker
+
+__all__ = ["WebdriverMasker"]
diff --git a/src/stealth/cloudflare/core/webdriver/mask.py b/src/stealth/cloudflare/core/webdriver/mask.py
new file mode 100644
index 0000000..76f1080
--- /dev/null
+++ b/src/stealth/cloudflare/core/webdriver/mask.py
@@ -0,0 +1,217 @@
+"""Webdriver automation signal suppression implementation.
+
+This module provides the WebdriverMasker class which suppresses navigator.webdriver
+and other automation detection signals in Playwright browser contexts.
+
+Module: src.stealth.cloudflare.core.webdriver.mask
+
+Classes:
+    WebdriverMasker: Suppresses automation signals in browser contexts.
+"""
+
+from typing import Any, Optional
+
+from src.observability.logger import get_logger
+
+# Initialize logger for this module
+logger = get_logger("cloudflare.webdriver")
+
+
+class WebdriverMasker:
+    """Suppresses navigator.webdriver and other automation signals in browser contexts.
+
+    This class injects JavaScript into Playwright browser contexts to mask
+    automation detection signals, making the browser appear as a regular user browser.
+
+    Attributes:
+        enabled: Whether the masker is currently enabled.
+
+    Example:
+        ```python
+        from playwright.async_api import async_playwright
+        from src.stealth.cloudflare.core.webdriver import WebdriverMasker
+
+        async def main():
+            masker = WebdriverMasker()
+            async with async_playwright() as p:
+                browser = await p.chromium.launch()
+                context = await browser.new_context()
+                await masker.apply(context)
+                # Context now has automation signals suppressed
+        ```
+    """
+
+    # JavaScript injection script to suppress automation signals
+    SUPPRESSION_SCRIPT: str = """
+    (function() {
+        // Suppress navigator.webdriver property
+        Object.defineProperty(navigator, 'webdriver', {
+            get: function() { return undefined; },
+            configurable: false
+        });
+
+        // Remove common automation detection properties from window
+        const automationProps = [
+            '$cdc_adoQpoasnfa76pfcZLmcfl_Array',
+            '$cdc_adoQpoasnfa76pfcZLmcfl_Object',
+            '$cdc_adoQpoasnfa76pfcZLmcfl_Promise',
+            '$cdc_adoQpoasnfa76pfcZLmcfl_Symbol'
+        ];
+
+        automationProps.forEach(function(prop) {
+            try {
+                if (window.hasOwnProperty(prop)) {
+                    delete window[prop];
+                }
+            } catch (e) {
+                // Ignore errors when deleting properties
+            }
+        });
+
+        // Override Chrome runtime detection
+        if (window.chrome) {
+            window.chrome.runtime = undefined;
+        }
+
+        // Mask automation-related functions
+        const originalAttachShadow = Element.prototype.attachShadow;
+        if (originalAttachShadow) {
+            Element.prototype.attachShadow = function(options) {
+                return originalAttachShadow.call(this, options);
+            };
+        }
+    })();
+    """
+
+    def __init__(self) -> None:
+        """Initialize the WebdriverMasker."""
+        self._enabled: bool = False
+        self._applied_count: int = 0
+        logger.info(
+            "webdriver_masker_initialized",
+            component="webdriver_masker",
+        )
+
+    @property
+    def enabled(self) -> bool:
+        """Check if the masker is currently enabled.
+
+        Returns:
+            True if the masker has been applied to at least one context.
+        """
+        return self._enabled
+
+    @property
+    def applied_count(self) -> int:
+        """Get the number of contexts this masker has been applied to.
+
+        Returns:
+            Number of times apply() has been called successfully.
+        """
+        return self._applied_count
+
+    def get_suppression_script(self) -> str:
+        """Get the JavaScript suppression script.
+
+        Returns:
+            The JavaScript code used to suppress automation signals.
+        """
+        return self.SUPPRESSION_SCRIPT
+
+    async def apply(
+        self,
+        context: Any,
+        *,
+        enabled: bool = True,
+    ) -> None:
+        """Apply automation signal suppression to a Playwright browser context.
+
+        This method injects JavaScript into the browser context that suppresses
+        navigator.webdriver and other automation detection signals.
+
+        Args:
+            context: A Playwright browser context (BrowserContext or similar).
+            enabled: Whether to enable suppression (default: True).
+
+        Raises:
+            TypeError: If the context doesn't support add_init_script.
+        """
+        if not enabled:
+            logger.debug(
+                "webdriver_masker_disabled_skipping",
+                component="webdriver_masker",
+            )
+            return
+
+        try:
+            # Add the initialization script to the context
+            # This script runs before any page loads
+            await context.add_init_script(self.SUPPRESSION_SCRIPT)
+
+            self._enabled = True
+            self._applied_count += 1
+
+            logger.info(
+                "webdriver_masker_applied",
+                component="webdriver_masker",
+                applied_count=self._applied_count,
+            )
+
+        except AttributeError as e:
+            logger.error(
                "webdriver_masker_apply_failed",
                component="webdriver_masker",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise TypeError("Context must support add_init_script() method") from e
+        except Exception as e:
+            logger.error(
                "webdriver_masker_apply_error",
                component="webdriver_masker",
                error=str(e),
                error_type=type(e).__name__,
            )
+            raise
+
+    async def remove(self, context: Any) -> None:
+        """Remove automation signal suppression from a context.
+
+        Note: This does not fully remove the init script as Playwright
+        doesn't support removal of init scripts. This is primarily for
+        logging and state management purposes.
+
+        Args:
+            context: A Playwright browser context.
+        """
+        logger.info(
+            "webdriver_masker_remove_requested",
+            component="webdriver_masker",
+            note="init_script_removal_not_supported",
+        )
+        # Note: We keep _enabled state as removing init scripts is not supported
+        # The masker will remain enabled for this instance
+
+    def reset_state(self) -> None:
+        """Reset the masker state.
+
+        This resets the enabled state and counter. Use with caution
+        as it doesn't affect already applied contexts.
+        """
+        self._enabled = False
+        self._applied_count = 0
+        logger.info(
+            "webdriver_masker_state_reset",
+            component="webdriver_masker",
+        )
+
+    def __repr__(self) -> str:
+        """Return a string representation of the masker.
+
+        Returns:
+            String representation showing enabled state and application count.
+        """
+        return (
+            f"WebdriverMasker(enabled={self._enabled}, "
+            f"applied_count={self._applied_count})"
+        )
diff --git a/src/stealth/cloudflare/exceptions/__init__.py b/src/stealth/cloudflare/exceptions/__init__.py
index 5bc2043..562c577 100644
--- a/src/stealth/cloudflare/exceptions/__init__.py
+++ b/src/stealth/cloudflare/exceptions/__init__.py
@@ -35,3 +35,9 @@ class SensitivityConfigurationError(CloudflareConfigError):
     """Raised when sensitivity configuration is invalid."""
 
     pass
+
+
+class WebdriverMaskerError(CloudflareConfigError):
+    """Raised when webdriver signal suppression fails."""
+
+    pass
```

## Blind Hunter Findings

*(Cynical, adversarial review - find issues the developer missed)*

1. **Unused import: `Optional`** - The `Optional` type is imported but never used in `mask.py`
2. **Missing `WebdriverMaskerError` usage** - A custom exception is defined but never raised in the code
3. **`configurable: false` locks future modifications** - If the masker needs to be disabled or reconfigured, the webdriver property cannot be changed back
4. **No error handling in JavaScript for edge browsers** - The script assumes Chrome/Chromium but doesn't handle Firefox/Safari edge cases
5. **Silent failure on `chrome.runtime = undefined`** - If `window.chrome` exists but doesn't have `runtime`, this could throw in some browser versions
6. **attachShadow override does nothing** - The override just calls the original with no actual masking - this is misleading dead code
7. **No validation of context type** - The `apply()` method accepts `Any` but doesn't validate it's actually a Playwright context before calling `add_init_script`
8. **`remove()` method is misleading** - The docstring says "Remove automation signal suppression" but it doesn't actually remove anything
9. **Race condition potential** - No locking mechanism if `apply()` is called concurrently on multiple contexts
10. **No cleanup/destructor** - Missing `__aenter__`/`__aexit__` context manager support despite story requirements mentioning it
11. **Hardcoded automation property names** - The CDC property names are hardcoded; if Cloudflare adds new detection methods, this won't catch them
12. **No version compatibility check** - Doesn't verify Playwright version supports `add_init_script()`

---
*Reviewer: Blind Hunter (Adversarial General)*
*Date: 2026-03-19*
