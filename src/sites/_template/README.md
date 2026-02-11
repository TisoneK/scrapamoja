# Modular Site Scraper Template

A comprehensive, production-ready template for creating modular site scrapers with advanced features including flows, processors, validators, components, and multi-environment configuration.

## 🏗️ Flow Architecture Patterns

This template supports **four architectural patterns** for different site complexity levels:

### Pattern A: Simple Pattern 📝
**Best for:** Static sites, simple navigation, basic extraction
```
simple_site/
├── flow.py                 # Single flow file with all navigation logic
└── scraper.py
```

### Pattern B: Standard Pattern ⚖️
**Best for:** Dynamic sites, moderate complexity, mixed operations
```
standard_site/
├── flow.py                 # Basic navigation and coordination
├── flows/                  # Specialized flows
│   ├── __init__.py
│   ├── search_flow.py      # Complex search logic
│   ├── pagination_flow.py  # Pagination handling
│   └── extraction_flow.py  # Data extraction
└── scraper.py
```

### Pattern C: Complex Pattern 🎯
**Best for:** SPAs, complex navigation, multi-domain operations
```
complex_site/
├── flows/                  # Domain-separated flows
│   ├── __init__.py
│   ├── navigation/         # Navigation flows
│   │   ├── __init__.py
│   │   ├── match_nav.py    # Match page navigation
│   │   ├── live_nav.py     # Live matches navigation
│   │   └── competition_nav.py  # Competition navigation
│   ├── extraction/         # Data extraction flows
│   │   ├── __init__.py
│   │   ├── match_extract.py    # Match data extraction
│   │   ├── odds_extract.py      # Betting odds extraction
│   │   └── stats_extract.py     # Live statistics extraction
│   ├── filtering/          # Filtering flows
│   │   ├── __init__.py
│   │   ├── date_filter.py  # Date filtering logic
│   │   ├── sport_filter.py # Sport filtering logic
│   │   └── competition_filter.py  # Competition filtering
│   └── authentication/     # Authentication flows
│       ├── __init__.py
│       ├── login_flow.py   # Traditional login
│       └── oauth_flow.py   # OAuth authentication
└── scraper.py
```

### Pattern D: Legacy Pattern 🔄
**Best for:** Backward compatibility with existing implementations
```
legacy_site/
├── flow.py                 # Original single flow file
├── flows/                  # Original flat flow structure
│   ├── __init__.py
│   ├── base_flow.py
│   ├── search_flow.py
│   ├── login_flow.py
│   └── pagination_flow.py
└── scraper.py
```

## 🎯 Pattern Selection Guide

Use this decision tree to choose the right pattern:

1. **Is the site mostly static with simple navigation?**
   - **Yes** → Use **Simple Pattern**
   - **No** → Continue to question 2

2. **Does the site have complex search, pagination, or extraction needs?**
   - **Yes** → Continue to question 3
   - **No** → Use **Standard Pattern**

3. **Is the site a SPA with multiple domains (navigation, extraction, filtering, auth)?**
   - **Yes** → Use **Complex Pattern**
   - **No** → Use **Standard Pattern**

4. **Are you maintaining an existing scraper?**
   - **Yes** → Consider **Legacy Pattern** or migrate gradually
   - **No** → Use the pattern from questions 1-3

## 🚀 Features

### Core Architecture
- **Modular Design**: Granular components with single responsibilities
- **Async/Await**: Full async support for optimal performance
- **Configuration Management**: Multi-environment configuration with feature flags
- **Component System**: Reusable components for common functionality
- **Data Processing Pipeline**: Normalization → Validation → Transformation
- **Error Handling**: Comprehensive error handling and resilience patterns

### Navigation Flows
- **Domain-Separated Flows**: Navigation, extraction, filtering, authentication
- **Search Flow**: Advanced search with retry logic and metadata extraction
- **Login Flow**: Authentication with OAuth support and stealth mode
- **Pagination Flow**: Multiple pagination patterns (button, infinite scroll, load more)
- **Base Flow**: Common navigation functionality and utilities

### Data Processing
- **Data Normalizer**: HTML decoding, whitespace cleaning, case conversion
- **Data Validator**: Quality checks, type validation, business rules
- **Data Transformer**: Field mapping, value mapping, calculated fields
- **Validation Pipeline**: Chain multiple validators together

### Reusable Components
- **OAuth Authentication**: OAuth 1.0a/2.0 support with token management
- **Rate Limiter**: Multiple algorithms (token bucket, sliding window, fixed window)
- **Stealth Handler**: Anti-bot detection avoidance with fingerprint randomization

### Configuration
- **Multi-Environment**: Development, production, and custom configurations
- **Feature Flags**: Dynamic feature toggling with percentage-based rollouts
- **Validation**: Configuration validation with custom rules

## 📁 Directory Structure

