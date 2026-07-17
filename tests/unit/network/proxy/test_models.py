"""Unit tests for src.network.proxy.models — no network."""

from __future__ import annotations

import pytest

from src.network.proxy.models import (
    ProxyEndpoint,
    ProxyHealth,
    ProxyScheme,
    ProxySource,
)


class TestProxyEndpointConstruction:
    def test_direct_sentinel(self):
        ep = ProxyEndpoint.direct()
        assert ep.is_direct
        assert ep.scheme is ProxyScheme.DIRECT
        assert ep.to_url() is None
        assert ep.to_playwright_proxy() is None
        assert ep.to_httpx_proxy() is None

    def test_http_requires_host(self):
        with pytest.raises(ValueError):
            ProxyEndpoint(id="x", scheme=ProxyScheme.HTTP, host=None)

    def test_default_port_filled_per_scheme(self):
        assert ProxyEndpoint(id="a", scheme=ProxyScheme.HTTP, host="h").port == 80
        assert ProxyEndpoint(id="b", scheme=ProxyScheme.SOCKS5, host="h").port == 1080

    def test_invalid_port_rejected(self):
        with pytest.raises(ValueError):
            ProxyEndpoint(id="x", scheme=ProxyScheme.HTTP, host="h", port=70000)

    def test_string_scheme_coerced(self):
        ep = ProxyEndpoint(id="x", scheme="http", host="h", port=8080)
        assert ep.scheme is ProxyScheme.HTTP


class TestRenderers:
    def test_to_url_with_credentials(self):
        ep = ProxyEndpoint(
            id="k", scheme=ProxyScheme.HTTP, host="h", port=8080,
            username="u", password="p",
        )
        assert ep.to_url() == "http://u:p@h:8080"
        assert ep.to_url(with_credentials=False) == "http://h:8080"

    def test_to_playwright_proxy_splits_credentials(self):
        ep = ProxyEndpoint(
            id="k", scheme=ProxyScheme.HTTP, host="h", port=8080,
            username="u", password="p", bypass=["localhost", "127.0.0.1"],
        )
        pw = ep.to_playwright_proxy()
        assert pw == {
            "server": "http://h:8080",
            "username": "u",
            "password": "p",
            "bypass": "localhost,127.0.0.1",
        }
        # credentials must NOT be embedded in the server field
        assert "u:p@" not in pw["server"]

    def test_to_httpx_proxy_embeds_credentials(self):
        ep = ProxyEndpoint(id="k", scheme=ProxyScheme.HTTP, host="h", port=8080,
                           username="u", password="p")
        assert ep.to_httpx_proxy() == "http://u:p@h:8080"


class TestFromUrl:
    def test_full_url(self):
        ep = ProxyEndpoint.from_url("socks5://u:p@1.2.3.4:1080", country="KE")
        assert ep.scheme is ProxyScheme.SOCKS5
        assert ep.host == "1.2.3.4"
        assert ep.port == 1080
        assert ep.username == "u" and ep.password == "p"
        assert ep.country == "KE"

    def test_bare_host_port_defaults_http(self):
        ep = ProxyEndpoint.from_url("1.2.3.4:8080")
        assert ep.scheme is ProxyScheme.HTTP
        assert ep.host == "1.2.3.4" and ep.port == 8080


class TestRedaction:
    def test_repr_never_leaks_password(self):
        ep = ProxyEndpoint(id="k", scheme=ProxyScheme.HTTP, host="h", port=8080,
                           username="u", password="secret")
        assert "secret" not in repr(ep)

    def test_to_dict_redacts_by_default(self):
        ep = ProxyEndpoint(id="k", scheme=ProxyScheme.HTTP, host="h", port=8080,
                           username="u", password="secret")
        assert ep.to_dict()["password"] == "***"
        assert ep.to_dict(redact=False)["password"] == "secret"


class TestAdapters:
    def test_from_navigation_config(self):
        class NavCfg:
            proxy_id = "nav1"
            proxy_type = "socks5"
            host = "9.9.9.9"
            port = 1080
            username = None
            password = None
            country = "RU"

        ep = ProxyEndpoint.from_navigation_config(NavCfg())
        assert ep.id == "nav1"
        assert ep.scheme is ProxyScheme.SOCKS5
        assert ep.country == "RU"

    def test_from_stealth_session(self):
        class Sess:
            session_id = "s1"
            ip_address = "5.5.5.5"
            port = 8000

        ep = ProxyEndpoint.from_stealth_session(Sess())
        assert ep.host == "5.5.5.5"
        assert ep.source is ProxySource.RESIDENTIAL


class TestProxyHealth:
    def test_optimistic_before_samples(self):
        h = ProxyHealth()
        assert h.success_rate == 1.0
        assert h.is_healthy

    def test_success_rate_and_latency_ewma(self):
        h = ProxyHealth()
        h.record_success(100)
        h.record_success(200)
        assert h.success_rate == 1.0
        assert h.ewma_latency_ms is not None
        assert 100 <= h.ewma_latency_ms <= 200

    def test_auto_dead_after_consecutive_failures(self):
        h = ProxyHealth(dead_after_consecutive_failures=3)
        h.record_failure("e")
        h.record_failure("e")
        assert not h.dead
        h.record_failure("e")
        assert h.dead
        assert not h.is_healthy

    def test_success_resets_consecutive_failures(self):
        h = ProxyHealth(dead_after_consecutive_failures=3)
        h.record_failure("e")
        h.record_failure("e")
        h.record_success()
        assert h.consecutive_failures == 0

    def test_low_success_rate_unhealthy(self):
        h = ProxyHealth(min_success_rate=0.5, dead_after_consecutive_failures=99)
        h.record_success()
        h.record_failure("e")
        h.record_failure("e")
        assert h.success_rate < 0.5
        assert not h.is_healthy

    def test_reset_revives(self):
        h = ProxyHealth(dead_after_consecutive_failures=1)
        h.record_failure("e")
        assert h.dead
        h.reset()
        assert not h.dead
