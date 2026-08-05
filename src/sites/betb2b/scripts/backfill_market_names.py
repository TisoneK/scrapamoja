"""Backfill real names onto existing ``markets`` rows saved as ``"G=<n>"`` (ADR-19).

Before the GS-indexed naming landed, market groups the code couldn't name were
stored as ``markets.name = "G=27"`` etc. New scrapes now write real names, but
old rows keep the placeholder. This one-off backfill resolves each ``G=<n>`` row
by its ``raw_g`` against the committed ``market_group_names_by_g_en.json`` table
(feed-G → name; globally unique) and either updates the name in place or — when
a correctly-named row for the same ``(name, market_type, raw_g)`` already exists
(a newer scrape created it) — MERGES: repoints ``odds_snapshots.market_id`` to
the existing row and deletes the placeholder row. Groups with no known name are
left as honest ``G=<n>`` (never guessed).

Requires ``DATABASE_URL`` (the live Supabase / any SQLAlchemy URL). DRY-RUN by
default — prints the plan and changes nothing. Pass ``--apply`` to write, in a
single transaction.

    DATABASE_URL=... python -m src.sites.betb2b.scripts.backfill_market_names
    DATABASE_URL=... python -m src.sites.betb2b.scripts.backfill_market_names --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict

from ._common import ensure_repo_on_path, repo_root

ensure_repo_on_path()

_G_TABLE = repo_root() / "src/sites/betb2b/data/market_group_names_by_g_en.json"


def _load_g_names() -> Dict[int, str]:
    raw = json.loads(_G_TABLE.read_text(encoding="utf-8"))
    return {int(k): v for k, v in raw.items() if isinstance(v, str) and v.strip()}


def run(apply: bool = False, like: str = "G=%", *, verbose: bool = True) -> Dict[str, int]:
    """Resolve placeholder ``G=<n>`` market names and (optionally) write them.

    Returns ``{"renamed": .., "merged": .., "skipped": ..}``. Reads
    ``DATABASE_URL`` via the shared engine builder. Idempotent.
    """
    from sqlalchemy import delete, select, update
    from src.core.db import get_engine
    from src.sites.betb2b.models import Market, OddsSnapshot

    g_names = _load_g_names()

    def _match(col, val):
        return col.is_(None) if val is None else col == val

    def _say(msg: str) -> None:
        if verbose:
            print(msg)

    m, o = Market.__table__, OddsSnapshot.__table__
    _say(f"Loaded {len(g_names)} G -> name entries.")
    counts = {"renamed": 0, "merged": 0, "skipped": 0}

    with get_engine().begin() as conn:
        rows = conn.execute(
            select(m.c.market_id, m.c.name, m.c.market_type, m.c.raw_g)
            .where(m.c.name.like(like))
        ).fetchall()
        _say(f"Found {len(rows)} placeholder market rows matching {like!r}.\n")

        for mid, name, mtype, raw_g in rows:
            target = g_names.get(raw_g) if raw_g is not None else None
            if not target:
                counts["skipped"] += 1
                _say(f"  SKIP   market_id={mid} {name!r} (raw_g={raw_g}: no known name)")
                continue

            existing = conn.execute(
                select(m.c.market_id).where(
                    _match(m.c.name, target),
                    _match(m.c.market_type, mtype),
                    _match(m.c.raw_g, raw_g),
                    m.c.market_id != mid,
                )
            ).scalar()

            if existing is not None:
                counts["merged"] += 1
                _say(f"  MERGE  market_id={mid} {name!r} -> existing "
                     f"market_id={existing} {target!r} (repoint odds + delete)")
                if apply:
                    conn.execute(update(o).where(o.c.market_id == mid)
                                 .values(market_id=existing))
                    conn.execute(delete(m).where(m.c.market_id == mid))
            else:
                counts["renamed"] += 1
                _say(f"  RENAME market_id={mid} {name!r} -> {target!r}")
                if apply:
                    conn.execute(update(m).where(m.c.market_id == mid)
                                 .values(name=target))

        if not apply:
            _say("\n-- DRY RUN (no changes written) --")
            conn.rollback()

    verb = "Applied" if apply else "Would apply"
    _say(f"\n{verb}: {counts['renamed']} renamed, {counts['merged']} merged, "
         f"{counts['skipped']} left as G=<n>.")
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="Write the changes (default: dry-run, no writes).")
    ap.add_argument("--like", default="G=%",
                    help="SQL LIKE pattern for placeholder names (default 'G=%%').")
    args = ap.parse_args()

    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL is not set — point it at the store (Supabase) first.",
              file=sys.stderr)
        return 2

    run(apply=args.apply, like=args.like)
    return 0


if __name__ == "__main__":
    sys.exit(main())
