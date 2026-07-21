"""Tests for the interval poll loop (src/sites/betb2b/poll.py).

The loop is pure — clock/sleep are injected — so we test stop conditions,
interval pacing, and error resilience without a browser or a database.
"""

from __future__ import annotations

import pytest

from src.sites.betb2b.poll import poll_loop


class _Clock:
    """Deterministic clock advanced by the fake sleep."""
    def __init__(self):
        self.t = 0.0
    def __call__(self):
        return self.t


def _fakes(scrape_cost=0.0):
    clock = _Clock()
    slept: list[float] = []

    async def sleep(s):
        slept.append(s)
        clock.t += s

    async def scrape_once():
        clock.t += scrape_cost  # a scrape takes wall-clock time
        return {"event_count": 1}

    persisted: list = []

    def persist(r):
        persisted.append(r)
        return len(persisted)  # fake run_id

    return clock, sleep, slept, scrape_once, persist, persisted


async def test_stops_after_cycles():
    clock, sleep, slept, scrape_once, persist, persisted = _fakes()
    n = await poll_loop(scrape_once=scrape_once, persist=persist, interval=10,
                        cycles=3, clock=clock, sleep=sleep)
    assert n == 3
    assert len(persisted) == 3
    # Sleeps happen between cycles, not after the last one.
    assert len(slept) == 2


async def test_stops_after_max_seconds():
    # Each scrape costs 4s; max_seconds=10 → cycles at t=0,? stop once elapsed>=10.
    clock, sleep, slept, scrape_once, persist, persisted = _fakes(scrape_cost=4.0)
    n = await poll_loop(scrape_once=scrape_once, persist=persist, interval=0,
                        max_seconds=10, clock=clock, sleep=sleep)
    # t after cycle1=4, cycle2=8, cycle3=12 (>=10 → stop). So 3 cycles.
    assert n == 3


async def test_interval_paces_from_cycle_start():
    # scrape costs 3s, interval 10 → sleep 7s between cycles.
    clock, sleep, slept, scrape_once, persist, persisted = _fakes(scrape_cost=3.0)
    await poll_loop(scrape_once=scrape_once, persist=persist, interval=10,
                    cycles=2, clock=clock, sleep=sleep)
    assert slept == [pytest.approx(7.0)]


async def test_overrun_does_not_sleep_negative():
    # scrape costs 12s but interval is 10 → no sleep (next starts immediately).
    clock, sleep, slept, scrape_once, persist, persisted = _fakes(scrape_cost=12.0)
    await poll_loop(scrape_once=scrape_once, persist=persist, interval=10,
                    cycles=2, clock=clock, sleep=sleep)
    assert slept == []  # never a negative/zero sleep


async def test_should_stop_halts_before_next_cycle():
    clock, sleep, slept, scrape_once, persist, persisted = _fakes()

    # Stop once 2 cycles have been persisted (checked each iteration).
    n = await poll_loop(scrape_once=scrape_once, persist=persist, interval=1,
                        should_stop=lambda: len(persisted) >= 2,
                        clock=clock, sleep=sleep)
    assert n == 2


async def test_bad_cycle_does_not_kill_the_loop():
    clock = _Clock()
    slept: list[float] = []

    async def sleep(s):
        slept.append(s)

    calls = {"n": 0}

    async def scrape_once():
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("transient scrape failure")
        return {"event_count": 1}

    errors: list = []
    persisted: list = []
    n = await poll_loop(
        scrape_once=scrape_once,
        persist=lambda r: persisted.append(r),
        interval=1, cycles=3,
        on_error=lambda i, e: errors.append((i, str(e))),
        clock=clock, sleep=sleep,
    )
    # The failing cycle 2 doesn't count as completed, so it takes 4 scrape
    # attempts to reach 3 completed cycles — the loop recovered, didn't die.
    assert n == 3
    assert len(persisted) == 3
    assert calls["n"] == 4
    assert len(errors) == 1 and "transient" in errors[0][1]
