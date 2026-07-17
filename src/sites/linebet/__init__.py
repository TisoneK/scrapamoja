"""
Linebet site package — hybrid browser + API interception scraper.

Public surface:

    from src.sites.linebet import LinebetScraper, register

The scraper is built on the Site Template Integration Framework
(``BaseSiteTemplate``) and inherits from ``BaseSiteScraper`` so it can
be registered with ``ScraperRegistry``. See ``scraper.py`` for the
implementation and ``README.md`` for the operator guide.
"""

from .scraper import LinebetScraper
from .config import SITE_CONFIG, get_linebet_config

__version__ = "1.0.0"
__author__ = "Tisone Kironget"
__description__ = (
    "Hybrid browser+API scraper for linebet.com — Playwright bypasses "
    "anti-bot, NetworkInterceptor harvests the JSON API responses."
)

__all__ = ["LinebetScraper", "SITE_CONFIG", "get_linebet_config", "register"]


def register(registry) -> None:
    """Register :class:`LinebetScraper` with a :class:`ScraperRegistry`.

    Usage::

        from src.sites import ScraperRegistry
        from src.sites.linebet import register

        registry = ScraperRegistry()
        register(registry)

    The registry validates the scraper class (interface, SITE_CONFIG,
    required files) and raises ``RegistryError`` on any problem.

    Args:
        registry: a :class:`src.sites.registry.ScraperRegistry` instance.
    """
    registry.register(SITE_CONFIG["id"], LinebetScraper)

