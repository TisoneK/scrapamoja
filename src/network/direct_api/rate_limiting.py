"""Rate limiting components for per-domain HTTP request throttling.

This module provides token bucket rate limiting for controlling
request rates to individual domains.
"""

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """Token bucket rate limiter for per-domain rate limiting.

    Implements a simple token bucket algorithm for rate limiting
    requests to individual domains.

    Attributes:
        rate: Number of tokens added per second (default: 10)
        capacity: Maximum number of tokens in the bucket (default: 10)
    """

    rate: float = 10.0  # requests per second
    capacity: float = 10.0  # maximum tokens
    tokens: float = field(default=10.0)
    last_update: float = field(default_factory=time.monotonic)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


@dataclass
class RateLimiter:
    """Per-domain rate limiter using token bucket.

    Supports configurable rate and capacity per domain.
    """

    _buckets: dict[str, TokenBucket] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    default_rate: float = 10.0
    default_capacity: float = 10.0

    def __init__(self, rate: float = 10.0, capacity: float = 10.0) -> None:
        """Initialize rate limiter with custom defaults.

        Args:
            rate: Default number of requests per second per domain
            capacity: Default maximum tokens per domain
        """
        self._buckets = {}
        self._lock = asyncio.Lock()
        self.default_rate = rate
        self.default_capacity = capacity

    async def acquire(self, domain: str) -> None:
        """Acquire rate limit token for the given domain."""
        async with self._lock:
            if domain not in self._buckets:
                self._buckets[domain] = TokenBucket(
                    rate=self.default_rate,
                    capacity=self.default_capacity
                )
            bucket = self._buckets[domain]

        await bucket.acquire()
