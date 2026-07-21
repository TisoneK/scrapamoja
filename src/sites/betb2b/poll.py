"""Interval poller — scrape + persist on a loop so line-movement accumulates.

The odds store only pays off when something polls it over time: dedup
(``store.persist_result``) records movement, not heartbeats, so a poller can
run as fast as scrapes complete and the DB only grows when the market moves.

:func:`poll_loop` is the pure control loop (injectable clock/sleep, no I/O of
its own) so it is unit-testable without a browser or a database. The CLI
(`betb2b poll`) wires the real scraper + ``persist_result`` into it.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Optional

__all__ = ["poll_loop"]


async def poll_loop(
    *,
    scrape_once: Callable[[], Awaitable[Any]],
    persist: Callable[[Any], Any],
    interval: float,
    cycles: int = 0,
    max_seconds: float = 0.0,
    on_cycle: Optional[Callable[[int, Any, Any], None]] = None,
    on_error: Optional[Callable[[int, Exception], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> int:
    """Scrape + persist repeatedly; return the number of cycles completed.

    One cycle = ``scrape_once()`` → ``persist(result)`` → ``on_cycle``. The next
    cycle starts ``interval`` seconds after this one *started* (never negative;
    if a scrape overruns the interval, the next starts immediately). A failed
    scrape/persist is reported via ``on_error`` and does NOT stop the loop.

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
