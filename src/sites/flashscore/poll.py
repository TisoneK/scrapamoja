"""Interval poller for Flashscore live matches.

:func:`poll_loop` is the pure control loop (injectable clock/sleep, no I/O of
its own) so it is unit-testable without a browser — the same proven design as
the BetB2B poller (:mod:`src.sites.betb2b.poll`). The CLI (`flashscore
live-poll`) wires the real :class:`~src.sites.flashscore.scraper.FlashscoreScraper`
into it.

:func:`select_live_matches` and :func:`format_match_line` are pure helpers the
CLI uses to pick the target match out of a scrape result and render one compact
line per cycle. Keeping them here (not in the command) means they are covered
by unit tests that never launch a browser.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

__all__ = ["poll_loop", "select_live_matches", "format_match_line"]


async def poll_loop(
    *,
    scrape_once: Callable[[], Awaitable[Any]],
    persist: Callable[[Any], Any],
    interval: float,
    cycles: int = 0,
    max_seconds: float = 0.0,
    on_cycle: Callable[[int, Any, Any], None] | None = None,
    on_error: Callable[[int, Exception], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> int:
    """Scrape + persist repeatedly; return the number of cycles completed.

    One cycle = ``scrape_once()`` -> ``persist(result)`` -> ``on_cycle``. The
    next cycle starts ``interval`` seconds after this one *started* (never
    negative; if a scrape overruns the interval, the next starts immediately).
    A failed scrape/persist is reported via ``on_error`` and does NOT stop the
    loop — a flaky network cycle must not kill a live poller.

    Stops when: ``cycles`` completed (if > 0), ``max_seconds`` of wall-clock
    elapsed (if > 0), or ``should_stop()`` returns True (checked each cycle).
    """
    start = clock()
    n = 0
    while True:
        if should_stop is not None and should_stop():
            break

        t0 = clock()
        try:
            result = await scrape_once()
            run_id = persist(result)
            n += 1
            if on_cycle is not None:
                on_cycle(n, result, run_id)
        except Exception as exc:  # noqa: BLE001 — one bad cycle must not kill the poller
            if on_error is not None:
                on_error(n + 1, exc)

        if cycles and n >= cycles:
            break
        if max_seconds and (clock() - start) >= max_seconds:
            break
        if should_stop is not None and should_stop():
            break

        wait = interval - (clock() - t0)
        if wait > 0:
            await sleep(wait)

    return n


def select_live_matches(
    matches: list[dict[str, Any]] | None,
    *,
    team: str | None = None,
    match_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return the scraped match dicts that match the filter.

    ``team`` is a case-insensitive substring tested against BOTH the home and
    away team name (so "beer sheva" finds "Hapoel Beer Sheva" on either side).
    ``match_id`` is an exact Flashscore match id. With neither filter, every
    (non-error) match is returned. Error rows (``{"error": ...}``) and
    non-dict entries are always dropped.
    """
    out: list[dict[str, Any]] = []
    needle = team.lower() if team else None
    for m in matches or []:
        if not isinstance(m, dict) or m.get("error"):
            continue
        if match_id and m.get("match_id") != match_id:
            continue
        if needle:
            teams = m.get("teams") or {}
            home = (teams.get("home") or "").lower()
            away = (teams.get("away") or "").lower()
            if needle not in home and needle not in away:
                continue
        out.append(m)
    return out


def format_match_line(
    m: dict[str, Any],
    *,
    cycle: int | None = None,
    now: datetime | None = None,
) -> str:
    """Render one compact line for a scraped match, e.g.::

        [cycle 3 07:42:10] Hapoel Beer Sheva 18-15 Hapoel Tel Aviv | live

    The trailing segment is the live stage/clock when the scrape provides one
    (basketball listings often leave it blank — see the module docstring),
    falling back to the status word.
    """
    teams = m.get("teams") or {}
    home = teams.get("home") or "?"
    away = teams.get("away") or "?"
    score = m.get("score") or "-"
    stage = (m.get("time") or "").strip()
    status = (m.get("status") or "").strip()
    ts = (now or datetime.now(UTC)).strftime("%H:%M:%S")
    prefix = f"[{ts}]" if cycle is None else f"[cycle {cycle} {ts}]"
    tail = f" | {stage}" if stage else (f" | {status}" if status else "")
    return f"{prefix} {home} {score} {away}{tail}"
