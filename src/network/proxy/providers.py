"""Proxy providers — sources of :class:`ProxyEndpoint` for the manager.

A provider abstracts *where* endpoints come from. The manager holds one or more
providers and pools their endpoints. This keeps the manager agnostic to whether
an endpoint is a hardcoded ngrok tunnel, a static list, or (later) a residential
rotation service.

The ABC intentionally mirrors ``src/stealth/proxy_manager.py::ProxyProvider`` so
the residential providers there can be adapted onto this manager in the planned
follow-up migration.

Module: src.network.proxy.providers
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from .models import ProxyEndpoint, ProxyScheme, ProxySource

__all__ = [
    "ProxyProvider",
    "DirectProvider",
    "StaticProvider",
    "ManualEndpointProvider",
]


class ProxyProvider(ABC):
    """Abstract source of proxy endpoints."""

    @abstractmethod
    def endpoints(self) -> List[ProxyEndpoint]:
        """Return the current set of endpoints this provider offers."""
        raise NotImplementedError

    async def initialize(self) -> bool:  # pragma: no cover - default no-op
        """Verify connectivity/credentials. Override if the provider needs it."""
        return True


class DirectProvider(ProxyProvider):
    """Always offers the single DIRECT (no-proxy) endpoint."""

    def __init__(self, id: str = "direct") -> None:
        self._endpoint = ProxyEndpoint.direct(id=id)

    def endpoints(self) -> List[ProxyEndpoint]:
        return [self._endpoint]


class StaticProvider(ProxyProvider):
    """Offers a fixed, in-memory list of endpoints."""

    def __init__(self, endpoints: Sequence[ProxyEndpoint]) -> None:
        self._endpoints = list(endpoints)

    def endpoints(self) -> List[ProxyEndpoint]:
        return list(self._endpoints)


class ManualEndpointProvider(ProxyProvider):
    """A single, manually-specified endpoint.

    Used for the operator-supplied Kenya proxy (a ``gost`` HTTP proxy exposed via
    ngrok). Construct from a URL or from explicit host/port/credentials.
    """

    def __init__(self, endpoint: ProxyEndpoint) -> None:
        self._endpoint = endpoint

    def endpoints(self) -> List[ProxyEndpoint]:
        return [self._endpoint]

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        id: Optional[str] = None,
        country: Optional[str] = None,
        source: ProxySource = ProxySource.MANUAL,
    ) -> "ManualEndpointProvider":
        return cls(ProxyEndpoint.from_url(url, id=id, country=country, source=source))

    @classmethod
    def ngrok(
        cls,
        host: str,
        port: int,
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
        country: Optional[str] = None,
        id: str = "kenya-ngrok",
    ) -> "ManualEndpointProvider":
        """Build a provider for an ngrok-exposed HTTP proxy (host:port + auth)."""
        return cls(
            ProxyEndpoint(
                id=id,
                scheme=ProxyScheme.HTTP,
                host=host,
                port=port,
                username=username,
                password=password,
                country=country,
                source=ProxySource.NGROK,
            )
        )
