"""ORM-backed store path (ADR-13) — used when ``DATABASE_URL`` is set.

Mirrors the raw-``sqlite3`` :mod:`store` one-to-one, but through SQLAlchemy
Core over the typed ORM tables, so the scraper writes to **Supabase Postgres**
(and any SQLAlchemy backend) with correct boolean/timestamp/serial handling.
Dialect-aware upserts (``ON CONFLICT``) work on both Postgres and SQLite, so the
same code path is exercised on SQLite in tests (``DATABASE_URL=sqlite:///…``).

:mod:`store` dispatches to this module by connection type; callers keep the same
API (``init_db`` → a connection, helpers take that ``conn``, return dicts).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Connection, func, select
from sqlalchemy.dialects.postgresql import insert as _pg_insert
from sqlalchemy.dialects.sqlite import insert as _sqlite_insert

from .models import (
    Base, Country, Event, EventState, H2HGame, H2HPeriodScore, League,
    Market, OddsSnapshot, PeriodScore, ScrapeRun, ScraperJob, Sport,
    Statistic, SubGame, Team,
)

logger = logging.getLogger(__name__)

# Table handles (Core over the ORM metadata).
_sports, _countries, _leagues, _teams = Sport.__table__, Country.__table__, League.__table__, Team.__table__
_events, _markets, _runs = Event.__table__, Market.__table__, ScrapeRun.__table__
_states, _periods, _odds = EventState.__table__, PeriodScore.__table__, OddsSnapshot.__table__
_h2h, _h2hp, _stats, _jobs = H2HGame.__table__, H2HPeriodScore.__table__, Statistic.__table__, ScraperJob.__table__
_subgames = SubGame.__table__

# One engine per resolved URL (pool reuse); schema ensured once.
_engines: Dict[str, Any] = {}


# Columns added to already-existing tables — `create_all` only adds missing
# TABLES, not columns, so on Postgres (the live Supabase table) they need an
# explicit idempotent ALTER. SQLite (tests) gets them fresh from create_all.
_ADDED_COLUMNS_PG = [
    ("events", "stat_game_id", "TEXT"),
    ("events", "final_score_home", "INTEGER"),
    ("events", "final_score_away", "INTEGER"),
    ("events", "winner", "INTEGER"),
    ("events", "result_status", "INTEGER"),
    ("events", "result_captured_at", "TIMESTAMPTZ"),
]


def _ensure_columns(eng) -> None:
    if eng.dialect.name != "postgresql":
        return  # SQLite path: create_all built the full table
    from sqlalchemy import inspect, text

    # Only ALTER columns that are genuinely missing. Issuing no-op `ADD COLUMN
    # IF NOT EXISTS` is still DDL, which a read-only session rejects — e.g. when
    # Supabase forces the project read-only for exceeding its disk quota. On a
    # redeploy the columns already exist, so this normally runs zero DDL.
    insp = inspect(eng)
    missing = []
    for table, col, typ in _ADDED_COLUMNS_PG:
        try:
            existing = {c["name"] for c in insp.get_columns(table)}
        except Exception:  # noqa: BLE001 — table may not exist yet
            existing = set()
        if col not in existing:
            missing.append((table, col, typ))
    if not missing:
        return
    try:
        with eng.begin() as c:
            for table, col, typ in missing:
                c.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typ}'))
    except Exception as e:  # noqa: BLE001
        # A read-only DB (e.g. over-quota Supabase) can't ALTER — log and carry
        # on so the app still starts and serves reads instead of crash-looping.
        logger.warning("could not add columns %s (read-only DB?): %s", missing, e)


def _get_engine():
    from src.core.db import get_engine, resolve_database_url
    url = resolve_database_url()
    eng = _engines.get(url)
    if eng is None:
        eng = get_engine()
        Base.metadata.create_all(eng, checkfirst=True)
        _ensure_columns(eng)
        _engines[url] = eng
    return eng


def connect() -> Connection:
    """A SQLAlchemy Connection (commit-as-you-go) with the schema ensured."""
    return _get_engine().connect()


def _ins(conn: Connection):
    return _pg_insert if conn.dialect.name == "postgresql" else _sqlite_insert


def _as_int(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None and str(v) != "" else None
    except (TypeError, ValueError):
        return None


def _dt(v: Any) -> Optional[datetime]:
    """Coerce ISO string / epoch / datetime → aware datetime (or None)."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(v, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None


