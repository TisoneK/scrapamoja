"""Stage 2 validation — prove traffic actually routes through the proxy.

These tests stand up a tiny in-process recording CONNECT proxy on localhost and
assert that both the httpx path (``verify_proxy``) and the Playwright path
(``verify_proxy_playwright``) send their requests *through* the proxy the
:class:`ProxyManager` hands out. On a single machine the egress IP can't change
(same host), so the IP-change assertion belongs to Stage 4 (the real remote
proxy); here we prove the plumbing: the request reaches the proxy.

Network + browser required, so these are integration-marked and deselected by
default.
"""

from __future__ import annotations

import asyncio
from typing import List

import pytest

from src.network.proxy import (
    ProxyEndpoint,
    ProxyManager,
    StaticProvider,
    verify_proxy,
    verify_proxy_playwright,
)


class RecordingConnectProxy:
    """Minimal HTTP CONNECT proxy that records the hosts it tunnels to."""

    def __init__(self) -> None:
        self.connected_hosts: List[str] = []
        self._server: asyncio.AbstractServer | None = None
        self.port: int | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request_line = await reader.readline()
            parts = request_line.decode("latin-1", "ignore").split()
            if len(parts) < 2 or parts[0].upper() != "CONNECT":
                writer.close()
                return
            host_port = parts[1]
            self.connected_hosts.append(host_port)
            # Drain the remaining request headers.
            while True:
                header = await reader.readline()
                if header in (b"\r\n", b"\n", b""):
                    break
            host, _, port = host_port.partition(":")
            try:
                up_reader, up_writer = await asyncio.open_connection(host, int(port or 443))
            except Exception:
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                await writer.drain()
                writer.close()
                return
            writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
            await writer.drain()
            await asyncio.gather(
                self._pipe(reader, up_writer),
                self._pipe(up_reader, writer),
                return_exceptions=True,
            )
        except Exception:
            try:
                writer.close()
            except Exception:
                pass

    @staticmethod
    async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_httpx_routes_through_local_proxy():
    proxy = RecordingConnectProxy()
    await proxy.start()
    try:
        ep = ProxyEndpoint.from_url(f"http://127.0.0.1:{proxy.port}", id="local")
        result = await verify_proxy(ep, with_geo=False, timeout=20)
        assert result.ok, result.error
        assert any("api.ipify.org" in h for h in proxy.connected_hosts), proxy.connected_hosts
    finally:
        await proxy.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manager_acquired_endpoint_routes_and_records_health():
    proxy = RecordingConnectProxy()
    await proxy.start()
    try:
        manager = ProxyManager(providers=[StaticProvider([
            ProxyEndpoint.from_url(f"http://127.0.0.1:{proxy.port}", id="local"),
        ])])
        ep = manager.acquire(site="api.ipify.org")
        result = await verify_proxy(ep, with_geo=False, timeout=20)
        assert result.ok, result.error
        manager.report_success(ep.id, result.latency_ms)
        assert manager.health_of("local").successes == 1
        assert proxy.connected_hosts
    finally:
        await proxy.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_playwright_routes_through_local_proxy():
    proxy = RecordingConnectProxy()
    await proxy.start()
    try:
        ep = ProxyEndpoint.from_url(f"http://127.0.0.1:{proxy.port}", id="local")
        result = await verify_proxy_playwright(ep)
        assert result.ok, result.error
        assert any("api.ipify.org" in h for h in proxy.connected_hosts), proxy.connected_hosts
    finally:
        await proxy.stop()
