"""Proxy data models — the single canonical proxy representation.

This module defines :class:`ProxyEndpoint`, the one model that all outbound
traffic (Playwright browser contexts, httpx clients, HAR export) consults when
it needs a proxy. It supersedes the three pre-existing, fragmented proxy models:

- ``src/browser/models/proxy.py::ProxySettings`` (rich, but not read by the
  Playwright launch path),
- ``src/browser/models/configuration.py::ProxySettings`` (a different class),
- the flat ``config.proxy_server / proxy_username / proxy_password`` fields the
  browser session manager actually reads.

Adapters (``from_browser_proxysettings`` etc.) let the legacy models interoperate
so callers can migrate incrementally rather than all at once.

Module: src.network.proxy.models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

__all__ = [
    "ProxyScheme",
    "ProxySource",
    "ProxyEndpoint",
    "ProxyHealth",
]


class ProxyScheme(str, Enum):
    """Proxy connection scheme.

    Unlike ``browser/models/enums.py::ProxyType`` this includes ``DIRECT`` — the
    "no proxy" case — so a routing decision can always resolve to a concrete
    :class:`ProxyEndpoint` rather than ``None``.
    """

    DIRECT = "direct"
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxySource(str, Enum):
    """Where an endpoint came from — for observability and routing policy."""

    DIRECT = "direct"
    MANUAL = "manual"
    NGROK = "ngrok"
    RESIDENTIAL = "residential"
    DATACENTER = "datacenter"


# Default ports per scheme, used when a URL omits the port.
_DEFAULT_PORTS = {
    ProxyScheme.HTTP: 80,
    ProxyScheme.HTTPS: 443,
    ProxyScheme.SOCKS5: 1080,
}


@dataclass
class ProxyEndpoint:
    """A single proxy endpoint (or the DIRECT / no-proxy sentinel).

    This is the canonical proxy value object. It knows how to render itself for
    every downstream consumer (``to_playwright_proxy``, ``to_httpx_proxy``,
    ``to_url``) so those formats are built in exactly one place.

    For DIRECT, ``host``/``port`` are unused and the render methods return
    ``None`` (meaning "make a normal, un-proxied connection").
    """

    id: str
    scheme: ProxyScheme = ProxyScheme.DIRECT
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    source: ProxySource = ProxySource.MANUAL
    bypass: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.scheme, str) and not isinstance(self.scheme, ProxyScheme):
            self.scheme = ProxyScheme(self.scheme)
        if isinstance(self.source, str) and not isinstance(self.source, ProxySource):
            self.source = ProxySource(self.source)

        if self.scheme is ProxyScheme.DIRECT:
            # A direct endpoint carries no host/port/credentials.
            self.host = None
            self.port = None
            self.username = None
            self.password = None
            return

        if not self.host:
            raise ValueError(f"proxy {self.id!r}: host is required for scheme {self.scheme.value}")
        if self.port is None:
            self.port = _DEFAULT_PORTS[self.scheme]
        if not (0 < int(self.port) <= 65535):
            raise ValueError(f"proxy {self.id!r}: invalid port {self.port}")
        self.port = int(self.port)

    # ------------------------------------------------------------------ #
    # Predicates
    # ------------------------------------------------------------------ #
    @property
    def is_direct(self) -> bool:
        return self.scheme is ProxyScheme.DIRECT

    @property
    def has_credentials(self) -> bool:
        return bool(self.username) and bool(self.password)

    # ------------------------------------------------------------------ #
    # Renderers — the ONLY places these formats are constructed
    # ------------------------------------------------------------------ #
    def to_url(self, *, with_credentials: bool = True) -> Optional[str]:
        """Full proxy URL, e.g. ``http://user:pass@host:port``.

        Returns ``None`` for DIRECT.
        """
        if self.is_direct:
            return None
        auth = ""
        if with_credentials and self.has_credentials:
            auth = f"{self.username}:{self.password}@"
        return f"{self.scheme.value}://{auth}{self.host}:{self.port}"

    def to_playwright_proxy(self) -> Optional[Dict[str, Any]]:
        """Playwright ``new_context(proxy=...)`` dict, or ``None`` for DIRECT.

        Playwright takes the server without embedded credentials plus separate
        ``username``/``password`` keys. NOTE: Chromium does not support SOCKS
        proxy authentication — for authenticated proxies use HTTP/HTTPS.
        """
        if self.is_direct:
            return None
        proxy: Dict[str, Any] = {"server": f"{self.scheme.value}://{self.host}:{self.port}"}
        if self.has_credentials:
            proxy["username"] = self.username
            proxy["password"] = self.password
        if self.bypass:
            proxy["bypass"] = ",".join(self.bypass)
        return proxy

    def to_httpx_proxy(self) -> Optional[str]:
        """Proxy URL string for httpx (``AsyncClient(proxy=...)``), or ``None``."""
        return self.to_url(with_credentials=True)

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_dict(self, *, redact: bool = True) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scheme": self.scheme.value,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": ("***" if self.password and redact else self.password),
            "country": self.country,
            "source": self.source.value,
            "bypass": list(self.bypass),
        }

    # ------------------------------------------------------------------ #
    # Constructors
    # ------------------------------------------------------------------ #
    @classmethod
    def direct(cls, id: str = "direct") -> "ProxyEndpoint":
        """The no-proxy sentinel endpoint."""
        return cls(id=id, scheme=ProxyScheme.DIRECT, source=ProxySource.DIRECT)

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        id: Optional[str] = None,
        country: Optional[str] = None,
        source: ProxySource = ProxySource.MANUAL,
        bypass: Optional[List[str]] = None,
    ) -> "ProxyEndpoint":
        """Parse ``scheme://user:pass@host:port`` into an endpoint."""
        parsed = urlparse(url if "://" in url else f"http://{url}")
        try:
            scheme = ProxyScheme(parsed.scheme)
        except ValueError:
            scheme = ProxyScheme.HTTP
        if scheme is ProxyScheme.DIRECT:
            return cls.direct(id=id or "direct")
        if not parsed.hostname:
            raise ValueError(f"invalid proxy URL: {url!r}")
        return cls(
            id=id or f"{parsed.hostname}:{parsed.port or _DEFAULT_PORTS.get(scheme, 0)}",
            scheme=scheme,
            host=parsed.hostname,
            port=parsed.port,
            username=parsed.username,
            password=parsed.password,
            country=country,
            source=source,
            bypass=bypass or [],
        )

    # ------------------------------------------------------------------ #
    # Adapters from the legacy models (incremental migration)
    # ------------------------------------------------------------------ #
    @classmethod
    def from_browser_proxysettings(cls, settings: Any, *, id: Optional[str] = None) -> "ProxyEndpoint":
        """Adapt ``src/browser/models/proxy.py::ProxySettings``."""
        scheme = ProxyScheme(getattr(settings.proxy_type, "value", settings.proxy_type))
        return cls(
            id=id or f"browser:{settings.server}:{settings.port}",
            scheme=scheme,
            host=settings.server,
            port=settings.port,
            username=getattr(settings, "username", None),
            password=getattr(settings, "password", None),
            bypass=list(getattr(settings, "bypass_list", []) or []),
        )

    @classmethod
    def from_navigation_config(cls, cfg: Any) -> "ProxyEndpoint":
        """Adapt ``src/navigation/proxy_manager.py::ProxyConfig``."""
        return cls(
            id=getattr(cfg, "proxy_id", None) or f"nav:{cfg.host}:{cfg.port}",
            scheme=ProxyScheme(getattr(cfg, "proxy_type", "http")),
            host=cfg.host,
            port=cfg.port,
            username=getattr(cfg, "username", None),
            password=getattr(cfg, "password", None),
            country=getattr(cfg, "country", None),
        )

    @classmethod
    def from_stealth_session(cls, session: Any) -> "ProxyEndpoint":
        """Adapt ``src/stealth/models.py::ProxySession``."""
        return cls(
            id=getattr(session, "session_id", None) or f"stealth:{session.ip_address}:{session.port}",
            scheme=ProxyScheme.HTTP,
            host=session.ip_address,
            port=session.port,
            source=ProxySource.RESIDENTIAL,
            country=getattr(session, "country", None),
        )

    def __repr__(self) -> str:  # never leak credentials
        if self.is_direct:
            return "ProxyEndpoint(direct)"
        creds = " +auth" if self.has_credentials else ""
        loc = f" {self.country}" if self.country else ""
        return f"ProxyEndpoint({self.id}: {self.scheme.value}://{self.host}:{self.port}{creds}{loc})"


