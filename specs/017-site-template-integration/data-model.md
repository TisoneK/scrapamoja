# Data Model: Site Template Integration Framework

**Feature**: 017-site-template-integration  
**Date**: 2025-01-29  
**Version**: 1.0

## Core Entities

### SiteTemplate

Represents a standardized site scraper template with framework integration capabilities.

**Attributes**:
- `name` (string): Unique identifier for the template (e.g., "github", "twitter")
- `version` (string): Template version following semantic versioning
- `description` (string): Human-readable description of the template purpose
- `author` (string): Template author/organization
- `created_at` (datetime): Template creation timestamp
- `updated_at` (datetime): Last modification timestamp
- `framework_version` (string): Required framework version compatibility
- `site_domain` (string): Primary domain the template targets (e.g., "github.com")
- `supported_domains` (list[string]): Additional domains supported by template
- `configuration_schema` (object): JSON schema for template-specific configuration

**Relationships**:
- Has many `YAMLSelectorConfiguration`
- Has many `ExtractionRuleSet`
- Has one `IntegrationBridge`

**Validation Rules**:
- `name` must be unique across all templates
- `framework_version` must be compatible with current framework
- `site_domain` must be a valid domain format
- `configuration_schema` must be valid JSON Schema

### IntegrationBridge

Connector that links site-specific components with existing framework infrastructure.

**Attributes**:
- `template_name` (string): Associated template name
- `bridge_type` (enum): Type of integration (SELECTOR_LOADER, EXTRACTOR_BRIDGE, LIFECYCLE_BRIDGE)
- `component_class` (string): Fully qualified class name for the bridge implementation
- `configuration` (object): Bridge-specific configuration
- `enabled` (boolean): Whether the bridge is active
- `priority` (integer): Initialization priority (lower numbers initialize first)

**Relationships**:
- Belongs to `SiteTemplate`
- Manages `YAMLSelectorConfiguration`
- Manages `ExtractionRuleSet`

**Validation Rules**:
- `component_class` must exist and be importable
- `priority` must be non-negative integer
- `bridge_type` must be valid enum value

### YAMLSelectorConfiguration

Site-specific selector definitions that load into existing selector engine.

**Attributes**:
- `template_name` (string): Associated template name
- `selector_name` (string): Unique selector name within template
- `yaml_content` (string): YAML configuration content
- `selector_type` (enum): Type of selector (SEMANTIC, STRUCTURAL, HYBRID)
- `confidence_threshold` (float): Minimum confidence score for acceptance
- `strategies` (list[object]): Multi-strategy resolution configuration
- `validation_rules` (list[object]): Selector validation rules

**Relationships**:
- Belongs to `SiteTemplate`
- Managed by `IntegrationBridge`

**Validation Rules**:
- `yaml_content` must be valid YAML
- `confidence_threshold` must be between 0.0 and 1.0
- `selector_name` must be unique within template
- `strategies` must contain at least one primary strategy

### ExtractionRuleSet

Collection of extraction rules using existing extractor module.

**Attributes**:
- `template_name` (string): Associated template name
- `rule_set_name` (string): Unique rule set name within template
- `rules` (list[object]): Extraction rule definitions
- `output_schema` (object): JSON schema for extracted data
- `transformation_pipeline` (list[object]): Data transformation configuration

**Relationships**:
- Belongs to `SiteTemplate`
- Managed by `IntegrationBridge`

**Validation Rules**:
- `rules` must be valid ExtractionRule objects
- `output_schema` must be valid JSON Schema
- `rule_set_name` must be unique within template

### SiteRegistry

Central registry for discovering and managing available site scrapers.

**Attributes**:
- `registry_version` (string): Registry schema version
- `templates` (list[SiteTemplate]): Registered site templates
- `last_updated` (datetime): Last registry update timestamp
- `discovery_paths` (list[string]): Filesystem paths for template discovery
- `metadata` (object): Registry metadata and configuration

**Relationships**:
- Has many `SiteTemplate`
- Manages `RegistryEntry`

**Validation Rules**:
- `templates` list must not contain duplicate names
- `discovery_paths` must exist and be accessible
- `registry_version` must follow semantic versioning

### RegistryEntry

Metadata entry for a registered site template.

**Attributes**:
- `template_name` (string): Template name
- `entry_type` (enum): Type of entry (TEMPLATE, BRIDGE, VALIDATOR)
- `file_path` (string): Filesystem path to the entry
- `metadata` (object): Entry-specific metadata
- `health_status` (enum): Health status (ACTIVE, INACTIVE, ERROR)
- `last_validated` (datetime): Last validation timestamp

**Relationships**:
- Belongs to `SiteRegistry`
- References `SiteTemplate`

