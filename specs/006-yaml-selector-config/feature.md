# YAML-Based Selector Configuration System

## Feature Overview

Introduce a selector configuration system that externalizes all selector definitions into YAML files organized using a hierarchical folder structure mirroring selector intent, context, and scope. This feature formalizes selector storage, discovery, and evolution while improving clarity, navigation, and long-term maintainability.

## Core Rule

**Selectors must be defined declaratively in YAML files and must not be hardcoded elsewhere in the system.**

The Selector Engine is the only component allowed to load, interpret, and resolve these files.

## Structural Organization Rules

### Folder-Based Semantic Grouping

Selector YAML files must be grouped by domain and context using the progressive navigation hierarchy:

```
src/selectors/config/
  main/
    sport.yaml
  fixture/
    listings.yaml
  match/
    header.yaml
    tabs/
      primary/
        summary.yaml
        odds.yaml
        h2h.yaml
      secondary/
        stats.yaml
        lineups.yaml
        standings.yaml
      tertiary/
        history.yaml
        records.yaml
```

**Folder Structure Principles:**
- Folders represent semantic scope, not implementation
- Folder names describe what the selector is about, not how it is resolved
- No quality-based or marketing language in folder or file names
- Follow the navigation hierarchy: Main → Sport → Fixture → Match → Primary Tabs → Secondary Tabs → Tertiary Tabs

### YAML Selector Definition Requirements

Each YAML file must define selectors as semantic units, not raw selectors. Each selector entry must include:

- A semantic identifier (business meaning)
- A context scope (e.g. match header, odds tab)
- One or more resolution strategies
- Optional validation and confidence hints

**Example YAML Structure:**
```yaml
# match/header.yaml
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

### Selector Inheritance & Reuse

Parent folders may define:
- Shared context constraints
- Default validation rules
- Common strategy templates

Child selectors inherit these unless explicitly overridden.

**Example Parent Configuration:**
```yaml
# match/_context.yaml
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

## Selector Engine Responsibilities

The Selector Engine must:
1. **Discover** selector YAML files recursively under `src/selectors/config/`
2. **Load and validate** selector schemas at startup
3. **Resolve selectors by semantic name**, not file path
4. **Support selector lookup** independent of physical file location
5. **Treat YAML files as authoritative** selector definitions

Other system components:
- Must never read selector YAML files directly
- Must never embed DOM selectors internally

## Change Management Rules

- Selector changes are configuration changes, not code changes
- YAML selector files are versioned and reviewable independently
- Structural reorganization of selector folders must not break semantic selector references

## Navigation Hierarchy Compliance

All pages, views, and selectors must align to the progressive navigation hierarchy:

```
Main Page
  → Sport
    → Fixture / Listings
      → Match Page
        → Primary Tabs
          → Secondary Tabs
            → Tertiary Tabs
              → (Further nested tabs if present)
```

**Structural Principles:**
- Each level inherits context from its parent level
- No level may assume information from a sibling level
- Deeper levels must not redefine higher-level scope
- Selectors and configurations must be scoped to the lowest valid level
- Folder and file organization must reflect this hierarchy exactly

## Naming Rules

Use structural, neutral terms only. Avoid qualitative, temporal, or comparative naming.

**Allowed:**
- main, sport, fixture, match
- tabs, subtabs, sections
- primary, secondary, tertiary
- overview, details, stats, markets, history

**Disallowed:**
- advanced, updated, new, legacy
- final, best, extra
- v2, v3 (unless versioning is explicit and formal)

## Enforcement Statement

Any selector logic found outside the Selector Engine or outside the YAML configuration system is considered a constitutional violation.

## Technical Requirements

### File System Structure
```
src/selectors/config/
├── _global.yaml              # Global defaults and shared templates
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

### YAML Schema Definition

Each selector YAML file follows this schema:

```yaml
# File metadata
metadata:
  version: "1.0"
  last_updated: "2025-01-27"
  description: "Match header selectors"

# Context defaults for this level
context_defaults:
  page_type: "match"
  section: "header"
  wait_strategy: "network_idle"
  timeout: 10000

# Validation defaults for this level
validation_defaults:
  required: false
  type: "string"
  min_length: 1

# Strategy templates for this level
strategy_templates:
  team_name:
    type: "text_anchor"
    validation:
      pattern: "^[A-Za-z\\s]+$"
    confidence:
      threshold: 0.75

# Selector definitions
selectors:
  selector_name:
    description: "Human-readable description"
    context: "match.header"
    strategies:
      - type: "strategy_type"
        # Strategy-specific parameters
    validation:
      # Validation rules (inherits from defaults)
    confidence:
      # Confidence scoring (inherits from defaults)
```

## Integration Points

### Selector Engine Modifications
1. **ConfigurationLoader**: Load and parse YAML files
2. **SelectorRegistry**: Register selectors by semantic name
3. **ContextResolver**: Resolve context inheritance
4. **ValidationEngine**: Apply validation rules from YAML
5. **ConfidenceCalculator**: Use confidence weights from YAML

### New Components
1. **YAMLSchemaValidator**: Validate YAML file structure
2. **ConfigurationWatcher**: Monitor for configuration changes
3. **InheritanceResolver**: Handle parent-child inheritance
4. **SemanticIndex**: Map semantic names to file locations

## Success Criteria

1. **All selectors externalized** to YAML files
2. **No hardcoded selectors** in application code
3. **Hierarchical organization** follows navigation structure
4. **Inheritance system** reduces duplication by 80%
5. **Semantic lookup** works independent of file location
6. **Configuration changes** don't require code deployment
7. **Schema validation** prevents malformed configurations
8. **Performance impact** is minimal (<5% overhead)

## Implementation Phases

### Phase 1: Core Infrastructure
- YAML schema definition and validation
- Basic file loading and parsing
- Simple selector registration

### Phase 2: Inheritance System
- Parent-child context inheritance
- Template system for shared strategies
- Validation rule inheritance

### Phase 3: Advanced Features
- Configuration hot-reloading
- Semantic indexing and lookup optimization
- Performance monitoring and caching

### Phase 4: Migration & Integration
- Migrate existing hardcoded selectors
- Update Selector Engine integration
- Comprehensive testing and validation
- Performance optimization and tuning

## Constitution Compliance

This feature aligns with the following constitution principles:

1. **Selector-First Engineering**: Formalizes selector definitions as first-class configuration artifacts
2. **Deep Modularity**: Separates selector configuration from execution logic
3. **Test-First Validation**: YAML schema validation ensures configuration quality
4. **Production Resilience**: Configuration changes without code deployment
5. **Neutral Naming Convention**: Enforces structural, descriptive naming throughout

## Dependencies

- **Selector Engine**: Must be modified to load from YAML
- **Configuration System**: Integration with existing configuration management
- **Validation Framework**: Extend to support YAML-based validation rules
- **Logging System**: Add configuration loading and validation events

## Risks and Mitigations

### Risks
1. **Performance overhead** from file loading and parsing
2. **Configuration complexity** may become unmanageable
3. **Migration effort** for existing hardcoded selectors
4. **Schema evolution** challenges

### Mitigations
1. **Caching and lazy loading** for performance
2. **Tooling and validation** to manage complexity
3. **Automated migration tools** and gradual transition
4. **Versioned schemas** and backward compatibility
