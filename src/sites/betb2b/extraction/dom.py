"""DOM extractor for BetB2B skins — the PRIMARY, drift-proof extraction path.

Per ADR-4, the direct-API feed (``service-api/{Live,Line}Feed/*``) rotates
its auth-header contract (returns 406 without an SW-injected ``x-dt``), so
DOM extraction — reading the odds the SPA already rendered — is the
reliable path. This module drives an already-navigated Playwright ``page``
and returns the same ``Event``/``Market``/``Selection`` models the API
extractor produces.

Selectors target the **1xbet/BetB2B Vue grid** shipped on linebet/melbet/
betwinner/22bet/megapari/888starz/helabet/paripesa — the
``dashboard-champ`` → ``dashboard-champ__game`` → ``dashboard-game-block__team``
hierarchy. Each sport can override the selectors via
:class:`~src.sites.betb2b.sports.base.DOMSelectors`.

The extractor is **strict** by default — it rejects rows that don't yield
exactly two non-empty team names. This avoids the failure mode where broad
``[class*="team"]`` matches pick up score numbers, controls, or duplicate
template strings and synthesize garbage events (the prior bug).

It never raises: on any trouble it returns whatever parsed (possibly an
empty list).
"""

from __future__ import annotations

import logging
import re
from typing import Any, List, Optional

from ..sports.base import DOMSelectors
from .models import Event, EventStatus, Market, MarketType, Selection, Sport

__all__ = ["extract_events_from_page"]

logger = logging.getLogger(__name__)


def _enum_fallback(enum_cls, *names):
    for n in names:
        m = getattr(enum_cls, n, None)
        if m is not None:
            return m
    return list(enum_cls)[-1]


# ---------------------------------------------------------------------------
# Validation — reject garbage team names
# ---------------------------------------------------------------------------
# Team names that are obviously not team names (score fragments, template
# placeholders, score board labels). Used to filter out the prior failure
# mode where the broad selectors picked up score numbers as team names.
_GARBAGE_TEAM_PATTERNS = [
    re.compile(r"^\d+$"),                          # pure number
    re.compile(r"^\d+\s*[:\-]\s*\d+$"),            # score "2 : 1"
    re.compile(r"^\d+\s+\d+\s+\d+$"),              # "0 0 0"
    re.compile(r"^[A-Z\s]{20,}$"),                 # all-caps shouting
    re.compile(r"^0000$"),                          # the placeholder bug
    re.compile(r"^\d{4}$"),                         # 4-digit year/code
]
# Reject team names that are too long (real team names are < 80 chars).
_MAX_TEAM_NAME_LEN = 80
# Reject team names that are too short (1 char is not a team).
_MIN_TEAM_NAME_LEN = 2


def _is_plausible_team_name(name: str) -> bool:
    """Heuristic: is this string plausibly a real team name?"""
    if not name:
        return False
    n = name.strip()
    if not ( _MIN_TEAM_NAME_LEN <= len(n) <= _MAX_TEAM_NAME_LEN):
        return False
    for pat in _GARBAGE_TEAM_PATTERNS:
        if pat.match(n):
            return False
    return True


# ---------------------------------------------------------------------------
# In-page walker — uses sport-specific selectors
# ---------------------------------------------------------------------------
def _build_page_script(selectors: DOMSelectors) -> str:
    """Build the in-page JS walker that returns a list of plain event dicts.

    The script walks the ``dashboard-champ`` containers, reads the
    championship name from the header, then walks the game rows inside each
    championship. For each game row it pulls the team names (trying each
    selector in order), the live score (optional), and the odds cells.
    """
    def _js_str(s: str) -> str:
        """Quote a string for JS embedding, escaping internal double quotes."""
        esc = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{esc}"'

    team_sels = ", ".join(_js_str(s) for s in selectors.team_names)
    score_sels = ", ".join(_js_str(s) for s in selectors.team_scores)
    odds_sels = ", ".join(_js_str(s) for s in selectors.odds)
    time_sels = ", ".join(_js_str(s) for s in selectors.start_time)
    live_pat = selectors.live_class_pattern

    return r"""
    (cfg) => {
      const txt = el => (el && el.textContent ? el.textContent.trim() : "");
      const num = s => { const m = (s||"").replace(',', '.').match(/-?\d+(?:\.\d+)?/); return m ? parseFloat(m[0]) : null; };

      const TEAM_SEL = [%s];
      const SCORE_SEL = [%s];
      const ODDS_SEL = [%s];
      const TIME_SEL = [%s];
      const LIVE_PAT = %r;
      const CHAMP = %r;
      const CHAMP_NAME = %r;
      const GAME = %r;

      const queryFirst = (root, sels) => {
        for (const s of sels) {
          try {
            const els = root.querySelectorAll(s);
            if (els.length > 0) return [...els];
          } catch(e) { /* ignore */ }
        }
        return [];
      };

      // Walk championship containers.
      const champs = document.querySelectorAll(CHAMP);
      const out = [];
      champs.forEach(champ => {
        // Championship name (league / competition title).
        let comp = "";
        const nameEl = champ.querySelector(CHAMP_NAME);
        if (nameEl) comp = txt(nameEl).split('\n')[0];

        // Game rows inside this championship.
        const games = champ.querySelectorAll(GAME);
        games.forEach(row => {
          // Team names — expect exactly 2.
          const teamEls = queryFirst(row, TEAM_SEL);
          // Filter to non-empty
          const teams = teamEls.map(txt).filter(Boolean);
          if (teams.length < 2) return;

          // Odds cells.
          const oddEls = queryFirst(row, ODDS_SEL);
          const odds = [];
          oddEls.forEach(b => {
            const label = (b.getAttribute('data-name') || b.getAttribute('title') || b.getAttribute('aria-label') || "").trim();
            const price = num(txt(b));
            if (price && price >= 1.0) {
              odds.push({
                label,
                price,
                suspended: /lock|suspend|disabled|blocked|is-disabled/i.test((b.className||"") + " " + txt(b)),
              });
            }
          });

          // Fallback: if the CSS odds selectors matched nothing (the Vue grid's
          // coefficient classes drift often), collect any leaf descendant whose
          // text is a plausible coefficient (1.01..999). Class-name-independent.
          if (odds.length === 0) {
            row.querySelectorAll('*').forEach(el => {
              if (el.childElementCount !== 0) return;
              const t = txt(el);
              if (/^\d{1,3}\.\d{1,3}$/.test(t)) {
                const v = parseFloat(t);
                if (v >= 1.01 && v <= 999) {
                  const cl = (el.className && el.className.baseVal !== undefined) ? el.className.baseVal : (el.className || "");
                  odds.push({ label: "", price: v, suspended: /lock|suspend|disabled|blocked|is-disabled/i.test('' + cl) });
                }
              }
            });
          }

          // Scores (live).
          const scoreEls = queryFirst(row, SCORE_SEL);
          const scoreTxt = scoreEls.map(txt).filter(Boolean).join(' ');

          // Start time.
          const timeEls = queryFirst(row, TIME_SEL);
          const timeTxt = timeEls.map(txt).filter(Boolean).join(' ');

          // Live flag — check row class for the LIVE_PAT token.
          const live = LIVE_PAT ? new RegExp(LIVE_PAT, 'i').test(row.className || "") : false;

          out.push({
            home: teams[0],
            away: teams[1],
            comp: comp,
            scoreTxt: scoreTxt,
            timeTxt: timeTxt,
            odds: odds,
            live: live,
          });
        });
      });
      return out;
    }
    """ % (team_sels, score_sels, odds_sels, time_sels, live_pat,
           selectors.championship, selectors.championship_name, selectors.game)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_1X2_LABELS = {0: "1", 1: "X", 2: "2"}
