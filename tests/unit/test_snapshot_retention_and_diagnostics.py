"""Snapshot retention + the cross-module diagnostics hub."""
import os
import time

from src.core.snapshot.retention import sweep


def _bundle(base, name, size, age_days):
    d = base / "site" / "mod" / "comp" / "20260101" / name
    d.mkdir(parents=True)
    (d / "body.txt").write_text("x" * size)
    meta = d / "metadata.json"
    meta.write_text("{}")
    t = time.time() - age_days * 86400
    os.utime(meta, (t, t))
    return d


def test_sweep_deletes_by_age_then_size_and_prunes_empty_dirs(tmp_path):
    old = _bundle(tmp_path, "old", 10, age_days=30)
    a = _bundle(tmp_path, "a", 600_000, age_days=3)
    b = _bundle(tmp_path, "b", 600_000, age_days=1)
    dry = sweep(str(tmp_path), days=14, max_mb=1, dry_run=True)
    assert dry["deleted"] == 2 and old.exists() and a.exists()          # dry run touches nothing
    r = sweep(str(tmp_path), days=14, max_mb=1)
    assert r["by_reason"] == {"age": 1, "size": 1}
    assert not old.exists() and not a.exists() and b.exists()           # oldest dropped until it fits
    assert r["kept"] == 1


def test_sweep_leaves_everything_when_within_limits_and_removes_empty_dirs(tmp_path):
    keep = _bundle(tmp_path, "keep", 10, age_days=1)
    assert sweep(str(tmp_path), days=14, max_mb=100)["deleted"] == 0 and keep.exists()
    (tmp_path / "empty" / "nested").mkdir(parents=True)
    sweep(str(tmp_path), days=14, max_mb=100)
    assert not (tmp_path / "empty").exists()


def test_diagnostics_hub_health_and_failure(tmp_path, monkeypatch):
    import src.observability.diagnostics as diag
    from src.security.evidence import EvidenceLog
    monkeypatch.setattr(diag, "_evidence", EvidenceLog(tmp_path / "ev", snapshot_dir=str(tmp_path / "snaps")))
    seen = []
    diag.add_health_sink(lambda **kw: seen.append(kw))
    try:
        diag.report_request("h", "https://h/x", 200, 12.0, 5)
        diag.report_failure("http_error", "h", "https://h/x", status=500, body="boom")
    finally:
        diag._health_sinks.clear()
    assert seen[0]["ok"] is True and seen[0]["status"] == 200
    assert diag.health_summary()["h"]["requests"] == 1 and diag.health_summary()["h"]["success_rate"] == 1.0
    diag.reset_health()
    assert list((tmp_path / "snaps").rglob("metadata.json"))          # the failure kept its evidence
    assert diag.evidence_log().read(days=1)[0]["kind"] == "http_error"


def test_network_client_reports_health_and_failures(tmp_path, monkeypatch):
    import asyncio
    import httpx
    import src.observability.diagnostics as diag
    from src.network.direct_api.client import AsyncHttpClient
    from src.security.evidence import EvidenceLog
    monkeypatch.setattr(diag, "_evidence", EvidenceLog(tmp_path / "ev", snapshot_dir=str(tmp_path / "snaps")))
    seen = []
    diag.add_health_sink(lambda **kw: seen.append(kw))

    async def run():
        async with AsyncHttpClient() as c:
            c._client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503, text="down")))
            await c.get("https://svc.example/api").execute()
    try:
        asyncio.run(run())
    finally:
        diag._health_sinks.clear()
    assert seen and seen[0]["status"] == 503 and seen[0]["ok"] is False
    assert any(r["kind"] == "http_error" for r in diag.evidence_log().read(days=1))
