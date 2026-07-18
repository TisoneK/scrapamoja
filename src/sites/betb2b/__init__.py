"""BetB2B / 1xbet family scraper package.

One parameterized scraper covers the whole BetB2B platform family —
linebet, melbet, betwinner, 22bet, megapari, 888starz, helabet,
paripesa, … — with per-skin config in YAML.

Extraction mode is **hybrid** (ADR-3 in `.context/memory/plans/decisions.md`):
browser bootstrap once through an allowed-country proxy to harvest
session cookies, then ``httpx``-poll the ``/service-api/{LiveFeed,
LineFeed}/…`` feeds directly. See ``README.md`` for the operator guide.

Quick start::

    from src.network.proxy import build_proxy_manager
    from src.sites.betb2b import BetB2BScraper, BetB2BSkinConfig

    skin = BetB2BSkinConfig.from_yaml("src/sites/betb2b/skins/linebet.yaml")
    pm = build_proxy_manager({
        "endpoints": [{"id": "kenya",
                       "url": "http://USER:PASS@bore.pub:1074",
                       "country": "KE", "source": "ngrok"}],
        "routing": [{"pattern": "*." + skin.domain, "target": "kenya"}],
    })

    async with BetB2BScraper(skin, proxy_manager=pm) as scraper:
        result = await scraper.scrape(action="list_live")
        print(result["event_count"], "live events")
"""

from __future__ import annotations

from .client import BetB2BFeedClient
from .config import (
    DEFAULT_BASE_BETTING_HEADERS,
    DEFAULT_BOOTSTRAP_PATHS,
    DEFAULT_FEED_PATHS,
    DEFAULT_FEED_QUERY_PARAMS,
    DEFAULT_SESSION_TTL_SECONDS,
    DEFAULT_SKIN_CONFIG,
    DEFAULT_STEALTH_PROFILE,
    BetB2BSkinConfig,
)
from .extraction.models import (
    BetB2BScrapeResult,
    CapturedFeedResponse,
    Event,
    Market,
    Selection,
    Sport,
)
from .extraction.rules import BetB2BExtractionRules
from .scraper import BetB2BScraper
from .session import BetB2BSessionManager

__version__ = "1.0.0"
__author__ = "Tisone Kironget"
__description__ = (
    "Hybrid cookie-harvest + httpx-poll scraper for the BetB2B / 1xbet "
    "family of bookmakers. One base scraper, many skins."
)

__all__ = [
    # Scraper
    "BetB2BScraper",
    "BetB2BSessionManager",
    "BetB2BFeedClient",
    "BetB2BExtractionRules",
    # Config
    "BetB2BSkinConfig",
    "DEFAULT_SKIN_CONFIG",
    "DEFAULT_BASE_BETTING_HEADERS",
    "DEFAULT_FEED_PATHS",
    "DEFAULT_FEED_QUERY_PARAMS",
    "DEFAULT_BOOTSTRAP_PATHS",
    "DEFAULT_STEALTH_PROFILE",
    "DEFAULT_SESSION_TTL_SECONDS",
    # Models
    "Event",
    "Market",
    "Selection",
    "Sport",
    "CapturedFeedResponse",
    "BetB2BScrapeResult",
]


def register(registry) -> None:
    """Register the betb2b family with a :class:`ScraperRegistry`.

    The betb2b scraper is parameterised by skin, so this registers a
    lazy factory rather than a single scraper class. Callers can then
    pull a per-skin scraper via
    ``registry.get(f"betb2b:{skin_name}")``.
    """
    def factory(skin_name: str = "linebet"):
        from pathlib import Path

        skin_path = Path(__file__).parent / "skins" / f"{skin_name}.yaml"
        if not skin_path.exists():
            raise FileNotFoundError(f"No skin YAML at {skin_path}")
        skin = BetB2BSkinConfig.from_yaml(skin_path)
        return BetB2BScraper(skin)

    # Register under a family-wide key + per-skin keys lazily.
    registry.register("betb2b", factory)  # type: ignore[arg-type]
