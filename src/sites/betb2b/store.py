"""SQLite persistence for BetB2B scrape results — a real home for odds data.

Until now a scrape produced a standalone JSON blob (see :mod:`.storage`): it
overwrote nothing, deduped nothing, and was never queried. This module gives
the harvested events/odds a structured, time-series store so the downstream
odds-comparison use case is a query, not a JSON diff.

Design (see ADR-6):

* ``scrape_runs``    — one row per :func:`persist_result` call (provenance).
* ``events``         — one row per match, UPSERT-ed on ``event_id``. Because
  every BetB2B skin shares the same backend event ids (verified Session 25),
  one match is one row regardless of how many skins report it.
* ``event_states``   — time-series of an event's live state per run
  (status / score / minute / period).
* ``odds_snapshots`` — time-series of prices: one row per selection per run.
  This is where **line movement** and **cross-skin comparison** live.

The input is the plain dict from ``BetB2BScrapeResult.to_dict()`` (the same
JSON the CLI already emits), so this works on any saved output too.

SQLite is the first backend (stdlib, zero deps, one file). The schema avoids
SQLite-only types (TEXT/INTEGER/REAL only; timestamps are ISO-8601 TEXT) so
it ports to Postgres with only the id-column type changing.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = [
    "init_db",
    "persist_result",
    "latest_odds",
    "line_movement",
    "cross_skin_odds",
]

PathLike = str | Path

SCHEMA = """
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