def _match(col, val):
    """NULL-safe equality (mirrors SQLite ``IS``) portable across dialects."""
    return col.is_(None) if val is None else col == val


# --------------------------------------------------------------------------- #
# Dimensions (get-or-create / NULL-safe upsert)
# --------------------------------------------------------------------------- #
def _sport(conn, sport_id: Optional[int], name: Optional[str]) -> Optional[int]:
    if sport_id is None:
        return None
    stmt = _ins(conn)(_sports).values(
        sport_id=sport_id, name=name, slug=(name or "").lower() or None)
    stmt = stmt.on_conflict_do_update(
        index_elements=["sport_id"],
        set_={"name": func.coalesce(stmt.excluded.name, _sports.c.name),
              "slug": func.coalesce(stmt.excluded.slug, _sports.c.slug)})
    conn.execute(stmt)
    return sport_id


def _country(conn, name: Optional[str]) -> Optional[int]:
    if not name:
        return None
    conn.execute(_ins(conn)(_countries).values(name=name)
                 .on_conflict_do_nothing(index_elements=["name"]))
    return conn.execute(
        select(_countries.c.country_id).where(_countries.c.name == name)).scalar()


def _league(conn, league_id, name, sport_id, country_id) -> Optional[int]:
    league_id = _as_int(league_id)
    if league_id is None:
        return None
    stmt = _ins(conn)(_leagues).values(
        league_id=league_id, name=name, sport_id=sport_id, country_id=country_id)
    stmt = stmt.on_conflict_do_update(
        index_elements=["league_id"],
        set_={"name": func.coalesce(stmt.excluded.name, _leagues.c.name),
              "sport_id": func.coalesce(stmt.excluded.sport_id, _leagues.c.sport_id),
              "country_id": func.coalesce(stmt.excluded.country_id, _leagues.c.country_id)})
    conn.execute(stmt)
    return league_id


def _team(conn, name, sport_id, *, backend_id=None, country_id=None,
          feed_id=None, image=None, feed_country_id=None) -> Optional[int]:
    def _backfill(team_id):
        conn.execute(_teams.update().where(_teams.c.team_id == team_id).values(
            feed_id=func.coalesce(_teams.c.feed_id, feed_id),
            image=func.coalesce(_teams.c.image, image),
            feed_country_id=func.coalesce(_teams.c.feed_country_id, feed_country_id)))
        return team_id

    if backend_id:
        row = conn.execute(select(_teams.c.team_id).where(
            _teams.c.backend_id == backend_id)).first()
        if row:
            if name:
                conn.execute(_teams.update().where(_teams.c.team_id == row[0]).values(
                    name=func.coalesce(name, _teams.c.name),
                    country_id=func.coalesce(country_id, _teams.c.country_id)))
            return _backfill(row[0])
    if not name:
        return None
    row = conn.execute(select(_teams.c.team_id, _teams.c.backend_id).where(
        _teams.c.name == name, _match(_teams.c.sport_id, sport_id))).first()
    if row:
        if backend_id and not row[1]:
            conn.execute(_teams.update().where(_teams.c.team_id == row[0]).values(
                backend_id=backend_id,
                country_id=func.coalesce(country_id, _teams.c.country_id)))
        return _backfill(row[0])
    return conn.execute(_teams.insert().values(
        backend_id=backend_id, name=name, sport_id=sport_id, country_id=country_id,
        feed_id=feed_id, image=image, feed_country_id=feed_country_id
    ).returning(_teams.c.team_id)).scalar()


