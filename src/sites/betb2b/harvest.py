"""Browser-free event-id harvest from the sportsbook page HTML.

The rendered DOM virtualizes the game grid — it materializes only ~one
screenful of rows (Session 25: 16 championships on the live-basketball page but
only 10 rendered), so DOM extraction structurally under-captures. The **raw**
HTML, however, carries the match links for the *whole* card (42 event ids in
the same capture) and is reachable with a plain ``httpx`` GET — no browser, no
virtualization.

So the drift-proof discovery path is: ``httpx`` GET the sport page → pull the
event ids out of the HTML → ``GetGameZip?id=`` each (the per-match endpoint,
which returns 200; the list feeds are 406 per ADR-4). This module does the
pure ID extraction; the scraper does the fetch + GetGameZip.

Event ids on this platform are 9–10 digit numbers that appear as the deepest
``/<digits>-<slug>`` segment of a match link (league/country segments are ≤7
digits). We over-collect slightly and let ``GetGameZip`` (``Success:false`` for
a non-event id) be the final filter.
"""

from __future__ import annotations

import re
from typing import List

__all__ = ["extract_event_ids"]

# A 9+ digit run not glued to more digits — the event-id shape. League/country
# ids in the URL hierarchy are ≤7 digits, so this cleanly discriminates them.
_EVENT_ID_RE = re.compile(r"(?<!\d)(\d{9,10})(?!\d)")


def extract_event_ids(html: str, *, limit: int = 0) -> List[str]:
    """Return distinct event ids from page HTML, in first-seen order.

    Args:
        html: the raw page HTML (from an httpx GET, not a rendered DOM).
        limit: cap the number returned (0 = no cap).
    """
    seen: dict[str, None] = {}
    for m in _EVENT_ID_RE.finditer(html or ""):
        seen.setdefault(m.group(1), None)
    ids = list(seen)
    return ids[:limit] if limit and limit > 0 else ids
