# Quick Start Guide: Enhanced Site Scraper Template System

**Created**: 2025-01-29  
**Purpose**: Getting started guide for developers using the modular template system

## Overview

The Enhanced Site Scraper Template System provides a modular, component-based architecture for creating robust, maintainable web scrapers. This guide will help you get started quickly.

## Prerequisites

- Python 3.11+
- Playwright installed (`pip install playwright`)
- Existing selector engine and browser lifecycle components
- Basic understanding of async/await patterns

## Quick Start: Creating Your First Modular Scraper

### Step 1: Copy the Template

```bash
# Copy the enhanced template
cp -r src/sites/_template src/sites/my_site

# Navigate to your new site directory
cd src/sites/my_site
```

### Step 2: Configure Your Site

Edit `config/base.py`:

```python
# config/base.py
SITE_CONFIG = {
    "id": "my_site",
    "name": "My Website",
    "base_url": "https://example.com",
    "version": "1.0.0",
    "maintainer": "your-email@example.com",
    "description": "My custom website scraper",
    "tags": ["custom", "example"]
}
```

### Step 3: Implement Navigation Flows

Create `flows/search_flow.py`:

```python
# flows/search_flow.py
from ..flows.base_flow import BaseFlow
from typing import Dict, Any

class SearchFlow(BaseFlow):
    """Search navigation flow for my site."""
    
    async def execute_search(self, query: str) -> Dict[str, Any]:
        """Execute search with given query."""
        # Navigate to search page
        await self.page.goto(f"{self.base_url}/search")
        
        # Fill search form
        await self.page.fill("#search-input", query)
        await self.page.click("#search-button")
        
        # Wait for results
        await self.page.wait_for_selector(".search-results")
        
        return {
            "query": query,
            "url": self.page.url,
            "results_found": True
        }
```

### Step 4: Create Data Processors

Create `processors/normalizer.py`:

```python
# processors/normalizer.py
from typing import Dict, Any

class DataNormalizer:
    """Data normalization processor."""
    
    def normalize_search_results(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize search results data."""
        return {
            "type": "search_results",
            "query": raw_data.get("query"),
            "result_count": len(raw_data.get("results", [])),
            "results": [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "snippet": item.get("snippet")
                }
                for item in raw_data.get("results", [])
            ],
            "timestamp": raw_data.get("timestamp")
        }
```

### Step 5: Implement Main Scraper

Edit `scraper.py`:

```python
# scraper.py
from src.sites.base.site_scraper import BaseSiteScraper
from .flows.search_flow import SearchFlow
from .processors.normalizer import DataNormalizer
from .config.base import SITE_CONFIG

class MySiteScraper(BaseSiteScraper):
    """My Site scraper implementation."""
    
    site_id = SITE_CONFIG["id"]
    site_name = SITE_CONFIG["name"]
    base_url = SITE_CONFIG["base_url"]
    
    def __init__(self, page, selector_engine):
        super().__init__(page, selector_engine)
        self.search_flow = SearchFlow(page, selector_engine)
        self.normalizer = DataNormalizer()
    
    async def navigate(self):
        """Navigate to site home page."""
        await self.page.goto(self.base_url)
    
    async def scrape(self, **kwargs):
        """Scrape data from the site."""
        if "query" in kwargs:
            # Search scraping
            search_results = await self.search_flow.execute_search(kwargs["query"])
            return self.normalizer.normalize_search_results(search_results)
        else:
            # Home page scraping
            return await self.scrape_home_page()
    
    async def scrape_home_page(self):
        """Scrape home page data."""
        title = await self.page.title()
        return {
            "type": "home_page",
            "title": title,
            "url": self.page.url
        }
    
    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize scraped data."""
        if raw_data.get("type") == "search_results":
            return self.normalizer.normalize_search_results(raw_data)
        return raw_data
```

### Step 6: Test Your Scraper

Create a simple test script:

```python
# test_my_scraper.py
import asyncio
from playwright.async_api import async_playwright
from src.sites.my_site.scraper import MySiteScraper

async def test_my_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Create scraper instance
        scraper = MySiteScraper(page, selector_engine=None)
        
        try:
            # Navigate to site
            await scraper.navigate()
            print(f"Navigated to: {page.url}")
            
            # Scrape search results
            results = await scraper.scrape(query="python programming")
            print(f"Search results: {results}")
            
            # Normalize data
            normalized = scraper.normalize(results)
            print(f"Normalized: {normalized}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_my_scraper())
```

## Advanced Features

### Using Reusable Components

#### Authentication Component

```python
# components/oauth_auth.py
from src.sites.shared_components.authentication.oauth import OAuthComponent

class MySiteScraper(BaseSiteScraper):
    def __init__(self, page, selector_engine):
        super().__init__(page, selector_engine)
        self.auth = OAuthComponent(
            client_id="your-client-id",
            client_secret="your-client-secret",
            redirect_uri="https://example.com/callback"
        )
    
    async def login(self):
        """Login using OAuth."""
        await self.auth.authenticate(self.page)
```

#### Rate Limiting Component

