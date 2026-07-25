"""ADR-11 one-time data copy: legacy SQLite files → the shared store.

Per ADR-11 consequence: "A one-time data copy (SQLAlchemy script over the
shared models) moves existing rows." This is that script. It reads the three
legacy SQLite databases:

  * data/betb2b/odds.db        → betb2b product data (raw sqlite3 store)
  * data/adaptive.db           → Selector Engine feature flags + failure events
  * (audit_log lives in adaptive.db — same Base, copied together)

...and writes every row into the TARGET store (resolved from DATABASE_URL —
Railway Postgres in deployed envs, or a SQLite file for a dry run). The betb2b
side reads via the ORM models (src/sites/betb2b/models.py); the adaptive side
reads via its ORM models. Both write through SQLAlchemy sessions, so the copy
is dialect-agnostic — it runs unchanged against Postgres or SQLite.

Usage:
  # Dry run into a local SQLite file (safe, no live DB needed):
  python -m scripts.migrate_sqlite_to_postgres --target sqlite:////tmp/copy.db

  # Real migration (operator, with DATABASE_URL set to the Railway Postgres):
  DATABASE_URL=postgresql+psycopg://... python -m scripts.migrate_sqlite_to_postgres

Notes:
  * Idempotent-ish: re-running against a Postgres with existing rows will
    INSERT duplicates for append-only fact tables (odds_snapshots, event_states,
    …). Run it ONCE per cutover. Dimension tables use natural keys so the
    ORM merge would need on-conflict handling for true idempotency — out of
    scope for a one-time copy.
  * The betb2b source is read with raw sqlite3 (that's how store.py wrote it)
    and written via the ORM models. The adaptive source is read + written via
    its ORM models.
  * Cannot be fully exercised from the Z.ai sandbox (no live Postgres), so it
    is shipped with a --dry-run self-check that copies into a temp SQLite file
    and reports row counts. The operator runs the real cutover.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

# betb2b ORM models (the ADR-11 portable schema)
from src.sites.betb2b.models import (
    Base as BetB2BBase,
    Sport, Country, League, Team, Event, Market,
    ScrapeRun, EventState, PeriodScore, OddsSnapshot,
    H2HGame, H2HPeriodScore, Statistic,
)
# adaptive ORM models
from src.selectors.adaptive.db.models.recipe import Base as AdaptiveBase
from src.core.db import resolve_database_url

REPO = Path(__file__).resolve().parents[1]

# betb2b tables in copy order (dimensions before facts; parents before children).
BETB2B_TABLES = [
    "sports", "countries", "leagues", "teams", "events", "markets",
    "scrape_runs", "event_states", "period_scores", "odds_snapshots",
    "h2h_games", "h2h_period_scores", "statistics",
]


def _open_source_sqlite(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"source SQLite not found: {path}")
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def copy_betb2b(src_path: Path, target_engine) -> dict[str, int]:
    """Copy the betb2b odds.db into the target via ORM models."""
    counts: dict[str, int] = {}
    if not src_path.exists():
        print(f"[betb2b] source not found, skipping: {src_path}")
        return counts
    BetB2BBase.metadata.create_all(target_engine, checkfirst=True)
    conn = _open_source_sqlite(src_path)
    try:
        # Map table name → ORM class
        cls = {
            "sports": Sport, "countries": Country, "leagues": League,
            "teams": Team, "events": Event, "markets": Market,
            "scrape_runs": ScrapeRun, "event_states": EventState,
            "period_scores": PeriodScore, "odds_snapshots": OddsSnapshot,
            "h2h_games": H2HGame, "h2h_period_scores": H2HPeriodScore,
            "statistics": Statistic,
        }
        with Session(target_engine) as s:
            for table in BETB2B_TABLES:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                model = cls[table]
                for r in rows:
                    d = {k: r[k] for k in r.keys()}
                    s.add(model(**d))
                s.commit()
                counts[table] = len(rows)
                print(f"[betb2b] {table}: {len(rows)} rows copied")
    finally:
        conn.close()
    return counts


def copy_adaptive(src_path: Path, target_engine) -> dict[str, int]:
    """Copy the adaptive.db (incl. audit_log) into the target via ORM models."""
    counts: dict[str, int] = {}
    if not src_path.exists():
        print(f"[adaptive] source not found, skipping: {src_path}")
        return counts
    AdaptiveBase.metadata.create_all(target_engine, checkfirst=True)
    src_engine = create_engine(f"sqlite:///{src_path}")
    try:
        insp = inspect(src_engine)
        tables = insp.get_table_names()
        with Session(target_engine) as s, Session(src_engine) as src_s:
            for table in sorted(tables):
                rows = src_s.execute(text(f"SELECT * FROM {table}")).fetchall()
                for r in rows:
                    d = {k: r._mapping[k] for k in r._mapping.keys()}
                    s.execute(text(f"INSERT INTO {table} ({', '.join(d.keys())}) "
                                   f"VALUES ({', '.join(':' + k for k in d.keys())})"), d)
                s.commit()
                counts[table] = len(rows)
                print(f"[adaptive] {table}: {len(rows)} rows copied")
    finally:
        src_engine.dispose()
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description="ADR-11 one-time SQLite→store data copy")
    ap.add_argument("--target", default=None,
                    help="target SQLAlchemy URL (default: resolve_database_url)")
    ap.add_argument("--betb2b-source", default=str(REPO / "data" / "betb2b" / "odds.db"),
                    help="path to the legacy betb2b odds.db")
    ap.add_argument("--adaptive-source", default=str(REPO / "data" / "adaptive.db"),
                    help="path to the legacy adaptive.db")
    ap.add_argument("--dry-run", action="store_true",
                    help="copy into a fresh temp SQLite file instead of the resolved target")
    args = ap.parse_args()

    if args.dry_run:
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / "copy.db"
        target_url = f"sqlite:///{tmp}"
        print(f"[dry-run] target = {target_url}")
    else:
        target_url = args.target or resolve_database_url()
        print(f"[live] target = {target_url}")

    target_engine = create_engine(target_url)

    betb2b_counts = copy_betb2b(Path(args.betb2b_source), target_engine)
    adaptive_counts = copy_adaptive(Path(args.adaptive_source), target_engine)

    total = sum(betb2b_counts.values()) + sum(adaptive_counts.values())
    print(f"\n=== COPY COMPLETE: {total} rows "
          f"({sum(betb2b_counts.values())} betb2b + {sum(adaptive_counts.values())} adaptive) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
