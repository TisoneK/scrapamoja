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


def _put(conn, eid, home, away, start, league):
    conn.execute(
        "INSERT INTO events (event_id, league_id, home_name, away_name, start_time, "
        "first_seen, last_seen) VALUES (?,?,?,?,?,?,?)",
        (eid, league, home, away, start, "2026-10-02", "2026-10-02"))


def test_relisted_match_is_linked_not_deleted(tmp_path, monkeypatch):
    from src.sites.betb2b import store
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("BETB2B_STORE_MODE", "local")
    conn = store.init_db(str(tmp_path / "o.db"))
    conn.execute("PRAGMA foreign_keys = OFF")   # league rows are irrelevant here
    _put(conn, "757618816", "Yukatel Denizli", "Tofas", "2026-10-03T10:00", 1107661)  # old id
    _put(conn, "757884023", "Yukatel Denizli", "Tofas", "2026-10-03T10:00", 1107661)  # relisted
    _put(conn, "900000001", "Yukatel Denizli", "Tofas", "2026-10-10T10:00", 1107661)  # rematch, other date
    _put(conn, "900000002", "Yukatel Denizli", "Tofas", "2026-10-03T10:00", 999)      # other league
    conn.commit()

    assert store.mark_superseded(conn) == 1
    rows = dict(conn.execute("SELECT event_id, superseded_by FROM events").fetchall())
    assert rows["757618816"] == "757884023"       # old id points at the live one
    assert rows["757884023"] is None              # newest is untouched
    assert rows["900000001"] is None and rows["900000002"] is None   # different match
    assert len(rows) == 4                          # nothing deleted
    assert store.mark_superseded(conn) == 0        # idempotent


def test_sub_game_listing_is_not_stored_as_a_match(skin):
    from types import SimpleNamespace
    from src.sites.betb2b.scraper import BetB2BScraper

    s = BetB2BScraper(skin, direct=True)
    s.retries = 0

    async def fake_fetch_game(eid, root="line", **kw):
        value = {"SG": [{"I": 757880281, "PN": ""}]} if eid == "757880276" else {}
        return SimpleNamespace(status=200, decoded={"Value": value}, eid=eid)

    async def noop(*a, **k):
        return None

    s.feed_client.fetch_game = fake_fetch_game
    s.extraction_rules.extract_from_captured = lambda cap: [Event(
        event_id=cap.eid, sport=Sport.BASKETBALL, competition="L", home="Jena", away="Chemnitz")]
    s._enrich_with_subgames = noop

    events = asyncio.run(s.fetch_events(["757880276", "757880281"]))
    assert [e.event_id for e in events] == ["757880276"]    # the sub-game id is dropped
