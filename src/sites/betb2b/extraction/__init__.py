"""Extraction sub-package — terse 1xbet JSON → typed dataclasses."""

from .models import (
    BetB2BScrapeResult,
    CapturedFeedResponse,
    Event,
    EventStatus,
    Market,
    MarketType,
    PeriodScore,
    Selection,
    Sport,
)
from .rules import BetB2BExtractionRules

__all__ = [
    "BetB2BExtractionRules",
    "Event",
    "Market",
    "PeriodScore",
    "Selection",
    "Sport",
    "EventStatus",
    "MarketType",
    "CapturedFeedResponse",
    "BetB2BScrapeResult",
]
