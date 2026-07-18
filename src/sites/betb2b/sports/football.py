"""Football (soccer) scraper — BetB2B ``SI=1``.

Football is the default 3-way moneyline sport (home / draw / away, ``1X2``).
Most BetB2B markets are designed around football, so this scraper ships
the family-default market labels (no overrides needed).
"""

from __future__ import annotations

from ..extraction.models import MarketType, Sport
from .base import MarketGroupOverride, SportScraper


class FootballScraper(SportScraper):
    """Per-sport scraper for Football / Soccer (BetB2B ``SI=1``)."""

    sport_id = 1
    slug = "football"
    live_slug = "football"
    sport_enum = Sport.FOOTBALL
    display_name = "Football"

    has_draw = True  # 1X2 (home / draw / away)
    period_name = "half"
    periods_count = 2

    # Football uses the family-default market labels (1x2, Total Goals, …).
    # Only add explicit hints for the most-trafficked markets to make the
    # output self-describing even if DEFAULT_MARKET_GROUPS lags.
    market_group_overrides = [
        MarketGroupOverride(g_id=1, name="1x2",
                            market_type=MarketType.MONEYLINE_12),
        MarketGroupOverride(g_id=2, name="Handicap",
                            market_type=MarketType.HANDICAP),
        MarketGroupOverride(g_id=3, name="Total Goals",
                            market_type=MarketType.TOTALS),
        MarketGroupOverride(g_id=17, name="Total Goals",
                            market_type=MarketType.TOTALS),
        MarketGroupOverride(g_id=6, name="Double Chance",
                            market_type=MarketType.DOUBLE_CHANCE),
        MarketGroupOverride(g_id=9, name="Both Teams To Score",
                            market_type=MarketType.BTTS),
    ]

    def enrich_event(self, event):
        """Football-specific enrichment.

        Maps the raw ``period`` string ("1st half", "Halftime", "2nd half")
        to a canonical half number on ``event.minute``.
        """
        if event.period:
            p = event.period.lower()
            if "1st half" in p or "first half" in p or p == "1h":
                if event.minute is None:
                    event.minute = 1
            elif "2nd half" in p or "second half" in p or p == "2h":
                if event.minute is None:
                    event.minute = 2
            elif "halftime" in p or "half-time" in p or "break" in p:
                if event.minute is None:
                    event.minute = 2  # between halves
        return event
