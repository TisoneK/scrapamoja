"""Map betb2b events → scorewise-engine ingest requests (ADR-7).

One betb2b ``Event`` (dict from ``Event.to_dict()``) becomes up to 9
``PredictRequest``s — one per :class:`PredictionScope` the data supports:
FULL_MATCH, FIRST/SECOND_HALF, QUARTER_1..4, HOME/AWAY_TEAM_TOTAL. Each carries
that scope's totals line (Over-odds nearest 1.85 — the engine's calculation
line) and H2H scores that MATCH the scope.

Pure functions — no I/O. The ingest HTTP client is separate. Repos stay
isolated: this module only knows the engine's JSON contract.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

__all__ = ["event_to_predict_requests", "build_ingest_matches", "post_ingest"]

# period_key (1xbet ``periods[].period_key``) → quarter index, per Session-21
# _PERIOD_TYPE_NAMES (18=1st quarter … 21=4th quarter).
_QKEY = {18: 1, 19: 2, 20: 3, 21: 4}

# Scopes whose H2H/odds we can build, and how to combine quarter scores.
_QUARTER_SCOPES = {"QUARTER_1": (1,), "QUARTER_2": (2,), "QUARTER_3": (3,), "QUARTER_4": (4,),
                   "FIRST_HALF": (1, 2), "SECOND_HALF": (3, 4)}


def _nearest_185_total(markets: List[Dict[str, Any]], scope: str,
                       market_name: str = "Total") -> Optional[Dict[str, float]]:
    """Return {match_total, over_odds, under_odds} for the given market/scope,
    choosing the rung whose Over price is closest to 1.85. None if absent."""
    over: Dict[float, float] = {}
    under: Dict[float, float] = {}
    for m in markets:
        if m.get("name") != market_name or (m.get("scope") or "FULL_MATCH") != scope:
            continue
        for s in m.get("selections") or []:
            line, price = s.get("line"), s.get("price")
            if line is None or price is None:
                continue
            nm = str(s.get("name") or "")
            (over if nm.startswith("Over") else under if nm.startswith("Under") else {})[line] = price
    if not over:
        return None
    # match_total must end in .5 (engine rule) — filter, then nearest-1.85 Over.
    cands = [ln for ln in over if abs((ln * 2) % 2 - 1) < 1e-6]  # x.5
    if not cands:
        return None
    best = min(cands, key=lambda ln: abs(over[ln] - 1.85))
    return {"match_total": best, "over_odds": over[best], "under_odds": under.get(best)}


def _moneyline(markets: List[Dict[str, Any]], scope: str) -> Dict[str, Optional[float]]:
    for m in markets:
        if m.get("name") == "To Win Match" and (m.get("scope") or "FULL_MATCH") == scope:
            odds = {s.get("name"): s.get("price") for s in m.get("selections") or []}
            return {"home_odds": odds.get("1"), "away_odds": odds.get("2")}
    return {"home_odds": None, "away_odds": None}


def _team_names(h2h: Dict[str, Any]) -> Dict[str, str]:
    return {str(t.get("id")): t.get("title", "") for t in (h2h.get("teams") or [])}


def _h2h_for_scope(ev: Dict[str, Any], scope: str) -> List[Dict[str, Any]]:
    """H2H matches with scores matching the scope (ADR-7)."""
    h2h = ev.get("h2h_data") or {}
    names = _team_names(h2h)
    out: List[Dict[str, Any]] = []
    for g in h2h.get("game_shorts") or []:
        # Skip future fixtures (not played yet).
        if g.get("status") == 1 and not (g.get("score1") or g.get("score2")):
            continue
        date = str(g.get("date_start") or "")[:10]
        home = names.get(str(g.get("team1_id")), "?")
        away = names.get(str(g.get("team2_id")), "?")
        if scope in ("FULL_MATCH", "HOME_TEAM_TOTAL", "AWAY_TEAM_TOTAL"):
            hs, as_ = g.get("score1"), g.get("score2")
        else:
            qidx = _QUARTER_SCOPES.get(scope)
            if not qidx:
                continue
            by_q = {_QKEY.get(p.get("period_key")): (p.get("home_score"), p.get("away_score"))
                    for p in g.get("periods") or []}
            if not all(q in by_q for q in qidx):
                continue
            hs = sum(by_q[q][0] or 0 for q in qidx)
            as_ = sum(by_q[q][1] or 0 for q in qidx)
        if hs is None or as_ is None:
            continue
        out.append({"home_team": home, "away_team": away,
                    "home_score": int(hs), "away_score": int(as_), "date": date})
    return out


def event_to_predict_requests(ev: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One betb2b event dict → a list of engine PredictRequest dicts (per scope)."""
    match_id = str(ev.get("event_id") or "")
    home, away = ev.get("home") or "", ev.get("away") or ""
    if not (match_id and home and away):
        return []
    markets = ev.get("markets") or []
    reqs: List[Dict[str, Any]] = []

    def add(scope: str, odds: Optional[Dict[str, Any]]) -> None:
        if not odds or odds.get("match_total") is None:
            return
        reqs.append({
            "match_id": match_id, "home_team": home, "away_team": away, "scope": scope,
            "odds": odds, "h2h_matches": _h2h_for_scope(ev, scope),
        })

    # Combined-total scopes (full + halves + quarters) present in the markets.
    for scope in ["FULL_MATCH", "FIRST_HALF", "SECOND_HALF",
                  "QUARTER_1", "QUARTER_2", "QUARTER_3", "QUARTER_4"]:
        t = _nearest_185_total(markets, scope)
        if t is not None:
            t.update(_moneyline(markets, scope))
            add(scope, t)

    # Individual-team totals (full match single teams).
    add("HOME_TEAM_TOTAL", _nearest_185_total(markets, "FULL_MATCH", "Individual Total Home"))
    add("AWAY_TEAM_TOTAL", _nearest_185_total(markets, "FULL_MATCH", "Individual Total Away"))
    return reqs


def build_ingest_matches(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten a list of event dicts into engine PredictRequest matches."""
    matches: List[Dict[str, Any]] = []
    for ev in events:
        matches.extend(event_to_predict_requests(ev))
    return matches


async def post_ingest(
    matches: List[Dict[str, Any]], engine_url: str, *,
    source: str = "betb2b-scraper", token: Optional[str] = None,
    scraped_at: Optional[str] = None, chunk: int = 100,
) -> List[Dict[str, Any]]:
    """POST matches to ``{engine_url}/api/ingest`` in chunks of ≤100.

    Returns one summary dict per chunk. ``token`` (if given) → Bearer auth.
    """
    import httpx

    # The engine authenticates ingest with an `x-api-key` header.
    headers = {"content-type": "application/json"}
    if token:
        headers["x-api-key"] = token
    url = f"{engine_url.rstrip('/')}/api/ingest"
    out: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=45.0) as c:
        for i in range(0, len(matches), chunk):
            payload = {"source": source, "scraped_at": scraped_at,
                       "matches": matches[i:i + chunk]}
            try:
                r = await c.post(url, json=payload, headers=headers)
                out.append({"status": r.status_code, "sent": len(payload["matches"]),
                            "body": r.text[:200]})
            except Exception as exc:  # noqa: BLE001
                out.append({"status": 0, "sent": len(payload["matches"]), "error": str(exc)[:200]})
    return out
