# Site Scraper Framework

A template-driven system for creating and managing website scrapers with zero core framework modifications.

## Overview

The Site Scraper Framework enables developers to add new websites by copying a template folder, filling YAML selectors, and writing minimal Python glue code. No deep knowledge of BrowserManager, selectors internals, or lifecycle is required.

## Quick Start

### 1. Copy the Template

```bash
cp -r src/sites/_template src/sites/your_site_name
```

### 2. Update Configuration

Edit `src/sites/your_site_name/config.py`:

```python
SITE_CONFIG = {
    "id": "your_site_name",
    "name": "Your Site Name",
    "base_url": "https://example.com",
    "version": "1.0.0",
    "maintainer": "your-email@example.com",
    "description": "Brief description of your scraper",
    "tags": ["category1", "category2"]
}
```

### 3. Implement Required Methods

Edit `src/sites/your_site_name/scraper.py`:

```python
from src.sites.base.site_scraper import BaseSiteScraper
from .flow import YourSiteFlow
from .config import SITE_CONFIG

class YourSiteScraper(BaseSiteScraper):
    site_id = SITE_CONFIG["id"]
    site_name = SITE_CONFIG["name"]
    base_url = SITE_CONFIG["base_url"]

    def __init__(self, page, selector_engine):
        super().__init__(page, selector_engine)
        self.flow = YourSiteFlow(page, selector_engine)

    async def navigate(self):
        await self.flow.open_home()

    async def scrape(self, **kwargs):
        # Your scraping logic here
        return {"data": "example"}

    def normalize(self, raw_data):
        return {"normalized": raw_data}
```

### 4. Define Selectors

Create YAML files in `src/sites/your_site_name/selectors/`:

```yaml
# selectors/search_input.yaml
description: "Search input field"
confidence_threshold: 0.7
strategies:
  - type: "css"
    selector: "input[type='search']"
    weight: 1.0
  - type: "xpath"
    selector: "//input[@type='search']"
    weight: 0.8
```

### 5. Register Your Scraper

Add to `src/sites/registry.py`:

```python
from src.sites.your_site_name.scraper import YourSiteScraper

# In your registry initialization
registry.register("your_site_name", YourSiteScraper)
```

## Architecture

### Core Components

- **BaseSiteScraper**: Abstract base class defining the scraper contract
- **BaseFlow**: Abstract base class for navigation-only logic
- **ScraperRegistry**: Central registry for discovery and management
- **Validation System**: Comprehensive validation with helpful error messages

### Template Structure

```
src/sites/_template/
├── __init__.py          # Module initialization
├── config.py           # Site configuration (SITE_CONFIG)
├── scraper.py          # Main scraper implementation
├── flow.py             # Navigation logic only
├── models.py           # Optional: Site-specific data models
├── selectors/         # YAML selector definitions
│   └── example.yaml   # Example selector configuration
└── README.md           # Template documentation
```

### Required Files

- `config.py` - Must contain `SITE_CONFIG` dictionary
- `flow.py` - Must contain navigation flow class
- `scraper.py` - Must contain scraper implementation
- `selectors/` - Must contain at least one YAML selector file

### Optional Files

- `models.py` - Site-specific data models (not required for simple scrapers)

## API Reference

### BaseSiteScraper

Abstract base class that all scrapers must inherit from.

#### Required Class Attributes

- `site_id` (str): Unique identifier for the scraper
- `site_name` (str): Human-readable name
- `base_url` (str): Base URL for the site

#### Required Methods

```python
async def navigate(self) -> None:
    """Bring page to initial ready state for scraping."""
    pass

async def scrape(self, **kwargs) -> Dict[str, Any]:
    """Perform scraping using configured selectors."""
    pass

def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform raw scraped data into structured output."""
    pass
```

#### Optional Methods

```python
def get_site_info(self) -> Dict[str, str]:
    """Get site information for debugging and logging."""
    pass

def validate_state(self) -> Dict[str, Any]:
    """Validate scraper state and return status information."""
    pass
```

### BaseFlow

Abstract base class for navigation-only logic.

#### Usage

```python
class YourSiteFlow(BaseFlow):
    async def open_home(self):
        await self.page.goto("https://example.com")
        await self.page.wait_for_load_state('networkidle')
    
    async def perform_search(self, query: str):
        search_input = await self.selector_engine.find(self.page, "search_input")
        await search_input.type(query)
        await search_input.press('Enter')
```

