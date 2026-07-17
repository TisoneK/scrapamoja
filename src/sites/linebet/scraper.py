"""
Linebet scraper — hybrid browser + API interception.

This module is the public surface of the Linebet site template. It
extends :class:`src.sites.base.template.site_template.BaseSiteTemplate`
and implements the hybrid scraping pattern described in the package
docstring:

  1. Launch / reuse a Playwright browser pointed at ``linebet.com/en``.
  2. Attach a :class:`src.network.interception.NetworkInterceptor`
     *before* navigation, configured with
     :data:`src.sites.linebet.config.API_URL_PATTERNS`.
  3. Drive the browser via :class:`LinebetFlow` (navigate + scroll to
     trigger lazy API calls + wait for the burst to settle).
  4. Decode each captured response with
     :meth:`LinebetExtractionRules.decode_captured_response` and project
     it onto :class:`Event` instances via
     :meth:`LinebetExtractionRules.extract_from_captured`.
  5. De-duplicate events by ``event_id`` and return a single
     :class:`LinebetScrapeResult`.

Usage::

    from src.sites.linebet import LinebetScraper

    scraper = LinebetScraper(page, selector_engine)
    await scraper.initialize(page, selector_engine)
    result = await scraper.scrape(action="list_prematch")
    print(result.to_dict())

Actions:

* ``list_prematch`` — open the home page, scroll a few times, harvest
  every prematch ``/api/`` response.
* ``list_live`` — open ``/en/live``, harvest live endpoint responses.
* ``list_all`` — do both in one scrape.
* ``raw_capture`` — capture only; do not run the extractor. Useful for
  debugging API drift.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.network.interception import NetworkInterceptor, CapturedResponse
from src.sites.base.template.selector_loader import FileSystemSelectorLoader
from src.sites.base.template.site_template import BaseSiteTemplate

from .config import (
    API_URL_PATTERNS,
    DEFAULT_API_SETTLE_SECONDS,
    DEFAULT_SCRAPE_TIMEOUT_SECONDS,
    MAX_CAPTURED_RESPONSES,
    SITE_CONFIG,
    SITE_DOMAIN,
    SUPPORTED_DOMAINS,
)
from .extraction.models import (
    CapturedAPIResponse,
    Event,
    LinebetScrapeResult,
)
from .extraction.rules import LinebetExtractionRules
from .flow import LinebetFlow

logger = logging.getLogger(__name__)

_VALID_ACTIONS = {
    "list_prematch",
    "list_live",
    "list_all",
    "raw_capture",
}


class LinebetScraper(BaseSiteTemplate):
    """Hybrid browser+API scraper for linebet.com."""

    # ----- BaseSiteScraper compatibility (registry uses these) -----
    site_id = SITE_CONFIG["id"]
    site_name = SITE_CONFIG["name"]
    base_url = SITE_CONFIG["base_url"]

    def __init__(self, page: Any, selector_engine: Any) -> None:
        """Initialise the Linebet template.

        Args:
            page: Playwright page instance. Must NOT have navigated yet —
                ``NetworkInterceptor.attach`` raises :class:`TimingError`
                if called after ``page.goto``. The flow's
                ``navigate_to_*`` methods handle navigation.
            selector_engine: Framework selector engine. Used by the
                ``FileSystemSelectorLoader`` to register this template's
                YAML selectors (kept for framework compliance — the
                hybrid mode does not need them for extraction).
        """
        super().__init__(
            name="linebet",
            version="1.0.0",
            description=SITE_CONFIG["description"],
            author=SITE_CONFIG["maintainer"],
            framework_version="1.0.0",
            site_domain=SITE_DOMAIN,
            supported_domains=SUPPORTED_DOMAINS,
        )

        self.capabilities = [
            "prematch_list",
            "live_list",
            "market_capture",
            "raw_api_capture",
            "hybrid_browser_api",
        ]
        self.dependencies = [
            "BaseSiteTemplate",
            "selector_engine",
            "NetworkInterceptor",
            "playwright",
        ]

        # Framework wires ``page`` / ``selector_engine`` into us via
        # ``initialize()`` — but the quotes-style scraper (and most
        # existing call sites) pass them to ``__init__`` directly. Handle
        # both paths so we work either way.
        if page is not None:
            self.page = page
        if selector_engine is not None:
            self.selector_engine = selector_engine

        self.flow: Optional[LinebetFlow] = None
        self.extraction_rules = LinebetExtractionRules()
        self.selector_loader: Optional[FileSystemSelectorLoader] = None

        # Hybrid-mode state
        self._interceptor: Optional[NetworkInterceptor] = None
        self._captured_raw: List[CapturedResponse] = []
        self._captured_lock = asyncio.Lock()

        logger.info("LinebetScraper initialised for %s", self.site_domain)

    # ------------------------------------------------------------------
    # BaseSiteTemplate hooks
    # ------------------------------------------------------------------
    async def _setup_template_specific(self) -> bool:
        """Load YAML selectors (framework compliance) and build the flow."""
        try:
            selectors_dir = Path(__file__).parent / "selectors"
            self.selector_loader = FileSystemSelectorLoader(
                template_name=self.name,
                selector_engine=self.selector_engine,
                selectors_directory=selectors_dir,
            )
            # Loading is best-effort. The hybrid mode does not depend on
            # these selectors; they exist so the template passes framework
            # validation and so future DOM-fallback extraction can use them.
            try:
                await self.selector_loader.load_site_selectors(self.name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Linebet selector load failed (non-fatal): %s", exc)

            self.flow = LinebetFlow(self.page, self.selector_engine)
            logger.info("Linebet template-specific setup complete")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Linebet template-specific setup failed: %s", exc)
            return False

    async def _validate_scrape_params(self, action: str = "list_prematch", **kwargs: Any) -> bool:
        if action not in _VALID_ACTIONS:
            logger.error("Unknown action %r — valid: %s", action, sorted(_VALID_ACTIONS))
            return False
        if self.page is None or self.selector_engine is None:
            logger.error("Linebet scraper not initialised — call initialize() first")
            return False
        return True

    async def _execute_scrape_logic(
        self,
        action: str = "list_prematch",
        settle_seconds: Optional[float] = None,
        scroll_count: int = 3,
        timeout_seconds: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run the hybrid scrape pipeline for the requested action."""
        start = datetime.now(timezone.utc)
        timeout = timeout_seconds if timeout_seconds is not None else DEFAULT_SCRAPE_TIMEOUT_SECONDS

        try:
            async with asyncio.timeout(timeout):
                captured = await self._run_capture_pipeline(
                    action=action,
                    settle_seconds=settle_seconds,
                    scroll_count=scroll_count,
                )
        except asyncio.TimeoutError:
            logger.error("Linebet scrape timed out after %ss", timeout)
            return LinebetScrapeResult(
                action=action,
                url=self.page.url if self.page else "",
                scrape_duration_seconds=(datetime.now(timezone.utc) - start).total_seconds(),
                error=f"scrape timed out after {timeout}s",
            ).to_dict()

        # Decode + project
        decoded: List[CapturedAPIResponse] = []
        for cap in captured:
            ct = cap.headers.get("content-type", "") if cap.headers else ""
            decoded.append(
                self.extraction_rules.decode_captured_response(
                    url=cap.url,
                    status=cap.status,
                    content_type=ct,
                    raw_bytes=cap.raw_bytes,
                )
            )

        events: List[Event] = []
        if action != "raw_capture":
            for cap in decoded:
                events.extend(self.extraction_rules.extract_from_captured(cap))

        # De-duplicate events by event_id (an event can appear in both the
        # list endpoint and a per-event market-detail endpoint).
        events = self._dedupe_events(events)

        duration = (datetime.now(timezone.utc) - start).total_seconds()
        result = LinebetScrapeResult(
            action=action,
            url=self.page.url if self.page else "",
            events=events,
            captured_responses=decoded,
            scrape_duration_seconds=duration,
        )
        logger.info(
            "Linebet scrape '%s' done: %d events from %d captured responses in %.2fs",
            action, len(events), len(decoded), duration,
        )
        return result.to_dict()

    # ------------------------------------------------------------------
    # Hybrid pipeline
    # ------------------------------------------------------------------
    async def _run_capture_pipeline(
        self,
        action: str,
        settle_seconds: Optional[float],
        scroll_count: int,
    ) -> List[CapturedResponse]:
        """Attach the interceptor, drive the flow, harvest captures.

        Critical timing: ``NetworkInterceptor.attach`` MUST be called
        before any ``page.goto``. If the page has already navigated, we
        raise a clear error rather than letting the interceptor's
        ``TimingError`` propagate opaquely.
        """
        if self.flow is None:
            raise RuntimeError("LinebetFlow not built — was initialize() called?")

        # Reset capture buffer
        async with self._captured_lock:
            self._captured_raw.clear()

        # Build + attach the interceptor
        self._interceptor = NetworkInterceptor(
            patterns=list(API_URL_PATTERNS),
            handler=self._on_captured_response,
            dev_logging=False,
        )
        await self._interceptor.attach(self.page)
        logger.debug(
            "NetworkInterceptor attached with patterns=%s", API_URL_PATTERNS,
        )

        try:
            # Drive the flow. ``list_all`` does home -> live; the other
            # actions go straight to the requested page.
            if action == "list_live":
                await self.flow.navigate_to_live()
            elif action == "list_prematch":
                await self.flow.navigate_to_home()
            elif action == "list_all":
                await self.flow.navigate_to_home()
                await self.flow.scroll_fixtures(scroll_count=scroll_count)
                await self.flow.navigate_to_live()
            elif action == "raw_capture":
                await self.flow.navigate_to_home()

            # Dismiss consent banner (best-effort) — the banner can block
            # subsequent scroll-triggered fetches.
            await self.flow.dismiss_consent_if_present()

            # Trigger lazy-loaded fixtures
            if action in {"list_prematch", "list_all", "raw_capture"}:
                await self.flow.scroll_fixtures(scroll_count=scroll_count)

            # Wait for the API burst to settle
            await self.flow.wait_for_api_burst(settle_seconds=settle_seconds)

        finally:
            # Always detach so the interceptor can be re-used / re-attached
            # on a subsequent scrape call.
            if self._interceptor is not None:
                await self._interceptor.detach()
                self._interceptor = None

        async with self._captured_lock:
            captured = list(self._captured_raw)
        logger.debug("Captured %d Linebet API responses", len(captured))
        return captured

    async def _on_captured_response(self, response: CapturedResponse) -> None:
        """Handler invoked by ``NetworkInterceptor`` for every matched response."""
        async with self._captured_lock:
            if len(self._captured_raw) >= MAX_CAPTURED_RESPONSES:
                logger.warning(
                    "Captured-response cap (%d) reached — dropping %s",
                    MAX_CAPTURED_RESPONSES, response.url,
                )
                return
            self._captured_raw.append(response)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _dedupe_events(events: List[Event]) -> List[Event]:
        """De-duplicate events by ``event_id`` and merge markets."""
        by_id: Dict[str, Event] = {}
        for ev in events:
            if not ev.event_id:
                continue
            existing = by_id.get(ev.event_id)
            if existing is None:
                by_id[ev.event_id] = ev
                continue
            # Merge: prefer richer market lists; if the new copy has more
            # markets, replace; otherwise keep the existing one.
            if len(ev.markets) > len(existing.markets):
                # Keep the existing source_url (first seen wins) but take
                # the richer market list.
                existing.markets = ev.markets
                existing.raw_endpoint = ev.raw_endpoint
        return list(by_id.values())

    # ------------------------------------------------------------------
    # Introspection / framework compliance
    # ------------------------------------------------------------------
    def get_template_info(self) -> Dict[str, Any]:
        info = super().get_template_info() if hasattr(super(), "get_template_info") else {}
        info.update({
            "site_id": self.site_id,
            "site_name": self.site_name,
            "base_url": self.base_url,
            "mode": "hybrid_browser_api",
            "api_url_patterns": list(API_URL_PATTERNS),
            "default_settle_seconds": DEFAULT_API_SETTLE_SECONDS,
            "max_captured_responses": MAX_CAPTURED_RESPONSES,
        })
        return info
