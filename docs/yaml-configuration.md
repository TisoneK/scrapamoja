# YAML-Based Selector Configuration System

## Overview

The YAML-Based Selector Configuration System externalizes all selector definitions from hardcoded application logic into YAML configuration files. This system supports hierarchical organization, inheritance, semantic resolution, and hot-reloading capabilities.

## Architecture

### Core Components

1. **Configuration Loader** (`src/selectors/engine/configuration/loader.py`)
   - Loads and validates YAML configuration files
   - Handles recursive directory scanning
   - Provides error handling and rollback capabilities

2. **Inheritance Resolver** (`src/selectors/engine/configuration/inheritance.py`)
   - Resolves configuration inheritance from parent folders
   - Handles context defaults and strategy templates
   - Detects circular references and conflicts

3. **Semantic Index** (`src/selectors/engine/configuration/index.py`)
   - Provides fast semantic selector lookup
   - Supports context-aware resolution
   - Handles conflict detection and management

4. **File Watcher** (`src/selectors/engine/configuration/watcher.py`)
   - Monitors configuration file changes
   - Triggers hot-reload operations
   - Provides rollback on validation failures

5. **Enhanced Registry** (`src/selectors/engine/registry.py`)
   - Integrates all configuration components
   - Manages configuration lifecycle
   - Provides statistics and health monitoring

6. **Enhanced Resolver** (`src/selectors/engine/resolver.py`)
   - Resolves selectors with inheritance applied
   - Provides context-aware disambiguation
   - Calculates confidence scores

## Configuration Structure

### Directory Organization

```
src/selectors/config/
├── main/                    # Main page selectors
├── fixture/                 # Fixture/match list selectors
├── match/                   # Match detail selectors
│   └── tabs/               # Tab-specific selectors
│       ├── primary/
│       ├── secondary/
│       └── tertiary/
└── _context.yaml           # Root context defaults
```

### Configuration File Format

```yaml
metadata:
  version: "1.0.0"
  last_updated: "2025-01-27T17:00:00Z"
  description: "Configuration description"

context_defaults:
  page_type: "main"
  wait_strategy: "network_idle"
  timeout: 10000
  section: "navigation"

validation_defaults:
  required: true
  type: "string"
  min_length: 1

strategy_templates:
  navigation_link:
    type: "css_selector"
    parameters:
      selector: "a[href]"
    validation:
      required: true
      type: "string"
    confidence:
      threshold: 0.8

selectors:
  main_navigation:
    description: "Main navigation menu"
    context: "main.navigation"
    strategies:
      - type: "css_selector"
        parameters:
          selector: "nav.main-nav, .navigation"
        priority: 1
    validation:
      required: true
      type: "object"
    confidence:
      threshold: 0.8
```

## Key Features

### 1. Hierarchical Inheritance

Configuration files inherit context defaults and strategy templates from parent folders:

```yaml
# match/_context.yaml (parent)
context_defaults:
  page_type: "match"
  timeout: 10000

strategy_templates:
  match_element:
    type: "css_selector"
    parameters:
      selector: ".match"

# match/tabs/primary/match_overview.yaml (child)
# Inherits context_defaults and strategy_templates from parent
# Can override specific values if needed
```

### 2. Semantic Resolution

Selectors are resolved by semantic name, independent of file location:

```python
from src.selectors.engine.configuration import get_configuration_integration

integration = get_configuration_integration()
await integration.initialize_from_config(Path("src/selectors/config"))

# Resolve selector by semantic name
result = await integration.resolve_selector_with_config(
    "main_navigation",
    page_type="main",
    section="navigation"
)
```

### 3. Strategy Templates

Reusable strategy definitions reduce duplication:

```yaml
strategy_templates:
  team_name:
    type: "css_selector"
    parameters:
      selector: ".team-name, .team"

selectors:
  home_team:
    strategies:
      - template: "team_name"  # Uses template
        priority: 1
      - type: "css_selector"  # Override with specific selector
        parameters:
          selector: ".home-team"
        priority: 2
```

### 4. Hot-Reloading

Configuration changes are detected and applied without application restart:

```python
# File changes are automatically detected
# Configuration is validated before applying
# Rollback occurs on validation failure
# Semantic index is updated incrementally
```

## Usage Guide

### Initialization

```python
from src.selectors.engine.configuration import get_configuration_integration
from pathlib import Path

# Get the global configuration integration
integration = get_configuration_integration()

# Initialize with configuration root
await integration.initialize_from_config(Path("src/selectors/config"))
```

### Selector Resolution

```python
# Basic resolution
result = await integration.resolve_selector_with_config(
    semantic_name="page_title",
    page_type="main",
    section="content"
)

# With context
result = await integration.resolve_selector_with_config(
    semantic_name="home_team",
    page_type="fixture",
    section="list",
    tab_context="primary"
)
```

### Getting Available Selectors

```python
# Get selectors for a context
selectors = integration.get_available_selectors("main", "navigation")

# Validate selector context
is_valid = integration.validate_selector_context("page_title", "main", "content")

# Get suggestions
suggestions = integration.enhanced_resolver.suggest_selectors("nav", "main", limit=5)
```

### Monitoring and Statistics

```python
# Get configuration statistics
stats = integration.get_configuration_stats()
print(f"Loaded {stats.total_selectors} selectors from {stats.total_configurations} files")

# Get hot-reload status
reload_status = await integration.enhanced_registry.get_hot_reload_status()
print(f"Hot-reload enabled: {reload_status['hot_reload_enabled']}")

# Get system health
health = integration.get_integration_health()
print(f"System healthy: {health['healthy']}")
```

