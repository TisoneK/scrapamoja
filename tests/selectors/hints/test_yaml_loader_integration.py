"""
Integration tests for YAML selector loading with hints.

These tests verify the complete flow from YAML file loading to selector creation
with hints, ensuring that the integration between the YAML loader and hint
parsing works correctly.
"""

import os
import yaml
import tempfile
import pytest
from src.selectors.yaml_loader import YAMLSelectorLoader
from src.selectors.hints.models import SelectorHint


class TestYamlLoaderHintIntegration:
    """Integration tests for YAML loader with hints."""
    
    def test_load_selector_with_hints_from_file(self):
        """Test loading a selector from YAML file with hints."""
        # Create temporary YAML file for testing
        yaml_content = '''
id: test-hint-selector
name: Test Hint Selector
selector_type: css
pattern: ".test-element"
strategies:
  - type: css
    priority: 1
    config: {"selector": ".test-element"}
hints:
  stability: 0.9
  priority: 3
  alternatives: ["fallback1", "fallback2"]
  metadata:
    source: "test"
'''.strip()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_selector.yaml")
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            
            # Temporarily disable file path validation for test
            from src.selectors.config import get_config
            config = get_config()
            original_validate = config.validate_file_paths
            config.validate_file_paths = False
            
            try:
                # Load selector from file
                loader = YAMLSelectorLoader(config=config)
                selector = loader.load_selector_from_file(temp_file)
            finally:
                config.validate_file_paths = original_validate
            
            # Verify selector basic properties
            assert selector.id == "test-hint-selector"
            assert selector.name == "Test Hint Selector"
            assert selector.selector_type.value == "css"
            assert selector.pattern == ".test-element"
            
            # Verify hints are parsed correctly
            assert selector.hints is not None
            assert isinstance(selector.hints, SelectorHint)
            assert selector.hints.stability == 0.9
            assert selector.hints.priority == 3
            assert selector.hints.alternatives == ["fallback1", "fallback2"]
            assert selector.hints.metadata == {"source": "test"}
    
    def test_load_selector_without_hints(self):
        """Test loading a selector without hints."""
        yaml_content = '''
id: test-no-hints
name: Test No Hints Selector
selector_type: css
pattern: ".test-element"
strategies:
  - type: css
    priority: 1
    config: {"selector": ".test-element"}
'''.strip()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_no_hints.yaml")
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            
            # Temporarily disable file path validation for test
            from src.selectors.config import get_config
            config = get_config()
            original_validate = config.validate_file_paths
            config.validate_file_paths = False
            
            try:
                # Load selector from file
                loader = YAMLSelectorLoader(config=config)
                selector = loader.load_selector_from_file(temp_file)
            finally:
                config.validate_file_paths = original_validate
            
            # Should have None or default hints
            assert selector.hints is not None
            assert isinstance(selector.hints, SelectorHint)
            assert selector.hints.stability == 0.5
            assert selector.hints.priority == 5
            assert selector.hints.alternatives == []
            assert selector.hints.metadata is None
    
    def test_load_selector_with_invalid_hints(self):
        """Test that invalid hints raise appropriate exception."""
        yaml_content = '''
id: test-invalid-hints
name: Test Invalid Hints
selector_type: css
pattern: ".test-element"
strategies:
  - type: css
    priority: 1
    config: {}
hints:
  stability: 2.0
  priority: 0
  alternatives: "not a list"
'''.strip()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_invalid_hints.yaml")
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            
            loader = YAMLSelectorLoader()
            with pytest.raises(Exception):
                selector = loader.load_selector_from_file(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
