"""Request pacing: a minimum spacing between request STARTS, shared by every caller.

Limiting how many requests are in flight is not the same as limiting how fast they
are sent — four workers on a site that answers in 200 ms still send ~20 requests a
second, which anti-scraping systems read as a burst and answer by dropping the
address for a while. A :class:`Pacer` hands out start slots ``1 / rate`` seconds
apart no matter how many tasks are waiting.
"""

from __future__ import annotations

import asyncio
import time
from typing import Callable, Optional


class Pacer:
    def __init__(self, rate_per_second: float, clock: Callable[[], float] = time.monotonic):
        self.interval = 1.0 / rate_per_second if rate_per_second and rate_per_second > 0 else 0.0
        self._clock = clock
        self._last_start: Optional[float] = None
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        """Return when this caller's start slot arrives (immediately if pacing is off)."""
        if self.interval <= 0:
            return
        # One caller at a time, each spaced from the previous caller's ACTUAL start.
        # A pre-computed schedule (slot = max(next, now)) collapses where the event
        # loop's timer is coarse — Windows rounds to ~15.6 ms, so two slots 20 ms
        # apart can wake in the same tick and go out together. Sleeping while
        # holding the lock keeps the spacing true at any timer resolution.
        async with self._lock:
            now = self._clock()
            if self._last_start is not None:
                delay = self._last_start + self.interval - now
                if delay > 0:
                    await asyncio.sleep(delay)
                    now = self._clock()
            self._last_start = now
