"""
Unit tests for YAML selector loading functionality.

These tests verify that YAML selectors can be loaded, validated, and registered correctly.
Tests are written to FAIL initially and will pass after implementation.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.selectors.models import (
    YAMLSelector, SelectorStrategy, SelectorType, StrategyType,
    SelectorValidationError, ValidationResult, LoadResult
)
from src.selectors.exceptions import (
    SelectorLoadingError, SelectorValidationError as SelectorValidationException,
    SelectorFileError
)


class TestYAMLSelectorLoader:
    """Test cases for YAML selector loader."""
    
    @pytest.fixture
    def sample_yaml_selector(self):
        """Sample YAML selector data for testing."""
        return {
            "id": "test_article_title",
            "name": "Article Title Selector",
            "description": "Extracts article title from Wikipedia pages",
            "selector_type": "css",
            "pattern": "h1#firstHeading",
            "strategies": [
                {
                    "type": "text_anchor",
                    "priority": 1,
                    "config": {
                        "anchor_text": "Article Title"
                    },
                    "confidence_threshold": 0.9,
                    "enabled": True
                }
            ],
            "validation_rules": {
                "min_confidence": 0.8,
                "required_attributes": ["text"]
            },
            "metadata": {
                "version": "1.0.0",
                "author": "test"
            }
        }
    
    @pytest.fixture
    def temp_selector_file(self, sample_yaml_selector):
        """Create temporary YAML selector file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_yaml_selector, f)
            return f.name
    
    def test_load_selector_from_valid_file(self, temp_selector_file, sample_yaml_selector):
        """Test loading selector from valid YAML file."""
        # This test should FAIL initially - loader not implemented yet
        from src.selectors.yaml_loader import YAMLSelectorLoader
        
        loader = YAMLSelectorLoader()
        result = loader.load_selector_from_file(temp_selector_file)
        
        assert result is not None
        assert result.id == sample_yaml_selector["id"]
        assert result.name == sample_yaml_selector["name"]
        assert result.selector_type == SelectorType.CSS
        assert result.pattern == sample_yaml_selector["pattern"]
        assert len(result.strategies) == 1
        assert result.strategies[0].type == StrategyType.TEXT_ANCHOR
    
    def test_load_selector_from_invalid_yaml(self):
        """Test loading selector from invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_file = f.name
        
        from src.selectors.yaml_loader import YAMLSelectorLoader
        
        loader = YAMLSelectorLoader()
        
        with pytest.raises(SelectorLoadingError):
            loader.load_selector_from_file(invalid_file)
        
        Path(invalid_file).unlink()
    
    def test_load_selector_from_nonexistent_file(self):
        """Test loading selector from nonexistent file."""
        from src.selectors.yaml_loader import YAMLSelectorLoader
        
        loader = YAMLSelectorLoader()
        
        with pytest.raises(SelectorFileError):
            loader.load_selector_from_file("/nonexistent/file.yaml")
    
    def test_load_selector_from_file_without_required_fields(self):
        """Test loading selector missing required fields."""
        incomplete_selector = {
            "name": "Incomplete Selector"
            # Missing required fields: id, selector_type, pattern, strategies
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(incomplete_selector, f)
            incomplete_file = f.name
        
        from src.selectors.yaml_loader import YAMLSelectorLoader
        
        loader = YAMLSelectorLoader()
        
        with pytest.raises(SelectorValidationError):
            loader.load_selector_from_file(incomplete_file)
        
        Path(incomplete_file).unlink()
    
    def test_load_selectors_from_directory(self, temp_selector_file):
        """Test loading multiple selectors from directory."""
        # Create additional selector files
        temp_dir = Path(temp_selector_file).parent
        
        # Create second selector
        second_selector = {
            "id": "test_article_content",
            "name": "Article Content Selector",
            "selector_type": "css",
            "pattern": "div#mw-content-text",
            "strategies": [
                {
                    "type": "attribute_match",
                    "priority": 1,
                    "config": {
                        "attribute": "id",
                        "value_pattern": "mw-content-text"
                    },
                    "confidence_threshold": 0.8,
                    "enabled": True
                }
            ]
        }
        
        second_file = temp_dir / "second_selector.yaml"
        with open(second_file, 'w') as f:
            yaml.dump(second_selector, f)
        
        from src.selectors.yaml_loader import YAMLSelectorLoader
        
        loader = YAMLSelectorLoader()
        result = loader.load_selectors_from_directory(str(temp_dir))
        
        assert result.success is True
        assert result.selectors_loaded == 2
        assert result.selectors_failed == 0
        assert len(result.errors) == 0
    
    def test_load_selectors_from_directory_with_mixed_success(self, temp_selector_file):
        """Test loading selectors with some failures."""
        temp_dir = Path(temp_selector_file).parent
        
        # Create invalid selector file
        invalid_file = temp_dir / "invalid.yaml"
        with open(invalid_file, 'w') as f:
            f.write("invalid: yaml: [")
        
        from src.selectors.yaml_loader import YAMLSelectorLoader
        
        loader = YAMLSelectorLoader()
        result = loader.load_selectors_from_directory(str(temp_dir))
        
        assert result.success is True  # Continue on error
        assert result.selectors_loaded == 1
        assert result.selectors_failed == 1
        assert len(result.errors) == 1
    
    def test_selector_validation_integration(self, temp_selector_file):
        """Test selector validation during loading."""
        from src.selectors.yaml_loader import YAMLSelectorLoader
        
        loader = YAMLSelectorLoader()
        selector = loader.load_selector_from_file(temp_selector_file)
        
        # Validation should be performed automatically
        assert selector is not None
        assert selector.validate() == []  # No validation errors
    
    def test_performance_monitoring_integration(self, temp_selector_file):
        """Test that performance monitoring is integrated."""
        from src.selectors.yaml_loader import YAMLSelectorLoader
        from src.selectors.performance_monitor import get_performance_monitor
        
        monitor = get_performance_monitor()
        initial_stats = monitor.get_stats("selector_loading")
        
        loader = YAMLSelectorLoader()
        loader.load_selector_from_file(temp_selector_file)
        
        # Performance should be recorded
        final_stats = monitor.get_stats("selector_loading")
        assert final_stats["total_operations"] > initial_stats.get("total_operations", 0)


class TestSelectorStrategy:
    """Test cases for selector strategy functionality."""
    
    def test_strategy_validation_valid(self):
        """Test validation of valid strategy."""
        strategy = SelectorStrategy(
            type=StrategyType.TEXT_ANCHOR,
            priority=1,
            config={"anchor_text": "Test"},
            confidence_threshold=0.8
        )
        
        errors = strategy.validate()
        assert len(errors) == 0
    
    def test_strategy_validation_missing_config(self):
        """Test validation of strategy with missing config."""
        strategy = SelectorStrategy(
            type=StrategyType.TEXT_ANCHOR,
            priority=1,
            config={},  # Missing required anchor_text
            confidence_threshold=0.8
        )
        
        errors = strategy.validate()
        assert len(errors) > 0
        assert any("anchor_text" in error for error in errors)
    
    def test_strategy_validation_invalid_priority(self):
        """Test validation of strategy with invalid priority."""
        strategy = SelectorStrategy(
            type=StrategyType.TEXT_ANCHOR,
            priority=0,  # Invalid priority
            config={"anchor_text": "Test"},
            confidence_threshold=0.8
        )
        
        with pytest.raises(ValueError, match="Strategy priority must be positive"):
            strategy.validate()
    
    def test_strategy_validation_invalid_confidence(self):
        """Test validation of strategy with invalid confidence threshold."""
        strategy = SelectorStrategy(
            type=StrategyType.TEXT_ANCHOR,
            priority=1,
            config={"anchor_text": "Test"},
            confidence_threshold=1.5  # Invalid confidence
        )
        
        with pytest.raises(ValueError, match="Confidence threshold must be between 0.0 and 1.0"):
            strategy.validate()


class TestYAMLSelector:
    """Test cases for YAML selector functionality."""
    
    @pytest.fixture
    def valid_selector_data(self):
        """Valid selector data for testing."""
        return {
            "id": "test_selector",
            "name": "Test Selector",
            "selector_type": "css",
            "pattern": ".test-class",
            "strategies": [
                {
                    "type": "text_anchor",
                    "priority": 1,
                    "config": {"anchor_text": "test"},
                    "confidence_threshold": 0.8,
                    "enabled": True
                }
            ]
        }
    
    def test_selector_creation_valid(self, valid_selector_data):
        """Test creating valid selector."""
        strategies = [SelectorStrategy.from_dict(s) for s in valid_selector_data["strategies"]]
        selector = YAMLSelector(
            id=valid_selector_data["id"],
            name=valid_selector_data["name"],
            selector_type=SelectorType(valid_selector_data["selector_type"]),
            pattern=valid_selector_data["pattern"],
            strategies=strategies,
            file_path="/test/path.yaml"
        )
        
        assert selector.id == "test_selector"
        assert selector.name == "Test Selector"
        assert selector.selector_type == SelectorType.CSS
        assert selector.pattern == ".test-class"
        assert len(selector.strategies) == 1
    
    def test_selector_validation_empty_id(self, valid_selector_data):
        """Test selector validation with empty ID."""
        valid_selector_data["id"] = ""
        strategies = [SelectorStrategy.from_dict(s) for s in valid_selector_data["strategies"]]
        
        with pytest.raises(ValueError, match="Selector ID cannot be empty"):
            YAMLSelector(
                id=valid_selector_data["id"],
                name=valid_selector_data["name"],
                selector_type=SelectorType(valid_selector_data["selector_type"]),
                pattern=valid_selector_data["pattern"],
                strategies=strategies,
                file_path="/test/path.yaml"
            )
    
    def test_selector_validation_no_strategies(self, valid_selector_data):
        """Test selector validation with no strategies."""
        with pytest.raises(ValueError, match="Selector must have at least one strategy"):
            YAMLSelector(
                id=valid_selector_data["id"],
                name=valid_selector_data["name"],
                selector_type=SelectorType(valid_selector_data["selector_type"]),
                pattern=valid_selector_data["pattern"],
                strategies=[],  # No strategies
                file_path="/test/path.yaml"
            )
    
    def test_selector_duplicate_strategy_priorities(self, valid_selector_data):
        """Test selector validation with duplicate strategy priorities."""
        valid_selector_data["strategies"].append({
            "type": "attribute_match",
            "priority": 1,  # Same priority as first strategy
            "config": {"attribute": "class", "value_pattern": "test"},
            "confidence_threshold": 0.7,
            "enabled": True
        })
        
        strategies = [SelectorStrategy.from_dict(s) for s in valid_selector_data["strategies"]]
        
        with pytest.raises(ValueError, match="Strategy priorities must be unique"):
            YAMLSelector(
                id=valid_selector_data["id"],
                name=valid_selector_data["name"],
                selector_type=SelectorType(valid_selector_data["selector_type"]),
                pattern=valid_selector_data["pattern"],
                strategies=strategies,
                file_path="/test/path.yaml"
            )
    
    def test_selector_to_dict_roundtrip(self, valid_selector_data):
        """Test selector serialization and deserialization."""
        strategies = [SelectorStrategy.from_dict(s) for s in valid_selector_data["strategies"]]
        selector = YAMLSelector(
            id=valid_selector_data["id"],
            name=valid_selector_data["name"],
            selector_type=SelectorType(valid_selector_data["selector_type"]),
            pattern=valid_selector_data["pattern"],
            strategies=strategies,
            file_path="/test/path.yaml"
        )
        
        # Convert to dict and back
        selector_dict = selector.to_dict()
        restored_selector = YAMLSelector.from_dict(selector_dict)
        
        assert restored_selector.id == selector.id
        assert restored_selector.name == selector.name
        assert restored_selector.selector_type == selector.selector_type
        assert restored_selector.pattern == selector.pattern
        assert len(restored_selector.strategies) == len(selector.strategies)
