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
  → ``critical`` (default 92%). The scheduler's quota pass reads the size and
  **fails loud** at warn/over so the incident is visible before the provider
  flips the store read-only.

Two-tier model (ADR-6): by default the scraper only OBSERVES the hosted
store's size — it does **not** prune or truncate the cloud. The engine owns
cloud retention/filtering of the scraped tables. ``retention_action`` /
``BETB2B_CLOUD_RETENTION=1`` restore the scraper's own self-pruning (aged odds
history has no product value — final results live on ``events``) for
single-tier / standalone use where no engine manages the same store.

Env (all optional):

  BETB2B_DB_LIMIT_MB       hosted size limit, MB (default 500 — Supabase free tier)
  BETB2B_DB_WARN_PCT       warn level, % of limit (default 80)
  BETB2B_DB_CRITICAL_PCT   critical level, % of limit (default 92)
  BETB2B_PRUNE_DAYS        prune odds history for events older than this (default 7)
  BETB2B_PRUNE_BATCH       events per delete batch (default 2000)
  BETB2B_QUOTA_HARD=0      disable the automatic fact-history TRUNCATE escalation
                           (default on: when the store is over its hard limit, the
                           quota pass resets fact history itself — the operator
                           playbook, run by the machine)
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
HARD_ENV = "BETB2B_QUOTA_HARD"
RETENTION_ENV = "BETB2B_CLOUD_RETENTION"


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


def hard_enabled() -> bool:
    """Whether the quota pass may reset fact history itself when the store is
    past the provider's hard limit (default: yes — the operator playbook,
    run automatically; the delete ladder alone cannot reclaim the reported
    size of an already-over store)."""
    return os.environ.get(HARD_ENV, "1").strip().lower() not in {"0", "false", "no", "off"}


def retention_enabled() -> bool:
    """Whether the SCRAPER may delete/prune the hosted (cloud) store itself.

    **Default OFF** under the two-tier model (ADR-6, supervisor's division of
    labour): the scraper fetches and stores — local-first archive, then mirrors
    everything up — and never omits or deletes cloud data. The **engine** owns
    cloud retention and filtering of the scraped tables (its own ``sw retain``
    extended to cover them). Set ``BETB2B_CLOUD_RETENTION=1`` to restore the
    scraper's old self-pruning for single-tier / standalone use (no engine
    reading the same store)."""
    return os.environ.get(RETENTION_ENV, "0").strip().lower() in {"1", "true", "yes", "on"}


def retention_action(st: Optional[Dict[str, Any]], *, enabled: Optional[bool] = None) -> Optional[str]:
    """What the scheduler's quota pass should DO about hosted-store size.

    * ``None`` — observe only (**the default**: the engine owns cloud
      retention). The pass still reads the size and fails loud at warn/over;
      it just never deletes.
    * ``"prune"`` — bounded aged-fact prune (only when retention is opted in
      AND the store is at the critical level).
    * ``"truncate"`` — hard fact-history reset (opted in, critical, already
      over the hard limit, and :func:`hard_enabled`).

    ``enabled`` overrides :func:`retention_enabled` (for tests)."""
    if enabled is None:
        enabled = retention_enabled()
    if not enabled or st is None or st.get("level") != "critical":
        return None
    return "truncate" if (st.get("over") and hard_enabled()) else "prune"


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