@dataclass
class ProxyHealth:
    """Rolling health for one endpoint — drives failover and health-weighting.

    Mirrors the success-rate idea in ``navigation/proxy_manager.py`` and the
    status concept in ``stealth/models.py::ProxyStatus``, unified here.
    """

    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    last_latency_ms: Optional[float] = None
    ewma_latency_ms: Optional[float] = None
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None
    dead: bool = False

    # Number of consecutive failures after which an endpoint auto-marks dead.
    dead_after_consecutive_failures: int = 3
    # Minimum success rate to still be considered healthy (once it has samples).
    min_success_rate: float = 0.3
    # EWMA smoothing factor for latency.
    _alpha: float = 0.3

    @property
    def total(self) -> int:
        return self.successes + self.failures

    @property
    def success_rate(self) -> float:
        """Success rate in ``[0, 1]``; optimistic (1.0) before any samples."""
        if self.total == 0:
            return 1.0
        return self.successes / self.total

    @property
    def is_healthy(self) -> bool:
        if self.dead:
            return False
        if self.total == 0:
            return True
        return self.success_rate >= self.min_success_rate

    def record_success(self, latency_ms: Optional[float] = None) -> None:
        self.successes += 1
        self.consecutive_failures = 0
        self.last_error = None
        self.last_used = datetime.now()
        if latency_ms is not None:
            self.last_latency_ms = latency_ms
            if self.ewma_latency_ms is None:
                self.ewma_latency_ms = latency_ms
            else:
                self.ewma_latency_ms = (
                    self._alpha * latency_ms + (1 - self._alpha) * self.ewma_latency_ms
                )

    def record_failure(self, error: Optional[str] = None) -> None:
        self.failures += 1
        self.consecutive_failures += 1
        self.last_error = error
        self.last_used = datetime.now()
        if self.consecutive_failures >= self.dead_after_consecutive_failures:
            self.dead = True

    def reset(self) -> None:
        self.consecutive_failures = 0
        self.dead = False
        self.last_error = None
