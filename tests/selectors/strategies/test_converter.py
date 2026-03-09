"""
Unit tests for strategy format converter.

Tests the conversion between Flashscore's legacy strategy format
and the engine's StrategyPattern format.
"""

import pytest
from typing import Dict, Any, List


class TestDetectFormat:
    """Tests for format detection."""

    def test_detect_legacy_format(self):
        """Test detection of legacy format with strategies list."""
        from src.selectors.strategies.converter import detect_format, StrategyFormat
        
        legacy_config = {
            "strategies": [
                {"type": "css", "selector": ".team.home", "weight": 1.0},
                {"type": "css", "selector": ".team.away", "weight": 0.8}
            ]
        }
        
        assert detect_format(legacy_config) == StrategyFormat.LEGACY

    def test_detect_strategypattern_format(self):
        """Test detection of StrategyPattern format."""
        from src.selectors.strategies.converter import detect_format, StrategyFormat
        
        strategypattern_config = {
            "type": "css",
            "priority": 100,
            "config": {"selector": ".team.home"}
        }
        
        assert detect_format(strategypattern_config) == StrategyFormat.STRATEGY_PATTERN

    def test_detect_strategypattern_with_config(self):
        """Test detection when config key present."""
        from src.selectors.strategies.converter import detect_format, StrategyFormat
        
        config_with_config = {
            "id": "home_team",
            "type": "css",
            "config": {"selector": ".team.home"},
            "priority": 50
        }
        
        assert detect_format(config_with_config) == StrategyFormat.STRATEGY_PATTERN

    def test_default_to_legacy(self):
        """Test that unknown formats default to legacy for backward compatibility."""
        from src.selectors.strategies.converter import detect_format, StrategyFormat
        
        unknown_config = {"unknown": "structure"}
        
        assert detect_format(unknown_config) == StrategyFormat.LEGACY


class TestConvertLegacyStrategy:
    """Tests for converting individual legacy strategies."""

    def test_convert_css_strategy(self):
        """Test converting a CSS strategy."""
        from src.selectors.strategies.converter import (
            convert_legacy_to_strategypattern, LegacyStrategy
        )
        
        legacy = LegacyStrategy(
            type="css",
            selector=".detailScore__wrapper",
            weight=1.0
        )
        
        result = convert_legacy_to_strategypattern(legacy, "test_strategy")
        
        assert result.id == "test_strategy"
        assert result.config["selector"] == ".detailScore__wrapper"
        assert result.priority == 100  # weight 1.0 * 100

    def test_convert_xpath_strategy(self):
        """Test converting an XPath strategy."""
        from src.selectors.strategies.converter import (
            convert_legacy_to_strategypattern, LegacyStrategy
        )
        
        legacy = LegacyStrategy(
            type="xpath",
            selector="//div[@class='score']",
            weight=0.8
        )
        
        result = convert_legacy_to_strategypattern(legacy, "xpath_strategy")
        
        assert result.id == "xpath_strategy"
        assert result.config["selector"] == "//div[@class='score']"
        assert result.priority == 80  # weight 0.8 * 100

    def test_convert_from_dict(self):
        """Test converting from a dictionary input."""
        from src.selectors.strategies.converter import convert_legacy_to_strategypattern
        
        legacy_dict = {
            "type": "css",
            "selector": ".team.home",
            "weight": 0.5
        }
        
        result = convert_legacy_to_strategypattern(legacy_dict, "dict_strategy")
        
        assert result.id == "dict_strategy"
        assert result.config["selector"] == ".team.home"
        assert result.priority == 50

    def test_weight_to_priority_conversion(self):
        """Test weight to priority conversion range."""
        from src.selectors.strategies.converter import convert_legacy_to_strategypattern, LegacyStrategy
        
        # Test various weights
        test_cases = [
            (0.0, 1),    # Minimum weight -> minimum priority
            (0.5, 50),   # Mid weight -> mid priority
            (1.0, 100),  # Maximum weight -> maximum priority
            (0.75, 75),  # Quarter weight -> quarter priority
        ]
        
        for weight, expected_priority in test_cases:
            legacy = LegacyStrategy(type="css", selector=".test", weight=weight)
            result = convert_legacy_to_strategypattern(legacy, "test")
            assert result.priority == expected_priority, f"Failed for weight {weight}"

    def test_default_priority_when_weight_none(self):
        """Test default priority when weight is None."""
        from src.selectors.strategies.converter import convert_legacy_to_strategypattern, LegacyStrategy
        
        legacy = LegacyStrategy(type="css", selector=".test", weight=None)
        
        result = convert_legacy_to_strategypattern(legacy, "test", default_priority=50)
        
        assert result.priority == 50

    def test_alternatives_preserved(self):
        """Test that alternatives are preserved in config."""
        from src.selectors.strategies.converter import convert_legacy_to_strategypattern, LegacyStrategy
        
        legacy = LegacyStrategy(
            type="css",
            selector=".team",
            weight=1.0,
            alternatives=["alt1", "alt2"]
        )
        
        result = convert_legacy_to_strategypattern(legacy, "test")
        
        assert "alternatives" in result.config
        assert result.config["alternatives"] == ["alt1", "alt2"]

    def test_confidence_preserved(self):
        """Test that confidence is preserved in config."""
        from src.selectors.strategies.converter import convert_legacy_to_strategypattern, LegacyStrategy
        
        legacy = LegacyStrategy(
            type="css",
            selector=".team",
            weight=1.0,
            confidence=0.95
        )
        
        result = convert_legacy_to_strategypattern(legacy, "test")
        
        assert "confidence" in result.config
        assert result.config["confidence"] == 0.95


