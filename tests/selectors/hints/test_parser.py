"""
Unit tests for selector hint parsing.

These tests verify that the hint parsing functionality correctly:
1. Parses valid hint data from YAML
2. Handles missing fields with default values
3. Validates hint data types and ranges
4. Raises appropriate exceptions for invalid data
"""

import pytest
from src.selectors.hints.models import SelectorHint, HintSchema
from src.selectors.hints.parser import parse_hints
from src.selectors.exceptions import SelectorConfigurationError


class TestSelectorHint:
    """Tests for SelectorHint model."""
    
    def test_selector_hint_default_values(self):
        """Test that SelectorHint uses default values when fields are missing."""
        hint = SelectorHint()
        assert hint.stability == 0.5
        assert hint.priority == 5
        assert hint.alternatives == []
        assert hint.metadata is None
    
    def test_selector_hint_with_values(self):
        """Test creating SelectorHint with specific values."""
        hint = SelectorHint(
            stability=0.9,
            priority=3,
            alternatives=["fallback1", "fallback2"],
            metadata={"source": "yaml"}
        )
        assert hint.stability == 0.9
        assert hint.priority == 3
        assert hint.alternatives == ["fallback1", "fallback2"]
        assert hint.metadata == {"source": "yaml"}
    
    def test_selector_hint_from_dict(self):
        """Test creating SelectorHint from dictionary."""
        data = {
            "stability": 0.8,
            "priority": 2,
            "alternatives": ["alt1", "alt2"],
            "metadata": {"key": "value"}
        }
        hint = SelectorHint.from_dict(data)
        assert hint.stability == 0.8
        assert hint.priority == 2
        assert hint.alternatives == ["alt1", "alt2"]
        assert hint.metadata == {"key": "value"}
    
    def test_selector_hint_to_dict(self):
        """Test converting SelectorHint to dictionary."""
        hint = SelectorHint(
            stability=0.7,
            priority=4,
            alternatives=["a", "b"],
            metadata={"test": "data"}
        )
        data = hint.to_dict()
        assert data["stability"] == 0.7
        assert data["priority"] == 4
        assert data["alternatives"] == ["a", "b"]
        assert data["metadata"] == {"test": "data"}
    
    def test_selector_hint_invalid_stability(self):
        """Test that invalid stability values raise ValueError."""
        with pytest.raises(ValueError):
            SelectorHint(stability=-0.1)
        
        with pytest.raises(ValueError):
            SelectorHint(stability=1.1)
    
    def test_selector_hint_invalid_priority(self):
        """Test that invalid priority values raise ValueError."""
        with pytest.raises(ValueError):
            SelectorHint(priority=0)
        
        with pytest.raises(ValueError):
            SelectorHint(priority=11)
    
    def test_selector_hint_invalid_alternatives(self):
        """Test that invalid alternatives type raises ValueError."""
        with pytest.raises(ValueError):
            SelectorHint(alternatives="not a list")
    
    def test_selector_hint_invalid_metadata(self):
        """Test that invalid metadata type raises ValueError."""
        with pytest.raises(ValueError):
            SelectorHint(metadata="not a dict")


class TestHintSchema:
    """Tests for HintSchema validation."""
    
    def test_hint_schema_defaults(self):
        """Test that HintSchema provides default values."""
        validated = HintSchema.validate(None)
        assert validated["stability"] == 0.5
        assert validated["priority"] == 5
        assert validated["alternatives"] == []
        assert validated["metadata"] is None
    
    def test_hint_schema_validate_valid_data(self):
        """Test validating valid hint data."""
        data = {
            "stability": 0.9,
            "priority": 3,
            "alternatives": ["fallback1", "fallback2"],
            "metadata": {"source": "yaml"}
        }
        validated = HintSchema.validate(data)
        expected = {**data, "strategy": "linear"}
        assert validated == expected
    
    def test_hint_schema_validate_missing_fields(self):
        """Test that missing fields get default values."""
        data = {"stability": 0.8}
        validated = HintSchema.validate(data)
        assert validated["stability"] == 0.8
        assert validated["priority"] == 5
        assert validated["alternatives"] == []
    
    def test_hint_schema_invalid_type(self):
        """Test that invalid hint data types raise errors."""
        with pytest.raises(ValueError):
            HintSchema.validate("not a dict")
    
    def test_hint_schema_invalid_stability(self):
        """Test invalid stability values raise errors."""
        with pytest.raises(ValueError):
            HintSchema.validate({"stability": -0.1})
        
        with pytest.raises(ValueError):
            HintSchema.validate({"stability": 1.1})
    
    def test_hint_schema_invalid_priority(self):
        """Test invalid priority values raise errors."""
        with pytest.raises(ValueError):
            HintSchema.validate({"priority": 0})
        
        with pytest.raises(ValueError):
            HintSchema.validate({"priority": 11})
    
    def test_hint_schema_invalid_alternatives(self):
        """Test invalid alternatives type raises error."""
        with pytest.raises(ValueError):
            HintSchema.validate({"alternatives": "not a list"})


class TestHintParser:
    """Tests for parse_hints function."""
    
    def test_parse_hints_with_valid_data(self):
        """Test parsing valid hint data."""
        data = {
            "stability": 0.9,
            "priority": 3,
            "alternatives": ["fallback1", "fallback2"]
        }
        hint = parse_hints(data)
        assert isinstance(hint, SelectorHint)
        assert hint.stability == 0.9
        assert hint.priority == 3
        assert hint.alternatives == ["fallback1", "fallback2"]
    
    def test_parse_hints_with_no_data(self):
        """Test parsing with no hint data returns default values."""
        hint = parse_hints(None)
        assert isinstance(hint, SelectorHint)
        assert hint.stability == 0.5
        assert hint.priority == 5
        assert hint.alternatives == []
    
    def test_parse_hints_with_empty_dict(self):
        """Test parsing empty hint dictionary returns defaults."""
        hint = parse_hints({})
        assert isinstance(hint, SelectorHint)
        assert hint.stability == 0.5
        assert hint.priority == 5
        assert hint.alternatives == []
    
    def test_parse_hints_with_invalid_data(self):
        """Test that invalid hint data raises SelectorConfigurationError."""
        with pytest.raises(SelectorConfigurationError):
            parse_hints("not a dict")
        
        with pytest.raises(SelectorConfigurationError):
            parse_hints({"stability": "invalid"})


class TestHintIntegration:
    """Integration tests for hint parsing."""
    
    def test_complete_hint_workflow(self):
        """Test the complete workflow from raw data to SelectorHint."""
        raw_data = {
            "stability": 0.85,
            "priority": 2,
            "alternatives": ["secondary", "tertiary"],
            "metadata": {"confidence": 0.95}
        }
        
        # Parse directly
        hint = SelectorHint.from_dict(raw_data)
        assert hint.stability == 0.85
        assert hint.priority == 2
        assert hint.alternatives == ["secondary", "tertiary"]
        assert hint.metadata == {"confidence": 0.95}
        assert hint.strategy == "linear"
        
        # Validate first then parse
        validated = HintSchema.validate(raw_data)
        expected = {**raw_data, "strategy": "linear"}
        assert validated == expected
        hint2 = SelectorHint.from_dict(validated)
        assert hint.to_dict() == hint2.to_dict()
    
    def test_default_values_propagation(self):
        """Test that default values are correctly propagated through the parsing chain."""
        data = {}
        hint = parse_hints(data)
        assert hint.stability == 0.5
        assert hint.priority == 5
        assert hint.alternatives == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
