"""Compare match page UI data vs API endpoint data for BetB2B skins.

Navigates to a specific match page (e.g. an NBA game on linebet),
extracts ALL visible UI data from the rendered page, polls ALL available
API endpoints for that match, and produces a structured comparison report
showing:

- What data the UI shows
- What data the API endpoints return
- What data we are NOT currently collecting (the gap)

Usage::

    # By event ID + sport (auto-constructs the match URL)
    python -m src.sites.betb2b.scripts.compare_match \\
        --skin linebet --sport basketball --event-id 352015844

    # By explicit match URL
    python -m src.sites.betb2b.scripts.compare_match \\
        --skin linebet \\
        --match-url "https://linebet.com/en/line/basketball/352015844-..."

    # Live match (vs prematch)
    python -m src.sites.betb2b.scripts.compare_match \\
        --skin linebet --sport basketball --event-id 352015844 --live

    # With proxy
    BETB2B_PROXY_URL=http://bore.pub:37582 \\
    BETB2B_PROXY_USER=TisoneK BETB2B_PROXY_PASS=Taalib01 \\
    BETB2B_PROXY_COUNTRY=KE BETB2B_PROXY_ID=kenya \\
    python -m src.sites.betb2b.scripts.compare_match \\
        --skin linebet --sport basketball --event-id 352015844

Output::

    data/telemetry/betb2b/match_comparison/<timestamp>_<skin>_<event>/
    ├── comparison_report.json   # Full structured comparison
    ├── match_page.html          # Rendered HTML for reference
    ├── match_screenshot.png     # Full-page screenshot
    └── api_responses/           # Raw API responses
        ├── GetGameZip.json
        ├── GetSubsOptionsForGame.json
        ├── h2h.json
        └── ...
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models for the comparison report
# ---------------------------------------------------------------------------
@dataclass
class UICategory:
    """One category of UI data extracted from the match page."""

    field: str
    found: bool
    value: Any = None
    note: str = ""


@dataclass
class APIEndpointResult:
    """Result of polling one API endpoint."""

    endpoint: str
    url: str
    status: int
    success: bool
    data_size: int
    has_value: bool
    error: str = ""
    keys: List[str] = field(default_factory=list)


@dataclass
class Gap:
    """A data gap — something visible in UI but NOT collected from API."""

    category: str        # e.g. "scoreboard", "period_scores", "statistics"
    data_found: str      # what the UI shows
    api_available: bool  # whether any API has this data
    api_source: str      # which endpoint would provide it
    currently_collected: bool  # whether our extraction pipeline collects it
    recommendation: str  # what to do


@dataclass
class ComparisonReport:
    """Complete comparison between UI data and API endpoint data."""

    skin: str = ""
    event_id: str = ""
    match_url: str = ""
    sport: str = ""
    timestamp: str = ""

    # UI categories found on the page
    ui_categories: Dict[str, bool] = field(default_factory=dict)

    # Detailed UI data
    scoreboard: Dict[str, Any] = field(default_factory=dict)
    period_scores: List[Dict[str, Any]] = field(default_factory=list)
    statistics: List[Dict[str, Any]] = field(default_factory=list)
    market_groups_page: List[Dict[str, Any]] = field(default_factory=list)
    h2h_sections: List[Dict[str, Any]] = field(default_factory=list)

    # API endpoint results
    api_endpoints: List[Dict[str, Any]] = field(default_factory=list)

    # Gap analysis
    gaps: List[Dict[str, Any]] = field(default_factory=list)

    # What we currently collect vs what's available
    currently_collected: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helper: resolve match URL
# ---------------------------------------------------------------------------
def _sport_slug(sport_name: str) -> str:
    """Convert sport name to URL slug used by BetB2B."""
    slug_map = {
        "basketball": "basketball",
        "football": "football",
        "ice-hockey": "ice-hockey",
        "tennis": "tennis",
        "esports": "esports",
        "baseball": "baseball",
    }
    return slug_map.get(sport_name.lower(), sport_name.lower())


def build_match_url(
    skin_domain: str,
    sport: str,
    event_id: str,
    *,
    is_live: bool = False,
) -> str:
    """Build a match page URL from parts.

    The exact URL path pattern varies by sport. For basketball:
    ``/en/line/basketball/<champ-id>-<champ-name>/<event-id>-<teams>``

    We construct the shortest plausible path; the SPA redirects as needed.
    """
    prefix = "live" if is_live else "line"
    slug = _sport_slug(sport)
    return f"https://{skin_domain}/en/{prefix}/{slug}/0-unknown/{event_id}-match"


# ---------------------------------------------------------------------------
# API endpoint definitions
# ---------------------------------------------------------------------------
# Known BetB2B API endpoints for a specific match, with parameter schemas.
MATCH_API_ENDPOINTS: List[Dict[str, Any]] = [
    {
        "name": "GetGameZip",
        "path": "/service-api/{root}Feed/GetGameZip",
        "params": {"id": "{event_id}", "isSubGames": "true", "grMode": "4"},
        "root": "line",
        "description": "Full event with all markets (primary odds path)",
        "currently_collected": True,  # via _enrich_dom_events_with_odds
    },
    {
        "name": "GetSubsOptionsForGame",
        "path": "/service-api/{root}Feed/GetSubsOptionsForGame",
        "params": {"id": "{event_id}"},
        "root": "line",
        "description": "Substitution / market options for the event",
        "currently_collected": False,
    },
    {
        "name": "H2H (statisticfeed)",
        "path": "/service-api/statisticfeed/api/v1/Game/h2h",
        "params": {"id": "{h2h_id}", "lng": "en", "ref": "{partner}", "fcountry": "{country}", "gr": "{gr}"},
        "root": "line",
        "description": "Head-to-head statistics (previous meetings, form)",
        "currently_collected": True,  # via discover_h2h.py (separate script)
    },
    {
        "name": "GameStatistics (statisticfeed)",
        "path": "/service-api/statisticfeed/api/v1/Game/statistics",
        "params": {"id": "{h2h_id}", "lng": "en", "ref": "{partner}", "fcountry": "{country}", "gr": "{gr}"},
        "root": "line",
        "description": "Per-match statistics (possession, shots, etc.)",
        "currently_collected": False,
    },
    {
        "name": "GameTimeline (statisticfeed)",
        "path": "/service-api/statisticfeed/api/v1/Game/timeline",
        "params": {"id": "{h2h_id}", "lng": "en", "ref": "{partner}", "fcountry": "{country}", "gr": "{gr}"},
        "root": "line",
        "description": "Match timeline (goals, cards, events)",
        "currently_collected": False,
    },
    {
        "name": "GetGameZip (live)",
        "path": "/service-api/{root}Feed/GetGameZip",
        "params": {"id": "{event_id}", "isSubGames": "true", "grMode": "4"},
        "root": "live",
        "description": "Live version of GetGameZip",
        "currently_collected": True,
    },
    {
        "name": "Get1x2_VZip (sport-filtered)",
        "path": "/service-api/{root}Feed/Get1x2_VZip",
        "params": {"id": "{event_id}", "count": "1"},
        "root": "line",
        "description": "List feed filtered to just this event",
        "currently_collected": False,
    },
]


# ---------------------------------------------------------------------------
# API polling
# ---------------------------------------------------------------------------
async def poll_match_endpoints(
    skin: Any,
    event_id: str,
    *,
    session_manager: Any,
    proxy_endpoint: Any = None,
) -> List[Dict[str, Any]]:
    """Poll all known API endpoints for a match and return results.

    Uses the existing :class:`BetB2BFeedClient` for authenticated feeds
    and direct httpx for unauthenticated statisticfeed endpoints.

    Args:
        skin: BetB2BSkinConfig instance.
        event_id: the target event's numeric ID.
        session_manager: BetB2BSessionManager for harvested cookies.
        proxy_endpoint: optional ProxyEndpoint for routing.

    Returns:
        List of APIEndpointResult dicts.
    """
    import httpx
    from src.sites.betb2b.client import BetB2BFeedClient
    from src.sites.betb2b.extraction.rules import BetB2BExtractionRules

    results: List[Dict[str, Any]] = []

    # Build feed client for service-api endpoints
    feed_client = BetB2BFeedClient(
        skin=skin,
        session_manager=session_manager,
        proxy=proxy_endpoint,
        timeout=20.0,
        rate_limit_per_minute=30,
    )
    await feed_client.start()

    try:
        for ep_def in MATCH_API_ENDPOINTS:
            name = ep_def["name"]
            root = ep_def["root"]
            currently_collected = ep_def["currently_collected"]

            try:
                # Resolve params
                params = {}
                for k, v in ep_def["params"].items():
                    resolved = v.replace("{event_id}", str(event_id))
                    resolved = resolved.replace("{partner}", str(skin.partner))
                    resolved = resolved.replace("{country}", str(skin.country))
                    resolved = resolved.replace("{gr}", str(skin.gr))
                    # h2h_id is unknown at this stage — try with event_id
                    resolved = resolved.replace("{h2h_id}", str(event_id))
                    params[k] = resolved

                # For statisticfeed endpoints, build URL manually
                if "statisticfeed" in ep_def["path"]:
                    url = f"{skin.base_url}{ep_def['path']}?{_urlencode(params)}"
                    # Direct httpx call with harvested session cookies
                    session = await session_manager.get_session()
                    cookie_header = session.to_cookie_header()
                    headers = skin.merged_headers(session_cookies=cookie_header)
                    headers["accept"] = "application/json"

                    proxy_url = proxy_endpoint.to_httpx_proxy() if proxy_endpoint else None
                    async with httpx.AsyncClient(proxy=proxy_url, timeout=20.0, follow_redirects=True) as client:
                        resp = await client.get(url, headers=headers)
                        data = _decode_response(resp)
                        results.append(_make_endpoint_result(
                            name=name, url=url, status=resp.status_code,
                            data=data, currently_collected=currently_collected,
                            endpoint_path=ep_def["path"],
                        ))
                else:
                    # Use feed client for service-api endpoints
                    cap = await feed_client.fetch(
                        "game" if "GetGameZip" in ep_def["path"] or "GetSubsOptions" in ep_def["path"] else "events_top",
                        root=root,
                        extra_params=params,
                    )
                    data = cap.decoded if cap.decoded else {}
                    results.append(_make_endpoint_result(
                        name=name, url=cap.url, status=cap.status,
                        data=data, currently_collected=currently_collected,
                        endpoint_path=ep_def["path"],
                    ))

            except Exception as exc:
                logger.warning("Endpoint %s failed: %s", name, exc)
                results.append({
                    "endpoint": name,
                    "endpoint_path": ep_def["path"],
                    "url": "",
                    "status": 0,
                    "success": False,
                    "error": str(exc),
                    "data_size": 0,
                    "has_value": False,
                    "keys": [],
                    "currently_collected": currently_collected,
                })
    finally:
        await feed_client.close()

    return results


def _urlencode(params: Dict[str, str]) -> str:
    from urllib.parse import urlencode
    return urlencode(params)


def _decode_response(resp: Any) -> Any:
    """Try to decode an httpx response as JSON."""
    try:
        return resp.json()
    except Exception:
        try:
            text = resp.text[:500]
            return {"raw_text": text}
        except Exception:
            return {}


def _status_ok(code: int) -> bool:
    """Return True if status code indicates success (2xx or 204)."""
    return code == 204 or (200 <= code < 300)


def _make_endpoint_result(
    *,
    name: str,
    url: str,
    status: int,
    data: Any,
    currently_collected: bool,
    endpoint_path: str,
) -> Dict[str, Any]:
    """Build a result dict for one endpoint."""
    has_value = False
    keys: List[str] = []
    data_size = 0

    if isinstance(data, dict):
        has_value = bool(data.get("Success")) if "Success" in data else len(data) > 0
        keys = list(data.keys())
        if "Value" in data and isinstance(data["Value"], list):
            data_size = len(data["Value"])
        else:
            data_size = len(json.dumps(data, default=str))
    elif isinstance(data, list):
        has_value = len(data) > 0
        data_size = len(data)
    else:
        data_size = len(str(data))

    return {
        "endpoint": name,
        "endpoint_path": endpoint_path,
        "url": url,
        "status": status,
        "success": _status_ok(status),
        "error": "",
        "data_size": data_size,
        "has_value": has_value,
        "keys": keys,
        "currently_collected": currently_collected,
    }


# ---------------------------------------------------------------------------
# Gap analysis
# ---------------------------------------------------------------------------
def _analyze_gaps(
    ui_data: Dict[str, Any],
    api_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Compare UI data vs API data and identify gaps.

    A gap = something visible in the UI that is NOT available from any
    API endpoint we polled, OR is available but not currently collected
    by our extraction pipeline.
    """
    gaps: List[Dict[str, Any]] = []

    # ── Scoreboard fields ──────────────────────────────────────
    sb = ui_data.get("scoreboard", {})
    # (field_name, display_name, currently_collected, api_category_key)
    scoreboard_fields = [
        ("home_team", "Team names (home/away)", True, "team_names"),
        ("away_team", "Team names (home/away)", True, "team_names"),
        ("home_score", "Live/final scores", True, "scores"),
        ("away_score", "Live/final scores", True, "scores"),
        ("competition", "League/competition name", True, "competition"),
        ("status", "Match status (live/finished/not_started)", True, "status"),
        ("minute", "Live minute", True, "minute"),
        ("period", "Current period (quarter, half, set)", True, "period"),
        ("venue", "Venue/stadium name", False, "venue"),
        ("start_time", "Match start time", True, "start_time"),
    ]

    # Check what we collect vs what the API provides
    api_has_values: Dict[str, bool] = {
        "team_names": False,
        "scores": False,
        "competition": False,
        "status": False,
        "minute": False,
        "period": False,
        "venue": False,
        "start_time": False,
        "period_scores": False,
        "statistics": False,
        "markets": False,
        "h2h": False,
    }

    # Which API endpoint provides what
    api_provides: Dict[str, str] = {
        "team_names": "GetGameZip",
        "scores": "GetGameZip",
        "competition": "GetGameZip",
        "status": "GetGameZip",
        "minute": "GetGameZip",
        "period": "GetGameZip (SC field)",
        "venue": "None (not in any known endpoint)",
        "start_time": "GetGameZip (S field)",
        "period_scores": "GetGameZip (SC.PS[] or AE[])",
        "statistics": "statisticfeed/statistics",
        "markets": "GetGameZip (E[]/AE[])",
        "h2h": "statisticfeed/h2h",
    }

    for api_res in api_results:
        ep = api_res.get("endpoint", "")
        reached = _status_ok(api_res.get("status", 0))
        has_data = api_res.get("success") and api_res.get("has_value")

        if reached and has_data:
            if "GetGameZip" in ep:
                api_has_values["team_names"] = True
                api_has_values["scores"] = True
                api_has_values["competition"] = True
                api_has_values["status"] = True
                api_has_values["minute"] = True
                api_has_values["period"] = True
                api_has_values["start_time"] = True
                api_has_values["period_scores"] = True
                api_has_values["markets"] = True
            if "statisticfeed" in ep:
                if "h2h" in ep:
                    api_has_values["h2h"] = True
                if "statistics" in ep:
                    api_has_values["statistics"] = True
                if "timeline" in ep:
                    api_has_values["statistics"] = True

    for field_name, display_name, currently_collected, api_key in scoreboard_fields:
        ui_value = sb.get(field_name)
        found = bool(ui_value) and ui_value not in (None, "", 0, "0")
        api_source = api_provides.get(api_key, "unknown")
        api_avail = api_has_values.get(api_key, False)

        if found and not currently_collected:
            gaps.append({
                "category": "scoreboard",
                "data_found": f"{display_name} = {ui_value}",
                "api_available": api_avail,
                "api_source": api_source,
                "currently_collected": False,
                "recommendation": f"Add {field_name} to Event dataclass extraction",
            })
        elif found and currently_collected and not api_avail:
            gaps.append({
                "category": "scoreboard",
                "data_found": f"{display_name} = {ui_value} (UI only)",
                "api_available": False,
                "api_source": api_source,
                "currently_collected": True,
                "recommendation": f"Confirm {field_name} is in API schema (may be in raw SC field)",
            })

    # ── Period scores ───────────────────────────────────────────
    period_scores = ui_data.get("period_scores", [])
    if period_scores:
        if not api_has_values["period_scores"]:
            gaps.append({
                "category": "period_scores",
                "data_found": f"{len(period_scores)} periods: {period_scores[:3]}...",
                "api_available": api_has_values["period_scores"],
                "api_source": "GetGameZip (SC.PS[] or separate feed)",
                "currently_collected": True,
                "recommendation": "✅ Wired: _extract_period_scores() in rules.py extracts SC.PS[] into Event.period_scores",
            })
        else:
            # Even if available, check if we extract it
            gaps.append({
                "category": "period_scores",
                "data_found": f"{len(period_scores)} period scores found in UI",
                "api_available": True,
                "api_source": "GetGameZip (SC field)",
                "currently_collected": True,
                "recommendation": "✅ Wired: _extract_period_scores() in rules.py now extracts SC.PS[] into Event.period_scores",
            })

    # ── Statistics ──────────────────────────────────────────────
    stats = ui_data.get("statistics", [])
    if stats:
        api_stat_ok = any("statistics" in r.get("endpoint", "") and r.get("success")
                          for r in api_results)
        gaps.append({
            "category": "statistics",
            "data_found": f"{len(stats)} stat rows: {[s.get('label') for s in stats[:5]]}",
            "api_available": api_stat_ok,
            "api_source": "statisticfeed/api/v1/Game/statistics",
            "currently_collected": False,
            "recommendation": (
                "Add statisticfeed/statistics endpoint to scraper; "
                "wire into Event as optional stats field"
            ),
        })

    # ── H2H ─────────────────────────────────────────────────────
    h2h = ui_data.get("h2h_sections", [])
    if h2h:
        api_h2h_ok = any("h2h" in r.get("endpoint", "") and r.get("success")
                         for r in api_results)
        gaps.append({
            "category": "h2h",
            "data_found": f"{len(h2h)} H2H sections found in UI (hover-triggered popup)",
            "api_available": api_h2h_ok,
            "api_source": "statisticfeed/api/v1/Game/h2h",
            "currently_collected": False,
            "recommendation": (
                "Wire H2H data into scraper from statisticfeed endpoint "
                "(exists as separate script, not in main pipeline)"
            ),
        })

    # ── Market groups on match page ─────────────────────────────
    markets = ui_data.get("market_groups", [])
    if markets:
        api_market_ok = api_has_values["markets"]
        gaps.append({
            "category": "markets",
            "data_found": f"{len(markets)} market groups on match page",
            "api_available": api_market_ok,
            "api_source": "GetGameZip (E[]/AE[] arrays)",
            "currently_collected": True,
            "recommendation": (
                "Markets are collected from GetGameZip. Verify match-page "
                "renders same markets as API response."
            ),
        })

    return gaps


