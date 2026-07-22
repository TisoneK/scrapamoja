"""SQLite store for BetB2B scrape results — the full match model, not just odds.

One database for all of betb2b (``skin`` is a column, never a separate DB). The
match universe (sports, countries, leagues, teams, events, markets) is shared
across skins — every skin reports the same backend ``event_id`` (verified
Session 25) — so those are **dimension** tables with no ``skin`` column, UPSERT-ed
to one row per real entity. Everything a *skin observed at a moment* (scores,
odds, period breakdowns, H2H, stats) is a **fact** table carrying ``skin`` +
``captured_at``, appended as a time-series.

Schema (ADR-6, revised):

  dimensions          facts (skin-scoped, time-series)
  ----------          -------------------------------
  sports              scrape_runs      one row per persist_result()
  countries           event_states     status/score/minute/period per run
  leagues             period_scores    per-quarter breakdown per run
  teams               odds_snapshots   one price per selection per run
  events              h2h_games        historical head-to-head matches
  markets             statistics       flattened stat rows

Input is the plain ``BetB2BScrapeResult.to_dict()`` dict, so it works on live
scrapes and on saved JSON alike. SQLite first (stdlib, one file); the schema is
Postgres-portable (TEXT/INTEGER/REAL, ISO-8601 timestamps, explicit FKs).
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "init_db",
    "persist_result",
    "latest_odds",
    "line_movement",
    "cross_skin_odds",
    "counts",
]

PathLike = str | Path

SCHEMA = """
-- ------------------------------------------------------------------ --
-- Dimensions (skin-agnostic — one row per real entity, UPSERT-ed)     --
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS sports (
    sport_id  INTEGER PRIMARY KEY,          -- the backend SI (3=basketball)
    name      TEXT,
    slug      TEXT
);

CREATE TABLE IF NOT EXISTS countries (
    country_id  INTEGER PRIMARY KEY,        -- surrogate
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS leagues (
    league_id   INTEGER PRIMARY KEY,        -- the backend LI
    name        TEXT,
    sport_id    INTEGER REFERENCES sports(sport_id),
    country_id  INTEGER REFERENCES countries(country_id)
);

CREATE TABLE IF NOT EXISTS teams (
    team_id     INTEGER PRIMARY KEY,        -- surrogate
    backend_id  TEXT UNIQUE,                -- the h2h hash id when known
    name        TEXT NOT NULL,
    sport_id    INTEGER REFERENCES sports(sport_id),
    country_id  INTEGER REFERENCES countries(country_id),
    UNIQUE(name, sport_id)
);

CREATE TABLE IF NOT EXISTS events (
    event_id      TEXT PRIMARY KEY,         -- the backend event id (shared across skins)
    sport_id      INTEGER REFERENCES sports(sport_id),
    league_id     INTEGER REFERENCES leagues(league_id),
    country_id    INTEGER REFERENCES countries(country_id),
    home_team_id  INTEGER REFERENCES teams(team_id),
    away_team_id  INTEGER REFERENCES teams(team_id),
    home_name     TEXT,                     -- denormalized for convenience
    away_name     TEXT,
    start_time    TEXT,
    first_seen    TEXT,
    last_seen     TEXT
);

CREATE TABLE IF NOT EXISTS markets (
    market_id    INTEGER PRIMARY KEY,       -- surrogate
    name         TEXT,
    market_type  TEXT,
    raw_g        INTEGER
);

-- ------------------------------------------------------------------ --
-- Facts (skin-scoped time-series, append-only)                        --
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id            INTEGER PRIMARY KEY,
    skin              TEXT NOT NULL,
    action            TEXT,
    sport             TEXT,
    url               TEXT,
    extracted_at      TEXT NOT NULL,
    duration_seconds  REAL,
    event_count       INTEGER,
    success           INTEGER,
    error             TEXT,
    template_version  TEXT
);

