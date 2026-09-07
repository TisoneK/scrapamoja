"""Local fallback store — keeps writes when the primary store is unavailable.

The remote store (Supabase Postgres via ``DATABASE_URL``) is the primary. When
it fails — a quota restriction forces the project read-only, the connection
drops, the provider restarts — writes used to be dropped outright (the
scheduler backed off and logged; job runs failed). This module switches writes
to a **local SQLite mirror** instead and queues every write for replay:

* **Activate.** A write or connect that fails with a fallback-eligible error
  (read-only transaction, connection-class error, provider shutdown/capacity)
  flips the process into fallback mode. ``store.init_db`` then hands out a
  connection to the local mirror, so reads (change-only dedup lookups,
  scheduling filters, the job queue) keep working against local data.
* **Outbox.** Every write made while in fallback mode is appended (as JSON)
  to a ``fallback_outbox`` table in the mirror, FIFO.
* **Probe.** After each fallback write (throttled), try a throwaway write
  transaction on the primary: ``INSERT … ROLLBACK``. A restricted project
  still serves reads, so only a real write proves recovery.
* **Drain.** The first successful probe flips writes back to the primary and
  replays the outbox in order. Replay rides the store's normal upsert and
  change-only dedup paths, so replaying a payload the primary already has is
  harmless.

State is per-process: two services (worker + web) each keep their own mirror
and outbox. The mirror file is the same store the app uses in local mode
(``BETB2B_DB_PATH`` / ``data/betb2b/odds.db``) unless ``BETB2B_FALLBACK_DB_PATH``
is set — point it at a mounted volume if fallback data must survive redeploys.

Env:

  BETB2B_FALLBACK=0                disable entirely (fail like before)
  BETB2B_FALLBACK_DB_PATH          mirror file (default: the local store path)
  BETB2B_FALLBACK_PROBE_SECONDS    min seconds between primary probes (300)
  BETB2B_FALLBACK_OUTBOX_MAX       max queued payloads; oldest dropped (5000)
  BETB2B_FALLBACK_DRAIN_MAX        max payloads replayed per drain pass (500)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

ENABLE_ENV = "BETB2B_FALLBACK"
PATH_ENV = "BETB2B_FALLBACK_DB_PATH"
PROBE_SECONDS_ENV = "BETB2B_FALLBACK_PROBE_SECONDS"
OUTBOX_MAX_ENV = "BETB2B_FALLBACK_OUTBOX_MAX"
DRAIN_MAX_ENV = "BETB2B_FALLBACK_DRAIN_MAX"

DEFAULT_PROBE_SECONDS = 300.0
DEFAULT_OUTBOX_MAX = 5000
DEFAULT_DRAIN_MAX = 500
DRAIN_TIME_BUDGET_SECONDS = 60.0   # one drain pass never blocks a scrape forever
FINISH_DRAIN_HOLD_SECONDS = 60.0   # min gap between opportunistic drain passes
PROBE_LOG_GAP_SECONDS = 1800.0     # "still not writable" info logs, throttled

# record_result kwargs that ride in a 'result' outbox payload (event_id travels
# separately — it is the positional key, not a keyword).
_RESULT_KEYS = ("stat_game_id", "score_home", "score_away", "winner", "status", "at")

# Connection-class / capacity / shutdown SQLSTATEs worth failing over for.
# Deliberately NOT here: auth (28P01/28000 — a config bug), integrity /
# programming errors (our bugs), serialization (a retry, not an outage).
_RESOURCE_SQLSTATES = {"53000", "53001", "53002", "53003", "53300"}
_SHUTDOWN_SQLSTATES = {"57P01", "57P02", "57P03"}
_CONN_MESSAGES = (
    "connection refused", "connection reset", "server closed the connection",
    "could not connect", "connection timed out", "timed out",
    "name or service not known", "temporary failure in name resolution",
    "getaddrinfo failed", "no route to host", "network is unreachable",
    "broken pipe", "failed to establish", "connection is closed",
    "connection was closed", "terminating connection",
    "the database system is starting up", "the database system is shutting down",
    "too many connections",
)

_lock = threading.Lock()
_mirror_path: Optional[str] = None
_outbox_remaining = False   # in-memory hint: the outbox may hold undrained rows

_state: Dict[str, Any] = {
    "active": False,
    "reason": None,        # read_only | connectivity | write
    "since": None,         # ISO timestamp of activation
    "recovered_at": None,  # ISO timestamp of the last flip back
    "failures": 0,
    "last_error": None,
    "probes": 0,
    "drained": 0,          # payloads replayed to the primary
    "dropped": 0,          # payloads dropped by the outbox cap
    "flips": 0,            # fallback → primary transitions
    # monotonic throttles (excluded from status())
    "_last_probe_at": 0.0,
    "_last_probe_log": 0.0,
    "_last_drain_at": 0.0,
}


# --------------------------------------------------------------------------- #
# Failure classification
# --------------------------------------------------------------------------- #
def classify_failure(exc: BaseException | None) -> Optional[str]:
    """Why a primary-store call failed, in fallback terms.

    Returns ``"read_only"`` (quota restriction), ``"connectivity"`` (outage,
    provider restart, capacity), or ``None`` when failing over would be wrong —
    a bug or a request problem must fail loudly, not silently move to another
    database.
    """
    if exc is None:
        return None
    from . import store

    seen: set[int] = set()
    e: BaseException | None = exc
    while e is not None and id(e) not in seen:
        seen.add(id(e))
        if store.is_read_only_error(e):
            return "read_only"
        sqlstate = getattr(e, "sqlstate", None) or getattr(e, "pgcode", None) or ""
        if sqlstate == "25006":
            return "read_only"
        if sqlstate.startswith("08") or sqlstate in _RESOURCE_SQLSTATES \
                or sqlstate in _SHUTDOWN_SQLSTATES:
            return "connectivity"
        msg = str(e).lower()
        if any(m in msg for m in _CONN_MESSAGES):
            return "connectivity"
        e = getattr(e, "orig", None) or e.__cause__ or e.__context__
    # Plain transport-level errors (ConnectionRefusedError, socket timeouts…)
    # reach the store unwrapped when the driver does not dress them up.
    import socket
    if isinstance(exc, (ConnectionError, TimeoutError, socket.gaierror)):
        return "connectivity"
    return None


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def enabled() -> bool:
    return os.environ.get(ENABLE_ENV, "1").strip().lower() not in {"0", "false", "no", "off"}


def probe_seconds() -> float:
    try:
        return float(os.environ.get(PROBE_SECONDS_ENV, DEFAULT_PROBE_SECONDS))
    except ValueError:
        return DEFAULT_PROBE_SECONDS


def outbox_max() -> int:
    try:
        return int(os.environ.get(OUTBOX_MAX_ENV, DEFAULT_OUTBOX_MAX))
    except ValueError:
        return DEFAULT_OUTBOX_MAX


def drain_max() -> int:
    try:
        return int(os.environ.get(DRAIN_MAX_ENV, DEFAULT_DRAIN_MAX))
    except ValueError:
        return DEFAULT_DRAIN_MAX


# --------------------------------------------------------------------------- #
# Mirror (the local SQLite store — same schema as local mode, plus the outbox)
# --------------------------------------------------------------------------- #
def _resolve_mirror_path(explicit: Any) -> str:
    """Precedence: the env var (explicit operator intent) > the caller's
    store path (in local-mode call sites this IS the store file) > the
    service default. Resolved once — the mirror is process-stable."""
    global _mirror_path
    if _mirror_path:
        return _mirror_path
    env = os.environ.get(PATH_ENV)
    if env:
        _mirror_path = env
    elif explicit:
        _mirror_path = str(explicit)
    else:
        from .service import db_path
        _mirror_path = db_path()
    parent = os.path.dirname(_mirror_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return _mirror_path


def mirror_path() -> Optional[str]:
    return _mirror_path


def mirror_connect(explicit: Any = None):
    """Open (and schema-ensure) the local fallback store. A sqlite3 connection —
    the store's own SQLite code path handles everything on it."""
    from . import store
    return store._connect_sqlite(_resolve_mirror_path(explicit))


