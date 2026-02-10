# Site Template Integration Framework

**Version**: 1.0.0  
**Author**: Scorewise Team  
**Last Updated**: 2025-01-29

## Overview

The Site Template Integration Framework provides a standardized, modular approach to creating site scrapers by leveraging existing Scorewise framework components. It enables rapid development of high-quality scrapers while maintaining consistency, reusability, and compliance with framework conventions.

## Key Features

- **Template-Based Development**: Create scrapers using standardized templates
- **Automatic Framework Integration**: Seamless connection with existing components
- **YAML Selector Configuration**: Declarative selector definitions
- **Component Integration**: Browser lifecycle, resource monitoring, logging
- **Centralized Registry**: Template discovery and management
- **Comprehensive Validation**: Quality assurance and compliance checking

## Architecture

### Core Components

```
src/sites/base/template/
├── __init__.py                 # Framework exports
├── interfaces.py              # Core interfaces and DTOs
├── site_template.py           # Base template implementation
├── integration_bridge.py      # Framework component integration
├── selector_loader.py         # YAML selector loading
├── site_registry.py          # Template discovery and management
├── validation.py             # Validation and compliance checking
├── browser_lifecycle.py      # Browser lifecycle integration
├── resource_monitoring.py   # Resource monitoring integration
├── logging_integration.py   # Structured logging integration
└── error_handling.py         # Error handling and retry logic
```

### Template Structure

```
src/sites/{site_name}/
├── __init__.py                # Package initialization
├── scraper.py                 # Main scraper implementation
├── config.py                  # Site-specific configuration
├── flow.py                    # Navigation and interaction flows
├── integration_bridge.py     # Site-specific integration
├── selector_loader.py         # YAML selector loading
├── selectors/                 # YAML selector definitions
│   ├── {selector_name}.yaml
│   └── ...
├── flows/                     # Flow implementations
│   ├── {flow_name}.py
│   └── ...
└── extraction/                # Extraction rules and models
    ├── rules.py
    ├── models.py
    └── __init__.py
```

## Quick Start

### 1. Create a New Template

```python
from src.sites.base.template import BaseSiteTemplate

class MySiteScraper(BaseSiteTemplate):
    def __init__(self, page, selector_engine):
        super().__init__(
            name="mysite",
            version="1.0.0",
            description="My site scraper",
            author="Your Name",
            framework_version="1.0.0",
            site_domain="mysite.com"
        )
```

### 2. Define YAML Selectors

Create `src/sites/mysite/selectors/main_content.yaml`:

```yaml
name: main_content
description: Main content area selector
selector: .main-content
strategies:
  - name: css
    type: css
    priority: 1
    confidence: 0.9
validation:
  required: true
  exists: true
  min_length: 50
```

### 3. Use the Template

```python
# Initialize template
scraper = MySiteScraper(page, selector_engine)

# Initialize template components
await scraper.initialize()

# Scrape data
result = await scraper.scrape(
    action="get_content",
    selector_name="main_content"
)
```

## Core Classes

### BaseSiteTemplate

The base class for all site templates. Provides:

- Automatic framework integration
- Component initialization
- Error handling and retry logic
- Performance monitoring
- Health checking

```python
class BaseSiteTemplate:
    def __init__(self, name, version, description, author, framework_version, site_domain)
    async def initialize(self) -> bool
    async def scrape(self, action: str, **kwargs) -> Dict[str, Any]
    async def health_check(self) -> Dict[str, Any]
    def get_template_info(self) -> Dict[str, Any]
```

### IntegrationBridge

Connects site-specific components with framework infrastructure:

```python
class FullIntegrationBridge:
    def __init__(self, template_name, selector_engine, page)
    async def initialize(self) -> bool
    def get_available_components(self) -> Dict[str, Any]
    def is_component_available(self, component_name: str) -> bool
```

### SiteRegistry

Centralized template discovery and management:

