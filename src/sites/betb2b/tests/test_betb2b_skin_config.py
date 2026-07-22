"""Skin config loading — the merge semantics of the overridable tables."""

from __future__ import annotations

from src.sites.betb2b.config import BetB2BSkinConfig


def _minimal(**extra):
    return BetB2BSkinConfig.from_dict({"name": "testskin", "domain": "example.test", **extra})


def test_features_from_yaml_merge_onto_the_defaults():
    """Naming one flag must not drop the others. They are the family's
    contract, not a set the skin restates in full."""
    default = _minimal()
    cfg = _minimal(features={"subgames": True})
    assert cfg.features["subgames"] is True
    for flag, value in default.features.items():
        if flag != "subgames":
            assert cfg.features[flag] == value, f"{flag} lost when subgames was set"


def test_features_override_a_default_that_is_on():
    assert _minimal(features={"live": False}).features["live"] is False


def test_features_absent_leaves_the_family_defaults():
    cfg = _minimal()
    assert cfg.features["prematch"] is True
    assert cfg.features["subgames"] is False


def test_lookup_tables_still_merge_onto_the_family_defaults():
    """Guards the pattern the features merge was made consistent with."""
    default = _minimal()
    cfg = _minimal(sport_map={"999": {"si_id": 999, "name": "Kabaddi"}})
    assert cfg.sport_map[999].name == "Kabaddi"
    assert set(default.sport_map) <= set(cfg.sport_map)


def test_unknown_keys_still_fail_loudly():
    import pytest

    with pytest.raises(ValueError, match="Unknown skin config keys"):
        _minimal(featurez={"subgames": True})