# --------------------------------------------------------------------------- #
# Activation state machine
# --------------------------------------------------------------------------- #
def active() -> bool:
    return bool(_state["active"])


def _activate(reason: str, exc: BaseException) -> None:
    detail = f"{type(exc).__name__}: {exc}"
    with _lock:
        _state["failures"] += 1
        _state["last_error"] = detail
        if _state["active"]:
            return
        _state.update(active=True, reason=reason, since=datetime.now(timezone.utc).isoformat())
    logger.warning(
        "primary store write failed (%s): %s — switching to the local fallback "
        "store at %s; writes are queued locally and replayed when the primary "
        "recovers", reason, exc, _mirror_path)


def _flip_back(pending: int) -> None:
    with _lock:
        _state["active"] = False
        _state["flips"] += 1
        _state["recovered_at"] = datetime.now(timezone.utc).isoformat()
    logger.warning(
        "primary store recovered — writes switch back to the primary; replaying "
        "%d queued write(s) from the local fallback store", pending)


def status() -> Dict[str, Any]:
    with _lock:
        snap = {k: v for k, v in _state.items() if not k.startswith("_")}
    snap["enabled"] = enabled()
    snap["mirror_path"] = _mirror_path
    if _state["active"] or _outbox_remaining:
        try:
            snap["outbox"] = _outbox_count()
        except Exception:  # noqa: BLE001 — status must never raise
            snap["outbox"] = None
    else:
        snap["outbox"] = 0
    return snap


