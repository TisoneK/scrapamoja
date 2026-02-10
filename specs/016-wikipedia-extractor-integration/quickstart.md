# Wikipedia Extractor Integration Quickstart Guide

## Overview

This guide helps you integrate the advanced extractor module with the Wikipedia scraper to enhance data extraction capabilities with structured extraction rules, type conversion, and advanced pattern matching.

## Prerequisites

- Complete extractor module implementation (Feature 014)
- Existing Wikipedia scraper (Feature 013)
- Python 3.11+ environment
- Playwright browser automation
- Basic understanding of web scraping concepts

## Installation

### 1. Update Dependencies

Ensure you have the latest extractor module installed:

```bash
pip install beautifulsoup4 lxml python-dateutil pydantic regex
```

### 2. Import Required Modules

```python
from src.sites.wikipedia.scraper import EnhancedWikipediaScraper
from src.sites.wikipedia.extraction.rules import WikipediaExtractionRules
from src.extractor import Extractor, ExtractionRule, ExtractionType, DataType
```

## Basic Usage

### Enhanced Article Scraping

```python
import asyncio
from src.sites.wikipedia.scraper import EnhancedWikipediaScraper
from src.browser.session import BrowserSession

async def scrape_article_with_extraction():
    # Initialize browser session
    async with BrowserSession() as session:
        page = await session.new_page()
        
        # Create enhanced scraper
        scraper = EnhancedWikipediaScraper(page, session.selector_engine)
        
        # Navigate to article
        await scraper.navigate()
        
        # Scrape with enhanced extraction
        result = await scraper.scrape_with_extraction(
            article_title="Python (programming language)"
        )
        
        print(f"Title: {result['title']}")
        print(f"Publication Date: {result['publication_date']}")
        print(f"Word Count: {result['word_count']}")
        print(f"Categories: {result['categories']}")
        print(f"Infobox: {result['infobox']}")

# Run the scraper
asyncio.run(scrape_article_with_extraction())
```

### Search Results with Enhanced Extraction

```python
async def search_with_extraction():
    async with BrowserSession() as session:
        page = await session.new_page()
        scraper = EnhancedWikipediaScraper(page, session.selector_engine)
        
        # Perform search with enhanced extraction
        result = await scraper.scrape_with_extraction(
            query="machine learning"
        )
        
        for search_result in result['results']:
            print(f"Title: {search_result['title']}")
            print(f"Relevance Score: {search_result['relevance_score']}")
            print(f"Article Size: {search_result['article_size']}")
            print(f"Last Modified: {search_result['last_modified']}")

asyncio.run(search_with_extraction())
```

## Configuration

### Custom Extraction Rules

```python
from src.extractor import ExtractionRule, ExtractionType, DataType, TransformationType

# Create custom extraction rules
custom_rules = {
    "article_title": ExtractionRule(
        name="article_title",
        field_path="article_title",
        extraction_type=ExtractionType.TEXT,
        target_type=DataType.TEXT,
        transformations=[TransformationType.TRIM, TransformationType.CLEAN],
        required=True
    ),
    
    "publication_date": ExtractionRule(
        name="publication_date",
        field_path="publication_date",
        extraction_type=ExtractionType.TEXT,
        target_type=DataType.DATE,
        regex_pattern=r"(\d{1,2}\s+\w+\s+\d{4})",
        transformations=[TransformationType.TRIM]
    ),
    
    "word_count": ExtractionRule(
        name="word_count",
        field_path="word_count",
        extraction_type=ExtractionType.TEXT,
        target_type=DataType.INTEGER,
        regex_pattern=r"(\d+)\s+words",
        transformations=[TransformationType.TRIM]
    )
}

# Apply custom rules
scraper.set_extraction_rules(custom_rules)
```

### Validation Configuration

```python
from src.sites.wikipedia.extraction.validators import WikipediaDataValidator

# Configure validation
validator = WikipediaDataValidator()
validator.set_validation_rules({
    "article_title": {"min_length": 1, "max_length": 255},
    "word_count": {"min_value": 0, "max_value": 1000000},
    "publication_date": {"required": False}
})

scraper.set_validator(validator)
```

## Advanced Features

### Infobox Data Extraction

```python
async def extract_infobox_data():
    async with BrowserSession() as session:
        page = await session.new_page()
        scraper = EnhancedWikipediaScraper(page, session.selector_engine)
        
        result = await scraper.scrape_with_extraction(
            article_title="United States"
        )
        
        infobox = result['infobox']
        print(f"Population: {infobox.get('population')}")
        print(f"Area: {infobox.get('area')}")
        print(f"Capital: {infobox.get('capital')}")
        print(f"Coordinates: {infobox.get('coordinates')}")
```

### Table of Contents Processing

```python
async def extract_toc_structure():
    async with BrowserSession() as session:
        page = await session.new_page()
        scraper = EnhancedWikipediaScraper(page, session.selector_engine)
        
        result = await scraper.scrape_with_extraction(
            article_title="Artificial intelligence"
        )
        
        toc = result['table_of_contents']
        for section in toc:
            print(f"Level {section['depth']}: {section['title']}")
            if 'subsections' in section:
                for subsection in section['subsections']:
                    print(f"  Level {subsection['depth']}: {subsection['title']}")
```

