"""One fixed vocabulary for what a stored line or score belongs to.

Every totals line carries a ``subject`` (whose points) and a ``period`` (which
stretch of the game). The source names these inconsistently (``Total``,
``Individual Total Home``, ``1 Half``, ``2nd quarter``); this module maps them
once, so a consumer never reads a label off a market name or a list position.

Pure functions — no I/O.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

__all__ = [
    "SUBJECTS", "SCOPE_PERIOD", "period_structure", "scope_from_period_name",
    "stat_scope", "classify", "build_totals_coverage", "COVERAGE_STATUSES",
]

MATCH, HOME_TEAM, AWAY_TEAM = "MATCH", "HOME_TEAM", "AWAY_TEAM"
SUBJECTS = (MATCH, HOME_TEAM, AWAY_TEAM)

# Source market name → subject. Only the plain over/under totals ladders.
_TOTAL_SUBJECT = {
    "Total": MATCH,
    "Individual Total Home": HOME_TEAM,
    "Individual Total Away": AWAY_TEAM,
}

# Internal scope (what the store has always called it) → period vocabulary.
SCOPE_PERIOD: Dict[str, str] = {
    "FULL_MATCH": "FULL_TIME",
    "FIRST_HALF": "HALF_1", "SECOND_HALF": "HALF_2",
    "QUARTER_1": "QUARTER_1", "QUARTER_2": "QUARTER_2",
    "QUARTER_3": "QUARTER_3", "QUARTER_4": "QUARTER_4",
    "PERIOD_1": "PERIOD_1", "PERIOD_2": "PERIOD_2", "PERIOD_3": "PERIOD_3",
}
_PERIOD_SCOPE = {v: k for k, v in SCOPE_PERIOD.items()}

# Source sub-game period name (``SG[].PN``) → scope.
_SUBGAME_SCOPES: Dict[str, str] = {
    "1st quarter": "QUARTER_1", "2nd quarter": "QUARTER_2",
    "3rd quarter": "QUARTER_3", "4th quarter": "QUARTER_4",
    "1 half": "FIRST_HALF", "1st half": "FIRST_HALF",
    "2 half": "SECOND_HALF", "2nd half": "SECOND_HALF",
    "1st period": "PERIOD_1", "2nd period": "PERIOD_2", "3rd period": "PERIOD_3",
}

# Which periods a sport has. Sports not listed only have FULL_TIME.
_BASKETBALL = ("FULL_TIME", "HALF_1", "HALF_2", "QUARTER_1", "QUARTER_2", "QUARTER_3", "QUARTER_4")
_STRUCTURE: Dict[str, Tuple[str, ...]] = {
    "basketball": _BASKETBALL,
    "football": ("FULL_TIME", "HALF_1", "HALF_2"),
    "ice hockey": ("FULL_TIME", "PERIOD_1", "PERIOD_2", "PERIOD_3"),
    "ice-hockey": ("FULL_TIME", "PERIOD_1", "PERIOD_2", "PERIOD_3"),
    "hockey": ("FULL_TIME", "PERIOD_1", "PERIOD_2", "PERIOD_3"),
}

COVERAGE_STATUSES = ("offered", "not_offered", "not_attempted", "fetch_failed")


def period_structure(sport: Any) -> Tuple[str, ...]:
    """Periods a sport's totals can exist for, in a fixed order."""
    key = str(getattr(sport, "value", sport) or "").strip().lower()
    return _STRUCTURE.get(key, ("FULL_TIME",))


def scope_from_period_name(pn: Any) -> Optional[str]:
    """Source sub-game period name → scope, or None when it is not a period."""
    return _SUBGAME_SCOPES.get(str(pn or "").strip().lower())


def stat_scope(name: Any) -> Optional[str]:
    """Scope for a named per-stat sub-game (``Rebounds`` → ``STAT_REBOUNDS``)."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", str(name or "")).strip("_").upper()
    return f"STAT_{slug}" if slug else None


def classify(market_name: Any, scope: Any) -> Tuple[Optional[str], str]:
    """``(subject, period)`` for a market in a scope.

    ``subject`` is set only for the three totals ladders and never for a
    per-stat sub-game (its ``Total`` counts rebounds, not points). ``period``
    always comes from the scope; stat scopes are ``FULL_TIME``.
    """
    scope = str(scope or "FULL_MATCH")
    period = SCOPE_PERIOD.get(scope, "FULL_TIME")
    if scope.startswith("STAT_"):
        return None, period
    return _TOTAL_SUBJECT.get(str(market_name or "")), period


def _has_lines(market: Dict[str, Any]) -> bool:
    return any(s.get("line") is not None and s.get("price") is not None
               for s in market.get("selections") or [])


def build_totals_coverage(
    sport: Any, markets: Iterable[Dict[str, Any]], *,
    subgames_enabled: bool, listed_scopes: Iterable[str],
    fetch_status: Dict[str, str],
) -> List[Dict[str, Any]]:
    """One row per subject x period: was the line offered, absent, or not looked at.

    - ``offered``: a totals ladder with lines is stored for it.
    - ``not_offered``: we asked the source and it has none (the period is not
      in the event's sub-game list, or the sub-game answered without it).
    - ``fetch_failed``: the sub-game is listed but fetching it failed.
    - ``not_attempted``: we did not ask (sub-games off, or no market data at all).

    ``markets`` are market dicts (``Market.to_dict()``); ``fetch_status`` maps
    scope → ``fetched`` | ``failed`` for the sub-games we tried.
    """
    markets = list(markets)
    listed = set(listed_scopes)
    main_fetched = any(m.get("scope", "FULL_MATCH") == "FULL_MATCH" for m in markets)
    offered = set()
    for m in markets:
        subject, period = classify(m.get("name"), m.get("scope"))
        if subject and _has_lines(m):
            offered.add((subject, period))
    rows: List[Dict[str, Any]] = []
    for period in period_structure(sport):
        for subject in SUBJECTS:
            if (subject, period) in offered:
                status = "offered"
            elif not main_fetched:
                status = "not_attempted"
            elif period == "FULL_TIME":
                status = "not_offered"
            else:
                scope = _PERIOD_SCOPE.get(period, "")
                if not subgames_enabled:
                    status = "not_attempted"
                elif scope in listed:
                    status = "fetch_failed" if fetch_status.get(scope) != "fetched" else "not_offered"
                else:
                    status = "not_offered"
            rows.append({"dataset": "totals", "subject": subject, "period": period, "status": status})
    return rows
