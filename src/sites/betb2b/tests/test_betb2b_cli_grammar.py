"""Tests for the friendly betb2b scrape grammar.

`scrape linebet live` (positional, betting words) is the easy path; the
`--skin`/`--action` flags still work. Sport stays optional (all sports).
"""

from __future__ import annotations

import pytest

from src.sites.betb2b.cli.main import (
    BetB2BCLI,
    _reconcile_scrape_target,
    _resolve_action,
)


@pytest.mark.parametrize(
    "word,expected",
    [
        ("live", "list_live"),
        ("inplay", "list_live"),
        ("scheduled", "list_prematch"),
        ("prematch", "list_prematch"),
        ("all", "list_all"),
        ("both", "list_all"),
        ("LIVE", "list_live"),        # case-insensitive
        ("list_prematch", "list_prematch"),  # canonical passthrough
        ("raw_capture", "raw_capture"),
    ],
)
def test_resolve_action(word, expected):
    assert _resolve_action(word) == expected


def test_resolve_action_rejects_garbage():
    with pytest.raises(ValueError):
        _resolve_action("nonsense")


@pytest.mark.parametrize(
    "skin_pos,status_pos,skin_flag,action_flag,expected",
    [
        # Easy positional form.
        ("linebet", "live", "linebet", "list_live", ("linebet", "list_live")),
        ("linebet", "scheduled", "linebet", "list_live", ("linebet", "list_prematch")),
        ("melbet", "all", "linebet", "list_live", ("melbet", "list_all")),
        # Lone status word → default skin.
        ("live", None, "linebet", "list_live", ("linebet", "list_live")),
        ("scheduled", None, "linebet", "list_live", ("linebet", "list_prematch")),
        # Skin only → default action.
        ("helabet", None, "linebet", "list_live", ("helabet", "list_live")),
        # No positionals → the flags win.
        (None, None, "linebet", "list_all", ("linebet", "list_all")),
        (None, None, "helabet", "live", ("helabet", "list_live")),  # friendly flag word
        # Positional overrides the flag default.
        ("melbet", "live", "linebet", "list_live", ("melbet", "list_live")),
    ],
)
def test_reconcile(skin_pos, status_pos, skin_flag, action_flag, expected):
    assert _reconcile_scrape_target(skin_pos, status_pos, skin_flag, action_flag) == expected


def test_reconcile_rejects_bad_status():
    with pytest.raises(ValueError):
        _reconcile_scrape_target("linebet", "yesterday", "linebet", "list_live")


class TestParserAcceptsBothForms:
    def setup_method(self):
        self.parser = BetB2BCLI().create_parser()

    def test_positional_form_parses(self):
        a = self.parser.parse_args(["scrape", "linebet", "live"])
        assert a.skin_pos == "linebet"
        assert a.status_pos == "live"

    def test_flag_form_still_parses(self):
        a = self.parser.parse_args(["scrape", "--skin", "melbet", "--action", "list_all"])
        assert a.skin == "melbet"
        assert a.action == "list_all"
        assert a.skin_pos is None and a.status_pos is None

    def test_bare_scrape_uses_defaults(self):
        a = self.parser.parse_args(["scrape"])
        assert a.skin == "linebet"
        assert a.action == "list_live"
        assert a.skin_pos is None and a.status_pos is None

    def test_positional_with_optional_sport_and_db(self):
        a = self.parser.parse_args(
            ["scrape", "melbet", "all", "--sport", "basketball", "--db", "x.db"]
        )
        assert a.skin_pos == "melbet"
        assert a.status_pos == "all"
        assert a.sport == "basketball"
        assert a.db == "x.db"
