"""Subject/period labels, the coverage record, all-sub-game capture, H2H backfill.

Store behaviour is checked on both backends: the raw-SQLite store and the ORM
store (exercised on SQLite through DATABASE_URL, as in test_betb2b_store_orm).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.sites.betb2b import store
from src.sites.betb2b.extraction.models import Event, Market, MarketType, Selection, Sport
from src.sites.betb2b.labels import (
    build_totals_coverage, classify, period_structure, scope_from_period_name, stat_scope,
)


# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #
def test_classify_labels_totals_by_subject_and_period():
    assert classify("Total", "FULL_MATCH") == ("MATCH", "FULL_TIME")
    assert classify("Individual Total Home", "QUARTER_2") == ("HOME_TEAM", "QUARTER_2")
    assert classify("Individual Total Away", "FIRST_HALF") == ("AWAY_TEAM", "HALF_1")
    assert classify("Total", "SECOND_HALF") == ("MATCH", "HALF_2")


def test_non_totals_have_no_subject_and_stat_totals_are_never_points():
    assert classify("Asian Handicap", "FULL_MATCH") == (None, "FULL_TIME")
    # A rebounds sub-game's "Total" counts rebounds — it must not read as match points.
    assert classify("Total", "STAT_REBOUNDS") == (None, "FULL_TIME")


def test_sub_game_names_map_to_scopes():
    assert scope_from_period_name("1 Half") == "FIRST_HALF"
    assert scope_from_period_name("2nd quarter") == "QUARTER_2"
    assert scope_from_period_name("Rebounds") is None
    assert stat_scope("Free Throws Scored") == "STAT_FREE_THROWS_SCORED"
    assert stat_scope("") is None


def test_period_structure_is_per_sport():
    assert len(period_structure(Sport.BASKETBALL)) == 7
    assert period_structure(Sport.FOOTBALL) == ("FULL_TIME", "HALF_1", "HALF_2")
    assert period_structure(Sport.TENNIS) == ("FULL_TIME",)


# --------------------------------------------------------------------------- #
# Coverage statuses
# --------------------------------------------------------------------------- #
def _total(name, scope):
    return {"name": name, "scope": scope, "selections": [
        {"name": "Over", "line": 100.5, "price": 1.9}, {"name": "Under", "line": 100.5, "price": 1.9}]}


def _by(rows):
    return {(r["subject"], r["period"]): r["status"] for r in rows if r["dataset"] == "totals"}


def test_coverage_separates_absent_from_not_looked_at_from_failed():
    markets = [_total("Total", "FULL_MATCH"), _total("Total", "QUARTER_1"),
               _total("Individual Total Home", "QUARTER_1")]
    rows = build_totals_coverage(
        Sport.BASKETBALL, markets, subgames_enabled=True,
        listed_scopes={"QUARTER_1", "QUARTER_2"}, fetch_status={"QUARTER_1": "fetched", "QUARTER_2": "failed"})
    st = _by(rows)
    assert len(st) == 21
    assert st[("MATCH", "FULL_TIME")] == "offered"
    assert st[("HOME_TEAM", "FULL_TIME")] == "not_offered"        # main game fetched, no such market
    assert st[("HOME_TEAM", "QUARTER_1")] == "offered"
    assert st[("AWAY_TEAM", "QUARTER_1")] == "not_offered"        # sub-game fetched, no away line
    assert st[("MATCH", "QUARTER_2")] == "fetch_failed"           # listed, fetch failed
    assert st[("MATCH", "QUARTER_3")] == "not_offered"            # source does not list it


def test_coverage_says_not_attempted_when_we_did_not_ask():
    off = build_totals_coverage(Sport.BASKETBALL, [_total("Total", "FULL_MATCH")],
                                subgames_enabled=False, listed_scopes={"QUARTER_1"}, fetch_status={})
    assert _by(off)[("MATCH", "QUARTER_1")] == "not_attempted"
    stub = build_totals_coverage(Sport.BASKETBALL, [], subgames_enabled=True,
                                 listed_scopes=set(), fetch_status={})
    assert set(_by(stub).values()) == {"not_attempted"}           # no market data at all


# --------------------------------------------------------------------------- #
# Scraper: every labelled sub-game is fetched, failures are recorded
# --------------------------------------------------------------------------- #
class _Feed:
    def __init__(self, fail=()):
        self.fail, self.calls = set(fail), []

    async def fetch_game(self, event_id, *, root="line"):
        self.calls.append(event_id)
        if event_id in self.fail:
            raise RuntimeError("boom")
        return SimpleNamespace(event_id=event_id)


class _Rules:
    def extract_markets_scoped(self, cap, scope):
        m = Market(name="Total", market_type=MarketType.TOTALS,
                   selections=[Selection(name="Over", price=1.9, line=10.5)])
        m.scope = scope
        return [m]


def _scraper(feed, subgames=True):
    from src.sites.betb2b import BetB2BScraper, BetB2BSkinConfig
    from pathlib import Path
    skin = BetB2BSkinConfig.from_yaml(
        str(Path(__file__).resolve().parents[1] / "skins" / "linebet.yaml"))
    skin = skin.with_overrides(features={**skin.features, "subgames": subgames})
    s = BetB2BScraper(skin, proxy_manager=None, telemetry_enabled=False)
    s.feed_client, s.extraction_rules = feed, _Rules()
    return s


def _event():
    return Event(event_id="1", sport=Sport.BASKETBALL, competition="c", home="h", away="a")


_CAP = SimpleNamespace(decoded={"Value": {"SG": [
    {"I": 11, "PN": "1st quarter"}, {"I": 12, "PN": "1 Half"}, {"I": 13, "TG": "Rebounds"},
    {"I": 14, "PN": "2nd quarter"}, {"I": 15}]}})   # 15 = unlabelled special group


@pytest.mark.asyncio
async def test_all_labelled_sub_games_are_fetched_with_their_scope():
    feed, ev = _Feed(fail={"14"}), _event()
    await _scraper(feed)._enrich_with_subgames(ev, _CAP, root="line")
    assert feed.calls == ["11", "12", "13", "14"]          # the unlabelled one is skipped
    assert {m.scope for m in ev.markets} == {"QUARTER_1", "FIRST_HALF", "STAT_REBOUNDS"}
    assert ev.subgame_fetch == {"QUARTER_1": "fetched", "FIRST_HALF": "fetched",
                                "STAT_REBOUNDS": "fetched", "QUARTER_2": "failed"}


@pytest.mark.asyncio
async def test_sub_games_can_be_switched_off():
    feed, ev = _Feed(), _event()
    await _scraper(feed, subgames=False)._enrich_with_subgames(ev, _CAP, root="line")
    assert feed.calls == [] and ev.subgame_fetch == {}


def test_finalize_coverage_records_h2h_and_totals():
    s = _scraper(_Feed())
    ok, none, failed, never = _event(), _event(), _event(), _event()
    none.h2h_status, failed.h2h_status = "none", "failed"
    s._finalize_coverage([ok, none, failed, never])
    h2h = [next(r for r in e.coverage if r["dataset"] == "h2h")["status"] for e in (ok, none, failed, never)]
    assert h2h == ["not_attempted", "not_offered", "fetch_failed", "not_attempted"]
    assert all(len(e.coverage) == 22 for e in (ok, none, failed, never))


# --------------------------------------------------------------------------- #
# Stores (both backends)
# --------------------------------------------------------------------------- #
@pytest.fixture(params=["sqlite", "orm"])
def conn(request, tmp_path, monkeypatch):
    if request.param == "orm":
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'orm.db'}")
        import src.sites.betb2b.store_orm as som
        som._engines.clear()
        c = store.init_db()
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        c = store.init_db(tmp_path / "odds.db")
    yield c
    c.close()


def _result(at, status="offered", start=None, h2h=None):
    start = start or (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    return {
        "skin": "linebet", "action": "list_prematch", "url": "u", "extracted_at": at,
        "success": True, "event_count": 1, "events": [{
            "event_id": "E1", "sport": "basketball", "sport_id": 3, "competition": "L",
            "league_id": 1, "home": "Alpha", "away": "Beta", "start_time": start,
            "markets": [
                {"name": "Individual Total Home", "market_type": "total", "raw_g": 15, "scope": "QUARTER_3",
                 "selections": [{"name": "Over", "price": 1.9, "line": 20.5},
                                {"name": "Under", "price": 1.9, "line": 20.5}]},
                {"name": "Total", "market_type": "total", "raw_g": 3, "scope": "STAT_REBOUNDS",
                 "selections": [{"name": "Over", "price": 1.9, "line": 80.5}]}],
            "h2h_data": h2h,
            "coverage": [{"dataset": "totals", "subject": "HOME_TEAM", "period": "QUARTER_3", "status": status},
                         {"dataset": "h2h", "subject": None, "period": None, "status": "fetch_failed"}],
        }],
    }


def _q(conn, sql):
    if store._is_orm(conn):
        from sqlalchemy import text
        return [tuple(r) for r in conn.execute(text(sql)).fetchall()]
    return [tuple(r) for r in conn.execute(sql).fetchall()]


def test_odds_are_stored_with_subject_and_period(conn):
    store.persist_result(_result("2026-10-03T10:00:00+00:00"), conn=conn)
    rows = _q(conn, "SELECT scope, subject, period FROM odds_snapshots ORDER BY scope, selection_name")
    assert ("QUARTER_3", "HOME_TEAM", "QUARTER_3") in rows
    assert ("STAT_REBOUNDS", None, "FULL_TIME") in rows


def test_coverage_is_stored_on_change_only(conn):
    store.persist_result(_result("2026-10-03T10:00:00+00:00"), conn=conn)
    store.persist_result(_result("2026-10-03T10:05:00+00:00"), conn=conn)          # same
    assert _q(conn, "SELECT COUNT(*) FROM coverage")[0][0] == 2
    store.persist_result(_result("2026-10-03T10:10:00+00:00", status="fetch_failed"), conn=conn)
    assert _q(conn, "SELECT COUNT(*) FROM coverage")[0][0] == 3                    # one changed row


def test_h2h_backfill_queue_and_record(conn):
    store.persist_result(_result("2026-10-03T10:00:00+00:00"), conn=conn)
    assert store.events_missing_h2h(conn) == ["E1"]
    run = store.begin_backfill_run(conn, "linebet", "backfill_h2h")
    h2h = {"sport_id": 3, "teams": [{"id": "ta", "title": "Alpha"}, {"id": "tb", "title": "Beta"}],
           "game_shorts": [{"game_id": "g", "team1_id": "ta", "team2_id": "tb", "score1": 90,
                            "score2": 80, "status": 3, "date_start": "2026-01-01T00:00:00+00:00",
                            "periods": [{"period_key": 18, "period_name": "1st quarter",
                                         "home_score": 20, "away_score": 18}]}]}
    store.record_h2h(conn, run, "E1", "linebet", h2h, "offered")
    assert _q(conn, "SELECT COUNT(*) FROM h2h_games")[0][0] == 1
    assert _q(conn, "SELECT home_score FROM h2h_period_scores")[0][0] == 20
    assert store.events_missing_h2h(conn) == []                                    # now stored


def test_source_said_none_is_not_asked_again_until_the_retry_window(conn):
    store.persist_result(_result("2026-10-03T10:00:00+00:00"), conn=conn)
    run = store.begin_backfill_run(conn, "linebet", "backfill_h2h")
    store.record_h2h(conn, run, "E1", "linebet", None, "not_offered",
                     at=datetime.now(timezone.utc).isoformat())
    assert store.events_missing_h2h(conn) == []
    old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    store.record_h2h(conn, run, "E1", "linebet", None, "not_offered", at=old)       # latest row is old
    assert store.events_missing_h2h(conn) == ["E1"]


def test_started_matches_are_not_backfilled(conn):
    past = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    store.persist_result(_result("2026-10-03T10:00:00+00:00", start=past), conn=conn)
    assert store.events_missing_h2h(conn) == []


# --------------------------------------------------------------------------- #
# A hard timeout keeps the events already fetched
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_timeout_keeps_the_events_fetched_so_far():
    import asyncio
    s = _scraper(_Feed())
    done, sub = _event(), _event()
    done.event_id, sub.event_id = "10", "11"     # 11 is a sub-game listing, not a match

    async def run_action(**_):
        s._partial_requested = ["10", "11", "12"]
        s._partial_events.extend([done, sub])
        s._partial_sub_ids.add("11")
        await asyncio.sleep(5)                    # the cap fires here
    s._run_action = run_action
    s._started = True
    for hook in ("_enrich_with_h2h", "_enrich_with_stats", "_enrich_with_stat_ids"):
        setattr(s, hook, lambda *a, **k: asyncio.sleep(0))
    res = await s.scrape(action="list_prematch", timeout_seconds=0.05)
    assert [e["event_id"] for e in res["events"]] == ["10"]
    assert res["success"] is True
    assert s.last_fetch_stats["timed_out"] is True
    assert s.last_fetch_stats["failed_ids"] == ["12"]      # 11 is a sub-game listing: not a miss


@pytest.mark.asyncio
async def test_timeout_with_nothing_fetched_is_still_an_error():
    import asyncio
    s = _scraper(_Feed())

    async def run_action(**_):
        await asyncio.sleep(5)
    s._run_action = run_action
    s._started = True
    res = await s.scrape(action="list_prematch", timeout_seconds=0.05)
    assert res["events"] == [] and "timed out" in res["error"]
