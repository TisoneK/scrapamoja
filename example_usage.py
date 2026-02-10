"""
Example usage of the Wikipedia scraper.

This shows how developers would actually use the Site Scraper Template System
in their applications - using the real scraper.py file, not test files.
"""

import asyncio
from playwright.async_api import async_playwright
from src.sites.wikipedia import WikipediaScraper
from src.sites.registry import ScraperRegistry


async def example_usage():
    """Example of how to use the Wikipedia scraper in production."""
    
    # Method 1: Direct usage (most common)
    print("🚀 Method 1: Direct Wikipedia Scraper Usage")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Create Wikipedia scraper directly
        scraper = WikipediaScraper(page, selector_engine=None)  # selector_engine would be real
        
        try:
            # Navigate to Wikipedia
            await scraper.navigate()
            print(f"✅ Navigated to: {page.url}")
            
            # Search for something
            search_data = await scraper.scrape(query="Python programming")
            print(f"✅ Search completed: {search_data.get('total_count', 0)} results")
            
            # Get specific article
            article_data = await scraper.scrape(article_title="Python_(programming_language)")
            print(f"✅ Article scraped: {article_data.get('article_title', 'Unknown')}")
            
            # Normalize data
            normalized = scraper.normalize(search_data)
            print(f"✅ Data normalized: {normalized.get('type', 'unknown')}")
            
        finally:
            await browser.close()
    
    # Method 2: Using Registry (for multiple sites)
    print("\n🚀 Method 2: Using Registry for Multiple Sites")
    print("=" * 50)
    
    # Register scrapers
    registry = ScraperRegistry()
    registry.register("wikipedia", WikipediaScraper)
    
    # List available scrapers
    scrapers = registry.list_scrapers()
    print(f"✅ Available scrapers: {scrapers}")
    
    # Get scraper class from registry
    wikipedia_class = registry.get_scraper("wikipedia")
    print(f"✅ Retrieved scraper class: {wikipedia_class.__name__}")
    
    # Get metadata
    metadata = registry.get_metadata("wikipedia")
    print(f"✅ Site metadata: {metadata.get('name', 'Unknown')}")
    
    # Validate all scrapers
    validation_results = registry.validate_all()
    for site_id, result in validation_results.items():
        status = "✅ Valid" if result.is_valid() else "❌ Invalid"
        print(f"✅ {site_id}: {status} (errors: {len(result.errors)}, warnings: {len(result.warnings)})")


if __name__ == "__main__":
    asyncio.run(example_usage())
