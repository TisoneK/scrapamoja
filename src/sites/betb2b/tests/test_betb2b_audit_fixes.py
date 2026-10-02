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


def _load_skin_linebet():
    from src.sites.betb2b.cli.main import _load_skin
    return _load_skin("linebet")


def _put(conn, eid, home, away, start, league, venue="Arena"):
    conn.execute(
        "INSERT INTO events (event_id, league_id, home_name, away_name, start_time, "
        "venue, first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?)",
        (eid, league, home, away, start, venue, "2026-10-02", "2026-10-02"))


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
    _put(conn, "757880276", "Jena", "Chemnitz", "2026-10-04T14:30", 24593)               # real match
    _put(conn, "757880281", "Jena", "Chemnitz", "2026-10-04T14:30", 24593, venue=None)  # venue-less sub-game stub
    conn.commit()

    assert store.mark_superseded(conn) == 1
    rows = dict(conn.execute("SELECT event_id, superseded_by FROM events").fetchall())
    assert rows["757618816"] == "757884023"       # old id points at the live one
    assert rows["757884023"] is None              # newest is untouched
    assert rows["900000001"] is None and rows["900000002"] is None   # different match
    assert rows["757880276"] is None              # a stub with a higher id never supersedes the match
    assert len(rows) == 6                          # nothing deleted
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


def test_stat_game_id_is_persisted_and_backfill_queue(tmp_path, monkeypatch):
    from src.sites.betb2b import store
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("BETB2B_STORE_MODE", "local")
    db = str(tmp_path / "o.db")
    a = _ev("Lleida", "Burgos"); a.event_id = "1"; a.stat_game_id = "68659e8b"
    b = _ev("Jena", "Chemnitz"); b.event_id = "2"
    from src.sites.betb2b.extraction.models import BetB2BScrapeResult
    store.persist_result(BetB2BScrapeResult(skin="melbet", action="list_prematch",
                                            url="u", events=[a, b]).to_dict(), db)
    conn = store.init_db(db)
    got = dict(conn.execute("SELECT event_id, stat_game_id FROM events").fetchall())
    assert got == {"1": "68659e8b", "2": None}
    assert store.events_missing_stat_id(conn) == ["2"]        # only the one without an id
    # a later scrape that lacks the id never erases a stored one
    a2 = _ev("Lleida", "Burgos"); a2.event_id = "1"
    store.persist_result(BetB2BScrapeResult(skin="melbet", action="list_prematch",
                                            url="u", events=[a2]).to_dict(), db)
    assert dict(conn.execute("SELECT event_id, stat_game_id FROM events").fetchall())["1"] == "68659e8b"


def test_enrich_with_stat_ids_sets_ids(skin):
    from src.sites.betb2b.scraper import BetB2BScraper
    s = BetB2BScraper(skin, direct=True)

    async def fake_result(ident):
        return ({"stat_game_id": "S" + ident} if ident != "404" else None), False

    s.fetch_result_checked = fake_result
    evs = []
    for i in ("10", "404"):
        e = _ev("A", "B"); e.event_id = i; evs.append(e)
    asyncio.run(s._enrich_with_stat_ids(evs))
    assert [e.stat_game_id for e in evs] == ["S10", None]


def test_known_sub_game_ids_are_not_refetched_as_matches(tmp_path, monkeypatch):
    from src.sites.betb2b import store
    from src.sites.betb2b.extraction.models import BetB2BScrapeResult
    import time
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("BETB2B_STORE_MODE", "local")
    db = str(tmp_path / "o.db")
    parent = _ev("Jena", "Chemnitz"); parent.event_id = "757880276"
    parent.sub_games = [
        {"sub_game_id": "757880277", "name": None, "period": "1st quarter"},
        {"sub_game_id": "757880281", "name": None, "period": None},      # unlabelled special group
    ]
    store.persist_result(BetB2BScrapeResult(skin="melbet", action="list_prematch",
                                            url="u", events=[parent]).to_dict(), db)
    future = time.time() + 3600
    pairs = [("757880276", future), ("757880277", future), ("757880281", future), ("999", future)]
    assert store.unprocessed_ids(pairs, db) == ["999"]   # stored match + its sub-games are skipped


