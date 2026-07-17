"""ProxyManager — the single chokepoint every outbound connection asks for a proxy.

The scraper never constructs Playwright proxy dicts or httpx proxy URLs itself.
It asks the manager: ``endpoint = manager.acquire(site="linebet.com")`` and renders
via the endpoint. The manager owns the pool, rotation strategy, per-endpoint health,
failover (skipping unhealthy endpoints), and per-site routing rules.

Rotation strategies (``RotationStrategy``) are named to align with
``src/stealth/models.py::ProxyRotationStrategy`` for the planned convergence.

Module: src.network.proxy.manager
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Dict, List, Optional, Sequence, TypeVar

from .models import ProxyEndpoint, ProxyHealth
from .providers import DirectProvider, ProxyProvider, StaticProvider

logger = logging.getLogger(__name__)

__all__ = [
    "RotationStrategy",
    "RoutingRule",
    "ProxyManager",
    "NoHealthyProxyError",
]

T = TypeVar("T")


class RotationStrategy(str, Enum):
    """How ``acquire`` picks among the eligible (healthy) endpoints."""

    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    STICKY = "sticky"           # keep using one endpoint until it fails
    HEALTH_WEIGHTED = "health_weighted"  # prefer higher success-rate / lower latency


class NoHealthyProxyError(RuntimeError):
    """Raised when routing/rotation cannot find any healthy endpoint."""


@dataclass
class RoutingRule:
    """Map a host/URL pattern to a preferred endpoint id or source-group.

    ``pattern`` is a glob-ish string (``*`` wildcard). ``target`` is an endpoint
    ``id``. The first matching rule wins; if no rule matches, the manager's
    default applies.
    """

    pattern: str
    target: str

    def matches(self, host: str) -> bool:
        regex = "^" + re.escape(self.pattern).replace(r"\*", ".*") + "$"
        return re.match(regex, host, re.IGNORECASE) is not None


def _host_of(site: Optional[str]) -> Optional[str]:
    if not site:
        return None
    s = site.strip()
    if "://" in s:
        from urllib.parse import urlparse

        s = urlparse(s).hostname or s
    else:
        s = s.split("/", 1)[0]
    return s.lower() or None


class ProxyManager:
    """Owns the proxy pool and hands out endpoints on request.

    Typical use::

        manager = ProxyManager(providers=[DirectProvider(), StaticProvider([...])])
        ep = manager.acquire(site="linebet.com")
        # ... use ep.to_playwright_proxy() / ep.to_httpx_proxy() ...
        manager.report_success(ep.id, latency_ms=180)
    """

    def __init__(
        self,
        providers: Optional[Sequence[ProxyProvider]] = None,
        *,
        strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN,
        routing_rules: Optional[Sequence[RoutingRule]] = None,
        default_target: Optional[str] = None,
    ) -> None:
        self._providers: List[ProxyProvider] = list(providers) if providers else [DirectProvider()]
        self.strategy = strategy
        self.routing_rules: List[RoutingRule] = list(routing_rules or [])
        # Endpoint id to fall back on when no routing rule matches (e.g. "direct").
        self.default_target = default_target

        self._pool: Dict[str, ProxyEndpoint] = {}
        self._health: Dict[str, ProxyHealth] = {}
        self._rr_index = 0
        self._sticky_id: Optional[str] = None
        self._refresh_pool()

    # ------------------------------------------------------------------ #
    # Pool management
    # ------------------------------------------------------------------ #
    def _refresh_pool(self) -> None:
        for provider in self._providers:
            for ep in provider.endpoints():
                if ep.id not in self._pool:
                    self._pool[ep.id] = ep
                    self._health[ep.id] = ProxyHealth()

    def add_provider(self, provider: ProxyProvider) -> None:
        self._providers.append(provider)
        self._refresh_pool()

    def add_endpoint(self, endpoint: ProxyEndpoint) -> None:
        self.add_provider(StaticProvider([endpoint]))

    @property
    def endpoints(self) -> List[ProxyEndpoint]:
        return list(self._pool.values())

    def health_of(self, endpoint_id: str) -> Optional[ProxyHealth]:
        return self._health.get(endpoint_id)

    def get(self, endpoint_id: str) -> Optional[ProxyEndpoint]:
        return self._pool.get(endpoint_id)

    # ------------------------------------------------------------------ #
    # Routing + selection
    # ------------------------------------------------------------------ #
    def _target_for(self, site: Optional[str]) -> Optional[str]:
        host = _host_of(site)
        if host:
            for rule in self.routing_rules:
                if rule.matches(host):
                    return rule.target
        return self.default_target

    def _eligible(self, target: Optional[str]) -> List[ProxyEndpoint]:
        """Healthy endpoints, optionally filtered to a routing target.

        ``target`` may name a specific endpoint id or a ``ProxySource`` value
        (e.g. ``"ngrok"``) to select a group.
        """
        healthy = [ep for ep in self._pool.values() if self._health[ep.id].is_healthy]
        if not target:
            return healthy
        # Exact endpoint id match takes precedence.
        exact = [ep for ep in healthy if ep.id == target]
        if exact:
            return exact
        # Otherwise treat target as a source group.
        group = [ep for ep in healthy if ep.source.value == target]
        return group or healthy  # fall back to any healthy if target unmatched

    def acquire(self, site: Optional[str] = None) -> ProxyEndpoint:
        """Return an endpoint to use, honoring routing then rotation + health.

        Raises :class:`NoHealthyProxyError` if nothing eligible remains.
        """
        target = self._target_for(site)
        candidates = self._eligible(target)
        if not candidates:
            raise NoHealthyProxyError(
                f"no healthy proxy for site={site!r} (target={target!r})"
            )
        ep = self._select(candidates)
        from datetime import datetime

        self._health[ep.id].last_used = datetime.now()
        return ep

    def _select(self, candidates: List[ProxyEndpoint]) -> ProxyEndpoint:
        if self.strategy is RotationStrategy.RANDOM:
            return random.choice(candidates)

        if self.strategy is RotationStrategy.STICKY:
            if self._sticky_id:
                for ep in candidates:
                    if ep.id == self._sticky_id:
                        return ep
            self._sticky_id = candidates[0].id
            return candidates[0]

        if self.strategy is RotationStrategy.HEALTH_WEIGHTED:
            def score(ep: ProxyEndpoint) -> tuple:
                h = self._health[ep.id]
                latency = h.ewma_latency_ms if h.ewma_latency_ms is not None else 0.0
                # Higher success first, then lower latency.
                return (-h.success_rate, latency)

            return sorted(candidates, key=score)[0]

        # ROUND_ROBIN (default)
        ep = candidates[self._rr_index % len(candidates)]
        self._rr_index += 1
        return ep

    # ------------------------------------------------------------------ #
    # Health reporting
    # ------------------------------------------------------------------ #
    def report_success(self, endpoint_id: str, latency_ms: Optional[float] = None) -> None:
        h = self._health.get(endpoint_id)
        if h:
            h.record_success(latency_ms)

    def report_failure(self, endpoint_id: str, error: Optional[str] = None) -> None:
        h = self._health.get(endpoint_id)
        if h:
            h.record_failure(error)
            if h.dead:
                logger.warning("proxy %s marked dead: %s", endpoint_id, error)
            # A sticky endpoint that failed should release its stickiness.
            if self._sticky_id == endpoint_id:
                self._sticky_id = None

    def mark_dead(self, endpoint_id: str) -> None:
        h = self._health.get(endpoint_id)
        if h:
            h.dead = True
            if self._sticky_id == endpoint_id:
                self._sticky_id = None

    def reset(self, endpoint_id: str) -> None:
        h = self._health.get(endpoint_id)
        if h:
            h.reset()

    def reset_all(self) -> None:
        for h in self._health.values():
            h.reset()

    # ------------------------------------------------------------------ #
    # Failover helper
    # ------------------------------------------------------------------ #
    async def with_failover(
        self,
        operation: Callable[[ProxyEndpoint], Awaitable[T]],
        *,
        site: Optional[str] = None,
        max_tries: int = 3,
    ) -> T:
        """Run ``operation(endpoint)``, retrying on the next healthy endpoint.

        On each failure the endpoint is reported failed (so it may drop out of
        the healthy set) and the next ``acquire`` picks another. Re-raises the
        last exception if all tries are exhausted.
        """
        import time

        last_exc: Optional[BaseException] = None
        for _ in range(max_tries):
            try:
                ep = self.acquire(site=site)
            except NoHealthyProxyError:
                # Pool exhausted mid-failover: surface the real operational
                # error if we have one, else the exhaustion error itself.
                if last_exc is not None:
                    break
                raise
            start = time.monotonic()
            try:
                result = await operation(ep)
                self.report_success(ep.id, (time.monotonic() - start) * 1000.0)
                return result
            except Exception as exc:  # noqa: BLE001 - failover is intentionally broad
                last_exc = exc
                self.report_failure(ep.id, str(exc))
                logger.info("proxy %s failed, will fail over: %s", ep.id, exc)
        if last_exc is not None:
            raise last_exc
        raise NoHealthyProxyError(f"no proxy succeeded for site={site!r} in {max_tries} tries")
