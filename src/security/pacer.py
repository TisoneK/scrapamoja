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
from typing import Callable


class Pacer:
    def __init__(self, rate_per_second: float, clock: Callable[[], float] = time.monotonic):
        self.interval = 1.0 / rate_per_second if rate_per_second and rate_per_second > 0 else 0.0
        self._clock = clock
        self._next = 0.0

    async def wait(self) -> None:
        """Return when this caller's start slot arrives (immediately if pacing is off)."""
        if self.interval <= 0:
            return
        now = self._clock()
        # No await between reading and updating _next, so concurrent tasks (one event
        # loop) each get their own distinct slot.
        slot = max(self._next, now)
        self._next = slot + self.interval
        delay = slot - now
        if delay > 0:
            await asyncio.sleep(delay)