```python
class BaseSiteRegistry:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    async def initialize(self) -> bool
    async def discover_templates(self) -> Dict[str, RegistryEntry]
    async def load_template(self, template_name: str, page, selector_engine)
    async def search_templates(self, **kwargs) -> List[RegistryEntry]
```

## YAML Selectors

### Structure

```yaml
name: selector_name
description: Human-readable description
selector: CSS selector or XPath expression
strategies:
  - name: strategy_name
    type: css|xpath|text|attribute|hybrid
    priority: 1-100
    confidence: 0.0-1.0
    timeout: 1000-30000
    retry_count: 0-5
validation:
  required: boolean
  exists: boolean
  text_pattern: regex_pattern
  attribute_pattern: regex_pattern
  min_length: integer
  max_length: integer
metadata:
  category: navigation|content|interaction|extraction
  tags: [tag1, tag2]
  version: x.y.z
  author: author_name
```

### Strategy Types

- **css**: CSS selector strategy
- **xpath**: XPath expression strategy
- **text**: Text content strategy
- **attribute**: Attribute value strategy
- **hybrid**: Combined strategy approach

### Validation Rules

- **required**: Element must exist
- **exists**: Element existence check
- **text_pattern**: Regex pattern for text content
- **attribute_pattern**: Regex pattern for attributes
- **min_length/max_length**: Length constraints

## Framework Integration

### Browser Lifecycle Integration

Automatic integration with browser lifecycle management:

```python
# Automatic screenshot capture
await scraper.capture_screenshot("before_action")

# Automatic HTML capture
await scraper.capture_html("after_action")

# Error state capture
await scraper.capture_error_state("error_context")
```

### Resource Monitoring Integration

Real-time resource monitoring with threshold alerts:

```python
# Get resource status
status = await scraper.get_resource_status()

# Resource history
history = await scraper.get_resource_history()

# Threshold alerts
alerts = await scraper.get_threshold_alerts()
```

### Logging Integration

Structured logging with correlation IDs:

```python
# Performance logging
scraper.log_performance("operation_name", duration, metadata)

# Error logging
scraper.log_error(exception, context)

# Info logging
scraper.log_info("message", **kwargs)
```

## Validation Framework

### YAML Selector Validation

```python
from src.sites.base.template.validation import YAMLSelectorValidator

validator = YAMLSelectorValidator()
result = await validator.validate_selector_file("selector.yaml")
```

### Extraction Rule Validation

```python
from src.sites.base.template.validation import ExtractionRuleValidator

validator = ExtractionRuleValidator()
result = await validator.validate_extraction_rule(rule_data)
```

### Framework Compliance Validation

```python
from src.sites.base.template.validation import FrameworkComplianceValidator

validator = FrameworkComplianceValidator()
result = await validator.validate_template_compliance(template_path)
```

## Template Registry

### Discovery

Automatic template discovery from filesystem:

```python
registry = BaseSiteRegistry()
await registry.initialize()

# Discover all templates
templates = await registry.discover_templates()

# Search templates
results = await registry.search_templates(
    query="github",
    category="code_repository",
    tags=["yaml_selectors"]
)
```

### Registration

Manual template registration:

```python
template_metadata = {
    "name": "mysite",
    "version": "1.0.0",
    "description": "My site scraper",
    "template_path": "src/sites/mysite",
    "module_path": "src/sites/mysite/scraper.py"
}

await registry.register_template(template_metadata)
```

### Loading

Dynamic template instantiation:

```python
# Load template instance
scraper = await registry.load_template("mysite", page, selector_engine)

# Get template info
info = await registry.get_template_instance_info("mysite")
```

## Configuration

### Template Configuration

```python
# src/sites/mysite/config.py
SITE_CONFIG = {
    "name": "mysite",
    "domain": "mysite.com",
    "base_url": "https://mysite.com",
    "rate_limit": {
        "requests_per_minute": 60,
        "burst_size": 10
    },
    "pagination": {
        "max_pages": 100,
        "page_size": 20
    },
    "extraction": {
        "timeout": 30,
        "retry_count": 3
    },
    "features": {
        "screenshot_capture": True,
        "html_capture": True,
        "resource_monitoring": True
    }
}
```