```python
# components/rate_limiter.py
from src.sites.shared_components.rate_limiting.rate_limiter import RateLimiter

class MySiteScraper(BaseSiteScraper):
    def __init__(self, page, selector_engine):
        super().__init__(page, selector_engine)
        self.rate_limiter = RateLimiter(
            requests_per_minute=60,
            burst_size=10
        )
    
    async def scrape_with_rate_limit(self, **kwargs):
        """Scrape with rate limiting."""
        async with self.rate_limiter:
            return await self.scrape(**kwargs)
```

### Multi-Environment Configuration

#### Development Configuration

```python
# config/dev.py
from .base import SITE_CONFIG

DEV_CONFIG = {
    **SITE_CONFIG,
    "environment": "dev",
    "rate_limit": {
        "requests_per_minute": 10,
        "burst_size": 5
    },
    "debug": True,
    "feature_flags": {
        "enable_verbose_logging": True,
        "enable_debug_ui": True
    }
}
```

#### Production Configuration

```python
# config/prod.py
from .base import SITE_CONFIG

PROD_CONFIG = {
    **SITE_CONFIG,
    "environment": "prod",
    "rate_limit": {
        "requests_per_minute": 120,
        "burst_size": 20
    },
    "stealth": {
        "user_agent_rotation": True,
        "mouse_movement": True,
        "randomized_timing": True
    },
    "feature_flags": {
        "enable_monitoring": True,
        "enable_caching": True
    }
}
```

### Plugin System

#### Creating a Plugin

```python
# plugins/custom_validator.py
from src.sites.base.plugin_manager import BasePlugin

class CustomValidatorPlugin(BasePlugin):
    """Custom data validation plugin."""
    
    def __init__(self):
        super().__init__(
            plugin_id="custom_validator",
            name="Custom Validator",
            version="1.0.0"
        )
    
    async def pre_process_hook(self, context, data):
        """Pre-processing validation hook."""
        if not data.get("query"):
            raise ValueError("Query parameter is required")
        return data
    
    async def post_process_hook(self, context, result):
        """Post-processing validation hook."""
        if not result.get("results"):
            context.logger.warning("No results found")
        return result
```

#### Using the Plugin

```python
# scraper.py
from plugins.custom_validator import CustomValidatorPlugin

class MySiteScraper(BaseSiteScraper):
    def __init__(self, page, selector_engine):
        super().__init__(page, selector_engine)
        self.plugin_manager.register_plugin(CustomValidatorPlugin())
```

## Best Practices

### 1. Component Organization

- Keep components small and focused
- Use clear naming conventions
- Document component interfaces
- Test components independently

### 2. Configuration Management

- Use environment-specific configurations
- Validate configurations on load
- Use feature flags for optional functionality
- Keep sensitive data out of configuration files

### 3. Error Handling

- Implement graceful error handling
- Use structured logging
- Provide meaningful error messages
- Implement retry logic for transient failures

### 4. Performance

- Use lazy loading for components
- Cache expensive operations
- Monitor component performance
- Use async/await consistently

## Troubleshooting

### Common Issues

#### Component Not Found

**Error**: `ComponentNotFoundError: Component 'xyz' not found`

**Solution**: 
- Check component registration
- Verify component ID spelling
- Ensure component is in correct directory

#### Configuration Validation Failed

**Error**: `ConfigurationValidationError: Invalid configuration`

**Solution**:
- Check configuration schema
- Verify required fields
- Check data types

#### Plugin Loading Failed

**Error**: `PluginLoadError: Failed to load plugin`

**Solution**:
- Check plugin dependencies
- Verify plugin permissions
- Check plugin entry point

### Getting Help

1. Check the documentation in `docs/`
2. Look at example scrapers in `examples/`
3. Check logs for detailed error messages
4. Use the validation tools to diagnose issues

## Migration from Flat Template

If you have an existing scraper using the flat template, follow these steps:

### 1. Backup Existing Scraper

```bash
cp -r src/sites/old_site src/sites/old_site_backup
```

### 2. Create New Modular Structure

```bash
cp -r src/sites/_template src/sites/old_site_modular
```

### 3. Migrate Components

- Move flow logic to `flows/` directory
- Move configuration to `config/` directory
- Move data processing to `processors/` directory
- Update main scraper to use components

### 4. Test Migration

- Run existing tests
- Verify functionality
- Update tests as needed

### 5. Update References

- Update import statements
- Update registry entries
- Update documentation

## Next Steps

1. **Explore Components**: Browse the shared components library
2. **Create Custom Components**: Build reusable components for your needs
3. **Implement Plugins**: Extend functionality with plugins
4. **Configure Environments**: Set up dev/staging/prod configurations
5. **Monitor Performance**: Use built-in monitoring tools

## Resources

- [API Documentation](contracts/modular-template-api.md)
- [Data Model Reference](data-model.md)
- [Component Library](../shared_components/)
- [Example Scrapers](../../examples/)
- [Troubleshooting Guide](../docs/troubleshooting.md)

**Status**: ✅ Quick start guide complete, ready for developer onboarding