## Configuration Validation

### Schema Validation

All configuration files are validated against the expected schema:

- Required sections must be present
- Field types and formats are validated
- Strategy templates must be properly defined
- Selector definitions must be complete

### Inheritance Validation

Inheritance chains are validated for:

- Circular references
- Conflicting defaults
- Template compatibility
- Breaking changes during reload

### Runtime Validation

Selectors are validated during resolution:

- Context appropriateness
- Strategy availability
- Parameter compatibility
- Confidence thresholds

## Performance Considerations

### Loading Performance

- **Target**: <100ms per configuration file
- **Optimization**: Parallel loading of multiple files
- **Caching**: Inheritance chains and resolved selectors

### Lookup Performance

- **Target**: <10ms semantic selector lookup
- **Optimization**: Semantic indexing with context awareness
- **Caching**: Frequently accessed selectors

### Hot-Reload Performance

- **Target**: <2s for complete hot-reload cycle
- **Optimization**: Incremental index updates
- **Validation**: Fast schema validation

## Error Handling

### Configuration Errors

```python
try:
    config = await loader.load_configuration(file_path)
except SchemaValidationException as e:
    print(f"Schema validation failed: {e.validation_errors}")
except ConfigurationException as e:
    print(f"Configuration error: {e.message}")
```

### Resolution Errors

```python
try:
    result = await integration.resolve_selector_with_config(name, page, section)
except ValueError as e:
    print(f"Selector not found: {e}")
except Exception as e:
    print(f"Resolution error: {e}")
```

### Hot-Reload Errors

- Invalid configurations are automatically rolled back
- Error details are logged with correlation IDs
- System continues operating with previous valid configuration

## Best Practices

### Configuration Organization

1. **Use Semantic Names**: Choose descriptive, meaningful selector names
2. **Logical Grouping**: Organize selectors by context and usage
3. **Consistent Structure**: Follow the established file format
4. **Clear Documentation**: Provide descriptions for all selectors

### Selector Design

1. **Multiple Strategies**: Provide fallback strategies for robustness
2. **Appropriate Priorities**: Order strategies by reliability
3. **Realistic Confidence**: Set confidence thresholds based on selector stability
4. **Context Awareness**: Use context-specific selectors when needed

### Performance Optimization

1. **Template Usage**: Use strategy templates to reduce duplication
2. **Inheritance Efficiency**: Leverage context defaults effectively
3. **Selective Loading**: Load only necessary configurations
4. **Cache Management**: Monitor and optimize cache usage

## Migration Guide

### From Hardcoded Selectors

1. **Identify Selectors**: Find all hardcoded selector definitions
2. **Create YAML Files**: Organize by context and usage
3. **Define Templates**: Extract common strategy patterns
4. **Test Resolution**: Verify selectors resolve correctly
5. **Update Code**: Replace hardcoded references with configuration calls

### Example Migration

**Before:**
```python
# Hardcoded selector
SELECTORS = {
    "main_navigation": "nav.main-nav, .navigation",
    "page_title": "title, h1, .page-title"
}
```

**After:**
```python
# YAML configuration
# main/page_selectors.yaml
selectors:
  main_navigation:
    context: "main.navigation"
    strategies:
      - type: "css_selector"
        parameters:
          selector: "nav.main-nav, .navigation"

# Code usage
result = await integration.resolve_selector_with_config(
    "main_navigation", "main", "navigation"
)
```

## Troubleshooting

### Common Issues

1. **Configuration Not Found**
   - Check file paths and naming
   - Verify YAML syntax
   - Ensure proper directory structure

2. **Selector Resolution Fails**
   - Check semantic name spelling
   - Verify context matches
   - Review strategy definitions

3. **Hot-Reload Not Working**
   - Verify file monitoring is active
   - Check file permissions
   - Review validation errors

4. **Performance Issues**
   - Monitor cache hit rates
   - Check inheritance chain complexity
   - Review configuration file sizes

### Debugging Tools

```python
# Export configuration data for debugging
data = await integration.enhanced_registry.export_configuration_data()

# Get detailed metrics
metrics = integration.enhanced_resolver.get_resolver_stats()

# Validate configuration integrity
issues = integration.enhanced_registry.validate_configuration_integrity()
```

## Integration with Existing Systems

### Selector Engine Integration

```python
from src.selectors.engine.integration import ConfigurationAwareSelectorEngine

# Wrap existing engine with configuration support
engine = ConfigurationAwareSelectorEngine(existing_engine, config_root)

# Use enhanced resolution
result = await engine.resolve_with_config(
    "page_title", "main", "content"
)
```

### Event Integration

```python
# Configuration change events are automatically published
# Subscribe to configuration updates for custom handling
```

## Security Considerations

### File Access

- Configuration files should have appropriate read permissions
- Monitor for unauthorized file modifications
- Validate file paths to prevent directory traversal

### Content Validation

- All YAML content is validated against schema
- Strategy parameters are type-checked
- Selector expressions are sandboxed

### Hot-Reload Security

- Configuration changes are validated before application
- Rollback prevents invalid configurations from persisting
- Audit trail tracks all configuration changes

## Future Enhancements

### Planned Features

1. **Configuration Versioning**: Support for multiple configuration versions
2. **Remote Configuration**: Load configurations from remote sources
3. **Configuration Templates**: Pre-built configuration templates
4. **Visual Editor**: GUI for creating and editing configurations
5. **Advanced Analytics**: Configuration usage and performance analytics

### Extension Points

- Custom strategy types
- Additional validation rules
- Custom inheritance resolvers
- Alternative file formats
