"""Session bootstrap for the BetB2B family scraper.

Implements the "browser-harvest cookies" half of the hybrid extraction
mode.

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
or the httpx client sees an auth-error status (401/419/440), at
which point :meth:`BetB2BSessionManager.get_session` re-bootstraps.
Challenges, country blocks, bans and rate limits are NOT answered with a
blind re-bootstrap — they go through the :mod:`src.security` guard.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, List, Optional

from src.network.proxy import ProxyEndpoint, verify_proxy
from src.network.session import SessionHarvester, SessionPackage, SessionValidator
from src.security import (
    BETB2B_RULES, Action, BlockType, BlockVerdict, BrowserTier, SecurityGuard,
    SiteBlocked, SiteInCooldown,
)
from src.security import Pacer
from src.security import resolver as sec_resolver

from .config import BetB2BSkinConfig

logger = logging.getLogger(__name__)

# $BETB2B_PROFILE: "off" → fresh throwaway browser every run (old behaviour);
# unset → a persistent profile named after the skin; anything else → that name.
PROFILE_ENV = "BETB2B_PROFILE"
_MAX_BLOCK_STEPS = 8        # rungs one bootstrap may climb before giving up


class _Retry(Exception):
    """Internal: close this browser and bootstrap again at the (new) tier."""


def profile_name_for(skin_name: str) -> Optional[str]:
    raw = (os.environ.get(PROFILE_ENV) or "").strip()
    if raw.lower() in ("off", "0", "false", "none", "ephemeral"):
        return None
    return raw or f"betb2b-{skin_name}"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


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
        security_guard: Optional[SecurityGuard] = None,
        has_browser: bool = True,
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

        # Block history is per (skin, egress): a geo block seen direct says
        # nothing about the same skin through an allowed-country proxy.
        egress = proxy.id if proxy is not None and not proxy.is_direct else None
        self.guard = security_guard or SecurityGuard(
            f"{skin.name}@{egress}" if egress else skin.name,
            rules=BETB2B_RULES,
            has_failover=bool(os.environ.get("BETB2B_FALLBACK_SKINS")),
            has_browser=has_browser,
            fail_threshold=_env_int("BETB2B_FAIL_THRESHOLD", 6),
            fail_cooldown=float(_env_int("BETB2B_FAIL_COOLDOWN", 300)),
            hourly_budget=_env_int("BETB2B_HOURLY_BUDGET", 0),
        )
        # One pacer per skin, shared by the feed client and the scraper's direct calls:
        # bounds requests PER SECOND (concurrency alone still sends ~20/s on a fast site).
        self.pacer = Pacer(float(os.environ.get("BETB2B_MAX_RPS", 3) or 0))
        self._profiles: Optional[Any] = None
        self.profile_name = profile_name_for(skin.name)

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

    @property
    def profiles(self) -> Any:
        """The profile manager — imported lazily: ``src.browser`` logs to stdout on import,
        which would corrupt the CLI's JSON output."""
        if self._profiles is None:
            from src.browser.profiles import ProfileManager
            self._profiles = ProfileManager()
        return self._profiles

    @asynccontextmanager
    async def _open_page(self, pw: Any, tier: BrowserTier) -> AsyncIterator[Any]:
        """Open a browser at ``tier`` and yield ``(context, page)``; always closed on exit.

        Uses the skin's persistent profile (cookies and any passed browser
        validation survive between runs) unless ``$BETB2B_PROFILE=off`` or the
        profile is already open in another process, in which case a throwaway
        browser is used. Tier 0 keeps the skin's configured identity; stronger
        tiers let the real browser report its own user agent, which is the
        only consistent one.
        """
        from contextlib import AsyncExitStack

        from src.browser.profiles import ProfileInUse

        stealth = self.skin.stealth_profile
        identity: dict[str, Any] = {
            "viewport": stealth.get("viewport", {"width": 1536, "height": 864}),
            "locale": stealth.get("locale", "en-US"),
            "timezone_id": stealth.get("timezone", "Europe/London"),
        }
        if not tier.apply_stealth:
            identity["user_agent"] = stealth.get("user_agent")
        proxy_cfg = None
        if self.proxy is not None and not self.proxy.is_direct:
            proxy_cfg = self.proxy.to_playwright_proxy() or None
        headless = bool(stealth.get("headless", True)) and tier.headless

        async def launch(stack: AsyncExitStack, channel: Optional[str]) -> Any:
            if self.profile_name:
                try:
                    return await stack.enter_async_context(self.profiles.open_context(
                        pw, self.profile_name, headless=headless, channel=channel,
                        stealth_args=tier.apply_stealth, proxy=proxy_cfg, identity=identity))
                except ProfileInUse as exc:
                    logger.warning("skin=%s %s — using a throwaway browser", self.skin.name, exc)
            kwargs: dict[str, Any] = {"headless": headless}
            if channel:
                kwargs["channel"] = channel
            if tier.apply_stealth:
                kwargs["args"] = ["--disable-blink-features=AutomationControlled"]
                kwargs["ignore_default_args"] = ["--enable-automation"]
            browser = await pw.chromium.launch(**kwargs)
            stack.push_async_callback(browser.close)
            ctx_kwargs = dict(identity)
            if proxy_cfg:
                ctx_kwargs["proxy"] = proxy_cfg
            return await browser.new_context(**ctx_kwargs)

        async with AsyncExitStack() as stack:
            try:
                context = await launch(stack, tier.channel)
            except Exception as exc:  # noqa: BLE001
                if not tier.channel:
                    raise
                logger.warning("skin=%s tier %s unavailable (%s) — using bundled Chromium",
                               self.skin.name, tier.name, str(exc).splitlines()[0])
                context = await launch(stack, None)
            if tier.apply_stealth:
                try:
                    from src.stealth.anti_detection import AntiDetectionMasker
                    await AntiDetectionMasker().apply_masks(context)
                except Exception as exc:  # noqa: BLE001 — masking is an extra, never a blocker
                    logger.debug("skin=%s stealth masks not applied: %s", self.skin.name, exc)
            page = context.pages[0] if context.pages else await context.new_page()
            yield page

    def _explain_block(self, verdict: BlockVerdict) -> None:
        """Say what a country/IP block means for *this* egress, so the log is actionable."""
        if verdict.type not in (BlockType.GEO_BLOCK, BlockType.IP_BANNED):
            return
        if self.proxy is not None and not self.proxy.is_direct:
            logger.warning(
                "skin=%s still blocked THROUGH proxy %r — the proxy is the problem (tunnel down or "
                "rotated, or its egress country/IP is not allowed). Check the proxy; this skin is "
                "rested on this egress only.", self.skin.name, self.proxy.id)
        elif not os.environ.get("BETB2B_PROXY_URL"):
            logger.warning(
                "skin=%s blocked on the DIRECT egress. The browser path needs an allowed-country "
                "proxy (set BETB2B_PROXY_URL/USER/PASS, e.g. a tunnel that exits in an allowed country); feed endpoints "
                "usually work direct.", self.skin.name)
        else:
            logger.warning("skin=%s blocked on the DIRECT egress although BETB2B_PROXY_URL is set — "
                           "run without --direct / pass the proxy to the browser path.", self.skin.name)

    async def _check_page(self, page: Any, status: Optional[int], tier: BrowserTier) -> None:
        """Classify what ``page`` shows; walk the ladder if it is a block."""
        verdict = await self.guard.inspect_page(page, status)
        if verdict.blocked:
            await self._resolve_block(page, verdict, tier)

    async def _resolve_block(self, page: Any, verdict: BlockVerdict, tier: BrowserTier) -> None:
        """Walk the policy ladder for a block seen on ``page``.

        Returns when the page is clear. Raises :class:`_Retry` to re-open the
        browser at a stronger tier, or :class:`SiteBlocked` when nothing the
        caller can do is left (failover / cooldown / abort).
        """
        for _ in range(_MAX_BLOCK_STEPS):
            decision = self.guard.on_block(verdict)
            if decision.action is Action.WAIT_FOR_CLEARANCE:
                clearance = await sec_resolver.wait_for_clearance(page, rules=BETB2B_RULES)
            elif decision.action is Action.HUMAN_HANDOFF and not tier.headless:
                clearance = await sec_resolver.human_handoff(
                    page, site=self.skin.name, rules=BETB2B_RULES)
            elif decision.action in (Action.ESCALATE_BROWSER, Action.REFRESH_SESSION):
                raise _Retry()
            else:
                self._explain_block(verdict)
                raise self.guard.blocked(verdict, decision)
            if clearance.cleared:
                logger.info("skin=%s block cleared after %.0fs (%s)", self.skin.name,
                            clearance.waited_s, decision.action.value)
                return
            verdict = clearance.verdict
        raise self.guard.blocked(verdict)

    async def _bootstrap(self) -> SessionPackage:
        """Run the browser bootstrap → cookie harvest pipeline.

        A block (country, JS challenge, CAPTCHA, …) is classified and answered
        by the guard's policy — wait it out, retry in a stronger browser, hand
        to a person — rather than re-bootstrapped blindly; a site that keeps
        blocking is put on cooldown and surfaces as :class:`SiteBlocked`.
        """
        if not self.skin.enabled:
            raise RuntimeError(f"skin={self.skin.name} is disabled")
        self.guard.preflight()   # SiteInCooldown: don't touch a site that just blocked us

        # Validate proxy egress country BEFORE opening a browser — saves
        # an expensive Playwright launch if the proxy is misconfigured.
        if self.proxy is not None and not self.proxy.is_direct:
            ok = await self._verify_proxy_country()
            if not ok:
                raise RuntimeError(
                    f"skin={self.skin.name}: proxy {self.proxy.id!r} egress "
                    f"country not in allowed_countries={self.skin.allowed_countries}"
                )

        for _ in range(_MAX_BLOCK_STEPS):
            try:
                session = await self._bootstrap_once(self.guard.tier)
            except _Retry:
                continue
            self.guard.on_success()
            return session
        raise RuntimeError(f"skin={self.skin.name}: bootstrap did not settle after {_MAX_BLOCK_STEPS} attempts")

    async def _bootstrap_once(self, tier: BrowserTier) -> SessionPackage:
        from playwright.async_api import async_playwright

        logger.info(
            "skin=%s bootstrapping session via proxy=%s domain=%s tier=%s profile=%s",
            self.skin.name,
            self.proxy.id if self.proxy and not self.proxy.is_direct else "DIRECT",
            self.skin.domain, tier.name, self.profile_name or "ephemeral",
        )

        async with async_playwright() as pw:
            async with self._open_page(pw, tier) as page:
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

                # Classify what we landed on: country block (HTTP 203 →
                # /en/block), JS browser-validation page, CAPTCHA, ban, ...
                # Also when the navigation itself errored (a reset can still
                # leave a challenge page behind).
                await self._check_page(page, resp.status if resp is not None else None, tier)

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

                # Never harvest cookies from a page that is showing a challenge.
                await self._check_page(page, None, tier)

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

        This is the drift-tolerant fallback path: when the direct
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
        try:
            self.guard.preflight()
        except SiteInCooldown as exc:
            logger.warning("skin=%s dom-render skipped: %s", self.skin.name, exc)
            return []

        try:
            async with async_playwright() as pw:
                async with self._open_page(pw, self.guard.tier) as page:
                    resp = None
                    try:
                        # 'commit' is the earliest non-empty document state.
                        # linebet's SPA keeps a long-poll open after load,
                        # so 'domcontentloaded'/'networkidle' can hang through
                        # slow residential proxies.
                        resp = await page.goto(
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

                    await self._check_page(page, resp.status if resp is not None else None,
                                           self.guard.tier)

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
        except _Retry:
            logger.warning("skin=%s dom-render blocked; escalated browser tier for the next attempt",
                           self.skin.name)
            return []
        except SiteBlocked as exc:
            logger.warning("skin=%s dom-render skipped: %s", self.skin.name, exc)
            return []
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