```
_template/
├── README.md                 # This file
├── scraper.py               # Main scraper implementation
├── patterns/                # 🆕 Architectural patterns
│   ├── __init__.py         # Pattern registry and utilities
│   ├── simple/             # Simple pattern (single flow.py)
│   │   ├── __init__.py
│   │   └── flow.py
│   ├── standard/           # Standard pattern (flow.py + flows/)
│   │   ├── __init__.py
│   │   ├── flow.py
│   │   └── flows/
│   │       ├── __init__.py
│   │       ├── search_flow.py
│   │       ├── pagination_flow.py
│   │       └── extraction_flow.py
│   └── complex/            # Complex pattern (domain-separated)
│       ├── __init__.py
│       └── flows/
│           ├── __init__.py
│           ├── navigation/
│           ├── extraction/
│           ├── filtering/
│           └── authentication/
├── flows/                   # Legacy flows (backward compatibility)
│   ├── __init__.py         # Flow registry and utilities
│   ├── base_flow.py        # Base flow class
│   ├── search_flow.py      # Search functionality
│   ├── login_flow.py       # Authentication flow
│   └── pagination_flow.py  # Pagination handling
├── config/                  # Configuration management
│   ├── __init__.py         # Config registry and utilities
│   ├── base.py             # Base configuration
│   ├── dev.py              # Development configuration
│   ├── prod.py             # Production configuration
│   └── feature_flags.py    # Feature flags management
├── processors/              # Data processing pipeline
│   ├── __init__.py         # Processor registry and pipeline
│   ├── normalizer.py       # Data normalization
│   ├── validator.py        # Data validation
│   └── transformer.py      # Data transformation
├── validators/              # Validation system
│   ├── __init__.py         # Validator registry and pipeline
│   ├── config_validator.py # Configuration validation
│   └── data_validator.py   # Data validation
└── components/             # Reusable components
    ├── __init__.py         # Component registry and manager
    ├── oauth_auth.py       # OAuth authentication
    ├── rate_limiter.py     # Rate limiting
    └── stealth_handler.py  # Stealth functionality
```

## 🛠️ Getting Started

### 1. Choose Your Pattern 🎯

First, decide which architectural pattern fits your site complexity:

```bash
# Interactive pattern selection (recommended)
python setup.py --interactive

# Or specify pattern directly
python setup.py --pattern simple    # For basic sites
python setup.py --pattern standard  # For dynamic sites  
python setup.py --pattern complex   # For SPAs and complex sites
```

### 2. Copy the Template
```bash
cp -r src/sites/_template src/sites/your_site_name
```

### 3. Update Basic Configuration
Edit `src/sites/your_site_name/scraper.py`:
```python
class YourSiteScraper(ModularSiteScraper):
    site_id = "your_site"
    site_name = "Your Site Name"
    base_url = "https://example.com"
    
    async def setup_components(self) -> None:
        # Register your flows, processors, validators, and components
        # Based on your chosen pattern
        pass
```

### 4. Configure Your Site
Create `src/sites/your_site_name/config/site_config.py`:
```python
SITE_CONFIG = {
    "id": "your_site",
    "name": "Your Site Name", 
    "base_url": "https://example.com",
    "pattern": "complex",  # simple, standard, or complex
    "selectors": {
        "search_input": "#search",
        "search_button": "#search-btn",
        # Add your selectors
    }
}
```

### 4. Define Selectors
Create YAML files in `src/sites/your_site_name/selectors/`:
```yaml
# search_input.yaml
selector: "#search-input"
type: "input"
confidence_threshold: 0.8
attributes:
  - name: "placeholder"
    type: "string"
  - name: "name"
    type: "string"
```

### 5. Register Your Scraper
Add to `src/sites/registry.py`:
```python
from src.sites.your_site_name.scraper import YourSiteScraper

registry.register("your_site", YourSiteScraper)
```

## 📖 Usage Examples

### Basic Scraping
```python
from src.sites.registry import ScraperRegistry

# Get scraper
registry = ScraperRegistry()
scraper_class = registry.get_scraper("your_site")
scraper = scraper_class(page, selector_engine)

# Navigate and scrape
await scraper.navigate()
data = await scraper.scrape(query="search term")
normalized = scraper.normalize(data)
```

### Using Modular Components
```python
# Use flows
await scraper.flow.perform_search("query")
await scraper.flow.login(username, password)
await scraper.flow.paginate_results()

# Use processors
normalizer = DataNormalizer()
cleaned_data = await normalizer.process(raw_data)

validator = DataValidator()
validation_result = await validator.process(cleaned_data)

transformer = DataTransformer()
final_data = await transformer.process(validation_result.data)
```

### Using Components
```python
# OAuth authentication
oauth = OAuthAuthComponent()
oauth.configure_oauth(
    oauth_version="2.0",
    client_id="your_client_id",
    client_secret="your_client_secret",
    authorization_url="https://example.com/oauth/authorize",
    token_url="https://example.com/oauth/token"
)

# Rate limiting
rate_limiter = RateLimiterComponent()
rate_limiter.set_domain_limits("example.com", requests_per_second=2.0)

# Stealth handling
stealth = StealthHandlerComponent()
await stealth.execute(page=page, apply_all=True)
```

