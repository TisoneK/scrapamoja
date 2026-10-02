"""Fixes from the DB audit: placeholder 'Home (Points)' listings are not matches;
a blocked/unreachable site is a FAILED run, not '0 events, success'."""
import asyncio
from types import SimpleNamespace

import pytest

from src.sites.betb2b.extraction.models import Event, Sport
from src.sites.betb2b.extraction.rules import is_placeholder_event


@pytest.fixture
def skin():
    from src.sites.betb2b.cli.main import _load_skin
    return _load_skin("linebet")


def _ev(home, away):
    return Event(event_id="1", sport=Sport.BASKETBALL, competition="L", home=home, away=away)


@pytest.mark.parametrize("home,away,expected", [
    ("Home (Points)", "Away (Points)", True),
    ("Home", "Away", True),
    ("Team 1", "Team 2", True),
    ("Home Guard", "Away Wolves", False),      # real clubs are never dropped
    ("Real Madrid", "Away (Points)", False),   # both sides must be generic
    ("Lleida", "Burgos", False),
])
def test_placeholder_detection(home, away, expected):
    assert is_placeholder_event(_ev(home, away)) is expected


def test_blocked_discovery_is_a_failed_run(skin):
    from src.sites.betb2b.scraper import BetB2BScraper

    s = BetB2BScraper(skin, direct=True)
    blocked = SimpleNamespace(status=200, decoded=None, url="u")   # WAF challenge page

    async def fake_sports(root="line"):
        return blocked

    s.feed_client.fetch_sports = fake_sports
    assert asyncio.run(s.discover_ids()) == []
    assert s._discovery_failed is True
