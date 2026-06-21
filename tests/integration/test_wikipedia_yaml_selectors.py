"""
Integration tests for Wikipedia YAML selector integration.

These tests verify that YAML selectors integrate properly with the existing selector engine
and can extract real data from Wikipedia pages.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.selectors.models import (
    YAMLSelector, SelectorStrategy, SelectorType, StrategyType
)
from src.selectors.exceptions import (
    SelectorLoadingError, SelectorRegistrationError
)


class TestWikipediaYAMLSelectorIntegration:
    """Integration tests for Wikipedia YAML selectors."""
    
    @pytest.fixture
    def sample_wikipedia_selectors(self):
        """Sample Wikipedia YAML selectors for testing."""
        return {
            "article_title.yaml": {
                "id": "wikipedia_article_title",
                "name": "Wikipedia Article Title",
                "description": "Extracts the main article title from Wikipedia pages",
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
                    },
                    {
                        "type": "attribute_match",
                        "priority": 2,
                        "config": {
                            "attribute": "id",
                            "value_pattern": "firstHeading"
                        },
                        "confidence_threshold": 0.8,
                        "enabled": True
                    }
                ],
                "validation_rules": {
                    "min_confidence": 0.8,
                    "required_attributes": ["text"]
                }
            },
            "article_content.yaml": {
                "id": "wikipedia_article_content",
                "name": "Wikipedia Article Content",
                "description": "Extracts the main article content from Wikipedia pages",
                "selector_type": "css",
                "pattern": "div#mw-content-text",
                "strategies": [
                    {
                        "type": "dom_relationship",
                        "priority": 1,
                        "config": {
                            "relationship_type": "ancestor",
                            "target_selector": "h1#firstHeading"
                        },
                        "confidence_threshold": 0.9,
                        "enabled": True
                    }
                ],
                "validation_rules": {
                    "min_confidence": 0.7,
                    "min_length": 100
                }
            }
        }
    
    @pytest.fixture
    def temp_selector_directory(self, sample_wikipedia_selectors):
        """Create temporary directory with sample selector files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            selector_dir = Path(temp_dir) / "selectors"
            selector_dir.mkdir()
            
            for filename, selector_data in sample_wikipedia_selectors.items():
                selector_file = selector_dir / filename
                with open(selector_file, 'w') as f:
                    yaml.dump(selector_data, f)
            
            yield str(selector_dir)
    
    def test_yaml_selector_loading_integration(self, temp_selector_directory):
        """Test integration of YAML selector loading with existing systems."""
        # This test should FAIL initially - integration not implemented yet
        from src.selectors.yaml_loader import YAMLSelectorLoader
        from src.selectors.registry import SelectorRegistry
        
        # Load selectors
        loader = YAMLSelectorLoader()
        load_result = loader.load_selectors_from_directory(temp_selector_directory)
        
        assert load_result.success is True
        assert load_result.selectors_loaded == 2
        
        # Register selectors
        registry = SelectorRegistry()
        for selector_file in Path(temp_selector_directory).glob("*.yaml"):
            selector = loader.load_selector_from_file(str(selector_file))
            registry.register_selector(selector)
        
        # Verify selectors are registered
        assert len(registry.selectors) == 2
        assert "wikipedia_article_title" in registry.selectors
        assert "wikipedia_article_content" in registry.selectors
    
    def test_selector_engine_yaml_integration(self, temp_selector_directory):
        """Test integration with existing selector engine."""
        # This test should FAIL initially - engine integration not implemented yet
        from src.selectors.yaml_loader import YAMLSelectorLoader
        from src.selectors.engine import SelectorEngine  # Assuming this exists
        
        # Load and register YAML selectors
        loader = YAMLSelectorLoader()
        selectors = []
        
        for selector_file in Path(temp_selector_directory).glob("*.yaml"):
            selector = loader.load_selector_from_file(str(selector_file))
            selectors.append(selector)
        
        # Integrate with selector engine
        engine = SelectorEngine()
        
        for selector in selectors:
            engine.register_yaml_selector(selector)
        
        # Verify engine has YAML selectors
        stats = engine.get_statistics()
        assert stats["yaml_selectors_count"] == 2
        assert "wikipedia_article_title" in stats["available_selectors"]
    
    @pytest.mark.asyncio
    async def test_real_wikipedia_extraction(self, temp_selector_directory):
        """Test real Wikipedia data extraction using YAML selectors."""
        # This test should FAIL initially - real extraction not implemented yet
        from src.selectors.yaml_loader import YAMLSelectorLoader
        from src.sites.wikipedia.scraper import WikipediaScraper  # Assuming this exists
        
        # Setup scraper with YAML selectors
        loader = YAMLSelectorLoader()
        selectors = []
        
        for selector_file in Path(temp_selector_directory).glob("*.yaml"):
            selector = loader.load_selector_from_file(str(selector_file))
            selectors.append(selector)
        
        scraper = WikipediaScraper()
        scraper.load_yaml_selectors(selectors)
        
        # Mock real Wikipedia page content
        mock_html = """
        <html>
        <head><title>Test Article - Wikipedia</title></head>
        <body>
            <h1 id="firstHeading">Test Article</h1>
            <div id="mw-content-text">
                <p>This is the main content of the Wikipedia article.</p>
                <p>It contains multiple paragraphs and useful information.</p>
            </div>
        </body>
        </html>
        """
        
        # Extract data using YAML selectors
        with patch.object(scraper, 'get_page_content', return_value=mock_html):
            result = await scraper.extract_article("https://en.wikipedia.org/wiki/Test_Article")
        
        # Verify real data extraction
        assert result is not None
        assert result["title"] == "Test Article"
        assert "main content of the Wikipedia article" in result["content"]
        assert len(result["content"]) > 100  # Should extract substantial content
    
    def test_selector_fallback_mechanism(self, temp_selector_directory):
        """Test fallback mechanism when YAML selectors fail."""
        # This test should FAIL initially - fallback not implemented yet
        from src.selectors.yaml_loader import YAMLSelectorLoader
        from src.sites.wikipedia.scraper import WikipediaScraper
        
        # Create invalid selector
        invalid_selector_data = {
            "id": "invalid_selector",
            "name": "Invalid Selector",
            "selector_type": "css",
            "pattern": "nonexistent-element",
            "strategies": [
                {
                    "type": "text_anchor",
                    "priority": 1,
                    "config": {"anchor_text": "nonexistent"},
                    "confidence_threshold": 0.9,
                    "enabled": True
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_selector_data, f)
            invalid_file = f.name
        
        try:
            loader = YAMLSelectorLoader()
            selector = loader.load_selector_from_file(invalid_file)
            
            scraper = WikipediaScraper()
            scraper.load_yaml_selectors([selector])
            
            # Should fall back to basic extraction
            result = scraper.extract_with_fallback("https://en.wikipedia.org/wiki/Test")
            
            # Should still get some data, even if YAML selector fails
            assert result is not None
            assert "fallback" in result.get("extraction_method", "")
            
        finally:
            Path(invalid_file).unlink()
    
    def test_selector_performance_monitoring(self, temp_selector_directory):
        """Test performance monitoring integration."""
        # This test should FAIL initially - performance monitoring not integrated
        from src.selectors.yaml_loader import YAMLSelectorLoader
        from src.selectors.performance_monitor import get_performance_monitor
        
        monitor = get_performance_monitor()
        initial_stats = monitor.get_stats("selector_loading")
        
        # Load selectors
        loader = YAMLSelectorLoader()
        load_result = loader.load_selectors_from_directory(temp_selector_directory)
        
        # Check performance metrics were recorded
        final_stats = monitor.get_stats("selector_loading")
        assert final_stats["total_operations"] > initial_stats.get("total_operations", 0)
        assert final_stats["successful_operations"] >= load_result.selectors_loaded
    
    def test_selector_hot_reload(self, temp_selector_directory):
        """Test hot-reloading of YAML selectors."""
        # This test should FAIL initially - hot reload not implemented
        from src.selectors.yaml_loader import YAMLSelectorLoader
        from src.selectors.registry import SelectorRegistry
        
        loader = YAMLSelectorLoader()
        registry = SelectorRegistry()
        
        # Initial load
        load_result = loader.load_selectors_from_directory(temp_selector_directory)
        for selector_file in Path(temp_selector_directory).glob("*.yaml"):
            selector = loader.load_selector_from_file(str(selector_file))
            registry.register_selector(selector)
        
        initial_count = len(registry.selectors)
        
        # Add new selector file
        new_selector = {
            "id": "new_selector",
            "name": "New Selector",
            "selector_type": "css",
            "pattern": ".new-element",
            "strategies": [
                {
                    "type": "text_anchor",
                    "priority": 1,
                    "config": {"anchor_text": "new"},
                    "confidence_threshold": 0.8,
                    "enabled": True
                }
            ]
        }
        
        new_file = Path(temp_selector_directory) / "new_selector.yaml"
        with open(new_file, 'w') as f:
            yaml.dump(new_selector, f)
        
        # Hot reload
        reload_result = loader.reload_selectors()
        
        # Verify new selector was loaded
        assert reload_result.success is True
        assert len(registry.selectors) > initial_count
    
    def test_selector_error_handling(self, temp_selector_directory):
        """Test error handling in YAML selector operations."""
        # This test should FAIL initially - error handling not implemented
        from src.selectors.yaml_loader import YAMLSelectorLoader
        
        loader = YAMLSelectorLoader()
        
        # Create malformed YAML file
        malformed_file = Path(temp_selector_directory) / "malformed.yaml"
        with open(malformed_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        # Should handle error gracefully
        load_result = loader.load_selectors_from_directory(temp_selector_directory)
        
        assert load_result.success is True  # Continue on error
        assert load_result.selectors_failed > 0
        assert len(load_result.errors) > 0
        assert "malformed.yaml" in str(load_result.errors[0])
    
    def test_selector_validation_integration(self, temp_selector_directory):
        """Test selector validation integration."""
        # This test should FAIL initially - validation integration not implemented
        from src.selectors.yaml_loader import YAMLSelectorLoader
        from src.selectors.validator import SelectorValidator
        
        loader = YAMLSelectorLoader()
        validator = SelectorValidator()
        
        # Load selectors with validation
        selectors = []
        validation_results = []
        
        for selector_file in Path(temp_selector_directory).glob("*.yaml"):
            selector = loader.load_selector_from_file(str(selector_file))
            validation_result = validator.validate_selector(selector)
            validation_results.append(validation_result)
            
            if validation_result.is_valid:
                selectors.append(selector)
        
        # All sample selectors should be valid
        assert all(result.is_valid for result in validation_results)
        assert len(selectors) == 2
    
    def test_selector_caching_integration(self, temp_selector_directory):
        """Test selector caching integration."""
        # This test should FAIL initially - caching not implemented
        from src.selectors.yaml_loader import YAMLSelectorLoader
        
        loader = YAMLSelectorLoader()
        
        # First load
        start_time = pytest.importorskip("time").time()
        load_result1 = loader.load_selectors_from_directory(temp_selector_directory)
        first_load_time = pytest.importorskip("time").time() - start_time
        
        # Second load (should be faster due to caching)
        start_time = pytest.importorskip("time").time()
        load_result2 = loader.load_selectors_from_directory(temp_selector_directory)
        second_load_time = pytest.importorskip("time").time() - start_time
        
        # Both loads should succeed
        assert load_result1.success is True
        assert load_result2.success is True
        assert load_result1.selectors_loaded == load_result2.selectors_loaded
        
        # Second load should be faster (cached)
        assert second_load_time < first_load_time
