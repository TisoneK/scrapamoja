"""Tests for browser-free event-id extraction (src/sites/betb2b/harvest.py)."""

from __future__ import annotations

import pytest

from src.sites.betb2b.harvest import (
    extract_champ_ids, extract_event_ids, extract_leagues_from_sports,
)


# --- GetSportsZip league parsing (ADR-15 browser-free discovery) ------------ #
_SPORTS = {"Value": [
    {"I": 3, "N": "Basketball", "L": [
        {"LI": 197289, "GC": 9, "L": "WNBA"},
        {"LI": 850473, "GC": 2, "L": "Philippines"},
        {"LI": 1, "GC": 0, "L": "empty (no games)"},
    ]},
    {"I": 1, "N": "Football", "L": [{"LI": 999, "GC": 50, "L": "EPL"}]},
]}


def test_extract_leagues_filters_sport_and_sorts_by_games():
    # basketball only; GC=0 dropped; highest game-count first
    assert extract_leagues_from_sports(_SPORTS, 3) == [
        (197289, 9, "WNBA"), (850473, 2, "Philippines")]


def test_extract_leagues_all_sports_when_no_filter():
    assert extract_leagues_from_sports(_SPORTS, None) == [
        (999, 50, "EPL"), (197289, 9, "WNBA"), (850473, 2, "Philippines")]


def test_extract_leagues_empty_safe():
    assert extract_leagues_from_sports({}, 3) == []
    assert extract_leagues_from_sports({"Value": None}, 3) == []
    assert extract_leagues_from_sports({"Value": [{"I": 3, "L": None}]}, 3) == []


def test_extracts_nine_digit_event_ids():
    html = (
        '<a href="/en/live/basketball/1463027-philippines/850473-cup/'
        '738047045-phoenix-rain">…</a>'
        '<a href="/en/live/basketball/1463027-philippines/850473-cup/'
        '738062773-caixa-minas">…</a>'
    )
    ids = extract_event_ids(html)
    assert ids == ["738047045", "738062773"]  # 9-digit events, order preserved


def test_ignores_short_league_country_ids():
    # 6–7 digit league/country ids must NOT be picked up as events.
    html = "/852345-league/233807-country/1463027-region/738047045-match"
    assert extract_event_ids(html) == ["738047045"]


def test_dedupes_repeated_ids():
    html = "/738047045-a ... /738047045-a ... /738062773-b"
    assert extract_event_ids(html) == ["738047045", "738062773"]


def test_limit_caps_result():
    html = " ".join(f"/{738000000 + i}-t{i}" for i in range(10))
    assert len(extract_event_ids(html, limit=3)) == 3


def test_empty_and_none_safe():
    assert extract_event_ids("") == []
    assert extract_event_ids(None) == []


def test_does_not_glue_longer_numbers():
    # A 15-digit blob (e.g. a timestamp) is not an event id.
    assert extract_event_ids("timestamp 1737460000123456") == []


def test_bare_ids_and_asset_hashes_are_not_events():
    # Only match-link ids (<id>-<slug>) count. Bare numbers and 9-10 digit runs
    # embedded in asset hashes / file paths must NOT be fetched (they each cost a
    # wasted GetGameZip → "Game is not found"). Real HTML shapes observed live.
    html = (
        'src="/…/1b72754ed49e8e7fb4b4d3c251436156/Aviator-dropdown.png" '
        'href="third-party-files/140599367e25275c31b876fa5394b" '
        'data-x="1785159600" '  # bare timestamp-ish number
        'href="/en/line/basketball/1413697-x/354744562-england-3x3-women">'
    )
    assert extract_event_ids(html) == ["354744562"]  # only the real match link


# --- champ (league) id extraction for GetChampZip discovery ----------------- #

def test_extract_champ_ids_from_league_links():
    html = (
        '<a href="/en/line/basketball/850473-philippines-governors-cup">x</a>'
        '<a href="/en/live/basketball/1933939-kenya-premier-league">y</a>'
    )
    assert extract_champ_ids(html) == ["850473", "1933939"]


def test_extract_champ_ids_dedupes_and_orders():
    html = (
        "/en/line/basketball/850473-a /en/line/basketball/850473-a "
        "/en/line/basketball/1906293-b"
    )
    assert extract_champ_ids(html) == ["850473", "1906293"]


def test_extract_champ_ids_ignores_event_ids():
    # The deep 9-10 digit event id must NOT be read as a champ id; only the
    # 4-7 digit id immediately after the sport slug is a league.
    html = "/en/line/basketball/850473-cup/738047045-phoenix-rain"
    assert extract_champ_ids(html) == ["850473"]


def test_extract_champ_ids_empty_safe():
    assert extract_champ_ids("") == []
    assert extract_champ_ids(None) == []
    assert extract_champ_ids("no league links here") == []


def test_champ_feed_path_wired_with_top_false():
    # GetChampZip is wired as the "champ" feed, and top must be overridable to
    # false (top=true returns 0 games for a specific champ).
    from src.sites.betb2b.config import DEFAULT_SKIN_CONFIG
    url = DEFAULT_SKIN_CONFIG.feed_url(
        "champ", root="line", extra_params={"champ": "850473", "top": "false"})
    assert "/LineFeed/GetChampZip?" in url
    assert "champ=850473" in url
    assert "top=false" in url
