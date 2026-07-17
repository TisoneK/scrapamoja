"""Declarative construction of a :class:`ProxyManager` from plain config.

Keeps proxy configuration canonical to this package (rather than threading it
through the central ``AppConfig``): a dict — loadable from YAML or env — fully
describes the pool, rotation strategy, and per-site routing. This is what makes
Stages 4 (add the Kenya endpoint) and 5 (route ``linebet.* -> kenya``)
declarative instead of hardcoded.

Schema::

    {
      "strategy": "round_robin",          # RotationStrategy value (optional)
      "default_target": "direct",          # endpoint id / source group (optional)
      "endpoints": [
        {"id": "direct", "scheme": "direct"},
        {"id": "kenya", "url": "http://user:pass@7.tcp.ngrok.io:19472",
         "country": "KE", "source": "ngrok"},
        # or explicit fields instead of url:
        {"id": "dc1", "scheme": "http", "host": "1.2.3.4", "port": 8080,
         "username": "u", "password": "p", "source": "datacenter"},
      ],
      "routing": [
        {"pattern": "linebet.*", "target": "kenya"},
        {"pattern": "flashscore.*", "target": "kenya"},
        {"pattern": "github.com", "target": "direct"},
      ],
    }

Module: src.network.proxy.config
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .manager import ProxyManager, RotationStrategy, RoutingRule
from .models import ProxyEndpoint, ProxyScheme, ProxySource
from .providers import StaticProvider

__all__ = ["build_endpoint", "build_proxy_manager", "DEFAULT_PROXY_CONFIG"]


# A safe default: direct-only, no routing. The manager behaves exactly like
# "no proxy" until endpoints/routing are configured.
DEFAULT_PROXY_CONFIG: Dict[str, Any] = {
    "strategy": RotationStrategy.ROUND_ROBIN.value,
    "default_target": "direct",
    "endpoints": [{"id": "direct", "scheme": "direct"}],
    "routing": [],
}


def build_endpoint(spec: Dict[str, Any]) -> ProxyEndpoint:
    """Build one :class:`ProxyEndpoint` from a dict spec (``url`` or fields)."""
    if spec.get("scheme") == ProxyScheme.DIRECT.value or spec.get("url") == "direct":
        return ProxyEndpoint.direct(id=spec.get("id", "direct"))

    source = ProxySource(spec["source"]) if spec.get("source") else ProxySource.MANUAL

    if spec.get("url"):
        return ProxyEndpoint.from_url(
            spec["url"],
            id=spec.get("id"),
            country=spec.get("country"),
            source=source,
        )

    return ProxyEndpoint(
        id=spec["id"],
        scheme=ProxyScheme(spec.get("scheme", "http")),
        host=spec.get("host"),
        port=spec.get("port"),
        username=spec.get("username"),
        password=spec.get("password"),
        country=spec.get("country"),
        source=source,
        bypass=list(spec.get("bypass", []) or []),
    )


def build_proxy_manager(config: Optional[Dict[str, Any]] = None) -> ProxyManager:
    """Construct a :class:`ProxyManager` from a config dict (see module schema).

    ``None`` yields the direct-only default (behaves as "no proxy").
    """
    cfg = config or DEFAULT_PROXY_CONFIG

    endpoints: List[ProxyEndpoint] = [
        build_endpoint(spec) for spec in cfg.get("endpoints", [])
    ]
    if not endpoints:
        endpoints = [ProxyEndpoint.direct()]

    strategy = RotationStrategy(cfg.get("strategy", RotationStrategy.ROUND_ROBIN.value))
    routing = [
        RoutingRule(pattern=r["pattern"], target=r["target"])
        for r in cfg.get("routing", [])
    ]

    return ProxyManager(
        providers=[StaticProvider(endpoints)],
        strategy=strategy,
        routing_rules=routing,
        default_target=cfg.get("default_target"),
    )