# --------------------------------------------------------------------------- #
# Store hooks (called from store.py)
# --------------------------------------------------------------------------- #
def recover_write_failure(kind: str, exc: BaseException, payload: Dict[str, Any],
                          fallback_path: Any = None):
    """Handle a failed primary write. If the failure is fallback-eligible:
    activate fallback mode, apply the write to the local mirror (which also
    enqueues it for replay) and return the mirror's result — a run_id for
    ``"persist"``, True for ``"result"``. Returns None when the failure is not
    eligible or the mirror itself failed, so the store re-raises the original."""
    if not enabled():
        return None
    reason = classify_failure(exc)
    if reason is None:
        return None
    _resolve_mirror_path(fallback_path)
    _activate(reason, exc)
    try:
        from . import store
        conn = mirror_connect()
        try:
            if kind == "persist":
                return store.persist_result(payload, conn=conn)
            if kind == "result":
                kwargs = {k: payload[k] for k in _RESULT_KEYS if k in payload}
                store.record_result(conn, str(payload.get("event_id")), **kwargs)
                return True
            return None
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 — the mirror failed too; surface the primary error
        logger.exception("local fallback store write failed (kind=%s) — "
                         "re-raising the primary error", kind)
        return None


def recover_connect_failure(exc: BaseException, fallback_path: Any = None) -> bool:
    """Handle a failed primary connect (from ``store.init_db``). True when the
    process should carry on against the local mirror."""
    if not enabled():
        return False
    reason = classify_failure(exc)
    if reason is None:
        return False
    _resolve_mirror_path(fallback_path)
    _activate(reason, exc)
    return True


def after_write(kind: str, payload: Dict[str, Any]) -> None:
    """Called by the store after every successful primary write. Two jobs:
    enqueue the payload when writes are going to the mirror through a
    pre-existing connection (the caller supplied its ``conn`` before fallback
    activated), and run the recovery cycle (probe → flip back → drain, or the
    post-recovery opportunistic drain)."""
    if not enabled():
        return
    if _state["active"]:
        if kind == "result":
            payload = {"event_id": payload.get("event_id"),
                       **{k: v for k, v in payload.items()
                          if k in _RESULT_KEYS and v is not None}}
        enqueue(kind, payload)
        maybe_probe_and_drain()
    else:
        maybe_finish_drain()


def mirror_active() -> bool:
    """True while writes belong on the local mirror (fallback mode on). Callers
    open mirror connections directly instead of primary ones."""
    return enabled() and _state["active"]


# --------------------------------------------------------------------------- #
# Probe + drain (recovery)
# --------------------------------------------------------------------------- #
def maybe_probe_and_drain() -> None:
    """After a fallback-mode write: if the probe throttle has elapsed, test the
    primary with a throwaway write and, if it lands, flip back and replay."""
    if not _state["active"]:
        return
    now = time.monotonic()
    if now - float(_state["_last_probe_at"]) < probe_seconds():
        return
    with _lock:
        _state["_last_probe_at"] = now
        _state["probes"] += 1
    try:
        writable = _probe_primary_writable()
    except Exception as exc:  # noqa: BLE001 — a probe crash must not break writes
        logger.debug("fallback probe crashed: %s", exc)
        writable = False
    if not writable:
        return
    pending = _outbox_count()
    _flip_back(pending)
    _drain()


def maybe_finish_drain() -> None:
    """After a successful primary write: opportunistically replay outbox rows
    left over from a just-ended fallback period (the first drain pass is capped,
    so a long restriction empties over several writes)."""
    global _outbox_remaining
    if _state["active"] or not _outbox_remaining:
        return
    now = time.monotonic()
    if now - float(_state["_last_drain_at"]) < FINISH_DRAIN_HOLD_SECONDS:
        return
    with _lock:
        _state["_last_drain_at"] = now
    _drain()


def _connect_primary():
    from . import store_orm
    return store_orm.connect()


def _probe_primary_writable() -> bool:
    """A real (but rolled-back) write on the primary. Reads stay allowed on a
    restricted project, so only a write proves writes are back."""
    try:
        conn = _connect_primary()
    except Exception as exc:  # noqa: BLE001
        _log_probe_unreachable(exc)
        return False
    try:
        from .models import ScraperJob
        trans = conn.begin()
        try:
            conn.execute(ScraperJob.__table__.insert().values(
                skin="__probe__", action="__probe__", status="__probe__",
                created_at=datetime.now(timezone.utc), created_by="__fallback_probe__"))
        finally:
            trans.rollback()   # the probe never persists anything
        return True
    except Exception as exc:  # noqa: BLE001
        _log_probe_unreachable(exc)
        return False
    finally:
        conn.close()