**Validation Rules**:
- `file_path` must exist and be accessible
- `template_name` must match registered template
- `health_status` must be valid enum value

### ValidationFramework

Set of rules and checks for ensuring scraper quality and compliance.

**Attributes**:
- `framework_version` (string): Validation framework version
- `validation_rules` (list[object]): Validation rule definitions
- `schemas` (object): JSON schemas for validation
- `compliance_checks` (list[object]): Framework compliance checks

**Relationships**:
- Validates `SiteTemplate`
- Validates `YAMLSelectorConfiguration`
- Validates `ExtractionRuleSet`

**Validation Rules**:
- `validation_rules` must be valid rule objects
- `schemas` must be valid JSON Schema objects
- `compliance_checks` must reference constitutional principles

## State Transitions

### SiteTemplate Lifecycle

```
CREATED → VALIDATED → REGISTERED → ACTIVE → DEPRECATED → REMOVED
    ↓         ↓          ↓         ↓         ↓         ↓
  [error]   [error]   [error]   [error]   [error]   [error]
```

**States**:
- `CREATED`: Template initially created
- `VALIDATED`: Template passes validation checks
- `REGISTERED`: Template registered in site registry
- `ACTIVE`: Template actively used for scraping
- `DEPRECATED`: Template marked as deprecated
- `REMOVED`: Template removed from registry

### IntegrationBridge Lifecycle

```
INITIALIZED → CONFIGURED → ACTIVE → ERROR → RECOVERED
      ↓          ↓        ↓       ↓        ↓
    [error]    [error]  [error] [retry]  [active]
```

**States**:
- `INITIALIZED`: Bridge initially created
- `CONFIGURED`: Bridge configured with template
- `ACTIVE`: Bridge actively integrating components
- `ERROR`: Bridge encountered error
- `RECOVERED`: Bridge recovered from error

## Data Relationships

### Template Composition

```
SiteTemplate (1) ──── (1) IntegrationBridge
    │                      │
    │                      ├── (1..*) YAMLSelectorConfiguration
    │                      └── (1..*) ExtractionRuleSet
    │
    └── (1..*) RegistryEntry
            │
            └── (1) SiteRegistry
```

### Validation Hierarchy

```
ValidationFramework
    ├── validates → SiteTemplate
    ├── validates → YAMLSelectorConfiguration
    ├── validates → ExtractionRuleSet
    └── validates → IntegrationBridge
```

## Schema Definitions

### SiteTemplate Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["name", "version", "framework_version", "site_domain"],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_-]*$",
      "minLength": 2,
      "maxLength": 50
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "framework_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "site_domain": {
      "type": "string",
      "format": "hostname"
    },
    "supported_domains": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "hostname"
      }
    },
    "configuration_schema": {
      "type": "object",
      "$ref": "https://json-schema.org/draft-07/schema#"
    }
  }
}
```

### YAMLSelectorConfiguration Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["selector_name", "yaml_content", "selector_type"],
  "properties": {
    "selector_name": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*$"
    },
    "yaml_content": {
      "type": "string"
    },
    "selector_type": {
      "enum": ["SEMANTIC", "STRUCTURAL", "HYBRID"]
    },
    "confidence_threshold": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "strategies": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object"
      }
    }
  }
}
```

## Performance Considerations

### Memory Usage

- **SiteTemplate**: ~1KB per template (metadata only)
- **YAMLSelectorConfiguration**: ~5KB per selector (including YAML content)
- **ExtractionRuleSet**: ~3KB per rule set (rule definitions)
- **SiteRegistry**: ~100KB for 100 templates (registry overhead)

### Loading Times

- **Template discovery**: ~50ms for 100 templates (filesystem scan)
- **YAML parsing**: ~10ms per selector configuration
- **Validation**: ~20ms per template (schema validation)
- **Registry initialization**: ~100ms total (including all templates)

### Optimization Strategies

- **Lazy loading**: Load configurations only when needed
- **Caching**: Cache parsed YAML and validation results
- **Indexing**: Index templates by domain and capability
- **Batching**: Batch validation operations for multiple templates

## Security Considerations

### Input Validation

- **YAML content**: Validate against safe YAML parsing rules
- **File paths**: Validate paths are within expected directories
- **Class names**: Validate component classes are allowed and safe
- **Configuration**: Validate all configuration against schemas

### Access Control

- **Template registration**: Controlled access to prevent malicious templates
- **Bridge execution**: Sandboxed execution of integration bridges
- **File system**: Restricted file system access to template directories
- **Network**: Controlled network access for template operations

### Audit Trail

- **Template changes**: Log all template modifications
- **Validation results**: Log validation outcomes and issues
- **Registry operations**: Log all registry modifications
- **Bridge operations**: Log bridge initialization and errors
