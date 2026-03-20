"""Fingerprint randomization module.

This module provides functionality to randomize canvas and WebGL fingerprints
in Playwright browser contexts, making each browser session appear unique.

Module: src.stealth.cloudflare.core.fingerprint

Classes:
    CanvasFingerprintRandomizer: Randomizes canvas fingerprint.
    WebGLSpoofer: Spoofs WebGL renderer information.
"""

from src.stealth.cloudflare.core.fingerprint.scripts import (
    CanvasFingerprintRandomizer,
    WebGLSpoofer,
)

__all__ = ["CanvasFingerprintRandomizer", "WebGLSpoofer"]