class TestConvertLegacyStrategies:
    """Tests for converting lists of strategies."""

    def test_convert_multiple_strategies(self):
        """Test converting multiple strategies."""
        from src.selectors.strategies.converter import convert_legacy_strategies
        
        legacy_strategies = [
            {"type": "css", "selector": ".first", "weight": 1.0},
            {"type": "css", "selector": ".second", "weight": 0.8},
            {"type": "xpath", "selector": "//div", "weight": 0.6}
        ]
        
        results = convert_legacy_strategies(legacy_strategies, "home_team")
        
        assert len(results) == 3
        assert results[0].id == "home_team_0"
        assert results[1].id == "home_team_1"
        assert results[2].id == "home_team_2"

    def test_convert_empty_list(self):
        """Test converting empty strategy list."""
        from src.selectors.strategies.converter import convert_legacy_strategies
        
        results = convert_legacy_strategies([], "test")
        
        assert results == []


class TestConvertLegacyYaml:
    """Tests for full YAML config conversion."""

    def test_convert_full_legacy_config(self):
        """Test converting a complete legacy YAML config."""
        from src.selectors.strategies.converter import convert_legacy_yaml
        
        legacy_config = {
            "id": "home_team",
            "name": "Home Team",
            "description": "Selects home team name",
            "strategies": [
                {"type": "css", "selector": ".team.home", "weight": 1.0},
                {"type": "css", "selector": ".home-team", "weight": 0.9}
            ],
            "metadata": {"source": "flashscore"}
        }
        
        result = convert_legacy_yaml(legacy_config, "home_team")
        
        # Should have converted strategies
        assert "strategies" in result
        assert len(result["strategies"]) == 2
        
        # Check first strategy is converted
        first_strategy = result["strategies"][0]
        assert "id" in first_strategy
        assert "priority" in first_strategy
        assert "config" in first_strategy
        assert first_strategy["config"]["selector"] == ".team.home"

    def test_passthrough_strategypattern_format(self):
        """Test that StrategyPattern format is passed through unchanged."""
        from src.selectors.strategies.converter import convert_legacy_yaml
        
        strategypattern_config = {
            "id": "test",
            "type": "css",
            "priority": 100,
            "config": {"selector": ".test"}
        }
        
        result = convert_legacy_yaml(strategypattern_config, "test")
        
        # Should be unchanged
        assert result == strategypattern_config

    def test_preserves_metadata(self):
        """Test that metadata is preserved during conversion."""
        from src.selectors.strategies.converter import convert_legacy_yaml
        
        legacy_config = {
            "id": "test",
            "strategies": [{"type": "css", "selector": ".test", "weight": 1.0}],
            "metadata": {"wait_for_element": True, "tab_context": "summary"}
        }
        
        result = convert_legacy_yaml(legacy_config, "test")
        
        assert result["metadata"] == {"wait_for_element": True, "tab_context": "summary"}


class TestIsLegacyFormat:
    """Tests for file format detection."""

    def test_legacy_yaml_file(self, tmp_path):
        """Test detecting legacy format in a YAML file."""
        from src.selectors.strategies.converter import is_legacy_format
        
        # Create a temporary legacy YAML file
        yaml_file = tmp_path / "legacy.yaml"
        yaml_file.write_text("""
strategies:
  - type: css
    selector: .test
    weight: 1.0
""")
        
        assert is_legacy_format(str(yaml_file)) is True

    def test_strategypattern_yaml_file(self, tmp_path):
        """Test detecting StrategyPattern format in a YAML file."""
        from src.selectors.strategies.converter import is_legacy_format
        
        # Create a temporary StrategyPattern YAML file
        yaml_file = tmp_path / "strategypattern.yaml"
        yaml_file.write_text("""
type: css
priority: 100
config:
  selector: .test
""")
        
        assert is_legacy_format(str(yaml_file)) is False

    def test_nonexistent_file(self):
        """Test handling of nonexistent file."""
        from src.selectors.strategies.converter import is_legacy_format
        
        assert is_legacy_format("/nonexistent/file.yaml") is False


class TestIntegrationWithYamlLoader:
    """Integration tests with YAML loader."""

    def test_detect_format_in_yaml_loader(self):
        """Test that format detection works correctly."""
        from src.selectors.strategies.converter import detect_format, StrategyFormat
        
        # Test with a sample legacy config (simulating what yaml_loader would receive)
        legacy_config = {
            "strategies": [
                {"type": "css", "selector": ".test", "weight": 1.0}
            ]
        }
        
        # This is what yaml_loader does - detects format before conversion
        format_type = detect_format(legacy_config)
        assert format_type == StrategyFormat.LEGACY

    def test_conversion_happens_before_yaml_selector_creation(self):
        """Test that conversion produces correct structure for YAMLSelector."""
        from src.selectors.strategies.converter import convert_legacy_yaml
        
        legacy_config = {
            "id": "test_selector",
            "name": "Test Selector",
            "description": "A test selector",
            "selector_type": "css",
            "pattern": ".test",
            "strategies": [
                {"type": "css", "selector": ".detailScore__wrapper", "weight": 1.0},
                {"type": "css", "selector": ".detailScore__divider", "weight": 0.9}
            ],
            "metadata": {"source": "flashscore"}
        }
        
        result = convert_legacy_yaml(legacy_config, "test_selector")
        
        # Verify conversion produces StrategyPattern format
        assert "strategies" in result
        strategies = result["strategies"]
        
        # Check that each strategy now has the new format
        for strategy in strategies:
            assert "priority" in strategy, "Converted strategy should have priority"
            assert "config" in strategy, "Converted strategy should have config"
            assert "selector" in strategy["config"], "Config should contain selector"
        
        # Verify priorities are converted from weights (1.0 -> 100, 0.9 -> 90)
        assert strategies[0]["priority"] == 100
        assert strategies[1]["priority"] == 90


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
