# Site Scraper API Contract

**Feature**: 013-site-scraper-template  
**Date**: 2025-01-29  
**Purpose**: API specification for site scraper base contracts and interfaces

## BaseSiteScraper API

### Abstract Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from playwright.async_api import Page

class BaseSiteScraper(ABC):
    """Abstract base class defining the contract for all site scrapers."""
    
    # Class attributes (must be defined by implementation)
    site_id: str
    site_name: str
    base_url: str
    
    def __init__(self, page: Page, selector_engine: SelectorEngine):
        """Initialize scraper with page and selector engine."""
        self.page = page
        self.selector_engine = selector_engine
    
    @abstractmethod
    async def navigate(self) -> None:
        """Bring page to initial ready state for scraping."""
        pass
    
    @abstractmethod
    async def scrape(self, **kwargs) -> Dict[str, Any]:
        """Perform scraping using configured selectors."""
        pass
    
    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw scraped data into structured output."""
        pass
```

### Implementation Requirements

**Class Attributes**:
- `site_id`: Must match configuration ID, unique across all scrapers
- `site_name`: Human-readable name for logging and debugging
- `base_url`: Base URL for navigation and validation

**Method Contracts**:

#### navigate()
- **Purpose**: Prepare page for scraping (login, navigation, setup)
- **Parameters**: None
- **Returns**: None
- **Exceptions**: Should raise NavigationError for critical failures
- **Side Effects**: May modify page state, cookies, localStorage

#### scrape(**kwargs)
- **Purpose**: Extract data using configured selectors
- **Parameters**: Variable keyword arguments for scraping parameters
- **Returns**: Dictionary containing raw scraped data
- **Exceptions**: Should raise ScrapingError for extraction failures
- **Side Effects**: Should not modify page state significantly

#### normalize(raw_data)
- **Purpose**: Transform raw data into standardized format
- **Parameters**: raw_data - Dictionary from scrape() method
- **Returns**: Dictionary with standardized structure
- **Exceptions**: Should raise NormalizationError for transformation failures
- **Side Effects**: No side effects, pure transformation

## BaseFlow API

### Abstract Interface

```python
from abc import ABC
from playwright.async_api import Page

class BaseFlow(ABC):
    """Abstract base class for navigation-only logic."""
    
    def __init__(self, page: Page, selector_engine: SelectorEngine):
        """Initialize flow with page and selector engine."""
        self.page = page
        self.selector_engine = selector_engine
```

### Implementation Constraints

**Allowed Operations**:
- Page navigation (goto, click, scroll)
- Form interactions (type, select, check)
- Wait operations (wait_for_selector, wait_for_navigation)
- State validation (element presence, text content)

**Forbidden Operations**:
- Data extraction (use scraper.scrape() instead)
- Data normalization (use scraper.normalize() instead)
- Complex business logic (keep navigation focused)

## Site Configuration API

### Configuration Structure

```python
SITE_CONFIG = {
    "id": "example_site",
    "name": "Example Site",
    "base_url": "https://example.com",
    "version": "1.0.0",
    "maintainer": "developer@example.com",
    "description": "Example site scraper for demonstration",
    "tags": ["example", "demo"]
}
```

### Required Fields

- `id`: String matching regex `^[a-z0-9_]+$`
- `name`: Non-empty string
- `base_url`: Valid URL string
- `version`: Semantic version string
- `maintainer`: Non-empty string (email or name)

### Optional Fields

- `description`: String describing the scraper purpose
- `tags`: List of strings for categorization

## Registry API

### Registry Interface

```python
class ScraperRegistry:
    """Central registry for managing site scrapers."""
    
    def register(self, site_id: str, scraper_class: Type[BaseSiteScraper]) -> None:
        """Register a scraper class."""
        pass
    
    def get_scraper(self, site_id: str) -> Type[BaseSiteScraper]:
        """Get scraper class by site ID."""
        pass
    
    def list_scrapers(self) -> List[str]:
        """List all registered scraper IDs."""
        pass
    
    def get_metadata(self, site_id: str) -> SiteConfiguration:
        """Get site configuration metadata."""
        pass
    
    def validate_all(self) -> Dict[str, ValidationResult]:
        """Validate all registered scrapers."""
        pass
```

### Usage Examples

```python
# Register scrapers
registry = ScraperRegistry()
registry.register("wikipedia", WikipediaScraper)
registry.register("flashscore", FlashscoreScraper)

# Get scraper class
scraper_class = registry.get_scraper("wikipedia")

# Create instance
scraper = scraper_class(page, selector_engine)

# Use scraper
await scraper.navigate()
raw_data = await scraper.scrape(query="python")
normalized_data = scraper.normalize(raw_data)
```

## Selector Definition API

### YAML Structure

```yaml
description: "Search input field"
confidence_threshold: 0.7
timeout: 5.0
retry_count: 3
strategies:
  - type: "css"
    selector: "input[type='search']"
    weight: 1.0
  - type: "xpath"
    selector: "//input[@type='search']"
    weight: 0.8
  - type: "text"
    selector: "Search"
    weight: 0.6
```

### Field Specifications

**description**: Human-readable description of the selector purpose
**confidence_threshold**: Minimum confidence score (0.0-1.0)
**timeout**: Maximum time to wait for selector (seconds)
**retry_count**: Number of retry attempts on failure
**strategies**: List of resolution strategies in priority order

### Strategy Types

- `css`: CSS selector
- `xpath`: XPath expression
- `text`: Text content matching
- `attribute`: Attribute value matching
- `role`: ARIA role matching

## Validation API

### ValidationResult Interface

```python
class ValidationResult:
    """Validation result for scraper implementation."""
    
    def __init__(self):
        self.valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.missing_files: List[str] = []
        self.invalid_selectors: List[str] = []
    
    def add_error(self, message: str) -> None:
        """Add a critical validation error."""
        self.errors.append(message)
        self.valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a non-critical validation warning."""
        self.warnings.append(message)
    
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.valid
```

### Validation Rules

**File Existence**:
- `config.py` must exist
- `flow.py` must exist
- `scraper.py` must exist
- `selectors/` directory must exist

**Configuration Validation**:
- SITE_CONFIG must be defined
- All required fields must be present
- Field values must match validation rules

**Interface Compliance**:
- Scraper class must inherit from BaseSiteScraper
- All required methods must be implemented
- Class attributes must be defined

**Selector Validation**:
- All YAML files must be valid
- Selector definitions must match schema
- Strategy types must be supported

## Error Handling

### Exception Hierarchy

```python
class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass

class NavigationError(ScraperError):
    """Navigation-related errors."""
    pass

class ScrapingError(ScraperError):
    """Data extraction errors."""
    pass

class NormalizationError(ScraperError):
    """Data transformation errors."""
    pass

class ValidationError(ScraperError):
    """Validation errors."""
    pass

class RegistryError(ScraperError):
    """Registry-related errors."""
    pass
```

### Error Response Format

```python
{
    "error_type": "NavigationError",
    "message": "Failed to navigate to search page",
    "site_id": "example_site",
    "timestamp": "2025-01-29T10:30:00Z",
    "context": {
        "url": "https://example.com/search",
        "selector": "search_input",
        "confidence": 0.3
    }
}
```