def _market(conn, name, market_type, raw_g) -> int:
    raw_g = _as_int(raw_g)
    mid = conn.execute(select(_markets.c.market_id).where(
        _match(_markets.c.name, name), _match(_markets.c.market_type, market_type),
        _match(_markets.c.raw_g, raw_g))).scalar()
    if mid is not None:
        return mid
    return conn.execute(_markets.insert().values(
        name=name, market_type=market_type, raw_g=raw_g
    ).returning(_markets.c.market_id)).scalar()


# --------------------------------------------------------------------------- #
# Change-only dedup lookups
# --------------------------------------------------------------------------- #
def _last_state(conn, event_id, skin):
    r = conn.execute(select(
        _states.c.status, _states.c.is_live, _states.c.score_home, _states.c.score_away,
        _states.c.minute, _states.c.period, _states.c.time_remaining
    ).where(_states.c.event_id == event_id, _states.c.skin == skin)
     .order_by(_states.c.state_id.desc()).limit(1)).first()
    if not r:
        return None
    return (r[0], bool(r[1]) if r[1] is not None else None, r[2], r[3], r[4], r[5], r[6])


def _last_periods(conn, event_id, skin):
    rows = conn.execute(select(
        _periods.c.period_key, _periods.c.period_name, _periods.c.home_score,
        _periods.c.away_score, func.max(_periods.c.id)
    ).where(_periods.c.event_id == event_id, _periods.c.skin == skin)
     .group_by(_periods.c.period_key, _periods.c.period_name,
               _periods.c.home_score, _periods.c.away_score)).all()
    return {r[0]: (r[1], r[2], r[3]) for r in rows}


def _last_odds(conn, event_id, skin):
    # Latest (price, is_suspended) per (scope, market_id, selection, line).
    # SQLite lets bare columns ride a GROUP BY (returns the max-row's values);
    # Postgres rejects that (GroupingError), so join the max snap_id back to the
    # table to fetch that row's price/is_suspended — portable on both.
    sub = select(
        _odds.c.scope, _odds.c.market_id, _odds.c.selection_name, _odds.c.line,
        func.max(_odds.c.snap_id).label("mx")
    ).where(_odds.c.event_id == event_id, _odds.c.skin == skin).group_by(
        _odds.c.scope, _odds.c.market_id, _odds.c.selection_name, _odds.c.line).subquery()
    rows = conn.execute(select(
        _odds.c.scope, _odds.c.market_id, _odds.c.selection_name, _odds.c.line,
        _odds.c.price, _odds.c.is_suspended
    ).join(sub, _odds.c.snap_id == sub.c.mx)).all()
    return {(r[0], r[1], r[2], r[3]): (r[4], bool(r[5]) if r[5] is not None else False)
            for r in rows}


# --- Bulk variants: one query for the whole batch of events, not one per event.
# The change-only dedup needs each event's last-seen row; fetching them per event
# was N network round-trips to Supabase. These fetch them all at once, keyed by
# event_id, so persist reads them from memory in the loop.
def _last_states_bulk(conn, event_ids, skin):
    if not event_ids:
        return {}
    sub = select(_states.c.event_id, func.max(_states.c.state_id).label("mx")).where(
        _states.c.event_id.in_(event_ids), _states.c.skin == skin
    ).group_by(_states.c.event_id).subquery()
    rows = conn.execute(select(
        _states.c.event_id, _states.c.status, _states.c.is_live, _states.c.score_home,
        _states.c.score_away, _states.c.minute, _states.c.period, _states.c.time_remaining
    ).join(sub, _states.c.state_id == sub.c.mx)).all()
    return {r[0]: (r[1], bool(r[2]) if r[2] is not None else None, r[3], r[4], r[5], r[6], r[7])
            for r in rows}


