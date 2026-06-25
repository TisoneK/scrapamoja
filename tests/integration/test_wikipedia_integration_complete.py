"""
Integration test for complete Wikipedia YAML selector integration.

This test verifies that the integration bridge properly connects all components
and resolves the critical blocking issue where YAML selectors are not loaded into the selector engine.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from pathlib import Path

from src.sites.wikipedia.scraper import WikipediaScraper
from src.sites.wikipedia.integration_bridge import WikipediaIntegrationBridge, initialize_wikipedia_integration
from src.selectors.engine import SelectorEngine


class TestWikipediaIntegrationComplete:
    """Test complete Wikipedia integration with YAML selector loading."""
    
    @pytest.mark.asyncio
    async def test_complete_integration_bridge_initialization(self):
        """Test that the complete integration bridge initializes correctly."""
        # Create mock objects
        mock_page = AsyncMock()
        mock_selector_engine = AsyncMock()
        
        # Create integration bridge
        bridge = WikipediaSelectorIntegration(mock_selector_engine)
        
        # Mock the underlying integration components
        with patch.object(bridge, 'yaml_integration') as mock_yaml_integration:
            mock_yaml_integration.initialize_wikipedia_selectors.return_value = True
            mock_yaml_integration.get_integration_status.return_value = {
                "initialized": True,
                "total_engine_selectors": 5,
                "engine_selectors": ["article_title", "article_content", "search_results", "infobox_rows", "toc_sections"]
            }
        
        with patch.object(bridge, 'config_integration') as mock_config_integration:
            mock_config_integration.initialize.return_value = None
            mock_config_integration._is_initialized = True
        
        # Test initialization
        result = await bridge.initialize_complete_integration()
        
        assert result is True
        assert bridge.is_initialized()
        assert bridge._yaml_selectors_initialized is True
        assert bridge.complete_integration is not None
        
        # Verify integration status
        status = bridge.get_integration_status()
        assert status["yaml"]["initialized"] is True
        assert status["config"]["initialized"] is True
        assert status["engine"]["total_engine_selectors"] == 5
    
    @pytest.mark.asyncio
    async def test_dom_context_bridge_integration(self):
        """Test that DOM context bridge is properly integrated with extraction flow."""
        # Create mock objects
        mock_page = AsyncMock()
        mock_selector_engine = AsyncMock()
        
        # Create integration bridge
        bridge = WikipediaSelectorIntegration(mock_selector_engine)
        
        # Mock the integration initialization
        with patch.object(bridge, 'initialize_complete_integration') as mock_init:
            mock_init.return_value = True
            mock_init.return_value.is_initialized = True
            mock_init.return_value.get_dom_context_bridge.return_value = lambda page, url, context: {
                "page": page,
                "url": url,
                "context": context,
                "timestamp": "2026-01-29T23:00:00Z"
            }
        
        # Test initialization
        result = await bridge.initialize_complete_integration()
        
        assert result is True
        assert bridge.get_dom_context_bridge() is not None
        
        # Test DOM context bridge function
        bridge_func = bridge.get_dom_context_bridge()
        mock_page.return_value = "mock_page"
        
        # Test bridge function call
        dom_context = bridge_func(mock_page, "https://en.wikipedia.org/wiki/Test", "test_context")
        
        # Verify DOM context structure
        assert dom_context["page"] == "mock_page"
        assert dom_context["url"] == "https://en.wikipedia.org/wiki/Test"
        assert dom_context["tab_context"] == "test_context"
        assert "timestamp" in dom_context
    
    @pytest.mark.asyncio
    async def test_wikipedia_scraper_with_complete_integration(self):
        """Test Wikipedia scraper with complete integration."""
        # Create mock objects
        mock_page = AsyncMock()
        mock_selector_engine = SelectorEngine()
        
        # Create Wikipedia scraper
        scraper = WikipediaScraper(mock_page, mock_selector_engine)
        
        # Mock the integration bridge
        with patch.object(scraper, 'initialize_yaml_selectors') as mock_init:
            mock_init.return_value = True
        
        # Test scraping
        result = await scraper.scrape(article_title="Test_Article")
        
        # Verify the scraper was initialized with integration
        assert scraper._yaml_selectors_initialized is True
        assert scraper.complete_integration is not None
        
        # Verify result structure
        assert "article_title" in result
        assert "content" in result
        assert "scraped_at" in result
    
    @pytest.mark.asyncio
    async def test_integration_error_handling(self):
        """Test error handling in integration bridge."""
        # Create mock objects
        mock_page = AsyncMock()
        mock_selector_engine = AsyncMock()
        
        # Create integration bridge
        bridge = WikipediaSelectorIntegration(mock_selector_engine)
        
        # Mock YAML integration failure
        with patch.object(bridge, 'yaml_integration') as mock_yaml_integration:
            mock_yaml_integration.initialize_wikipedia_selectors.return_value = False
        
        # Test initialization failure
        result = await bridge.initialize_complete_integration()
        
        assert result is False
        assert not bridge.is_initialized()
        assert bridge.complete_integration is None
        
        # Check error status
        status = bridge.get_integration_status()
        assert not status["yaml"]["initialized"]
    
    @pytest.mark.asyncio
    async def test_selector_engine_integration(self):
        """Test that selector engine receives registered selectors."""
        # Create mock objects
        mock_page = AsyncMock()
        mock_selector_engine = AsyncMock()
        
        # Create integration bridge
        bridge = WikipediaSelectorIntegration(mock_selector_engine)
        
        # Mock the integration to simulate loaded selectors
        with patch.object(bridge, 'initialize_complete_integration') as mock_init:
            mock_init.return_value = True
            mock_init.return_value.get_integration_status.return_value = {
                "yaml": {"initialized": True, "total_engine_selectors": 3},
                "engine": {"total_selectors": 3, "registered_selectors": ["article_title", "article_content", "search_results"]}
            }
        
        # Mock selector engine registration
        with patch.object(mock_selector_engine, 'register_selector') as mock_register:
            mock_register.return_value = True
        
        # Test initialization
        result = await bridge.initialize_complete_integration()
        
        assert result is True
        
        # Verify that register_selector was called
        mock_register.assert_called()
        
        # Check that integration status shows selectors
        status = bridge.get_integration_status()
        assert status["engine"]["total_selectors"] == 3
        assert "article_title" in status["engine"]["registered_selectors"]
        assert "article_content" in status["engine"]["registered_selectors"]
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self):
        """Test that performance monitoring works through integration."""
        # Create mock objects
        mock_page = AsyncMock()
        mock_selector_engine = AsyncMock()
        
        # Create integration bridge
        bridge = WikipediaSelectorIntegration(mock_selector_engine)
        
        # Mock performance monitoring
        with patch.object(bridge, 'initialize_complete_integration') as mock_init:
            mock_init.return_value = True
            mock_init.return_value.get_integration_status.return_value = {
                "yaml": {"initialized": True, "total_engine_selectors": 4},
                "engine": {
                    "total_selectors": 4,
                    "registered_selectors": ["article_title", "integration_test", "article_content", "search_results"],
                    "performance_monitor_active": True
                }
            }
        
        # Test initialization
        result = await bridge.initialize_complete_integration()
        
        assert result is True
        
        # Verify performance monitoring is active
        status = bridge.get_integration_status()
        assert status["engine"]["performance_monitor_active"] is True


# Test data for mocking
MOCK_YAML_SELECTORS = {
    "article_title.yaml": {
        "description": "Wikipedia article title selector",
        "confidence_threshold": 0.9,
        "strategies": [
            {
                "type": "css",
                "selector": "#firstHeading",
                "weight": 1.0
            }
        ]
    },
    "article_content.yaml": {
        "description": "Wikipedia article content selector",
        "confidence_threshold": 0.8,
        "strategies": [
            {
                "type": "css",
                "selector": "#mw-content-text",
                "weight": 1.0
            }
        ]
    },
    "search_results.yaml": {
        "description": "Wikipedia search results selector",
        "confidence_threshold": 0.7,
        "strategies": [
            {
                "type": "css",
                "selector": ".mw-search-results",
                "weight": 1.0
            }
        ]
    }
}


if __name__ == "__main__":
    pytest.main([__file__])
