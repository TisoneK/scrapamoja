"""Unit tests for proxy-verification retry on flaky tunnels.

Ephemeral bore/gost tunnels drop connections intermittently. A single
ReadError on the pre-flight egress check must NOT abort a multi-minute
scrape (Session 25: two live runs aborted on a transient verify error even
though the tunnel answered on the next request). A definitive country
mismatch, by contrast, must fail fast.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import src.sites.betb2b.session as session_mod
from src.sites.betb2b.config import DEFAULT_SKIN_CONFIG
from src.sites.betb2b.session import BetB2BSessionManager


def _ok(country="KE"):
    return SimpleNamespace(ok=True, country_code=country, error=None,
                           egress_ip="102.210.56.70", latency_ms=3000.0)


def _unreachable():
    return SimpleNamespace(ok=False, country_code=None, error="ReadError",
                           egress_ip=None, latency_ms=None)


def _manager():
    proxy = SimpleNamespace(id="kenya", is_direct=False)
    return BetB2BSessionManager(
        DEFAULT_SKIN_CONFIG, proxy=proxy,  # type: ignore[arg-type]
        proxy_verify_backoff=0.0,  # no real sleeping in tests
    )


async def test_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    async def fake_verify(proxy, **kw):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("ReadError")  # transient
        return _ok()

    monkeypatch.setattr(session_mod, "verify_proxy", fake_verify)
    mgr = _manager()
    assert await mgr._verify_proxy_country() is True
    assert calls["n"] == 3  # failed twice, succeeded on the third


async def test_transient_unreachable_then_ok(monkeypatch):
    seq = [_unreachable(), _ok()]

    async def fake_verify(proxy, **kw):
        return seq.pop(0)

    monkeypatch.setattr(session_mod, "verify_proxy", fake_verify)
    mgr = _manager()
    assert await mgr._verify_proxy_country() is True
    assert seq == []


async def test_gives_up_after_all_attempts(monkeypatch):
    calls = {"n": 0}

    async def fake_verify(proxy, **kw):
        calls["n"] += 1
        raise RuntimeError("ReadError")

    monkeypatch.setattr(session_mod, "verify_proxy", fake_verify)
    mgr = _manager()  # default 3 attempts
    assert await mgr._verify_proxy_country() is False
    assert calls["n"] == 3


async def test_country_mismatch_fails_fast(monkeypatch):
    calls = {"n": 0}

    async def fake_verify(proxy, **kw):
        calls["n"] += 1
        return _ok(country="US")  # answered, wrong country

    monkeypatch.setattr(session_mod, "verify_proxy", fake_verify)
    mgr = _manager()
    assert await mgr._verify_proxy_country() is False
    assert calls["n"] == 1  # no retry on a definitive mismatch