CREATE TABLE IF NOT EXISTS event_states (
    state_id        INTEGER PRIMARY KEY,
    run_id          INTEGER NOT NULL REFERENCES scrape_runs(run_id),
    event_id        TEXT NOT NULL REFERENCES events(event_id),
    skin            TEXT NOT NULL,
    status          TEXT,
    is_live         INTEGER,
    score_home      INTEGER,
    score_away      INTEGER,
    minute          INTEGER,
    period          TEXT,
    time_remaining  TEXT,
    captured_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS period_scores (
    id           INTEGER PRIMARY KEY,
    run_id       INTEGER NOT NULL REFERENCES scrape_runs(run_id),
    event_id     TEXT NOT NULL REFERENCES events(event_id),
    skin         TEXT NOT NULL,
    period_key   INTEGER,
    period_name  TEXT,
    home_score   INTEGER,
    away_score   INTEGER,
    captured_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS odds_snapshots (
    snap_id         INTEGER PRIMARY KEY,
    run_id          INTEGER NOT NULL REFERENCES scrape_runs(run_id),
    event_id        TEXT NOT NULL REFERENCES events(event_id),
    skin            TEXT NOT NULL,
    market_id       INTEGER REFERENCES markets(market_id),
    selection_name  TEXT,
    line            REAL,
    price           REAL NOT NULL,
    is_suspended    INTEGER,
    raw_t           INTEGER,
    scope           TEXT DEFAULT 'FULL_MATCH',
    captured_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS h2h_games (
    id                 INTEGER PRIMARY KEY,
    run_id             INTEGER NOT NULL REFERENCES scrape_runs(run_id),
    event_id           TEXT NOT NULL REFERENCES events(event_id),
    skin               TEXT NOT NULL,
    game_id            TEXT,
    sport_id           INTEGER,
    team1_backend_id   TEXT,
    team2_backend_id   TEXT,
    date_start         TEXT,
    score1             INTEGER,
    score2             INTEGER,
    sub_score1         INTEGER,
    sub_score2         INTEGER,
    winner             INTEGER,
    status             INTEGER,
    captured_at        TEXT NOT NULL
);

-- Per-quarter breakdown of a historical H2H game — the raw material for
-- scoped ingestion (QUARTER_n / FIRST_HALF / SECOND_HALF H2H scores). The
-- feed's game_shorts[].periods[] carries this; the pipeline needs H2H scores
-- that match the prediction scope (ADR-7).
CREATE TABLE IF NOT EXISTS h2h_period_scores (
    id           INTEGER PRIMARY KEY,
    h2h_game_id  INTEGER NOT NULL REFERENCES h2h_games(id),
    event_id     TEXT,
    period_key   INTEGER,
    period_name  TEXT,
    home_score   INTEGER,
    away_score   INTEGER
);

CREATE TABLE IF NOT EXISTS statistics (
    id           INTEGER PRIMARY KEY,
    run_id       INTEGER NOT NULL REFERENCES scrape_runs(run_id),
    event_id     TEXT NOT NULL REFERENCES events(event_id),
    skin         TEXT NOT NULL,
    name         TEXT,
    value        TEXT,
    captured_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_events_league   ON events(league_id);
CREATE INDEX IF NOT EXISTS ix_events_sport     ON events(sport_id);
CREATE INDEX IF NOT EXISTS ix_states_event     ON event_states(event_id, captured_at);
CREATE INDEX IF NOT EXISTS ix_periods_event    ON period_scores(event_id, captured_at);
CREATE INDEX IF NOT EXISTS ix_odds_event       ON odds_snapshots(event_id, skin, captured_at);
CREATE INDEX IF NOT EXISTS ix_odds_market      ON odds_snapshots(event_id, skin, market_id, selection_name, captured_at);
CREATE INDEX IF NOT EXISTS ix_h2h_event        ON h2h_games(event_id);
"""


def init_db(path: PathLike) -> sqlite3.Connection:
    """Open (creating if needed) the store and ensure the schema."""
    p = Path(path)
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def _as_int(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None and str(v) != "" else None
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Dimension get-or-create helpers (SELECT-then-INSERT — NULL-safe UPSERT)
# --------------------------------------------------------------------------- #
def _upsert_sport(conn, sport_id: Optional[int], name: Optional[str]) -> Optional[int]:
    if sport_id is None:
        return None
    conn.execute(
        "INSERT INTO sports (sport_id, name, slug) VALUES (?,?,?) "
        "ON CONFLICT(sport_id) DO UPDATE SET name=COALESCE(excluded.name, sports.name), "
        "slug=COALESCE(excluded.slug, sports.slug)",
        (sport_id, name, (name or "").lower() or None),
    )
    return sport_id


def _get_or_create_country(conn, name: Optional[str]) -> Optional[int]:
    if not name:
        return None
    row = conn.execute("SELECT country_id FROM countries WHERE name=?", (name,)).fetchone()
    if row:
        return row["country_id"]
    return int(conn.execute("INSERT INTO countries (name) VALUES (?)", (name,)).lastrowid)


def _upsert_league(conn, league_id, name, sport_id, country_id) -> Optional[int]:
    league_id = _as_int(league_id)
    if league_id is None:
        return None
    conn.execute(
        "INSERT INTO leagues (league_id, name, sport_id, country_id) VALUES (?,?,?,?) "
        "ON CONFLICT(league_id) DO UPDATE SET "
        "name=COALESCE(excluded.name, leagues.name), "
        "sport_id=COALESCE(excluded.sport_id, leagues.sport_id), "
        "country_id=COALESCE(excluded.country_id, leagues.country_id)",
        (league_id, name, sport_id, country_id),
    )
    return league_id


def _get_or_create_team(
    conn, name: Optional[str], sport_id: Optional[int],
    *, backend_id: Optional[str] = None, country_id: Optional[int] = None,
) -> Optional[int]:
    if backend_id:
        row = conn.execute("SELECT team_id FROM teams WHERE backend_id=?", (backend_id,)).fetchone()
        if row:
            if name:  # enrich name/country if we now know them
                conn.execute(
                    "UPDATE teams SET name=COALESCE(?, name), country_id=COALESCE(?, country_id) "
                    "WHERE team_id=?", (name, country_id, row["team_id"]),
                )
            return row["team_id"]
    if not name:
        return None
    row = conn.execute(
        "SELECT team_id, backend_id FROM teams WHERE name=? AND sport_id IS ?",
        (name, sport_id),
    ).fetchone()
    if row:
        if backend_id and not row["backend_id"]:  # backfill backend id/country
            conn.execute(
                "UPDATE teams SET backend_id=?, country_id=COALESCE(?, country_id) WHERE team_id=?",
                (backend_id, country_id, row["team_id"]),
            )
        return row["team_id"]
    return int(conn.execute(
        "INSERT INTO teams (backend_id, name, sport_id, country_id) VALUES (?,?,?,?)",
        (backend_id, name, sport_id, country_id),
    ).lastrowid)


def _get_or_create_market(conn, name, market_type, raw_g) -> int:
    raw_g = _as_int(raw_g)
    row = conn.execute(
        "SELECT market_id FROM markets WHERE name IS ? AND market_type IS ? AND raw_g IS ?",
        (name, market_type, raw_g),
    ).fetchone()
    if row:
        return row["market_id"]
    return int(conn.execute(
        "INSERT INTO markets (name, market_type, raw_g) VALUES (?,?,?)",
        (name, market_type, raw_g),
    ).lastrowid)


# --------------------------------------------------------------------------- #
# "Last stored value" lookups — for change-only dedup (record movement, not
# heartbeats: a fast poll otherwise writes thousands of identical rows).
# --------------------------------------------------------------------------- #
def _last_odds(conn, event_id: str, skin: str) -> Dict[tuple, tuple]:
    """Latest (price, is_suspended) per (scope, market_id, selection, line) for a skin."""
    rows = conn.execute(
        "SELECT scope, market_id, selection_name, line, price, is_suspended, MAX(snap_id) "
        "FROM odds_snapshots WHERE event_id=? AND skin=? "
        "GROUP BY scope, market_id, selection_name, line",
        (event_id, skin),
    ).fetchall()
    return {(r["scope"], r["market_id"], r["selection_name"], r["line"]): (r["price"], r["is_suspended"])
            for r in rows}


def _last_state(conn, event_id: str, skin: str) -> Optional[tuple]:
    """The most recent observable state tuple for a skin (None if never seen)."""
    r = conn.execute(
        "SELECT status, is_live, score_home, score_away, minute, period, time_remaining "
        "FROM event_states WHERE event_id=? AND skin=? ORDER BY state_id DESC LIMIT 1",
        (event_id, skin),
    ).fetchone()
    return tuple(r) if r else None


def _last_periods(conn, event_id: str, skin: str) -> Dict[Any, tuple]:
    """Latest (period_name, home, away) per period_key for a skin."""
    rows = conn.execute(
        "SELECT period_key, period_name, home_score, away_score, MAX(id) "
        "FROM period_scores WHERE event_id=? AND skin=? GROUP BY period_key",
        (event_id, skin),
    ).fetchall()
    return {r["period_key"]: (r["period_name"], r["home_score"], r["away_score"]) for r in rows}


# --------------------------------------------------------------------------- #
# Persist
# --------------------------------------------------------------------------- #
def persist_result(
    result: Dict[str, Any], path: PathLike, *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """Persist one ``BetB2BScrapeResult.to_dict()`` payload; return the run_id.

    Dimensions (sports/countries/leagues/teams/events/markets) are UPSERT-ed to
    one row per entity; the fact tables are appended (time-series per run). Pass
    an open ``conn`` to reuse a connection; otherwise one is opened + closed.
    """
    owns = conn is None
    conn = conn or init_db(path)
    try:
        skin = result.get("skin") or ""
        at = result.get("extracted_at") or ""
        events: List[Dict[str, Any]] = result.get("events") or []
        sport_name = next((e.get("sport") for e in events if e.get("sport")), None)
        odds_ins = odds_skip = 0  # change-only dedup counters

        run_id = int(conn.execute(
            "INSERT INTO scrape_runs "
            "(skin, action, sport, url, extracted_at, duration_seconds, "
            " event_count, success, error, template_version) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (skin, result.get("action"), sport_name, result.get("url"), at,
             result.get("scrape_duration_seconds"), result.get("event_count", len(events)),
             1 if result.get("success") else 0, result.get("error"),
             result.get("template_version")),
        ).lastrowid)

        for ev in events:
            event_id = str(ev.get("event_id") or "").strip()
            if not event_id:
                continue

            # --- dimensions ---
            sport_id = _upsert_sport(conn, _as_int(ev.get("sport_id")), ev.get("sport"))
            country_id = _get_or_create_country(conn, ev.get("country"))
            league_id = _upsert_league(
                conn, ev.get("league_id"), ev.get("competition"), sport_id, country_id)
            home_id = _get_or_create_team(conn, ev.get("home"), sport_id, country_id=country_id)
            away_id = _get_or_create_team(conn, ev.get("away"), sport_id, country_id=country_id)

            conn.execute(
                "INSERT INTO events "
                "(event_id, sport_id, league_id, country_id, home_team_id, away_team_id, "
                " home_name, away_name, start_time, first_seen, last_seen) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(event_id) DO UPDATE SET "
                "  sport_id=COALESCE(excluded.sport_id, events.sport_id), "
                "  league_id=COALESCE(excluded.league_id, events.league_id), "
                "  country_id=COALESCE(excluded.country_id, events.country_id), "
                "  home_team_id=COALESCE(excluded.home_team_id, events.home_team_id), "
                "  away_team_id=COALESCE(excluded.away_team_id, events.away_team_id), "
                "  start_time=COALESCE(excluded.start_time, events.start_time), "
                "  last_seen=excluded.last_seen",
                (event_id, sport_id, league_id, country_id, home_id, away_id,
                 ev.get("home"), ev.get("away"), ev.get("start_time"), at, at),
            )

            # --- facts: live state (only when it changed) ---
            state = (ev.get("status"), 1 if ev.get("is_live") else 0,
                     _as_int(ev.get("score_home")), _as_int(ev.get("score_away")),
                     _as_int(ev.get("minute")), ev.get("period"), ev.get("time_remaining"))
            if _last_state(conn, event_id, skin) != state:
                conn.execute(
                    "INSERT INTO event_states "
                    "(run_id, event_id, skin, status, is_live, score_home, score_away, "
                    " minute, period, time_remaining, captured_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (run_id, event_id, skin, *state, at),
                )

            # --- facts: per-period scores (only changed periods) ---
            last_periods = _last_periods(conn, event_id, skin)
            for ps in ev.get("period_scores") or []:
                pk = _as_int(ps.get("period_key"))
                row = (ps.get("period_name"), _as_int(ps.get("home_score")), _as_int(ps.get("away_score")))
                if last_periods.get(pk) == row:
                    continue
                conn.execute(
                    "INSERT INTO period_scores "
                    "(run_id, event_id, skin, period_key, period_name, home_score, away_score, captured_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (run_id, event_id, skin, pk, *row, at),
                )
                last_periods[pk] = row

            # --- facts: odds (only when a selection's price/suspension changed) ---
            last_odds = _last_odds(conn, event_id, skin)
            for m in ev.get("markets") or []:
                market_id = _get_or_create_market(conn, m.get("name"), m.get("market_type"), m.get("raw_g"))
                scope = m.get("scope") or "FULL_MATCH"
                for s in m.get("selections") or []:
                    price = s.get("price")
                    if price is None:
                        continue
                    price = float(price)
                    susp = 1 if s.get("is_suspended") else 0
                    key = (scope, market_id, s.get("name"), s.get("line"))
                    if last_odds.get(key) == (price, susp):
                        odds_skip += 1
                        continue
                    conn.execute(
                        "INSERT INTO odds_snapshots "
                        "(run_id, event_id, skin, market_id, selection_name, line, price, "
                        " is_suspended, raw_t, scope, captured_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (run_id, event_id, skin, market_id, s.get("name"), s.get("line"),
                         price, susp, _as_int(s.get("raw_t")), scope, at),
                    )
                    last_odds[key] = (price, susp)
                    odds_ins += 1

            # --- facts: H2H (+ enrich teams dim from h2h team metadata) ---
            h2h = ev.get("h2h_data")
            if h2h:
                for t in h2h.get("teams") or []:
                    tc = t.get("country") or {}
                    _get_or_create_team(
                        conn, t.get("title"), _as_int(h2h.get("sport_id")) or sport_id,
                        backend_id=str(t.get("id")) if t.get("id") else None,
                        country_id=_get_or_create_country(conn, tc.get("title")),
                    )
                for g in h2h.get("game_shorts") or []:
                    h2h_game_id = int(conn.execute(
                        "INSERT INTO h2h_games "
                        "(run_id, event_id, skin, game_id, sport_id, team1_backend_id, "
                        " team2_backend_id, date_start, score1, score2, sub_score1, "
                        " sub_score2, winner, status, captured_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (run_id, event_id, skin, g.get("game_id"), _as_int(h2h.get("sport_id")),
                         g.get("team1_id"), g.get("team2_id"), g.get("date_start"),
                         _as_int(g.get("score1")), _as_int(g.get("score2")),
                         _as_int(g.get("sub_score1")), _as_int(g.get("sub_score2")),
                         _as_int(g.get("winner")), _as_int(g.get("status")), at),
                    ).lastrowid)
                    # Per-quarter H2H breakdown → scoped ingestion (ADR-7).
                    for ps in g.get("periods") or []:
                        conn.execute(
                            "INSERT INTO h2h_period_scores "
                            "(h2h_game_id, event_id, period_key, period_name, home_score, away_score) "
                            "VALUES (?,?,?,?,?,?)",
                            (h2h_game_id, event_id, _as_int(ps.get("period_key")),
                             ps.get("period_name"), _as_int(ps.get("home_score")),
                             _as_int(ps.get("away_score"))),
                        )

            # --- facts: statistics (flatten name/value dicts) ---
            for st in ev.get("statistics") or []:
                if isinstance(st, dict):
                    for k, v in st.items():
                        conn.execute(
                            "INSERT INTO statistics (run_id, event_id, skin, name, value, captured_at) "
                            "VALUES (?,?,?,?,?,?)",
                            (run_id, event_id, skin, str(k), str(v), at),
                        )
        conn.commit()
        logger.info(
            "persist run %d (skin=%s): %d odds changes stored, %d unchanged skipped",
            run_id, skin, odds_ins, odds_skip,
        )
        return run_id
    finally:
        if owns:
            conn.close()


# --------------------------------------------------------------------------- #
# Read helpers
# --------------------------------------------------------------------------- #
def latest_odds(conn, event_id: str, *, skin: Optional[str] = None) -> List[sqlite3.Row]:
    """Most recent price per (skin, market, selection) for one event."""
    sql = (
        "SELECT o.skin, m.name AS market_name, o.selection_name, o.line, o.price, "
        "       o.is_suspended, MAX(o.captured_at) AS captured_at "
        "FROM odds_snapshots o JOIN markets m ON m.market_id=o.market_id "
        "WHERE o.event_id=? " + ("AND o.skin=? " if skin else "")
        + "GROUP BY o.skin, m.name, o.selection_name, o.line "
        "ORDER BY o.skin, m.name, o.selection_name"
    )
    return conn.execute(sql, (event_id, skin) if skin else (event_id,)).fetchall()


def line_movement(conn, event_id, skin, market_name, selection_name) -> List[sqlite3.Row]:
    """Full price history for one selection — the line-movement series."""
    return conn.execute(
        "SELECT o.captured_at, o.price, o.is_suspended FROM odds_snapshots o "
        "JOIN markets m ON m.market_id=o.market_id "
        "WHERE o.event_id=? AND o.skin=? AND m.name=? AND o.selection_name=? "
        "ORDER BY o.captured_at",
        (event_id, skin, market_name, selection_name),
    ).fetchall()


def cross_skin_odds(conn, event_id, market_name, selection_name) -> List[sqlite3.Row]:
    """Latest price for one selection across every skin — ascending, best last."""
    return conn.execute(
        "SELECT o.skin, o.price, o.line, MAX(o.captured_at) AS captured_at "
        "FROM odds_snapshots o JOIN markets m ON m.market_id=o.market_id "
        "WHERE o.event_id=? AND m.name=? AND o.selection_name=? "
        "GROUP BY o.skin ORDER BY o.price",
        (event_id, market_name, selection_name),
    ).fetchall()


def counts(conn) -> Dict[str, int]:
    """Row counts per table — a quick health/coverage summary."""
    tables = [
        "sports", "countries", "leagues", "teams", "events", "markets",
        "scrape_runs", "event_states", "period_scores", "odds_snapshots",
        "h2h_games", "h2h_period_scores", "statistics",
    ]
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