CREATE TABLE IF NOT EXISTS events (
    event_id     TEXT PRIMARY KEY,
    sport        TEXT,
    sport_id     INTEGER,
    competition  TEXT,
    league_id    INTEGER,
    home         TEXT,
    away         TEXT,
    country      TEXT,
    start_time   TEXT,
    first_seen   TEXT,
    last_seen    TEXT
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

CREATE TABLE IF NOT EXISTS odds_snapshots (
    snap_id         INTEGER PRIMARY KEY,
    run_id          INTEGER NOT NULL REFERENCES scrape_runs(run_id),
    event_id        TEXT NOT NULL REFERENCES events(event_id),
    skin            TEXT NOT NULL,
    market_name     TEXT,
    market_type     TEXT,
    market_raw_g    INTEGER,
    selection_name  TEXT,
    line            REAL,
    price           REAL NOT NULL,
    is_suspended    INTEGER,
    raw_t           INTEGER,
    raw_g           INTEGER,
    captured_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_states_event   ON event_states(event_id, captured_at);
CREATE INDEX IF NOT EXISTS ix_odds_event     ON odds_snapshots(event_id, skin, captured_at);
CREATE INDEX IF NOT EXISTS ix_odds_selection ON odds_snapshots(event_id, skin, market_name, selection_name, captured_at);
"""


def init_db(path: PathLike) -> sqlite3.Connection:
    """Open (creating if needed) the SQLite store and ensure the schema."""
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


def persist_result(
    result: Dict[str, Any],
    path: PathLike,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """Persist one ``BetB2BScrapeResult.to_dict()`` payload; return the run_id.

    Idempotent on the event dimension (``events`` is UPSERT-ed); the state and
    odds rows are append-only time-series (one snapshot per run). Pass an open
    ``conn`` to reuse a connection (tests); otherwise one is opened + closed.
    """
    owns = conn is None
    conn = conn or init_db(path)
    try:
        skin = result.get("skin") or ""
        captured_at = result.get("extracted_at") or ""
        events: List[Dict[str, Any]] = result.get("events") or []
        # Infer sport from the first event (the CLI filters one sport per run).
        sport = next((e.get("sport") for e in events if e.get("sport")), None)

        cur = conn.execute(
            "INSERT INTO scrape_runs "
            "(skin, action, sport, url, extracted_at, duration_seconds, "
            " event_count, success, error, template_version) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                skin, result.get("action"), sport, result.get("url"),
                captured_at, result.get("scrape_duration_seconds"),
                result.get("event_count", len(events)),
                1 if result.get("success") else 0,
                result.get("error"), result.get("template_version"),
            ),
        )
        run_id = int(cur.lastrowid)

        for ev in events:
            event_id = str(ev.get("event_id") or "").strip()
            if not event_id:
                continue

            # UPSERT the match row (first_seen kept, last_seen bumped).
            conn.execute(
                "INSERT INTO events "
                "(event_id, sport, sport_id, competition, league_id, home, away, "
                " country, start_time, first_seen, last_seen) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(event_id) DO UPDATE SET "
                "  sport=excluded.sport, competition=excluded.competition, "
                "  home=excluded.home, away=excluded.away, "
                "  country=COALESCE(excluded.country, events.country), "
                "  start_time=COALESCE(excluded.start_time, events.start_time), "
                "  last_seen=excluded.last_seen",
                (
                    event_id, ev.get("sport"), _as_int(ev.get("sport_id")),
                    ev.get("competition"), _as_int(ev.get("league_id")),
                    ev.get("home"), ev.get("away"), ev.get("country"),
                    ev.get("start_time"), captured_at, captured_at,
                ),
            )

            # Time-series: live state this run.
            conn.execute(
                "INSERT INTO event_states "
                "(run_id, event_id, skin, status, is_live, score_home, score_away, "
                " minute, period, time_remaining, captured_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    run_id, event_id, skin, ev.get("status"),
                    1 if ev.get("is_live") else 0,
                    _as_int(ev.get("score_home")), _as_int(ev.get("score_away")),
                    _as_int(ev.get("minute")), ev.get("period"),
                    ev.get("time_remaining"), captured_at,
                ),
            )

            # Time-series: one odds row per selection.
            for m in ev.get("markets") or []:
                for s in m.get("selections") or []:
                    price = s.get("price")
                    if price is None:
                        continue
                    conn.execute(
                        "INSERT INTO odds_snapshots "
                        "(run_id, event_id, skin, market_name, market_type, "
                        " market_raw_g, selection_name, line, price, is_suspended, "
                        " raw_t, raw_g, captured_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            run_id, event_id, skin, m.get("name"),
                            m.get("market_type"), _as_int(m.get("raw_g")),
                            s.get("name"), s.get("line"), float(price),
                            1 if s.get("is_suspended") else 0,
                            _as_int(s.get("raw_t")), _as_int(s.get("raw_g")),
                            captured_at,
                        ),
                    )
        conn.commit()
        return run_id
    finally:
        if owns:
            conn.close()


# --------------------------------------------------------------------------- #
# Read helpers — the queries loose JSON couldn't answer
# --------------------------------------------------------------------------- #
def latest_odds(
    conn: sqlite3.Connection, event_id: str, *, skin: Optional[str] = None,
) -> List[sqlite3.Row]:
    """Most recent price per (skin, market, selection) for one event."""
    sql = (
        "SELECT skin, market_name, selection_name, line, price, is_suspended, "
        "       MAX(captured_at) AS captured_at "
        "FROM odds_snapshots WHERE event_id = ? "
        + ("AND skin = ? " if skin else "")
        + "GROUP BY skin, market_name, selection_name, line "
        "ORDER BY skin, market_name, selection_name"
    )
    params = (event_id, skin) if skin else (event_id,)
    return conn.execute(sql, params).fetchall()


def line_movement(
    conn: sqlite3.Connection, event_id: str, skin: str,
    market_name: str, selection_name: str,
) -> List[sqlite3.Row]:
    """Full price history for one selection — the line-movement series."""
    return conn.execute(
        "SELECT captured_at, price, is_suspended FROM odds_snapshots "
        "WHERE event_id=? AND skin=? AND market_name=? AND selection_name=? "
        "ORDER BY captured_at",
        (event_id, skin, market_name, selection_name),
    ).fetchall()


def cross_skin_odds(
    conn: sqlite3.Connection, event_id: str,
    market_name: str, selection_name: str,
) -> List[sqlite3.Row]:
    """Latest price for one selection across every skin — the comparison query.

    Returns the best (highest) price last, so the caller can pick the top line.
    """
    return conn.execute(
        "SELECT skin, price, line, MAX(captured_at) AS captured_at "
        "FROM odds_snapshots "
        "WHERE event_id=? AND market_name=? AND selection_name=? "
        "GROUP BY skin ORDER BY price",
        (event_id, market_name, selection_name),
    ).fetchall()
