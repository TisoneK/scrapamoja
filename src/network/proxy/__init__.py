"""Canonical proxy layer for Scrapamoja.

The single source of truth for outbound-proxy configuration. Every consumer that
opens a connection (Playwright browser contexts, httpx clients, HAR export) asks a
:class:`ProxyManager` for a :class:`ProxyEndpoint` and renders it via the endpoint's
``to_playwright_proxy()`` / ``to_httpx_proxy()`` methods — no consumer builds proxy
config by hand.

Quick start::

    from src.network.proxy import ProxyManager, ProxyEndpoint, StaticProvider

    manager = ProxyManager(providers=[
        StaticProvider([ProxyEndpoint.direct(),
                        ProxyEndpoint.from_url("http://user:pass@host:8080",
                                               country="KE")]),
    ])
    ep = manager.acquire(site="linebet.com")
    playwright_proxy = ep.to_playwright_proxy()   # dict or None (direct)

See ``src/network/proxy/verify.py`` for the egress-IP check used to prove a proxy
actually changes our IP.
"""

from __future__ import annotations

from .manager import (
    NoHealthyProxyError,
    ProxyManager,
    RotationStrategy,
    RoutingRule,
)
from .models import ProxyEndpoint, ProxyHealth, ProxyScheme, ProxySource
from .providers import (
    DirectProvider,
    ManualEndpointProvider,
    ProxyProvider,
    StaticProvider,
)
from .verify import ProxyCheckResult, verify_proxy, verify_proxy_playwright

__all__ = [
    # models
    "ProxyEndpoint",
    "ProxyHealth",
    "ProxyScheme",
    "ProxySource",
    # manager
    "ProxyManager",
    "RotationStrategy",
    "RoutingRule",
    "NoHealthyProxyError",
    # providers
    "ProxyProvider",
    "DirectProvider",
    "StaticProvider",
    "ManualEndpointProvider",
    # verify
    "ProxyCheckResult",
    "verify_proxy",
    "verify_proxy_playwright",
]
