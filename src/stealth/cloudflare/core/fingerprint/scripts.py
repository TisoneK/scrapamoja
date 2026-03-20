"""Fingerprint randomization implementation.

This module provides the CanvasFingerprintRandomizer and WebGLSpoofer classes
which randomize canvas and WebGL fingerprints in Playwright browser contexts.

Module: src.stealth.cloudflare.core.fingerprint.scripts

Classes:
    CanvasFingerprintRandomizer: Randomizes canvas fingerprint.
    WebGLSpoofer: Spoofs WebGL renderer information.

WebGL Constants (from WEBGL_debug_renderer_info extension):
    GPU_VENDOR: 37445
    GPU_RENDERER: 37446
"""

import asyncio
from typing import Any, Optional, Set

from src.observability.logger import get_logger
from src.stealth.cloudflare.exceptions import FingerprintRandomizerError

# Initialize logger for this module
logger = get_logger("cloudflare.fingerprint")

# WebGL constants (避免 magic numbers)
GPU_VENDOR: int = 37445
GPU_RENDERER: int = 37446

# Maximum canvas dimensions for memory-safe operations
MAX_CANVAS_DIMENSION: int = 4096

# Default GPU configurations
COMMON_GPU_RENDERERS: list[str] = [
    "ANGLE (NVIDIA GeForce RTX 3080)",
    "ANGLE (NVIDIA GeForce RTX 4070)",
    "ANGLE (AMD Radeon RX 6800 XT)",
]
COMMON_GPU_VENDORS: list[str] = [
    "NVIDIA Corporation",
    "AMD",
]