### Framework Configuration

```python
# Global framework configuration
FRAMEWORK_CONFIG = {
    "auto_discovery": True,
    "validation_level": "strict",
    "cache_enabled": True,
    "performance_monitoring": True,
    "logging_level": "INFO"
}
```

## Error Handling

### Template Errors

```python
class TemplateError(Exception):
    """Base template error."""
    pass

class TemplateValidationError(TemplateError):
    """Template validation error."""
    pass

class TemplateInitializationError(TemplateError):
    """Template initialization error."""
    pass
```

### Retry Logic

Automatic retry with exponential backoff:

```python
# Configure retry settings
RETRY_CONFIG = {
    "max_attempts": 3,
    "base_delay": 1.0,
    "max_delay": 30.0,
    "exponential_base": 2.0,
    "jitter": True
}
```

## Performance Optimization

### Caching

Template and selector caching:

```python
# Enable caching
CACHE_CONFIG = {
    "template_cache_ttl": 3600,
    "selector_cache_ttl": 1800,
    "validation_cache_ttl": 900
}
```

### Lazy Loading

Component lazy loading:

```python
# Components loaded on-demand
LAZY_LOADING = {
    "browser_lifecycle": True,
    "resource_monitoring": True,
    "logging_integration": True
}
```

## Security Considerations

### Template Sandboxing

```python
# Security configuration
SECURITY_CONFIG = {
    "allow_file_access": False,
    "allow_network_access": True,
    "allow_system_commands": False,
    "max_execution_time": 300
}
```

### Input Validation

```python
# Input validation rules
VALIDATION_RULES = {
    "selector_validation": True,
    "extraction_validation": True,
    "framework_compliance": True
}
```

## Testing

### Unit Tests

```python
# tests/sites/template/test_site_template.py
import pytest
from src.sites.base.template import BaseSiteTemplate

class TestBaseSiteTemplate:
    def test_template_initialization(self):
        # Test template initialization
        pass
    
    def test_template_scraping(self):
        # Test scraping functionality
        pass
```

### Integration Tests

```python
# tests/sites/github/test_integration.py
import pytest
from src.sites.github.scraper import GitHubScraper

class TestGitHubIntegration:
    async def test_github_scraping(self):
        # Test GitHub scraping integration
        pass
```

## Best Practices

### 1. Follow Constitutional Principles

- **Selector-Centric**: Use existing selector engine, no hardcoded selectors
- **Modularity**: Clear separation of concerns
- **Async-First**: Use async/await throughout
- **Observability**: Structured logging and monitoring

### 2. Template Structure

- Follow the standard directory structure
- Use descriptive naming conventions
- Include comprehensive documentation
- Implement proper error handling

### 3. YAML Selectors

- Use semantic selector names
- Include comprehensive validation rules
- Provide multiple strategies for reliability
- Document selector purpose and usage

### 4. Framework Integration

- Leverage automatic component integration
- Use provided integration bridges
- Implement proper error handling
- Follow framework conventions

## Troubleshooting

### Common Issues

1. **Template Initialization Errors**
   - Check required files exist
   - Verify configuration syntax
   - Validate framework compatibility

2. **Selector Validation Errors**
   - Check YAML syntax
   - Validate selector expressions
   - Ensure required fields present

3. **Framework Integration Issues**
   - Verify component availability
   - Check integration bridge configuration
   - Validate dependency requirements

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Issues

Monitor resource usage:

```python
# Check resource status
status = await scraper.get_resource_status()

# Get performance metrics
metrics = scraper.get_performance_metrics()
```

## Migration Guide

### From Manual Scrapers

1. **Create Template Structure**
   ```
   src/sites/mysite/
   ├── scraper.py
   ├── config.py
   └── selectors/
   ```

