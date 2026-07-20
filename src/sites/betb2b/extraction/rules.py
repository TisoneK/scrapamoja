"""BetB2B family extraction rules.

Project raw 1xbet terse-key ``Value[]`` JSON onto the typed dataclasses
in :mod:`~src.sites.betb2b.extraction.models`.

The 1xbet terse schema (per
`src/sites/linebet/snapshots/normalized/livefeed_get1x2_schema.md`):

    {"Success": true, "Error": "", "Value": [<event>, …]}

Per event (single-letter keys):

    I / ZP   event id           O1 / O2  team names (O1E/O2E = English)
    SN / SI  sport name / id    O1I/O2I  team ids
    L  / LI  league name / id   S        start time (unix)
    CN       country            SC       score: FS{S1,S2}, PS[], CP, TS, SLS
    E[]      markets: T=type, G=group, C=odds, CV=odds str,
                    P=param (handicap/total line), B=blocked
    AE[]     grouped markets: {G, ME:[…same shape as E]}

The extractor is defensive — a malformed payload degrades to an empty
list / ``None``, never an exception. The BetB2B backend ships schema
drift without notice, so we'd rather drop a few events than crash
mid-scrape.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..config import BetB2BSkinConfig
from ..markets import lookup_market
from ..sport_ids import lookup_sport
from .models import (
    CapturedFeedResponse,
    Event,
    EventStatus,
    H2HData,
    H2HGameShort,
    Market,
    MarketType,
    PeriodScore,
    Selection,
    Sport,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Coercion helpers
# ---------------------------------------------------------------------------
def _coerce_int(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _coerce_float(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _coerce_datetime(raw: Any) -> Optional[datetime]:
    """Coerce a timestamp into a UTC datetime.

    The BetB2B feed uses Unix epoch seconds (int / numeric string) for the
    ``S`` field. We also handle ISO-8601 strings for forward-compat.
    """
    if raw is None or raw == "":
        return None
    f = _coerce_float(raw)
    if f is not None:
        try:
            return datetime.fromtimestamp(f, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(raw, str):
        s = raw.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Group-id → MarketType mapping (used when the per-T table doesn't have it)
# ---------------------------------------------------------------------------
_GROUP_TO_MARKET_TYPE: Dict[int, MarketType] = {
    1: MarketType.MONEYLINE_12,
    2: MarketType.HANDICAP,
    3: MarketType.TOTALS,
    4: MarketType.TOTALS,           # individual total — model as TOTALS
    5: MarketType.CORRECT_SCORE,
    6: MarketType.DOUBLE_CHANCE,
    7: MarketType.HT_FT,
    8: MarketType.ODD_EVEN,
    9: MarketType.BTTS,
    17: MarketType.TOTALS,
    101: MarketType.MONEYLINE_12,
    102: MarketType.MONEYLINE_H2H,
}


def _market_type_for_group(g_id: int) -> MarketType:
    return _GROUP_TO_MARKET_TYPE.get(g_id, MarketType.OTHER)


# ---------------------------------------------------------------------------
# Sport name → Sport enum
# ---------------------------------------------------------------------------
# Common BetB2B period-type integers to human-readable names.
# These are sport-specific; type 18 = "1st quarter" for basketball
# but could mean something different for other sports. The mapping
# covers the most common values seen in H2H gameShorts.periods[].type.
_PERIOD_TYPE_NAMES: Dict[int, str] = {
    1: "1st half",
    2: "2nd half",
    3: "3rd period",
    4: "4th period",
    5: "1st set",
    6: "2nd set",
    7: "3rd set",
    8: "4th set",
    9: "5th set",
    18: "1st quarter",
    19: "2nd quarter",
    20: "3rd quarter",
    21: "4th quarter",
    22: "1st overtime",
    23: "2nd overtime",
}

_SPORT_NAME_ALIASES: Dict[str, Sport] = {
    "soccer": Sport.FOOTBALL,
    "football": Sport.FOOTBALL,
    "basketball": Sport.BASKETBALL,
    "tennis": Sport.TENNIS,
    "ice hockey": Sport.HOCKEY,
    "hockey": Sport.HOCKEY,
    "baseball": Sport.BASEBALL,
    "volleyball": Sport.VOLLEYBALL,
    "table tennis": Sport.TABLE_TENNIS,
    "esports": Sport.ESPORTS,
    "e-sports": Sport.ESPORTS,
    "cybersport": Sport.ESPORTS,
    "handball": Sport.HANDBALL,
    "cricket": Sport.CRICKET,
    "rugby": Sport.RUGBY,
    "mma": Sport.MMA,
    "boxing": Sport.BOXING,
}


def _coerce_sport(sport_name: Any, sport_id: Optional[int], skin: BetB2BSkinConfig) -> Tuple[Sport, str]:
    """Return (Sport enum, display name).

    Prefers the SN field; falls back to the sport_map lookup by SI id;
    finally falls back to Sport.OTHER.
    """
    if isinstance(sport_name, str) and sport_name.strip():
        name = sport_name.strip()
        enum = _SPORT_NAME_ALIASES.get(name.lower(), Sport.OTHER)
        return enum, name

    if sport_id is not None:
        mapped = lookup_sport(sport_id, skin.sport_map)
        if mapped:
            enum = _SPORT_NAME_ALIASES.get(mapped.lower(), Sport.OTHER)
            return enum, mapped

    return Sport.OTHER, "Other"


# ---------------------------------------------------------------------------
# Status coercion
# ---------------------------------------------------------------------------
def _coerce_status(sc: Dict[str, Any], is_live: bool) -> Tuple[EventStatus, Optional[int], Optional[str], Optional[str]]:
    """Derive (status, minute, period, time_remaining) from the ``SC`` block.

    The ``SC`` (score) block carries: ``CP`` (current period int),
    ``CPS`` (current period name), ``TS`` (clock seconds),
    ``SLS`` (time-left text). We use these to derive a coarse status +
    a period label + a minute-ish field for football.
    """
    if not sc:
        return (EventStatus.LIVE if is_live else EventStatus.NOT_STARTED, None, None, None)

    cp = _coerce_int(sc.get("CP"))
    cps = sc.get("CPS")
    sls = sc.get("SLS")
    ts = _coerce_int(sc.get("TS"))

    # If the event has an SC block at all and is_live=True, it's LIVE.
    # If it has an SC block but is_live=False (prematch detail), we
    # still treat as NOT_STARTED — the SC block just carries structure.
    if not is_live:
        return (EventStatus.NOT_STARTED, None, None, None)

    # Derive a "minute" for football (TS is seconds since period start;
    # we approximate the match minute by scaling — this is rough but
    # useful for downstream filtering).
    minute: Optional[int] = None
    if ts is not None and cp is not None:
        # Heuristic: football halves are 45 min; basketball quarters 12.
        # We just use TS in minutes as the within-period minute.
        minute = ts // 60

    return (EventStatus.LIVE, minute, cps if isinstance(cps, str) else None,
            sls if isinstance(sls, str) else None)


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------
class BetB2BExtractionRules:
    """Project raw BetB2B feed JSON payloads onto our dataclass models.

    All methods are defensive: a malformed payload degrades to an empty
    list / ``None``, never an exception. The extractor is parameterised
    by a :class:`BetB2BSkinConfig` so it uses the per-skin market/sport
    lookup tables.
    """

    def __init__(self, skin: BetB2BSkinConfig) -> None:
        self.skin = skin
        logger.info("BetB2BExtractionRules initialised for skin=%s", skin.name)

    # ----- public API -----
    def decode_response(
        self,
        url: str,
        status: int,
        content_type: str,
        raw_bytes: Optional[bytes],
    ) -> CapturedFeedResponse:
        """Decode a raw HTTP response into a :class:`CapturedFeedResponse`.

        ``raw_bytes`` may be ``None`` for bodyless responses (204, 304).
        Decode failures result in an empty ``decoded`` dict — the
        extractor will then return no events, but the scrape continues.
        """
        decoded: Dict[str, Any] = {}
        body_len = len(raw_bytes) if raw_bytes else 0
        if raw_bytes:
            try:
                text = raw_bytes.decode("utf-8", errors="replace")
                decoded = json.loads(text)
                if not isinstance(decoded, dict):
                    # Some payloads are top-level lists — wrap them.
                    decoded = {"_root_list": decoded}
            except (json.JSONDecodeError, ValueError) as exc:
                logger.debug("Could not decode JSON from %s: %s", url, exc)
                decoded = {}

        return CapturedFeedResponse(
            url=url,
            status=status,
            content_type=content_type,
            body_bytes=body_len,
            decoded=decoded,
        )

    def extract_from_captured(self, captured: CapturedFeedResponse) -> List[Event]:
        """Project a captured feed response onto :class:`Event` instances."""
        payload = captured.decoded
        if not payload:
            return []

        # The 1xbet envelope is {"Success": true, "Error": "", "Value": [...]}.
        # Some endpoints return the array directly at the top level.
        if isinstance(payload, dict):
            if payload.get("Success") is False:
                logger.warning(
                    "Feed %s returned Success=false: Error=%r",
                    captured.url, payload.get("Error"),
                )
                return []
            value = payload.get("Value")
        elif isinstance(payload, list):
            value = payload
        else:
            return []

        if value is None:
            return []
        if not isinstance(value, list):
            # Some endpoints wrap Value in another structure (e.g. by sport).
            value = self._flatten_value(value)

        events: List[Event] = []
        for ev_dict in value:
            if not isinstance(ev_dict, dict):
                continue
            ev = self._build_event(ev_dict, source_url=captured.url)
            if ev is not None:
                events.append(ev)

        logger.debug(
            "Extracted %d events from %s (skin=%s)",
            len(events), captured.url, self.skin.name,
        )
        return events

    # ----- event building -----
    def _flatten_value(self, value: Any) -> List[Dict[str, Any]]:
        """Flatten a nested Value structure into a list of event dicts.

        Some endpoints (e.g. ``GetSportsShortZip``) return
        ``{"Value": [{"Sports": [{"Events": [...]}]}]}`` — walk it.
        """
        out: List[Dict[str, Any]] = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                if self._looks_like_event(node):
                    out.append(node)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(value)
        return out

    def _looks_like_event(self, obj: Dict[str, Any]) -> bool:
        """Heuristic: does this dict represent a fixture/event?

        The 1xbet event shape has ``I`` (id) + ``O1``/``O2`` (teams).
        """
        has_id = any(k in obj for k in ("I", "ZP", "id", "Id"))
        has_teams = any(
            k in obj for k in ("O1", "O2", "Home", "Away", "Team1", "Team2")
        )
        return has_id and has_teams

    def _build_event(self, ev: Dict[str, Any], source_url: str) -> Optional[Event]:
        event_id = self._event_id(ev)
        home, away = self._event_team_names(ev)
        if not event_id or (not home and not away):
            return None

        sport_id = _coerce_int(ev.get("SI"))
        sport_name = ev.get("SN")
        sport_enum, sport_display = _coerce_sport(sport_name, sport_id, self.skin)

        competition = self._event_competition(ev)
        start_time = _coerce_datetime(ev.get("S"))
        country = ev.get("CN")
        league_id = _coerce_int(ev.get("LI"))

        sc = ev.get("SC") or {}
        is_live = self._infer_is_live(ev, sc)
        status, minute, period, time_remaining = _coerce_status(sc, is_live)

        score_home, score_away = self._extract_score(sc)
        markets = self._extract_markets(ev, is_live=is_live)

        period_scores = self._extract_period_scores(sc)

        return Event(
            event_id=event_id,
            sport=sport_enum,
            competition=competition,
            home=home,
            away=away,
            start_time=start_time,
            status=status,
            score_home=score_home,
            score_away=score_away,
            minute=minute,
            period=period,
            period_scores=period_scores,
            time_remaining=time_remaining,
            is_live=is_live,
            country=country if isinstance(country, str) else None,
            markets=markets,
            source_url=source_url,
            raw_endpoint=source_url,
            sport_id=sport_id,
            league_id=league_id,
        )

    def _event_id(self, ev: Dict[str, Any]) -> str:
        eid = ev.get("I") or ev.get("ZP") or ev.get("id") or ev.get("Id")
        return str(eid) if eid not in (None, "") else ""

    def _event_team_names(self, ev: Dict[str, Any]) -> Tuple[str, str]:
        # Prefer English names (O1E/O2E) — the SN field is locale-specific.
        home = ev.get("O1E") or ev.get("O1") or ev.get("Home") or ev.get("Team1") or ""
        away = ev.get("O2E") or ev.get("O2") or ev.get("Away") or ev.get("Team2") or ""
        return str(home).strip(), str(away).strip()

    def _event_competition(self, ev: Dict[str, Any]) -> str:
        comp = ev.get("L") or ev.get("League") or ev.get("LeagueName") or ""
        return str(comp).strip() if comp else ""

    def _infer_is_live(self, ev: Dict[str, Any], sc: Dict[str, Any]) -> bool:
        """Infer whether an event is live.

        The 1xbet feed doesn't carry an explicit ``is_live`` flag on the
        event. We treat the presence of a non-empty ``SC`` (score) block
        as a live signal — prematch events either omit ``SC`` or have an
        empty one. The LiveFeed root also implies live.
        """
        if sc and (sc.get("FS") or sc.get("PS") or "CP" in sc):
            return True
        # If the source URL is the LiveFeed root, treat as live.
        if "/LiveFeed/" in ev.get("_source_url", ""):
            return True
        return False

    def _extract_score(self, sc: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
        """Extract (home_score, away_score) from the ``SC`` block.

        ``FS`` (full score) is ``{"S1": home, "S2": away}``.
        """
        if not sc:
            return None, None
        fs = sc.get("FS")
        if isinstance(fs, dict):
            return _coerce_int(fs.get("S1")), _coerce_int(fs.get("S2"))
        return None, None

    def _extract_period_scores(self, sc: Dict[str, Any]) -> List[PeriodScore]:
        """Extract ``SC.PS[]`` into a list of :class:`PeriodScore`.

        Each element is ``{"Key": 1, "Value": {"S1": 19, "S2": 20, "NF": "1st quarter"}}``.
        Returns empty list if absent.
        """
        if not sc:
            return []
        ps_list = sc.get("PS")
        if not isinstance(ps_list, list):
            return []
        scores: List[PeriodScore] = []
        for item in ps_list:
            if not isinstance(item, dict):
                continue
            key = _coerce_int(item.get("Key"))
            val = item.get("Value")
            if not isinstance(val, dict):
                continue
            s1 = _coerce_int(val.get("S1"))
            s2 = _coerce_int(val.get("S2"))
            name = val.get("NF") or val.get("N") or ""
            if not isinstance(name, str):
                name = str(name) if name is not None else ""
            scores.append(PeriodScore(
                period_name=name,
                home_score=s1 or 0,
                away_score=s2 or 0,
                period_key=key or 0,
            ))
        return scores

    # ----- markets -----
    def _extract_markets(self, ev: Dict[str, Any], *, is_live: bool) -> List[Market]:
        """Extract markets from an event dict.

        Two layouts are supported:

        1. ``E[]`` — a flat list of selections, each carrying ``T``
           (type), ``G`` (group), ``C`` (odds), ``P`` (line), ``B``
           (blocked). Selections belonging to the same market are
           grouped by ``(G, T)`` — each ``T`` is one selection inside
           the market identified by ``G``.

        2. ``AE[]`` — grouped markets: ``[{G, ME: [...same as E]}]``.
           This is the richer layout; when present we prefer it.
        """
        markets: List[Market] = []

        # Layout 2: AE[] (grouped)
        ae = ev.get("AE")
        if isinstance(ae, list) and ae:
            for group in ae:
                if not isinstance(group, dict):
                    continue
                g_id = _coerce_int(group.get("G"))
                me = group.get("ME")
                if not isinstance(me, list):
                    continue
                market = self._build_market_from_selections(
                    me, g_id=g_id, is_live=is_live,
                )
                if market is not None:
                    markets.append(market)

        # Layout 1: E[] (flat) — only used to ENRICH existing markets
        # (add selections the AE layout missed) or as a fallback when
        # AE is absent.
        e = ev.get("E")
        if isinstance(e, list) and e:
            # Group E selections by G — each G is one market.
            by_g: Dict[int, List[Dict[str, Any]]] = {}
            for sel in e:
                if not isinstance(sel, dict):
                    continue
                g_id = _coerce_int(sel.get("G"))
                if g_id is None:
                    continue
                by_g.setdefault(g_id, []).append(sel)

            # If we already have AE markets, merge E selections into them
            # by G; otherwise build fresh markets from E.
            existing_by_g: Dict[int, Market] = {m.raw_g: m for m in markets if m.raw_g is not None}
            for g_id, sels in by_g.items():
                if g_id in existing_by_g:
                    # Skip — AE layout is richer, E is just a subset.
                    continue
                market = self._build_market_from_selections(
                    sels, g_id=g_id, is_live=is_live,
                )
                if market is not None:
                    markets.append(market)

        return markets

    def _build_market_from_selections(
        self,
        sels: List[Dict[str, Any]],
        *,
        g_id: Optional[int],
        is_live: bool,
    ) -> Optional[Market]:
        """Build one :class:`Market` from a list of selection dicts.

        Each selection dict has ``T`` (type), ``C`` (odds), ``CV`` (odds
        str), ``P`` (line), ``B`` (blocked). We look up ``T`` in the
        skin's market_types table to get the (market_name,
        selection_label) pair.
        """
        if not sels:
            return None
        if g_id is None:
            return None

        market_name: Optional[str] = None
        selections: List[Selection] = []

        for sel in sels:
            if not isinstance(sel, dict):
                continue
            t_id = _coerce_int(sel.get("T"))
            if t_id is None:
                continue

            price = _coerce_float(sel.get("C") or sel.get("CV"))
            if price is None:
                continue  # no odds → not a real selection

            line = _coerce_float(sel.get("P"))
            blocked = bool(sel.get("B") or False)

            m_name, sel_label = lookup_market(
                g_id=g_id,
                t_id=t_id,
                market_groups=self.skin.market_groups,
                market_types=self.skin.market_types,
            )
            if market_name is None:
                market_name = m_name or f"G={g_id}"

            # If we have a line (handicap/total), append it to the label
            # so the selection is self-describing.
            label = sel_label or f"T={t_id}"
            if line is not None:
                # Format the line: +1.5 / -1.5 / 2.5 — keep the sign for
                # handicaps, drop it for totals (2.5 not +2.5).
                if g_id in (2,) and line >= 0:
                    label = f"{label} (+{line:g})"
                elif g_id in (2,):
                    label = f"{label} ({line:g})"
                elif g_id in (3, 17, 4):
                    label = f"{label} {line:g}"

            selections.append(Selection(
                name=label,
                price=price,
                line=line,
                is_suspended=blocked,
                raw_t=t_id,
                raw_g=g_id,
            ))

        if not selections:
            return None

        return Market(
            name=market_name or f"G={g_id}",
            market_type=_market_type_for_group(g_id),
            selections=selections,
            is_live=is_live,
            is_suspended=all(s.is_suspended for s in selections),
            raw_g=g_id,
        )

    # ------------------------------------------------------------------ #
    # H2H (statisticfeed)
    # ------------------------------------------------------------------ #
    @staticmethod
    def extract_h2h_data(raw: Dict[str, Any]) -> Optional[H2HData]:
        """Parse a statisticfeed H2H response into an :class:`H2HData`.

        The H2H endpoint returns team metadata (``teams[]``) and
        historical match results (``gameShorts[]``) with per-period
        scores. Returns ``None`` if the raw data is malformed.

        Response shape::

            {
                "teams": [{...}],
                "gameShorts": [{
                    "id": "...",
                    "team1": "...",
                    "team2": "...",
                    "dateStart": 1752183000,
                    "score1": 81,
                    "score2": 90,
                    "periods": [{"score1": 15, "score2": 22, "type": 18}]
                }],
                "sportId": 3
            }
        """
        if not raw or not isinstance(raw, dict):
            return None

        teams = raw.get("teams")
        game_shorts_raw = raw.get("gameShorts")
        if not isinstance(teams, list) or not isinstance(game_shorts_raw, list):
            return None

        sport_id = _coerce_int(raw.get("sportId"))
        game_shorts: List[H2HGameShort] = []

        for gs in game_shorts_raw:
            if not isinstance(gs, dict):
                continue
            periods_raw = gs.get("periods")
            periods: List[PeriodScore] = []
            if isinstance(periods_raw, list):
                for p in periods_raw:
                    if not isinstance(p, dict):
                        continue
                    pt = _coerce_int(p.get("type"))
                    periods.append(PeriodScore(
                        period_name=_PERIOD_TYPE_NAMES.get(pt, f"period_{pt}") if pt else "",
                        home_score=_coerce_int(p.get("score1")) or 0,
                        away_score=_coerce_int(p.get("score2")) or 0,
                        period_key=pt or 0,
                    ))

            game_shorts.append(H2HGameShort(
                game_id=str(gs.get("id", "")),
                team1_id=str(gs.get("team1", "")),
                team2_id=str(gs.get("team2", "")),
                date_start=_coerce_datetime(gs.get("dateStart")),
                score1=_coerce_int(gs.get("score1")),
                score2=_coerce_int(gs.get("score2")),
                sub_score1=_coerce_int(gs.get("subScore1")),
                sub_score2=_coerce_int(gs.get("subScore2")),
                winner=_coerce_int(gs.get("winner")),
                status=_coerce_int(gs.get("status")),
                periods=periods,
            ))

        return H2HData(
            teams=teams,
            game_shorts=game_shorts,
            sport_id=sport_id,
        )
