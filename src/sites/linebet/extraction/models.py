"""
Linebet data models.

These dataclasses describe the normalised output of the Linebet scraper.
The raw API responses are large, deeply-nested JSON blobs whose exact
shape varies between pre-match and live endpoints — the
``LinebetExtractionRules`` class is responsible for projecting those
blobs onto the flat shapes defined here.
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
    """Sports Linebet exposes. Values match the names used in API responses."""
    FOOTBALL = "Football"
    BASKETBALL = "Basketball"
    TENNIS = "Tennis"
    HOCKEY = "Ice Hockey"
    BASEBALL = "Baseball"
    VOLLEYBALL = "Volleyball"
    TABLE_TENNIS = "Table Tennis"
    ESPORTS = "Esports"
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
    """Common betting market types we project out of the raw odds payload."""
    MONEYLINE_12 = "1x2"                # 3-way: home / draw / away
    MONEYLINE_H2H = "h2h"               # 2-way: home / away (no draw)
    DOUBLE_CHANCE = "double_chance"     # 1X / 12 / X2
    TOTALS = "totals"                   # over/under
    HANDICAP = "handicap"               # Asian handicap
    CORRECT_SCORE = "correct_score"
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "price": self.price,
            "line": self.line,
            "is_suspended": self.is_suspended,
        }


@dataclass
class Market:
    """A betting market (e.g. "Match Result 1X2") with its selections."""
    name: str
    market_type: MarketType
    selections: List[Selection] = field(default_factory=list)
    is_live: bool = False
    is_suspended: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "market_type": self.market_type.value,
            "selections": [s.to_dict() for s in self.selections],
            "is_live": self.is_live,
            "is_suspended": self.is_suspended,
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
    is_live: bool = False
    markets: List[Market] = field(default_factory=list)
    source_url: str = ""
    raw_endpoint: str = ""                # which /api/ endpoint produced this

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
            "is_live": self.is_live,
            "markets": [m.to_dict() for m in self.markets],
            "source_url": self.source_url,
            "raw_endpoint": self.raw_endpoint,
        }


@dataclass
class CapturedAPIResponse:
    """A captured Linebet API response — kept for debugging / replay."""
    url: str
    status: int
    content_type: str
    body_bytes: int                       # size of raw payload
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
class LinebetScrapeResult:
    """Top-level result wrapper returned by ``LinebetScraper.scrape``."""
    action: str
    url: str
    events: List[Event] = field(default_factory=list)
    captured_responses: List[CapturedAPIResponse] = field(default_factory=list)
    scrape_duration_seconds: float = 0.0
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_source: str = "linebet_scraper"
    template_version: str = "1.0.0"
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "url": self.url,
            "events": [e.to_dict() for e in self.events],
            "captured_responses": [c.to_dict() for c in self.captured_responses],
            "scrape_duration_seconds": self.scrape_duration_seconds,
            "extracted_at": self.extracted_at.isoformat(),
            "extraction_source": self.extraction_source,
            "template_version": self.template_version,
            "error": self.error,
            "success": self.success,
            "event_count": len(self.events),
            "captured_response_count": len(self.captured_responses),
        }
