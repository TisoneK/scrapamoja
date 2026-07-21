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
from typing import Any, List, Optional

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
        grid_wait_ms: int = 20_000,
        proxy_verify_attempts: int = 3,
        proxy_verify_backoff: float = 3.0,
    ) -> None:
        self.skin = skin
        self.proxy = proxy
        self.settle_seconds = settle_seconds
        self.bootstrap_timeout_ms = bootstrap_timeout_ms
        self.grid_wait_ms = grid_wait_ms
        self.proxy_verify_attempts = proxy_verify_attempts
        self.proxy_verify_backoff = proxy_verify_backoff

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

                # 'commit' is the earliest non-empty document state.
                # The BetB2B SPA keeps long-poll connections open after
                # load, so 'domcontentloaded' and 'networkidle' can hang
                # through slow residential proxies. 'commit' fires the
                # moment a navigable document exists.
                try:
                    resp = await page.goto(
                        home_url,
                        wait_until="commit",
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
                        wait_until="commit",
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
        """Verify the proxy's egress country is in the skin's allowed list.

        Ephemeral tunnels (bore/gost) drop connections intermittently, so a
        single ``ReadError`` on the pre-flight check would otherwise abort a
        multi-minute scrape even though the tunnel works on the next request.
        Retry transient reachability failures with backoff; a *definitive*
        country mismatch (the tunnel answered, wrong country) fails fast — no
        amount of retrying moves the egress IP.
        """
        if not self.skin.allowed_countries:
            return True  # no allow-list = allow all

        attempts = max(1, self.proxy_verify_attempts)
        for attempt in range(1, attempts + 1):
            try:
                result = await verify_proxy(self.proxy, timeout=20.0, with_geo=True)  # type: ignore[arg-type]
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "skin=%s proxy verification error (attempt %d/%d): %s",
                    self.skin.name, attempt, attempts, exc,
                )
                result = None

            if result is not None and not result.ok:
                logger.warning(
                    "skin=%s proxy %s unreachable (attempt %d/%d): %s",
                    self.skin.name, self.proxy.id, attempt, attempts,  # type: ignore[union-attr]
                    result.error,
                )
                result = None

            if result is None:
                # Transient — back off and retry unless this was the last try.
                if attempt < attempts:
                    await asyncio.sleep(self.proxy_verify_backoff * attempt)
                continue

            # The tunnel answered — a country mismatch is definitive, not transient.
            if result.country_code and result.country_code not in self.skin.allowed_countries:
                logger.warning(
                    "skin=%s proxy egress country=%s not in allowed=%s",
                    self.skin.name, result.country_code, self.skin.allowed_countries,
                )
                return False

            logger.info(
                "skin=%s proxy OK: egress=%s country=%s latency=%.0fms (attempt %d)",
                self.skin.name, result.egress_ip, result.country_code,
                result.latency_ms or 0.0, attempt,
            )
            return True

        logger.warning(
            "skin=%s proxy %s unreachable after %d attempts — giving up",
            self.skin.name, self.proxy.id, attempts,  # type: ignore[union-attr]
        )
        return False

    async def render_dom_events(
        self,
        *,
        is_live: bool,
        sport: Optional[Any] = None,
        settle_seconds: Optional[float] = None,
        _on_page_ready: Optional[Any] = None,
        bootstrap_path: Optional[str] = None,
        dom_selectors: Optional[Any] = None,
        has_draw: bool = True,
    ) -> List[Any]:
        """Navigate the live/line page and extract events from the rendered DOM.

        This is the drift-tolerant fallback path (ADR-4): when the direct
        ``httpx`` feed poll fails (e.g. a non-2xx status), read the odds
        the SPA already rendered in a real browser instead of chasing the
        API's auth-header contract. Best-effort — returns an empty list
        on any failure rather than raising.

        Args:
            is_live: True for the live feed page, False for prematch.
            sport: optional sport filter passed to ``extract_events_from_page``.
            settle_seconds: how long to wait for the SPA to settle.
            _on_page_ready: optional async callback(page, is_live=bool) invoked
                after the page has loaded and settled but *before* extraction.
                Used by the scraper to capture success-path snapshots while
                the Playwright page is still alive.
            bootstrap_path: override the bootstrap path. Defaults to the skin's
                ``live`` or ``line`` bootstrap path. Use this to target a
                per-sport page like ``/en/line/basketball``.
            dom_selectors: optional :class:`DOMSelectors` bundle for the
                extractor. Passed through to :func:`extract_events_from_page`.
            has_draw: whether the sport's main market is 3-way (1x2) or 2-way
                (h2h). Passed through to :func:`extract_events_from_page`.
        """
        from playwright.async_api import async_playwright

        from .extraction.dom import extract_events_from_page

        wait_s = self.settle_seconds if settle_seconds is None else settle_seconds
        if bootstrap_path:
            url = f"{self.skin.base_url}{bootstrap_path}"
        else:
            route = "live" if is_live else "line"
            url = self.skin.bootstrap_url(route)
        stealth = self.skin.stealth_profile

        try:
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

                    try:
                        # 'commit' is the earliest non-empty document state.
                        # linebet's SPA keeps a long-poll open after load,
                        # so 'domcontentloaded'/'networkidle' can hang through
                        # slow residential proxies.
                        await page.goto(
                            url, wait_until="commit",
                            timeout=self.bootstrap_timeout_ms,
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "skin=%s dom-render goto %s failed: %s",
                            self.skin.name, url, exc,
                        )
                        # Even on timeout the page may be partially loaded —
                        # give it a short grace period and try anyway.

                    await self._dismiss_consent(page)
                    await asyncio.sleep(wait_s)

                    # A fixed settle is fragile across proxy speeds — the in-play
                    # Vue grid can take >10s to render through a slow tunnel,
                    # leaving extraction to run on a still-empty page (the
                    # Session 25 integration finding: 0 raw rows despite a live
                    # card). Actively wait for the game grid to attach. Best-
                    # effort: a genuinely empty card (no live games) just falls
                    # through to extraction, which returns [].
                    game_sel = (
                        dom_selectors.game if dom_selectors is not None
                        else ".dashboard-champ__game"
                    )
                    try:
                        await page.wait_for_selector(
                            game_sel, timeout=self.grid_wait_ms, state="attached",
                        )
                    except Exception:  # noqa: BLE001
                        logger.debug(
                            "skin=%s game grid %r not present after settle "
                            "(empty card or still loading)",
                            self.skin.name, game_sel,
                        )

                    # Invoke the page-ready callback (e.g. for snapshot capture)
                    # while the page is still alive.
                    if _on_page_ready is not None:
                        try:
                            await _on_page_ready(page, is_live=is_live)
                        except Exception as cb_exc:  # noqa: BLE001
                            logger.debug(
                                "skin=%s _on_page_ready callback failed: %s",
                                self.skin.name, cb_exc,
                            )

                    events = await extract_events_from_page(
                        page, is_live=is_live, source_url=url, sport=sport,
                        dom_selectors=dom_selectors, has_draw=has_draw,
                    )
                    logger.info(
                        "skin=%s dom-render extracted %d events from %s",
                        self.skin.name, len(events), url,
                    )
                    return events
                finally:
                    await browser.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("skin=%s dom-render failed: %s", self.skin.name, exc)
            return []

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
