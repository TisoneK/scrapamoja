"""Unit tests for src.network.proxy.providers — no network."""

from __future__ import annotations

from src.network.proxy.models import ProxyScheme, ProxySource
from src.network.proxy.providers import (
    DirectProvider,
    ManualEndpointProvider,
    StaticProvider,
)


def test_direct_provider_offers_direct():
    eps = DirectProvider().endpoints()
    assert len(eps) == 1
    assert eps[0].is_direct


def test_static_provider_returns_copy():
    from src.network.proxy.models import ProxyEndpoint

    original = [ProxyEndpoint.direct(), ProxyEndpoint.from_url("http://h:8080")]
    provider = StaticProvider(original)
    got = provider.endpoints()
    assert len(got) == 2
    got.clear()
    assert len(provider.endpoints()) == 2  # internal list untouched


def test_manual_from_url():
    provider = ManualEndpointProvider.from_url(
        "http://u:p@1.2.3.4:8080", id="kenya", country="KE"
    )
    ep = provider.endpoints()[0]
    assert ep.id == "kenya"
    assert ep.country == "KE"
    assert ep.username == "u"


def test_manual_ngrok_builder():
    provider = ManualEndpointProvider.ngrok(
        "7.tcp.ngrok.io", 19472, username="scrapamoja", password="pw", country="KE"
    )
    ep = provider.endpoints()[0]
    assert ep.scheme is ProxyScheme.HTTP
    assert ep.host == "7.tcp.ngrok.io"
    assert ep.port == 19472
    assert ep.source is ProxySource.NGROK
    assert ep.has_credentials
