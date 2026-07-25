"""Tests for the ADR-11 betb2b ORM models (src/sites/betb2b/models.py).

Verifies the portable schema: tables create on the SQLite fallback, the
ADR-11 hot-path indexes are present, the SQLite-isms are ported (Boolean for
success/is_live/is_suspended; BigInteger surrogate PKs; DateTime(timezone=True)
timestamps), and a persist-shaped insert round-trips on SQLite. DDL is also
compiled against the PostgreSQL dialect (without a live server) to prove
portability.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, select, Boolean, DateTime, Integer
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm import Session

from src.sites.betb2b.models import (
    Base, Event, OddsSnapshot, ScrapeRun, Sport, Market,
)


def _expected_tables():
    return {
        "sports", "countries", "leagues", "teams", "events", "markets",
        "scrape_runs", "event_states", "period_scores", "odds_snapshots",
        "h2h_games", "h2h_period_scores", "statistics",
    }


def _col(cols: list[dict], name: str) -> dict:
    """get_columns() returns a list of column dicts; pick one by name."""
    return next(c for c in cols if c["name"] == name)


def test_all_tables_create_on_sqlite():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    assert _expected_tables() <= set(insp.get_table_names())


def test_adr11_hot_path_indexes_exist():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    odds_ix = {i["name"] for i in insp.get_indexes("odds_snapshots")}
    events_ix = {i["name"] for i in insp.get_indexes("events")}
    # ADR-11: odds_snapshots(event_id, extracted_at) — captured_at is the
    # time-series column (same role as extracted_at in the ADR text).
    assert "ix_odds_event_extracted" in odds_ix
    # ADR-11: events(start_time)
    assert "ix_events_start_time" in events_ix


def test_sqlite_isms_ported_to_portable_types():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    insp = inspect(engine)

    # success / is_live / is_suspended are Boolean (were INTEGER 0/1)
    assert isinstance(_col(insp.get_columns("scrape_runs"), "success")["type"], Boolean)
    assert isinstance(_col(insp.get_columns("event_states"), "is_live")["type"], Boolean)
    assert isinstance(_col(insp.get_columns("odds_snapshots"), "is_suspended")["type"], Boolean)

    # surrogate PKs are BigInteger (resolved to INTEGER on sqlite, BIGINT on
    # pg — BigInteger is a subclass of Integer, so isinstance covers both).
    assert isinstance(_col(insp.get_columns("scrape_runs"), "run_id")["type"], Integer)
    assert isinstance(_col(insp.get_columns("odds_snapshots"), "snap_id")["type"], Integer)

    # timestamps are DateTime(timezone=True) (were TEXT). Reflection on SQLite
    # drops the timezone flag, so assert against the model declaration directly
    # — that's the source of truth that compiles to TIMESTAMP WITH TIME ZONE
    # on Postgres (verified in test_ddl_compiles_for_postgresql_dialect).
    assert isinstance(_col(insp.get_columns("events"), "start_time")["type"], DateTime)
    assert Event.__table__.c.start_time.type.timezone is True

    # event_id stays a natural TEXT key (the shared backend id)
    pk = insp.get_pk_constraint("events")["constrained_columns"]
    assert pk == ["event_id"]


def test_ddl_compiles_for_postgresql_dialect():
    # No live Postgres needed — compile each table's CREATE through the pg
    # dialect to prove no SQLite-only constructs survive. Should produce
    # BIGINT/BOOLEAN/TIMESTAMP WITH TIME ZONE, not INTEGER/TEXT/AUTOINCREMENT.
    ddl = "\n".join(
        str(CreateTable(t).compile(dialect=postgresql.dialect()))
        for t in Base.metadata.sorted_tables
    ).upper()
    assert "CREATE TABLE" in ddl
    assert "BIGINT" in ddl            # BigInteger -> BIGINT on pg
    assert "BOOLEAN" in ddl           # Boolean -> BOOLEAN on pg
    assert "TIMESTAMP WITH TIME ZONE" in ddl  # DateTime(timezone=True) on pg
    assert "AUTOINCREMENT" not in ddl  # SQLite-only keyword must not leak


def test_persist_shaped_insert_round_trips_on_sqlite():
    # Exercise the ORM the way persist_result() will once ported: a run + an
    # event + a snapshot, then read back. Confirms FKs + types work end-to-end.
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    at = datetime.now(timezone.utc)

    with Session(engine) as s:
        sport = Sport(sport_id=3, name="basketball", slug="basketball")
        s.add(sport)
        s.flush()
        run = ScrapeRun(skin="linebet", action="list_live", extracted_at=at,
                        success=True, event_count=1, duration_seconds=1.0)
        s.add(run)
        s.flush()
        event = Event(event_id="738047045", sport_id=3, home_name="Phoenix",
                      away_name="Rain or Shine", first_seen=at, last_seen=at)
        s.add(event)
        s.flush()
        market = Market(name="To Win Match", market_type="moneyline_h2h", raw_g=1)
        s.add(market)
        s.flush()
        snap = OddsSnapshot(run_id=run.run_id, event_id="738047045", skin="linebet",
                            market_id=market.market_id, selection_name="1",
                            price=1.5, is_suspended=False, scope="FULL_MATCH",
                            captured_at=at)
        s.add(snap)
        s.commit()

    with Session(engine) as s:
        rows = s.execute(select(OddsSnapshot).where(OddsSnapshot.event_id == "738047045")).scalars().all()
        assert len(rows) == 1
        assert rows[0].price == 1.5
        assert rows[0].is_suspended is False
        assert rows[0].scope == "FULL_MATCH"