def _last_periods_bulk(conn, event_ids, skin):
    if not event_ids:
        return {}
    sub = select(
        _periods.c.event_id, _periods.c.period_key, func.max(_periods.c.id).label("mx")
    ).where(_periods.c.event_id.in_(event_ids), _periods.c.skin == skin).group_by(
        _periods.c.event_id, _periods.c.period_key).subquery()
    rows = conn.execute(select(
        _periods.c.event_id, _periods.c.period_key, _periods.c.period_name,
        _periods.c.home_score, _periods.c.away_score
    ).join(sub, _periods.c.id == sub.c.mx)).all()
    out: Dict[str, Dict[Any, Any]] = {}
    for r in rows:
        out.setdefault(r[0], {})[r[1]] = (r[2], r[3], r[4])
    return out


def _last_odds_bulk(conn, event_ids, skin):
    if not event_ids:
        return {}
    sub = select(
        _odds.c.event_id, _odds.c.scope, _odds.c.market_id, _odds.c.selection_name,
        _odds.c.line, func.max(_odds.c.snap_id).label("mx")
    ).where(_odds.c.event_id.in_(event_ids), _odds.c.skin == skin).group_by(
        _odds.c.event_id, _odds.c.scope, _odds.c.market_id,
        _odds.c.selection_name, _odds.c.line).subquery()
    rows = conn.execute(select(
        _odds.c.event_id, _odds.c.scope, _odds.c.market_id, _odds.c.selection_name,
        _odds.c.line, _odds.c.price, _odds.c.is_suspended
    ).join(sub, _odds.c.snap_id == sub.c.mx)).all()
    out: Dict[str, Dict[Any, Any]] = {}
    for r in rows:
        out.setdefault(r[0], {})[(r[1], r[2], r[3], r[4])] = (
            r[5], bool(r[6]) if r[6] is not None else False)
    return out


