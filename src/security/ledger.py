"""Per-site block history: cooldowns, circuit breaker, escalation tier.

Persisted to a small JSON file so a cooldown survives the process — a fresh
run must not walk straight back into a site that just challenged or banned
the previous one. The clock is injectable for tests.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from .models import BlockType, BlockVerdict

ENV_DIR = "SCRAPAMOJA_SECURITY_DIR"


def default_dir() -> Path:
    return Path(os.environ.get(ENV_DIR) or Path.home() / ".scrapamoja" / "security")


@dataclass
class SiteState:
    consecutive_blocks: int = 0
    last_type: Optional[str] = None
    last_vendor: Optional[str] = None
    last_block_at: float = 0.0
    cooldown_until: float = 0.0
    attempts: Dict[str, int] = field(default_factory=dict)   # per block type, since last success
    browser_tier: int = 0
    total_blocks: int = 0
    consecutive_failures: int = 0     # timeouts / dropped connections in a row (not blocks)
    window_start: float = 0.0         # request-budget window
    window_count: int = 0


class BlockLedger:
    def __init__(self, path: Optional[Path] = None, clock: Callable[[], float] = time.time):
        self.path = Path(path) if path else default_dir() / "ledger.json"
        self._clock = clock
        self._sites: Dict[str, SiteState] = {}
        self._load()

    # -- persistence ---------------------------------------------------- #
    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text())
            self._sites = {k: SiteState(**v) for k, v in raw.items()}
        except (OSError, ValueError, TypeError):
            self._sites = {}          # missing or corrupt: start clean, never block a scrape

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
            with os.fdopen(fd, "w") as fh:
                json.dump({k: asdict(v) for k, v in self._sites.items()}, fh, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass                      # a read-only home must not break scraping

    # -- queries -------------------------------------------------------- #
    def state(self, site: str) -> SiteState:
        return self._sites.setdefault(site, SiteState())

    def cooldown_left(self, site: str) -> Tuple[float, Optional[BlockType]]:
        st = self._sites.get(site)
        if st is None:
            return 0.0, None
        left = st.cooldown_until - self._clock()
        if left <= 0:
            return 0.0, None
        return left, BlockType(st.last_type) if st.last_type else None

    def attempt(self, site: str, block_type: BlockType) -> int:
        return self.state(site).attempts.get(block_type.value, 0)

    # -- updates -------------------------------------------------------- #
    def record_block(self, site: str, verdict: BlockVerdict) -> int:
        """Log a block; returns the 0-based attempt number it was (for the ladder)."""
        st = self.state(site)
        n = st.attempts.get(verdict.type.value, 0)
        st.attempts[verdict.type.value] = n + 1
        st.consecutive_blocks += 1
        st.total_blocks += 1
        st.last_type, st.last_vendor = verdict.type.value, verdict.vendor
        st.last_block_at = self._clock()
        self._save()
        return n

    def start_cooldown(self, site: str, seconds: float) -> None:
        self.state(site).cooldown_until = self._clock() + seconds
        self._save()

    def set_tier(self, site: str, tier: int) -> None:
        self.state(site).browser_tier = tier
        self._save()

    def record_failure(self, site: str, threshold: int, base_cooldown: float,
                       max_cooldown: float = 6 * 3600.0) -> float:
        """A transport failure (timeout / dropped connection). After ``threshold`` in a row
        the site is rested for ``base_cooldown`` seconds, doubling for each further
        failure streak. Returns the cooldown started (0 if none)."""
        st = self.state(site)
        st.consecutive_failures += 1
        if threshold <= 0 or st.consecutive_failures < threshold:
            return 0.0
        over = st.consecutive_failures - threshold
        seconds = min(max_cooldown, base_cooldown * (2 ** min(over, 10)))
        st.last_type, st.last_block_at = BlockType.UNREACHABLE.value, self._clock()
        st.cooldown_until = self._clock() + seconds
        self._save()
        return seconds

    def charge(self, site: str, budget: int, window: float = 3600.0) -> float:
        """Count one request against an hourly budget; returns the seconds until the window
        resets when the budget is spent (0 = fine). ``budget <= 0`` means unlimited."""
        if budget <= 0:
            return 0.0
        st, now = self.state(site), self._clock()
        if now - st.window_start >= window:
            st.window_start, st.window_count = now, 0
        if st.window_count >= budget:
            return max(1.0, st.window_start + window - now)
        st.window_count += 1
        self._charges = getattr(self, "_charges", 0) + 1
        if self._charges % 25 == 0:      # persist often enough to survive a crash, not on every request
            self._save()
        return 0.0

    def record_success(self, site: str) -> None:
        """A clean response: forget the streak but keep the tier that worked."""
        st = self._sites.get(site)
        if st is not None and st.consecutive_failures:
            st.consecutive_failures = 0
        if st is None or (st.consecutive_blocks == 0 and not st.attempts):
            return
        st.consecutive_blocks = 0
        st.attempts.clear()
        st.cooldown_until = 0.0
        self._save()

    def clear(self, site: str) -> None:
        self._sites.pop(site, None)
        self._save()
