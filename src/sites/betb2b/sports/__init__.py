"""Per-sport scraper framework for the BetB2B family.

The :class:`BetB2BScraper` is parameterised by skin (bookmaker brand) and by
sport (Football, Basketball, …). Each sport customises:

* the URL slug (``/en/line/<slug>``) the browser bootstraps against,
* the BetB2B ``SI`` sport id used as the ``sports=<id>`` feed query param,
* DOM selectors used by the drift-tolerance fallback extractor,
* market-group name overrides (e.g. basketball calls ``G=1`` "To Win Match"
  with 12-style moneyline, while football calls it ``1X2``),
* sport-specific event enrichment hooks.

Adding a new sport = drop a 50-line module in ``sports/`` and register it in
``sports/registry.py``. No changes to ``scraper.py`` or ``session.py``.

Quick start::

    from src.sites.betb2b.sports import get_sport_scraper

    SportCls = get_sport_scraper("basketball")     # by slug
    SportCls = get_sport_scraper(sport_id=3)        # by SI id

    sport_scraper = SportCls()
    print(sport_scraper.sport_id, sport_scraper.slug, sport_scraper.bootstrap_path)
    # 3 basketball /en/line/basketball
"""

from __future__ import annotations

from .base import SportScraper, SportScraperContext
from .registry import (
    DEFAULT_SPORT_SCRAPERS,
    get_sport_scraper,
    list_sport_slugs,
    list_sport_scraper_summaries,
    register_sport_scraper,
    resolve_sport,
)

__all__ = [
    "SportScraper",
    "SportScraperContext",
    "DEFAULT_SPORT_SCRAPERS",
    "get_sport_scraper",
    "list_sport_slugs",
    "list_sport_scraper_summaries",
    "register_sport_scraper",
    "resolve_sport",
]