### ScraperRegistry

Central registry for managing scrapers.

#### Methods

```python
# Register a scraper
registry.register("site_id", ScraperClass)

# Get scraper class
scraper_class = registry.get_scraper("site_id")

# List all scrapers
scrapers = registry.list_scrapers()

# Get site metadata
metadata = registry.get_metadata("site_id")

# Validate all scrapers
results = registry.validate_all()

# Validate specific scraper
result = registry.validate_scraper("site_id")
```

## Configuration

### SITE_CONFIG Structure

```python
SITE_CONFIG = {
    "id": "unique_site_id",           # Required: lowercase, numbers, underscores only
    "name": "Human Readable Name",     # Required: non-empty string
    "base_url": "https://example.com", # Required: valid URL with http/https
    "version": "1.0.0",               # Required: semantic versioning
    "maintainer": "email@example.com", # Required: non-empty string
    "description": "Optional description", # Optional: string
    "tags": ["tag1", "tag2"]           # Optional: list of strings
}
```

### Selector Configuration

```yaml
description: "Human-readable description"
confidence_threshold: 0.7  # Required: 0.0-1.0
timeout: 5.0               # Optional: seconds
retry_count: 3             # Optional: number of retries
strategies:                # Required: non-empty list
  - type: "css"             # Required: css, xpath, text, attribute, role
    selector: ".example"    # Required: selector string
    weight: 1.0             # Optional: 0.0-1.0
```

## Validation

The framework provides comprehensive validation:

### File Validation

- Required files exist and are accessible
- Selectors directory contains valid YAML files
- YAML syntax and schema validation

### Configuration Validation

- All required fields present and valid
- Field formats and types checked
- URL and version format validation

### Interface Compliance

- Class inheritance from BaseSiteScraper
- Required class attributes present
- Required methods implemented with correct signatures

### Error Messages

Validation provides actionable error messages:

```
Missing required file: config.py
Create the missing file in your scraper directory

Invalid confidence_threshold in search.yaml: must be between 0.0 and 1.0
Update the confidence threshold to a valid range

Missing required method: navigate
Implement the required abstract method in your scraper class
```

## Best Practices

### 1. Separation of Concerns

- **Flow classes**: Navigation only, no data extraction
- **Scraper classes**: Orchestration and data extraction
- **Selectors**: YAML-only, no Python logic

### 2. Error Handling

```python
async def scrape(self, **kwargs):
    try:
        results = await self.selector_engine.extract_all(self.page, "results")
        return {"results": results}
    except Exception as e:
        self.logger.error("Scraping failed", error=str(e))
        return {"results": [], "error": str(e)}
```

### 3. Performance

- Use selector engine caching
- Implement appropriate timeouts
- Handle network errors gracefully

### 4. Testing

```python
# Test your scraper
from src.sites.base.contract_validator import validate_and_create_scraper

# This will validate contracts during instantiation
scraper = validate_and_create_scraper(YourScraper, page, selector_engine)
```

## Examples

See the example implementations:

- `src/sites/wikipedia/` - Simple scraper with search functionality
- `src/sites/flashscore/` - More complex scraper with multiple flows

## Troubleshooting

### Common Issues

1. **Missing Required Files**: Ensure all required files exist in your scraper directory
2. **Invalid YAML Syntax**: Check YAML indentation and structure
3. **Wrong Method Signatures**: Follow the exact method signatures from BaseSiteScraper
4. **Configuration Errors**: Validate SITE_CONFIG structure and values

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Validation will show detailed debug information
results = registry.validate_all()
```

### Getting Help

- Check the [validation troubleshooting guide](../../docs/validation-troubleshooting.md)
- Review example implementations
- Enable debug logging for detailed error information

## Contributing

When adding new scrapers:

1. Copy the template and follow the structure
2. Implement all required methods with correct signatures
3. Add comprehensive YAML selectors
4. Test with the validation system
5. Register in the central registry

## Performance

- **Startup Validation**: <2 seconds for all scrapers
- **Scraper Instantiation**: <100ms per scraper
- **Validation Caching**: 5-minute cache for repeated validations
- **Memory Usage**: Minimal overhead per scraper

## Security

- Input validation for all configuration
- YAML parsing with safe loader
- No code execution from configuration files
- Sandboxed scraper execution

## License

This framework is part of the Scorewise Scraper project. See the main project license for details.
