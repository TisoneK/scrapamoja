"""Tests for the Flashscore live poller (src/sites/flashscore/poll.py).

The loop is pure — clock/sleep are injected — so stop conditions, interval
pacing and error resilience are tested without a browser. The selection and
formatting helpers are likewise pure and cover the real scrape dict shape
(``teams``/``score``/``time``/``status``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.sites.flashscore.poll import (
    format_match_line,
    poll_loop,
    select_live_matches,
)


class _Clock:
    """Deterministic clock advanced by the fake sleep."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _fakes(scrape_cost=0.0, result=None):
    clock = _Clock()
    slept: list[float] = []

    async def sleep(s):
        slept.append(s)
        clock.t += s

    async def scrape_once():
        clock.t += scrape_cost
        return result if result is not None else {"selected": []}

    persisted: list = []

    def persist(r):
        persisted.append(r)
        return len(persisted)

    return clock, sleep, slept, scrape_once, persist, persisted


# --------------------------- poll_loop --------------------------------- #

async def test_stops_after_cycles():
    clock, sleep, slept, scrape_once, persist, persisted = _fakes()
    n = await poll_loop(scrape_once=scrape_once, persist=persist, interval=10,
                        cycles=3, clock=clock, sleep=sleep)
    assert n == 3
    assert len(persisted) == 3
    # Sleeps happen between cycles, not after the last one.
    assert len(slept) == 2


async def test_stops_after_max_seconds():
    clock, sleep, slept, scrape_once, persist, persisted = _fakes(scrape_cost=4.0)
    n = await poll_loop(scrape_once=scrape_once, persist=persist, interval=0,
                        max_seconds=10, clock=clock, sleep=sleep)
    # t after cycle1=4, cycle2=8, cycle3=12 (>=10 -> stop). So 3 cycles.
    assert n == 3


async def test_interval_paces_from_cycle_start():
    clock, sleep, slept, scrape_once, persist, persisted = _fakes(scrape_cost=3.0)
    await poll_loop(scrape_once=scrape_once, persist=persist, interval=10,
                    cycles=2, clock=clock, sleep=sleep)
    assert slept == [pytest.approx(7.0)]


async def test_overrun_does_not_sleep_negative():
    # scrape costs 15s, interval 10 -> next cycle starts immediately (no sleep).
    clock, sleep, slept, scrape_once, persist, persisted = _fakes(scrape_cost=15.0)
    await poll_loop(scrape_once=scrape_once, persist=persist, interval=10,
                    cycles=2, clock=clock, sleep=sleep)
    assert slept == []


async def test_error_does_not_stop_loop():
    clock = _Clock()
    calls = {"n": 0}
    errors: list[int] = []

    async def sleep(s):
        clock.t += s

    async def scrape_once():
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("network blip")
        return {"selected": []}

    def on_error(n, exc):
        errors.append(n)

    # 3 successful cycles are needed; the failing call #2 is not counted.
    n = await poll_loop(scrape_once=scrape_once, persist=lambda r: None,
                        interval=1, cycles=3, on_error=on_error,
                        clock=clock, sleep=sleep)
    assert n == 3            # 3 successful cycles completed
    assert calls["n"] == 4   # one extra call for the failed cycle
    assert errors == [2]     # the failure was reported, loop kept going


async def test_should_stop_before_first_cycle():
    clock, sleep, slept, scrape_once, persist, persisted = _fakes()
    n = await poll_loop(scrape_once=scrape_once, persist=persist, interval=10,
                        should_stop=lambda: True, clock=clock, sleep=sleep)
    assert n == 0
    assert persisted == []


# ----------------------- select_live_matches --------------------------- #

_MATCHES = [
    {"match_id": "aaa", "teams": {"home": "Hapoel Beer Sheva",
                                  "away": "Hapoel Tel Aviv"}, "score": "18-15"},
    {"match_id": "bbb", "teams": {"home": "Olimpia Milano",
                                  "away": "Treviso"}, "score": "38-28"},
    {"error": "boom"},
    "not-a-dict",
]


def test_select_by_team_substring_either_side():
    # Away-team substring, different case.
    out = select_live_matches(_MATCHES, team="tel aviv")
    assert [m["match_id"] for m in out] == ["aaa"]
    # Home-team substring.
    out = select_live_matches(_MATCHES, team="milano")
    assert [m["match_id"] for m in out] == ["bbb"]


def test_select_by_match_id():
    out = select_live_matches(_MATCHES, match_id="bbb")
    assert [m["match_id"] for m in out] == ["bbb"]


def test_select_drops_errors_and_non_dicts_when_unfiltered():
    out = select_live_matches(_MATCHES)
    assert [m["match_id"] for m in out] == ["aaa", "bbb"]


def test_select_no_match_returns_empty():
    assert select_live_matches(_MATCHES, team="nonexistent") == []
    assert select_live_matches(None, team="x") == []


# ------------------------ format_match_line ---------------------------- #

_T = datetime(2026, 10, 11, 7, 42, 10, tzinfo=UTC)


def test_format_with_stage():
    m = {"teams": {"home": "A", "away": "B"}, "score": "10-8", "time": "Q2"}
    assert format_match_line(m, cycle=3, now=_T) == "[cycle 3 07:42:10] A 10-8 B | Q2"


def test_format_falls_back_to_status_when_no_stage():
    m = {"teams": {"home": "A", "away": "B"}, "score": "10-8",
         "time": "", "status": "live"}
    assert format_match_line(m, cycle=1, now=_T) == "[cycle 1 07:42:10] A 10-8 B | live"


def test_format_missing_fields_are_placeholdered():
    assert format_match_line({}, now=_T) == "[07:42:10] ? - ?"
