"""Viewport normalization implementation.

This module provides the ViewportNormalizer class which manages viewport
dimension selection for Playwright browser contexts, making each session
appear to have a common screen resolution.

Module: src.stealth.cloudflare.core.viewport.normalizer

Classes:
    ViewportNormalizer: Manages viewport dimension pool and selection logic.
    ViewportDimension: Represents a viewport dimension with width and height.
"""

import random
from typing import Any, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    # Import Playwright types only for type checking
    try:
        from playwright.async_api import BrowserContext
    except ImportError:
        BrowserContext = Any

from src.observability.logger import get_logger
from src.stealth.cloudflare.exceptions import CloudflareConfigError, ViewportNormalizationError
from src.stealth.cloudflare.models.config import CloudflareConfig

# Initialize logger for this module
logger = get_logger("cloudflare.viewport")


class ViewportDimension:
    """Represents a viewport dimension with width, height, and weight.

    Attributes:
        width: The viewport width in pixels.
        height: The viewport height in pixels.
        weight: The relative probability of selection (0-1).
    """

    def __init__(self, width: int, height: int, weight: float = 1.0) -> None:
        """Initialize a ViewportDimension.

        Args:
            width: The viewport width in pixels.
            height: The viewport height in pixels.
            weight: The relative probability of selection (0-1).

        Raises:
            ValueError: If width, height, or weight is invalid.
        """
        if width <= 0:
            raise ValueError(f"Width must be positive, got {width}")
        if height <= 0:
            raise ValueError(f"Height must be positive, got {height}")
        if weight <= 0:
            raise ValueError(f"Weight must be positive, got {weight}")

        self.width = width
        self.height = height
        self.weight = weight

    def __repr__(self) -> str:
        return f"ViewportDimension(width={self.width}, height={self.height}, weight={self.weight})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ViewportDimension):
            return False
        return self.width == other.width and self.height == other.height


# Standard viewport dimension pool with common screen resolutions
# Based on usage statistics - more common resolutions have higher weights
DEFAULT_VIEWPORT_POOL: list[ViewportDimension] = [
    ViewportDimension(1920, 1080, 0.35),   # Full HD - 35%
    ViewportDimension(1366, 768, 0.25),    # HD - 25%
    ViewportDimension(1440, 900, 0.15),    # WXGA+ - 15%
    ViewportDimension(1536, 864, 0.10),    # HD+ - 10%
    ViewportDimension(1280, 720, 0.08),    # HD - 8%
    ViewportDimension(1600, 900, 0.07),    # HD+ - 7%
]



class ViewportNormalizer:
    """Manages viewport normalization for Playwright browser contexts.

    This class provides functionality to select and apply realistic viewport
    dimensions to Playwright browser contexts, making each session appear to
    come from a common screen resolution.

    Attributes:
        enabled: Whether the viewport normalizer is currently enabled.
        selected_dimension: The currently selected viewport dimension for this session.

    Example:
        ```python
        from playwright.async_api import async_playwright
        from src.stealth.cloudflare.core.viewport import ViewportNormalizer

        async def main():
            normalizer = ViewportNormalizer()
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context()
                await normalizer.apply_viewport(context)
                # Context now has normalized viewport
        ```
    """

    def __init__(
        self,
        enabled: bool = True,
        config: Optional[CloudflareConfig] = None,
        custom_pool: Optional[list[ViewportDimension]] = None,
    ) -> None:
        """Initialize the ViewportNormalizer.

        Args:
            enabled: Whether viewport normalization is enabled.
            config: Optional CloudflareConfig for integration with Epic 1 settings.
            custom_pool: Optional custom viewport dimension pool.

        Raises:
            ViewportNormalizationError: If custom_pool is invalid.
        """
        # Override enabled if config is provided and Cloudflare protection is disabled
        if config and not config.is_enabled():
            enabled = False

        self.enabled: bool = enabled
        self.config: Optional[CloudflareConfig] = config

        # Validate and set custom pool or use default
        if custom_pool is not None and len(custom_pool) > 0:
            self.pool: list[ViewportDimension] = custom_pool
        else:
            self.pool = DEFAULT_VIEWPORT_POOL.copy()

        # Selected dimension for this session (cached for consistency)
        self.selected_dimension: Optional[ViewportDimension] = None

        logger.info(
            "ViewportNormalizer initialized",
            extra={
                "enabled": enabled,
                "pool_size": len(self.pool),
                "has_custom_pool": custom_pool is not None,
            },
        )

    async def select_dimension(self) -> ViewportDimension:
        """Select a viewport dimension from the pool using weighted random selection.

        Returns:
            A randomly selected ViewportDimension based on weights.

        Raises:
            ViewportNormalizationError: If dimension selection fails.
        """
        if not self.enabled:
            logger.debug("Viewport normalization disabled, returning default")
            return self.pool[0]  # Return first dimension as default

        try:
            # Use cached dimension if available for session consistency
            if self.selected_dimension:
                logger.debug(
                    "Using cached viewport dimension",
                    extra={
                        "width": self.selected_dimension.width,
                        "height": self.selected_dimension.height,
                    },
                )
                return self.selected_dimension

            # Select dimension using weighted random selection
            weights = [d.weight for d in self.pool]
            selected = random.choices(self.pool, weights=weights)[0]

            # Cache for session consistency
            self.selected_dimension = selected

            logger.debug(
                "Viewport dimension selected",
                extra={
                    "width": selected.width,
                    "height": selected.height,
                    "weight": selected.weight,
                },
            )
            return selected

        except Exception as e:
            logger.error(
                "Failed to select viewport dimension",
                extra={"error": str(e)},
            )
            raise ViewportNormalizationError(
                f"Failed to select viewport dimension: {e}"
            ) from e

    async def apply_viewport(
        self, context: Union["BrowserContext", Any]
    ) -> None:
        """Apply normalized viewport to a Playwright browser context.

        Args:
            context: The Playwright browser context to modify.

        Raises:
            ViewportNormalizationError: If application fails.
        """
        if not self.enabled:
            logger.debug("Viewport normalization disabled, skipping application")
            return

        # Check for null context
        if context is None:
            logger.warning("Context is None, viewport application skipped")
            return

        try:
            dimension = await self.select_dimension()

            # Check if context supports set_viewport_size
            if not hasattr(context, "set_viewport_size"):
                logger.warning(
                    "Context does not support viewport size modification, "
                    "viewport application skipped"
                )
                return

            # Apply viewport size
            await context.set_viewport_size({
                "width": dimension.width,
                "height": dimension.height,
            })

            logger.info(
                "Viewport applied to context",
                extra={
                    "width": dimension.width,
                    "height": dimension.height,
                },
            )

        except Exception as e:
            logger.error(
                "Failed to apply viewport to context",
                extra={"error": str(e)},
            )
            raise ViewportNormalizationError(
                f"Failed to apply viewport to context: {e}"
            ) from e

    def get_pool_size(self) -> int:
        """Get the size of the viewport dimension pool.

        Returns:
            The number of viewport dimensions in the pool.
        """
        return len(self.pool)

    def get_dimension_distribution(self) -> dict[str, int]:
        """Get the distribution of viewport dimensions in the pool.

        Returns:
            A dictionary mapping dimension strings to their counts.
        """
        distribution: dict[str, int] = {}
        for dim in self.pool:
            key = f"{dim.width}x{dim.height}"
            distribution[key] = distribution.get(key, 0) + 1
        return distribution

    def reset_selection(self) -> None:
        """Reset the cached viewport selection.

        This allows a new random dimension to be selected for a new session.
        """
        self.selected_dimension = None
        logger.debug("Viewport selection reset for new session")
