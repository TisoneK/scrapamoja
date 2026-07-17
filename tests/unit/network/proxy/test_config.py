"""Unit tests for src.network.proxy.config — declarative manager construction."""

from __future__ import annotations

from src.network.proxy import build_proxy_manager
from src.network.proxy.config import build_endpoint
from src.network.proxy.manager import RotationStrategy
from src.network.proxy.models import ProxyScheme, ProxySource


def test_default_is_direct_only():
    m = build_proxy_manager()
    assert [e.id for e in m.endpoints] == ["direct"]
    assert m.acquire().is_direct


def test_build_endpoint_from_url():
    ep = build_endpoint({"id": "kenya", "url": "http://u:p@h:8080",
                         "country": "KE", "source": "ngrok"})
    assert ep.id == "kenya"
    assert ep.country == "KE"
    assert ep.source is ProxySource.NGROK
    assert ep.has_credentials


def test_build_endpoint_from_fields():
    ep = build_endpoint({"id": "dc1", "scheme": "socks5", "host": "1.2.3.4",
                         "port": 1080, "source": "datacenter"})
    assert ep.scheme is ProxyScheme.SOCKS5
    assert ep.port == 1080
    assert ep.source is ProxySource.DATACENTER


def test_build_endpoint_direct():
    assert build_endpoint({"id": "d", "scheme": "direct"}).is_direct


def test_full_config_with_routing():
    m = build_proxy_manager({
        "strategy": "health_weighted",
        "default_target": "direct",
        "endpoints": [
            {"id": "direct", "scheme": "direct"},
            {"id": "kenya", "url": "http://u:p@ng:19472", "country": "KE",
             "source": "ngrok"},
        ],
        "routing": [
            # leading-wildcard matches the apex domain AND subdomains (m.linebet.com)
            {"pattern": "*linebet.com", "target": "kenya"},
            {"pattern": "github.com", "target": "direct"},
        ],
    })
    assert m.strategy is RotationStrategy.HEALTH_WEIGHTED
    assert m.acquire(site="linebet.com").id == "kenya"
    assert m.acquire(site="https://m.linebet.com/en/live").id == "kenya"
    assert m.acquire(site="github.com").id == "direct"
    assert m.acquire(site="unknown.com").id == "direct"  # default_target


def test_empty_endpoints_falls_back_to_direct():
    m = build_proxy_manager({"endpoints": []})
    assert m.acquire().is_direct
