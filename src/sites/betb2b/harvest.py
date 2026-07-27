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

__all__ = ["extract_event_ids", "extract_champ_ids"]

# A 9–10 digit id that is the head of a match-link segment: ``<id>-<slug>``
# (e.g. ``/354744562-england-3x3-women``). Requiring the trailing ``-<slug>``
# is what separates real event links from bare 9–10 digit runs that also appear
# in the HTML — asset hashes and third-party-file names (e.g.
# ``.../…c251436156/Aviator.png``, ``third-party-files/140599367…``) — which
# otherwise each cost a wasted, rate-limited ``GetGameZip`` returning
# "Game is not found". League/country ids in the hierarchy are ≤7 digits.
_EVENT_ID_RE = re.compile(r"(?<!\d)(\d{9,10})(?=-[a-z0-9])", re.IGNORECASE)

# A league/championship link: ``/en/(line|live)/<sport>/<champId>-<slug>``.
# Champ ids are 4–7 digits (distinct from the 9–10 digit event ids). Feeding
# each champ id to the un-gated ``GetChampZip`` yields that league's full,
# accurate game list — broader + cleaner than scraping the landing page alone,
# since the aggregate list feeds are SW-gated (406, ADR-4).
_CHAMP_LINK_RE = re.compile(
    r"/en/(?:line|live)/[a-z0-9\-]+/(\d{4,7})-[a-z0-9\-]+", re.IGNORECASE
)


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


def extract_champ_ids(html: str, *, limit: int = 0) -> List[str]:
    """Return distinct league/championship ids from page HTML, first-seen order.

    These come from the ``/en/(line|live)/<sport>/<champId>-<slug>`` links the
    sport landing page server-renders (the "top" leagues, geo-curated to the
    egress country). Each id is meant for ``GetChampZip?champ=<id>``.
    """
    seen: dict[str, None] = {}
    for m in _CHAMP_LINK_RE.finditer(html or ""):
        seen.setdefault(m.group(1), None)
    ids = list(seen)
    return ids[:limit] if limit and limit > 0 else ids
