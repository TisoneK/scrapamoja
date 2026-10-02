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
from typing import Any, Dict, Iterable, List, Mapping, Optional

ENV_DIR = "SCRAPAMOJA_EVIDENCE_DIR"
KEEP_DAYS = 7
# Identical failures (same site, kind, status, body hash / error) are written in full this many
# times per process; later repeats are only counted (see the closing summary record).
FULL_RECORDS_PER_SIGNATURE = 3
MAX_BODY_CHARS = 2000


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
                 clock=time.time):
        self.dir = Path(directory) if directory else default_dir()
        self.keep_days = keep_days
        self._clock = clock
        self._seen: collections.Counter = collections.Counter()
        self._swept = False
        self._registered = False

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
            self._append(rec)
            if not self._registered:
                atexit.register(self.flush)
                self._registered = True
        except Exception:  # noqa: BLE001 — never break a scrape over its own diagnostics
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


def _strip_query(url: str) -> str:
    return url.split("?")[0] if url else url
