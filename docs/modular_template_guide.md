# Modular Template System Guide

## Overview

The modular template system provides a comprehensive framework for creating extensible, maintainable, and scalable web scrapers. This guide covers the architecture, usage patterns, best practices, and advanced features of the modular template system.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Getting Started](#getting-started)
3. [Core Components](#core-components)
4. [Plugin Development](#plugin-development)
5. [Configuration Management](#configuration-management)
6. [Best Practices](#best-practices)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)
9. [Migration Guide](#migration-guide)
10. [Examples](#examples)

## Architecture Overview

The modular template system is built around several key components that work together to provide a flexible and extensible scraping framework:

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Modular Template System                    │
├─────────────────────────────────────────────────────────────────┤
│  Component Interface    │  Plugin System      │  Configuration    │
│  - IComponent          │  - Plugin Interface │  - Config Loader   │
│  - BaseComponent       │  - Plugin Registry  │  - Config Validator│
│  - ComponentFactory     │  - Plugin Discovery │  - Config Merger    │
│  - ComponentManager     │  - Plugin Lifecycle │  - Config Cache     │
├─────────────────────────────────────────────────────────────────┤
│  Browser Management    │  Data Processing   │  Storage System     │
│  - BrowserSession      │  - Extractor Module  │  - Snapshot API     │
│  - BrowserConfig       │  - Transformers     │  - File Storage     │
│  - Resource Monitor    │  - Validators        │  - Database Storage │
├─────────────────────────────────────────────────────────────────┤
│  Selector System       │  Telemetry System   │  Error Handling     │
│  - Selector Engine     │  - Metrics Collection│  - Error Handler    │
│  - Selector Strategies  │  - Performance      │  - Recovery Logic   │
│  - YAML Configuration │  - Health Monitoring │  - Alert System     │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Modularity**: Each component is self-contained with clear interfaces
2. **Extensibility**: Plugin system allows custom functionality injection
3. **Configuration**: Comprehensive configuration management with multiple sources
4. **Observability**: Built-in telemetry and monitoring
5. **Resilience**: Robust error handling and recovery mechanisms
6. **Performance**: Optimized for high-performance scraping operations

## Getting Started

### Basic Usage

```python
from src.sites.base.site_scraper import ModularSiteScraper
from src.sites.base.component_interface import ComponentContext

# Create a modular scraper
scraper = ModularSiteScraper("example_site")

# Initialize with configuration
await scraper.initialize({
    "browser": {
        "headless": True,
        "viewport": {"width": 1920, "height": 1080}
    },
    "selectors": {
        "title": "h1",
        "content": ".content"
    }
})

# Scrape data
results = await scraper.scrape(url="https://example.com")
print(results)
```

### Component Registration

```python
from src.sites.base.component_interface import BaseComponent, register_component

class CustomExtractor(BaseComponent):
    def __init__(self):
        super().__init__("custom_extractor")
    
    async def extract(self, context, **kwargs):
        # Custom extraction logic
        return {"custom_data": "extracted"}

# Register component
register_component(CustomExtractor())
```

## Core Components

### Component Interface

The component interface provides the foundation for all modular components:

```python
from src.sites.base.component_interface import BaseComponent, ComponentResult

class MyComponent(BaseComponent):
    def __init__(self, component_id):
        super().__init__(component_id)
    
    async def execute(self, context: ComponentContext, **kwargs) -> ComponentResult:
        # Component implementation
        return ComponentResult(
            success=True,
            data={"result": "success"}
        )
```

### Plugin System

The plugin system enables extensibility through hooks and custom logic:

```python
from src.sites.base.plugin_interface import BasePlugin, PluginMetadata, HookType

class ValidationPlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            id="validation_plugin",
            name="Data Validation Plugin",
            plugin_type=PluginType.VALIDATION,
            hooks=[HookType.AFTER_EXTRACT]
        )
    
    async def execute(self, context, hook_type, **kwargs):
        if hook_type == HookType.AFTER_EXTRACT:
            data = kwargs.get('extracted_data', {})
            # Validate data
            return PluginResult(success=True, data={"validated": True})

# Register plugin
from src.sites.base.plugin_interface import register_plugin
register_plugin(ValidationPlugin())
```

### Configuration Management

Comprehensive configuration management with multiple sources:

```python
# Configuration file (config.json)
{
    "browser": {
        "headless": true,
        "viewport": {"width": 1920, "height": 1080}
    },
    "plugins": {
        "validation_plugin": {
            "enabled": true,
            "strict_mode": false
        }
    }
}

# Load configuration
from src.sites.base.config_loader import ConfigLoader
loader = ConfigLoader()
config = await loader.load_from_file("config.json")
```

## Plugin Development

### Creating a Plugin

1. **Extend BasePlugin**:
```python
from src.sites.base.plugin_interface import BasePlugin, PluginMetadata, PluginType, HookType

class MyPlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            id="my_plugin",
            name="My Custom Plugin",
            version="1.0.0",
            author="Your Name",
            plugin_type=PluginType.CUSTOM,
            hooks=[HookType.BEFORE_SCRAPE, HookType.AFTER_SCRAPE],
            permissions=["data_access"]
        )
```

2. **Implement Lifecycle Methods**:
```python
async def _on_initialize(self, context):
    # Initialization logic
    return True

async def _on_execute(self, context, hook_type, **kwargs):
    # Plugin execution logic
    return PluginResult(success=True, data={})

async def _on_cleanup(self, context):
    # Cleanup logic
    return True
```

3. **Register the Plugin**:
```python
from src.sites.base.plugin_interface import register_plugin
register_plugin(MyPlugin())
```

### Plugin Hooks

Available hooks for different lifecycle events:

- `BEFORE_SCRAPE`: Before scraping starts
- `AFTER_SCRAPE`: After scraping completes
- `BEFORE_EXTRACT`: Before data extraction
- `AFTER_EXTRACT`: After data extraction
- `BEFORE_NAVIGATE`: Before navigation
- `AFTER_NAVIGATE`: After navigation
- `ERROR_OCCURRED`: When an error occurs
- `VALIDATION_FAILED`: When validation fails

### Plugin Configuration

```python
# Plugin configuration schema
{
    "plugins": {
        "my_plugin": {
            "enabled": true,
            "setting1": "value1",
            "setting2": 42
        }
    }
}
```

## Configuration Management

### Configuration Sources

The system supports multiple configuration sources:

1. **JSON Files**:
```json
{
    "browser": {"headless": true},
    "selectors": {"title": "h1"}
}
```

2. **YAML Files**:
```yaml
browser:
  headless: true
selectors:
  title: h1
```

3. **Environment Variables**:
```bash
export BROWSER_HEADLESS=true
export SELECTORS_TITLE=h1
```

4. **Command Line Arguments**:
```bash
python scraper.py --browser.headless --selectors.title h1
```

### Configuration Hierarchy

Configuration is loaded in this priority order (highest to lowest):

1. Command line arguments
2. Environment variables
3. Site-specific configuration files
4. Global configuration files
5. Default values

### Configuration Validation

```python
from src.sites.base.config_schemas import ConfigSchema

# Define schema
schema = ConfigSchema({
    "browser": {
        "headless": {"type": "boolean", "default": False},
        "viewport": {
            "width": {"type": "integer", "min": 800, "max": 3840},
            "height": {"type": "integer", "min": 600, "max": 2160}
        }
    }
})

# Validate configuration
validator = ConfigValidator()
result = validator.validate(config, schema)
```

## Best Practices

### Component Design

1. **Single Responsibility**: Each component should have one clear purpose
2. **Loose Coupling**: Components should depend on abstractions, not implementations
3. **High Cohesion**: Related functionality should be grouped together
4. **Interface Segregation**: Small, focused interfaces are preferred
5. **Dependency Inversion**: Depend on abstractions, not concrete classes

### Error Handling

```python
from src.sites.base.component_interface import ComponentResult

async def safe_execute(self, context, **kwargs):
    try:
        # Component logic
        result = await self._execute_internal(context, **kwargs)
        return ComponentResult(success=True, data=result)
    except Exception as e:
        self.logger.error(f"Component execution failed: {e}")
        return ComponentResult(
            success=False,
            errors=[str(e)],
            metadata={"error_type": type(e).__name__}
        )
```

### Performance Optimization

1. **Async Operations**: Use async/await for I/O operations
2. **Connection Pooling**: Reuse browser instances when possible
3. **Caching**: Cache frequently accessed data
4. **Resource Management**: Properly clean up resources
5. **Batch Operations**: Process items in batches when possible

### Testing

```python
import unittest
from unittest.mock import Mock, AsyncMock

class TestMyComponent(unittest.TestCase):
    async def test_component_execution(self):
        component = MyComponent("test")
        context = Mock()
        
        result = await component.execute(context)
        
        self.assertTrue(result.success)
        self.assertIn("expected_key", result.data)
```

## Advanced Features

### Plugin Sandboxing

Execute plugins in isolated environments:

```python
from src.sites.base.plugin_sandbox import PluginSandbox, SandboxConfig, SandboxType

# Configure sandbox
config = SandboxConfig(
    sandbox_type=SandboxType.PROCESS,
    security_level=SecurityLevel.STANDARD,
    resource_limits={
        "max_memory_mb": 512,
        "max_execution_time_seconds": 30
    }
)

# Create sandbox
sandbox = PluginSandbox(config)

# Execute plugin in sandbox
result = await sandbox.execute_plugin(plugin, context, HookType.AFTER_EXTRACT)
```

### Telemetry and Monitoring

Collect metrics and monitor performance:

```python
from src.sites.base.plugin_telemetry import record_metric, record_execution

# Record custom metrics
record_metric("my_component", "operations_completed", 1)

# Record execution metrics
record_execution("my_component", 150.5, True)

# Get telemetry data
from src.sites.base.plugin_telemetry import generate_report
report = generate_report("my_component")
```

### Hot Reloading

Automatically reload configuration changes:

```python
from src.sites.base.config_hot_reload import ConfigHotReloader

# Enable hot reloading
reloader = ConfigHotReloader()
await reloader.start_monitoring("config.json")

# Configuration changes will be automatically reloaded
```

### Version Compatibility

Ensure plugin compatibility:

```python
from src.sites.base.plugin_compatibility import PluginCompatibilityChecker

checker = PluginCompatibilityChecker()

# Check plugin compatibility
result = checker.check_plugin_compatibility("my_plugin")
print(f"Compatibility: {result.status.value}")
```

## Troubleshooting

### Common Issues

1. **Plugin Not Loading**:
   - Check plugin registration
   - Verify plugin metadata
   - Check for import errors
   - Review plugin dependencies

2. **Configuration Not Loading**:
   - Verify file paths
   - Check file permissions
   - Validate JSON/YAML syntax
   - Review configuration hierarchy

3. **Performance Issues**:
   - Monitor resource usage
   - Check for memory leaks
   - Review plugin execution time
   - Optimize database queries

4. **Browser Issues**:
   - Check browser configuration
   - Verify network connectivity
   - Review selector accuracy
   - Check for anti-bot detection

### Debug Mode

Enable debug mode for detailed logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# Enable debug mode in scraper
scraper = ModularSiteScraper("example_site", debug=True)
```

### Plugin Debugging

Debug plugin execution:

```python
# Enable plugin debugging
plugin = MyPlugin()
await plugin.initialize(context)

# Execute with debugging
result = await plugin.execute(context, HookType.AFTER_EXTRACT)
print(f"Plugin result: {result}")
```

## Migration Guide

### From Flat Template to Modular

1. **Identify Components**:
   ```python
   # Old flat template
   class WikipediaScraper:
       def scrape_title(self):
           return self.page.locator("h1").text
   
   # Modular approach
   class TitleExtractor(BaseComponent):
       async def extract(self, context, **kwargs):
           return {"title": context.page.locator("h1").text}
   ```

2. **Create Configuration**:
   ```json
   {
     "components": {
       "title_extractor": {
           "selector": "h1",
           "attribute": "text"
       }
     }
   }
   ```

3. **Update Scraper**:
   ```python
   # Old approach
   scraper = WikipediaScraper()
   
   # Modular approach
   scraper = ModularSiteScraper("wikipedia")
   await scraper.initialize(config)
   ```

### Migration Tools

Use the migration tools to automate the conversion:

```bash
python tools/migration/convert_flat_template.py \
    --input old_scraper.py \
    --output modular_scraper.py \
    --config migration_config.json
```

## Examples

### Basic Web Scraper

```python
from src.sites.base.site_scraper import ModularSiteScraper

class BlogScraper(ModularSiteScraper):
    def __init__(self):
        super().__init__("blog")
    
    async def scrape_article(self, url):
        await self.navigate(url)
        
        # Extract data using components
        title = await self.extract_component("title")
        content = await self.extract_component("content")
        author = await self.extract_component("author")
        
        return {
            "title": title,
            "content": content,
            "author": author
        }

# Usage
scraper = BlogScraper()
await scraper.initialize()
article = await scraper.scrape_article("https://blog.example.com/article")
```

### E-commerce Scraper

```python
class EcommerceScraper(ModularSiteScraper):
    def __init__(self):
        super().__init__("ecommerce")
    
    async def scrape_product(self, url):
        await self.navigate(url)
        
        # Extract product data
        product_data = await self.extract_component("product_info")
        price = await self.extract_component("price")
        availability = await self.extract_component("availability")
        reviews = await self.extract_component("reviews")
        
        return {
            "product": product_data,
            "price": price,
            "availability": availability,
            "reviews": reviews
        }
```

### API Integration

```python
from src.sites.base.plugin_interface import BasePlugin, HookType

class APIIntegrationPlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            id="api_integration",
            name="API Integration Plugin",
            plugin_type=PluginType.CUSTOM,
            hooks=[HookType.AFTER_EXTRACT]
        )
    
    async def execute(self, context, hook_type, **kwargs):
        if hook_type == HookType.AFTER_EXTRACT:
            data = kwargs.get('extracted_data', {})
            
            # Send to API
            await self._send_to_api(data)
            
            return PluginResult(
                success=True,
                data={"api_sent": True}
            )
    
    async def _send_to_api(self, data):
        # API integration logic
        pass
```

### Custom Validation Plugin

```python
class CustomValidationPlugin(BasePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            id="custom_validation",
            name="Custom Validation Plugin",
            plugin_type=PluginType.VALIDATION,
            hooks=[HookType.AFTER_EXTRACT]
        )
    
    async def execute(self, context, hook_type, **kwargs):
        if hook_type == HookType.AFTER_EXTRACT:
            data = kwargs.get('extracted_data', {})
            
            # Custom validation logic
            validation_result = self._validate_data(data)
            
            return PluginResult(
                success=validation_result['valid'],
                data=validation_result
            )
    
    def _validate_data(self, data):
        # Custom validation implementation
        return {"valid": True, "errors": []}
```

This comprehensive guide provides everything needed to effectively use and extend the modular template system for creating powerful, maintainable web scrapers.
