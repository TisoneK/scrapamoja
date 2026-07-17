"""Tests for src.network.proxy.verify.

The formatting test is a pure unit test. The probes hit the network (ipify /
ip-api) so they are marked ``integration`` and deselected by default.
"""

from __future__ import annotations

import pytest

from src.network.proxy.models import ProxyEndpoint
from src.network.proxy.verify import ProxyCheckResult, verify_proxy


def test_check_result_str_ok():
    r = ProxyCheckResult(endpoint_id="k", ok=True, egress_ip="1.2.3.4",
                         country_code="KE", latency_ms=123.4)
    s = str(r)
    assert "1.2.3.4" in s and "KE" in s and "123ms" in s


def test_check_result_str_failed():
    r = ProxyCheckResult(endpoint_id="k", ok=False, error="ConnectError: nope")
    assert "FAILED" in str(r)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_direct_probe_returns_our_ip():
    result = await verify_proxy(ProxyEndpoint.direct(), with_geo=False)
    assert result.ok
    assert result.egress_ip


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dead_proxy_reports_failure_not_raises():
    dead = ProxyEndpoint.from_url("http://127.0.0.1:1", id="dead")
    result = await verify_proxy(dead, timeout=3)
    assert not result.ok
    assert result.error
