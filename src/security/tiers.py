"""Browser tiers: progressively more browser-like ways to open a page.

Tier 0 is the cheap default. Tiers above it are only used after a block, and
only the ones this machine can actually run (a headed browser needs a display).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class BrowserTier:
    name: str
    headless: bool
    channel: Optional[str]      # None = bundled Chromium; "chrome" = installed Google Chrome
    apply_stealth: bool         # run the framework's masking init-script


ALL_TIERS = (
    BrowserTier("headless-chromium", headless=True, channel=None, apply_stealth=False),
    BrowserTier("chrome-headless", headless=True, channel="chrome", apply_stealth=True),
    BrowserTier("chrome-headed", headless=False, channel="chrome", apply_stealth=True),
)


def has_display() -> bool:
    if sys.platform in ("darwin", "win32"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def available_tiers() -> List[BrowserTier]:
    return [t for t in ALL_TIERS if t.headless or has_display()]


def tier_at(index: int) -> BrowserTier:
    tiers = available_tiers()
    return tiers[max(0, min(index, len(tiers) - 1))]


def max_tier() -> int:
    return len(available_tiers()) - 1
