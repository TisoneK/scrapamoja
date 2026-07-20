"""Unit tests for the BetB2B family extractor.

Run with::

    pytest src/sites/betb2b/tests/ -v

Tests run without a browser or network — they exercise the extractor
against synthetic 1xbet-terse-key payloads that mimic the real feed
shapes (sample is in `src/sites/linebet/snapshots/normalized/
livefeed_get1x2_schema.md`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.sites.betb2b.config import BetB2BSkinConfig, DEFAULT_SKIN_CONFIG
from src.sites.betb2b.extraction.models import (
    EventStatus,
    H2HData,
    H2HGameShort,
    MarketType,
    PeriodScore,
    Sport,
)
from src.sites.betb2b.extraction.rules import BetB2BExtractionRules


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def skin() -> BetB2BSkinConfig:
    # Use the default linebet skin — every test benefits from its lookup tables.
    return DEFAULT_SKIN_CONFIG


@pytest.fixture
def rules(skin: BetB2BSkinConfig) -> BetB2BExtractionRules:
    return BetB2BExtractionRules(skin)


# A trimmed live event mimicking the captured Get1x2_VZip shape.
SAMPLE_LIVE_EVENT = {
    "I": 737248980,
    "ZP": 737248980,
    "O1": "Minnesota Timberwolves",
    "O2": "Los Angeles Clippers",
    "O1E": "Minnesota Timberwolves",
    "O2E": "Los Angeles Clippers",
    "O1I": 6882,
    "O2I": 6892,
    "SN": "Basketball",
    "SI": 3,
    "L": "NBA. Summer League",
    "LI": 75093,
    "CN": "United States",
    "S": 1784342700,
    "SC": {
        "FS": {"S1": 118, "S2": 126},
        "PS": [],
        "CP": 5,
        "CPS": "1 Overtime",
        "TS": 68,
        "SLS": "2 min remaining",
    },
    "E": [
        {"T": 402, "C": 1.025, "CV": "1.025", "B": True, "G": 101},
        {"T": 7, "P": 7.5, "C": 1.825, "CV": "1.825", "B": True, "G": 2},
        {"T": 8, "P": -7.5, "C": 1.98, "CV": "1.98", "B": True, "G": 2},
        {"T": 401, "C": 12.5, "CV": "12.5", "B": True, "G": 101},
    ],
    "AE": [
        {
            "G": 2,
            "ME": [
                {"T": 8, "P": -7.5, "C": 1.98, "CV": "1.98", "B": True, "G": 2, "CE": 1},
                {"T": 7, "P": 7.5, "C": 1.825, "CV": "1.825", "B": True, "G": 2, "CE": 1},
            ],
        }
    ],
}

SAMPLE_LIVE_FEED = {
    "Success": True,
    "Error": "",
    "Value": [SAMPLE_LIVE_EVENT],
}


# ---------------------------------------------------------------------------
# Decode tests
# ---------------------------------------------------------------------------
def test_decode_valid_json(rules: BetB2BExtractionRules) -> None:
    body = json.dumps(SAMPLE_LIVE_FEED).encode("utf-8")
    cap = rules.decode_response(
        url="https://linebet.com/service-api/LiveFeed/Get1x2_VZip",
        status=200,
        content_type="application/json",
        raw_bytes=body,
    )
    assert cap.status == 200
    assert cap.body_bytes == len(body)
    assert cap.decoded.get("Success") is True
    assert isinstance(cap.decoded.get("Value"), list)


def test_decode_empty_body(rules: BetB2BExtractionRules) -> None:
    cap = rules.decode_response(
        url="https://example.com",
        status=204,
        content_type="",
        raw_bytes=None,
    )
    assert cap.body_bytes == 0
    assert cap.decoded == {}


def test_decode_invalid_json(rules: BetB2BExtractionRules) -> None:
    cap = rules.decode_response(
        url="https://example.com",
        status=200,
        content_type="text/html",
        raw_bytes=b"<html>not json</html>",
    )
    assert cap.decoded == {}


# ---------------------------------------------------------------------------
# Extraction tests
# ---------------------------------------------------------------------------
def test_extract_from_live_feed(rules: BetB2BExtractionRules) -> None:
    body = json.dumps(SAMPLE_LIVE_FEED).encode("utf-8")
    cap = rules.decode_response(
        url="https://linebet.com/service-api/LiveFeed/Get1x2_VZip",
        status=200,
        content_type="application/json",
        raw_bytes=body,
    )
    events = rules.extract_from_captured(cap)
    assert len(events) == 1

    ev = events[0]
    assert ev.event_id == "737248980"
    assert ev.home == "Minnesota Timberwolves"
    assert ev.away == "Los Angeles Clippers"
    assert ev.sport == Sport.BASKETBALL
    assert ev.competition == "NBA. Summer League"
    assert ev.country == "United States"
    assert ev.is_live is True
    assert ev.status == EventStatus.LIVE
    assert ev.score_home == 118
    assert ev.score_away == 126
    assert ev.period == "1 Overtime"
    assert ev.time_remaining == "2 min remaining"
    assert ev.sport_id == 3
    assert ev.league_id == 75093


def test_extract_handles_success_false(rules: BetB2BExtractionRules) -> None:
    """If the feed returns Success=false, extractor returns no events."""
    cap = rules.decode_response(
        url="https://example.com/feed",
        status=200,
        content_type="application/json",
        raw_bytes=json.dumps({"Success": False, "Error": "boom", "Value": None}).encode(),
    )
    assert rules.extract_from_captured(cap) == []


def test_extract_handles_empty_value(rules: BetB2BExtractionRules) -> None:
    cap = rules.decode_response(
        url="https://example.com/feed",
        status=200,
        content_type="application/json",
        raw_bytes=json.dumps({"Success": True, "Value": []}).encode(),
    )
    assert rules.extract_from_captured(cap) == []


def test_extract_market_groups_from_ae(rules: BetB2BExtractionRules) -> None:
    """The AE layout (grouped markets) should produce at least one market."""
    body = json.dumps(SAMPLE_LIVE_FEED).encode("utf-8")
    cap = rules.decode_response(
        url="https://linebet.com/service-api/LiveFeed/Get1x2_VZip",
        status=200,
        content_type="application/json",
        raw_bytes=body,
    )
    events = rules.extract_from_captured(cap)
    assert events
    ev = events[0]
    # AE layout has group 2 (handicap) with 2 selections.
    markets_g2 = [m for m in ev.markets if m.raw_g == 2]
    assert markets_g2
    m = markets_g2[0]
    assert m.market_type == MarketType.HANDICAP
    assert len(m.selections) == 2
    # Both selections carry a line (the P field).
    assert all(s.line is not None for s in m.selections)
    # Both are blocked (B=True) → market should be suspended.
    assert m.is_suspended is True


def test_extract_market_groups_from_e_when_no_ae(rules: BetB2BExtractionRules) -> None:
    """When AE is absent, E (flat) should still produce markets grouped by G."""
    event = dict(SAMPLE_LIVE_EVENT)
    event.pop("AE", None)  # remove the richer layout
    feed = {"Success": True, "Value": [event]}
    cap = rules.decode_response(
        url="https://linebet.com/service-api/LiveFeed/Get1x2_VZip",
        status=200,
        content_type="application/json",
        raw_bytes=json.dumps(feed).encode(),
    )
    events = rules.extract_from_captured(cap)
    assert events
    ev = events[0]
    # E has selections in groups 101 and 2.
    groups = {m.raw_g for m in ev.markets}
    assert 101 in groups
    assert 2 in groups


def test_extract_skips_non_event_dicts(rules: BetB2BExtractionRules) -> None:
    """The _flatten_value walker must not mistake non-event dicts for events."""
    payload = {
        "Success": True,
        "Value": [
            {"I": 1, "O1": "A", "O2": "B", "SN": "Football", "SI": 1},
            {"Random": "metadata", "NotAnEvent": True},
        ],
    }
    cap = rules.decode_response(
        url="https://example.com/feed",
        status=200,
        content_type="application/json",
        raw_bytes=json.dumps(payload).encode(),
    )
    events = rules.extract_from_captured(cap)
    assert len(events) == 1
    assert events[0].home == "A"


def test_extract_prematch_uses_more_markets(rules: BetB2BExtractionRules) -> None:
    """Prematch events typically carry ~20 markets — extractor should handle that."""
    selections_e = []
    # Build a prematch-style event with 3 markets (1x2, totals, double chance).
    # 1x2 group 1: T=1 (W1), T=2 (X), T=3 (W2)
    selections_e.append({"T": 1, "C": 1.85, "G": 1})
    selections_e.append({"T": 2, "C": 3.40, "G": 1})
    selections_e.append({"T": 3, "C": 4.20, "G": 1})
    # Totals group 3: T=9 (Over), T=10 (Under) with P=2.5
    selections_e.append({"T": 9, "C": 1.95, "P": 2.5, "G": 3})
    selections_e.append({"T": 10, "C": 1.95, "P": 2.5, "G": 3})
    # Double chance group 6: T=13 (1X), T=14 (12), T=15 (X2)
    selections_e.append({"T": 13, "C": 1.20, "G": 6})
    selections_e.append({"T": 14, "C": 1.30, "G": 6})
    selections_e.append({"T": 15, "C": 1.50, "G": 6})

    event = {
        "I": 999,
        "O1": "Arsenal",
        "O2": "Chelsea",
        "SN": "Football",
        "SI": 1,
        "L": "Premier League",
        "LI": 1,
        "S": 1784342700,
        "E": selections_e,
        # No SC block → prematch.
    }
    feed = {"Success": True, "Value": [event]}
    cap = rules.decode_response(
        url="https://linebet.com/service-api/LineFeed/Get1x2_VZip",
        status=200,
        content_type="application/json",
        raw_bytes=json.dumps(feed).encode(),
    )
    events = rules.extract_from_captured(cap)
    assert len(events) == 1
    ev = events[0]
    assert ev.is_live is False
    assert ev.status == EventStatus.NOT_STARTED
    assert ev.score_home is None
    assert ev.score_away is None

    # 3 markets — one per group present in E.
    groups = {m.raw_g for m in ev.markets}
    assert groups == {1, 3, 6}

    # Find the 1x2 market and verify selections.
    m_1x2 = next(m for m in ev.markets if m.raw_g == 1)
    assert m_1x2.market_type == MarketType.MONEYLINE_12
    labels = {s.name for s in m_1x2.selections}
    assert "1" in labels and "X" in labels and "2" in labels

    # Find the totals market and verify the line is rendered in the label.
    m_totals = next(m for m in ev.markets if m.raw_g == 3)
    assert m_totals.market_type == MarketType.TOTALS
    over_sel = next(s for s in m_totals.selections if "Over" in s.name)
    assert over_sel.line == 2.5
    assert "2.5" in over_sel.name


def test_extract_with_unknown_market_ids(rules: BetB2BExtractionRules) -> None:
    """Unknown T/G ids should degrade gracefully (no exception, market emitted)."""
    event = {
        "I": 1, "O1": "A", "O2": "B", "SN": "Football", "SI": 1,
        "E": [{"T": 9999, "C": 2.0, "G": 999, "P": 3.3}],
    }
    feed = {"Success": True, "Value": [event]}
    cap = rules.decode_response(
        url="https://example.com/feed",
        status=200,
        content_type="application/json",
        raw_bytes=json.dumps(feed).encode(),
    )
    events = rules.extract_from_captured(cap)
    assert events
    ev = events[0]
    assert len(ev.markets) == 1
    m = ev.markets[0]
    # Unknown group → OTHER market type, name falls back to "G=999".
    assert m.market_type == MarketType.OTHER
    assert "999" in m.name
    # Selection label falls back to "T=9999" but still includes the line.
    assert m.selections
    assert "9999" in m.selections[0].name


# ---------------------------------------------------------------------------
# Skin config tests
# ---------------------------------------------------------------------------
def test_skin_config_from_yaml(tmp_path: Path) -> None:
    """A minimal skin YAML loads with defaults filled in."""
    yaml_text = """