# --------------------------------------------------------------------------- #
# Persist
# --------------------------------------------------------------------------- #
def persist_result(conn: Connection, result: Dict[str, Any]) -> int:
    skin = result.get("skin") or ""
    at = _dt(result.get("extracted_at"))
    events: List[Dict[str, Any]] = result.get("events") or []
    sport_name = next((e.get("sport") for e in events if e.get("sport")), None)

    run_id = conn.execute(_runs.insert().values(
        skin=skin, action=result.get("action"), sport=sport_name, url=result.get("url"),
        extracted_at=at, duration_seconds=result.get("scrape_duration_seconds"),
        event_count=result.get("event_count", len(events)),
        success=bool(result.get("success")), error=result.get("error"),
        template_version=result.get("template_version"),
    ).returning(_runs.c.run_id)).scalar()

    # Per-persist caches + batches: repeating dimensions are looked up once, and
    # the bulk facts are accumulated and inserted with one executemany each —
    # collapsing hundreds of per-row network round-trips (the Supabase-persist
    # slowness) into a handful.
    sport_cache: Dict[Any, Any] = {}
    country_cache: Dict[Any, Any] = {}
    league_cache: Dict[Any, Any] = {}
    market_cache: Dict[Any, Any] = {}
    team_cache: Dict[Any, Any] = {}
    odds_batch: List[dict] = []
    period_batch: List[dict] = []
    stat_batch: List[dict] = []
    # H2H games are inserted in one batch after the loop (each needs its returned
    # id for the period-scores FK), so accumulate (game-values, periods) together.
    h2h_game_batch: List[dict] = []
    h2h_periods_batch: List[List[dict]] = []
    h2hp_batch: List[dict] = []

    # Bulk-prefetch the change-only dedup state for every event at once (one query
    # each) instead of one round-trip per event.
    all_ids = [str(ev.get("event_id") or "").strip() for ev in events]
    all_ids = [i for i in all_ids if i]
    last_states = _last_states_bulk(conn, all_ids, skin)
    last_periods_all = _last_periods_bulk(conn, all_ids, skin)
    last_odds_all = _last_odds_bulk(conn, all_ids, skin)

    def _sport_c(sid, name):
        if sid is None:
            return None
        if sid not in sport_cache:
            sport_cache[sid] = _sport(conn, sid, name)
        return sport_cache[sid]

    def _country_c(name):
        if not name:
            return None
        if name not in country_cache:
            country_cache[name] = _country(conn, name)
        return country_cache[name]

    def _league_c(lid, name, sport_id, country_id):
        lid = _as_int(lid)
        if lid is None:
            return None
        if lid not in league_cache:
            league_cache[lid] = _league(conn, lid, name, sport_id, country_id)
        return league_cache[lid]

    def _market_c(name, mtype, raw_g):
        mkey = (name, mtype, _as_int(raw_g))
        if mkey not in market_cache:
            market_cache[mkey] = _market(conn, name, mtype, raw_g)
        return market_cache[mkey]

    def _team_c(name, sport_id, **kw):
        # Memoize per (backend_id, name, sport_id): the same team recurs across
        # events (home/away + H2H participants), so this avoids re-running the
        # SELECT(+backfill) round-trip for a team already resolved this persist.
        key = (kw.get("backend_id"), name, sport_id)
        if key not in team_cache:
            team_cache[key] = _team(conn, name, sport_id, **kw)
        return team_cache[key]

    for ev in events:
        event_id = str(ev.get("event_id") or "").strip()
        if not event_id:
            continue

        sport_id = _sport_c(_as_int(ev.get("sport_id")), ev.get("sport"))
        country_id = _country_c(ev.get("country"))
        league_id = _league_c(ev.get("league_id"), ev.get("competition"), sport_id, country_id)
        home_id = _team_c(ev.get("home"), sport_id, country_id=country_id,
                          feed_id=_as_int(ev.get("home_team_feed_id")), image=ev.get("home_team_image"),
                          feed_country_id=_as_int(ev.get("home_team_country_id")))
        away_id = _team_c(ev.get("away"), sport_id, country_id=country_id,
                          feed_id=_as_int(ev.get("away_team_feed_id")), image=ev.get("away_team_image"),
                          feed_country_id=_as_int(ev.get("away_team_country_id")))

        estmt = _ins(conn)(_events).values(
            event_id=event_id, sport_id=sport_id, league_id=league_id, country_id=country_id,
            home_team_id=home_id, away_team_id=away_id, home_name=ev.get("home"),
            away_name=ev.get("away"), start_time=_dt(ev.get("start_time")),
            venue=ev.get("venue"), stage=ev.get("stage"), first_seen=at, last_seen=at)
        estmt = estmt.on_conflict_do_update(index_elements=["event_id"], set_={
            "sport_id": func.coalesce(estmt.excluded.sport_id, _events.c.sport_id),
            "league_id": func.coalesce(estmt.excluded.league_id, _events.c.league_id),
            "country_id": func.coalesce(estmt.excluded.country_id, _events.c.country_id),
            "home_team_id": func.coalesce(estmt.excluded.home_team_id, _events.c.home_team_id),
            "away_team_id": func.coalesce(estmt.excluded.away_team_id, _events.c.away_team_id),
            "start_time": func.coalesce(estmt.excluded.start_time, _events.c.start_time),
            "venue": func.coalesce(estmt.excluded.venue, _events.c.venue),
            "stage": func.coalesce(estmt.excluded.stage, _events.c.stage),
            "last_seen": estmt.excluded.last_seen})
        conn.execute(estmt)

        # facts: live state (only when changed)
        state = (ev.get("status"), bool(ev.get("is_live")), _as_int(ev.get("score_home")),
                 _as_int(ev.get("score_away")), _as_int(ev.get("minute")),
                 ev.get("period"), ev.get("time_remaining"))
        if last_states.get(event_id) != state:
            conn.execute(_states.insert().values(
                run_id=run_id, event_id=event_id, skin=skin, status=state[0], is_live=state[1],
                score_home=state[2], score_away=state[3], minute=state[4], period=state[5],
                time_remaining=state[6], wp_home=ev.get("wp_home"), wp_away=ev.get("wp_away"),
                captured_at=at))

        # facts: period scores (only changed) → batch
        last_periods = last_periods_all.get(event_id, {})
        for ps in ev.get("period_scores") or []:
            pk = _as_int(ps.get("period_key"))
            row = (ps.get("period_name"), _as_int(ps.get("home_score")), _as_int(ps.get("away_score")))
            if last_periods.get(pk) == row:
                continue
            period_batch.append(dict(
                run_id=run_id, event_id=event_id, skin=skin, period_key=pk, period_name=row[0],
                home_score=row[1], away_score=row[2], captured_at=at))
            last_periods[pk] = row

        # facts: odds (only when a selection's price/suspension changed) → batch
        last_odds = last_odds_all.get(event_id, {})
        for m in ev.get("markets") or []:
            market_id = _market_c(m.get("name"), m.get("market_type"), m.get("raw_g"))
            scope = m.get("scope") or "FULL_MATCH"
            for s in m.get("selections") or []:
                price = s.get("price")
                if price is None:
                    continue
                price = float(price)
                susp = bool(s.get("is_suspended"))
                key = (scope, market_id, s.get("name"), s.get("line"))
                if last_odds.get(key) == (price, susp):
                    continue
                odds_batch.append(dict(
                    run_id=run_id, event_id=event_id, skin=skin, market_id=market_id,
                    selection_name=s.get("name"), line=s.get("line"), price=price,
                    is_suspended=susp, raw_t=_as_int(s.get("raw_t")), scope=scope, captured_at=at))
                last_odds[key] = (price, susp)

        # facts: H2H (+ enrich teams dim). Games are accumulated and inserted in
        # one batch after the loop — each game's periods carry the game's list
        # index so they can be re-linked to the returned id (see the flush below).
        h2h = ev.get("h2h_data")
        if h2h:
            for t in h2h.get("teams") or []:
                tc = t.get("country") or {}
                _team_c(t.get("title"), _as_int(h2h.get("sport_id")) or sport_id,
                        backend_id=str(t.get("id")) if t.get("id") else None,
                        country_id=_country_c(tc.get("title")))
            for g in h2h.get("game_shorts") or []:
                h2h_game_batch.append(dict(
                    run_id=run_id, event_id=event_id, skin=skin, game_id=g.get("game_id"),
                    sport_id=_as_int(h2h.get("sport_id")), team1_backend_id=g.get("team1_id"),
                    team2_backend_id=g.get("team2_id"), date_start=_dt(g.get("date_start")),
                    score1=_as_int(g.get("score1")), score2=_as_int(g.get("score2")),
                    sub_score1=_as_int(g.get("sub_score1")), sub_score2=_as_int(g.get("sub_score2")),
                    winner=_as_int(g.get("winner")), status=_as_int(g.get("status")), captured_at=at))
                h2h_periods_batch.append([
                    dict(event_id=event_id,
                         period_key=_as_int(ps.get("period_key")), period_name=ps.get("period_name"),
                         home_score=_as_int(ps.get("home_score")), away_score=_as_int(ps.get("away_score")))
                    for ps in g.get("periods") or []])

        # dimension: sub-games (SG[] — named per-period/per-stat groups) → upsert
        for sg in ev.get("sub_games") or []:
            sgid = str(sg.get("sub_game_id") or "").strip()
            if not sgid:
                continue
            sstmt = _ins(conn)(_subgames).values(
                sub_game_id=sgid, event_id=event_id, name=sg.get("name"),
                period=sg.get("period"), period_index=_as_int(sg.get("period_index")),
                market_count=_as_int(sg.get("market_count")),
                sport_id=_as_int(sg.get("sport_id")), first_seen=at, last_seen=at)
            sstmt = sstmt.on_conflict_do_update(index_elements=["sub_game_id"], set_={
                "event_id": sstmt.excluded.event_id,
                "name": func.coalesce(sstmt.excluded.name, _subgames.c.name),
                "period": func.coalesce(sstmt.excluded.period, _subgames.c.period),
                "period_index": func.coalesce(sstmt.excluded.period_index, _subgames.c.period_index),
                "market_count": func.coalesce(sstmt.excluded.market_count, _subgames.c.market_count),
                "sport_id": func.coalesce(sstmt.excluded.sport_id, _subgames.c.sport_id),
                "last_seen": sstmt.excluded.last_seen})
            conn.execute(sstmt)

        # facts: statistics (flatten name/value) → batch
        for st in ev.get("statistics") or []:
            if isinstance(st, dict):
                for k, v in st.items():
                    stat_batch.append(dict(
                        run_id=run_id, event_id=event_id, skin=skin,
                        name=str(k), value=str(v), captured_at=at))

    # One executemany per fact type — the big round-trip saving.
    if period_batch:
        conn.execute(_periods.insert(), period_batch)
    if odds_batch:
        conn.execute(_odds.insert(), odds_batch)
    # H2H games in one batched INSERT...RETURNING (was one round-trip per game).
    # SQLAlchemy's insertmanyvalues returns ids in input order, so zip them back
    # to each game's periods to fill the FK.
    if h2h_game_batch:
        ids = conn.execute(_h2h.insert().returning(_h2h.c.id), h2h_game_batch).scalars().all()
        for game_id, periods in zip(ids, h2h_periods_batch):
            for p in periods:
                h2hp_batch.append(dict(h2h_game_id=game_id, **p))
    if h2hp_batch:
        conn.execute(_h2hp.insert(), h2hp_batch)
    if stat_batch:
        conn.execute(_stats.insert(), stat_batch)
    conn.commit()
    logger.info("persist run %s (skin=%s): %d events, %d odds → Postgres",
                run_id, skin, len(events), len(odds_batch))
    return run_id