# ---------------------------------------------------------------------------
# Main script
# ---------------------------------------------------------------------------
async def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare match page UI data vs API endpoints for BetB2B skins"
    )
    parser.add_argument("--skin", default="linebet", help="Skin name (default: linebet)")
    parser.add_argument("--sport", default="basketball",
                        help="Sport slug (basketball, football, etc.)")
    parser.add_argument("--event-id", default=None,
                        help="Target event ID (numeric). If not set, uses first event from live feed.")
    parser.add_argument("--match-url", default=None,
                        help="Explicit match page URL (overrides auto-construction)")
    parser.add_argument("--live", action="store_true",
                        help="Use live path instead of prematch (line)")
    parser.add_argument("--settle", type=float, default=12.0,
                        help="SPA settle seconds (default: 12)")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: data/telemetry/betb2b/match_comparison/)")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Headless browser (default: True)")
    parser.add_argument("--hover", action="store_true", default=True,
                        help="Hover team names to trigger H2H popups")
    parser.add_argument("--verbose", "-v", action="store_true", help="DEBUG logging")
    args = parser.parse_args()

    # ── Setup ───────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    from src.sites.betb2b.cli.main import _load_skin, _build_proxy_manager_from_env
    from src.sites.betb2b.config import BetB2BSkinConfig
    from src.sites.betb2b.session import BetB2BSessionManager
    from src.sites.betb2b.extraction.match_detail import extract_match_page

    skin = _load_skin(args.skin)
    print(f"Skin: {skin.name} ({skin.domain})")
    print(f"Partner={skin.partner} gr={skin.gr} country={skin.country}")

    pm_and_id = _build_proxy_manager_from_env()
    proxy_manager = pm_and_id[0] if pm_and_id else None
    proxy_endpoint_id = pm_and_id[1] if pm_and_id else None

    # Resolve proxy endpoint
    proxy_endpoint = None
    if proxy_manager:
        if proxy_endpoint_id:
            proxy_endpoint = proxy_manager.get(proxy_endpoint_id)
        if not proxy_endpoint:
            proxy_endpoint = proxy_manager.acquire(site=skin.domain)
        print(f"Proxy: {proxy_endpoint.id if proxy_endpoint else 'DIRECT'}")
    else:
        print("Proxy: DIRECT (no BETB2B_PROXY_URL set)")

    # ── Build match URL ─────────────────────────────────────────
    if args.match_url:
        match_url = args.match_url
    elif args.event_id:
        match_url = build_match_url(
            skin.domain, args.sport, args.event_id, is_live=args.live,
        )
    else:
        # No event ID given — scrape the live feed and use the first event
        print("\nNo --event-id given. Scraping live feed to find first event...")
        from src.sites.betb2b import BetB2BScraper

        async with BetB2BScraper(
            skin,
            proxy_manager=proxy_manager,
            proxy_endpoint_id=proxy_endpoint_id,
            settle_seconds=args.settle,
            sport=args.sport,
        ) as scraper:
            result = await scraper.scrape(
                action="list_live" if args.live else "list_prematch",
                count=5,
            )
        events = result.get("events", [])
        if not events:
            print("ERROR: No events found in feed. Try with a different sport or proxy.")
            return 1

        first = events[0]
        event_id = first.get("event_id", "")
        match_url = build_match_url(skin.domain, args.sport, event_id, is_live=args.live)
        print(f"Using first event: {first.get('home')} vs {first.get('away')} (ID={event_id})")
        args.event_id = event_id

    print(f"\nMatch URL: {match_url}")

    # ── Output directory ────────────────────────────────────────
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if args.output:
        out_dir = Path(args.output)
    else:
        out_dir = Path("data/telemetry/betb2b/match_comparison") / f"{ts}_{args.skin}_{args.event_id or 'auto'}"
    out_dir.mkdir(parents=True, exist_ok=True)
    api_dir = out_dir / "api_responses"
    api_dir.mkdir(exist_ok=True)
    print(f"Output: {out_dir}")

    report = ComparisonReport(
        skin=args.skin,
        event_id=args.event_id or "",
        match_url=match_url,
        sport=args.sport,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # ── Bootstrap session + browser ─────────────────────────────
    print("\n--- Bootstrapping browser session ---")
    session_manager = BetB2BSessionManager(
        skin=skin,
        proxy=proxy_endpoint,
        settle_seconds=args.settle,
    )

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=args.headless)
        try:
            stealth = skin.stealth_profile
            context_kwargs = {
                "user_agent": stealth.get("user_agent"),
                "viewport": stealth.get("viewport", {"width": 1536, "height": 864}),
                "locale": stealth.get("locale", "en-US"),
                "timezone_id": stealth.get("timezone", "Europe/London"),
            }
            if proxy_endpoint and not proxy_endpoint.is_direct:
                pp = proxy_endpoint.to_playwright_proxy()
                if pp:
                    context_kwargs["proxy"] = pp

            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()

            # ── Navigate to match page ──────────────────────────
            print(f"\n--- Navigating to match page ---")
            try:
                await page.goto(match_url, wait_until="commit", timeout=45000)
            except Exception as exc:
                print(f"  Navigation warning: {exc}")

            print(f"  Final URL: {page.url}")
            await asyncio.sleep(args.settle)
            print(f"  Page title: {await page.title()}")

            # ── Extract UI data ─────────────────────────────────
            print(f"\n--- Extracting UI data ---")
            ui_data = await extract_match_page(page)

            # Record UI categories
            report.scoreboard = ui_data.scoreboard
            report.period_scores = ui_data.period_scores
            report.statistics = ui_data.statistics
            report.market_groups_page = ui_data.market_groups
            report.h2h_sections = ui_data.h2h_sections

            sb = ui_data.scoreboard
            report.ui_categories = {
                "scoreboard": bool(sb.get("home_team")),
                "period_scores": len(ui_data.period_scores) > 0,
                "statistics": len(ui_data.statistics) > 0,
                "market_groups": len(ui_data.market_groups) > 0,
                "h2h_sections": len(ui_data.h2h_sections) > 0,
                "venue": bool(sb.get("venue")),
            }

            print(f"  Scoreboard: {sb.get('home_team', '?')} vs {sb.get('away_team', '?')}")
            print(f"    Scores: {sb.get('home_score', '?')}-{sb.get('away_score', '?')}")
            print(f"    Competition: {sb.get('competition', '?')}")
            print(f"    Status: {sb.get('status', '?')} Minute: {sb.get('minute', '?')}")
            print(f"    Event ID: {sb.get('event_id', '?')}")

            if ui_data.period_scores:
                print(f"  Period scores ({len(ui_data.period_scores)}):")
                for ps in ui_data.period_scores[:6]:
                    print(f"    {ps.get('period_name', '?')}: {ps.get('home_score')}-{ps.get('away_score')}")
            else:
                print(f"  Period scores: NONE FOUND")

            if ui_data.statistics:
                print(f"  Statistics ({len(ui_data.statistics)} rows):")
                for s in ui_data.statistics[:5]:
                    print(f"    {s.get('label', '?')}: {s.get('home_value')} - {s.get('away_value')}")
            else:
                print(f"  Statistics: NONE FOUND")

            if ui_data.market_groups:
                print(f"  Market groups on match page ({len(ui_data.market_groups)}):")
                for mg in ui_data.market_groups[:5]:
                    print(f"    {mg.get('group_name', '?')}: {len(mg.get('selections', []))} selections")
            else:
                print(f"  Market groups: NONE FOUND")

            if ui_data.h2h_sections:
                print(f"  H2H sections ({len(ui_data.h2h_sections)}):")
                for h in ui_data.h2h_sections[:3]:
                    print(f"    [{h.get('matchCount', 0)} kw] {h.get('text', '')[:150]}")
            else:
                print(f"  H2H sections: NONE FOUND (may need hover)")

            # ── Hover team names for H2H ────────────────────────
            if args.hover and ui_data.h2h_sections:
                team_names = list({
                    sb.get("home_team", ""),
                    sb.get("away_team", ""),
                })
                team_names = [t for t in team_names if t]
                print(f"\n--- Hovering team names for H2H popups ---")
                for name in team_names:
                    try:
                        el = await page.query_selector(f':has-text("{name}")')
                        if el:
                            await el.hover(timeout=5000, force=True)
                            await asyncio.sleep(3)
                            print(f"  Hovered: {name}")
                    except Exception as exc:
                        print(f"  Hover failed for {name}: {exc}")

                # Re-extract UI data after hover
                ui_data = await extract_match_page(page)
                if ui_data.h2h_sections:
                    report.h2h_sections = ui_data.h2h_sections
                    print(f"  H2H sections after hover: {len(ui_data.h2h_sections)}")
                    for h in ui_data.h2h_sections[:3]:
                        print(f"    [{h.get('matchCount', 0)} kw] {h.get('text', '')[:150]}")

            # ── Screenshot + HTML ───────────────────────────────
            screenshot_path = out_dir / "match_screenshot.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"\nScreenshot: {screenshot_path}")

            html = await page.content()
            (out_dir / "match_page.html").write_text(html, encoding="utf-8")
            print(f"HTML saved: {len(html)}b")

        finally:
            await browser.close()

    # ── Poll API endpoints ──────────────────────────────────────
    print(f"\n--- Polling API endpoints ---")
    api_results = await poll_match_endpoints(
        skin,
        args.event_id or report.scoreboard.get("event_id", ""),
        session_manager=session_manager,
        proxy_endpoint=proxy_endpoint,
    )
    report.api_endpoints = api_results

    for r in api_results:
        status_icon = "✅" if r.get("success") and r.get("has_value") else \
                      "⚠️" if r.get("success") else "❌"
        collected = "📦" if r.get("currently_collected") else "📭"
        print(
            f"  {status_icon}{collected} {r.get('endpoint'):35s} "
            f"status={r.get('status')} "
            f"has_value={r.get('has_value')} "
            f"size={r.get('data_size')}",
            flush=True,
        )

    # ── Gap analysis ───────────────────────────────────────────
    print(f"\n--- Gap Analysis ---")
    gaps = _analyze_gaps(
        {
            "scoreboard": report.scoreboard,
            "period_scores": report.period_scores,
            "statistics": report.statistics,
            "market_groups": report.market_groups_page,
            "h2h_sections": report.h2h_sections,
        },
        api_results,
    )
    report.gaps = gaps

    # What we currently collect vs what's available
    report.currently_collected = {
        "event_basics": True,        # via Get1x2_VZip + GetGameZip
        "scores": True,              # via SC field in feed
        "markets": True,             # via GetGameZip E[]/AE[]
        "period_scores": True,       # extracted via _extract_period_scores() in rules.py (SC.PS[])
        "statistics": False,         # NOT collected (no endpoint wired)
        "h2h": False,                # NOT wired into main scraper
        "match_timeline": False,     # NOT collected
        "venue_info": False,         # NOT collected
        "detailed_stats": False,     # NOT collected
        "period_data": False,        # NOT extracted from SC or per-sport
    }

    if not gaps:
        print("  No gaps found! UI data is fully covered by API endpoints.")
    else:
        print(f"  {len(gaps)} gap(s) found:")
        for g in gaps:
            col = "✅" if g["currently_collected"] else "❌"
            print(f"  {col} [{g['category']}] {g['data_found'][:100]}")
            print(f"       API: {g['api_source']} (available={g['api_available']})")
            print(f"       Fix: {g['recommendation'][:120]}")

    # ── Write report ────────────────────────────────────────────
    report_path = out_dir / "comparison_report.json"
    report_dict = report.to_dict()
    report_path.write_text(
        json.dumps(report_dict, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nReport: {report_path}")
    print(f"\nDone! Summary:")
    print(f"  UI categories found: {sum(1 for v in report.ui_categories.values() if v)}/6")
    print(f"  API endpoints polled: {len(api_results)}")
    print(f"  API endpoints with data: {sum(1 for r in api_results if r.get('has_value'))}")
    print(f"  Gaps identified: {len(gaps)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
