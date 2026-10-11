"""Tests for the derived score-state helpers (src/sites/flashscore/poll.py).

All pure — the quarter parsing and the "freeze the Q1 total when play leaves
the 1st quarter" state machine run without a browser. These are the fields a
task2sms HTTP Data Source polls and keys its conditions off.
"""

from __future__ import annotations

from src.sites.flashscore.poll import (
    derive_score_state,
    parse_score,
    parse_stage,
)

# ------------------------------ parse_stage ---------------------------- #

def test_parse_stage_first_quarter_with_clock():
    p = parse_stage("1st Quarter 8")
    assert p["quarter"] == 1
    assert p["is_q1"] is True
    assert p["past_q1"] is False
    assert p["clock"] == "8"


def test_parse_stage_second_quarter_is_past_q1():
    p = parse_stage("2nd Quarter 7:12")
    assert p["quarter"] == 2
    assert p["is_q1"] is False
    assert p["past_q1"] is True
    assert p["clock"] == "7:12"


def test_parse_stage_half_time_is_past_q1_without_quarter():
    p = parse_stage("Half Time")
    assert p["quarter"] is None
    assert p["is_q1"] is False
    assert p["past_q1"] is True


def test_parse_stage_empty():
    p = parse_stage("")
    assert p["quarter"] is None
    assert p["is_q1"] is False
    assert p["past_q1"] is False


# ------------------------------ parse_score ---------------------------- #

def test_parse_score_numeric():
    assert parse_score("17-18") == (17, 18)
    assert parse_score("100-98") == (100, 98)


def test_parse_score_missing_or_placeholder():
    assert parse_score("") == (None, None)
    assert parse_score(None) == (None, None)
    assert parse_score("-") == (None, None)


# --------------------------- derive_score_state ------------------------ #

def _match(home_away, stage, *, home="Hapoel Beer Sheva", away="Hapoel Tel Aviv"):
    return {"teams": {"home": home, "away": away}, "score": home_away,
            "time": stage, "status": "live"}


def test_derive_not_found_carries_sticky_q1():
    prev = {"q1_final": 42, "q1_ended": True, "q1_total": 42, "match": "A vs B"}
    s = derive_score_state(None, prev, target="A vs B")
    assert s["found"] is False
    assert s["q1_final"] == 42
    assert s["q1_ended"] is True
    assert s["match"] == "A vs B"


def test_derive_live_in_q1_sets_q1_total_not_final():
    s = derive_score_state(_match("12-10", "1st Quarter 8"))
    assert s["found"] is True
    assert s["is_q1"] is True
    assert (s["home"], s["away"], s["total"]) == (12, 10, 22)
    assert s["q1_total"] == 22
    assert s["q1_final"] is None
    assert s["q1_ended"] is False
    assert s["match"] == "Hapoel Beer Sheva vs Hapoel Tel Aviv"


def test_derive_freezes_q1_final_on_quarter_boundary():
    # Last Q1 cycle: total 27.
    q1 = derive_score_state(_match("14-13", "1st Quarter 1"))
    assert q1["q1_total"] == 27 and q1["q1_final"] is None
    # Now Q2 starts: q1_final freezes to the last Q1 total (27), not the new total.
    q2 = derive_score_state(_match("15-13", "2nd Quarter 9"), q1)
    assert q2["is_q1"] is False
    assert q2["q1_ended"] is True
    assert q2["q1_final"] == 27
    assert q2["total"] == 28  # current running total keeps climbing


def test_derive_q1_final_is_sticky_after_freeze():
    q1 = derive_score_state(_match("14-13", "1st Quarter 1"))
    q2 = derive_score_state(_match("15-13", "2nd Quarter 9"), q1)
    half = derive_score_state(_match("30-28", "Half Time"), q2)
    assert half["q1_final"] == 27
    assert half["q1_ended"] is True