# --------------------------------------------------------------------------- #
# Control-plane jobs
# --------------------------------------------------------------------------- #
def create_job(conn, *, skin, action, sport=None, subgames=False, count=None, created_by=None) -> int:
    jid = conn.execute(_jobs.insert().values(
        skin=skin, sport=sport, action=action, subgames=bool(subgames), count=count,
        status="queued", created_at=datetime.now(timezone.utc), created_by=created_by
    ).returning(_jobs.c.job_id)).scalar()
    conn.commit()
    return jid


def claim_next_job(conn):
    if conn.execute(select(_jobs.c.job_id).where(_jobs.c.status == "running").limit(1)).first():
        return None
    row = conn.execute(select(_jobs.c.job_id).where(_jobs.c.status == "queued")
                       .order_by(_jobs.c.job_id).limit(1)).first()
    if not row:
        return None
    conn.execute(_jobs.update().where(_jobs.c.job_id == row[0], _jobs.c.status == "queued").values(
        status="running", phase="starting", started_at=datetime.now(timezone.utc)))
    conn.commit()
    return get_job(conn, row[0])


def update_job_phase(conn, job_id, phase) -> None:
    conn.execute(_jobs.update().where(_jobs.c.job_id == job_id, _jobs.c.status == "running")
                 .values(phase=phase))
    conn.commit()


