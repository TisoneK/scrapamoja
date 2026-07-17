"""
Linebet extraction rules.

The Linebet SPA fetches its data from a private JSON API under
``/api/...``. The exact response shapes vary between endpoints and can
change between releases, so this module takes a **defensive, best-effort
projection** approach:

  * Each known endpoint (prematch list, live list, market detail, …)
    gets a small ``_extract_*`` method.
  * Every method uses ``.get()`` with defaults and never raises on a
    missing key — it just returns an empty list / ``None``.
  * A single :meth:`extract_from_captured` dispatcher inspects the
    captured response URL and routes it to the right extractor.

The goal is resilience: when Linebet ships a new endpoint or reshuffles
a field, we degrade to "fewer events / fewer markets" rather than
crashing.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    CapturedAPIResponse,
    Event,
    EventStatus,
    Market,
    MarketType,
    Selection,
    Sport,
)

logger = logging.getLogger(__name__)


# Map known API path fragments to logical endpoint types. We use these
# to route a captured response to the right extractor.
_ENDPOINT_PREMATCH = "prematch"
_ENDPOINT_LIVE = "live"
_ENDPOINT_MARKET = "market"
_ENDPOINT_MENU = "menu"
_ENDPOINT_INFO = "info"
_ENDPOINT_UNKNOWN = "unknown"


def _classify_endpoint(url: str) -> str:
    """Classify a captured URL into a logical endpoint type."""
    u = url.lower()
    if "/api/live" in u or "/api/inplay" in u:
        return _ENDPOINT_LIVE
    if "/api/list" in u or "/api/prematch" in u or "/api/sport" in u:
        return _ENDPOINT_PREMATCH
    if "/api/bet" in u or "/api/market" in u or "/api/odds" in u:
        return _ENDPOINT_MARKET
    if "/api/menu" in u:
        return _ENDPOINT_MENU
    if "/api/info" in u or "/api/translations" in u:
        return _ENDPOINT_INFO
    return _ENDPOINT_UNKNOWN


# Sport-name normalisation. Linebet's sport labels are mostly English
# title-case, but the live endpoint occasionally uses different casing.
_SPORT_ALIASES: Dict[str, Sport] = {
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
}


def _coerce_sport(raw: Any) -> Sport:
    if isinstance(raw, Sport):
        return raw
    if not isinstance(raw, str):
        return Sport.OTHER
    key = raw.strip().lower()
    return _SPORT_ALIASES.get(key, Sport.OTHER)


def _coerce_status(raw: Any, is_live: bool) -> EventStatus:
    """Best-effort status coercion."""
    if raw is None:
        return EventStatus.LIVE if is_live else EventStatus.NOT_STARTED
    if isinstance(raw, int):
        # Linebet uses small ints for live state: 0=not started, 1=live,
        # 2=paused/break, 3=finished, 4=cancelled. Tolerate any value.
        mapping = {
            0: EventStatus.NOT_STARTED,
            1: EventStatus.LIVE,
            2: EventStatus.PAUSED,
            3: EventStatus.FINISHED,
            4: EventStatus.CANCELLED,
        }
        return mapping.get(raw, EventStatus.UNKNOWN)
    s = str(raw).strip().lower()
    if s in {"live", "inplay", "in_play", "in-play"}:
        return EventStatus.LIVE
    if s in {"paused", "break", "ht", "ft"}:
        return EventStatus.PAUSED
    if s in {"finished", "ended", "ft"}:
        return EventStatus.FINISHED
    if s in {"cancelled", "canceled", "void"}:
        return EventStatus.CANCELLED
    if s in {"not_started", "notstarted", "scheduled", "prematch"}:
        return EventStatus.NOT_STARTED
    return EventStatus.UNKNOWN


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

    Linebet uses two formats:
      * Unix epoch seconds (int / numeric string)
      * ISO-8601 strings with or without trailing 'Z'
    """
    if raw is None or raw == "":
        return None
    # Numeric epoch
    f = _coerce_float(raw)
    if f is not None:
        try:
            return datetime.fromtimestamp(f, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    # ISO string
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
# Market classification heuristics
# ---------------------------------------------------------------------------
_MARKET_NAME_PATTERNS: List[Tuple[re.Pattern[str], MarketType]] = [
    (re.compile(r"\b1\s*[xX]\s*2\b|match\s*result|three\s*way|1x2", re.I), MarketType.MONEYLINE_12),
    (re.compile(r"\bdouble\s*chance\b|1x\s*/\s*12\s*/\s*x2", re.I), MarketType.DOUBLE_CHANCE),
    (re.compile(r"\bover\s*/\s*under\b|\btotal\b|totals", re.I), MarketType.TOTALS),
    (re.compile(r"\bhandicap\b|asian\s*handicap|spread", re.I), MarketType.HANDICAP),
    (re.compile(r"\bcorrect\s*score\b", re.I), MarketType.CORRECT_SCORE),
    (re.compile(r"\bmoneyline\b|to\s*win|winner|h2h|head\s*to\s*head", re.I), MarketType.MONEYLINE_H2H),
]


def _classify_market(name: str) -> MarketType:
    if not name:
        return MarketType.OTHER
    for pat, mtype in _MARKET_NAME_PATTERNS:
        if pat.search(name):
            return mtype
    return MarketType.OTHER


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------
class LinebetExtractionRules:
    """Project raw Linebet API JSON payloads onto our dataclass models.

    All methods are defensive: a malformed payload degrades to an empty
    list / ``None``, never an exception. This is critical because
    Linebet ships backend changes without notice and we'd rather drop a
    few events than crash mid-scrape.
    """

    def __init__(self) -> None:
        self.field_mappings: Dict[str, Dict[str, str]] = {}
        logger.info("LinebetExtractionRules initialised")

    # ----- public API -----
    def extract_from_captured(self, captured: CapturedAPIResponse) -> List[Event]:
        """Route a captured response to the right extractor by URL."""
        endpoint = _classify_endpoint(captured.url)
        payload = captured.decoded

        if not payload:
            return []

        try:
            if endpoint == _ENDPOINT_PREMATCH:
                return self._extract_prematch(payload, captured.url)
            if endpoint == _ENDPOINT_LIVE:
                return self._extract_live(payload, captured.url)
            if endpoint == _ENDPOINT_MARKET:
                return self._extract_market_detail(payload, captured.url)
            # menu / info / unknown endpoints don't produce events directly.
            return []
        except Exception as exc:  # noqa: BLE001 — defensive projection
            logger.warning("Extraction failed for %s: %s", captured.url, exc)
            return []

    def decode_captured_response(
        self, url: str, status: int, content_type: str, raw_bytes: Optional[bytes]
    ) -> CapturedAPIResponse:
        """Decode a raw network response into a CapturedAPIResponse.

        ``raw_bytes`` may be ``None`` for bodyless responses (204, 304).
        Decode failures result in an empty ``decoded`` dict — the
        extractor will then return no events, but the scrape continues.
        """
        decoded: Dict[str, Any] = {}
        body_len = len(raw_bytes) if raw_bytes else 0
        if raw_bytes:
            try:
                text = raw_bytes.decode("utf-8", errors="replace")
                # Some endpoints return JSONP: `callback({...});`
                # Strip the wrapper if present.
                m = re.match(r"^\s*[\w$.]+\s*\((.*)\)\s*;?\s*$", text, re.DOTALL)
                if m:
                    text = m.group(1)
                decoded = json.loads(text)
                if not isinstance(decoded, dict):
                    # Some payloads are top-level lists — wrap them.
                    decoded = {"_root_list": decoded}
            except (json.JSONDecodeError, ValueError) as exc:
                logger.debug("Could not decode JSON from %s: %s", url, exc)
                decoded = {}

        return CapturedAPIResponse(
            url=url,
            status=status,
            content_type=content_type,
            body_bytes=body_len,
            decoded=decoded,
        )

    # ----- field mapping helpers -----
    def _get_first(self, obj: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        """Return the first present key from ``obj``."""
        for k in keys:
            if k in obj and obj[k] not in (None, ""):
                return obj[k]
        return default

    def _iter_event_dicts(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Yield event-like dicts from a payload of arbitrary shape.

        Linebet's list endpoints wrap the event array under various keys
        (``Value``, ``Events``, ``events``, ``Items``, ``Data``). Some
        wrap it under ``{"Value": {"Sport": [{"Events": [...]}]}}``.
        This helper walks the structure breadth-first and collects any
        dict that looks event-shaped (has team / id fields).
        """
        out: List[Dict[str, Any]] = []
        seen_ids: set = set()
        stack: List[Any] = [payload]
        while stack:
            node = stack.pop(0)
            if isinstance(node, dict):
                if self._looks_like_event(node):
                    eid = str(node.get("Id") or node.get("EventId") or node.get("id") or id(node))
                    if eid not in seen_ids:
                        seen_ids.add(eid)
                        out.append(node)
                # Continue walking even if it looks like an event — events
                # may be nested inside sport-grouping objects.
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):
                stack.extend(node)
        return out

    def _looks_like_event(self, obj: Dict[str, Any]) -> bool:
        """Heuristic: does this dict represent a fixture/event?"""
        has_id = any(k in obj for k in ("Id", "EventId", "id", "event_id"))
        has_teams = any(
            k in obj
            for k in (
                "Home", "Away", "O1", "O2",
                "Team1", "Team2", "team1_name", "team2_name",
                "homeName", "awayName", "HomeName", "AwayName",
            )
        )
        return has_id and has_teams

    def _event_team_names(self, ev: Dict[str, Any]) -> Tuple[str, str]:
        home = self._get_first(
            ev, "Home", "O1", "Team1", "team1_name", "homeName", "HomeName", default=""
        )
        away = self._get_first(
            ev, "Away", "O2", "Team2", "team2_name", "awayName", "AwayName", default=""
        )
        # Some payloads nest names under sub-objects.
        if isinstance(home, dict):
            home = home.get("Name") or home.get("name") or ""
        if isinstance(away, dict):
            away = away.get("Name") or away.get("name") or ""
        return str(home).strip(), str(away).strip()

    def _event_sport(self, ev: Dict[str, Any]) -> Sport:
        sport_raw = self._get_first(
            ev, "SportName", "Sport", "sport_name", "sportId", "sport", default=None
        )
        if isinstance(sport_raw, dict):
            sport_raw = sport_raw.get("Name") or sport_raw.get("name")
        return _coerce_sport(sport_raw)

    def _event_competition(self, ev: Dict[str, Any]) -> str:
        comp = self._get_first(
            ev, "LeagueName", "CompetitionName", "Tournament", "League", "competition", default=""
        )
        if isinstance(comp, dict):
            comp = comp.get("Name") or comp.get("name") or ""
        return str(comp).strip()

    def _event_id(self, ev: Dict[str, Any]) -> str:
        eid = self._get_first(ev, "Id", "EventId", "id", "event_id", default="")
        return str(eid) if eid != "" else ""

    def _event_start_time(self, ev: Dict[str, Any]) -> Optional[datetime]:
        raw = self._get_first(ev, "StartTime", "KickoffTime", "Start", "Date", "date", "start_time", default=None)
        return _coerce_datetime(raw)

    # ----- per-endpoint extractors -----
    def _extract_prematch(self, payload: Dict[str, Any], source_url: str) -> List[Event]:
        """Prematch list endpoint."""
        events: List[Event] = []
        for ev_dict in self._iter_event_dicts(payload):
            event = self._build_event(ev_dict, is_live=False, source_url=source_url)
            if event:
                events.append(event)
        logger.debug("Prematch extractor produced %d events from %s", len(events), source_url)
        return events

    def _extract_live(self, payload: Dict[str, Any], source_url: str) -> List[Event]:
        """Live / in-play endpoint."""
        events: List[Event] = []
        for ev_dict in self._iter_event_dicts(payload):
            event = self._build_event(ev_dict, is_live=True, source_url=source_url)
            if event:
                events.append(event)
        logger.debug("Live extractor produced %d events from %s", len(events), source_url)
        return events

    def _extract_market_detail(self, payload: Dict[str, Any], source_url: str) -> List[Event]:
        """Per-event market detail endpoint — usually one event, many markets."""
        events: List[Event] = []
        for ev_dict in self._iter_event_dicts(payload):
            event = self._build_event(ev_dict, is_live=False, source_url=source_url)
            if event:
                # Market-detail payloads carry richer market data; rebuild
                # markets from the top-level "Markets" / "MarketGroups" key
                # rather than the inline "Odds" block used by list endpoints.
                event.markets = self._extract_markets(ev_dict, is_live=False)
                events.append(event)
        return events

    # ----- event / market builders -----
    def _build_event(
        self, ev: Dict[str, Any], is_live: bool, source_url: str
    ) -> Optional[Event]:
        home, away = self._event_team_names(ev)
        event_id = self._event_id(ev)
        if not event_id or (not home and not away):
            # Not actually an event — false positive from the heuristic.
            return None

        score_home = _coerce_int(
            self._get_first(ev, "ScoreHome", "Score1", "HomeScore", "score_home", default=None)
        )
        score_away = _coerce_int(
            self._get_first(ev, "ScoreAway", "Score2", "AwayScore", "score_away", default=None)
        )
        minute = _coerce_int(
            self._get_first(ev, "Minute", "CurrentMinute", "GameTime", default=None)
        )
        status_raw = self._get_first(ev, "Status", "State", "EventStatus", default=None)

        markets = self._extract_markets(ev, is_live=is_live)

        return Event(
            event_id=event_id,
            sport=self._event_sport(ev),
            competition=self._event_competition(ev),
            home=home,
            away=away,
            start_time=self._event_start_time(ev),
            status=_coerce_status(status_raw, is_live),
            score_home=score_home,
            score_away=score_away,
            minute=minute,
            is_live=is_live,
            markets=markets,
            source_url=source_url,
            raw_endpoint=source_url,
        )

    def _extract_markets(self, ev: Dict[str, Any], is_live: bool) -> List[Market]:
        """Extract markets from an event dict.

        Two layouts are supported:

        1. Inline odds on list endpoints — a flat block like::

               {"Odds": {"1": 1.85, "X": 3.40, "2": 4.20}}

           or the Asian-handicap variant::

               {"Odds": [{"Name": "1X2", "Selections": [...]}]}

        2. Rich markets on detail endpoints::

               {"Markets": [{"Name": "Match Result 1X2",
                             "Selections": [{"Name": "1", "Price": 1.85}, ...]}]}
        """
        markets: List[Market] = []

        # Layout 2: explicit Markets array
        markets_block = self._get_first(ev, "Markets", "MarketGroups", "marketGroups", default=None)
        if isinstance(markets_block, list):
            for m in markets_block:
                if not isinstance(m, dict):
                    continue
                name = str(m.get("Name") or m.get("name") or "").strip()
                if not name:
                    continue
                selections = self._extract_selections(m, is_live)
                markets.append(
                    Market(
                        name=name,
                        market_type=_classify_market(name),
                        selections=selections,
                        is_live=is_live,
                        is_suspended=bool(m.get("IsSuspended") or m.get("is_suspended") or False),
                    )
                )

        # Layout 1: inline Odds block (only used if no explicit Markets)
        if not markets:
            odds_block = self._get_first(ev, "Odds", "odds", default=None)
            if isinstance(odds_block, dict):
                # Flat 1X2-style: {"1": 1.85, "X": 3.40, "2": 4.20}
                selections: List[Selection] = []
                for sel_name, price_val in odds_block.items():
                    price = _coerce_float(price_val)
                    if price is None:
                        continue
                    selections.append(Selection(name=str(sel_name), price=price))
                if selections:
                    markets.append(
                        Market(
                            name="Match Result",
                            market_type=MarketType.MONEYLINE_12,
                            selections=selections,
                            is_live=is_live,
                        )
                    )
            elif isinstance(odds_block, list):
                for m in odds_block:
                    if not isinstance(m, dict):
                        continue
                    name = str(m.get("Name") or m.get("name") or "Market").strip()
                    selections = self._extract_selections(m, is_live)
                    if selections:
                        markets.append(
                            Market(
                                name=name,
                                market_type=_classify_market(name),
                                selections=selections,
                                is_live=is_live,
                            )
                        )

        return markets

    def _extract_selections(self, market: Dict[str, Any], is_live: bool) -> List[Selection]:
        """Extract selections from a market dict."""
        raw = market.get("Selections") or market.get("selections") or market.get("Outcomes") or []
        if not isinstance(raw, list):
            return []
        out: List[Selection] = []
        for s in raw:
            if not isinstance(s, dict):
                continue
            name = str(s.get("Name") or s.get("name") or s.get("Label") or "").strip()
            price = _coerce_float(s.get("Price") or s.get("Odds") or s.get("price") or s.get("odds"))
            if price is None:
                continue
            line = _coerce_float(s.get("Line") or s.get("Handicap") or s.get("Total") or s.get("line"))
            suspended = bool(s.get("IsSuspended") or s.get("is_suspended") or s.get("Blocked") or False)
            out.append(Selection(name=name, price=price, line=line, is_suspended=suspended))
        return out

    # ----- utility for caller code -----
    def set_field_mappings(self, mappings: Dict[str, Dict[str, str]]) -> None:
        """Store field-name overrides. Currently informational — extraction
        is hard-coded to use the multi-key ``_get_first`` lookups so it
        tolerates Linebet's schema drift without configuration."""
        self.field_mappings = mappings or {}

    def get_all_rule_configs(self) -> Dict[str, Any]:
        """Compatibility shim — github's IntegrationBridge calls this. Returns
        a single named rule set so the bridge's setup logic is satisfied."""
        return {
            "linebet_default": {
                "sport_aliases": dict(_SPORT_ALIASES),
                "market_patterns": [(p.pattern, mt.value) for p, mt in _MARKET_NAME_PATTERNS],
            }
        }

    async def setup_rule_set(self, name: str, config: Dict[str, Any]) -> bool:
        """Compatibility shim — accepts rule-set registration without doing
        anything. Extraction rules in this template are stateless."""
        logger.debug("Linebet rule set '%s' registered (no-op)", name)
        return True
