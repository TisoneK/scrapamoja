"""DOM extractor for BetB2B skins — the PRIMARY, drift-proof extraction path.

Per ADR-4, the direct-API feed (`service-api/{Live,Line}Feed/*`) rotates its
auth-header contract (returns 406 without an SW-injected `x-dt`), so DOM
extraction — reading the odds the SPA already rendered — is the reliable path.
This module drives an already-navigated Playwright ``page`` and returns the same
``Event``/``Market``/``Selection`` models the API extractor produces.

Selectors are intentionally broad (class-name *contains* matches) so minor CSS
churn on the 1xbet/BetB2B grid doesn't break extraction. It never raises: on any
trouble it returns whatever parsed (possibly an empty list).

NOTE: shipped without live testing (token-constrained session). Verify against a
real `/en/live` + `/en/line/<sport>` page through the Kenya proxy before relying
on it, and tune the selectors in ``_PAGE_SCRIPT`` if the grid markup differs.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional

from .models import Event, EventStatus, Market, MarketType, Selection, Sport

__all__ = ["extract_events_from_page"]


def _enum_fallback(enum_cls, *names):
    for n in names:
        m = getattr(enum_cls, n, None)
        if m is not None:
            return m
    return list(enum_cls)[-1]


# In-page walker: returns a list of plain dicts (teams, score, competition, odds).
# Broad matches so it survives class-name drift across skins/versions.
_PAGE_SCRIPT = r"""
() => {
  const txt = el => (el && el.textContent ? el.textContent.trim() : "");
  const num = s => { const m = (s||"").replace(',', '.').match(/-?\d+(?:\.\d+)?/); return m ? parseFloat(m[0]) : null; };
  const rows = new Set();
  // event rows: 1xbet/BetB2B grids use c-events__item / dashboard-game / *event*item*
  document.querySelectorAll('[class*="c-events__item"],[class*="dashboard-game"],[class*="event"][class*="item"]').forEach(r => rows.add(r));
  const out = [];
  rows.forEach(row => {
    // team names
    const nameEls = row.querySelectorAll('[class*="team"],[class*="name__"],[class*="__name"],[class*="opponent"]');
    const names = [...nameEls].map(txt).filter(Boolean);
    if (names.length < 2) return;
    const home = names[0], away = names[1];
    // competition: nearest preceding champ/league header
    let comp = "";
    let p = row;
    for (let i = 0; i < 6 && p; i++) {
      p = p.previousElementSibling || (p.parentElement ? p.parentElement.previousElementSibling : null);
      if (p && /champ|league|title|caption|head/i.test(p.className || "")) { comp = txt(p).split('\n')[0]; break; }
    }
    // scores (live)
    const scoreEls = row.querySelectorAll('[class*="score"] [class*="value"],[class*="score__"],[class*="c-events-scoreboard"]');
    const scoreTxt = [...scoreEls].map(txt).filter(Boolean).join(' ');
    // odds buttons: coefficient cells
    const betEls = row.querySelectorAll('[class*="bet"] [class*="coef"],[class*="__coef"],[class*="c-bets__bet"],[class*="value--coef"],button[class*="bet"]');
    const odds = [];
    betEls.forEach(b => {
      const label = (b.getAttribute('data-name') || b.getAttribute('title') || b.getAttribute('aria-label') || "").trim();
      const price = num(txt(b));
      if (price && price >= 1.0) odds.push({ label, price, suspended: /lock|suspend|disabled|blocked/i.test((b.className||"") + " " + txt(b)) });
    });
    const live = /c-events__item--live|live/i.test(row.className || "");
    out.push({ home, away, comp, scoreTxt, odds, live });
  });
  return out;
}
"""

_1X2_LABELS = {0: "1", 1: "X", 2: "2"}


def _score_pair(s: str):
    m = re.search(r"(\d+)\s*[:\-]\s*(\d+)", s or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


async def extract_events_from_page(
    page: Any,
    *,
    is_live: bool,
    source_url: str = "",
    sport: Optional[Sport] = None,
) -> List[Event]:
    """Extract ``Event`` objects from an already-loaded live/line grid page.

    ``page`` is a Playwright Page already navigated to ``/en/live`` or
    ``/en/line/<sport>`` and given time to render. Best-effort and non-raising.
    """
    try:
        raw = await page.evaluate(_PAGE_SCRIPT)
    except Exception:
        return []

    default_sport = sport or _enum_fallback(Sport, "OTHER", "UNKNOWN")
    other_market = _enum_fallback(MarketType, "OTHER", "UNKNOWN", "MATCH_ODDS")
    st_live = _enum_fallback(EventStatus, "LIVE", "IN_PLAY", "NOT_STARTED")
    st_pre = _enum_fallback(EventStatus, "NOT_STARTED", "SCHEDULED", "PREMATCH")
    events: List[Event] = []

    for i, r in enumerate(raw or []):
        try:
            home = (r.get("home") or "").strip()
            away = (r.get("away") or "").strip()
            if not home or not away:
                continue
            sh, sa = _score_pair(r.get("scoreTxt", ""))
            live = bool(r.get("live") or is_live)

            selections: List[Selection] = []
            for j, o in enumerate(r.get("odds") or []):
                price = o.get("price")
                if not price:
                    continue
                selections.append(
                    Selection(
                        name=(o.get("label") or _1X2_LABELS.get(j, str(j + 1))),
                        price=float(price),
                        is_suspended=bool(o.get("suspended")),
                    )
                )

            markets: List[Market] = []
            if selections:
                markets.append(
                    Market(
                        name="Main",
                        market_type=other_market,
                        selections=selections,
                        is_live=live,
                    )
                )

            events.append(
                Event(
                    event_id=f"dom-{i}-{home}-{away}"[:120],
                    sport=default_sport,
                    competition=(r.get("comp") or "").strip(),
                    home=home,
                    away=away,
                    status=st_live if live else st_pre,
                    score_home=sh,
                    score_away=sa,
                    is_live=live,
                    markets=markets,
                    source_url=source_url,
                    raw_endpoint="dom",
                )
            )
        except Exception:
            continue

    return events
