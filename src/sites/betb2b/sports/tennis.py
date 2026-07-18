"""Tennis scraper — BetB2B ``SI=4``.

Tennis is 2-way (no draw). Markets are typically "To Win Match", "Set Betting",
"Game Handicap", "Total Games". Period = set.
"""

from __future__ import annotations

from ..extraction.models import MarketType, Sport
from .base import MarketGroupOverride, SportScraper


class TennisScraper(SportScraper):
    """Per-sport scraper for Tennis (BetB2B ``SI=4``)."""

    sport_id = 4
    slug = "tennis"
    live_slug = "tennis"
    sport_enum = Sport.TENNIS
    display_name = "Tennis"

    has_draw = False
    period_name = "set"
    periods_count = None  # best-of-3 or best-of-5, varies by tournament

    market_group_overrides = [
        MarketGroupOverride(g_id=1, name="To Win Match",
                            market_type=MarketType.MONEYLINE_H2H),
        MarketGroupOverride(g_id=2, name="Game Handicap",
                            market_type=MarketType.HANDICAP),
        MarketGroupOverride(g_id=3, name="Total Games",
                            market_type=MarketType.TOTALS),
        MarketGroupOverride(g_id=17, name="Total Games",
                            market_type=MarketType.TOTALS),
        MarketGroupOverride(g_id=5, name="Exact Score",
                            market_type=MarketType.CORRECT_SCORE),
    ]

    def enrich_event(self, event):
        """Tennis enrichment: maps "1st set" / "2nd set" to set number."""
        if event.period:
            p = event.period.lower()
            set_map = {
                "1st set": 1, "2nd set": 2, "3rd set": 3,
                "4th set": 4, "5th set": 5,
                "set 1": 1, "set 2": 2, "set 3": 3,
                "set 4": 4, "set 5": 5,
            }
            for k, v in set_map.items():
                if k in p:
                    if event.minute is None:
                        event.minute = v
                    break
        return event