class CanvasFingerprintRandomizer:
    """Randomizes canvas fingerprint to make each session unique.

    This class injects JavaScript into Playwright browser contexts to randomize
    canvas fingerprint, making each browser session appear unique to tracking scripts.

    Attributes:
        enabled: Whether the randomizer is currently enabled.

    Example:
        ```python
        from playwright.async_api import async_playwright
        from src.stealth.cloudflare.core.fingerprint import CanvasFingerprintRandomizer

        async def main():
            randomizer = CanvasFingerprintRandomizer()
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context()
                await randomizer.apply(context)
                # Context now has randomized canvas fingerprint
        ```
    """

    # JavaScript injection script to randomize canvas fingerprint
    CANVAS_RANDOMIZATION_SCRIPT: str = """
    (function() {
        const MAX_CANVAS_DIMENSION = 4096;
        
        // Logging helper (injects logging into page console)
        function logCanvasError(message, details) {
            try {
                console.warn('[CanvasFingerprintRandomizer] ' + message, details || '');
            } catch (e) {
                // Ignore logging errors
            }
        }
        
        // Validate canvas dimensions before operations
        function validateCanvasDimensions(width, height) {
            if (width <= 0 || height <= 0) {
                logCanvasError('Invalid canvas dimensions', { width, height });
                return false;
            }
            if (width > MAX_CANVAS_DIMENSION || height > MAX_CANVAS_DIMENSION) {
                logCanvasError('Canvas too large, skipping noise injection', { width, height });
                return false;
            }
            return true;
        }
        
        // Add noise to canvas with memory-safe sampling
        function addNoiseToCanvas(ctx, width, height) {
            // For large canvases, use sampling instead of full copy
            const pixelCount = width * height;
            if (pixelCount > 1000000) {
                // For large canvases (>1MP), only sample every Nth pixel
                const sampleRate = Math.ceil(pixelCount / 500000);
                const imageData = ctx.getImageData(0, 0, width, height);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4 * sampleRate) {
                    const noise = Math.floor(Math.random() * 3);
                    data[i] = (data[i] + noise) % 256;
                    data[i + 1] = (data[i + 1] + noise) % 256;
                    data[i + 2] = (data[i + 2] + noise) % 256;
                }
                ctx.putImageData(imageData, 0, 0);
            } else {
                // For smaller canvases, process all pixels
                const imageData = ctx.getImageData(0, 0, width, height);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    const noise = Math.floor(Math.random() * 3);
                    data[i] = (data[i] + noise) % 256;
                    data[i + 1] = (data[i + 1] + noise) % 256;
                    data[i + 2] = (data[i + 2] + noise) % 256;
                }
                ctx.putImageData(imageData, 0, 0);
            }
        }
        
        // Override HTMLCanvasElement.prototype.toDataURL
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            try {
                const ctx = this.getContext('2d');
                if (ctx && validateCanvasDimensions(this.width, this.height)) {
                    addNoiseToCanvas(ctx, this.width, this.height);
                }
            } catch (e) {
                logCanvasError('Error in toDataURL', { error: e.message, canvasWidth: this.width, canvasHeight: this.height });
            }
            return originalToDataURL.apply(this, arguments);
        };

        // Override HTMLCanvasElement.prototype.toBlob
        const originalToBlob = HTMLCanvasElement.prototype.toBlob;
        HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
            try {
                const ctx = this.getContext('2d');
                if (ctx && validateCanvasDimensions(this.width, this.height)) {
                    addNoiseToCanvas(ctx, this.width, this.height);
                }
            } catch (e) {
                logCanvasError('Error in toBlob', { error: e.message, canvasWidth: this.width, canvasHeight: this.height });
            }
            if (originalToBlob) {
                return originalToBlob.apply(this, arguments);
            }
        };

        // Override CanvasRenderingContext2D.getImageData to add noise
        const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function() {
            const imageData = originalGetImageData.apply(this, arguments);
            // Validate dimensions from arguments
            let width = arguments[2];
            let height = arguments[3];
            if (width > 0 && height > 0 && width <= MAX_CANVAS_DIMENSION && height <= MAX_CANVAS_DIMENSION) {
                const data = imageData.data;
                const pixelCount = width * height;
                if (pixelCount > 1000000) {
                    // Sampling for large canvases
                    const sampleRate = Math.ceil(pixelCount / 500000);
                    for (let i = 0; i < data.length; i += 4 * sampleRate) {
                        const noise = Math.floor(Math.random() * 2);
                        data[i] = (data[i] + noise) % 256;
                        data[i + 1] = (data[i + 1] + noise) % 256;
                        data[i + 2] = (data[i + 2] + noise) % 256;
                    }
                } else {
                    for (let i = 0; i < data.length; i += 4) {
                        const noise = Math.floor(Math.random() * 2);
                        data[i] = (data[i] + noise) % 256;
                        data[i + 1] = (data[i + 1] + noise) % 256;
                        data[i + 2] = (data[i + 2] + noise) % 256;
                    }
                }
            }
            return imageData;
        };
    })();
    """

    # Default timeout for add_init_script (seconds)
    DEFAULT_TIMEOUT: float = 5.0

    def __init__(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Initialize the CanvasFingerprintRandomizer.

        Args:
            timeout: Timeout in seconds for add_init_script calls (default: 5.0).
        """
        self._enabled: bool = False
        self._applied_count: int = 0
        self._timeout: float = timeout or self.DEFAULT_TIMEOUT
        self._applied_contexts: Set[int] = set()  # Track applied context IDs
        logger.info(
            "canvas_fingerprint_randomizer_initialized",
            component="canvas_fingerprint_randomizer",
            timeout=self._timeout,
        )

    @property
    def enabled(self) -> bool:
        """Check if the randomizer is currently enabled.

        Returns:
            True if the randomizer has been applied to at least one context.
        """
        return self._enabled

    @property
    def applied_count(self) -> int:
        """Get the number of contexts this randomizer has been applied to.

        Returns:
            Number of times apply() has been called successfully.
        """
        return self._applied_count

    def get_randomization_script(self) -> str:
        """Get the canvas randomization JavaScript script.

        Returns:
            The JavaScript code used to randomize canvas fingerprint.
        """
        return self.CANVAS_RANDOMIZATION_SCRIPT

    async def apply(
        self,
        context: Any,
        *,
        enabled: bool = True,
    ) -> None:
        """Apply canvas fingerprint randomization to a Playwright browser context.

        This method injects JavaScript into the browser context that randomizes
        canvas fingerprint, making each session appear unique.

        Args:
            context: A Playwright browser context (BrowserContext or similar).
            enabled: Whether to enable randomization (default: True).

        Raises:
            FingerprintRandomizerError: If the context doesn't support add_init_script.
        """
        if not enabled:
            logger.debug(
                "canvas_fingerprint_randomizer_disabled_skipping",
                component="canvas_fingerprint_randomizer",
            )
            return

        # Check for duplicate injection using context's unique identifier
        context_id = id(context)
        if context_id in self._applied_contexts:
            logger.debug(
                "canvas_fingerprint_randomizer_already_applied",
                component="canvas_fingerprint_randomizer",
                context_id=context_id,
            )
            return

        try:
            # Add the initialization script to the context with timeout
            # This script runs before any page loads
            await asyncio.wait_for(
                context.add_init_script(self.CANVAS_RANDOMIZATION_SCRIPT),
                timeout=self._timeout,
            )

            # Track this context to prevent duplicate injections
            self._applied_contexts.add(context_id)
            self._enabled = True
            self._applied_count += 1

            logger.info(
                "canvas_fingerprint_randomizer_applied",
                component="canvas_fingerprint_randomizer",
                applied_count=self._applied_count,
            )

        except asyncio.TimeoutError:
            logger.error(
                "canvas_fingerprint_randomizer_timeout",
                component="canvas_fingerprint_randomizer",
                timeout=self._timeout,
            )
            raise FingerprintRandomizerError(
                f"add_init_script() timed out after {self._timeout} seconds"
            )
        except AttributeError as e:
            logger.error(
                "canvas_fingerprint_randomizer_apply_failed",
                component="canvas_fingerprint_randomizer",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise FingerprintRandomizerError(
                "Context must support add_init_script() method"
            ) from e
        except Exception as e:
            logger.error(
                "canvas_fingerprint_randomizer_apply_error",
                component="canvas_fingerprint_randomizer",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def reset_state(self) -> None:
        """Reset the randomizer state.

        This resets the enabled state, counter, and clears tracked contexts.
        Use with caution as it doesn't affect already applied contexts.
        """
        self._enabled = False
        self._applied_count = 0
        self._applied_contexts.clear()
        logger.info(
            "canvas_fingerprint_randomizer_state_reset",
            component="canvas_fingerprint_randomizer",
        )

    async def __aenter__(self) -> "CanvasFingerprintRandomizer":
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
        self.reset_state()

    def __repr__(self) -> str:
        """Return a string representation of the randomizer.

        Returns:
            String representation showing enabled state and application count.
        """
        return (
            f"CanvasFingerprintRandomizer(enabled={self._enabled}, "
            f"applied_count={self._applied_count})"
        )


class WebGLSpoofer:
    """Spoofs WebGL renderer information to appear as common GPU.

    This class injects JavaScript into Playwright browser contexts to spoof
    WebGL renderer and vendor information, making the browser appear to use
    a common GPU rather than automated browser.

    Attributes:
        enabled: Whether the spoofer is currently enabled.

    Example:
        ```python
        from playwright.async_api import async_playwright
        from src.stealth.cloudflare.core.fingerprint import WebGLSpoofer

        async def main():
            spoofer = WebGLSpoofer()
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context()
                await spoofer.apply(context)
                # Context now has spoofed WebGL information
        ```
    """

    # Default timeout for add_init_script (seconds)
    DEFAULT_TIMEOUT: float = 5.0

    # Placeholder tokens for GPU values in JavaScript
    GPU_VENDOR_PLACEHOLDER: str = "GPU_VENDOR_PLACEHOLDER"
    GPU_RENDERER_PLACEHOLDER: str = "GPU_RENDERER_PLACEHOLDER"

    # Common GPU configurations for spoofing (can be randomly selected)
    COMMON_GPU_RENDERERS: list[str] = [
        "ANGLE (NVIDIA GeForce RTX 3080)",
        "ANGLE (NVIDIA GeForce RTX 4070)",
        "ANGLE (AMD Radeon RX 6800 XT)",
        "ANGLE (Intel Iris OpenGL)",
    ]
    COMMON_GPU_VENDORS: list[str] = [
        "NVIDIA Corporation",
        "AMD",
        "Intel",
    ]

    # Default values (for backwards compatibility)
    DEFAULT_GPU_RENDERER: str = "ANGLE (NVIDIA GeForce RTX 3080)"
    DEFAULT_GPU_VENDOR: str = "NVIDIA Corporation"

    # JavaScript injection script to spoof WebGL information
    WEBGL_SPOOFING_SCRIPT: str = """
    (function() {
        const GPU_VENDOR = 37445;
        const GPU_RENDERER = 37446;
        
        // Logging helper
        function logWebGLError(message, details) {
            try {
                console.warn('[WebGLSpoofer] ' + message, details || '');
            } catch (e) {
                // Ignore logging errors
            }
        }
        
        // Check if WebGL is available
        function isWebGLAvailable() {
            try {
                const canvas = document.createElement('canvas');
                return !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
            } catch (e) {
                logWebGLError('WebGL not available', { error: e.message });
                return false;
            }
        }
        
        // Only apply if WebGL is available
        if (!isWebGLAvailable()) {
            logWebGLError('Skipping WebGL spoofing - not available');
            return;
        }
        
        // Store original WebGL getParameter
        const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // Return spoofed values for WebGL renderer and vendor using constants
            if (parameter === GPU_VENDOR) {
                // GPU_VENDOR
                return 'GPU_VENDOR_PLACEHOLDER';
            }
            if (parameter === GPU_RENDERER) {
                // GPU_RENDERER
                return 'GPU_RENDERER_PLACEHOLDER';
            }
            return originalGetParameter.apply(this, arguments);
        };

        // Also handle WebGL2
        if (WebGL2RenderingContext) {
            const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                // Return spoofed values for WebGL2 renderer and vendor
                if (parameter === GPU_VENDOR) {
                    return 'GPU_VENDOR_PLACEHOLDER';
                }
                if (parameter === GPU_RENDERER) {
                    return 'GPU_RENDERER_PLACEHOLDER';
                }
                return originalGetParameter2.apply(this, arguments);
            };
        }

        // Override getExtension
        const originalGetExtension = WebGLRenderingContext.prototype.getExtension;
        WebGLRenderingContext.prototype.getExtension = function(name) {
            try {
                return originalGetExtension.apply(this, arguments);
            } catch (e) {
                return null;
            }
        };

        // Handle WebGL context lost/restored
        function setupContextLostHandler(canvas) {
            canvas.addEventListener('webglcontextlost', function(event) {
                logWebGLError('WebGL context lost', { width: canvas.width, height: canvas.height });
                event.preventDefault();
            }, false);
            
            canvas.addEventListener('webglcontextrestored', function(event) {
                logWebGLError('WebGL context restored - spoofing will be re-applied on next page load');
            }, false);
        }
        
        // Apply context lost handler to all existing and future canvases
        if (typeof HTMLCanvasElement !== 'undefined') {
            const originalGetContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type) {
                const context = originalGetContext.apply(this, arguments);
                if (context && (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl')) {
                    setupContextLostHandler(this);
                }
                return context;
            };
        }
    })();
    """

    def __init__(
        self,
        gpu_renderer: Optional[str] = None,
        gpu_vendor: Optional[str] = None,
        *,
        timeout: Optional[float] = None,
        randomize_gpu: bool = False,
    ) -> None:
        """Initialize the WebGLSpoofer.

        Args:
            gpu_renderer: Custom GPU renderer string to use (default: common GPU).
            gpu_vendor: Custom GPU vendor string to use (default: common vendor).
            timeout: Timeout in seconds for add_init_script calls (default: 5.0).
            randomize_gpu: If True, randomly select GPU from common pool (default: False).
        """
        import random
        
        self._enabled: bool = False
        self._applied_count: int = 0
        self._timeout: float = timeout or self.DEFAULT_TIMEOUT
        self._applied_contexts: Set[int] = set()  # Track applied context IDs
        self._randomize_gpu: bool = randomize_gpu
        
        # Determine GPU values
        if randomize_gpu:
            self._gpu_renderer: str = random.choice(self.COMMON_GPU_RENDERERS)
            self._gpu_vendor: str = random.choice(self.COMMON_GPU_VENDORS)
        else:
            self._gpu_renderer: str = gpu_renderer or self.DEFAULT_GPU_RENDERER
            self._gpu_vendor: str = gpu_vendor or self.DEFAULT_GPU_VENDOR
        
        logger.info(
            "webgl_spoofer_initialized",
            component="webgl_spoofer",
            gpu_renderer=self._gpu_renderer,
            gpu_vendor=self._gpu_vendor,
            timeout=self._timeout,
            randomize_gpu=randomize_gpu,
        )

    @property
    def enabled(self) -> bool:
        """Check if the spoofer is currently enabled.

        Returns:
            True if the spoofer has been applied to at least one context.
        """
        return self._enabled

    @property
    def applied_count(self) -> int:
        """Get the number of contexts this spoofer has been applied to.

        Returns:
            Number of times apply() has been called successfully.
        """
        return self._applied_count

    @property
    def gpu_renderer(self) -> str:
        """Get the GPU renderer string being used.

        Returns:
            The GPU renderer string.
        """
        return self._gpu_renderer

    @property
    def gpu_vendor(self) -> str:
        """Get the GPU vendor string being used.

        Returns:
            The GPU vendor string.
        """
        return self._gpu_vendor

    def _build_spoofing_script(self) -> str:
        """Build the WebGL spoofing script with configured GPU values.

        Returns:
            The JavaScript code used to spoof WebGL information.
        """
        # Replace the placeholder tokens with configured values
        script = self.WEBGL_SPOOFING_SCRIPT.replace(
            self.GPU_VENDOR_PLACEHOLDER, self._gpu_vendor
        )
        script = script.replace(
            self.GPU_RENDERER_PLACEHOLDER, self._gpu_renderer
        )
        return script

    def get_spoofing_script(self) -> str:
        """Get the WebGL spoofing JavaScript script.

        Returns:
            The JavaScript code used to spoof WebGL information.
        """
        return self._build_spoofing_script()

    async def apply(
        self,
        context: Any,
        *,
        enabled: bool = True,
    ) -> None:
        """Apply WebGL spoofing to a Playwright browser context.

        This method injects JavaScript into the browser context that spoofs
        WebGL renderer and vendor information.

        Args:
            context: A Playwright browser context (BrowserContext or similar).
            enabled: Whether to enable spoofing (default: True).

        Raises:
            FingerprintRandomizerError: If the context doesn't support add_init_script.
        """
        if not enabled:
            logger.debug(
                "webgl_spoofer_disabled_skipping",
                component="webgl_spoofer",
            )
            return

        # Check for duplicate injection using context's unique identifier
        context_id = id(context)
        if context_id in self._applied_contexts:
            logger.debug(
                "webgl_spoofer_already_applied",
                component="webgl_spoofer",
                context_id=context_id,
            )
            return

        try:
            # Add the initialization script to the context with timeout
            # This script runs before any page loads
            spoofing_script = self._build_spoofing_script()
            await asyncio.wait_for(
                context.add_init_script(spoofing_script),
                timeout=self._timeout,
            )

            # Track this context to prevent duplicate injections
            self._applied_contexts.add(context_id)
            self._enabled = True
            self._applied_count += 1

            logger.info(
                "webgl_spoofer_applied",
                component="webgl_spoofer",
                applied_count=self._applied_count,
                gpu_renderer=self._gpu_renderer,
                gpu_vendor=self._gpu_vendor,
            )

        except asyncio.TimeoutError:
            logger.error(
                "webgl_spoofer_timeout",
                component="webgl_spoofer",
                timeout=self._timeout,
            )
            raise FingerprintRandomizerError(
                f"add_init_script() timed out after {self._timeout} seconds"
            )
        except AttributeError as e:
            logger.error(
                "webgl_spoofer_apply_failed",
                component="webgl_spoofer",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise FingerprintRandomizerError(
                "Context must support add_init_script() method"
            ) from e
        except Exception as e:
            logger.error(
                "webgl_spoofer_apply_error",
                component="webgl_spoofer",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def reset_state(self) -> None:
        """Reset the spoofer state.

        This resets the enabled state, counter, and clears tracked contexts.
        Use with caution as it doesn't affect already applied contexts.
        """
        self._enabled = False
        self._applied_count = 0
        self._applied_contexts.clear()
        logger.info(
            "webgl_spoofer_state_reset",
            component="webgl_spoofer",
        )

    async def __aenter__(self) -> "WebGLSpoofer":
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
        self.reset_state()

    def __repr__(self) -> str:
        """Return a string representation of the spoofer.

        Returns:
            String representation showing enabled state and application count.
        """
        return (
            f"WebGLSpoofer(enabled={self._enabled}, "
            f"applied_count={self._applied_count}, "
            f"gpu_renderer='{self._gpu_renderer}')"
        )
