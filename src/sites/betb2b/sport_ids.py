"""BetB2B / 1xbet sport-id lookup table.

The 1xbet terse feed encodes the sport as the integer ``SI`` field
(e.g. ``SI=3`` is Basketball, ``SI=1`` is Football). This table maps
those ids to human-readable sport names + the project's
:class:`~src.sites.betb2b.extraction.models.Sport` enum value.

Values are the 1xbet-family constants — same ids across all skins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SportMap:
    """One ``SI`` sport id."""

    si_id: int
    name: str
    """Display name e.g. ``'Basketball'``, ``'Football'``."""


# Known 1xbet-family sport ids. Extend as more are observed live.
DEFAULT_SPORT_MAP: Dict[int, SportMap] = {
    s.si_id: s
    for s in [
        SportMap(1, "Football"),
        SportMap(2, "Ice Hockey"),
        SportMap(3, "Basketball"),
        SportMap(4, "Tennis"),
        SportMap(5, "Volleyball"),
        SportMap(6, "Handball"),
        SportMap(7, "Baseball"),
        SportMap(8, "Cricket"),
        SportMap(9, "Rugby"),
        SportMap(11, "Boxing"),
        SportMap(12, "MMA"),
        SportMap(13, "Table Tennis"),
        SportMap(14, "Badminton"),
        SportMap(15, "Golf"),
        SportMap(16, "Darts"),
        SportMap(17, "Cycling"),
        SportMap(18, "Snooker"),
        SportMap(19, "Formula 1"),
        SportMap(20, "Esports"),
        SportMap(21, "Aussie Rules"),
        SportMap(22, "Futsal"),
        SportMap(23, "Bandy"),
        SportMap(24, "Squash"),
        SportMap(25, "Floorball"),
        SportMap(26, "Water Polo"),
        SportMap(27, "Pesäpallo"),
        SportMap(28, "Kabaddi"),
        SportMap(29, "Netball"),
        SportMap(30, "Beach Volley"),
        SportMap(31, "Curdling"),
        SportMap(32, "Horse Racing"),
        SportMap(33, "Greyhound Racing"),
        SportMap(34, "Motorbikes"),
        SportMap(35, "Specials"),
        SportMap(36, "Speedway"),
        SportMap(75, "Politics"),
        SportMap(82, "Financials"),
    ]
}


def lookup_sport(
    si_id: int,
    sport_map: Dict[int, SportMap],
) -> "str | None":
    """Look up a sport's display name from its ``SI`` id."""
    sm = sport_map.get(si_id)
    return sm.name if sm is not None else None
