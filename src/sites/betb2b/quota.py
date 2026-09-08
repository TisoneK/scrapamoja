"""Quota monitor — watch the hosted store's size against the platform limit.

The deployed store is a hosted Postgres (Supabase) whose free tier flips a
project READ-ONLY once its size limit is crossed — every write then fails
until space is freed or the billing cycle resets. That has taken the store
down twice. This module makes the store's own size observable so the
scheduler can warn — and then act — BEFORE the provider does:

* ``db_bytes`` (via store) reads the size straight from the server:
  ``pg_database_size`` on Postgres — the same number the provider's dashboard
  shows. A local SQLite store has no hosted quota → ``None``.
* ``evaluate`` maps used/limit onto levels: ``ok`` → ``warn`` (default 80%)
  → ``critical`` (default 92%). The scheduler's quota pass prunes aged odds
  history at the critical level — tick history past the prune window has no
  product value (final results live on ``events``), so pruning keeps the
  store under the limit without touching anything the prediction products
  read.

Env (all optional):

  BETB2B_DB_LIMIT_MB       hosted size limit, MB (default 500 — Supabase free tier)
  BETB2B_DB_WARN_PCT       warn level, % of limit (default 80)
  BETB2B_DB_CRITICAL_PCT   critical level, % of limit (default 92)
  BETB2B_PRUNE_DAYS        prune odds history for events older than this (default 7)
  BETB2B_PRUNE_BATCH       events per delete batch (default 2000)
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

MB = 1024 * 1024

LIMIT_ENV = "BETB2B_DB_LIMIT_MB"
WARN_ENV = "BETB2B_DB_WARN_PCT"
CRITICAL_ENV = "BETB2B_DB_CRITICAL_PCT"
PRUNE_DAYS_ENV = "BETB2B_PRUNE_DAYS"
PRUNE_BATCH_ENV = "BETB2B_PRUNE_BATCH"


def _num(env: str, default: float) -> float:
    try:
        return float(os.environ.get(env, default))
    except (TypeError, ValueError):
        return float(default)


def limit_mb() -> float:
    return _num(LIMIT_ENV, 500)


def warn_pct() -> float:
    return _num(WARN_ENV, 80)


def critical_pct() -> float:
    return _num(CRITICAL_ENV, 92)


def prune_days() -> float:
    return _num(PRUNE_DAYS_ENV, 7)


def prune_batch() -> int:
    return int(_num(PRUNE_BATCH_ENV, 2000))


def evaluate(used_bytes: Optional[int], *, limit: Optional[float] = None,
             warn: Optional[float] = None, critical: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Map the store's used bytes onto a quota level.

    ``limit``/``warn``/``critical`` override the env-configured defaults
    (MB and % respectively). ``None`` used bytes (size unknown) → ``None``.

    Returns ``{"used_bytes", "used_mb", "limit_mb", "pct", "level", "over"}``
    where level is ``"ok"`` | ``"warn"`` | ``"critical"`` and ``over`` marks a
    store already past the limit (the provider's read-only state).
    """
    if used_bytes is None:
        return None
    lm = limit_mb() if limit is None else float(limit)
    wp = warn_pct() if warn is None else float(warn)
    cp = critical_pct() if critical is None else float(critical)
    lm = max(lm, 0.001)
    used = int(used_bytes)
    pct = used / (lm * MB) * 100.0
    if pct >= cp:
        level = "critical"
    elif pct >= wp:
        level = "warn"
    else:
        level = "ok"
    return {
        "used_bytes": used,
        "used_mb": used / MB,
        "limit_mb": lm,
        "pct": pct,
        "level": level,
        "over": used > lm * MB,
    }
