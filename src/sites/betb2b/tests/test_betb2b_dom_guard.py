"""Unit tests for the DOM extractor's garbage team-name guard.

Session 24 saw live DOM extraction return 70 events with garbled team names
like ``"Ajax  Olympiacos Piraeus  0000-Ajax  Olympiacus Piraeus  0000"`` —
the broken live selectors matched a container holding both teams + the
``0000`` score placeholder, and the guard let the concatenated string
through (it was <= 80 chars and ``^0000$`` only matched the whole value).

These tests pin the tightened guard: reject ``0000`` anywhere and reject
concatenation/duplication artifacts, without false-rejecting real names.

Runs without a browser — ``extract_events_from_page`` is driven with a fake
page whose ``evaluate`` returns canned raw rows.
"""

from __future__ import annotations

import pytest

from src.sites.betb2b.extraction.dom import (
    _is_plausible_team_name,
    _looks_duplicated,
    _score_pair,
    extract_events_from_page,
)
from src.sites.betb2b.extraction.models import Sport

# The exact garbled string observed in Session 24 (and a clean-duplicate variant).
GARBLED = "Ajax  Olympiacos Piraeus  0000-Ajax  Olympiacus Piraeus  0000"

REAL_NAMES = [
    "Ajax",
    "Olympiacos Piraeus",
    "Los Angeles Lakers",
    "Botafogo U22",
    "Minas Tenis Clube U22",
    "University of Zagreb",
    "Polytechnic University of Madrid",
    "Paris Saint-Germain",
    "1. FC Koln",
    "Bayer 04 Leverkusen",
]

GARBAGE_NAMES = [
    GARBLED,
    "Ajax  Olympiacos Piraeus  0000-Ajax  Olympiacos Piraeus  0000",
    "0000",
    "Lakers 0000",
    "2 : 1",
    "0 0 0",
    "Real Madrid Real Madrid",
]


@pytest.mark.parametrize("name", REAL_NAMES)
def test_real_names_accepted(name):
    assert _is_plausible_team_name(name) is True


@pytest.mark.parametrize("name", GARBAGE_NAMES)
def test_garbage_names_rejected(name):
    assert _is_plausible_team_name(name) is False


def test_placeholder_token_anywhere_rejected():
    # `0000` as a mid-string token, not just the whole value.
    assert _is_plausible_team_name("Lakers 0000") is False
    # But a 4-digit run that isn't the placeholder is fine.
    assert _is_plausible_team_name("Bayer 04 Leverkusen") is True


def test_duplication_detector():
    assert _looks_duplicated(GARBLED) is True
    assert _looks_duplicated("Real Madrid Real Madrid") is True
    assert _looks_duplicated("Olympiacos Piraeus") is False
    assert _looks_duplicated("Los Angeles Lakers") is False


@pytest.mark.parametrize(
    "text,expected",
    [
        ("88:90", (88, 90)),        # separated
        ("88 - 90", (88, 90)),      # dash separated
        ("46 57", (46, 57)),        # live grid: two adjacent __num spans, no separator
        ("46 57 25 30 21 27", (46, 57)),  # total pair sorts first; ignore periods
        ("", (None, None)),         # prematch — no score
        ("5", (None, None)),        # a lone number isn't a pair
    ],
)
def test_score_pair(text, expected):
    assert _score_pair(text) == expected


class _FakePage:
    """Minimal Playwright-page stand-in: evaluate() returns canned rows."""

    def __init__(self, rows):
        self._rows = rows

    async def evaluate(self, _script):
        return self._rows


async def test_extractor_rejects_garbled_rows_keeps_clean():
    rows = [
        # Garbled — both team fields are the concatenated garbage.
        {"home": GARBLED, "away": GARBLED, "comp": "X", "odds": [], "eventId": "111"},
        # Clean live row with a score and two odds.
        {
            "home": "Botafogo U22",
            "away": "Unifacisa U22",
            "comp": "Brazil NBB",
            "scoreTxt": "72 : 68",
            "odds": [{"label": "1", "price": 1.5}, {"label": "2", "price": 2.5}],
            "live": True,
            "eventId": "352940650",
        },
    ]
    events = await extract_events_from_page(
        _FakePage(rows), is_live=True, sport=Sport.BASKETBALL, has_draw=False,
    )
    assert len(events) == 1
    ev = events[0]
    assert ev.home == "Botafogo U22"
    assert ev.away == "Unifacisa U22"
    assert ev.event_id == "352940650"
    assert ev.score_home == 72 and ev.score_away == 68
    assert len(ev.markets) == 1  # the shallow grid stub (GetGameZip enriches later)
