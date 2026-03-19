"""Webdriver automation signal suppression module.

This module provides functionality to suppress navigator.webdriver and other
automation detection signals in Playwright browser contexts.

Module: src.stealth.cloudflare.core.webdriver

Classes:
    WebdriverMasker: Suppresses automation signals in browser contexts.
"""

from src.stealth.cloudflare.core.webdriver.mask import WebdriverMasker

__all__ = ["WebdriverMasker"]
