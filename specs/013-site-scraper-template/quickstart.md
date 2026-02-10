# Quick Start Guide: Site Scraper Template System

**Feature**: 013-site-scraper-template  
**Date**: 2025-01-29  
**Purpose**: Developer onboarding guide for adding new site scrapers

## Overview

The site scraper template system enables developers to add new website support by copying a template folder and filling in configuration, without modifying core framework code. This guide walks you through creating your first scraper.

## Prerequisites

- Python 3.11+
- Understanding of async/await patterns
- Basic knowledge of Playwright
- Familiarity with YAML configuration
- Understanding of web scraping concepts

## Step 1: Copy the Template

```bash
# Navigate to the sites directory
cd src/sites

# Copy the template to your new site
cp -r _template my_site

# Navigate to your new site directory
cd my_site
```

## Step 2: Configure Site Metadata

Edit `config.py` to define your site:

```python
SITE_CONFIG = {
    "id": "my_site",
    "name": "My Target Site",
    "base_url": "https://example.com",
    "version": "1.0.0",
    "maintainer": "your-email@example.com",
    "description": "Scraper for extracting data from Example.com",
    "tags": ["example", "demo", "tutorial"]
}
```

**Important**: The `id` must be unique and match your folder name (lowercase, underscores only).

## Step 3: Define Selectors

Create YAML selector files in the `selectors/` directory:

```yaml
# selectors/search_input.yaml
description: "Main search input field"
confidence_threshold: 0.7
strategies:
  - type: "css"
    selector: "input[type='search']"
    weight: 1.0
  - type: "xpath"
    selector: "//input[@type='search']"
    weight: 0.8
```

```yaml
# selectors/search_results.yaml
description: "Search results container"
confidence_threshold: 0.6
strategies:
  - type: "css"
    selector: ".search-results"
    weight: 1.0
  - type: "text"
    selector: "Results"
    weight: 0.5
```

## Step 4: Implement Navigation Flow

Edit `flow.py` to handle navigation logic:

```python
from sites.base.flow import BaseFlow

class MySiteFlow(BaseFlow):
    async def open_home(self):
        """Navigate to the home page."""
        await self.page.goto(self.base_url)
        await self.page.wait_for_load_state('networkidle')
    
    async def perform_search(self, query: str):
        """Perform a search query."""
        # Find search input using selector engine
        search_input = await self.selector_engine.find(
            self.page, "search_input"
        )
        
        # Type search query
        await search_input.clear()
        await search_input.type(query)
        
        # Submit search (click button or press Enter)
        await search_input.press('Enter')
        
        # Wait for results
        await self.page.wait_for_selector(
            lambda: self.selector_engine.find(self.page, "search_results"),
            timeout=10000
        )
```

## Step 5: Implement Main Scraper

Edit `scraper.py` to orchestrate the scraping:

```python
from sites.base.site_scraper import BaseSiteScraper
from .flow import MySiteFlow
from .config import SITE_CONFIG

class MySiteScraper(BaseSiteScraper):
    site_id = SITE_CONFIG["id"]
    site_name = SITE_CONFIG["name"]
    base_url = SITE_CONFIG["base_url"]

    def __init__(self, page, selector_engine):
        super().__init__(page, selector_engine)
        self.flow = MySiteFlow(page, selector_engine)

    async def navigate(self):
        """Navigate to initial state."""
        await self.flow.open_home()

    async def scrape(self, query: str):
        """Perform scraping with given parameters."""
        # Navigate to search
        await self.flow.perform_search(query)
        
        # Extract data using selectors
        results_container = await self.selector_engine.find(
            self.page, "search_results"
        )
        
        # Extract individual results
        results = await self.selector_engine.extract_all(
            self.page, "search_result_items"
        )
        
        return {
            "query": query,
            "results": results,
            "total_count": len(results)
        }

    def normalize(self, raw_data):
        """Normalize raw data to standard format."""
        return {
            "site": self.site_id,
            "timestamp": datetime.utcnow().isoformat(),
            "query": raw_data["query"],
            "results": [
                {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "description": result.get("description", "")
                }
                for result in raw_data["results"]
            ],
            "total_count": raw_data["total_count"]
        }
```

## Step 6: Register Your Scraper

Add your scraper to `src/sites/registry.py`:

```python
from sites.my_site.scraper import MySiteScraper

SCRAPER_REGISTRY = {
    # Existing scrapers...
    "my_site": MySiteScraper,
}

def get_scraper(site_id: str):
    if site_id not in SCRAPER_REGISTRY:
        raise KeyError(f"Unknown site scraper: {site_id}")
    return SCRAPER_REGISTRY[site_id]
```

