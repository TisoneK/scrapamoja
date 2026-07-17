"""
Unit tests for the Linebet scraper.

These tests run without a real browser or network — they exercise the
extractor and the scraper's plumbing against synthetic JSON payloads
that mimic Linebet's API response shapes. The hybrid capture pipeline
is tested with a mocked ``NetworkInterceptor``.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sites.linebet.config import (
    API_URL_PATTERNS,
    SITE_CONFIG,
    get_linebet_config,
    validate_config,
)
from src.sites.linebet.extraction.models import (
    Event,
    EventStatus,
    LinebetScrapeResult,
    Market,
    MarketType,
    Sport,
)
from src.sites.linebet.extraction.rules import LinebetExtractionRules
from src.sites.linebet.scraper import LinebetScraper


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
class TestLinebetConfig:
    def test_site_config_has_required_fields(self) -> None:
        for field in ("id", "name", "base_url", "version", "maintainer"):
            assert SITE_CONFIG[field], f"SITE_CONFIG missing {field}"

    def test_validate_config_passes(self) -> None:
        errors = validate_config()
        assert errors == [], f"validate_config returned errors: {errors}"

    def test_api_url_patterns_are_https(self) -> None:
        for pat in API_URL_PATTERNS:
            assert pat.startswith("https://"), f"pattern {pat} is not https"

    def test_get_config_value_dot_notation(self) -> None:
        cfg = get_linebet_config()
        assert cfg["hybrid"]["max_captured_responses"] > 0
        assert (
            get_linebet_config()["features"]["prematch"] is True
        )


# ---------------------------------------------------------------------------
# Extraction rules — synthetic payloads
# ---------------------------------------------------------------------------
PREMATCH_PAYLOAD: Dict[str, Any] = {
    "Value": [
        {
            "Id": "ev-1001",
            "SportName": "Football",
            "LeagueName": "Premier League",
            "Home": "Arsenal",
            "Away": "Chelsea",
            "StartTime": 1735682400,  # 2025-01-01T00:00:00Z
            "Status": 0,
            "Odds": {"1": 1.85, "X": 3.40, "2": 4.20},
        },
        {
            "Id": "ev-1002",
            "SportName": "Basketball",
            "LeagueName": "NBA",
            "Home": "Lakers",
            "Away": "Celtics",
            "StartTime": "2025-01-01T01:00:00Z",
            "Status": 0,
            "Odds": [
                {"Name": "Moneyline", "Selections": [
                    {"Name": "Lakers", "Price": 1.95},
                    {"Name": "Celtics", "Price": 1.85},
                ]},
            ],
        },
    ],
}

LIVE_PAYLOAD: Dict[str, Any] = {
    "Value": [
        {
            "Id": "ev-2001",
            "SportName": "Football",
            "LeagueName": "La Liga",
            "Home": "Madrid",
            "Away": "Barca",
            "Status": 1,
            "ScoreHome": 1,
            "ScoreAway": 0,
            "Minute": 35,
            "Odds": {"1": 1.60, "X": 4.00, "2": 5.00},
        },
    ],
}

MARKET_DETAIL_PAYLOAD: Dict[str, Any] = {
    "Id": "ev-1001",
    "Home": "Arsenal",
    "Away": "Chelsea",
    "SportName": "Football",
    "LeagueName": "Premier League",
    "Markets": [
        {
            "Name": "Match Result 1X2",
            "Selections": [
                {"Name": "Arsenal", "Price": 1.85},
                {"Name": "Draw", "Price": 3.40},
                {"Name": "Chelsea", "Price": 4.20},
            ],
        },
        {
            "Name": "Total Over/Under 2.5",
            "Selections": [
                {"Name": "Over", "Price": 1.90, "Line": 2.5},
                {"Name": "Under", "Price": 1.90, "Line": 2.5},
            ],
        },
        {
            "Name": "Asian Handicap -1.5",
            "Selections": [
                {"Name": "Arsenal", "Price": 2.10, "Line": -1.5},
                {"Name": "Chelsea", "Price": 1.75, "Line": 1.5},
            ],
        },
    ],
}


@pytest.fixture
def rules() -> LinebetExtractionRules:
    return LinebetExtractionRules()


class TestExtractionRules:
    def test_decode_captured_response_valid_json(self, rules: LinebetExtractionRules) -> None:
        body = json.dumps(PREMATCH_PAYLOAD).encode("utf-8")
        cap = rules.decode_captured_response(
            url="https://linebet.com/bff-api/sports/list/prematch",
            status=200,
            content_type="application/json",
            raw_bytes=body,
        )
        assert cap.status == 200
        assert cap.body_bytes > 0
        assert "Value" in cap.decoded

    def test_decode_captured_response_jsonp_wrapper(self, rules: LinebetExtractionRules) -> None:
        body = b'jQuery123({"Value": []});'
        cap = rules.decode_captured_response(
            url="https://linebet.com/bff-api/sports/list",
            status=200,
            content_type="application/javascript",
            raw_bytes=body,
        )
        assert cap.decoded == {"Value": []}

    def test_decode_captured_response_garbage(self, rules: LinebetExtractionRules) -> None:
        cap = rules.decode_captured_response(
            url="https://linebet.com/bff-api/sports/list",
            status=200,
            content_type="application/json",
            raw_bytes=b"not json at all",
        )
        assert cap.decoded == {}

    def test_decode_captured_response_bodyless(self, rules: LinebetExtractionRules) -> None:
        cap = rules.decode_captured_response(
            url="https://linebet.com/bff-api/sports/list",
            status=204,
            content_type="application/json",
            raw_bytes=None,
        )
        assert cap.body_bytes == 0
        assert cap.decoded == {}

    def test_extract_prematch(self, rules: LinebetExtractionRules) -> None:
        cap = rules.decode_captured_response(
            url="https://linebet.com/bff-api/sports/list/prematch",
            status=200,
            content_type="application/json",
            raw_bytes=json.dumps(PREMATCH_PAYLOAD).encode("utf-8"),
        )
        events = rules.extract_from_captured(cap)
        assert len(events) == 2

        ev1 = next(e for e in events if e.event_id == "ev-1001")
        assert ev1.sport is Sport.FOOTBALL
        assert ev1.home == "Arsenal"
        assert ev1.away == "Chelsea"
        assert ev1.competition == "Premier League"
        assert ev1.status is EventStatus.NOT_STARTED
        assert ev1.start_time is not None
        # Flat 1X2 odds block should produce one MONEYLINE_12 market
        assert len(ev1.markets) == 1
        assert ev1.markets[0].market_type is MarketType.MONEYLINE_12
        assert len(ev1.markets[0].selections) == 3

        ev2 = next(e for e in events if e.event_id == "ev-1002")
        assert ev2.sport is Sport.BASKETBALL
        # Array-style odds should produce a MONEYLINE_H2H market
        assert len(ev2.markets) == 1
        assert ev2.markets[0].market_type is MarketType.MONEYLINE_H2H

    def test_extract_live(self, rules: LinebetExtractionRules) -> None:
        cap = rules.decode_captured_response(
            url="https://linebet.com/bff-api/sports/live/all",
            status=200,
            content_type="application/json",
            raw_bytes=json.dumps(LIVE_PAYLOAD).encode("utf-8"),
        )
        events = rules.extract_from_captured(cap)
        assert len(events) == 1
        ev = events[0]
        assert ev.is_live is True
        assert ev.status is EventStatus.LIVE
        assert ev.score_home == 1
        assert ev.score_away == 0
        assert ev.minute == 35

    def test_extract_market_detail(self, rules: LinebetExtractionRules) -> None:
        cap = rules.decode_captured_response(
            url="https://linebet.com/bff-api/bet/event/ev-1001",
            status=200,
            content_type="application/json",
            raw_bytes=json.dumps(MARKET_DETAIL_PAYLOAD).encode("utf-8"),
        )
        events = rules.extract_from_captured(cap)
        assert len(events) == 1
        ev = events[0]
        assert ev.event_id == "ev-1001"
        assert len(ev.markets) == 3
        # Market types should be classified correctly
        market_types = {m.market_type for m in ev.markets}
        assert MarketType.MONEYLINE_12 in market_types
        assert MarketType.TOTALS in market_types
        assert MarketType.HANDICAP in market_types
        # Handicap selections should carry their lines
        handicap = next(m for m in ev.markets if m.market_type is MarketType.HANDICAP)
        lines = [s.line for s in handicap.selections]
        assert -1.5 in lines and 1.5 in lines

    def test_extract_config_endpoint_returns_empty(self, rules: LinebetExtractionRules) -> None:
        """Real captured /bff-api/config/group/get response — has no events."""
        cap = rules.decode_captured_response(
            url="https://linebet.com/bff-api/config/group/get?groups=d.technical,d.global&lang=en&d=linebet.com&g=HK&p=650",
            status=200,
            content_type="application/json",
            raw_bytes=b'{"1433": "errors_page_custom_block_mobile", "1432": "header_logo_light"}',
        )
        assert rules.extract_from_captured(cap) == []

    def test_extract_analytics_endpoint_returns_empty(self, rules: LinebetExtractionRules) -> None:
        """Real captured /analytics-module-api/ response — has no events."""
        cap = rules.decode_captured_response(
            url="https://linebet.com/analytics-module-api/v1/analytics?projectId=650&domain=linebet.com",
            status=200,
            content_type="application/json",
            raw_bytes=b'{"counters": [{"type": 8, "code": "22934032"}], "settings": {"isDeferredLoadingEnabled": true}}',
        )
        assert rules.extract_from_captured(cap) == []

    def test_extract_fatman_api_returns_empty(self, rules: LinebetExtractionRules) -> None:
        """Real captured /fatman-api/ response — analytics, no events."""
        cap = rules.decode_captured_response(
            url="https://linebet.com/fatman-api/a6f69e4388362d761ee5bb073edb23ae3d9341fb/ab.json",
            status=200,
            content_type="application/json",
            raw_bytes=b"[]",
        )
        assert rules.extract_from_captured(cap) == []

    def test_extract_malformed_payload_does_not_raise(self, rules: LinebetExtractionRules) -> None:
        cap = rules.decode_captured_response(
            url="https://linebet.com/bff-api/sports/list/prematch",
            status=200,
            content_type="application/json",
            raw_bytes=b'{"Value": "not a list of events"}',
        )
        # Should return [] without raising
        assert rules.extract_from_captured(cap) == []

    def test_sport_aliases(self, rules: LinebetExtractionRules) -> None:
        payload = {"Value": [
            {"Id": "x1", "SportName": "Soccer", "Home": "A", "Away": "B"},
            {"Id": "x2", "SportName": "e-sports", "Home": "C", "Away": "D"},
            {"Id": "x3", "SportName": "Unknown Sport", "Home": "E", "Away": "F"},
        ]}
        cap = rules.decode_captured_response(
            url="https://linebet.com/bff-api/sports/list",
            status=200,
            content_type="application/json",
            raw_bytes=json.dumps(payload).encode("utf-8"),
        )
        events = rules.extract_from_captured(cap)
        sports = {e.event_id: e.sport for e in events}
        assert sports["x1"] is Sport.FOOTBALL
        assert sports["x2"] is Sport.ESPORTS
        assert sports["x3"] is Sport.OTHER


# ---------------------------------------------------------------------------
# Scraper plumbing — NetworkInterceptor is mocked
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_page() -> MagicMock:
    page = MagicMock()
    page.url = "about:blank"
    # attach() probes document.readyState via page.evaluate()
    page.evaluate = AsyncMock(return_value="loading")
    page.goto = AsyncMock(return_value=None)
    page.locator = MagicMock()
    page.locator.return_value.first.count = AsyncMock(return_value=0)
    page.evaluate = AsyncMock(return_value="loading")
    return page


@pytest.fixture
def mock_selector_engine() -> MagicMock:
    engine = MagicMock()
    engine.register_selector = MagicMock()
    engine.list_selectors = MagicMock(return_value=[])
    return engine


@pytest.fixture
def scraper(mock_page: MagicMock, mock_selector_engine: MagicMock) -> LinebetScraper:
    # BaseSiteScraper.__init__ calls asyncio.create_task() to kick off
    # modular-component init, so we need a running event loop when the
    # scraper is constructed. Run the construction inside a fresh loop.
    async def _build() -> LinebetScraper:
        s = LinebetScraper(mock_page, mock_selector_engine)
        # Skip the heavy initialize() path; set the bare-minimum state.
        s.flow = MagicMock()
        s.flow.navigate_to_home = AsyncMock(return_value=True)
        s.flow.navigate_to_live = AsyncMock(return_value=True)
        s.flow.scroll_fixtures = AsyncMock(return_value=None)
        s.flow.dismiss_consent_if_present = AsyncMock(return_value=None)
        s.flow.wait_for_api_burst = AsyncMock(return_value=True)
        return s

    return asyncio.run(_build())


class _StubInterceptor:
    """Minimal stand-in for NetworkInterceptor that yields pre-baked captures."""

    def __init__(self, captures: List[Any]) -> None:
        self._captures = captures
        self.attached = False

    async def attach(self, page: Any) -> None:
        self.attached = True

    async def detach(self) -> None:
        self.attached = False


class TestScraperPlumbing:
    def test_validate_scrape_params_unknown_action(self, scraper: LinebetScraper) -> None:
        async def run() -> bool:
            return await scraper._validate_scrape_params(action="bogus")
        assert asyncio.run(run()) is False

    def test_validate_scrape_params_known_action(self, scraper: LinebetScraper) -> None:
        async def run() -> bool:
            return await scraper._validate_scrape_params(action="list_prematch")
        assert asyncio.run(run()) is True

    def test_dedupe_events_merges_markets(self) -> None:
        ev_a = Event(
            event_id="dup-1", sport=Sport.FOOTBALL, competition="L1",
            home="A", away="B",
            markets=[Market(name="M1", market_type=MarketType.MONEYLINE_12)],
        )
        ev_b = Event(
            event_id="dup-1", sport=Sport.FOOTBALL, competition="L1",
            home="A", away="B",
            markets=[
                Market(name="M1", market_type=MarketType.MONEYLINE_12),
                Market(name="M2", market_type=MarketType.TOTALS),
            ],
        )
        merged = LinebetScraper._dedupe_events([ev_a, ev_b])
        assert len(merged) == 1
        assert len(merged[0].markets) == 2  # richer copy wins

    def test_scrape_raw_capture_returns_captured_only(
        self, scraper: LinebetScraper, mock_page: MagicMock,
    ) -> None:
        from src.network.interception.models import CapturedResponse
        cap = CapturedResponse(
            url="https://linebet.com/bff-api/sports/list/prematch",
            status=200,
            headers={"content-type": "application/json"},
            raw_bytes=json.dumps(PREMATCH_PAYLOAD).encode("utf-8"),
        )

        # Bypass the real NetworkInterceptor with our stub.
        scraper.page.url = "https://linebet.com/en"
        with patch(
            "src.sites.linebet.scraper.NetworkInterceptor",
            return_value=_StubInterceptor(captures=[cap]),
        ):
            # Pre-seed the capture buffer so _run_capture_pipeline has something to harvest.
            scraper._captured_raw = [cap]

            async def fake_pipeline(*args, **kwargs):
                # Mirror the real method's contract: returns List[CapturedResponse]
                return [cap]
            scraper._run_capture_pipeline = fake_pipeline  # type: ignore[assignment]

            async def run() -> Dict[str, Any]:
                return await scraper._execute_scrape_logic(action="raw_capture")
            result_dict = asyncio.run(run())

        assert result_dict["error"] is None
        assert result_dict["action"] == "raw_capture"
        assert result_dict["captured_response_count"] == 1
        # raw_capture must NOT run the extractor
        assert result_dict["event_count"] == 0

    def test_scrape_list_prematch_runs_extractor(
        self, scraper: LinebetScraper,
    ) -> None:
        from src.network.interception.models import CapturedResponse
        cap = CapturedResponse(
            url="https://linebet.com/bff-api/sports/list/prematch",
            status=200,
            headers={"content-type": "application/json"},
            raw_bytes=json.dumps(PREMATCH_PAYLOAD).encode("utf-8"),
        )

        scraper.page.url = "https://linebet.com/en"
        scraper._captured_raw = [cap]

        async def fake_pipeline(*args, **kwargs):
            return [cap]
        scraper._run_capture_pipeline = fake_pipeline  # type: ignore[assignment]

        async def run() -> Dict[str, Any]:
            return await scraper._execute_scrape_logic(action="list_prematch")
        result_dict = asyncio.run(run())

        assert result_dict["error"] is None
        assert result_dict["event_count"] == 2
        assert result_dict["action"] == "list_prematch"
        assert result_dict["captured_response_count"] == 1

    def test_result_to_dict_shape(self) -> None:
        result = LinebetScrapeResult(action="list_prematch", url="https://linebet.com/en")
        d = result.to_dict()
        assert d["action"] == "list_prematch"
        assert d["success"] is True
        assert d["event_count"] == 0
        assert d["captured_response_count"] == 0
        assert "extracted_at" in d
