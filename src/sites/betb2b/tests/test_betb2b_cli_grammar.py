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


# ---------------------------------------------------------------------------
# Multi-skin resolution (one command, several skins → one shared --db)
# ---------------------------------------------------------------------------
from src.sites.betb2b.cli.main import _resolve_skins


def test_resolve_single_skin():
    assert _resolve_skins("linebet") == ["linebet"]


def test_resolve_comma_list_preserves_order_dedupes():
    assert _resolve_skins("linebet,melbet,helabet,linebet") == ["linebet", "melbet", "helabet"]


def test_resolve_strips_whitespace():
    assert _resolve_skins(" linebet , melbet ") == ["linebet", "melbet"]


def test_resolve_empty_defaults_to_linebet():
    assert _resolve_skins("") == ["linebet"]


def test_all_skins_lists_every_skin():
    skins = _resolve_skins("linebet", all_skins=True)
    assert "linebet" in skins and "melbet" in skins
    assert len(skins) >= 5  # 8 skins ship


class TestMultiSkinParsing:
    def setup_method(self):
        self.parser = BetB2BCLI().create_parser()

    def test_scrape_comma_list_parses(self):
        a = self.parser.parse_args(["scrape", "linebet,melbet", "live"])
        assert a.skin_pos == "linebet,melbet"

    def test_scrape_all_skins_flag(self):
        a = self.parser.parse_args(["scrape", "live", "--all-skins"])
        assert a.all_skins is True

    def test_poll_comma_list_parses(self):
        a = self.parser.parse_args(["poll", "linebet,melbet", "live", "--interval", "30"])
        assert a.skin_pos == "linebet,melbet"
        assert a.all_skins is False


class TestSubgamesFlag:
    """ADR-7's half/quarter scopes need sub-game fetching, and the `subgames`
    feature defaults to off — so the flag is the only thing that can reach the
    scoped-ingestion path from a command line."""

    def setup_method(self):
        self.parser = BetB2BCLI().create_parser()

    def test_scrape_accepts_subgames(self):
        assert self.parser.parse_args(["scrape", "linebet", "live", "--subgames"]).subgames is True

    def test_poll_accepts_subgames(self):
        assert self.parser.parse_args(["poll", "linebet", "live", "--subgames"]).subgames is True

    def test_subgames_defaults_off(self):
        assert self.parser.parse_args(["scrape", "linebet", "live"]).subgames is False

    def test_flag_turns_the_skin_feature_on(self):
        """The flag has to survive into the skin the scraper is built from —
        `_enrich_with_subgames` reads `skin.features['subgames']`, nothing else."""
        from src.sites.betb2b.config import DEFAULT_SKIN_CONFIG

        assert DEFAULT_SKIN_CONFIG.features["subgames"] is False
        overridden = DEFAULT_SKIN_CONFIG.with_overrides(
            features={**DEFAULT_SKIN_CONFIG.features, "subgames": True}
        )
        assert overridden.features["subgames"] is True
        assert overridden.features["h2h"] is DEFAULT_SKIN_CONFIG.features["h2h"]
