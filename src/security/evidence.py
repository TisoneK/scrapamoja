"""Evidence: what a blocked or failed request actually looked like, captured automatically.

Diagnosing a block used to mean re-creating it by hand (curl probes, a browser, guessing which
host dropped us). The guard is the one place every request passes through, so it records the
evidence the moment something goes wrong:

* ``block``       — a response the guard classified as a challenge / geo block / ban / ...
* ``unreachable`` — a request that got no answer at all (timeout, dropped connection)
* ``discovery``   — listings skipped before any request (outrights, placeholders)

A response is stored in the snapshot system's own *normalised* form
(:func:`src.core.snapshot.normalize.normalize_captured_response`: volatile query params and
JSON keys redacted, body truncated, SHA-256 of the body) so records are small, stable and can be
compared run to run with the same tooling. Records go to one JSON-lines file per day beside the
block ledger; old days are deleted. Recording never raises and never blocks a scrape.

Read it with ``python -m src.security evidence``.
"""

from __future__ import annotations

import atexit
import collections
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

ENV_DIR = "SCRAPAMOJA_EVIDENCE_DIR"
KEEP_DAYS = 7
# Identical failures (same site, kind, status, body hash / error) are written in full this many
# times per process; later repeats are only counted (see the closing summary record).
FULL_RECORDS_PER_SIGNATURE = 3
MAX_BODY_CHARS = 2000
# A response shape is only called drift once this many responses have taught the baseline which
# fields are optional (a single match lacks e.g. period scores that the next one has).
WARMUP_RESPONSES = 300


def default_dir() -> Path:
    if os.environ.get(ENV_DIR):
        return Path(os.environ[ENV_DIR])
    from .ledger import default_dir as ledger_dir          # same place as ledger.json
    return ledger_dir() / "evidence"


def _normalise(url: str, status: Optional[int], method: str,
               request_headers: Optional[Mapping[str, str]],
               response_headers: Optional[Mapping[str, str]],
               body: Any) -> Dict[str, Any]:
    """The snapshot system's normalised response record (falls back to a plain excerpt)."""
    try:
        from src.core.snapshot.normalize import NormalizerConfig, normalize_captured_response
        return normalize_captured_response(
            url, int(status or 0), method, dict(request_headers or {}),
            {str(k).lower(): str(v) for k, v in (response_headers or {}).items()}, body,
            NormalizerConfig(max_body_chars=MAX_BODY_CHARS))
    except Exception:  # noqa: BLE001 — evidence must never depend on the snapshot package importing
        text = body.decode("utf-8", "replace") if isinstance(body, bytes) else (body or "")
        return {"path": url.split("?")[0], "method": method, "status": status,
                "body": str(text)[:MAX_BODY_CHARS], "body_bytes": len(text)}


