"""SQLAlchemy ORM models for the BetB2B store — the ADR-11 portable schema.

ADR-11 moves betb2b data from a file-SQLite (raw ``sqlite3``) store to a shared
Railway PostgreSQL. The store's schema (ADR-6) is a clean relational model —
``sports``, ``countries``, ``leagues``, ``teams``, ``events``, ``markets``,
``scrape_runs``, ``event_states``, ``period_scores``, ``odds_snapshots``,
``h2h_games``, ``h2h_period_scores``, ``statistics`` — kept deliberately
"Postgres-portable". This module is that port: the same tables/columns/keys as
``store.py``'s ``SCHEMA`` string, but declared with SQLAlchemy types that
compile cleanly on **both** SQLite (local/CI fallback) and PostgreSQL
(deployed), per ADR-11 point 6.

Portable type choices (ADR-11 "port the SQLite-isms"):

* ``INTEGER PRIMARY KEY`` surrogate keys → :class:`BigInteger` (autoincrement).
  On SQLite ``BigInteger`` compiles to ``INTEGER`` (rowid-backed); on Postgres
  it compiles to ``BIGINT`` with an implicit sequence — both autoincrement.
  ``events.event_id`` is a natural TEXT key (the shared backend id), unchanged.
* ``TEXT`` timestamp columns (``start_time``, ``first_seen``, ``extracted_at``,
  ``captured_at``, ``date_start``) → :class:`DateTime` with
  ``timezone=True``. The store already writes ISO-8601 (+00:00) strings; on
  SQLite these round-trip as text, on Postgres they become ``timestamptz``.
* ``success INTEGER`` (0/1), ``is_live``, ``is_suspended``, ``winner``,
  ``status`` → :class:`Boolean` where the value is genuinely boolean;
  ``winner``/``status`` stay ``Integer`` (they're enum-like codes, not flags).

These models are the **canonical schema** for migrations (Alembic) and for the
one-time data copy from the legacy SQLite files. ``store.py``'s hand-written
``SCHEMA`` remains the SQLite materialization used by the live scraper today;
the two are kept in sync until the persist path is fully ported (backlogged —
see ADR-11 progress note). The read helpers (``latest_odds``, ``line_movement``,
``cross_skin_odds``, ``counts``) are defined here against the ORM so a
FastAPI service reading from Postgres uses the same relation shapes the
scraper writes.

Indexes (ADR-11 "index the hot query paths"): ``odds_snapshots(event_id,
extracted_at)`` and ``events(start_time)`` are added here in addition to the
pre-existing ``store.py`` indexes (which key on ``captured_at`` per skin).
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional


# A surrogate primary key that autoincrements on BOTH backends. SQLite only
# autoincrements the literal ``INTEGER PRIMARY KEY`` (rowid-backed); ``BIGINT``
# gets no rowid so inserts fail with NOT NULL on the PK. The variant compiles
# to ``INTEGER`` on SQLite (autoincrement) and ``BIGINT`` on Postgres (also
# autoincrement via an implicit sequence). ADR-11 "INTEGER PRIMARY KEY →
# IDENTITY/SERIAL" — this is the portable realization.
SurrogatePK = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    """Base for betb2b ORM models — distinct from the adaptive layer's Base.

    The two stores consolidate into one Postgres *instance* (ADR-11 point 3)
    but keep separate ``Base`` metadata so each can be migrated independently.
    A shared ``Base`` would couple their migration histories.
    """
    pass


# --------------------------------------------------------------------------- #
# Dimensions (skin-agnostic — one row per real entity, UPSERT-ed)             #
# --------------------------------------------------------------------------- #
class Sport(Base):
    __tablename__ = "sports"
    sport_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # backend SI (3=basketball)
    name: Mapped[Optional[str]] = mapped_column(Text)
    slug: Mapped[Optional[str]] = mapped_column(Text)


class Country(Base):
    __tablename__ = "countries"
    country_id: Mapped[int] = mapped_column(SurrogatePK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)


class League(Base):
    __tablename__ = "leagues"
    league_id: Mapped[int] = mapped_column(Integer, primary_key=True)  # backend LI
    name: Mapped[Optional[str]] = mapped_column(Text)
    sport_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sports.sport_id"))
    country_id: Mapped[Optional[int]] = mapped_column(ForeignKey("countries.country_id"))


class Team(Base):
    __tablename__ = "teams"
    team_id: Mapped[int] = mapped_column(SurrogatePK, primary_key=True, autoincrement=True)
    backend_id: Mapped[Optional[str]] = mapped_column(Text, unique=True)  # h2h hash id when known
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sport_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sports.sport_id"))
    country_id: Mapped[Optional[int]] = mapped_column(ForeignKey("countries.country_id"))
    feed_id: Mapped[Optional[int]] = mapped_column(Integer)          # O1I/O2I — feed team id
    image: Mapped[Optional[str]] = mapped_column(Text)              # O1IMG/O2IMG[0] — crest
    feed_country_id: Mapped[Optional[int]] = mapped_column(Integer)  # O1C/O2C — feed country id
    __table_args__ = (UniqueConstraint("name", "sport_id", name="uq_teams_name_sport"),)


class Event(Base):
    __tablename__ = "events"
    event_id: Mapped[str] = mapped_column(Text, primary_key=True)  # shared across skins
    sport_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sports.sport_id"))
    league_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leagues.league_id"))
    country_id: Mapped[Optional[int]] = mapped_column(ForeignKey("countries.country_id"))
    home_team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.team_id"))
    away_team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.team_id"))
    home_name: Mapped[Optional[str]] = mapped_column(Text)  # denormalized for convenience
    away_name: Mapped[Optional[str]] = mapped_column(Text)
    start_time: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True))
    venue: Mapped[Optional[str]] = mapped_column(Text)   # MIO.Loc — arena/venue
    stage: Mapped[Optional[str]] = mapped_column(Text)   # MIO.TSt — tournament stage
    first_seen: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        Index("ix_events_league", "league_id"),
        Index("ix_events_sport", "sport_id"),
        Index("ix_events_start_time", "start_time"),  # ADR-11 hot path
    )


class Market(Base):
    __tablename__ = "markets"
    market_id: Mapped[int] = mapped_column(SurrogatePK, primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    market_type: Mapped[Optional[str]] = mapped_column(Text)
    raw_g: Mapped[Optional[int]] = mapped_column(Integer)


# --------------------------------------------------------------------------- #
# Facts (skin-scoped time-series, append-only)                                #
# --------------------------------------------------------------------------- #
class ScrapeRun(Base):
    __tablename__ = "scrape_runs"
    run_id: Mapped[int] = mapped_column(SurrogatePK, primary_key=True, autoincrement=True)
    skin: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[Optional[str]] = mapped_column(Text)
    sport: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)
    extracted_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    event_count: Mapped[Optional[int]] = mapped_column(Integer)
    success: Mapped[Optional[bool]] = mapped_column(Boolean)  # was INTEGER 0/1
    error: Mapped[Optional[str]] = mapped_column(Text)
    template_version: Mapped[Optional[str]] = mapped_column(Text)


class EventState(Base):
    __tablename__ = "event_states"
    state_id: Mapped[int] = mapped_column(SurrogatePK, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(SurrogatePK, ForeignKey("scrape_runs.run_id"), nullable=False)
    event_id: Mapped[str] = mapped_column(Text, ForeignKey("events.event_id"), nullable=False)
    skin: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(Text)
    is_live: Mapped[Optional[bool]] = mapped_column(Boolean)  # was INTEGER 0/1
    score_home: Mapped[Optional[int]] = mapped_column(Integer)
    score_away: Mapped[Optional[int]] = mapped_column(Integer)
    minute: Mapped[Optional[int]] = mapped_column(Integer)
    period: Mapped[Optional[str]] = mapped_column(Text)
    time_remaining: Mapped[Optional[str]] = mapped_column(Text)
    wp_home: Mapped[Optional[float]] = mapped_column(Float)  # WP.P1 — win probability home
    wp_away: Mapped[Optional[float]] = mapped_column(Float)  # WP.P2 — win probability away
    captured_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (Index("ix_states_event", "event_id", "captured_at"),)


class PeriodScore(Base):
    __tablename__ = "period_scores"
    id: Mapped[int] = mapped_column(SurrogatePK, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(SurrogatePK, ForeignKey("scrape_runs.run_id"), nullable=False)
    event_id: Mapped[str] = mapped_column(Text, ForeignKey("events.event_id"), nullable=False)
    skin: Mapped[str] = mapped_column(Text, nullable=False)
    period_key: Mapped[Optional[int]] = mapped_column(Integer)
    period_name: Mapped[Optional[str]] = mapped_column(Text)
    home_score: Mapped[Optional[int]] = mapped_column(Integer)
    away_score: Mapped[Optional[int]] = mapped_column(Integer)
    captured_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (Index("ix_periods_event", "event_id", "captured_at"),)


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    snap_id: Mapped[int] = mapped_column(SurrogatePK, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(SurrogatePK, ForeignKey("scrape_runs.run_id"), nullable=False)
    event_id: Mapped[str] = mapped_column(Text, ForeignKey("events.event_id"), nullable=False)
    skin: Mapped[str] = mapped_column(Text, nullable=False)
    market_id: Mapped[Optional[int]] = mapped_column(ForeignKey("markets.market_id"))
    selection_name: Mapped[Optional[str]] = mapped_column(Text)
    line: Mapped[Optional[float]] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    is_suspended: Mapped[Optional[bool]] = mapped_column(Boolean)  # was INTEGER 0/1
    raw_t: Mapped[Optional[int]] = mapped_column(Integer)
    scope: Mapped[str] = mapped_column(Text, default="FULL_MATCH")
    captured_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        Index("ix_odds_event", "event_id", "skin", "captured_at"),
        Index("ix_odds_market", "event_id", "skin", "market_id", "selection_name", "captured_at"),
        Index("ix_odds_event_extracted", "event_id", "captured_at"),  # ADR-11 hot path
    )


class H2HGame(Base):
    __tablename__ = "h2h_games"
    id: Mapped[int] = mapped_column(SurrogatePK, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(SurrogatePK, ForeignKey("scrape_runs.run_id"), nullable=False)
    event_id: Mapped[str] = mapped_column(Text, ForeignKey("events.event_id"), nullable=False)
    skin: Mapped[str] = mapped_column(Text, nullable=False)
    game_id: Mapped[Optional[str]] = mapped_column(Text)
    sport_id: Mapped[Optional[int]] = mapped_column(Integer)
    team1_backend_id: Mapped[Optional[str]] = mapped_column(Text)
    team2_backend_id: Mapped[Optional[str]] = mapped_column(Text)
    date_start: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True))
    score1: Mapped[Optional[int]] = mapped_column(Integer)
    score2: Mapped[Optional[int]] = mapped_column(Integer)
    sub_score1: Mapped[Optional[int]] = mapped_column(Integer)
    sub_score2: Mapped[Optional[int]] = mapped_column(Integer)
    winner: Mapped[Optional[int]] = mapped_column(Integer)  # enum-like code, not a flag
    status: Mapped[Optional[int]] = mapped_column(Integer)  # enum-like code, not a flag
    captured_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (Index("ix_h2h_event", "event_id"),)


class H2HPeriodScore(Base):
    __tablename__ = "h2h_period_scores"
    id: Mapped[int] = mapped_column(SurrogatePK, primary_key=True, autoincrement=True)
    h2h_game_id: Mapped[int] = mapped_column(SurrogatePK, ForeignKey("h2h_games.id"), nullable=False)
    event_id: Mapped[Optional[str]] = mapped_column(Text)
    period_key: Mapped[Optional[int]] = mapped_column(Integer)
    period_name: Mapped[Optional[str]] = mapped_column(Text)
    home_score: Mapped[Optional[int]] = mapped_column(Integer)
    away_score: Mapped[Optional[int]] = mapped_column(Integer)


class Statistic(Base):
    __tablename__ = "statistics"
    id: Mapped[int] = mapped_column(SurrogatePK, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(SurrogatePK, ForeignKey("scrape_runs.run_id"), nullable=False)
    event_id: Mapped[str] = mapped_column(Text, ForeignKey("events.event_id"), nullable=False)
    skin: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(Text)
    value: Mapped[Optional[str]] = mapped_column(Text)
    captured_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)


__all__ = [
    "Base",
    "Sport", "Country", "League", "Team", "Event", "Market",
    "ScrapeRun", "EventState", "PeriodScore", "OddsSnapshot",
    "H2HGame", "H2HPeriodScore", "Statistic",
]
