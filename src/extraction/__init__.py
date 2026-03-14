"""Extraction mode routing module.

This module provides extraction mode routing based on site configuration.
It supports multiple extraction modes: raw (Direct API), intercepted, hybrid, and playwright.

## Usage

    from src.extraction import ExtractionModeRouter
    from src.sites.base import SiteConfigLoader
    
    config = SiteConfigLoader("flashscore").load()
    router = ExtractionModeRouter(config)
    handler = router.get_handler()
"""

from src.extraction.router import ExtractionModeRouter
from src.extraction.interfaces import ExtractionModeProtocol, ExtractionHandlerProtocol
from src.extraction.exceptions import InvalidExtractionModeError

__all__ = [
    "ExtractionModeRouter",
    "ExtractionModeProtocol",
    "ExtractionHandlerProtocol",
    "InvalidExtractionModeError",
]
