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
import re
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

__all__ = [
    "poll_loop",
    "select_live_matches",
    "format_match_line",
    "parse_stage",
    "parse_score",
    "derive_score_state",
]


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


# --------------------------------------------------------------------------- #
# Derived score state — turns one scraped match into the flat, JSON-friendly
# shape a task2sms HTTP Data Source polls (its conditions key off a single
# field like `q1_total` and its templates fill `{home}`/`{away}`/`{stage}`).
# All pure, so the quarter parsing and the "freeze the Q1 total when Q1 ends"
# state machine are unit-tested without a browser.
# --------------------------------------------------------------------------- #

_ORDINAL = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4}
_QUARTER_RE = re.compile(r"(1st|2nd|3rd|4th)\s*quarter|quarter\s*([1-4])", re.I)
_CLOCK_RE = re.compile(r"(\d{1,2}:\d{2}|\b\d{1,2}\b)\s*$")


def parse_stage(stage: str | None) -> dict[str, Any]:
    """Parse a live basketball stage string into structured fields.

    Examples: ``"1st Quarter 8"`` -> quarter 1, clock "8"; ``"Half Time"`` ->
    quarter None, past_q1 True; ``"2nd Quarter 7:12"`` -> quarter 2.
    ``past_q1`` is True once play has clearly moved beyond the 1st quarter
    (2nd+ quarter, half time, overtime, or a finished/after-match marker) —
    that is the edge the Q1 freeze watches for.
    """
    raw = (stage or "").strip()
    low = raw.lower()
    quarter: int | None = None
    m = _QUARTER_RE.search(low)
    if m:
        quarter = _ORDINAL.get(m.group(1)) if m.group(1) else int(m.group(2))
    clock_m = _CLOCK_RE.search(raw)
    clock = clock_m.group(1) if clock_m else None
    past_markers = ("half", "overtime", " ot", "finished", "after", "full time", "ended")
    past_q1 = (quarter is not None and quarter >= 2) or any(
        k in low for k in past_markers
    )
    return {
        "raw": raw,
        "quarter": quarter,
        "is_q1": quarter == 1,
        "past_q1": past_q1,
        "clock": clock,
    }


def parse_score(score: str | None) -> tuple[int | None, int | None]:
    """Parse a ``"home-away"`` score (e.g. ``"17-18"``) into integers.

    Returns ``(None, None)`` when the score is missing or not yet numeric
    (e.g. a just-started match showing ``"-"``).
    """
    if not score:
        return None, None
    m = re.match(r"\s*(\d+)\s*[-:]\s*(\d+)\s*$", score)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def derive_score_state(
    match: dict[str, Any] | None,
    prev: dict[str, Any] | None = None,
    *,
    target: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fold one scrape into the flat state a Data Source serves.

    ``match`` is the selected live match dict (``teams``/``score``/``time``/
    ``status``) or ``None`` when the target is not on the live board yet.
    ``prev`` is the previous derived state; it carries the "was in Q1" memory
    so the final 1st-quarter total can be frozen into ``q1_final`` the moment
    the stage leaves the 1st quarter — the number a 1Q-total bet settles on.

    Sticky fields (``q1_final``/``q1_ended``) are preserved from ``prev`` once
    set, so a Data Source still reports them after the match leaves Q1 (or the
    board). No betting judgement is made here — only arithmetic and staging.
    """
    prev = prev or {}
    ts = (now or datetime.now(UTC)).isoformat()

    # Defaults carry sticky Q1 facts forward even when the match isn't found.
    q1_final = prev.get("q1_final")
    q1_ended = bool(prev.get("q1_ended", False))

    if not match:
        return {
            "found": False,
            "status": "",
            "match": target or prev.get("match"),
            "stage": "",
            "quarter": None,
            "is_q1": False,
            "home": None,
            "away": None,
            "total": None,
            "q1_total": prev.get("q1_total"),
            "q1_final": q1_final,
            "q1_ended": q1_ended,
            "updated_at": ts,
        }

    teams = match.get("teams") or {}
    home_name = teams.get("home") or "?"
    away_name = teams.get("away") or "?"
    home, away = parse_score(match.get("score"))
    total = (home + away) if home is not None and away is not None else None
    parsed = parse_stage(match.get("time"))
    is_q1 = parsed["is_q1"]

    # While in Q1 the running total *is* the Q1 total; remember the last one.
    q1_total = total if is_q1 else prev.get("q1_total")

    # Freeze: we previously saw Q1 and now play has moved past it.
    if not q1_ended and parsed["past_q1"] and prev.get("q1_total") is not None:
        q1_final = prev.get("q1_total")
        q1_ended = True

    return {
        "found": True,
        "status": match.get("status") or "",
        "match": f"{home_name} vs {away_name}",
        "stage": parsed["raw"],
        "quarter": parsed["quarter"],
        "is_q1": is_q1,
        "home": home,
        "away": away,
        "total": total,
        "q1_total": q1_total,
        "q1_final": q1_final,
        "q1_ended": q1_ended,
        "updated_at": ts,
    }
