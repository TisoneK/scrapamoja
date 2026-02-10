# Quickstart Guide: YAML-Based Selector Configuration System

**Date**: 2025-01-27  
**Feature**: YAML-Based Selector Configuration System  
**Phase**: 1 - Design & Contracts

## Overview

This guide provides a quick introduction to using the YAML-based selector configuration system. It covers basic setup, configuration file creation, and common usage patterns.

## Quick Start

### 1. Basic Configuration Structure

Create your first selector configuration file:

```yaml
# src/selectors/config/match/header.yaml
metadata:
  version: "1.0"
  last_updated: "2025-01-27"
  description: "Match page header selectors"

context_defaults:
  page_type: "match"
  section: "header"
  wait_strategy: "network_idle"
  timeout: 10000

selectors:
  home_team:
    description: "Home team name extraction"
    context: "match.header"
    strategies:
      - type: "text_anchor"
        pattern: "Home Team"
        position: "after"
      - type: "attribute_match"
        attribute: "data-home-team"
    validation:
      required: true
      type: "string"
    confidence:
      threshold: 0.8
      weight: 1.0

  away_team:
    description: "Away team name extraction"
    context: "match.header"
    strategies:
      - type: "text_anchor"
        pattern: "Away Team"
        position: "after"
    validation:
      required: true
      type: "string"
    confidence:
      threshold: 0.8
      weight: 1.0
```

### 2. Initialize Configuration System

```python
from src.selectors.engine.configuration import ConfigurationSystem

async def main():
    # Initialize configuration system
    config_system = ConfigurationSystem()
    await config_system.initialize("src/selectors/config/")
    
    # Use semantic selector resolution
    selector = config_system.get_selector("home_team", context="match.header")
    result = await selector.resolve(dom_context)
    
    print(f"Found: {result.value} (confidence: {result.confidence})")
```

## Configuration File Organization

### Navigation Hierarchy

Organize files following the navigation hierarchy:

```
src/selectors/config/
├── _global.yaml              # Global defaults and templates
├── main/
│   ├── sport.yaml
│   └── _context.yaml         # Main-level context defaults
├── fixture/
│   ├── listings.yaml
│   └── _context.yaml         # Fixture-level context defaults
├── match/
│   ├── header.yaml
│   ├── _context.yaml         # Match-level context defaults
│   └── tabs/
│       ├── primary/
│       │   ├── summary.yaml
│       │   ├── odds.yaml
│       │   ├── h2h.yaml
│       │   └── _context.yaml
│       ├── secondary/
│       │   ├── stats.yaml
│       │   ├── lineups.yaml
│       │   ├── standings.yaml
│       │   └── _context.yaml
│       └── tertiary/
│           ├── history.yaml
│           ├── records.yaml
│           └── _context.yaml
```

### Context Defaults

Define reusable context defaults in `_context.yaml` files:

```yaml
# src/selectors/config/match/_context.yaml
context_defaults:
  page_type: "match"
  wait_strategy: "network_idle"
  timeout: 10000

validation_defaults:
  required: false
  type: "string"
  min_length: 1

strategy_templates:
  team_name:
    type: "text_anchor"
    validation:
      pattern: "^[A-Za-z\\s]+$"
    confidence:
      threshold: 0.75
```

## Advanced Features

### Strategy Templates

Create reusable strategy templates:

```yaml
# src/selectors/config/match/_context.yaml
strategy_templates:
  team_name:
    type: "text_anchor"
    validation:
      pattern: "^[A-Za-z\\s]+$"
    confidence:
      threshold: 0.75
      
  score_value:
    type: "attribute_match"
    validation:
      type: "number"
      min_value: 0
    confidence:
      threshold: 0.9
```

Reference templates in selectors:

```yaml
# src/selectors/config/match/header.yaml
selectors:
  home_team:
    description: "Home team name"
    strategies:
      - template: "team_name"
        parameters:
          pattern: "Home"
    # Inherits validation and confidence from template
```

### Inheritance

Child selectors inherit from parent context defaults:

```yaml
# src/selectors/config/match/tabs/primary/summary.yaml
# Inherits from match/_context.yaml and tabs/primary/_context.yaml

selectors:
  match_score:
    description: "Current match score"
    # Inherits context_defaults: page_type="match", wait_strategy="network_idle"
    strategies:
      - template: "score_value"
        parameters:
          attribute: "data-score"
    # Inherits validation_defaults: required=false, type="string"
    validation:
      required: true  # Override: this selector is required
```

