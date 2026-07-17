"""Unit tests for src.network.proxy.manager — rotation, health, failover, routing.

No network; failover tests use in-memory async operations.
"""

from __future__ import annotations

import pytest

from src.network.proxy.manager import (
    NoHealthyProxyError,
    ProxyManager,
    RotationStrategy,
    RoutingRule,
)
from src.network.proxy.models import ProxyEndpoint, ProxySource
from src.network.proxy.providers import DirectProvider, StaticProvider


def _ep(id, host="h", port=8080, source=ProxySource.MANUAL, country=None):
    return ProxyEndpoint.from_url(
        f"http://{host}:{port}", id=id, source=source, country=country
    )


def _manager(ids, **kwargs):
    return ProxyManager(providers=[StaticProvider([_ep(i) for i in ids])], **kwargs)


class TestPool:
    def test_default_pool_is_direct(self):
        m = ProxyManager()
        assert len(m.endpoints) == 1
        assert m.endpoints[0].is_direct

    def test_add_endpoint(self):
        m = ProxyManager(providers=[DirectProvider()])
        m.add_endpoint(_ep("a"))
        assert {e.id for e in m.endpoints} == {"direct", "a"}


class TestRotation:
    def test_round_robin_cycles(self):
        m = _manager(["a", "b", "c"], strategy=RotationStrategy.ROUND_ROBIN)
        seen = [m.acquire().id for _ in range(6)]
        assert seen == ["a", "b", "c", "a", "b", "c"]

    def test_sticky_keeps_one_until_failure(self):
        m = _manager(["a", "b"], strategy=RotationStrategy.STICKY)
        first = m.acquire().id
        assert m.acquire().id == first
        m.report_failure(first, "boom")
        assert m.acquire().id != first  # released stickiness, picks the other

    def test_health_weighted_prefers_higher_success(self):
        m = _manager(["a", "b"], strategy=RotationStrategy.HEALTH_WEIGHTED)
        # Make "a" worse than "b".
        m.report_failure("a", "e")
        m.report_success("b", 100)
        assert m.acquire().id == "b"


class TestFailoverSelection:
    def test_dead_endpoint_skipped(self):
        m = _manager(["a", "b"], strategy=RotationStrategy.ROUND_ROBIN)
        m.mark_dead("a")
        assert all(m.acquire().id == "b" for _ in range(3))

    def test_all_dead_raises(self):
        m = _manager(["a"], strategy=RotationStrategy.ROUND_ROBIN)
        m.mark_dead("a")
        with pytest.raises(NoHealthyProxyError):
            m.acquire()

    def test_reset_revives(self):
        m = _manager(["a"])
        m.mark_dead("a")
        m.reset("a")
        assert m.acquire().id == "a"


class TestRouting:
    def test_route_by_exact_id(self):
        m = ProxyManager(
            providers=[StaticProvider([
                ProxyEndpoint.direct(),
                _ep("kenya", country="KE"),
            ])],
            routing_rules=[RoutingRule("linebet.com", "kenya")],
            default_target="direct",
        )
        assert m.acquire(site="linebet.com").id == "kenya"
        assert m.acquire(site="github.com").id == "direct"

    def test_route_wildcard_and_url(self):
        m = ProxyManager(
            providers=[StaticProvider([ProxyEndpoint.direct(), _ep("kenya")])],
            routing_rules=[RoutingRule("*.linebet.com", "kenya")],
            default_target="direct",
        )
        assert m.acquire(site="https://m.linebet.com/en/live").id == "kenya"

    def test_route_by_source_group(self):
        m = ProxyManager(
            providers=[StaticProvider([
                ProxyEndpoint.direct(),
                _ep("k1", source=ProxySource.NGROK),
            ])],
            routing_rules=[RoutingRule("linebet.com", "ngrok")],
        )
        assert m.acquire(site="linebet.com").id == "k1"

    def test_unmatched_falls_back_to_default(self):
        m = ProxyManager(
            providers=[StaticProvider([ProxyEndpoint.direct(), _ep("a")])],
            default_target="direct",
        )
        assert m.acquire(site="whatever.com").id == "direct"


class TestWithFailover:
    @pytest.mark.asyncio
    async def test_succeeds_first_try(self):
        m = _manager(["a", "b"])
        calls = []

        async def op(ep):
            calls.append(ep.id)
            return "ok"

        assert await m.with_failover(op) == "ok"
        assert len(calls) == 1
        assert m.health_of(calls[0]).successes == 1

    @pytest.mark.asyncio
    async def test_fails_over_to_next(self):
        m = _manager(["a", "b"], strategy=RotationStrategy.ROUND_ROBIN)
        attempted = []

        async def op(ep):
            attempted.append(ep.id)
            if ep.id == "a":
                raise RuntimeError("a is down")
            return "recovered"

        result = await m.with_failover(op, max_tries=3)
        assert result == "recovered"
        assert attempted[0] == "a" and "b" in attempted
        assert m.health_of("a").failures >= 1

    @pytest.mark.asyncio
    async def test_raises_when_all_fail(self):
        m = _manager(["a", "b"])

        async def op(ep):
            raise RuntimeError("everything is down")

        with pytest.raises(RuntimeError, match="down"):
            await m.with_failover(op, max_tries=4)
