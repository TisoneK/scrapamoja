"""Unit tests for DOM-event GetGameZip market enrichment.

Covers the Session 25 fix: ``_enrich_dom_events_with_odds`` skipped every
DOM event because the DOM extractor attaches a shallow 1-market stub and the
guard was ``if e.markets`` (truthy). The correct guard is "already has a deep
tree" (``len(e.markets) > 1``), so a 0- or 1-market stub gets enriched with
the full ``GetGameZip`` market tree.

Runs without a browser or network — the ``GetGameZip`` response is a real
capture saved under ``fixtures/getgamezip_basketball.json`` (linebet,
Botafogo U22 v Unifacisa U22), and the feed client is faked.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest

from src.sites.betb2b.config import DEFAULT_SKIN_CONFIG, BetB2BSkinConfig
from src.sites.betb2b.extraction.models import (
    CapturedFeedResponse,
    Event,
    EventStatus,
    Market,
    MarketType,
    Selection,
    Sport,
)
from src.sites.betb2b.extraction.rules import BetB2BExtractionRules
from src.sites.betb2b.scraper import BetB2BScraper

_FIXTURE = Path(__file__).parent / "fixtures" / "getgamezip_basketball.json"


@pytest.fixture
def skin() -> BetB2BSkinConfig:
    return DEFAULT_SKIN_CONFIG


@pytest.fixture
def getgamezip_payload() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def getgamezip_capture(getgamezip_payload: dict) -> CapturedFeedResponse:
    return CapturedFeedResponse(
        url="https://linebet.com/service-api/LineFeed/GetGameZip?id=352940650",
        status=200,
        content_type="application/json",
        body_bytes=len(json.dumps(getgamezip_payload)),
        decoded=getgamezip_payload,
    )


def _dom_stub(event_id: str, *, is_live: bool = False, markets: int = 1) -> Event:
    """A DOM-extracted event stub — teams + at most the shallow main market."""
    mkts: List[Market] = []
    for i in range(markets):
        mkts.append(
            Market(
                name="To Win Match" if i == 0 else f"m{i}",
                market_type=MarketType.OTHER,
                selections=[
                    Selection(name="1", price=1.5),
                    Selection(name="2", price=2.5),
                ],
                is_live=is_live,
            )
        )
    return Event(
        event_id=event_id,
        sport=Sport.BASKETBALL,
        competition="Test League",
        home="Home",
        away="Away",
        status=EventStatus.LIVE if is_live else EventStatus.NOT_STARTED,
        is_live=is_live,
        markets=mkts,
        raw_endpoint="dom",
    )


class _FakeFeedClient:
    """Stand-in for BetB2BFeedClient that returns a canned GetGameZip."""

    def __init__(self, capture: CapturedFeedResponse) -> None:
        self._capture = capture
        self.calls: List[tuple[str, str]] = []

    async def fetch_game(self, event_id: str, *, root: str = "line") -> CapturedFeedResponse:
        self.calls.append((event_id, root))
        return self._capture


def _make_scraper(skin: BetB2BSkinConfig, fake_client: _FakeFeedClient) -> BetB2BScraper:
    scraper = BetB2BScraper(skin, proxy_manager=None, telemetry_enabled=False)
    scraper.feed_client = fake_client  # type: ignore[assignment]
    return scraper


# ---------------------------------------------------------------------------
# 1. The real GetGameZip capture parses to a deep market tree.
# ---------------------------------------------------------------------------
def test_getgamezip_yields_deep_market_tree(skin, getgamezip_capture):
    rules = BetB2BExtractionRules(skin)
    events = rules.extract_from_captured(getgamezip_capture)

    assert len(events) == 1
    ev = events[0]
    assert ev.home and ev.away
    # A basketball prematch game returns many markets (handicaps, totals, …).
    assert len(ev.markets) >= 5
    assert sum(len(m.selections) for m in ev.markets) >= 10


# ---------------------------------------------------------------------------
# 2. A 1-market DOM stub gets enriched (the Session 24 regression).
# ---------------------------------------------------------------------------
async def test_one_market_stub_is_enriched(skin, getgamezip_capture):
    fake = _FakeFeedClient(getgamezip_capture)
    scraper = _make_scraper(skin, fake)

    stub = _dom_stub("352940650", markets=1)
    assert len(stub.markets) == 1  # the shallow grid stub

    out = await scraper._enrich_dom_events_with_odds([stub])

    assert len(fake.calls) == 1  # GetGameZip WAS fetched (the fix)
    assert fake.calls[0] == ("352940650", "line")
    assert len(out) == 1
    assert len(out[0].markets) >= 5  # replaced with the full tree


# ---------------------------------------------------------------------------
# 3. A 0-market DOM stub is also enriched.
# ---------------------------------------------------------------------------
async def test_zero_market_stub_is_enriched(skin, getgamezip_capture):
    fake = _FakeFeedClient(getgamezip_capture)
    scraper = _make_scraper(skin, fake)

    out = await scraper._enrich_dom_events_with_odds([_dom_stub("352940650", markets=0)])

    assert len(fake.calls) == 1
    assert len(out[0].markets) >= 5


# ---------------------------------------------------------------------------
# 4. An already-deep event is NOT re-fetched (guard preserved).
# ---------------------------------------------------------------------------
async def test_deep_event_not_refetched(skin, getgamezip_capture):
    fake = _FakeFeedClient(getgamezip_capture)
    scraper = _make_scraper(skin, fake)

    deep = _dom_stub("352940650", markets=3)
    out = await scraper._enrich_dom_events_with_odds([deep])

    assert fake.calls == []  # no GetGameZip fetch
    assert out[0] is deep


# ---------------------------------------------------------------------------
# 5. A non-numeric event id is skipped (can't call GetGameZip?id=).
# ---------------------------------------------------------------------------
async def test_non_numeric_id_skipped(skin, getgamezip_capture):
    fake = _FakeFeedClient(getgamezip_capture)
    scraper = _make_scraper(skin, fake)

    stub = _dom_stub("dom-Home-Away", markets=1)
    out = await scraper._enrich_dom_events_with_odds([stub])

    assert fake.calls == []
    assert out[0] is stub


# ---------------------------------------------------------------------------
# 6. The max_odds_fetch budget caps the number of fetches.
# ---------------------------------------------------------------------------
async def test_fetch_budget_is_capped(skin, getgamezip_capture, monkeypatch):
    fake = _FakeFeedClient(getgamezip_capture)
    scraper = _make_scraper(skin, fake)
    monkeypatch.setattr(scraper.skin, "max_odds_fetch", 2, raising=False)

    stubs = [_dom_stub(str(352940650 + i), markets=1) for i in range(5)]
    out = await scraper._enrich_dom_events_with_odds(stubs)

    assert len(fake.calls) == 2  # capped
    assert len(out) == 5  # all events preserved (enriched or original)
