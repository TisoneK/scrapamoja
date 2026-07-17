"""
Linebet navigation flow.

Handles Playwright navigation only — no extraction. The hybrid
architecture means the flow's job is to:

  1. Land on ``linebet.com/en`` (or ``/en/live``) in a real browser so
     Cloudflare clears and the SPA bootstraps.
  2. Optionally interact with the page (switch sport, scroll the
     fixtures list) to *trigger* additional API calls that the
     :class:`NetworkInterceptor` will capture.
  3. Wait for the API surface to settle.

Extraction lives in ``scraper.py`` + ``extraction/rules.py``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from src.sites.base.flow import BaseFlow

from .config import (
    BASE_URL,
    DEFAULT_API_SETTLE_SECONDS,
    LIVE_URL,
)

logger = logging.getLogger(__name__)


class LinebetFlow(BaseFlow):
    """Navigation flow for linebet.com.

    The flow is intentionally simple — Linebet's SPA does most of the
    work after first paint, so we just need to land on the right URL
    and wait for the API burst to finish.
    """

    def __init__(self, page: Any, selector_engine: Any) -> None:
        super().__init__(page, selector_engine)
        self.flow_name = "linebet_main_flow"
        self.description = "Navigation flow for linebet.com hybrid scraper"
        self.current_url: Optional[str] = None

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    async def navigate_to_home(self) -> bool:
        """Open ``linebet.com/en`` and wait for the SPA to start fetching."""
        return await self._goto(BASE_URL)

    async def navigate_to_live(self) -> bool:
        """Open the in-play page directly — useful for live-only scrapes."""
        return await self._goto(LIVE_URL)

    async def navigate_to_sport(self, sport_slug: str) -> bool:
        """Navigate to a specific sport page, e.g. ``football``.

        Linebet's URL scheme is ``/en/sport/<slug>``. This is best-effort;
        if the slug doesn't resolve, the SPA falls back to the home page
        and we still capture whatever API calls fire.
        """
        if not sport_slug:
            return await self.navigate_to_home()
        return await self._goto(f"{BASE_URL}/sport/{sport_slug}")

    async def _goto(self, url: str) -> bool:
        try:
            logger.info("LinebetFlow navigating to %s", url)
            # ``domcontentloaded`` is the right wait state for hybrid mode —
            # the SPA fires its first /api/ calls immediately after DCL,
            # and we want the interceptor to see them. ``networkidle`` would
            # be too late (Linebet keeps a long-poll open for live odds).
            await self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
            self.current_url = self.page.url
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("LinebetFlow navigation to %s failed: %s", url, exc)
            return False

    # ------------------------------------------------------------------
    # Triggering extra API calls
    # ------------------------------------------------------------------
    async def wait_for_api_burst(self, settle_seconds: Optional[float] = None) -> bool:
        """Wait for the SPA's initial API burst to settle.

        We deliberately don't wait for ``networkidle`` — Linebet keeps a
        long-poll open for live odds, so ``networkidle`` would time out.
        Instead, sleep for a fixed window (default
        :data:`DEFAULT_API_SETTLE_SECONDS`), which is more than enough
        for the prematch + menu + initial live fetch to complete.
        """
        delay = settle_seconds if settle_seconds is not None else DEFAULT_API_SETTLE_SECONDS
        try:
            await asyncio.sleep(delay)
            return True
        except asyncio.CancelledError:
            logger.warning("LinebetFlow API-burst wait was cancelled")
            return False

    async def scroll_fixtures(self, scroll_count: int = 3, pause_seconds: float = 1.0) -> None:
        """Scroll the fixtures list to trigger lazy-loaded API calls.

        Linebet's prematch list is paginated server-side and fetched on
        scroll. Scrolling a few times forces additional ``/api/list/``
        calls, which the interceptor captures. Safe to call when no
        scroll container is present — it just no-ops.
        """
        try:
            for _ in range(max(1, scroll_count)):
                await self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                await asyncio.sleep(pause_seconds)
        except Exception as exc:  # noqa: BLE001
            logger.debug("scroll_fixtures no-op'd: %s", exc)

    async def dismiss_consent_if_present(self) -> None:
        """Best-effort dismissal of any cookie/consent banner.

        Linebet's consent dialog (when shown) sits in an iframe from a
        consent vendor and tends to have an "Accept" button with a
        predictable label. We try a few selectors; if none match, we
        silently move on — the banner doesn't block the API calls.
        """
        candidates = [
            'button#acceptAll',
            'button[aria-label="Accept all"]',
            'button:has-text("Accept all")',
            'button:has-text("Accept All")',
            'button:has-text("Agree")',
            'a:has-text("Accept all")',
        ]
        for sel in candidates:
            try:
                locator = self.page.locator(sel).first
                if await locator.count() > 0 and await locator.is_visible(timeout=500):
                    await locator.click(timeout=2000)
                    logger.info("LinebetFlow dismissed consent banner via %s", sel)
                    return
            except Exception:  # noqa: BLE001
                continue

    # ------------------------------------------------------------------
    # BaseFlow compatibility
    # ------------------------------------------------------------------
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Default flow execution — open the home page and settle."""
        target = kwargs.get("target", "home")
        if target == "live":
            ok = await self.navigate_to_live()
        elif isinstance(target, str) and target.startswith("sport:"):
            ok = await self.navigate_to_sport(target.split(":", 1)[1])
        else:
            ok = await self.navigate_to_home()

        if not ok:
            return {"flow": self.flow_name, "success": False, "url": None}

        await self.dismiss_consent_if_present()
        await self.wait_for_api_burst()

        return {
            "flow": self.flow_name,
            "success": True,
            "url": self.current_url,
        }