def _log_probe_unreachable(exc: BaseException) -> None:
    now = time.monotonic()
    if now - float(_state["_last_probe_log"]) >= PROBE_LOG_GAP_SECONDS:
        with _lock:
            _state["_last_probe_log"] = now
        logger.info("fallback probe: primary store still not writable (%s: %s) — "
                    "staying on the local fallback store", type(exc).__name__, exc)


def _drain() -> int:
    """Replay queued payloads into the primary, oldest first. Stops and
    re-activates fallback mode on the first primary failure. Returns the number
    of payloads replayed."""
    global _outbox_remaining
    if not _outbox_remaining:
        return 0
    try:
        conn = _connect_primary()
    except Exception as exc:  # noqa: BLE001
        _activate("connectivity", exc)
        return 0
    deadline = time.monotonic() + DRAIN_TIME_BUDGET_SECONDS
    drained = 0
    try:
        for seq, kind, payload in _outbox_rows(drain_max()):
            try:
                _replay(conn, kind, payload)
            except Exception as exc:  # noqa: BLE001
                _activate(classify_failure(exc) or "write", exc)
                logger.warning("replay stopped at outbox seq=%s — %d/%d payloads "
                               "replayed; the rest stay queued for the next drain",
                               seq, drained, drained + 1)
                break
            _outbox_delete(seq)
            drained += 1
            with _lock:
                _state["drained"] += 1
            if drained >= drain_max() or time.monotonic() > deadline:
                break
    finally:
        conn.close()
    with _lock:
        _state["_last_drain_at"] = time.monotonic()
    _outbox_remaining = _outbox_count() > 0
    if not _outbox_remaining:
        logger.info("fallback outbox fully replayed (%d payloads in this pass)", drained)
    elif drained:
        logger.info("fallback outbox partially replayed (%d payloads; %d remain)",
                    drained, _outbox_count())
    return drained


def _replay(conn, kind: str, payload: Dict[str, Any]) -> None:
    from . import store_orm
    if kind == "persist":
        store_orm.persist_result(conn, payload)
        return
    if kind == "result":
        event_id = payload.get("event_id")
        if not event_id:
            return
        kwargs = {k: payload[k] for k in _RESULT_KEYS if k in payload}
        store_orm.record_result(conn, str(event_id), **kwargs)
        return
    logger.error("unknown outbox payload kind %r — dropping", kind)


# --------------------------------------------------------------------------- #
# Outbox (lives inside the mirror DB)
# --------------------------------------------------------------------------- #
def enqueue(kind: str, payload: Dict[str, Any]) -> None:
    """Queue one write (made against the mirror) for replay to the primary."""
    global _outbox_remaining
    conn = mirror_connect()
    try:
        conn.execute(
            "INSERT INTO fallback_outbox (kind, payload, created_at) VALUES (?,?,?)",
            (kind, json.dumps(payload, default=str), datetime.now(timezone.utc).isoformat()))
        cap = outbox_max()
        over = int(conn.execute("SELECT COUNT(*) FROM fallback_outbox").fetchone()[0]) - cap
        for _ in range(max(0, over)):
            conn.execute("DELETE FROM fallback_outbox WHERE seq = "
                         "(SELECT MIN(seq) FROM fallback_outbox)")
        if over > 0:
            with _lock:
                _state["dropped"] += over
            logger.warning("fallback outbox cap (%d) reached — dropped %d oldest "
                           "payload(s); replay will miss those", cap, over)
        conn.commit()
    finally:
        conn.close()
    _outbox_remaining = True


def _outbox_rows(limit: int) -> List[Tuple[int, str, Dict[str, Any]]]:
    conn = mirror_connect()
    try:
        rows = conn.execute(
            "SELECT seq, kind, payload FROM fallback_outbox ORDER BY seq LIMIT ?",
            (limit,)).fetchall()
        return [(r["seq"], r["kind"], json.loads(r["payload"])) for r in rows]
    finally:
        conn.close()


def _outbox_delete(seq: int) -> None:
    conn = mirror_connect()
    try:
        conn.execute("DELETE FROM fallback_outbox WHERE seq = ?", (seq,))
        conn.commit()
    finally:
        conn.close()


def _outbox_count() -> int:
    conn = mirror_connect()
    try:
        return int(conn.execute("SELECT COUNT(*) FROM fallback_outbox").fetchone()[0])
    finally:
        conn.close()


def _reset_for_tests() -> None:
    """Restore pristine module state (tests only)."""
    global _mirror_path, _outbox_remaining
    _mirror_path = None
    _outbox_remaining = False
    for k, v in {
        "active": False, "reason": None, "since": None, "recovered_at": None,
        "failures": 0, "last_error": None, "probes": 0, "drained": 0,
        "dropped": 0, "flips": 0, "_last_probe_at": 0.0,
        "_last_probe_log": 0.0, "_last_drain_at": 0.0,
    }.items():
        _state[k] = v