### Semantic Resolution

Resolve selectors by semantic name, not file location:

```python
# These all resolve to the same selector regardless of file organization
selector1 = config_system.get_selector("home_team", context="match.header")
selector2 = config_system.get_selector("home_team")  # Uses current context
selector3 = config_system.get_selector("match.header.home_team")  # Fully qualified
```

## Common Patterns

### Multi-Strategy Selectors

Define fallback strategies for robustness:

```yaml
selectors:
  kickoff_time:
    description: "Match kickoff time"
    strategies:
      - type: "text_anchor"
        pattern: "Kickoff"
        position: "after"
        priority: 1
      - type: "attribute_match"
        attribute: "data-kickoff"
        priority: 2
      - type: "css_selector"
        selector: ".kickoff-time"
        priority: 3
    confidence:
      threshold: 0.7  # Lower threshold for fallback strategies
```

### Context-Specific Selectors

Define selectors that work in different contexts:

```yaml
# src/selectors/config/match/tabs/primary/odds.yaml
selectors:
  home_win_odds:
    description: "Home team win odds"
    context: "match.tabs.primary.odds"
    strategies:
      - type: "text_anchor"
        pattern: "Home Win"
        position: "after"
    validation:
      type: "number"
      min_value: 1.0
```

### Validation Rules

Define comprehensive validation:

```yaml
selectors:
  match_status:
    description: "Match status (live, finished, scheduled)"
    strategies:
      - type: "attribute_match"
        attribute: "data-status"
    validation:
      required: true
      type: "string"
      pattern: "^(live|finished|scheduled|postponed)$"
      custom_rules:
        status_transition: true  # Custom validation rule
```

## Hot-Reloading

The configuration system automatically detects and reloads changes:

```python
# Configuration system monitors files for changes
# Changes are applied without restarting the application

# Modify src/selectors/config/match/header.yaml
# System detects change within 1 second
# Selector registry is updated automatically
# New selectors are available immediately
```

### Error Handling

Invalid configurations don't crash the system:

```yaml
# Invalid YAML - syntax error
selectors:
  home_team:
    strategies:
      - type: "text_anchor"
        pattern: "Home Team"  # Missing closing quote
```

Result:
- Error logged with file location and line number
- Previous valid configuration remains active
- System continues operating with last known good configuration

## Performance Optimization

### Caching

The system automatically caches resolved selectors:

```python
# First lookup - loads from file, resolves inheritance
selector1 = config_system.get_selector("home_team")  # ~10ms

# Subsequent lookups - uses cache
selector2 = config_system.get_selector("home_team")  # ~1ms

# Cache is automatically updated on configuration changes
```

### Lazy Loading

Configurations are loaded on-demand:

```python
# Only loads configurations when first accessed
await config_system.initialize("src/selectors/config/")  # Fast startup

# First access to match selectors loads match configuration
selector = config_system.get_selector("home_team")  # Triggers load
```

## Migration Guide

### From Hardcoded Selectors

Replace hardcoded selectors:

```python
# Before (hardcoded)
HOME_TEAM_SELECTOR = "//div[@class='home-team']"

# After (YAML configuration)
selector = config_system.get_selector("home_team", context="match.header")
```

### Gradual Migration

1. **Create YAML files** for existing selectors
2. **Update code** to use configuration system
3. **Remove hardcoded selectors** from code
4. **Test** with both systems during transition
5. **Remove** old hardcoded selectors completely

## Troubleshooting

### Common Issues

1. **Selector not found**: Check semantic name and context
2. **Inheritance not working**: Verify `_context.yaml` files exist
3. **Template not found**: Ensure template is defined in inheritance chain
4. **Validation failing**: Check validation rules and data types

### Debug Information

Enable debug logging:

```python
import logging
logging.getLogger("selectors.configuration").setLevel(logging.DEBUG)

# Logs configuration loading, inheritance resolution, and selector lookup
```

### Configuration Validation

Validate configuration files:

```python
# Validate all configurations
results = await config_system.validate_all_configurations()
for file_path, result in results.items():
    if not result.is_valid:
        print(f"Errors in {file_path}: {result.errors}")
```

This quickstart guide provides the essential information for getting started with the YAML-based selector configuration system. For more detailed information, refer to the full specification and API contracts.
