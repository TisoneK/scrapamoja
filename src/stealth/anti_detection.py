"""
Anti-Detection Masking subsystem for the Stealth & Anti-Detection System.

Masks automation indicators to prevent bot detection. Removes webdriver properties,
Playwright console method patches, process information, and replaces plugins list
with realistic browser extensions.

This subsystem is critical for bypassing advanced bot detection like Cloudflare,
Datadome, and PerimeterX that detect Playwright/Selenium automation.

Module: src.stealth.anti_detection (v0.1.0)
Part of: User Story 1 - Prevent Detection as Automated Bot (P1)
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List

from .models import AntiDetectionEvent, EventType, EventSeverity
from .events import EventBuilder

logger = logging.getLogger(__name__)


# Realistic browser extensions/plugins for navigator.plugins spoofing
REALISTIC_PLUGINS = {
    "Chrome": [
        {"name": "Chrome PDF Plugin", "description": "Portable Document Format"},
        {"name": "Chrome PDF Viewer", "description": ""},
        {"name": "Native Client Executable", "description": ""},
        {"name": "Shockwave Flash", "description": "Shockwave Flash 32.0 r0"},
    ],
    "Firefox": [
        {"name": "Shockwave Flash", "description": "Shockwave Flash 32.0 r0"},
    ],
    "Safari": [
        {"name": "WebKit built-in PDF", "description": ""},
        {"name": "Google Earth Plugin", "description": ""},
        {"name": "Silverlight Plug-In", "description": ""},
    ],
}


class AntiDetectionMasker:
    """
    Masks automation and bot detection indicators in browser context.
    
    Applies multiple masking techniques:
    1. Remove navigator.webdriver property (primary indicator)
    2. Remove Playwright console method patches (secondary indicator)
    3. Hide process version and architecture info
    4. Populate navigator.plugins with realistic extensions
    5. Override language and other headers
    
    All masking is done via Playwright's initScript which runs before any
    page scripts, ensuring hooks are in place from the start.
    
    Example:
        ```python
        masker = AntiDetectionMasker(
            config=config,
            event_builder=builder,
        )
        
        # Apply all masking to browser context
        await masker.apply_masks(context)
        
        # Verify masking
        result = await page.evaluate("() => navigator.webdriver")
        assert result is None  # Successfully masked
        ```
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        event_builder: Optional[EventBuilder] = None,
    ):
        """
        Initialize AntiDetectionMasker.
        
        Args:
            config: Configuration dict with anti_detection settings
            event_builder: EventBuilder for audit logging
        """
        self.config = config or {}
        self.event_builder = event_builder
        self.masks_applied = False
        self._mask_count = 0
    
    async def apply_masks(self, context) -> Dict[str, Any]:
        """
        Apply all anti-detection masking to browser context.
        
        Orchestrates all masking techniques via browser context's initScript.
        This runs before any page scripts, ensuring proper hooking order.
        
        Args:
            context: Playwright BrowserContext object
            
        Returns:
            Result dict with masked_properties, indicators_removed, duration_ms
            
        Raises:
            RuntimeError: If context is None or masking fails with graceful_degradation=False
        """
        if context is None:
            raise RuntimeError("Browser context is None - cannot apply masks")
        
        import time
        start_time = time.time()
        
        try:
            # Build complete init script combining all masks
            init_script = self._build_init_script()
            
            # Apply init script to context
            await context.add_init_script(init_script)
            
            self.masks_applied = True
            duration_ms = int((time.time() - start_time) * 1000)
            
            result = {
                "success": True,
                "masked_properties": [
                    "navigator.webdriver",
                    "navigator.__proto__.webdriver",
                    "navigator.plugins",
                    "process.version",
                    "process.versions",
                ],
                "indicators_removed": self._mask_count,
                "duration_ms": duration_ms,
            }
            
            # Log masking event
            if self.event_builder:
                event = self.event_builder.create_event(
                    event_type=EventType.MASKING_APPLIED,
                    severity=EventSeverity.INFO,
                    details={
                        "subsystem": "anti_detection",
                        "masked_properties": result["masked_properties"],
                        "indicators_removed": self._mask_count,
                    },
                    duration_ms=duration_ms,
                    success=True,
                )
                # Event would be published by coordinator
            
            logger.info(
                f"Anti-detection masks applied successfully: "
                f"{self._mask_count} indicators removed in {duration_ms}ms"
            )
            
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.error(f"Failed to apply anti-detection masks: {e}", exc_info=True)
            
            # Log failure event
            if self.event_builder:
                event = self.event_builder.create_event(
                    event_type=EventType.MASKING_APPLIED,
                    severity=EventSeverity.ERROR,
                    details={
                        "subsystem": "anti_detection",
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    duration_ms=duration_ms,
                    success=False,
                )
            
            # Graceful degradation if configured
            if self.config.get("graceful_degradation", True):
                logger.warning(
                    "Anti-detection masking failed but graceful_degradation=True, "
                    "continuing without masks"
                )
                return {
                    "success": False,
                    "error": str(e),
                    "duration_ms": duration_ms,
                    "gracefully_degraded": True,
                }
            else:
                raise RuntimeError(f"Anti-detection masking failed: {e}") from e
    
    def _build_init_script(self) -> str:
        """
        Build complete init script combining all masking techniques.
        
        This script runs in the page context before any page JavaScript,
        ensuring proper hook placement and maximizing detection evasion.
        
        Returns:
            JavaScript code string for browser.add_init_script()
        """
        script = """
        // Anti-Detection Masking - Applied by Playwright Stealth Module
        (function() {
            // 1. Remove navigator.webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true,
            });
            
            // 2. Remove __proto__.webdriver (secondary check)
            Object.defineProperty(navigator.__proto__, 'webdriver', {
                get: () => undefined,
                configurable: true,
            });
            
            // 3. Remove Playwright console method patches
            // Restore originalconsole methods if they exist
            const consoleMethods = ['log', 'debug', 'info', 'warn', 'error'];
            consoleMethods.forEach(method => {
                if (console['__original_' + method]) {
                    console[method] = console['__original_' + method];
                }
            });
            
            // 4. Hide process information
            if (typeof window !== 'undefined' && window.process) {
                Object.defineProperty(window.process, 'version', {
                    get: () => undefined,
                    configurable: true,
                });
                Object.defineProperty(window.process, 'versions', {
                    get: () => ({}),
                    configurable: true,
                });
            }
            
            // 5. Populate navigator.plugins with realistic extensions
            const fakeMimeTypes = [
                { type: 'application/x-google-chrome-extension', suffixes: '' },
                { type: 'application/pdf', suffixes: 'pdf' },
                { type: 'text/plain', suffixes: 'txt' },
            ];
            
            const fakePlugins = [
                {
                    name: 'Chrome PDF Plugin',
                    description: 'Portable Document Format',
                    filename: 'internal-pdf-viewer',
                    length: 1,
                    item: function(i) { return fakeMimeTypes[0]; },
                    namedItem: function(name) { return null; },
                },
                {
                    name: 'Chrome PDF Viewer',
                    description: '',
                    filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                    length: 0,
                    item: function(i) { return null; },
                    namedItem: function(name) { return null; },
                },
                {
                    name: 'Native Client Executable',
                    description: '',
                    filename: 'internal-nacl-plugin',
                    length: 0,
                    item: function(i) { return null; },
                    namedItem: function(name) { return null; },
                },
            ];
            
            // Override navigator.plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => fakePlugins,
                configurable: true,
            });
            
            // 6. Hide chrome object (Chromium-specific)
            if (typeof window.chrome !== 'undefined') {
                delete window.chrome.loadTimes;
                delete window.chrome.csi;
            }
            
            // 7. Override headless detection vectors
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' }),
                }),
                configurable: true,
            });
        })();
        """
        
        # Count masked properties
        self._mask_count = 7  # navigator.webdriver, __proto__.webdriver, plugins, process.version/versions, chrome, permissions
        
        return script
    
    def _mask_webdriver_property(self) -> str:
        """
        Mask the navigator.webdriver property (primary detection vector).
        
        This is the most common bot detection - checking if navigator.webdriver
        is defined. By making it undefined, we evade basic detection.
        
        Returns:
            JavaScript code for webdriver masking
        """
        return """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true,
        });
        Object.defineProperty(navigator.__proto__, 'webdriver', {
            get: () => undefined,
            configurable: true,
        });
        """
    
    def _mask_playwright_indicators(self) -> str:
        """
        Mask Playwright-specific console method patches (secondary vector).
        
        Playwright patches console methods for debugging. Some bot detectors
        check for these patches to identify automation.
        
        Returns:
            JavaScript code for Playwright indicator masking
        """
        return """
        const consoleMethods = ['log', 'debug', 'info', 'warn', 'error'];
        consoleMethods.forEach(method => {
            if (console['__original_' + method]) {
                console[method] = console['__original_' + method];
            }
        });
        """
    
    def _mask_process_property(self) -> str:
        """
        Mask the process object (Node.js exposure detection vector).
        
        Some bot detectors check for window.process which indicates Node.js
        environment (typical in automation frameworks).
        
        Returns:
            JavaScript code for process masking
        """
        return """
        if (typeof window !== 'undefined' && window.process) {
            Object.defineProperty(window.process, 'version', {
                get: () => undefined,
                configurable: true,
            });
            Object.defineProperty(window.process, 'versions', {
                get: () => ({}),
                configurable: true,
            });
        }
        """
    
    def _add_realistic_plugins(self) -> str:
        """
        Add realistic browser plugins to navigator.plugins array.
        
        Real browsers have plugins (Flash, PDF viewer, etc.). Automation
        frameworks typically have empty plugins. Populating this makes
        detection harder.
        
        Returns:
            JavaScript code for plugins population
        """
        return """
        const fakePlugins = [
            {
                name: 'Chrome PDF Plugin',
                description: 'Portable Document Format',
                filename: 'internal-pdf-viewer',
                length: 1,
            },
            {
                name: 'Chrome PDF Viewer',
                description: '',
                filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                length: 0,
            },
            {
                name: 'Native Client Executable',
                description: '',
                filename: 'internal-nacl-plugin',
                length: 0,
            },
        ];
        
        Object.defineProperty(navigator, 'plugins', {
            get: () => fakePlugins,
            configurable: true,
        });
        """
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get masking status.
        
        Returns:
            Status dict with masks_applied and mask_count
        """
        return {
            "masks_applied": self.masks_applied,
            "mask_count": self._mask_count,
        }
    
    def reset(self) -> None:
        """Reset masker state (for testing)."""
        self.masks_applied = False
        self._mask_count = 0
