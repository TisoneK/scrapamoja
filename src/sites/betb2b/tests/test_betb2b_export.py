"""Tests for the scorewise-engine exporter (ADR-7)."""

from __future__ import annotations

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
    full = _h2h_for_scope(ev, "FULL_MATCH")
    assert len(full) == 1                        # future fixture filtered out
    assert (full[0]["home_score"], full[0]["away_score"]) == (107, 122)
    assert full[0]["home_team"] == "Phoenix" and full[0]["date"] == "2024-09-10"
    q1 = _h2h_for_scope(ev, "QUARTER_1")
    assert (q1[0]["home_score"], q1[0]["away_score"]) == (33, 31)
    fh = _h2h_for_scope(ev, "FIRST_HALF")
    assert (fh[0]["home_score"], fh[0]["away_score"]) == (57, 64)   # Q1+Q2


def test_empty_event_yields_nothing():
    assert event_to_predict_requests({"event_id": "1", "home": "", "away": ""}) == []
