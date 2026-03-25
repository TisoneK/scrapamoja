"""Viewport normalization module.

This module provides functionality to normalize viewport dimensions for Playwright
browser contexts, preventing viewport-based fingerprinting by standardizing browser
window dimensions to common user configurations.

Module: src.stealth.cloudflare.core.viewport

Classes:
    ViewportNormalizer: Manages viewport dimension pool and selection logic.
    ViewportDimension: Represents a viewport dimension with width and height.
"""

from src.stealth.cloudflare.core.viewport.normalizer import ViewportNormalizer, ViewportDimension

__all__ = ["ViewportNormalizer", "ViewportDimension"]
