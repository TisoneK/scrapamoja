"""BetB2B family data models.

These dataclasses describe the normalised output of the BetB2B family
scraper. They mirror the shape used by the linebet skin
(:mod:`src.sites.linebet.extraction.models`) — same fields, same enum
values — so downstream consumers can treat all skins uniformly.

The raw feed is 1xbet terse-key ``Value[]`` JSON; the
:class:`~src.sites.betb2b.extraction.rules.BetB2BExtractionRules` class
projects those blobs onto the flat shapes defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Sport(str, Enum):
    """Sports the BetB2B family exposes. Values match the ``SN`` field."""

    FOOTBALL = "Football"
    BASKETBALL = "Basketball"
    TENNIS = "Tennis"
    HOCKEY = "Ice Hockey"
    BASEBALL = "Baseball"
    VOLLEYBALL = "Volleyball"
    TABLE_TENNIS = "Table Tennis"
    ESPORTS = "Esports"
    HANDBALL = "Handball"
    CRICKET = "Cricket"
    RUGBY = "Rugby"
    MMA = "MMA"
    BOXING = "Boxing"
    OTHER = "Other"


class EventStatus(str, Enum):
    """Live-match status. Prematch events use ``NOT_STARTED``."""

    NOT_STARTED = "not_started"
    LIVE = "live"
    PAUSED = "paused"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class MarketType(str, Enum):
    """Common betting market types we project out of the raw odds payload.

    The BetB2B ``G`` group id maps onto these (see
    :mod:`src.sites.betb2b.markets`).
    """

    MONEYLINE_12 = "1x2"                # 3-way: home / draw / away
    MONEYLINE_H2H = "h2h"               # 2-way: home / away (no draw)
    DOUBLE_CHANCE = "double_chance"     # 1X / 12 / X2
    TOTALS = "totals"                   # over/under
    HANDICAP = "handicap"               # Asian handicap
    CORRECT_SCORE = "correct_score"
    BTTS = "btts"                       # both teams to score
    ODD_EVEN = "odd_even"
    HT_FT = "ht_ft"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------
@dataclass
class Selection:
    """A single priced outcome inside a market (e.g. "Home win @ 1.85")."""

    name: str
    price: float
    line: Optional[float] = None        # e.g. handicap -1.5, total 2.5
    is_suspended: bool = False
    raw_t: Optional[int] = None         # the raw ``T`` market-type id
    raw_g: Optional[int] = None         # the raw ``G`` group id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "price": self.price,
            "line": self.line,
            "is_suspended": self.is_suspended,
            "raw_t": self.raw_t,
            "raw_g": self.raw_g,
        }


@dataclass
class Market:
    """A betting market (e.g. "Match Result 1x2") with its selections."""

    name: str
    market_type: MarketType
    selections: List[Selection] = field(default_factory=list)
    is_live: bool = False
    is_suspended: bool = False
    raw_g: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "market_type": self.market_type.value,
            "selections": [s.to_dict() for s in self.selections],
            "is_live": self.is_live,
            "is_suspended": self.is_suspended,
            "raw_g": self.raw_g,
        }


@dataclass
class Event:
    """A single sporting event (fixture) and its markets."""

    event_id: str
    sport: Sport
    competition: str
    home: str
    away: str
    start_time: Optional[datetime] = None
    status: EventStatus = EventStatus.NOT_STARTED
    score_home: Optional[int] = None
    score_away: Optional[int] = None
    minute: Optional[int] = None          # live minute for football etc.
    period: Optional[str] = None          # e.g. "1st quarter", "1 Overtime"
    time_remaining: Optional[str] = None  # ``SLS`` field — text
    is_live: bool = False
    country: Optional[str] = None         # event country (``CN``)
    markets: List[Market] = field(default_factory=list)
    source_url: str = ""
    raw_endpoint: str = ""                # which feed endpoint produced this
    sport_id: Optional[int] = None        # the raw ``SI``
    league_id: Optional[int] = None       # the raw ``LI``

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "sport": self.sport.value,
            "competition": self.competition,
            "home": self.home,
            "away": self.away,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "status": self.status.value,
            "score_home": self.score_home,
            "score_away": self.score_away,
            "minute": self.minute,
            "period": self.period,
            "time_remaining": self.time_remaining,
            "is_live": self.is_live,
            "country": self.country,
            "markets": [m.to_dict() for m in self.markets],
            "source_url": self.source_url,
            "raw_endpoint": self.raw_endpoint,
            "sport_id": self.sport_id,
            "league_id": self.league_id,
        }


@dataclass
class CapturedFeedResponse:
    """A captured BetB2B feed response — kept for debugging / replay."""

    url: str
    status: int
    content_type: str
    body_bytes: int
    decoded: Dict[str, Any]               # parsed JSON (empty dict if decode failed)
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "status": self.status,
            "content_type": self.content_type,
            "body_bytes": self.body_bytes,
            "decoded_keys": list(self.decoded.keys()) if isinstance(self.decoded, dict) else None,
            "captured_at": self.captured_at.isoformat(),
        }


@dataclass
class BetB2BScrapeResult:
    """Top-level result wrapper returned by :meth:`BetB2BScraper.scrape`."""

    skin: str
    action: str
    url: str
    events: List[Event] = field(default_factory=list)
    captured_responses: List[CapturedFeedResponse] = field(default_factory=list)
    scrape_duration_seconds: float = 0.0
    session_harvested: bool = False
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_source: str = "betb2b_scraper"
    template_version: str = "1.0.0"
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skin": self.skin,
            "action": self.action,
            "url": self.url,
            "events": [e.to_dict() for e in self.events],
            "captured_responses": [c.to_dict() for c in self.captured_responses],
            "scrape_duration_seconds": self.scrape_duration_seconds,
            "session_harvested": self.session_harvested,
            "extracted_at": self.extracted_at.isoformat(),
            "extraction_source": self.extraction_source,
            "template_version": self.template_version,
            "error": self.error,
            "success": self.success,
            "event_count": len(self.events),
            "captured_response_count": len(self.captured_responses),
        }