2. **Convert Selectors**
   ```python
   # From: element.querySelector('.class')
   # To: YAML selector file
   ```

3. **Implement Template Class**
   ```python
   class MySiteScraper(BaseSiteTemplate):
       # Implementation
   ```

### From Previous Framework Versions

1. **Update Imports**
   ```python
   # From: from src.sites.base import BaseSiteScraper
   # To: from src.sites.base.template import BaseSiteTemplate
   ```

2. **Migrate Configuration**
   ```python
   # Update configuration structure
   # Use new configuration format
   ```

3. **Update Integration**
   ```python
   # Use new integration bridge
   # Leverage automatic component integration
   ```

## API Reference

### Core Classes

#### BaseSiteTemplate

```python
class BaseSiteTemplate:
    def __init__(self, name, version, description, author, framework_version, site_domain)
    async def initialize(self) -> bool
    async def scrape(self, action: str, **kwargs) -> Dict[str, Any]
    async def health_check(self) -> Dict[str, Any]
    def get_template_info(self) -> Dict[str, Any]
    async def capture_screenshot(self, context: str, filename: Optional[str] = None) -> str
    async def capture_html(self, context: str, filename: Optional[str] = None) -> str
    def get_performance_metrics(self) -> Dict[str, Any]
```

#### FullIntegrationBridge

```python
class FullIntegrationBridge:
    def __init__(self, template_name, selector_engine, page)
    async def initialize(self) -> bool
    def get_available_components(self) -> Dict[str, Any]
    def is_component_available(self, component_name: str) -> bool
    def get_integration_status(self) -> Dict[str, Any]
```

#### BaseSiteRegistry

```python
class BaseSiteRegistry:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    async def initialize(self) -> bool
    async def discover_templates(self) -> Dict[str, RegistryEntry]
    async def register_template(self, template_metadata: Dict[str, Any]) -> bool
    async def load_template(self, template_name: str, page, selector_engine)
    async def search_templates(self, **kwargs) -> List[RegistryEntry]
    async def get_template(self, template_name: str) -> Optional[RegistryEntry]
    async def list_templates(self, filters: Optional[Dict[str, Any]] = None) -> List[RegistryEntry]
```

### Validation Classes

#### YAMLSelectorValidator

```python
class YAMLSelectorValidator:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    async def validate_selector_file(self, file_path: Union[str, Path]) -> Dict[str, Any]
    async def validate_selector_directory(self, directory_path: Union[str, Path]) -> Dict[str, Any]
    def update_config(self, new_config: Dict[str, Any]) -> None
    def get_config(self) -> Dict[str, Any]
```

#### ExtractionRuleValidator

```python
class ExtractionRuleValidator:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    async def validate_extraction_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]
    async def validate_extraction_rules_directory(self, directory_path: Union[str, Path]) -> Dict[str, Any]
    def update_config(self, new_config: Dict[str, Any]) -> None
    def get_config(self) -> Dict[str, Any]
```

#### FrameworkComplianceValidator

```python
class FrameworkComplianceValidator:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    async def validate_template_compliance(self, template_path: str) -> Dict[str, Any]
    def get_compliance_summary(self) -> Dict[str, Any]
    def update_config(self, new_config: Dict[str, Any]) -> None
    def get_config(self) -> Dict[str, Any]
```

## Contributing

### Development Setup

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd scorewise
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Tests**
   ```bash
   pytest tests/sites/template/
   ```

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Include docstrings
- Write comprehensive tests

### Submitting Changes

1. Create feature branch
2. Implement changes with tests
3. Run validation suite
4. Submit pull request

## License

This framework is part of the Scorewise project and follows the same license terms.

## Support

For questions, issues, or contributions:

- **Documentation**: See this guide and inline documentation
- **Issues**: Create GitHub issues with detailed descriptions
- **Discussions**: Use GitHub discussions for questions
- **Examples**: See GitHub template implementation

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-29  
**Framework Version**: 1.0.0+
