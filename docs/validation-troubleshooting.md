# Validation Troubleshooting Guide

This guide provides comprehensive troubleshooting information for site scraper validation issues.

## Table of Contents

- [Common Validation Errors](#common-validation-errors)
- [File System Issues](#file-system-issues)
- [Configuration Problems](#configuration-problems)
- [Interface Compliance](#interface-compliance)
- [YAML Selector Issues](#yaml-selector-issues)
- [Registry Problems](#registry-problems)
- [Performance Optimization](#performance-optimization)

## Common Validation Errors

### Missing Required Files

**Error**: `Missing required file: config.py`
**Solution**: Create the missing file in your scraper directory

```bash
# Copy from template
cp src/sites/_template/config.py src/sites/your_site/config.py
```

**Required Files**:
- `config.py` - Site configuration
- `flow.py` - Navigation logic
- `scraper.py` - Main scraper implementation
- `selectors/` - Directory for YAML selector files

### Missing Required Directory

**Error**: `Missing required directory: selectors/`
**Solution**: Create the selectors directory

```bash
mkdir -p src/sites/your_site/selectors
```

## File System Issues

### File Permissions

**Error**: Permission denied when accessing files
**Solution**: Check file permissions

```bash
# Ensure files are readable
chmod 644 src/sites/your_site/*.py
chmod 755 src/sites/your_site/selectors/
```

### File Encoding

**Error**: Invalid encoding in YAML files
**Solution**: Ensure UTF-8 encoding

```yaml
# selectors/example.yaml - Save as UTF-8
description: "Example selector"
confidence_threshold: 0.7
strategies:
  - type: "css"
    selector: ".example"
```

## Configuration Problems

### Missing Required Fields

**Error**: `Missing required configuration field: id`
**Solution**: Add missing fields to SITE_CONFIG

```python
# config.py - Add all required fields
SITE_CONFIG = {
    "id": "your_site",           # Required
    "name": "Your Site Name",    # Required
    "base_url": "https://example.com",  # Required
    "version": "1.0.0",         # Required
    "maintainer": "your-email@example.com",  # Required
    "description": "Optional description",
    "tags": ["optional", "tags"]
}
```

### Invalid Site ID Format

**Error**: `Site ID must contain only lowercase letters, numbers, and underscores`
**Solution**: Use valid site ID format

```python
# Valid site IDs
"id": "my_site"
"id": "example_123"
"id": "test_site_v2"

# Invalid site IDs
"id": "MySite"        # Contains uppercase
"id": "my-site"        # Contains hyphen
"id": "my site"       # Contains space
```

### Invalid Base URL

**Error**: `Base URL must start with http:// or https://`
**Solution**: Use proper URL format

```python
# Valid URLs
"base_url": "https://example.com"
"base_url": "http://localhost:8080"

# Invalid URLs
"base_url": "example.com"
"base_url": "ftp://example.com"
```

### Invalid Version Format

**Error**: `Version must follow semantic versioning (e.g., 1.0.0)`
**Solution**: Use semantic versioning

```python
# Valid versions
"version": "1.0.0"
"version": "0.1.0"
"version": "2.3.1"

# Invalid versions
"version": "1.0"
"version": "v1.0.0"
"version": "1.0.0-beta"
```

## Interface Compliance

### Missing Class Attributes

**Error**: `Missing required class attribute: site_id`
**Solution**: Add required class attributes

```python
from src.sites.base.site_scraper import BaseSiteScraper

class YourSiteScraper(BaseSiteScraper):
    site_id = "your_site"        # Required
    site_name = "Your Site Name"  # Required
    base_url = "https://example.com"  # Required
    
    # ... rest of implementation
```

### Missing Required Methods

**Error**: `Missing required method: navigate`
**Solution**: Implement all required abstract methods

```python
class YourSiteScraper(BaseSiteScraper):
    # ... class attributes
    
    async def navigate(self) -> None:
        """Bring page to initial ready state."""
        # Your navigation logic here
        pass
    
    async def scrape(self, **kwargs) -> dict:
        """Perform scraping using selectors."""
        # Your scraping logic here
        return {"data": "example"}
    
    def normalize(self, raw_data: dict) -> dict:
        """Transform raw data into structured output."""
        # Your normalization logic here
        return {"normalized": raw_data}
```

### Method Signature Issues

**Error**: `normalize() method must take exactly one parameter (raw_data)`
**Solution**: Use correct method signatures

```python
# Correct signatures
async def navigate(self) -> None:                    # No parameters besides self
    pass

async def scrape(self, **kwargs) -> dict:               # Accepts **kwargs
    pass

def normalize(self, raw_data: dict) -> dict:           # Takes raw_data parameter
    pass
```

## YAML Selector Issues

### Invalid YAML Syntax

**Error**: `Invalid YAML syntax in example.yaml: mapping values are not allowed here`
**Solution**: Fix YAML syntax

```yaml
# Correct YAML
description: "Search input"
confidence_threshold: 0.7
strategies:
  - type: "css"
    selector: ".search-input"

# Incorrect YAML
description: "Search input"
confidence_threshold: 0.7
strategies: type: "css" selector: ".search-input"  # Wrong syntax
```

### Missing Required Fields

**Error**: `Schema validation failed in example.yaml: 'description' is a required property`
**Solution**: Add required fields

```yaml
# Required fields
description: "Search input field"          # Required
confidence_threshold: 0.7                    # Required
strategies:                                    # Required
  - type: "css"
    selector: ".search-input"
```

### Invalid Strategy Type

**Error**: `Invalid strategy type 'invalid_type' in example.yaml`
**Solution**: Use valid strategy types

```yaml
# Valid strategy types
strategies:
  - type: "css"        # CSS selector
    selector: ".class"
  - type: "xpath"      # XPath expression
    selector: "//div[@class='example']"
  - type: "text"       # Text content matching
    selector: "Search"
  - type: "attribute"   # Attribute value matching
    selector: "data-testid"
  - type: "role"        # ARIA role matching
    selector: "button"
```

### Invalid Confidence Threshold

**Error**: `Invalid confidence_threshold in example.yaml: must be between 0.0 and 1.0`
**Solution**: Use valid confidence range

```yaml
# Valid confidence thresholds
confidence_threshold: 0.7    # Good
confidence_threshold: 0.5    # Minimum acceptable
confidence_threshold: 1.0    # Perfect match

# Invalid confidence thresholds
confidence_threshold: -0.1   # Too low
confidence_threshold: 1.5    # Too high
confidence_threshold: "high"  # Wrong type
```

## Registry Problems

### Duplicate Site ID

**Error**: `Site ID 'example_site' already registered`
**Solution**: Use unique site IDs

```python
# Check existing sites
registry = ScraperRegistry()
print(registry.list_scrapers())

# Use unique ID
registry.register("example_site_v2", YourScraper)
```

### Scraper Not Found

**Error**: `Site 'unknown_site' not found in registry`
**Solution**: Register scraper before using

```python
# Register first
registry.register("your_site", YourScraper)

# Then use
scraper_class = registry.get_scraper("your_site")
```

### Invalid Inheritance

**Error**: `Scraper class must inherit from BaseSiteScraper`
**Solution**: Ensure proper inheritance

```python
# Correct inheritance
from src.sites.base.site_scraper import BaseSiteScraper

class YourScraper(BaseSiteScraper):  # Must inherit from BaseSiteScraper
    pass

# Incorrect inheritance
class YourScraper:  # Missing BaseSiteScraper inheritance
    pass
```

## Performance Optimization

### Validation Caching

Validation results are cached for 5 minutes by default. To clear cache:

```python
# Clear cache for specific site
registry.clear_validation_cache("your_site")

# Clear all cache
registry.clear_validation_cache()
```

### Cache Statistics

Monitor cache performance:

```python
stats = registry.get_cache_stats()
print(f"Cached sites: {stats['total_cached']}")
print(f"Cache TTL: {stats['cache_ttl']} seconds")
```

## Debugging Tips

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Validation will show detailed debug information
results = registry.validate_all()
```

### Use Error Formatter

```python
from src.sites.base.error_formatter import ErrorFormatter

# Get detailed error report
for site_id, result in results.items():
    if not result.is_valid():
        formatted = ErrorFormatter.format_validation_result(site_id, result)
        print(f"Site: {site_id}")
        print(f"Errors: {formatted['errors']}")
        print(f"Actions: {formatted['actions']}")
```

### Validate Individual Components

```python
from src.sites.base.validation import FileValidator, ConfigurationValidator

# Validate files only
from pathlib import Path
file_result = FileValidator.validate_required_files(Path("src/sites/your_site"))

# Validate configuration only
config_result = ConfigurationValidator.validate_site_config(SITE_CONFIG)
```

## Getting Help

If you encounter issues not covered in this guide:

1. Check the [API documentation](../contracts/)
2. Review the [quickstart guide](../sites/_template/README.md)
3. Examine example implementations in `src/sites/wikipedia/` and `src/sites/flashscore/`
4. Enable debug logging for detailed error information

## Common Mistakes to Avoid

1. **Forgetting to inherit from BaseSiteScraper**
2. **Using incorrect site ID format**
3. **Missing required configuration fields**
4. **Invalid YAML syntax in selector files**
5. **Not implementing all required abstract methods**
6. **Using wrong method signatures**
7. **Forgetting to create the selectors/ directory**

Remember: Validation errors are designed to help you create robust, compliant scrapers. Follow the guidance provided and your scrapers will work reliably with the framework.
