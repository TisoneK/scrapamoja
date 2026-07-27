"""HTTP contract + auth for the betb2b scraper control API.

The background runner is stubbed to a no-op here so jobs stay 'queued' and the
tests are deterministic (no browser, no timing). The runner's execution logic
is covered separately in tests/unit/test_scraper_service.py.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

KEY = "secret-test-key"
HDR = {"x-api-key": KEY}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SCRAPER_API_KEY", KEY)
    from src.api.routers import scraper as sc

    sc.service.path = str(tmp_path / "odds.db")

    async def _noop():
        return None

    monkeypatch.setattr(sc.service, "start", _noop)
    monkeypatch.setattr(sc.service, "stop", _noop)

    from src.api.main import create_app

    with TestClient(create_app()) as c:
        yield c


def test_missing_key_is_401(client):
    assert client.get("/api/scraper/runs").status_code == 401


def test_wrong_key_is_401(client):
    assert client.get("/api/scraper/runs", headers={"x-api-key": "nope"}).status_code == 401


def test_no_key_configured_is_503(client, monkeypatch):
    monkeypatch.delenv("SCRAPER_API_KEY", raising=False)
    assert client.get("/api/scraper/runs", headers=HDR).status_code == 503


def test_list_runs_empty(client):
    r = client.get("/api/scraper/runs", headers=HDR)
    assert r.status_code == 200 and r.json() == []


def test_trigger_queues_a_job(client):
    r = client.post("/api/scraper/runs", headers=HDR,
                    json={"skin": "linebet", "action": "live", "sport": "basketball"})
    assert r.status_code == 202
    job = r.json()
    assert job["status"] == "queued"
    assert job["action"] == "list_live"      # 'live' alias resolved
    assert job["skin"] == "linebet"
    # Round-trips via GET.
    got = client.get(f"/api/scraper/runs/{job['job_id']}", headers=HDR)
    assert got.status_code == 200 and got.json()["job_id"] == job["job_id"]


def test_action_alias_and_validation(client):
    ok = client.post("/api/scraper/runs", headers=HDR,
                     json={"skin": "linebet", "action": "all"})
    assert ok.status_code == 202 and ok.json()["action"] == "list_all"
    bad = client.post("/api/scraper/runs", headers=HDR,
                      json={"skin": "linebet", "action": "bogus"})
    assert bad.status_code == 422


def test_unknown_job_404(client):
    assert client.get("/api/scraper/runs/999999", headers=HDR).status_code == 404


def test_skins_and_sports(client):
    skins = client.get("/api/scraper/skins", headers=HDR).json()["skins"]
    assert "linebet" in skins
    sports = client.get("/api/scraper/sports", headers=HDR).json()["sports"]
    assert "basketball" in sports


def test_counts_endpoint(client):
    counts = client.get("/api/scraper/counts", headers=HDR).json()
    assert "events" in counts and "odds_snapshots" in counts
