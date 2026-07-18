"""HTTP feed client for the BetB2B family scraper.

The "direct httpx polling" half of the hybrid extraction mode (ADR-3).
Once :class:`~src.sites.betb2b.session.BetB2BSessionManager` has
harvested session cookies, this client polls the
``/service-api/{LiveFeed,LineFeed}/…`` endpoints directly via httpx —
no browser per poll.

All HTTP egress funnels through the canonical
:class:`~src.network.proxy.ProxyManager` / :class:`ProxyEndpoint` so
proxy routing, credentials, and health-checking are in one place.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from src.network.proxy import ProxyEndpoint
from src.network.session import SessionPackage

from .config import BetB2BSkinConfig
from .extraction.models import CapturedFeedResponse
from .extraction.rules import BetB2BExtractionRules

logger = logging.getLogger(__name__)


class BetB2BFeedClient:
    """httpx-based feed poller for one BetB2B skin.

    One instance per skin. Holds a long-lived :class:`httpx.AsyncClient`
    so connection pooling works across polls. Re-fetches the session
    cookie header from the :class:`BetB2BSessionManager` on every poll
    so cookie refresh is transparent.
    """

    def __init__(
        self,
        skin: BetB2BSkinConfig,
        session_manager: "BetB2BSessionManager",  # type: ignore[name-defined]  # avoid circular import
        proxy: Optional[ProxyEndpoint] = None,
        *,
        timeout: float = 20.0,
        rate_limit_per_minute: int = 30,
        user_agent: Optional[str] = None,
    ) -> None:
        self.skin = skin
        self.session_manager = session_manager
        self.proxy = proxy
        self.timeout = timeout
        self.rate_limit_per_minute = rate_limit_per_minute
        # The UA is part of the session — fall back to the stealth profile's.
        self.user_agent = user_agent or skin.stealth_profile.get(
            "user_agent",
            "Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0.0.0 Safari/537.36",
        )

        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_at: Optional[float] = None
        self._min_interval = (
            60.0 / rate_limit_per_minute if rate_limit_per_minute > 0 else 0.0
        )

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    async def __aenter__(self) -> "BetB2BFeedClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def start(self) -> None:
        if self._client is not None:
            return
        proxy_url = self.proxy.to_httpx_proxy() if self.proxy is not None else None
        # httpx 0.28 uses `proxy=` (singular) for a single proxy URL.
        self._client = httpx.AsyncClient(
            proxy=proxy_url,
            timeout=self.timeout,
            follow_redirects=True,
            headers={"accept-encoding": "gzip, deflate, br"},
        )
        logger.info(
            "skin=%s feed client started (proxy=%s, rate=%d/min)",
            self.skin.name,
            self.proxy.id if self.proxy and not self.proxy.is_direct else "DIRECT",
            self.rate_limit_per_minute,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------ #
    # Polling
    # ------------------------------------------------------------------ #
    async def fetch(
        self,
        feed: str,
        *,
        root: str = "live",
        extra_params: Optional[Dict[str, str]] = None,
        force_session_refresh: bool = False,
    ) -> CapturedFeedResponse:
        """Fetch one feed endpoint and return a decoded capture.

        Args:
            feed: key into ``skin.feed_paths`` (e.g. ``"events_top"``).
            root: ``"live"`` → ``LiveFeed`` root, ``"line"`` → ``LineFeed``.
            extra_params: per-call query param overrides.
            force_session_refresh: re-bootstrap the session before this
                request (use after a 401/403/419/440).

        Returns:
            :class:`CapturedFeedResponse` — decoded JSON ready for the
            :class:`BetB2BExtractionRules` extractor.
        """
        if self._client is None:
            await self.start()
        assert self._client is not None

        # Rate-limit politely.
        await self._respect_rate_limit()

        # Pull a fresh session (re-bootstraps if expired/forced).
        session: SessionPackage = await self.session_manager.get_session(
            force=force_session_refresh,
        )
        cookie_header = session.to_cookie_header()
        url = self.skin.feed_url(feed, root=root, extra_params=extra_params)
        headers = self.skin.merged_headers(session_cookies=cookie_header)
        headers.setdefault("user-agent", self.user_agent)
        # The feed is on the same origin we bootstrapped against.
        headers.setdefault("referer", self.skin.bootstrap_url("home"))
        headers.setdefault("origin", self.skin.base_url)

        start = time.monotonic()
        logger.debug(
            "skin=%s fetching feed=%s root=%s url=%s",
            self.skin.name, feed, root, url,
        )

        try:
            resp = await self._client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            logger.error(
                "skin=%s feed=%s HTTP error: %s", self.skin.name, feed, exc,
            )
            # Return an empty capture so the scrape continues.
            return CapturedFeedResponse(
                url=url, status=0, content_type="",
                body_bytes=0, decoded={},
            )

        latency_ms = (time.monotonic() - start) * 1000.0
        logger.info(
            "skin=%s feed=%s root=%s status=%d bytes=%d latency=%.0fms",
            self.skin.name, feed, root, resp.status_code,
            len(resp.content), latency_ms,
        )

        # If we see an auth-error status, notify the session manager.
        if self.session_manager.record_auth_failure(resp.status_code):
            logger.warning(
                "skin=%s feed=%s got auth-error %d — forcing re-bootstrap",
                self.skin.name, feed, resp.status_code,
            )
            # Don't recurse infinitely — clear the flag and let the next
            # call re-bootstrap. This call returns whatever we got.
            self.session_manager.clear()

        content_type = resp.headers.get("content-type", "")
        rules = BetB2BExtractionRules(self.skin)
        return rules.decode_response(
            url=url,
            status=resp.status_code,
            content_type=content_type,
            raw_bytes=resp.content,
        )

    async def fetch_many(
        self,
        feeds: List[str],
        *,
        root: str = "live",
        extra_params: Optional[Dict[str, str]] = None,
    ) -> List[CapturedFeedResponse]:
        """Fetch multiple feed endpoints sequentially (rate-limited)."""
        out: List[CapturedFeedResponse] = []
        for feed in feeds:
            cap = await self.fetch(feed, root=root, extra_params=extra_params)
            out.append(cap)
        return out

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    async def _respect_rate_limit(self) -> None:
        if self._min_interval <= 0 or self._last_request_at is None:
            self._last_request_at = time.monotonic()
            return
        elapsed = time.monotonic() - self._last_request_at
        wait = self._min_interval - elapsed
        if wait > 0:
            import asyncio

            await asyncio.sleep(wait)
        self._last_request_at = time.monotonic()
