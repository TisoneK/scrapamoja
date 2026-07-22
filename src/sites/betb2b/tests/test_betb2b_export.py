"""Tests for the scorewise-engine exporter (ADR-7)."""

from __future__ import annotations

import pytest

from src.sites.betb2b.export.scorewise import event_to_predict_requests, _h2h_for_scope


def _mkt(name, scope, rungs):
    return {"name": name, "market_type": "total", "raw_g": 17, "scope": scope,
            "selections": [{"name": s, "price": p, "line": ln} for (s, ln, p) in rungs]}


def _event():
    return {
        "event_id": "738047045", "home": "Phoenix", "away": "Rain or Shine",
        "markets": [
            _mkt("Total", "FULL_MATCH",
                 [("Over", 215.5, 1.72), ("Over", 216.5, 1.87), ("Over", 217.5, 2.0),
                  ("Under", 216.5, 1.95)]),
            _mkt("Total", "QUARTER_1", [("Over", 52.5, 1.85), ("Under", 52.5, 1.9)]),
            _mkt("Individual Total Home", "FULL_MATCH",
                 [("Over", 109.5, 1.8), ("Under", 109.5, 2.0)]),
        ],
        "h2h_data": {
            "sport_id": 3,
            "teams": [{"id": "A", "title": "Phoenix"}, {"id": "B", "title": "Rain or Shine"}],
            "game_shorts": [
                {"team1_id": "A", "team2_id": "B", "date_start": "2024-09-10T00:00:00+00:00",
                 "score1": 107, "score2": 122, "status": 3,
                 "periods": [{"period_key": 18, "home_score": 33, "away_score": 31},
                             {"period_key": 19, "home_score": 24, "away_score": 33}]},
                {"team1_id": "A", "team2_id": "B", "date_start": "2026-12-01T00:00:00+00:00",
                 "score1": 0, "score2": 0, "status": 1, "periods": []},  # future — filtered
            ],
        },
    }


def test_match_total_is_nearest_185_and_half():
    reqs = {r["scope"]: r for r in event_to_predict_requests(_event())}
    # 216.5 Over=1.87 is nearest 1.85 (vs 1.72 / 2.0); 217.5 also .5 but farther.
    assert reqs["FULL_MATCH"]["odds"]["match_total"] == 216.5
    assert reqs["FULL_MATCH"]["odds"]["over_odds"] == 1.87
    assert reqs["FULL_MATCH"]["odds"]["under_odds"] == 1.95


def test_scopes_present():
    scopes = {r["scope"] for r in event_to_predict_requests(_event())}
    assert "FULL_MATCH" in scopes
    assert "QUARTER_1" in scopes
    assert "HOME_TEAM_TOTAL" in scopes          # from Individual Total Home
    assert "AWAY_TEAM_TOTAL" not in scopes       # no away-total market → omitted


def test_h2h_scores_match_scope():
    ev = _event()
    full = _h2h_for_scope(ev, "FULL_MATCH", "Phoenix", "Rain or Shine")
    assert len(full) == 1                        # future fixture filtered out
    assert (full[0]["home_score"], full[0]["away_score"]) == (107, 122)
    assert full[0]["home_team"] == "Phoenix" and full[0]["date"] == "2024-09-10"
    q1 = _h2h_for_scope(ev, "QUARTER_1", "Phoenix", "Rain or Shine")
    assert (q1[0]["home_score"], q1[0]["away_score"]) == (33, 31)
    fh = _h2h_for_scope(ev, "FIRST_HALF", "Phoenix", "Rain or Shine")
    assert (fh[0]["home_score"], fh[0]["away_score"]) == (57, 64)   # Q1+Q2


def test_empty_event_yields_nothing():
    assert event_to_predict_requests({"event_id": "1", "home": "", "away": ""}) == []


# ---------------------------------------------------------------------------
# Semantic validation (ADR-8) — the engine's s02_h2h_totals ALWAYS computes
# `home_score + away_score`, whatever the scope. Structural checks (fields
# present, types right) miss the bug class where every field is valid but the
# sum the engine derives is the wrong quantity — that shipped once already
# (team totals carried full-match scores → ~229 compared against an ~109.5
# individual line → false HIGH OVER). These tests simulate the engine's
# computation instead of inspecting the fields.
# ---------------------------------------------------------------------------

# One played H2H game, quarter by quarter. Home 33+24+25+25 = 107,
# away 31+33+30+28 = 122 — the per-scope expectations below derive from these.
_Q = [(18, 33, 31), (19, 24, 33), (20, 25, 30), (21, 25, 28)]

