"""
Integration tests for site scraper registry.

Tests the complete registry functionality including registration,
validation, discovery, and error handling.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.sites.registry import ScraperRegistry
from src.sites.base.site_scraper import BaseSiteScraper
from src.sites.exceptions import RegistryError, ValidationError


class MockScraper(BaseSiteScraper):
    """Mock scraper for testing."""
    site_id = "test_site"
    site_name = "Test Site"
    base_url = "https://test.com"
    
    async def navigate(self):
        pass
    
    async def scrape(self, **kwargs):
        return {"test": "data"}
    
    def normalize(self, raw_data):
        return {"normalized": raw_data}


class InvalidScraper:
    """Invalid scraper that doesn't inherit from BaseSiteScraper."""
    site_id = "invalid_site"
    site_name = "Invalid Site"
    base_url = "https://invalid.com"


class TestScraperRegistry:
    """Test suite for ScraperRegistry functionality."""
    
    def setup_method(self):
        """Set up test registry before each test."""
        self.registry = ScraperRegistry()
    
    def test_register_valid_scraper(self):
        """Test registering a valid scraper."""
        # Should not raise any exceptions
        self.registry.register("test_site", MockScraper)
        
        # Verify scraper is registered
        assert "test_site" in self.registry.list_scrapers()
        assert self.registry.get_scraper("test_site") == MockScraper
    
    def test_register_duplicate_site_id(self):
        """Test registering duplicate site ID raises error."""
        self.registry.register("test_site", MockScraper)
        
        # Should raise RegistryError for duplicate ID
        with pytest.raises(RegistryError, match="already registered"):
            self.registry.register("test_site", MockScraper)
    
    def test_register_invalid_inheritance(self):
        """Test registering scraper without BaseSiteScraper inheritance."""
        # Should raise RegistryError for invalid inheritance
        with pytest.raises(RegistryError, match="must inherit from BaseSiteScraper"):
            self.registry.register("invalid_site", InvalidScraper)
    
    def test_get_nonexistent_scraper(self):
        """Test getting non-existent scraper raises error."""
        with pytest.raises(RegistryError, match="not found in registry"):
            self.registry.get_scraper("nonexistent")
    
    def test_get_nonexistent_metadata(self):
        """Test getting non-existent metadata raises error."""
        with pytest.raises(RegistryError, match="not found in registry"):
            self.registry.get_metadata("nonexistent")
    
    def test_list_scrapers_empty(self):
        """Test listing scrapers when registry is empty."""
        assert self.registry.list_scrapers() == []
    
    def test_list_scrapers_with_data(self):
        """Test listing scrapers with registered scrapers."""
        self.registry.register("test_site", MockScraper)
        self.registry.register("test_site_2", MockScraper)
        
        scrapers = self.registry.list_scrapers()
        assert len(scrapers) == 2
        assert "test_site" in scrapers
        assert "test_site_2" in scrapers
    
    def test_validate_all_empty(self):
        """Test validating all scrapers when registry is empty."""
        results = self.registry.validate_all()
        assert results == {}
    
    def test_validate_all_with_valid_scrapers(self):
        """Test validating all scrapers with valid registrations."""
        self.registry.register("test_site", MockScraper)
        
        results = self.registry.validate_all()
        assert len(results) == 1
        assert "test_site" in results
        assert results["test_site"].is_valid()
    
    def test_validate_nonexistent_scraper(self):
        """Test validating non-existent scraper."""
        result = self.registry.validate_scraper("nonexistent")
        assert not result.is_valid()
        assert "not found in registry" in result.errors[0]
    
    def test_get_metadata_for_registered_scraper(self):
        """Test getting metadata for registered scraper."""
        self.registry.register("test_site", MockScraper)
        
        metadata = self.registry.get_metadata("test_site")
        assert metadata["id"] == "test_site"
        assert metadata["name"] == "Test Site"
        assert metadata["base_url"] == "https://test.com"
    
    def test_validation_caching(self):
        """Test that validation results are cached."""
        self.registry.register("test_site", MockScraper)
        
        # First validation should compute result
        result1 = self.registry.validate_scraper("test_site")
        
        # Second validation should use cached result
        result2 = self.registry.validate_scraper("test_site")
        
        # Results should be the same object (cached)
        assert result1 is result2
    
    def test_multiple_scraper_registration(self):
        """Test registering multiple different scrapers."""
        # Create mock scrapers with different site IDs
        class MockScraper1(MockScraper):
            site_id = "test_site_1"
            site_name = "Test Site 1"
            base_url = "https://test1.com"
        
        class MockScraper2(MockScraper):
            site_id = "test_site_2"
            site_name = "Test Site 2"
            base_url = "https://test2.com"
        
        # Register both scrapers
        self.registry.register("test_site_1", MockScraper1)
        self.registry.register("test_site_2", MockScraper2)
        
        # Verify both are registered
        scrapers = self.registry.list_scrapers()
        assert len(scrapers) == 2
        assert "test_site_1" in scrapers
        assert "test_site_2" in scrapers
        
        # Verify metadata for both
        metadata1 = self.registry.get_metadata("test_site_1")
        metadata2 = self.registry.get_metadata("test_site_2")
        
        assert metadata1["id"] == "test_site_1"
        assert metadata2["id"] == "test_site_2"
        assert metadata1["name"] == "Test Site 1"
        assert metadata2["name"] == "Test Site 2"


if __name__ == "__main__":
    pytest.main([__file__])
