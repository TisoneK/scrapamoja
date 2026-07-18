"""Session bootstrap for the BetB2B family scraper.

Implements the "browser-harvest cookies" half of the hybrid extraction
mode (ADR-3 in `.context/memory/plans/decisions.md`).

Recipe:

  1. Launch Playwright Chromium through the skin's allowed-country proxy
     (via the canonical :class:`ProxyManager` / :class:`ProxyEndpoint`).
  2. Navigate to the skin's home page (and live page, optionally) so the
     SPA bootstraps and sets its ~21 session cookies.
  3. Dismiss any cookie-consent banner (best-effort).
  4. Wait for the SPA's initial API burst to settle.
  5. Harvest the cookies + user-agent via the framework's
     :class:`SessionHarvester`.
  6. Close the browser, return a :class:`SessionPackage` for the httpx
     client to use.

The harvested session is cached + re-used until either the TTL expires
or the httpx client sees an auth-error status (401/403/419/440), at
which point :meth:`BetB2BSessionManager.get_session` re-bootstraps.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from src.network.proxy import ProxyEndpoint, verify_proxy
from src.network.session import SessionHarvester, SessionPackage, SessionValidator

from .config import BetB2BSkinConfig

logger = logging.getLogger(__name__)


class BetB2BSessionManager:
    """Manages the harvested browser session for one skin.

    Lazily bootstraps a session on first use, caches it, and re-bootstraps
    when the TTL expires or an auth-error status is seen.
    """

    def __init__(
        self,
        skin: BetB2BSkinConfig,
        proxy: Optional[ProxyEndpoint] = None,
        *,
        settle_seconds: float = 12.0,
        bootstrap_timeout_ms: int = 45_000,
    ) -> None:
        self.skin = skin
        self.proxy = proxy
        self.settle_seconds = settle_seconds
        self.bootstrap_timeout_ms = bootstrap_timeout_ms

        self._harvester = SessionHarvester()
        self._validator = SessionValidator(
            session_ttl=skin.session_ttl_seconds,
            max_auth_failures=3,
        )

        self._session: Optional[SessionPackage] = None
        self._session_lock = asyncio.Lock()
        self._last_bootstrap_at: Optional[datetime] = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def get_session(self, *, force: bool = False) -> SessionPackage:
        """Return a valid session, bootstrapping or re-bootstrapping as needed.

        Args:
            force: if True, ignore the cache and re-bootstrap.

        Returns:
            A :class:`SessionPackage` with the harvested cookies + UA.
        """
        async with self._session_lock:
            if force or self._needs_bootstrap():
                self._session = await self._bootstrap()
                self._last_bootstrap_at = datetime.now(timezone.utc)
                self._validator.reset_auth_failures()
            assert self._session is not None  # for type-checkers
            return self._session

    def record_auth_failure(self, status_code: int) -> bool:
        """Record an auth-error HTTP status seen by the httpx client.

        Returns:
            True if max failures reached — the caller should re-call
            :meth:`get_session` to re-bootstrap.
        """
        if self._validator.is_auth_error(status_code):
            needs_rebootstrap = self._validator.record_auth_failures()
            logger.warning(
                "skin=%s auth-failure status=%d (count=%d, rebootstrap=%s)",
                self.skin.name, status_code,
                self._validator.auth_failure_count, needs_rebootstrap,
            )
            return needs_rebootstrap
        return False

    @property
    def has_session(self) -> bool:
        return self._session is not None

    @property
    def session_age(self) -> Optional[timedelta]:
        if self._last_bootstrap_at is None:
            return None
        return datetime.now(timezone.utc) - self._last_bootstrap_at

    def clear(self) -> None:
        """Drop the cached session (next ``get_session`` re-bootstraps)."""
        self._session = None
        self._last_bootstrap_at = None

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _needs_bootstrap(self) -> bool:
        if self._session is None:
            return True
        if self._validator.is_expired(self._session):
            logger.info(
                "skin=%s session expired (age=%s) — re-bootstrapping",
                self.skin.name, self.session_age,
            )
            return True
        return False

    async def _bootstrap(self) -> SessionPackage:
        """Run the browser bootstrap → cookie harvest pipeline."""
        if not self.skin.enabled:
            raise RuntimeError(f"skin={self.skin.name} is disabled")

        # Validate proxy egress country BEFORE opening a browser — saves
        # an expensive Playwright launch if the proxy is misconfigured.
        if self.proxy is not None and not self.proxy.is_direct:
            ok = await self._verify_proxy_country()
            if not ok:
                raise RuntimeError(
                    f"skin={self.skin.name}: proxy {self.proxy.id!r} egress "
                    f"country not in allowed_countries={self.skin.allowed_countries}"
                )

        from playwright.async_api import async_playwright

        stealth = self.skin.stealth_profile
        logger.info(
            "skin=%s bootstrapping session via proxy=%s domain=%s",
            self.skin.name,
            self.proxy.id if self.proxy and not self.proxy.is_direct else "DIRECT",
            self.skin.domain,
        )

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=stealth.get("headless", True))
            try:
                context_kwargs: dict[str, Any] = {
                    "user_agent": stealth.get("user_agent"),
                    "viewport": stealth.get("viewport", {"width": 1536, "height": 864}),
                    "locale": stealth.get("locale", "en-US"),
                    "timezone_id": stealth.get("timezone", "Europe/London"),
                }
                if self.proxy is not None and not self.proxy.is_direct:
                    pp = self.proxy.to_playwright_proxy()
                    if pp:
                        context_kwargs["proxy"] = pp

                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()

                home_url = self.skin.bootstrap_url("home")
                logger.info("skin=%s navigating to %s", self.skin.name, home_url)

                # domcontentloaded — the SPA fires its first API calls
                # immediately after DCL. networkidle would hang (linebet
                # keeps a long-poll open for live odds).
                try:
                    resp = await page.goto(
                        home_url,
                        wait_until="domcontentloaded",
                        timeout=self.bootstrap_timeout_ms,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("skin=%s goto home failed: %s", self.skin.name, exc)
                    resp = None

                # Detect geo/WAF block: HTTP 203 → redirect to /en/block.
                if resp is not None:
                    status = resp.status
                    final_url = page.url
                    if status == 203 or final_url.endswith("/block"):
                        raise RuntimeError(
                            f"skin={self.skin.name}: geo/WAF block detected "
                            f"(status={status}, url={final_url}). The proxy "
                            f"egress is not in an allowed country for this skin "
                            f"(allowed={self.skin.allowed_countries})."
                        )

                # Best-effort consent dismissal.
                await self._dismiss_consent(page)

                # Wait for the SPA's API burst to settle (sets cookies).
                await asyncio.sleep(self.settle_seconds)

                # Visit the live page too — some cookies are only set on
                # the live route (the SPA switches context).
                live_url = self.skin.bootstrap_url("live")
                try:
                    await page.goto(
                        live_url,
                        wait_until="domcontentloaded",
                        timeout=self.bootstrap_timeout_ms,
                    )
                    await asyncio.sleep(min(self.settle_seconds, 6.0))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("skin=%s live-page visit failed: %s", self.skin.name, exc)

                # Harvest cookies + UA via the framework's SessionHarvester.
                session = await self._harvester.harvest(
                    page, site_name=self.skin.name,
                )

                # Tag the session with the skin + proxy metadata.
                session.headers = []  # we don't harvest headers (no SW replay needed)
                logger.info(
                    "skin=%s session harvested: %d cookies, ua=%s",
                    self.skin.name,
                    len(session.cookies),
                    (session.user_agent or "")[:60] + "…",
                )

                if not session.cookies:
                    logger.warning(
                        "skin=%s bootstrap harvested ZERO cookies — feed "
                        "replay will likely 406. Check the proxy + WAF.",
                        self.skin.name,
                    )

                return session
            finally:
                await browser.close()

    async def _verify_proxy_country(self) -> bool:
        """Verify the proxy's egress country is in the skin's allowed list."""
        if not self.skin.allowed_countries:
            return True  # no allow-list = allow all
        try:
            result = await verify_proxy(self.proxy, timeout=20.0, with_geo=True)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "skin=%s proxy verification failed: %s", self.skin.name, exc,
            )
            return False

        if not result.ok:
            logger.warning(
                "skin=%s proxy %s unreachable: %s",
                self.skin.name, self.proxy.id, result.error,  # type: ignore[union-attr]
            )
            return False

        if result.country_code and result.country_code not in self.skin.allowed_countries:
            logger.warning(
                "skin=%s proxy egress country=%s not in allowed=%s",
                self.skin.name, result.country_code, self.skin.allowed_countries,
            )
            return False

        logger.info(
            "skin=%s proxy OK: egress=%s country=%s latency=%.0fms",
            self.skin.name, result.egress_ip, result.country_code,
            result.latency_ms or 0.0,
        )
        return True

    async def _dismiss_consent(self, page: Any) -> None:
        """Best-effort cookie-consent banner dismissal."""
        candidates = [
            'button#acceptAll',
            'button[aria-label="Accept all"]',
            'button:has-text("Accept all")',
            'button:has-text("Accept All")',
            'button:has-text("Agree")',
            'button:has-text("Got it")',
            'a:has-text("Accept all")',
        ]
        for sel in candidates:
            try:
                locator = page.locator(sel).first
                if await locator.count() > 0 and await locator.is_visible(timeout=500):
                    await locator.click(timeout=2000)
                    logger.info("skin=%s dismissed consent via %s", self.skin.name, sel)
                    return
            except Exception:  # noqa: BLE001
                continue
