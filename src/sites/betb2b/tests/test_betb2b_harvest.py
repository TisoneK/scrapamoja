"""Tests for browser-free event-id extraction (src/sites/betb2b/harvest.py)."""

from __future__ import annotations

import pytest

from src.sites.betb2b.harvest import extract_event_ids


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
    html = "738047045 ... 738047045 ... 738062773"
    assert extract_event_ids(html) == ["738047045", "738062773"]


def test_limit_caps_result():
    html = " ".join(str(738000000 + i) for i in range(10))
    assert len(extract_event_ids(html, limit=3)) == 3


def test_empty_and_none_safe():
    assert extract_event_ids("") == []
    assert extract_event_ids(None) == []


def test_does_not_glue_longer_numbers():
    # A 15-digit blob (e.g. a timestamp) is not an event id.
    assert extract_event_ids("timestamp 1737460000123456") == []