### Configuration Management
```python
# Load configuration
config = get_config("prod")  # or "dev"

# Feature flags
flags = FeatureFlags()
if flags.is_enabled("advanced_search"):
    # Use advanced search functionality
    pass

# Environment-specific settings
if config.environment == "dev":
    # Development-specific logic
    pass
```

## 🔧 Configuration

### Environment Configuration
Create configuration files in your site's config directory:

**Development (`config/dev.py`)**:
```python
from .base import BaseConfig

class DevConfig(BaseConfig):
    headless = False
    debug = True
    log_level = "DEBUG"
    screenshot_on_error = True
    requests_per_second = 1.0
```

**Production (`config/prod.py`)**:
```python
from .base import BaseConfig

class ProdConfig(BaseConfig):
    headless = True
    debug = False
    log_level = "INFO"
    screenshot_on_error = False
    requests_per_second = 0.5
```

### Feature Flags
Configure feature flags in `config/feature_flags.py`:
```python
FEATURE_FLAGS = {
    "advanced_search": {
        "enabled": True,
        "environments": ["dev", "prod"],
        "percentage": 100
    },
    "experimental_parser": {
        "enabled": True,
        "environments": ["dev"],
        "percentage": 10
    }
}
```

## 🧪 Testing

### Unit Tests
```python
import pytest
from src.sites.your_site_name.scraper import YourSiteScraper

@pytest.mark.asyncio
async def test_search_functionality():
    scraper = YourSiteScraper(mock_page, mock_selector_engine)
    result = await scraper.scrape(query="test query")
    assert result["type"] == "search"
    assert "results" in result
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_full_scraping_flow():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        scraper = YourSiteScraper(page, selector_engine)
        await scraper.navigate()
        data = await scraper.scrape()
        
        assert data is not None
        assert len(data) > 0
```

## 📊 Monitoring and Logging

### Structured Logging
The template includes structured JSON logging:
```python
# Logs are automatically structured with correlation IDs
logger.info("Search completed", extra={
    "query": query,
    "results_count": len(results),
    "execution_time_ms": execution_time
})
```

### Performance Monitoring
```python
# Performance metrics are automatically collected
stats = scraper.get_execution_stats()
print(f"Total requests: {stats.total_requests}")
print(f"Success rate: {stats.success_rate}%")
print(f"Average response time: {stats.avg_response_time}ms")
```

## 🚀 Advanced Features

### Custom Processors
```python
class CustomProcessor(BaseProcessor):
    async def process(self, data: Dict[str, Any]) -> ProcessorResult:
        # Your custom processing logic
        processed_data = self.custom_logic(data)
        return ProcessorResult(
            success=True,
            data=processed_data,
            execution_time_ms=execution_time
        )
```

### Custom Validators
```python
class CustomValidator(BaseValidator):
    async def validate(self, data: Dict[str, Any]) -> ValidationResult:
        # Your custom validation logic
        is_valid = self.custom_validation(data)
        return ValidationResult(
            valid=is_valid,
            errors=errors if not is_valid else []
        )
```

### Custom Components
```python
class CustomComponent(BaseComponent):
    async def execute(self, **kwargs) -> ComponentResult:
        # Your custom component logic
        result = await self.custom_operation(**kwargs)
        return ComponentResult(
            success=True,
            data=result
        )
```

## 🔒 Security and Best Practices

### Stealth Features
- User agent randomization
- Viewport size variation
- Timezone and language randomization
- Human-like mouse movement and typing
- Request timing randomization

### Rate Limiting
- Multiple rate limiting algorithms
- Domain-specific limits
- Automatic backoff on rate limit hits
- Configurable wait strategies

### Error Handling
- Graceful degradation
- Automatic retry with exponential backoff
- Circuit breaker pattern
- Comprehensive error logging

## 📈 Performance Optimization

### Async/Await Patterns
All operations are async for optimal performance:
```python
# Concurrent processing
results = await asyncio.gather(
    scraper.scrape_page(page1),
    scraper.scrape_page(page2),
    scraper.scrape_page(page3)
)
```

### Memory Management
- Automatic cleanup of resources
- Component lifecycle management
- Memory-efficient data structures

### Caching
- Built-in caching for frequently accessed data
- Configurable cache TTL
- Memory and disk-based caching options

## 🤝 Contributing

When contributing to the template:

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation
4. Ensure all async operations are properly handled
5. Follow the constitution principles (modularity, resilience, etc.)

## 📄 License

This template is part of the Scorewise Scraper project and follows the same license terms.

## 🆘 Support

For issues and questions:
1. Check the existing documentation
2. Review the test files for usage examples
3. Check the base classes for available methods
4. Review the configuration options

## 🎯 Next Steps

After setting up your scraper:

1. **Define Selectors**: Create comprehensive YAML selector definitions
2. **Implement Flows**: Add site-specific navigation logic
3. **Configure Processing**: Set up data processing pipelines
4. **Add Tests**: Write comprehensive tests
5. **Monitor Performance**: Set up monitoring and alerting
6. **Deploy**: Configure for production deployment

---

**Happy Scraping!** 🚀