### Link Analysis

```python
async def analyze_article_links():
    async with BrowserSession() as session:
        page = await session.new_page()
        scraper = EnhancedWikipediaScraper(page, session.selector_engine)
        
        result = await scraper.scrape_with_extraction(
            article_title="Computer science"
        )
        
        links = result['links']
        print(f"Internal links: {len(links['internal'])}")
        print(f"External links: {len(links['external'])}")
        print(f"References: {len(links['references'])}")
        print(f"Images: {len(links['images'])}")
```

## Error Handling

### Graceful Error Handling

```python
async def scrape_with_error_handling():
    async with BrowserSession() as session:
        page = await session.new_page()
        scraper = EnhancedWikipediaScraper(page, session.selector_engine)
        
        try:
            result = await scraper.scrape_with_extraction(
                article_title="Non-existent Article"
            )
            
            # Check for errors
            if 'errors' in result:
                print("Extraction errors:")
                for error in result['errors']:
                    print(f"  - {error}")
            
            # Check data quality
            if 'quality_metrics' in result:
                quality = result['quality_metrics']
                print(f"Data quality score: {quality['score']}")
                print(f"Completeness: {quality['completeness']}%")
                
        except Exception as e:
            print(f"Scraping failed: {e}")
```

### Default Value Handling

```python
# Configure default values for missing data
scraper.set_default_values({
    "publication_date": None,
    "word_count": 0,
    "categories": [],
    "infobox": {},
    "last_modified": None
})
```

## Performance Optimization

### Caching Configuration

```python
# Enable extraction rule caching
scraper.enable_caching(True)
scraper.set_cache_size(1000)
scraper.set_cache_ttl(3600)  # 1 hour
```

### Concurrent Processing

```python
import asyncio

async def scrape_multiple_articles():
    async with BrowserSession() as session:
        tasks = []
        
        # Create multiple pages for concurrent scraping
        for i in range(5):
            page = await session.new_page()
            scraper = EnhancedWikipediaScraper(page, session.selector_engine)
            
            task = scraper.scrape_with_extraction(
                article_title=f"Article {i+1}"
            )
            tasks.append(task)
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Article {i+1} failed: {result}")
            else:
                print(f"Article {i+1} scraped successfully")

asyncio.run(scrape_multiple_articles())
```

## Testing

### Unit Testing

```python
import pytest
from src.sites.wikipedia.scraper import EnhancedWikipediaScraper

@pytest.mark.asyncio
async def test_article_extraction():
    # Mock page and selector engine
    mock_page = create_mock_page()
    mock_selector_engine = create_mock_selector_engine()
    
    scraper = EnhancedWikipediaScraper(mock_page, mock_selector_engine)
    
    result = await scraper.scrape_with_extraction(
        article_title="Test Article"
    )
    
    assert result['title'] == "Test Article"
    assert isinstance(result['word_count'], int)
    assert len(result['categories']) >= 0
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_end_to_end_extraction():
    async with BrowserSession() as session:
        page = await session.new_page()
        scraper = EnhancedWikipediaScraper(page, session.selector_engine)
        
        result = await scraper.scrape_with_extraction(
            article_title="Python (programming language)"
        )
        
        # Verify extraction quality
        assert result['title'] is not None
        assert result['word_count'] > 0
        assert isinstance(result['infobox'], dict)
        assert len(result['links']['internal']) > 0
```

## Troubleshooting

### Common Issues

1. **Extraction Fails**: Check if article exists and is accessible
2. **Type Conversion Errors**: Verify data formats and regex patterns
3. **Performance Issues**: Enable caching and optimize extraction rules
4. **Memory Usage**: Monitor concurrent processing and cache size

### Debug Mode

```python
# Enable debug logging
scraper.enable_debug_logging(True)
scraper.set_log_level("DEBUG")

# Get extraction statistics
stats = scraper.get_extraction_statistics()
print(f"Total extractions: {stats['total']}")
print(f"Success rate: {stats['success_rate']}%")
print(f"Average time: {stats['avg_time']}ms")
```

## Best Practices

1. **Use Specific Rules**: Create targeted extraction rules for each data type
2. **Validate Results**: Always validate extracted data before use
3. **Handle Errors Gracefully**: Implement proper error handling and fallbacks
4. **Monitor Performance**: Track extraction metrics and optimize as needed
5. **Test Thoroughly**: Test with various article types and edge cases

## Migration Guide

### From Basic Scraper

```python
# Old approach
scraper = WikipediaScraper(page, selector_engine)
result = await scraper.scrape(article_title="Python")

# New approach
scraper = EnhancedWikipediaScraper(page, selector_engine)
result = await scraper.scrape_with_extraction(article_title="Python")
```

### Backward Compatibility

The enhanced scraper maintains full backward compatibility:

```python
# Still works
scraper = EnhancedWikipediaScraper(page, selector_engine)
result = await scraper.scrape(article_title="Python")  # Basic extraction
```

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the test cases for examples
3. Consult the extractor module documentation
4. Check the Wikipedia scraper source code

## Next Steps

1. Configure extraction rules for your specific use case
2. Set up validation and error handling
3. Implement performance optimization
4. Create comprehensive tests
5. Deploy to production with monitoring