name: testskin
domain: example.com
partner: 100
gr: 200
country: 87
geo: KE
"""
    p = tmp_path / "testskin.yaml"
    p.write_text(yaml_text)
    skin = BetB2BSkinConfig.from_yaml(p)
    assert skin.name == "testskin"
    assert skin.domain == "example.com"
    assert skin.base_url == "https://example.com"
    assert skin.partner == 100
    assert skin.gr == 200
    # Defaults preserved.
    assert skin.feed_paths["events_top"] == "/Get1x2_VZip"
    assert "is-srv" in skin.base_headers
    # Query params should be auto-populated from identity fields.
    assert skin.feed_query_params["partner"] == "100"
    assert skin.feed_query_params["gr"] == "200"
    assert skin.feed_query_params["country"] == "87"
    assert skin.feed_query_params["lng"] == "en"


def test_skin_config_unknown_key_rejected(tmp_path: Path) -> None:
    yaml_text = """
name: badskin
domain: example.com
nonexistent_field: oops
"""
    p = tmp_path / "badskin.yaml"
    p.write_text(yaml_text)
    with pytest.raises(ValueError, match="Unknown skin config keys"):
        BetB2BSkinConfig.from_yaml(p)


def test_skin_config_feed_url_renders(skin: BetB2BSkinConfig) -> None:
    url = skin.feed_url("events_top", root="live")
    assert url.startswith("https://linebet.com/service-api/LiveFeed/Get1x2_VZip?")
    # Auto-populated params should be present.
    assert "partner=189" in url
    assert "gr=650" in url
    assert "country=87" in url
    assert "lng=en" in url


def test_skin_config_feed_url_line_root(skin: BetB2BSkinConfig) -> None:
    url = skin.feed_url("events_top", root="line")
    assert "/service-api/LineFeed/Get1x2_VZip?" in url


def test_skin_config_feed_url_extra_params(skin: BetB2BSkinConfig) -> None:
    url = skin.feed_url("events_top", root="live", extra_params={"sports": "3"})
    assert "sports=3" in url
    # Original params still there.
    assert "partner=189" in url


def test_skin_config_validate(skin: BetB2BSkinConfig) -> None:
    assert skin.validate() == []

    bad = skin.with_overrides(domain="")
    errors = bad.validate()
    assert any("domain" in e for e in errors)


def test_skin_config_merged_headers_with_cookies(skin: BetB2BSkinConfig) -> None:
    h = skin.merged_headers(session_cookies="sess=abc; lng=en")
    assert h["cookie"] == "sess=abc; lng=en"
    assert h["is-srv"] == "false"
    assert h["x-app-n"] == "__BETTING_APP__"


def test_skin_config_with_overrides(skin: BetB2BSkinConfig) -> None:
    """with_overrides returns a new skin with the given fields changed."""
    other = skin.with_overrides(name="other", partner=999)
    assert other.name == "other"
    assert other.partner == 999
    # Original untouched.
    assert skin.name == "linebet"
    assert skin.partner == 189


# ---------------------------------------------------------------------------
# Market/sport lookup tests
# ---------------------------------------------------------------------------
def test_lookup_market_known(skin: BetB2BSkinConfig) -> None:
    from src.sites.betb2b.markets import lookup_market

    name, label = lookup_market(
        g_id=1, t_id=1,
        market_groups=skin.market_groups,
        market_types=skin.market_types,
    )
    assert name == "Match Result 1x2"
    assert label == "1"


def test_lookup_market_unknown(skin: BetB2BSkinConfig) -> None:
    from src.sites.betb2b.markets import lookup_market

    name, label = lookup_market(
        g_id=999, t_id=9999,
        market_groups=skin.market_groups,
        market_types=skin.market_types,
    )
    # Falls back to the group label, then to a raw G/T label.
    assert name is None or "999" in (name or "")
    assert "9999" in label


def test_lookup_sport_known(skin: BetB2BSkinConfig) -> None:
    from src.sites.betb2b.sport_ids import lookup_sport

    assert lookup_sport(3, skin.sport_map) == "Basketball"
    assert lookup_sport(1, skin.sport_map) == "Football"
    assert lookup_sport(999, skin.sport_map) is None


# ---------------------------------------------------------------------------
# Scraper plumbing tests (no network)
# ---------------------------------------------------------------------------
def test_scraper_dedupe_merges_markets() -> None:
    from src.sites.betb2b.extraction.models import Event, Market, MarketType, Selection
    from src.sites.betb2b.scraper import BetB2BScraper

    ev1 = Event(
        event_id="1", sport=Sport.FOOTBALL, competition="L",
        home="A", away="B", is_live=False,
        markets=[Market(name="M1", market_type=MarketType.MONEYLINE_12,
                        selections=[Selection(name="1", price=1.5)])],
    )
    ev2 = Event(
        event_id="1", sport=Sport.FOOTBALL, competition="L",
        home="A", away="B", is_live=True,
        markets=[
            Market(name="M1", market_type=MarketType.MONEYLINE_12,
                   selections=[Selection(name="1", price=1.5)]),
            Market(name="M2", market_type=MarketType.TOTALS,
                   selections=[Selection(name="Over", price=2.0, line=2.5)]),
        ],
    )
    out = BetB2BScraper._dedupe_events([ev1, ev2])
    assert len(out) == 1
    # Richer market list wins.
    assert len(out[0].markets) == 2
    # Live version preferred.
    assert out[0].is_live is True


def test_scraper_get_info(skin: BetB2BSkinConfig) -> None:
    from src.sites.betb2b.scraper import BetB2BScraper

    s = BetB2BScraper(skin)
    info = s.get_info()
    assert info["skin"]["name"] == "linebet"
    # extraction_mode now carries the ADR-4 annotation — just check the prefix.
    assert info["extraction_mode"].startswith("hybrid")
    assert "list_live" in info["actions"]
    # New: sport context is always present (defaults to AllSportsScraper).
    assert "sport" in info
    assert "sport_context" in info
    assert info["sport"]["slug"] == "" or info["sport"]["slug"] == "all"
    assert info["sport_context"]["bootstrap_path"] == "/en/line"


def test_scraper_get_info_with_sport(skin: BetB2BSkinConfig) -> None:
    """Per-sport scraper framework: passing sport=basketball customizes context."""
    from src.sites.betb2b.scraper import BetB2BScraper

    s = BetB2BScraper(skin, sport="basketball")
    info = s.get_info()
    assert info["sport"]["slug"] == "basketball"
    assert info["sport"]["sport_id"] == 3
    assert info["sport_context"]["bootstrap_path"] == "/en/line/basketball"
    assert info["sport_context"]["live_bootstrap_path"] == "/en/live/basketball"
    assert info["sport_context"]["sport_enum"] == "Basketball"
    # DOM selectors are populated.
    assert info["sport_context"]["dom_selectors"]["championship"] == ".dashboard-champ"


def test_sport_registry_resolves_all_sports() -> None:
    """The sports registry resolves every shipped sport slug + SI id."""
    from src.sites.betb2b.sports import (
        get_sport_scraper, list_sport_slugs, resolve_sport,
    )

    slugs = list_sport_slugs()
    assert "basketball" in slugs
    assert "football" in slugs
    assert "tennis" in slugs
    assert "ice-hockey" in slugs
    assert "esports" in slugs
    assert "all" in slugs

    # By slug.
    assert get_sport_scraper(slug="basketball").sport_id == 3
    # By SI id.
    assert get_sport_scraper(sport_id=3).slug == "basketball"
    # By Sport enum.
    from src.sites.betb2b.extraction.models import Sport
    assert get_sport_scraper(sport_enum=Sport.BASKETBALL).slug == "basketball"
    # resolve_sport helper.
    assert resolve_sport(None).slug in ("", "all")
    assert resolve_sport("basketball").sport_id == 3
    assert resolve_sport(3).slug == "basketball"
    assert resolve_sport(Sport.FOOTBALL).slug == "football"


def test_basketball_market_overrides() -> None:
    """Basketball overrides G=1 to 'To Win Match' (2-way H2H, no draw)."""
    from src.sites.betb2b.sports import get_sport_scraper

    b = get_sport_scraper(slug="basketball")
    overrides = b.market_group_overrides_dict
    assert overrides[1].name == "To Win Match"
    assert b.has_draw is False
    assert b.period_name == "quarter"
    assert b.periods_count == 4
    # Enrichment: "1st quarter" → minute=1.
    from src.sites.betb2b.extraction.models import Event, EventStatus, Sport
    e = Event(
        event_id="x", sport=Sport.BASKETBALL, competition="",
        home="A", away="B", period="2nd quarter", status=EventStatus.LIVE,
    )
    b.enrich_event(e)
    assert e.minute == 2


def test_extract_period_scores_from_sc(rules: BetB2BExtractionRules) -> None:
    """``SC.PS[]`` should be extracted into ``Event.period_scores``."""
    event = dict(SAMPLE_LIVE_EVENT)
    # Give it real period scores.
    event["SC"] = {
        "FS": {"S1": 118, "S2": 126},
        "PS": [
            {"Key": 1, "Value": {"S1": 19, "S2": 20, "NF": "1st quarter"}},
            {"Key": 2, "Value": {"S1": 21, "S2": 38, "NF": "2nd quarter"}},
            {"Key": 3, "Value": {"S1": 33, "S2": 34, "NF": "3rd quarter"}},
            {"Key": 4, "Value": {"S1": 42, "S2": 23, "NF": "4th quarter"}},
        ],
        "CP": 4,
        "CPS": "4th quarter",
        "TS": 1800,
        "SLS": "2 min remaining",
    }
    feed = {"Success": True, "Value": [event]}
    cap = rules.decode_response(
        url="https://linebet.com/service-api/LiveFeed/Get1x2_VZip",
        status=200,
        content_type="application/json",
        raw_bytes=json.dumps(feed).encode(),
    )
    events = rules.extract_from_captured(cap)
    assert len(events) == 1
    ev = events[0]
    assert len(ev.period_scores) == 4
    # Verify each period.
    assert ev.period_scores[0].period_name == "1st quarter"
    assert ev.period_scores[0].home_score == 19
    assert ev.period_scores[0].away_score == 20
    assert ev.period_scores[0].period_key == 1
    assert ev.period_scores[2].period_name == "3rd quarter"
    assert ev.period_scores[2].home_score == 33
    # Verify empty PS yields empty list.
    ev2_ps = rules._extract_period_scores({"PS": []})
    assert ev2_ps == []


def test_extract_period_scores_handles_malformed(rules: BetB2BExtractionRules) -> None:
    """Malformed PS[] should degrade gracefully — no crashes, no spam."""
    # None SC
    assert rules._extract_period_scores(None) == []
    # Empty dict
    assert rules._extract_period_scores({}) == []
    # PS not a list
    assert rules._extract_period_scores({"PS": "string"}) == []
    # Item missing Value
    ps = rules._extract_period_scores({"PS": [{"Key": 1, "Value": None}]})
    assert ps == []
    # Item with missing NF — falls back to empty string
    ps2 = rules._extract_period_scores({"PS": [{"Key": 1, "Value": {"S1": 10, "S2": 20}}]})
    assert len(ps2) == 1
    assert ps2[0].period_name == ""
    assert ps2[0].home_score == 10


# ---------------------------------------------------------------------------
# H2H extraction tests
# ---------------------------------------------------------------------------

SAMPLE_H2H_RESPONSE = {
    "teams": [
        {"id": "5ab1265c494765f3ca240306", "name": "Oklahoma City Thunder"},
        {"id": "5ab1265c494765f3ca240317", "name": "Brooklyn Nets"},
    ],
    "gameShorts": [
        {
            "id": "6865cd0d9930a40b3ceaeffb",
            "stageId": "68659e8b9930a40b3cb0bfd6",
            "team1": "5ab1265c494765f3ca240306",
            "team2": "5ab1265c494765f3ca240317",
            "dateStart": 1752183000,
            "score1": 81,
            "score2": 90,
            "subScore1": 0,
            "subScore2": 0,
            "winner": 2,
            "status": 3,
            "periods": [
                {"score1": 15, "score2": 22, "type": 18},
                {"score1": 20, "score2": 24, "type": 19},
            ],
        },
        {
            "id": "6865ce0d9930a40b3ceaeffc",
            "team1": "5ab1265c494765f3ca240306",
            "team2": "5ab1265c494765f3ca240317",
            "dateStart": 1752269400,
            "score1": 77,
            "score2": 85,
            "winner": 2,
            "status": 3,
            "periods": [],
        },
    ],
    "sportId": 3,
    "subSportId": None,
    "entity": "GameH2H",
}


def test_extract_h2h_data_valid(rules: BetB2BExtractionRules) -> None:
    """Valid H2H response should parse into H2HData with correct structure."""
    result = rules.extract_h2h_data(SAMPLE_H2H_RESPONSE)
    assert result is not None
    assert isinstance(result, H2HData)
    assert len(result.teams) == 2
    assert result.teams[0]["name"] == "Oklahoma City Thunder"
    assert result.sport_id == 3

    # gameShorts
    assert len(result.game_shorts) == 2

    gs0 = result.game_shorts[0]
    assert isinstance(gs0, H2HGameShort)
    assert gs0.game_id == "6865cd0d9930a40b3ceaeffb"
    assert gs0.score1 == 81
    assert gs0.score2 == 90
    assert gs0.winner == 2
    assert gs0.date_start is not None

    # Periods within gameShort
    assert len(gs0.periods) == 2
    assert gs0.periods[0].period_name == "1st quarter"
    assert gs0.periods[0].home_score == 15
    assert gs0.periods[0].away_score == 22
    assert gs0.periods[0].period_key == 18
    assert gs0.periods[1].period_name == "2nd quarter"

    # Second game has no periods
    gs1 = result.game_shorts[1]
    assert gs1.periods == []

    # Serialisation
    d = result.to_dict()
    assert len(d["teams"]) == 2
    assert len(d["game_shorts"]) == 2
    assert d["game_shorts"][0]["score1"] == 81
    assert d["sport_id"] == 3


def test_extract_h2h_data_none(rules: BetB2BExtractionRules) -> None:
    """None or empty dict returns None."""
    assert rules.extract_h2h_data(None) is None
    assert rules.extract_h2h_data({}) is None


def test_extract_h2h_data_malformed(rules: BetB2BExtractionRules) -> None:
    """Malformed responses should return None gracefully."""
    # Missing teams
    assert rules.extract_h2h_data({"gameShorts": []}) is None
    # Missing gameShorts
    assert rules.extract_h2h_data({"teams": []}) is None
    # Wrong types
    assert rules.extract_h2h_data({"teams": "not_list", "gameShorts": []}) is None
    assert rules.extract_h2h_data({"teams": [], "gameShorts": "not_list"}) is None


def test_extract_h2h_data_empty_game_shorts(rules: BetB2BExtractionRules) -> None:
    """Empty gameShorts array produces valid H2HData with no games."""
    raw = {"teams": [], "gameShorts": [], "sportId": 1}
    result = rules.extract_h2h_data(raw)
    assert result is not None
    assert result.game_shorts == []
    assert result.sport_id == 1


def test_extract_h2h_data_bad_periods(rules: BetB2BExtractionRules) -> None:
    """Malformed periods within gameShorts should not crash."""
    raw = {
        "teams": [{"id": "t1", "name": "Team A"}],
        "gameShorts": [
            {"id": "g1", "team1": "t1", "team2": "t2", "periods": "not_a_list"},
            {"id": "g2", "team1": "t1", "team2": "t2", "periods": [None, {"score1": 10}]},
        ],
        "sportId": 1,
    }
    result = rules.extract_h2h_data(raw)
    assert result is not None
    assert len(result.game_shorts) == 2
    # First game: periods was not a list → empty periods
    assert result.game_shorts[0].periods == []
    # Second game: skips None item, parses the dict item
    assert len(result.game_shorts[1].periods) == 1
    assert result.game_shorts[1].periods[0].home_score == 10