## Step 7: Test Your Scraper

Create a simple test script:

```python
import asyncio
from playwright.async_api import async_playwright
from src.sites.registry import get_scraper
from src.selector_engine import SelectorEngine

async def test_my_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Initialize selector engine
        selector_engine = SelectorEngine()
        
        # Get scraper instance
        scraper_class = get_scraper("my_site")
        scraper = scraper_class(page, selector_engine)
        
        try:
            # Navigate to site
            await scraper.navigate()
            
            # Perform scraping
            raw_data = await scraper.scrape(query="python programming")
            
            # Normalize data
            normalized_data = scraper.normalize(raw_data)
            
            print("Scraping successful!")
            print(f"Found {normalized_data['total_count']} results")
            
        finally:
            await browser.close()

# Run the test
asyncio.run(test_my_scraper())
```

## Step 8: Validation

The system automatically validates your scraper at startup:

```python
from src.sites.registry import ScraperRegistry

# Create registry and validate all scrapers
registry = ScraperRegistry()
registry.register("my_site", MySiteScraper)

# Validate your scraper
validation_result = registry.validate_scraper("my_site")
if validation_result.is_valid():
    print("✅ Scraper validation passed!")
else:
    print("❌ Validation errors:")
    for error in validation_result.errors:
        print(f"  - {error}")
```

## Best Practices

### Selector Design

1. **Use multiple strategies**: Always provide fallback selectors
2. **Set appropriate confidence thresholds**: 0.7+ for critical elements, 0.5+ for optional
3. **Be specific**: Use semantic selectors over brittle CSS classes
4. **Test thoroughly**: Verify selectors work across different page states

### Navigation Flow

1. **Keep it simple**: Flow classes should only handle navigation
2. **Wait properly**: Use explicit waits for dynamic content
3. **Handle errors**: Implement proper error handling for navigation failures
4. **Log actions**: Add structured logging for debugging

### Data Extraction

1. **Extract raw data**: Keep scraping logic separate from normalization
2. **Handle missing data**: Gracefully handle cases where elements aren't found
3. **Validate output**: Ensure normalized data matches expected schema
4. **Performance**: Avoid unnecessary waits and redundant operations

### Error Handling

1. **Use specific exceptions**: Use NavigationError, ScrapingError, etc.
2. **Provide context**: Include relevant context in error messages
3. **Log appropriately**: Use structured logging with correlation IDs
4. **Fail gracefully**: Allow partial success when possible

## Common Patterns

### Pagination

```python
async def scrape_all_results(self, query: str):
    """Scrape all paginated results."""
    all_results = []
    
    await self.flow.perform_search(query)
    
    while True:
        # Extract current page results
        page_results = await self.scrape_current_page()
        all_results.extend(page_results)
        
        # Check for next page
        if await self.flow.has_next_page():
            await self.flow.go_to_next_page()
        else:
            break
    
    return {"results": all_results, "total_count": len(all_results)}
```

### Authentication

```python
async def navigate(self):
    """Navigate with authentication."""
    await self.flow.open_home()
    
    # Check if already logged in
    if not await self.flow.is_logged_in():
        await self.flow.login(username, password)
    
    # Navigate to target page
    await self.flow.go_to_target_page()
```

### Rate Limiting

```python
async def scrape_with_delay(self, **kwargs):
    """Scrape with rate limiting."""
    import asyncio
    
    # Add delay between requests
    await asyncio.sleep(1.0)
    
    # Perform scraping
    return await super().scrape(**kwargs)
```

## Troubleshooting

### Common Issues

1. **Selector not found**: Check confidence thresholds and strategy order
2. **Navigation timeout**: Increase wait times or use different wait conditions
3. **Validation errors**: Ensure all required files and attributes are present
4. **Import errors**: Verify module structure and __init__.py files

### Debug Tips

1. **Use headful mode**: Set `headless=False` for visual debugging
2. **Add logging**: Use structured logging to trace execution
3. **Take screenshots**: Capture screenshots on failures
4. **Validate selectors**: Test selectors individually before integration

## Next Steps

1. **Add comprehensive tests**: Create unit and integration tests
2. **Document your selectors**: Add comments to YAML files
3. **Handle edge cases**: Implement robust error handling
4. **Monitor performance**: Track scraping success rates and timing
5. **Contribute back**: Share improvements with the community

## Support

- Check existing scrapers in `src/sites/` for reference implementations
- Review the API contracts in `specs/013-site-scraper-template/contracts/`
- Consult the data model documentation for detailed entity definitions
- Use the validation system to catch issues early
