"""BetB2B family base scraper.

The public surface of the betb2b site package. Parameterised by a
:class:`BetB2BSkinConfig` — every BetB2B-family bookmaker (linebet,
melbet, betwinner, 22bet, megapari, 888starz, helabet, paripesa, …)
is one skin config away from being scrapable.

Extraction mode is **hybrid** (ADR-3 in
`.context/memory/plans/decisions.md`):

  1. Browser bootstrap once through an allowed-country proxy to harvest
     ~21 session cookies (via :class:`BetB2BSessionManager`).
  2. ``httpx``-poll the ``/service-api/{LiveFeed,LineFeed}/…`` feeds
     directly (via :class:`BetB2BFeedClient`) — no browser per poll.
  3. Project the 1xbet terse-key ``Value[]`` JSON onto
     :class:`Event` / :class:`Market` / :class:`Selection` (via
     :class:`BetB2BExtractionRules`).

Per ADR-4, step 2 is best-effort: if a feed capture comes back non-2xx
or undecodable (the platform's auth-header contract rotates), the
scraper falls back to rendering the corresponding live/line page and
reading the odds via :func:`~.extraction.dom.extract_events_from_page`
instead of retrying the API.

Usage::

    from src.network.proxy import build_proxy_manager
    from src.sites.betb2b import BetB2BScraper
    from src.sites.betb2b.config import BetB2BSkinConfig

    skin = BetB2BSkinConfig.from_yaml("src/sites/betb2b/skins/linebet.yaml")
    pm = build_proxy_manager({
        "endpoints": [{"id": "kenya",
                       "url": "http://USER:PASS@bore.pub:1074",
                       "country": "KE", "source": "ngrok"}],
        "routing": [{"pattern": "*.linebet.com", "target": "kenya"}],
    })

    async with BetB2BScraper(skin, proxy_manager=pm) as scraper:
        result = await scraper.scrape(action="list_live")
        print(result["event_count"], "live events")
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.network.proxy import ProxyManager

from .client import BetB2BFeedClient
from .config import BetB2BSkinConfig
from .extraction.models import BetB2BScrapeResult, CapturedFeedResponse, Event, Sport
from .extraction.rules import BetB2BExtractionRules
from .session import BetB2BSessionManager
from .telemetry_integration import BetB2BTelemetry

logger = logging.getLogger(__name__)


_VALID_ACTIONS = {
    "list_live",          # poll LiveFeed (in-play)
    "list_prematch",      # poll LineFeed (prematch/scheduled)
    "list_all",           # poll both roots
    "raw_capture",        # capture only, no extraction
    "sports_short",       # poll the sports/champ tree
    "top_champs",         # poll the top-championships list
}


class BetB2BScraper:
    """Hybrid base scraper for the BetB2B / 1xbet family.

    This is a standalone scraper (NOT a ``BaseSiteScraper`` subclass) —
    the betb2b family is parameterised by skin, not by site, so it
    doesn't fit the one-class-per-site registry model. Per-skin
    :class:`LinebetScraper`-style adapters can wrap this if registry
    integration is needed.
    """

    def __init__(
        self,
        skin: BetB2BSkinConfig,
        *,
        proxy_manager: Optional[ProxyManager] = None,
        proxy_endpoint_id: Optional[str] = None,
        timeout: float = 20.0,
        rate_limit_per_minute: int = 30,
        settle_seconds: float = 12.0,
        telemetry: Optional[BetB2BTelemetry] = None,
        telemetry_enabled: bool = True,
        telemetry_output_dir: str = "./data/telemetry/betb2b",
    ) -> None:
        """Initialise the scraper for one skin.

        Args:
            skin: the :class:`BetB2BSkinConfig` to scrape.
            proxy_manager: a :class:`ProxyManager` with the skin's
                allowed-country proxy wired in. If None, the scraper
                runs DIRECT (only works for non-geo-gated testing).
            proxy_endpoint_id: which endpoint id in the
                :class:`ProxyManager` to route through. Defaults to
                ``skin.proxy_endpoint_id`` or "direct".
            timeout: per-request httpx timeout (seconds).
            rate_limit_per_minute: polite cap on feed polls.
            settle_seconds: how long to let the SPA settle during
                cookie-harvest bootstrap.
            telemetry: a pre-built :class:`BetB2BTelemetry` instance.
                If None, one is created automatically.
            telemetry_enabled: master switch for telemetry collection.
            telemetry_output_dir: where telemetry JSON files are written.
        """
        self.skin = skin
        self.proxy_manager = proxy_manager
        self.timeout = timeout
        self.rate_limit_per_minute = rate_limit_per_minute
        self.settle_seconds = settle_seconds

        # Resolve the proxy endpoint for this skin.
        endpoint_id = proxy_endpoint_id or skin.proxy_endpoint_id
        self.proxy_endpoint = self._resolve_proxy(endpoint_id)

        # Wire up the session manager + feed client.
        self.session_manager = BetB2BSessionManager(
            skin=skin,
            proxy=self.proxy_endpoint,
            settle_seconds=settle_seconds,
        )
        self.feed_client = BetB2BFeedClient(
            skin=skin,
            session_manager=self.session_manager,
            proxy=self.proxy_endpoint,
            timeout=timeout,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        self.extraction_rules = BetB2BExtractionRules(skin)

        # Telemetry — create if not provided, respect enabled flag.
        if telemetry is not None:
            self.telemetry = telemetry
        elif telemetry_enabled:
            self.telemetry = BetB2BTelemetry(
                skin, output_dir=telemetry_output_dir,
            )
        else:
            self.telemetry = BetB2BTelemetry.disabled(skin)

        self._started = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    async def __aenter__(self) -> "BetB2BScraper":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def start(self) -> None:
        if self._started:
            return
        await self.feed_client.start()
        self._started = True
        logger.info("BetB2BScraper started for skin=%s", self.skin.name)

    async def close(self) -> None:
        if not self._started:
            return
        await self.feed_client.close()
        # Flush any buffered telemetry events.
        self.telemetry.flush()
        self._started = False
        logger.info("BetB2BScraper closed for skin=%s", self.skin.name)

    # ------------------------------------------------------------------ #
    # Scrape
    # ------------------------------------------------------------------ #
    async def scrape(
        self,
        *,
        action: str = "list_live",
        sport_id: Optional[int] = None,
        count: int = 50,
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run one scrape action and return a :class:`BetB2BScrapeResult` dict.

        Args:
            action: one of :data:`_VALID_ACTIONS`.
            sport_id: optional sport id (``SI``) to filter the feed
                (e.g. Basketball=3, Football=1). Adds ``sports=<id>``
                to the feed query params.
            count: the ``count=`` query param (number of events to ask
                for, where supported).
            timeout_seconds: hard cap on the whole scrape.

        Returns:
            ``BetB2BScrapeResult.to_dict()`` — see
            :meth:`BetB2BScrapeResult.to_dict`.
        """
        if action not in _VALID_ACTIONS:
            raise ValueError(
                f"Unknown action {action!r} — valid: {sorted(_VALID_ACTIONS)}"
            )

        if not self.skin.enabled:
            raise RuntimeError(f"skin={self.skin.name} is disabled")

        if not self._started:
            await self.start()

        errors = self.skin.validate()
        if errors:
            raise RuntimeError(
                f"skin={self.skin.name} config invalid: {errors}"
            )

        start = datetime.now(timezone.utc)
        overall_timeout = timeout_seconds or 120.0

        try:
            async with asyncio.timeout(overall_timeout):
                captured, action_url, dom_events = await self._run_action(
                    action=action, sport_id=sport_id, count=count,
                )
        except asyncio.TimeoutError:
            logger.error(
                "skin=%s scrape '%s' timed out after %ss",
                self.skin.name, action, overall_timeout,
            )
            self.telemetry.record_scrape_complete(
                action=action, total_events=0, total_captures=0,
                session_harvested=self.session_manager.has_session,
                scrape_duration_seconds=(datetime.now(timezone.utc) - start).total_seconds(),
                error=f"scrape timed out after {overall_timeout}s",
            )
            result = BetB2BScrapeResult(
                skin=self.skin.name,
                action=action,
                url=self.skin.base_url,
                scrape_duration_seconds=(datetime.now(timezone.utc) - start).total_seconds(),
                error=f"scrape timed out after {overall_timeout}s",
            )
            return result.to_dict()

        # Extract events (unless raw_capture).
        events: List[Event] = []
        if action != "raw_capture":
            for cap in captured:
                events.extend(self.extraction_rules.extract_from_captured(cap))
            events.extend(dom_events)
            events = self._dedupe_events(events)

        # Did the session get harvested?
        session_harvested = self.session_manager.has_session

        duration = (datetime.now(timezone.utc) - start).total_seconds()
        result = BetB2BScrapeResult(
            skin=self.skin.name,
            action=action,
            url=action_url,
            events=events,
            captured_responses=captured,
            scrape_duration_seconds=duration,
            session_harvested=session_harvested,
        )
        logger.info(
            "skin=%s scrape '%s' done: %d events from %d captures in %.2fs",
            self.skin.name, action, len(events), len(captured), duration,
        )

        # Record telemetry for the complete scrape.
        total_markets = sum(len(e.markets) for e in events)
        self.telemetry.record_extraction(
            source="api" if captured else "dom",
            event_count=len(events),
            market_count=total_markets,
            duration_ms=duration * 1000,
        )
        self.telemetry.record_scrape_complete(
            action=action,
            total_events=len(events),
            total_captures=len(captured),
            session_harvested=session_harvested,
            scrape_duration_seconds=duration,
            error=result.error,
        )

        return result.to_dict()

    # ------------------------------------------------------------------ #
    # Action dispatch
    # ------------------------------------------------------------------ #
    async def _run_action(
        self,
        *,
        action: str,
        sport_id: Optional[int],
        count: int,
    ) -> "tuple[List[CapturedFeedResponse], str, List[Event]]":
        """Dispatch the action to one or more feed fetches.

        Per ADR-4, the direct-API feed is best-effort: a failed capture
        (non-2xx status, e.g. the 406 seen when the platform rotates its
        auth-header contract) triggers a DOM-extraction fallback on the
        corresponding live/line page instead of retrying the API.
        """
        extra_params: Dict[str, str] = {"count": str(count)}
        if sport_id is not None:
            extra_params["sports"] = str(sport_id)

        captured: List[CapturedFeedResponse] = []
        dom_events: List[Event] = []

        if action == "list_live":
            cap = await self.feed_client.fetch(
                "events_top", root="live", extra_params=extra_params,
            )
            captured.append(cap)
            if self._capture_failed(cap):
                dom_events.extend(await self._dom_fallback(is_live=True))
            return captured, cap.url, dom_events

        if action == "list_prematch":
            cap = await self.feed_client.fetch(
                "events_top", root="line", extra_params=extra_params,
            )
            captured.append(cap)
            if self._capture_failed(cap):
                dom_events.extend(await self._dom_fallback(is_live=False))
            return captured, cap.url, dom_events

        if action == "list_all":
            live_cap = await self.feed_client.fetch(
                "events_top", root="live", extra_params=extra_params,
            )
            line_cap = await self.feed_client.fetch(
                "events_top", root="line", extra_params=extra_params,
            )
            captured.extend([live_cap, line_cap])
            if self._capture_failed(live_cap):
                dom_events.extend(await self._dom_fallback(is_live=True))
            if self._capture_failed(line_cap):
                dom_events.extend(await self._dom_fallback(is_live=False))
            return captured, live_cap.url, dom_events

        if action == "raw_capture":
            # Capture both roots, no extraction, no DOM fallback.
            live_cap = await self.feed_client.fetch(
                "events_top", root="live", extra_params=extra_params,
            )
            captured.append(live_cap)
            return captured, live_cap.url, dom_events

        if action == "sports_short":
            # Both roots have a sports-short endpoint — prefer LineFeed
            # (prematch has the fuller tree). No DOM fallback (not an
            # event listing).
            cap = await self.feed_client.fetch(
                "sports_short", root="line", extra_params=extra_params,
            )
            captured.append(cap)
            return captured, cap.url, dom_events

        if action == "top_champs":
            cap = await self.feed_client.fetch(
                "top_champs", root="line", extra_params=extra_params,
            )
            captured.append(cap)
            return captured, cap.url, dom_events

        # Unreachable — action validated above.
        raise ValueError(f"Unhandled action {action!r}")

    @staticmethod
    def _capture_failed(cap: CapturedFeedResponse) -> bool:
        """True if the API capture didn't yield usable data."""
        return cap.status == 0 or cap.status >= 400 or not cap.decoded

    async def _dom_fallback(self, *, is_live: bool) -> List[Event]:
        """Render the corresponding live/line page and extract via DOM."""
        try:
            default_sport = Sport.OTHER
        except Exception:  # noqa: BLE001
            default_sport = None
        try:
            return await self.session_manager.render_dom_events(
                is_live=is_live, sport=default_sport,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "skin=%s DOM fallback (is_live=%s) failed: %s",
                self.skin.name, is_live, exc,
            )
            return []

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _resolve_proxy(self, endpoint_id: Optional[str]) -> Optional[Any]:
        """Resolve the proxy endpoint for this skin from the ProxyManager."""
        if self.proxy_manager is None:
            return None
        try:
            # Prefer an explicit endpoint id when the caller named one;
            # otherwise let routing rules pick from the skin's domain.
            if endpoint_id:
                ep = self.proxy_manager.get(endpoint_id)
                if ep is not None:
                    return ep
            return self.proxy_manager.acquire(site=self.skin.domain)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "skin=%s proxy resolution failed (endpoint_id=%s): %s — "
                "falling back to DIRECT",
                self.skin.name, endpoint_id, exc,
            )
            return None

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
            # Merge: prefer richer market lists; keep the first source_url.
            if len(ev.markets) > len(existing.markets):
                existing.markets = ev.markets
                existing.raw_endpoint = ev.raw_endpoint
            # Prefer the live version if we have both.
            if ev.is_live and not existing.is_live:
                existing.is_live = True
                existing.status = ev.status
                existing.score_home = ev.score_home or existing.score_home
                existing.score_away = ev.score_away or existing.score_away
                existing.minute = ev.minute or existing.minute
                existing.period = ev.period or existing.period
                existing.time_remaining = ev.time_remaining or existing.time_remaining
        return list(by_id.values())

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #
    def get_info(self) -> Dict[str, Any]:
        """Return scraper + skin info for the ``info`` CLI command."""
        return {
            "skin": self.skin.to_dict(),
            "actions": sorted(_VALID_ACTIONS),
            "extraction_mode": "hybrid (API primary, DOM fallback on failed capture — ADR-4)",
            "proxy_endpoint": (
                self.proxy_endpoint.to_dict(redact=True)
                if self.proxy_endpoint is not None
                else None
            ),
            "session_harvested": self.session_manager.has_session,
            "session_age_seconds": (
                self.session_manager.session_age.total_seconds()
                if self.session_manager.session_age is not None else None
            ),
            "telemetry": self.telemetry.get_summary(),
        }