def finish_job(conn, job_id, *, status, run_id=None, event_count=None, error=None) -> None:
    values = dict(status=status, finished_at=datetime.now(timezone.utc),
                  run_id=run_id, event_count=event_count, error=error)
    if status == "succeeded":
        values["phase"] = "done"
    conn.execute(_jobs.update().where(_jobs.c.job_id == job_id).values(**values))
    conn.commit()


def reset_orphan_jobs(conn) -> int:
    n = conn.execute(select(func.count()).select_from(_jobs)
                     .where(_jobs.c.status == "running")).scalar() or 0
    if n:
        conn.execute(_jobs.update().where(_jobs.c.status == "running").values(
            status="failed", finished_at=datetime.now(timezone.utc),
            error="interrupted (service restart)"))
        conn.commit()
    return int(n)


def _job_dict(row) -> Optional[dict]:
    return dict(row._mapping) if row is not None else None


def events_last_seen(conn, event_ids):
    ids = [str(e) for e in event_ids]
    if not ids:
        return {}
    rows = conn.execute(select(_events.c.event_id, _events.c.last_seen)
                        .where(_events.c.event_id.in_(ids))).all()
    return {r[0]: r[1] for r in rows}


def get_job(conn, job_id):
    return _job_dict(conn.execute(select(_jobs).where(_jobs.c.job_id == job_id)).first())