_H2H_LABELS = {0: "1", 1: "2"}


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
    dom_selectors: Optional[DOMSelectors] = None,
    has_draw: bool = True,
) -> List[Event]:
    """Extract ``Event`` objects from an already-loaded live/line grid page.

    Args:
        page: a Playwright Page already navigated to ``/en/live`` or
            ``/en/line/<sport>`` and given time to render.
        is_live: True for the live feed page, False for prematch.
        source_url: the URL the page was navigated to (recorded on each Event).
        sport: the :class:`Sport` enum value to tag events with. Defaults to
            ``Sport.OTHER``.
        dom_selectors: a :class:`DOMSelectors` bundle. Defaults to the
            1xbet/BetB2B grid selectors shipped with :mod:`.base`.
        has_draw: if False (e.g. basketball, tennis, esports), the odds
            labels default to "1"/"2" (h2h); otherwise "1"/"X"/"2" (1x2).

    Best-effort and non-raising.
    """
    selectors = dom_selectors or DOMSelectors()

    try:
        raw = await page.evaluate(_build_page_script(selectors))
    except Exception as exc:  # noqa: BLE001
        logger.warning("DOM evaluate failed on %s: %s", source_url, exc)
        return []

    default_sport = sport or _enum_fallback(Sport, "OTHER", "UNKNOWN")
    other_market = _enum_fallback(MarketType, "OTHER", "UNKNOWN", "MATCH_ODDS")
    st_live = _enum_fallback(EventStatus, "LIVE", "IN_PLAY", "NOT_STARTED")
    st_pre = _enum_fallback(EventStatus, "NOT_STARTED", "SCHEDULED", "PREMATCH")

    label_map = _1X2_LABELS if has_draw else _H2H_LABELS

    events: List[Event] = []
    seen_ids: set[str] = set()

    for i, r in enumerate(raw or []):
        try:
            home = (r.get("home") or "").strip()
            away = (r.get("away") or "").strip()

            # Strict validation: reject garbage team names.
            if not _is_plausible_team_name(home) or not _is_plausible_team_name(away):
                continue
            if home == away:
                continue  # template duplication bug guard

            sh, sa = _score_pair(r.get("scoreTxt", ""))
            live = bool(r.get("live") or is_live)

            selections: List[Selection] = []
            for j, o in enumerate(r.get("odds") or []):
                price = o.get("price")
                if not price:
                    continue
                selections.append(
                    Selection(
                        name=(o.get("label") or label_map.get(j, str(j + 1))),
                        price=float(price),
                        is_suspended=bool(o.get("suspended")),
                    )
                )

            markets: List[Market] = []
            if selections:
                market_name = "To Win Match" if not has_draw else "1x2"
                mt = _enum_fallback(
                    MarketType,
                    "MONEYLINE_H2H" if not has_draw else "MONEYLINE_12",
                    "OTHER",
                )
                markets.append(
                    Market(
                        name=market_name,
                        market_type=mt,
                        selections=selections,
                        is_live=live,
                    )
                )

            # Build a stable event id from team names (not the row index,
            # which would shift between renders).
            eid = f"dom-{home}-{away}"[:120]
            if eid in seen_ids:
                continue
            seen_ids.add(eid)

            events.append(
                Event(
                    event_id=eid,
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
        except Exception:  # noqa: BLE001
            continue

    logger.info(
        "DOM extract: %d valid events from %s (raw_rows=%d, rejected=%d)",
        len(events), source_url, len(raw or []),
        len(raw or []) - len(events),
    )
    return events
