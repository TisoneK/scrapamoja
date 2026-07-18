"""Basketball scraper — BetB2B ``SI=3``.

Basketball's main market is **2-way** (home or away, no draw — overtime
resolves ties). This overrides ``G=1`` from the football-style "1x2" label
to "To Win Match" (h2h moneyline). Other basketball markets (totals,
handicaps, exact score) use the same ``G`` ids as the rest of the family
but with sport-specific labels (e.g. "Total Points" not "Total Goals").

Bootstrap URL: ``/en/line/basketball``. The service worker pipeline gates
the feed; the per-sport bootstrap gives the SW the right context to load
the basketball championship tree.
"""

from __future__ import annotations

from ..extraction.models import MarketType, Sport
from .base import MarketGroupOverride, SportScraper


class BasketballScraper(SportScraper):
    """Per-sport scraper for Basketball (BetB2B ``SI=3``)."""

    sport_id = 3
    slug = "basketball"
    live_slug = "basketball"
    sport_enum = Sport.BASKETBALL
    display_name = "Basketball"

    # Basketball main market is 2-way (no draw — OT resolves ties).
    has_draw = False
    period_name = "quarter"
    periods_count = 4

    # Basketball-specific market-group labels. The G ids are shared across
    # the family; only the display names differ.
    market_group_overrides = [
        MarketGroupOverride(g_id=1, name="To Win Match",
                            market_type=MarketType.MONEYLINE_H2H),
        MarketGroupOverride(g_id=3, name="Total Points",
                            market_type=MarketType.TOTALS),
        MarketGroupOverride(g_id=17, name="Total Points",
                            market_type=MarketType.TOTALS),
        MarketGroupOverride(g_id=2, name="Handicap",
                            market_type=MarketType.HANDICAP),
        MarketGroupOverride(g_id=4, name="Team Total Points",
                            market_type=MarketType.TOTALS),
        MarketGroupOverride(g_id=5, name="Exact Score",
                            market_type=MarketType.CORRECT_SCORE),
    ]

    def enrich_event(self, event):
        """Basketball-specific enrichment.

        Maps the raw ``period`` string ("1st quarter", "Overtime") to a
        canonical quarter number on ``event.minute`` and keeps the raw
        period text on ``event.period``.
        """
        if event.period:
            p = event.period.lower()
            quarter_map = {
                "1st quarter": 1, "2nd quarter": 2,
                "3rd quarter": 3, "4th quarter": 4,
                "1 q": 1, "2 q": 2, "3 q": 3, "4 q": 4,
                "overtime": 5, "ot": 5, "1 ot": 5, "2 ot": 6,
            }
            for k, v in quarter_map.items():
                if k in p:
                    if event.minute is None:
                        event.minute = v
                    break
        return event
