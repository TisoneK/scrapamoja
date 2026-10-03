"""One place every module reports to, so an escalation can be diagnosed from the same evidence
whatever fetched the data (browser, httpx feed client, the generic network client, ...).

* **snapshots capture failures** -- :func:`report_failure` records a block / HTTP error / dead host
  in the evidence log, which also writes a snapshot bundle (``data/snapshots/<site>/...``).
* **telemetry reports health**  -- :func:`report_request` is called for EVERY request; whoever owns
  a telemetry system subscribes with :func:`add_health_sink` and aggregates (rate, latency, status).

Both are best-effort and never raise: diagnostics must not break the work they describe.
"""

from __future__ import annotations

from typing import Any, Callable, List, Mapping, Optional

_health_sinks: List[Callable[..., None]] = []
_evidence = None


def add_health_sink(sink: Callable[..., None]) -> None:
    """``sink(site=, url=, status=, latency_ms=, body_bytes=, ok=)`` for every request."""
    if sink not in _health_sinks:
        _health_sinks.append(sink)


def remove_health_sink(sink: Callable[..., None]) -> None:
    if sink in _health_sinks:
        _health_sinks.remove(sink)


def evidence_log():
    """The process-wide evidence log (the security guard keeps its own per-site one)."""
    global _evidence
    if _evidence is None:
        from src.security.evidence import EvidenceLog
        _evidence = EvidenceLog()
    return _evidence


_stats: dict = {}


def health_summary() -> dict:
    """Per-site view of every request reported in this process: count, success rate, status
    histogram, latency p50/p95/max. Works with no telemetry system attached."""
    out = {}
    for site, st in _stats.items():
        lat = sorted(st["lat"])
        pick = lambda q: round(lat[min(len(lat) - 1, int(q * len(lat)))], 1) if lat else 0.0
        out[site] = {"requests": st["n"], "success_rate": round(st["ok"] / st["n"], 3),
                     "status": dict(st["status"]),
                     "latency_ms": {"p50": pick(0.5), "p95": pick(0.95), "max": round(lat[-1], 1) if lat else 0.0}}
    return out


def reset_health() -> None:
    _stats.clear()


def report_request(site: str, url: str, status: int, latency_ms: float = 0.0,
                   body_bytes: int = 0) -> None:
    try:
        st = _stats.setdefault(site, {"n": 0, "ok": 0, "status": {}, "lat": []})
        st["n"] += 1
        st["ok"] += int(200 <= status < 300)
        st["status"][str(status)] = st["status"].get(str(status), 0) + 1
        st["lat"].append(latency_ms)
        del st["lat"][:-2000]                       # bounded memory in a long-running process
    except Exception:  # noqa: BLE001
        pass
    for sink in list(_health_sinks):
        try:
            sink(site=site, url=url, status=status, latency_ms=latency_ms, body_bytes=body_bytes,
                 ok=200 <= status < 300)
        except Exception:  # noqa: BLE001
            pass


def report_failure(kind: str, site: str, url: str, *, status: Optional[int] = None,
                   headers: Optional[Mapping[str, str]] = None, body: Any = None,
                   error: Optional[BaseException] = None, method: str = "GET") -> None:
    try:
        evidence_log().record(kind, site, url=url, status=status, method=method,
                              response_headers=headers, body=body, error=error)
    except Exception:  # noqa: BLE001
        pass
