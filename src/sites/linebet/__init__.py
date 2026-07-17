"""
Linebet site package — hybrid browser + API interception scraper.

Public surface:

    from src.sites.linebet import LinebetScraper

The scraper is built on the Site Template Integration Framework
(``BaseSiteTemplate``). See ``scraper.py`` for the implementation and
``README.md`` for the operator guide.
"""

from .scraper import LinebetScraper
from .config import SITE_CONFIG, get_linebet_config

__version__ = "1.0.0"
__author__ = "Tisone Kironget"
__description__ = (
    "Hybrid browser+API scraper for linebet.com — Playwright bypasses "
    "anti-bot, NetworkInterceptor harvests the JSON API responses."
)

__all__ = ["LinebetScraper", "SITE_CONFIG", "get_linebet_config"]