class EvidenceLog:
    def __init__(self, directory: Optional[Path] = None, *, keep_days: int = KEEP_DAYS,
                 clock=time.time, snapshots: bool = True, snapshot_dir: Optional[str] = None):
        self.dir = Path(directory) if directory else default_dir()
        self.keep_days = keep_days
        self._clock = clock
        self._seen: collections.Counter = collections.Counter()
        self._swept = False
        self._registered = False
        # Cross-cutting outputs. Every kept record is also (a) written as a snapshot bundle in the
        # snapshot system's own layout (so `data/snapshots/` has the full evidence for
        # an escalation) and (b) handed to sinks -- telemetry, alerting, a dashboard -- registered
        # by whichever module owns them. Both are best-effort.
        self.snapshots = snapshots
        self.snapshot_dir = snapshot_dir or os.environ.get("SCRAPAMOJA_SNAPSHOT_DIR", "data/snapshots")
        self.sinks: List[Callable[[Dict[str, Any]], None]] = []

    # -- writing ------------------------------------------------------------ #
    def record(self, kind: str, site: str, *, url: str = "", status: Optional[int] = None,
               method: str = "GET", request_headers: Optional[Mapping[str, str]] = None,
               response_headers: Optional[Mapping[str, str]] = None, body: Any = None,
               verdict: Any = None, error: Optional[BaseException] = None,
               scope: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        try:
            response = _normalise(url, status, method, request_headers, response_headers, body) \
                if (body is not None or response_headers is not None or status) else None
            sig = "|".join(str(x) for x in (
                site, kind, status, (response or {}).get("body_sha256", ""),
                type(error).__name__ if error else "", getattr(verdict, "type", "")))
            self._seen[sig] += 1
            if self._seen[sig] > FULL_RECORDS_PER_SIGNATURE:
                return                                        # counted; summarised at exit
            rec: Dict[str, Any] = {"ts": self._iso(), "kind": kind, "site": site, "scope": scope,
                                   "url": _strip_query(url), "status": status}
            if verdict is not None:
                rec["verdict"] = {"type": getattr(getattr(verdict, "type", None), "value", None),
                                  "vendor": getattr(verdict, "vendor", None),
                                  "evidence": list(getattr(verdict, "evidence", []) or [])[:5]}
            if error is not None:
                rec["error"] = f"{type(error).__name__}: {str(error)[:200]}"
            if response is not None:
                rec["response"] = response
            if extra:
                rec["extra"] = extra
            if self.snapshots and kind in ("block", "unreachable", "http_error") and body is not None:
                from src.core.snapshot.api_capture import capture_response_bundle
                bundle = capture_response_bundle(
                    site=site, module="security", component=kind, url=url, status=status,
                    method=method, request_headers=request_headers,
                    response_headers=response_headers, body=body, base_path=self.snapshot_dir,
                    note=(rec.get("verdict") or {}).get("type") or rec.get("error"))
                if bundle:
                    rec["snapshot_bundle"] = str(bundle)
            self._append(rec)
            self._notify(rec)
            if not self._registered:
                atexit.register(self.flush)
                self._registered = True
        except Exception:  # noqa: BLE001 — never break a scrape over its own diagnostics
            pass

    def add_sink(self, sink: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callable that receives every stored record (telemetry, alerting, ...)."""
        self.sinks.append(sink)

    def _notify(self, rec: Dict[str, Any]) -> None:
        for sink in list(self.sinks):
            try:
                sink(rec)
            except Exception:  # noqa: BLE001 -- a broken sink must not break the scrape
                pass

    def flush(self) -> None:
        """Write a closing summary of the repeats that were counted but not stored."""
        try:
            extra = {s: n - FULL_RECORDS_PER_SIGNATURE for s, n in self._seen.items()
                     if n > FULL_RECORDS_PER_SIGNATURE}
            if extra:
                self._append({"ts": self._iso(), "kind": "summary", "repeats_not_stored": extra})
                self._seen.clear()
        except Exception:  # noqa: BLE001
            pass

    def _append(self, rec: Dict[str, Any]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        if not self._swept:
            self._sweep()
            self._swept = True
        day = datetime.fromtimestamp(self._clock(), timezone.utc).strftime("%Y%m%d")
        with open(self.dir / f"evidence-{day}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str, sort_keys=True) + "\n")

    def _sweep(self) -> None:
        cutoff = self._clock() - self.keep_days * 86400
        for f in self.dir.glob("evidence-*.jsonl"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
            except OSError:
                pass

    def _iso(self) -> str:
        return datetime.fromtimestamp(self._clock(), timezone.utc).isoformat(timespec="seconds")

    def check_shape(self, site: str, endpoint: str, decoded: Any) -> Optional[Dict[str, Any]]:
        """Compare this response's structure with the baseline kept for (site, endpoint).

        The baseline is the union of every shape seen, so optional fields that appear only for
        some matches do not alarm. New paths are written as a ``drift`` record (the API contract changed) and
        returned. Vanished keys are deliberately not reported: error replies legitimately lack them. The first sighting only saves
        the baseline. Never raises.
        """
        try:
            if not isinstance(decoded, (dict, list)) or not decoded:
                return None
            shape = shape_of(decoded)
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in f"{site}__{endpoint}")
            path = self.dir / "shapes" / f"{safe}.json"
            saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            base = set(saved["paths"]) if saved else None
            seen = saved["seen"] if saved else 0
            if base is not None and shape <= base:
                if seen < WARMUP_RESPONSES or seen % 50 == 0:      # cheap counter, rarely rewritten
                    path.write_text(json.dumps({"seen": seen + 1, "paths": sorted(base)}), encoding="utf-8")
                return None
            added = sorted(shape - base) if base is not None else []
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"seen": seen + 1, "paths": sorted((base or set()) | shape)}),
                            encoding="utf-8")
            if base is None or seen < WARMUP_RESPONSES:
                return None            # still learning which fields are optional
            diff = {"added": added[:40], "added_total": len(added)}
            rec = {"ts": self._iso(), "kind": "drift", "site": site, "endpoint": endpoint, **diff}
            self._append(rec)
            self._notify(rec)
            return diff
        except Exception:  # noqa: BLE001
            return None

    # -- reading ------------------------------------------------------------ #
    def read(self, days: int = 1, site: Optional[str] = None) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        cutoff = self._clock() - days * 86400
        for f in sorted(self.dir.glob("evidence-*.jsonl")):
            try:
                if f.stat().st_mtime < cutoff:
                    continue
                for line in f.read_text(encoding="utf-8").splitlines():
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if site is None or r.get("site") == site:
                        out.append(r)
            except OSError:
                continue
        return out

    @staticmethod
    def summarise(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group by (site, kind, status, verdict type/vendor, error class) with a count and the
        latest example — the 'what is going wrong, how often' view."""
        groups: Dict[tuple, Dict[str, Any]] = {}
        for r in records:
            if r.get("kind") == "summary":
                continue
            v = r.get("verdict") or {}
            err = (r.get("error") or "").split(":")[0]
            if r.get("kind") == "drift":
                err = r.get("endpoint", "")
            key = (r.get("site"), r.get("kind"), r.get("status"), v.get("type"), v.get("vendor"), err)
            g = groups.setdefault(key, {"site": key[0], "kind": key[1], "status": key[2],
                                        "type": key[3], "vendor": key[4], "error": err or None,
                                        "count": 0, "first": r.get("ts"), "last": r.get("ts"),
                                        "example": None})
            g["count"] += 1
            g["last"] = r.get("ts")
            body = (r.get("response") or {}).get("body")
            g["example"] = {"url": r.get("url"), "body": (body if isinstance(body, str) else json.dumps(body))[:160] if body else None}
        return sorted(groups.values(), key=lambda g: (-g["count"], str(g["site"])))


def shape_of(obj: Any, prefix: str = "") -> set:
    """The *structure* of a decoded JSON body as ``{"Value.E[].C:float", ...}``.

    Values change on every request (odds, scores), so a hash can never tell "the API changed"
    from "the match moved". Key paths and value types can: lists are collapsed to ``[]`` and the
    shapes of all their items are unioned.
    """
    out: set = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out |= shape_of(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for item in obj:
            out |= shape_of(item, prefix + "[]")
        if not obj:
            out.add(prefix + "[]")
    else:
        kind = "null" if obj is None else "bool" if isinstance(obj, bool) else \
            "number" if isinstance(obj, (int, float)) else "str" if isinstance(obj, str) else "other"
        out.add(f"{prefix}:{kind}")
    return out


def _strip_query(url: str) -> str:
    return url.split("?")[0] if url else url
