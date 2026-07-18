"""Esports scraper — BetB2B ``SI=20``.

Esports on linebet is served from a separate SPA at ``/en/line/esports``
(sometimes ``/en/line/cybersport``). Markets are 2-way (BO1) or 3-way (BO3
with draw possible at series level). Period = game/map.
"""

from __future__ import annotations

from ..extraction.models import MarketType, Sport
from .base import MarketGroupOverride, SportScraper


class EsportsScraper(SportScraper):
    """Per-sport scraper for Esports (BetB2B ``SI=20``)."""

    sport_id = 20
    slug = "esports"
    live_slug = "esports"
    sport_enum = Sport.ESPORTS
    display_name = "Esports"

    has_draw = False  # typically BO1/BO3 with winner-takes-all
    period_name = "map"
    periods_count = None  # BO1/BO3/BO5 — varies

    market_group_overrides = [
        MarketGroupOverride(g_id=1, name="To Win Match",
                            market_type=MarketType.MONEYLINE_H2H),
        MarketGroupOverride(g_id=2, name="Map Handicap",
                            market_type=MarketType.HANDICAP),
        MarketGroupOverride(g_id=3, name="Total Maps",
                            market_type=MarketType.TOTALS),
        MarketGroupOverride(g_id=17, name="Total Maps",
                            market_type=MarketType.TOTALS),
        MarketGroupOverride(g_id=5, name="Exact Score",
                            market_type=MarketType.CORRECT_SCORE),
    ]

    def enrich_event(self, event):
        """Esports enrichment: maps "Map 1" / "Game 2" to map number."""
        if event.period:
            p = event.period.lower()
            for i in range(1, 8):
                if f"map {i}" in p or f"game {i}" in p:
                    if event.minute is None:
                        event.minute = i
                    break
        return event