# scope → the quantity the engine must arrive at by summing home+away.
_ENGINE_TOTAL_BY_SCOPE = {
    "FULL_MATCH": 229,        # 107 + 122 — both teams, whole game
    "FIRST_HALF": 121,        # (33+24) + (31+33)
    "SECOND_HALF": 108,       # (25+25) + (30+28)
    "QUARTER_1": 64,
    "QUARTER_2": 57,
    "QUARTER_3": 55,
    "QUARTER_4": 53,
    "HOME_TEAM_TOTAL": 107,   # home only — away zeroed
    "AWAY_TEAM_TOTAL": 122,   # away only — home zeroed
}


def _h2h_game(*, team1_id="A", team2_id="B", score1=107, score2=122):
    """A played head-to-head game. Swap the ids to get the reversed orientation
    (the visiting side listed as team1), which is how the feed really reports
    alternating home advantage."""
    reverse = team1_id != "A"
    periods = [{"period_key": k, "home_score": (b if reverse else a),
                "away_score": (a if reverse else b)} for (k, a, b) in _Q]
    return {"team1_id": team1_id, "team2_id": team2_id, "status": 3,
            "date_start": "2024-09-10T00:00:00+00:00",
            "score1": score1, "score2": score2, "periods": periods}


def _all_scopes_event(h2h_games=None):
    """An event carrying a .5 Over rung for every one of the 9 scopes, so
    ``event_to_predict_requests`` emits the full set."""
    rungs = [("Over", 100.5, 1.85), ("Under", 100.5, 1.9)]
    markets = [_mkt("Total", sc, rungs) for sc in
               ("FULL_MATCH", "FIRST_HALF", "SECOND_HALF",
                "QUARTER_1", "QUARTER_2", "QUARTER_3", "QUARTER_4")]
    markets += [_mkt("Individual Total Home", "FULL_MATCH", rungs),
                _mkt("Individual Total Away", "FULL_MATCH", rungs)]
    return {
        "event_id": "738047045", "home": "Phoenix", "away": "Rain or Shine",
        "markets": markets,
        "h2h_data": {
            "sport_id": 3,
            "teams": [{"id": "A", "title": "Phoenix"}, {"id": "B", "title": "Rain or Shine"}],
            "game_shorts": h2h_games if h2h_games is not None else [_h2h_game()],
        },
    }


@pytest.mark.parametrize("scope,expected", sorted(_ENGINE_TOTAL_BY_SCOPE.items()))
def test_h2h_sum_is_the_scope_relevant_quantity(scope, expected):
    """What the engine computes (home+away) must BE the scope's quantity."""
    reqs = {r["scope"]: r for r in event_to_predict_requests(_all_scopes_event())}
    assert scope in reqs, f"{scope} not emitted — the event has a .5 line for it"
    (m,) = reqs[scope]["h2h_matches"]
    assert m["home_score"] + m["away_score"] == expected


def test_all_nine_scopes_are_emitted_when_the_markets_are_there():
    reqs = event_to_predict_requests(_all_scopes_event())
    assert {r["scope"] for r in reqs} == set(_ENGINE_TOTAL_BY_SCOPE)


def test_team_totals_do_not_carry_the_full_match_total():
    """The `20eda23` regression, stated as the engine sees it: a team-total
    request whose H2H sums to the full-game total makes every game trivially
    OVER an individual line."""
    reqs = {r["scope"]: r for r in event_to_predict_requests(_all_scopes_event())}
    full = sum(reqs["FULL_MATCH"]["h2h_matches"][0][k] for k in ("home_score", "away_score"))
    for scope in ("HOME_TEAM_TOTAL", "AWAY_TEAM_TOTAL"):
        (m,) = reqs[scope]["h2h_matches"]
        assert m["home_score"] + m["away_score"] < full
        assert 0 in (m["home_score"], m["away_score"])


@pytest.mark.parametrize("scope,zeroed,kept", [("HOME_TEAM_TOTAL", "away_score", "home_score"),
                                               ("AWAY_TEAM_TOTAL", "home_score", "away_score")])
def test_team_total_zeroing_happens_after_orientation(scope, zeroed, kept):
    """When the feed lists the event's away side as team1, the scores are
    swapped into the event's orientation FIRST — zeroing before that would
    keep the wrong team's points under the right key."""
    ev = _all_scopes_event([_h2h_game(team1_id="B", team2_id="A", score1=122, score2=107)])
    (m,) = _h2h_for_scope(ev, scope, "Phoenix", "Rain or Shine")
    assert m[zeroed] == 0
    assert m[kept] == _ENGINE_TOTAL_BY_SCOPE[scope]   # 107 home / 122 away


def test_reversed_orientation_holds_for_every_scope():
    """The same expectations as the parametrized test, on the reversed feed
    ordering — orientation must not leak into any scope's aggregation."""
    ev = _all_scopes_event([_h2h_game(team1_id="B", team2_id="A", score1=122, score2=107)])
    for scope, expected in _ENGINE_TOTAL_BY_SCOPE.items():
        (m,) = _h2h_for_scope(ev, scope, "Phoenix", "Rain or Shine")
        assert m["home_score"] + m["away_score"] == expected, scope
