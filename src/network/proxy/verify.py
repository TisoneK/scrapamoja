"""Proxy verification — prove an endpoint actually changes our egress IP.

This is the Stage-2 check ("IP changes when expected") and doubles as a health
probe: it sends a request through the endpoint to an IP-echo service and reports
the observed egress IP + latency. A DIRECT endpoint returns our own IP, which is
exactly what you compare a real proxy against.

Requires network access, so tests using this are integration-marked.

Module: src.network.proxy.verify
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import httpx

from .models import ProxyEndpoint

__all__ = ["ProxyCheckResult", "verify_proxy", "verify_proxy_playwright"]

# IP-echo endpoints. ipify is primary; ip-api adds country for geo assertions.
IPIFY_URL = "https://api.ipify.org?format=json"
IPAPI_URL = "http://ip-api.com/json/?fields=status,country,countryCode,query"


@dataclass
class ProxyCheckResult:
    """Outcome of probing one endpoint."""

    endpoint_id: str
    ok: bool
    egress_ip: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    def __str__(self) -> str:
        if not self.ok:
            return f"[{self.endpoint_id}] FAILED: {self.error}"
        loc = f" ({self.country_code})" if self.country_code else ""
        lat = f" {self.latency_ms:.0f}ms" if self.latency_ms is not None else ""
        return f"[{self.endpoint_id}] {self.egress_ip}{loc}{lat}"


async def verify_proxy(
    endpoint: ProxyEndpoint,
    *,
    timeout: float = 20.0,
    with_geo: bool = True,
) -> ProxyCheckResult:
    """Send a request through ``endpoint`` and report the egress IP (+ country).

    Uses httpx (httpx 0.28 ``proxy=`` kwarg). ``endpoint.to_httpx_proxy()`` is
    ``None`` for DIRECT, in which case the request goes out un-proxied — useful
    as the baseline to compare a real proxy against.
    """
    proxy_url = endpoint.to_httpx_proxy()
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=timeout) as client:
            resp = await client.get(IPIFY_URL)
            resp.raise_for_status()
            egress_ip = resp.json().get("ip")
            latency_ms = (time.monotonic() - start) * 1000.0

            country = country_code = None
            if with_geo:
                try:
                    geo = await client.get(IPAPI_URL)
                    if geo.status_code == 200 and geo.json().get("status") == "success":
                        data = geo.json()
                        country = data.get("country")
                        country_code = data.get("countryCode")
                        egress_ip = data.get("query") or egress_ip
                except Exception:  # noqa: BLE001 - geo is best-effort
                    pass

            return ProxyCheckResult(
                endpoint_id=endpoint.id,
                ok=True,
                egress_ip=egress_ip,
                country=country,
                country_code=country_code,
                latency_ms=latency_ms,
            )
    except Exception as exc:  # noqa: BLE001 - report, don't raise
        return ProxyCheckResult(
            endpoint_id=endpoint.id,
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
            latency_ms=(time.monotonic() - start) * 1000.0,
        )


async def verify_proxy_playwright(
    endpoint: ProxyEndpoint,
    *,
    timeout_ms: int = 20000,
) -> ProxyCheckResult:
    """Same check, but through a Playwright Chromium context.

    Verifies the browser path (not just httpx) actually routes through the proxy —
    the format ``endpoint.to_playwright_proxy()`` produces is what browser launch
    consumes. Imports Playwright lazily so importing this module stays cheap.
    """
    from playwright.async_api import async_playwright

    proxy = endpoint.to_playwright_proxy()
    start = time.monotonic()
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                context = await browser.new_context(**({"proxy": proxy} if proxy else {}))
                page = await context.new_page()
                await page.goto(IPIFY_URL, timeout=timeout_ms)
                body = await page.inner_text("body")
                import json

                egress_ip = json.loads(body).get("ip")
                return ProxyCheckResult(
                    endpoint_id=endpoint.id,
                    ok=True,
                    egress_ip=egress_ip,
                    latency_ms=(time.monotonic() - start) * 1000.0,
                )
            finally:
                await browser.close()
    except Exception as exc:  # noqa: BLE001
        return ProxyCheckResult(
            endpoint_id=endpoint.id,
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
            latency_ms=(time.monotonic() - start) * 1000.0,
        )
