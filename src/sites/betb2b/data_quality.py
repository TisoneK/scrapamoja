"""Data-quality rules applied when scraped facts are stored.

Pure functions, no I/O. They back the fixes for the engine's audit of the
store (``scorewise-engine/repos/engine/engine/SCRAPER_DATA_ISSUES.md``):

* every ``h2h_games`` row is tagged ``kind`` — a real meeting of the event's two
  teams (``h2h``), a game of one of them against someone else
  (``team1_form`` / ``team2_form``), or one that touches neither under any
  known id (``unmapped``);
* a game listed twice in one response is stored once;
* placeholder scores (0-0, the 20-0 / 0-20 forfeit token) are not stored as
  results — the scores become NULL and ``result_flag`` says why;
* incomplete per-period rows are not stored.

Placeholder rules are basketball-only: 0-0 is a real football or hockey score.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

BASKETBALL = 3

KIND_H2H = "h2h"
KIND_TEAM1_FORM = "team1_form"
KIND_TEAM2_FORM = "team2_form"
KIND_UNMAPPED = "unmapped"

FLAG_NO_SCORE = "no_score"      # 0-0: nothing was captured / the game was not played
FLAG_FORFEIT = "forfeit"        # 20-0 / 0-20: the token score for a forfeit or walkover

# ``events.result_status`` for a finished match whose score is a placeholder
# (so it is neither "finished with a real result" (3) nor "never resolved" (-1)).
RESULT_STATUS_VOID = -2

_FORFEIT_SCORES = {(20, 0), (0, 20)}


def _int(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None and str(v) != "" else None
    except (TypeError, ValueError):
        return None


def placeholder_flag(sport_id: Any, score1: Any, score2: Any) -> Optional[str]:
    """``FLAG_NO_SCORE`` / ``FLAG_FORFEIT`` when the pair is a basketball placeholder."""
    if _int(sport_id) != BASKETBALL:
        return None
    s1, s2 = _int(score1), _int(score2)
    if s1 is None or s2 is None:
        return None
    if (s1, s2) == (0, 0):
        return FLAG_NO_SCORE
    if (s1, s2) in _FORFEIT_SCORES:
        return FLAG_FORFEIT
    return None


def norm_name(name: Any) -> str:
    return " ".join(str(name or "").casefold().split())


def event_team_ids(h2h: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Backend ids of the event's two teams: the first two entries of the H2H ``teams``."""
    ids = [str(t.get("id")) if t.get("id") else None for t in (h2h.get("teams") or [])[:2]]
    ids += [None] * (2 - len(ids))
    return ids[0], ids[1]


def match_event_teams(h2h: Mapping[str, Any], home: Any, away: Any) -> Tuple[Optional[str], Optional[str]]:
    """``(home_backend_id, away_backend_id)`` for the event's teams, from the H2H team list.

    Matched by name first. When exactly one side matches by name the other side is
    the remaining H2H team (there are only two). Never guessed by position alone —
    a feed that lists the teams in the other order would swap the ids."""
    teams = [t for t in (h2h.get("teams") or [])[:2] if t.get("id")]
    if len(teams) != 2:
        return None, None
    by_name = {norm_name(t.get("title")): str(t["id"]) for t in teams}
    h, a = by_name.get(norm_name(home)), by_name.get(norm_name(away))
    ids = [str(t["id"]) for t in teams]
    if h and a and h != a:
        return h, a
    if h and not a:
        rest = [i for i in ids if i != h]
        return h, rest[0] if len(rest) == 1 else None
    if a and not h:
        rest = [i for i in ids if i != a]
        return (rest[0] if len(rest) == 1 else None), a
    return None, None


def h2h_kind(team1_id: Any, team2_id: Any, event_a: Optional[str], event_b: Optional[str],
             aliases: Optional[Mapping[str, str]] = None) -> str:
    """Classify an H2H-list game against the event's two teams (``event_a`` / ``event_b``).

    ``aliases`` maps a second backend id of a team to its canonical one."""
    al = aliases or {}
    t1 = al.get(str(team1_id), str(team1_id))
    t2 = al.get(str(team2_id), str(team2_id))
    if event_a is None or event_b is None:
        return KIND_UNMAPPED
    ids = {t1, t2}
    if event_a in ids and event_b in ids:
        return KIND_H2H
    if event_a in ids:
        return KIND_TEAM1_FORM
    if event_b in ids:
        return KIND_TEAM2_FORM
    return KIND_UNMAPPED


def clean_periods(periods: Iterable[Mapping[str, Any]], sport_id: Any) -> List[Dict[str, Any]]:
    """Per-period rows worth storing, or ``[]`` if the set is unusable.

    A basketball game whose periods include a 0-0 or a missing-score row is stored
    without any period rows: a placeholder period would be scored as a real
    0-point quarter. A game the source gives no (or fewer) period rows for is left
    as it is — the engine skips it for period scopes."""
    rows = [dict(p) for p in periods or []]
    if _int(sport_id) != BASKETBALL or not rows:
        return rows
    for p in rows:
        h, a = _int(p.get("home_score")), _int(p.get("away_score"))
        if h is None or a is None or (h, a) == (0, 0):
            return []
    return rows


def prepare_h2h_games(h2h: Mapping[str, Any], *, sport_id: Any = None,
                      aliases: Optional[Mapping[str, str]] = None) -> List[Dict[str, Any]]:
    """The H2H response's games, ready to store: deduplicated, classified, cleaned.

    Each returned dict is the source game plus ``kind``, ``result_flag`` and
    cleaned ``periods``; a placeholder game keeps its row (the engine can see the
    fixture exists) with NULL scores."""
    sport = _int(h2h.get("sport_id")) or _int(sport_id)
    a, b = event_team_ids(h2h)
    if aliases:
        a = aliases.get(a, a) if a else a
        b = aliases.get(b, b) if b else b
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for g in h2h.get("game_shorts") or []:
        flag = placeholder_flag(sport, g.get("score1"), g.get("score2"))
        row = dict(g)
        if flag:
            row.update(score1=None, score2=None, sub_score1=None, sub_score2=None, winner=None)
        # Natural identity: the same game under two game ids (or listed twice) is one game.
        natural = (str(g.get("date_start")), frozenset((str(g.get("team1_id")), str(g.get("team2_id")))),
                   row.get("score1"), row.get("score2"))
        ident = (str(g.get("game_id")), row.get("status"), row.get("score1"), row.get("score2"))
        dated = g.get("date_start") is not None
        if (dated and natural in seen) or ident in seen:
            continue
        if dated:
            seen.add(natural)
        seen.add(ident)
        row["kind"] = h2h_kind(g.get("team1_id"), g.get("team2_id"), a, b, aliases)
        row["result_flag"] = flag
        row["periods"] = [] if flag else clean_periods(g.get("periods") or [], sport)
        out.append(row)
    return out


def removed_selections(last_odds: Mapping[tuple, tuple], seen_scopes: Iterable[str],
                       current_keys: Iterable[tuple]) -> List[tuple]:
    """Stored selections the latest fetch no longer offers.

    ``last_odds`` is ``{(scope, market_id, selection, line): (price, is_suspended)}``.
    A selection counts as removed only when its scope came back with markets this
    time (a scope that failed to fetch says nothing) and it is not among
    ``current_keys`` and was not already suspended. Returned as ``(key, price)``;
    the caller stores each as a suspended row, which is how a withdrawn line
    reaches a consumer reading the latest price per line."""
    scopes, current = set(seen_scopes), set(current_keys)
    return [(k, v[0]) for k, v in last_odds.items()
            if k[0] in scopes and k not in current and not v[1]]