def list_jobs(conn, *, limit=50, status=None):
    q = select(_jobs)
    if status:
        q = q.where(_jobs.c.status == status)
    q = q.order_by(_jobs.c.job_id.desc()).limit(limit)
    return [dict(r._mapping) for r in conn.execute(q).all()]


# --------------------------------------------------------------------------- #
# Queries
# --------------------------------------------------------------------------- #
def events_needing_results(conn, *, min_age_seconds: float = 9000.0, limit: int = 200):
    """(event_id, stat_game_id) for real matches that should have finished
    (start_time older than min_age, default 2.5h) and have no result yet —
    the results pass's work list (ADR-16/20). Oldest first."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=min_age_seconds)
    rows = conn.execute(
        select(_events.c.event_id, _events.c.stat_game_id).where(
            _events.c.away_team_id.isnot(None),   # a real H2H match, not an outright
            _events.c.start_time.isnot(None),
            _events.c.start_time < cutoff,
            _events.c.result_status.is_(None),     # not yet resolved
        ).order_by(_events.c.start_time).limit(limit)
    ).all()
    return [(r[0], r[1]) for r in rows]


def record_result(conn, event_id, *, stat_game_id=None, score_home=None,
                  score_away=None, winner=None, status=None, at=None) -> None:
    """Write a match's statisticfeed result onto the event (ADR-20). `stat_game_id`
    is captured whenever seen; the final score/winner/status are stamped only on
    `status == 3` (finished) — which also removes it from `events_needing_results`."""
    vals: Dict[str, Any] = {}
    if stat_game_id:
        vals["stat_game_id"] = str(stat_game_id)
    if status == 3:
        vals.update(final_score_home=_as_int(score_home), final_score_away=_as_int(score_away),
                    winner=_as_int(winner), result_status=3, result_captured_at=_dt(at))
    if not vals:
        return
    conn.execute(_events.update().where(_events.c.event_id == str(event_id)).values(**vals))
    conn.commit()


def counts(conn) -> Dict[str, int]:
    tables = [_sports, _countries, _leagues, _teams, _events, _markets, _subgames, _runs,
              _states, _periods, _odds, _h2h, _h2hp, _stats]
    return {t.name: conn.execute(select(func.count()).select_from(t)).scalar() for t in tables}


def latest_odds(conn, event_id, *, skin=None):
    sub = select(_odds.c.scope, _odds.c.market_id, _odds.c.selection_name, _odds.c.line,
                 func.max(_odds.c.snap_id).label("mx")).where(_odds.c.event_id == event_id)
    if skin:
        sub = sub.where(_odds.c.skin == skin)
    sub = sub.group_by(_odds.c.scope, _odds.c.market_id, _odds.c.selection_name, _odds.c.line).subquery()
    q = select(_odds).join(sub, _odds.c.snap_id == sub.c.mx)
    return [dict(r._mapping) for r in conn.execute(q).all()]