def test_stat_id_enrichment_stops_early_when_site_unreachable(skin):
    from src.sites.betb2b.scraper import BetB2BScraper
    s = BetB2BScraper(skin, direct=True)
    s.concurrency = 1
    calls = []

    async def always_down(ident):
        calls.append(ident)
        return None, True            # request FAILED (timeout), not "no data"

    s.fetch_result_checked = always_down
    evs = []
    for i in range(40):
        e = _ev("A", "B"); e.event_id = str(100 + i); evs.append(e)
    asyncio.run(s._enrich_with_stat_ids(evs))
    assert len(calls) < 40           # gave up after the failure streak instead of waiting out all 40


def test_no_data_is_not_treated_as_unreachable(skin):
    from src.sites.betb2b.scraper import BetB2BScraper
    s = BetB2BScraper(skin, direct=True)
    s.concurrency = 1
    calls = []

    async def no_data(ident):
        calls.append(ident)
        return None, False           # server answered "no data"

    s.fetch_result_checked = no_data
    evs = []
    for i in range(20):
        e = _ev("A", "B"); e.event_id = str(100 + i); evs.append(e)
    asyncio.run(s._enrich_with_stat_ids(evs))
    assert len(calls) == 20          # every event is still tried


@pytest.mark.parametrize("entry,expected", [
    ({"I": 1, "O1": "Lleida", "O2": "Burgos"}, False),                       # a real match
    ({"I": 2, "O1": "NBA. 2026/27. MVP", "O2": ""}, True),                   # outright: empty second side
    ({"I": 3, "O1": "NBA Cup. 2026. Winner"}, True),                         # O2 absent counts as empty
    ({"I": 4, "O1": "NBA. Regular season", "O2": None}, True),               # explicit null second side
    ({"I": 5, "O1": "Home (Points)", "O2": "Away (Points)"}, True),          # generic placeholder listing
    ({"I": 6, "O1": "Home Guard", "O2": "Away Wolves"}, False),              # real clubs with similar words
    ({"I": 7}, False),                                                       # a stub without O1 is never judged
])
def test_non_match_listing_detection(entry, expected):
    from src.sites.betb2b.extraction.rules import is_non_match_listing
    assert is_non_match_listing(entry) is expected


def test_discovery_skips_outrights_before_any_per_match_request(monkeypatch, tmp_path):
    """Outrights ('NBA 2026/27 MVP', O2 empty) and placeholder listings never become events, yet
    were fetched on every run — a quarter of all requests. Discovery now drops them from the
    league list alone."""
    from types import SimpleNamespace
    from src.sites.betb2b.scraper import BetB2BScraper
    s = BetB2BScraper(_load_skin_linebet(), sport="basketball", direct=True)

    async def sports(root="line"):
        return SimpleNamespace(status=200, decoded={"Success": True, "Value": [
            {"I": 3, "L": [{"LI": 1, "GC": 4, "L": "League"}]}]})

    async def champ(li, root="line"):
        return SimpleNamespace(status=200, decoded={"Success": True, "Value": {"G": [
            {"I": 10, "S": 111, "O1": "Lleida", "O2": "Burgos"},
            {"I": 11, "S": 222, "O1": "NBA. 2026/27. MVP", "O2": ""},
            {"I": 12, "S": 333, "O1": "Home (Points)", "O2": "Away (Points)"},
            {"I": 13, "S": 444, "O1": "Jena", "O2": "Chemnitz"}]}})

    s.feed_client.fetch_sports, s.feed_client.fetch_champ = sports, champ
    pairs = asyncio.run(s.discover_ids())
    assert [i for i, _ in pairs] == ["10", "13"]          # only the two real matches
