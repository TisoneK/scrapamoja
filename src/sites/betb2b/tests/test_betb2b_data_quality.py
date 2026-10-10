"""Fixes for the engine's audit of the store (SCRAPER_DATA_ISSUES): H2H kind, duplicate
games, placeholder scores, period rows, team backend ids.

Store behaviour is checked on both backends, like test_betb2b_coverage."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.sites.betb2b import store
from src.sites.betb2b.data_quality import (
    KIND_H2H, KIND_TEAM1_FORM, KIND_TEAM2_FORM, KIND_UNMAPPED, clean_periods,
    match_event_teams, placeholder_flag, prepare_h2h_games,
)

TEAMS = [{"id": "ta", "title": "Alpha"}, {"id": "tb", "title": "Beta"}]


def _g(gid, t1, t2, s1, s2, date="2026-01-01T00:00:00+00:00", **kw):
    return {"game_id": gid, "team1_id": t1, "team2_id": t2, "score1": s1, "score2": s2,
            "status": 3, "date_start": date, "periods": [], **kw}


def _h2h(*games, sport_id=3):
    return {"sport_id": sport_id, "teams": TEAMS, "game_shorts": list(games)}


# --------------------------------------------------------------------------- #
# Pure rules
# --------------------------------------------------------------------------- #
def test_kind_separates_meetings_from_each_teams_form():
    rows = prepare_h2h_games(_h2h(
        _g("1", "ta", "tb", 90, 80), _g("2", "tb", "ta", 70, 75, date="2026-01-02"),
        _g("3", "ta", "x", 60, 50, date="2026-01-03"), _g("4", "y", "tb", 61, 51, date="2026-01-04"),
        _g("5", "p", "q", 61, 51, date="2026-01-05")))
    assert [r["kind"] for r in rows] == [KIND_H2H, KIND_H2H, KIND_TEAM1_FORM, KIND_TEAM2_FORM, KIND_UNMAPPED]


def test_alias_ids_resolve_to_the_event_team():
    games = _h2h(_g("1", "alias-b", "x", 60, 50))
    assert prepare_h2h_games(games)[0]["kind"] == KIND_UNMAPPED
    assert prepare_h2h_games(games, aliases={"alias-b": "tb"})[0]["kind"] == KIND_TEAM2_FORM
    meeting = _h2h(_g("2", "ta", "alias-b", 60, 50))
    assert prepare_h2h_games(meeting, aliases={"alias-b": "tb"})[0]["kind"] == KIND_H2H


def test_no_event_teams_means_unmapped_not_a_guess():
    h = {"sport_id": 3, "teams": [], "game_shorts": [_g("1", "ta", "tb", 90, 80)]}
    assert prepare_h2h_games(h)[0]["kind"] == KIND_UNMAPPED


def test_same_game_listed_twice_or_under_two_game_ids_is_kept_once():
    rows = prepare_h2h_games(_h2h(_g("1", "ta", "tb", 82, 89), _g("1", "ta", "tb", 82, 89),
                                  _g("2", "tb", "ta", 89, 82), _g("3", "ta", "tb", 82, 89)))
    assert [r["game_id"] for r in rows] == ["1", "2"]    # "2" is the reversed listing: kept (different pair order)


def test_undated_games_with_equal_scores_are_not_collapsed():
    rows = prepare_h2h_games(_h2h(_g("1", "ta", "tb", 80, 70, date=None), _g("2", "ta", "tb", 80, 70, date=None)))
    assert len(rows) == 2


@pytest.mark.parametrize("s1,s2,flag", [(0, 0, "no_score"), (20, 0, "forfeit"), (0, 20, "forfeit"),
                                       (90, 80, None), (None, None, None)])
def test_basketball_placeholder_scores(s1, s2, flag):
    assert placeholder_flag(3, s1, s2) == flag


def test_placeholders_are_basketball_only():
    assert placeholder_flag(1, 0, 0) is None          # a football 0-0 is a result
    assert placeholder_flag(2, 20, 0) is None


def test_placeholder_game_keeps_its_row_with_null_scores_and_no_periods():
    g = _g("1", "ta", "tb", 20, 0, periods=[{"period_key": 18, "period_name": "QUARTER_1",
                                              "home_score": 5, "away_score": 0}], winner=1)
    row = prepare_h2h_games(_h2h(g))[0]
    assert (row["score1"], row["score2"], row["winner"], row["result_flag"]) == (None, None, None, "forfeit")
    assert row["periods"] == []


def test_zero_zero_period_drops_the_games_period_rows():
    ok = [{"period_name": f"QUARTER_{i}", "home_score": 20, "away_score": 18} for i in range(1, 5)]
    assert clean_periods(ok, 3) == ok
    assert clean_periods(ok[:3] + [{"period_name": "QUARTER_4", "home_score": 0, "away_score": 0}], 3) == []
    assert clean_periods(ok[:3] + [{"period_name": "QUARTER_4", "home_score": None, "away_score": 18}], 3) == []
    assert clean_periods([{"period_name": "HALF_1", "home_score": 0, "away_score": 0}], 1)   # not basketball


def test_event_teams_match_by_name_then_by_elimination():
    h = {"teams": TEAMS}
    assert match_event_teams(h, "Alpha", "Beta") == ("ta", "tb")
    assert match_event_teams(h, "beta ", "ALPHA") == ("tb", "ta")           # order in the feed does not matter
    assert match_event_teams(h, "Alpha", "Beta (W)") == ("ta", "tb")        # one name differs: the other team
    assert match_event_teams(h, "Gamma", "Delta") == (None, None)           # nothing matches: no guess


# --------------------------------------------------------------------------- #
# Stores
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


def _q(conn, sql):
    if store._is_orm(conn):
        from sqlalchemy import text
        return [tuple(r) for r in conn.execute(text(sql)).fetchall()]
    return [tuple(r) for r in conn.execute(sql).fetchall()]


def _result(home="Alpha", away="Beta", h2h=None, event_id="E1"):
    start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    return {"skin": "linebet", "action": "list_prematch", "url": "u", "extracted_at": "2026-10-03T10:00:00+00:00",
            "success": True, "event_count": 1, "events": [{
                "event_id": event_id, "sport": "basketball", "sport_id": 3, "competition": "L", "league_id": 1,
                "home": home, "away": away, "start_time": start, "markets": [], "h2h_data": h2h}]}


def test_persist_stores_kind_and_flag_and_skips_duplicates(conn):
    h = _h2h(_g("1", "ta", "tb", 90, 80), _g("1", "ta", "tb", 90, 80), _g("2", "ta", "x", 60, 50, date="2026-01-03"),
             _g("3", "tb", "z", 20, 0, date="2026-01-04"), _g("4", "ta", "tb", 0, 0, date="2026-02-01"))
    store.persist_result(_result(h2h=h), conn=conn)
    rows = _q(conn, "SELECT game_id, kind, score1, score2, result_flag FROM h2h_games ORDER BY game_id")
    assert rows == [("1", "h2h", 90, 80, None), ("2", "team1_form", 60, 50, None),
                    ("3", "team2_form", None, None, "forfeit"), ("4", "h2h", None, None, "no_score")]
    store.persist_result(_result(h2h=h), conn=conn)                       # a re-scrape adds nothing
    assert _q(conn, "SELECT COUNT(*) FROM h2h_games")[0][0] == 4


def test_event_teams_get_backend_ids_even_when_h2h_spells_them_differently(conn):
    h = {"sport_id": 3, "teams": [{"id": "ta", "title": "Alpha"}, {"id": "tb", "title": "Beta W"}], "game_shorts": []}
    store.persist_result(_result(home="Alpha", away="Beta", h2h=h), conn=conn)
    assert _q(conn, "SELECT t.backend_id FROM events e JOIN teams t ON t.team_id = e.home_team_id") == [("ta",)]
    assert _q(conn, "SELECT t.backend_id FROM events e JOIN teams t ON t.team_id = e.away_team_id") == [("tb",)]


def test_backfill_links_backend_ids_to_the_stored_event_teams(conn):
    store.persist_result(_result(), conn=conn)                       # stored without H2H: teams have no backend_id
    assert _q(conn, "SELECT COUNT(*) FROM teams WHERE backend_id IS NOT NULL")[0][0] == 0
    run = store.begin_backfill_run(conn, "linebet", "backfill_h2h")
    store.record_h2h(conn, run, "E1", "linebet", _h2h(_g("1", "ta", "tb", 90, 80)), "offered")
    assert _q(conn, "SELECT t.backend_id FROM events e JOIN teams t ON t.team_id = e.home_team_id") == [("ta",)]
    assert _q(conn, "SELECT t.backend_id FROM events e JOIN teams t ON t.team_id = e.away_team_id") == [("tb",)]
    assert _q(conn, "SELECT kind FROM h2h_games") == [("h2h",)]


def test_dedupe_removes_the_same_game_stored_under_two_game_ids(conn):
    store.persist_result(_result(), conn=conn)
    run = store.begin_backfill_run(conn, "linebet", "x")
    for gid in ("1", "2"):
        if store._is_orm(conn):
            from sqlalchemy import text
            conn.execute(text("INSERT INTO h2h_games (run_id, event_id, skin, game_id, team1_backend_id, "
                              "team2_backend_id, date_start, score1, score2, captured_at) VALUES "
                              "(:r,'E1','l',:g,'ta','tb','2026-01-01 00:00:00',82,89,'2026-10-03 10:00:00')"),
                         {"r": run, "g": gid})
        else:
            conn.execute("INSERT INTO h2h_games (run_id, event_id, skin, game_id, team1_backend_id, "
                         "team2_backend_id, date_start, score1, score2, captured_at) VALUES "
                         "(?,'E1','l',?,'ta','tb','2026-01-01T00:00:00',82,89,'2026-10-03T10:00:00')", (run, gid))
    conn.commit()
    assert store.dedupe_h2h_games(conn) == 1
    assert _q(conn, "SELECT COUNT(*) FROM h2h_games")[0][0] == 1


# --------------------------------------------------------------------------- #
# Results, removed lines, superseded events, aliases, repair
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("h,a,void", [(0, 0, True), (20, 0, True), (0, 20, True), (88, 81, False)])
def test_finished_basketball_with_a_placeholder_score_is_not_a_result(conn, h, a, void):
    store.persist_result(_result(), conn=conn)
    store.record_result(conn, "E1", stat_game_id="s1", score_home=h, score_away=a, winner=1, status=3,
                        at="2026-10-04T10:00:00+00:00")
    row = _q(conn, "SELECT result_status, final_score_home, final_score_away, winner FROM events")[0]
    assert row == ((-2, None, None, None) if void else (3, h, a, 1))
    assert store.events_needing_results(conn, min_age_seconds=0) == []   # not asked again either way


def test_simulated_alternative_matches_are_not_asked_for_a_result(conn):
    """"<League>. Alternative Matches" are the bookmaker's own simulated markets: the source never
    publishes a result for them, so the results work list leaves them out."""
    for eid, league in (("E1", "EuroCup"), ("E2", "EuroCup. Alternative Matches")):
        r = _result(event_id=eid)
        r["events"][0]["competition"] = league
        r["events"][0]["league_id"] = 100 + int(eid[1:])
        r["events"][0]["start_time"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        store.persist_result(r, conn=conn)
    pending = [e for e, _ in store.events_needing_results(conn, min_age_seconds=0)]
    assert "E1" in pending and "E2" not in pending
    store.mark_alternative(conn)      # persist already flagged it; a second call changes nothing
    assert _q(conn, "SELECT event_id, is_alternative FROM events ORDER BY event_id") == [("E1", 0), ("E2", 1)]


def test_events_by_ids_names_the_asked_matches_only(conn):
    """`results --event ID`: the work list is exactly the asked, stored matches (status included)."""
    store.persist_result(_result(), conn=conn)
    assert store.events_by_ids(conn, ["E1", "nope"]) == [("E1", None, None)]
    store.record_result(conn, "E1", stat_game_id="s1", score_home=88, score_away=81, winner=1, status=3,
                        at="2026-10-04T10:00:00+00:00")
    assert store.events_by_ids(conn, ["E1"]) == [("E1", "s1", 3)]


def test_a_football_nil_nil_is_still_a_result(conn):
    r = _result()
    r["events"][0].update(sport="football", sport_id=1)
    store.persist_result(r, conn=conn)
    store.record_result(conn, "E1", score_home=0, score_away=0, winner=0, status=3, at="2026-10-04T10:00:00+00:00")
    assert _q(conn, "SELECT result_status, final_score_home, final_score_away FROM events") == [(3, 0, 0)]


def _with_totals(lines, event_id="E1"):
    r = _result(event_id=event_id)
    r["events"][0]["markets"] = [{"name": "Total", "market_type": "total", "raw_g": 17, "scope": "FULL_MATCH",
                                  "selections": [s for line in lines for s in (
                                      {"name": "Over", "price": 1.9, "line": line},
                                      {"name": "Under", "price": 1.9, "line": line})]}]
    return r


def test_a_line_the_source_withdrew_is_stored_suspended(conn):
    store.persist_result(_with_totals([160.5, 161.5]), conn=conn)
    store.persist_result(_with_totals([161.5]), conn=conn)                # 160.5 is gone
    latest = _q(conn, "SELECT line, MAX(snap_id), is_suspended FROM odds_snapshots GROUP BY line, selection_name "
                      "ORDER BY line")
    assert {(line, bool(susp)) for line, _, susp in latest} == {(160.5, True), (161.5, False)}
    store.persist_result(_with_totals([161.5]), conn=conn)                # nothing new to say
    assert _q(conn, "SELECT COUNT(*) FROM odds_snapshots")[0][0] == 6


def test_a_scope_that_did_not_come_back_withdraws_nothing(conn):
    store.persist_result(_with_totals([160.5]), conn=conn)
    store.persist_result(_result(), conn=conn)                            # no markets at all this time
    assert _q(conn, "SELECT COUNT(*) FROM odds_snapshots WHERE is_suspended IN (1, TRUE)")[0][0] == 0


def test_a_superseded_event_gets_no_new_odds_or_h2h(conn):
    store.persist_result(_with_totals([160.5], event_id="E1"), conn=conn)
    store.persist_result(_with_totals([160.5], event_id="E2"), conn=conn)      # the re-listing, higher id
    store._run_sql(conn, "UPDATE events SET start_time = (SELECT start_time FROM events WHERE event_id = 'E1')", {})
    conn.commit()
    assert store.mark_superseded(conn) == 1
    assert _q(conn, "SELECT superseded_by FROM events WHERE event_id = 'E1'") == [("E2",)]
    before = _q(conn, "SELECT COUNT(*) FROM odds_snapshots WHERE event_id = 'E1'")[0][0]
    r = _with_totals([150.5], event_id="E1")
    r["events"][0]["h2h_data"] = _h2h(_g("1", "ta", "tb", 90, 80))
    store.persist_result(r, conn=conn)
    assert _q(conn, "SELECT COUNT(*) FROM odds_snapshots WHERE event_id = 'E1'")[0][0] == before
    assert _q(conn, "SELECT COUNT(*) FROM h2h_games WHERE event_id = 'E1'")[0][0] == 0


def _insert_game(conn, run, event_id, gid, t1, t2, s1, s2, date="2026-01-01 00:00:00", sport=3):
    params = dict(r=run, e=event_id, g=gid, t1=t1, t2=t2, s1=s1, s2=s2, d=date, sp=sport,
                  c=store._ts_for(conn, "2026-10-03T10:00:00+00:00"))
    sql = ("INSERT INTO h2h_games (run_id, event_id, skin, game_id, sport_id, team1_backend_id, team2_backend_id, "
           "date_start, score1, score2, captured_at) VALUES (:r,:e,'l',:g,:sp,:t1,:t2,:d,:s1,:s2,:c)")
    store._run_sql(conn, sql, params)
    conn.commit()


def test_repair_cleans_old_rows_and_learns_aliases(conn):
    # E1 = Alpha v Beta (ta, tb). Beta's history also lists a game under a second id "tb2".
    h = {"sport_id": 3, "teams": TEAMS, "game_shorts": []}
    store.persist_result(_result(h2h=h), conn=conn)
    run = store.begin_backfill_run(conn, "linebet", "x")
    _insert_game(conn, run, "E1", "g1", "tb", "q", 70, 60, date="2026-02-02 19:00:00")      # known id
    _insert_game(conn, run, "E1", "g2", "tb2", "q", 70, 60, date="2026-02-02 19:00:00")     # same game, alias
    _insert_game(conn, run, "E1", "g3", "tb2", "r", 55, 54, date="2026-02-09 19:00:00")     # only under the alias
    _insert_game(conn, run, "E1", "g4", "ta", "tb", 0, 0, date="2026-03-01 19:00:00")       # placeholder
    _insert_game(conn, run, "E1", "g5", "ta", "z", 20, 0, date="2026-03-02 19:00:00")       # forfeit token
    _insert_game(conn, run, "E1", "g6", "u", "v", 80, 70, date="2026-03-03 19:00:00")       # matches nothing
    store._run_sql(conn, "INSERT INTO h2h_period_scores (h2h_game_id, event_id, period_key, period_name, "
                         "home_score, away_score) SELECT id, event_id, 18, 'QUARTER_1', 0, 0 FROM h2h_games "
                         "WHERE game_id = 'g1'", {})
    store._run_sql(conn, "UPDATE events SET sport_id = 3, result_status = 3, final_score_home = 0, "
                         "final_score_away = 0 WHERE event_id = 'E1'", {})
    conn.commit()

    out = store.repair_data_quality(conn)
    assert out["placeholder_h2h_games"] == 2 and out["voided_results"] == 1 and out["aliases_added"] == 1
    assert out["h2h_games_with_empty_periods"] == 1
    assert _q(conn, "SELECT alias_backend_id, backend_id FROM team_aliases") == [("tb2", "tb")]
    kinds = dict(_q(conn, "SELECT game_id, kind FROM h2h_games"))
    assert kinds == {"g1": "team2_form", "g2": "team2_form", "g3": "team2_form", "g4": "h2h",
                     "g5": "team1_form", "g6": "unmapped"}
    assert _q(conn, "SELECT score1, score2, result_flag FROM h2h_games WHERE game_id IN ('g4', 'g5') "
                    "ORDER BY game_id") == [(None, None, "no_score"), (None, None, "forfeit")]
    assert _q(conn, "SELECT result_status, final_score_home FROM events") == [(-2, None)]
    assert store.repair_data_quality(conn) == {"duplicate_h2h_games": 0, "placeholder_h2h_games": 0,
                                               "h2h_games_with_empty_periods": 0, "voided_results": 0,
                                               "aliases_added": 0, "h2h_kind_changed": 0, "alternative_matches_flagged": 0}


def test_an_alias_that_matches_two_teams_is_left_unmapped(conn):
    store.persist_result(_result(h2h={"sport_id": 3, "teams": TEAMS, "game_shorts": []}), conn=conn)
    run = store.begin_backfill_run(conn, "linebet", "x")
    _insert_game(conn, run, "E1", "g1", "ta", "q", 70, 60)
    _insert_game(conn, run, "E1", "g2", "tb", "q", 70, 60)          # same date/opponent/score under both teams
    _insert_game(conn, run, "E1", "g3", "mystery", "q", 70, 60)
    assert store.resolve_team_aliases(conn) == 0


def test_backfill_queue_asks_again_only_for_events_whose_teams_lack_backend_ids(conn):
    store.persist_result(_result(), conn=conn)
    run = store.begin_backfill_run(conn, "linebet", "x")
    _insert_game(conn, run, "E1", "g1", "ta", "tb", 70, 60)           # has H2H, but the teams are unlinked
    assert store.events_missing_h2h(conn) == ["E1"]
    store.record_coverage(conn, run, "E1", "linebet", "h2h", "offered")   # asked just now: leave it alone
    assert store.events_missing_h2h(conn) == []
