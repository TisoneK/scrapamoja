"""Ice Hockey scraper — BetB2B ``SI=2``.

Ice hockey main market is 3-way (1X2 — home / draw / away; ties go to
overtime/shootout in some leagues, but the 1X2 market is regulation-time).
Includes "Puck Line" (handicap) and "Total Goals".
"""

from __future__ import annotations

from ..extraction.models import MarketType, Sport
from .base import MarketGroupOverride, SportScraper


class HockeyScraper(SportScraper):
    """Per-sport scraper for Ice Hockey (BetB2B ``SI=2``)."""

    sport_id = 2
    slug = "ice-hockey"
    live_slug = "ice-hockey"
    sport_enum = Sport.HOCKEY
    display_name = "Ice Hockey"

    has_draw = True  # 1X2 (regulation time)
    period_name = "period"
    periods_count = 3

    market_group_overrides = [
        MarketGroupOverride(g_id=1, name="1x2 (Regulation)",
                            market_type=MarketType.MONEYLINE_12),
        MarketGroupOverride(g_id=2, name="Puck Line",
                            market_type=MarketType.HANDICAP),
        MarketGroupOverride(g_id=3, name="Total Goals",
                            market_type=MarketType.TOTALS),
        MarketGroupOverride(g_id=17, name="Total Goals",
                            market_type=MarketType.TOTALS),
        MarketGroupOverride(g_id=6, name="Double Chance",
                            market_type=MarketType.DOUBLE_CHANCE),
    ]

    def enrich_event(self, event):
        """Hockey enrichment: maps "1st period" / "2nd period" / "3rd period"."""
        if event.period:
            p = event.period.lower()
            period_map = {
                "1st period": 1, "2nd period": 2, "3rd period": 3,
                "1 period": 1, "2 period": 2, "3 period": 3,
                "overtime": 4, "ot": 4, "shootout": 5, "so": 5,
            }
            for k, v in period_map.items():
                if k in p:
                    if event.minute is None:
                        event.minute = v
                    break
        return event
