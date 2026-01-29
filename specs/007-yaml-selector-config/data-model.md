# Data Model: YAML-Based Selector Configuration System

**Date**: 2025-01-27  
**Feature**: YAML-Based Selector Configuration System  
**Phase**: 1 - Design & Contracts

## Entity Overview

This data model defines the core entities for the YAML-based selector configuration system, supporting hierarchical organization, inheritance, and semantic resolution.

## Core Entities

### SelectorConfiguration

Represents a complete YAML configuration file with all its components.

**Attributes**:
- `file_path`: str - Absolute path to the YAML file
- `metadata`: ConfigurationMetadata - File metadata and versioning
- `context_defaults`: Optional[ContextDefaults] - Inherited context configuration
- `validation_defaults`: Optional[ValidationDefaults] - Default validation rules
- `strategy_templates`: Dict[str, StrategyTemplate] - Reusable strategy definitions
- `selectors`: Dict[str, SemanticSelector] - Selector definitions
- `parent_path`: Optional[str] - Path to parent configuration for inheritance

**Validation Rules**:
- Must follow navigation hierarchy structure
- All selector names must be unique within scope
- Required fields must be present and valid

### ConfigurationMetadata

Metadata about the configuration file for versioning and tracking.

**Attributes**:
- `version`: str - Schema version (e.g., "1.0")
- `last_updated`: str - ISO date string (e.g., "2025-01-27")
- `description`: str - Human-readable description of file contents

**Validation Rules**:
- Version must follow semantic versioning pattern
- Last_updated must be valid ISO date
- Description must be non-empty string

### ContextDefaults

Default configuration inherited by child selectors and configurations.

**Attributes**:
- `page_type`: str - Page type identifier (e.g., "match", "fixture")
- `wait_strategy`: str - DOM waiting strategy (e.g., "network_idle")
- `timeout`: int - Timeout in milliseconds
- `section`: Optional[str] - Page section identifier

**Validation Rules**:
- Page type must be from allowed values
- Wait strategy must be supported strategy
- Timeout must be positive integer
- Section must be valid navigation hierarchy level

### ValidationDefaults

Default validation rules inherited by selectors.

**Attributes**:
- `required`: bool - Whether selector result is required
- `type`: str - Expected data type (e.g., "string", "number")
- `min_length`: Optional[int] - Minimum length for string values
- `max_length`: Optional[int] - Maximum length for string values
- `pattern`: Optional[str] - Regex pattern for validation

**Validation Rules**:
- Type must be supported data type
- Min/max length must be positive integers
- Pattern must be valid regex if provided

### StrategyTemplate

Reusable strategy definition that can be referenced by multiple selectors.

**Attributes**:
- `type`: str - Strategy type (e.g., "text_anchor", "attribute_match")
- `parameters`: Dict[str, Any] - Strategy-specific parameters
- `validation`: Optional[ValidationRule] - Template-specific validation
- `confidence`: Optional[ConfidenceConfig] - Template confidence settings

**Validation Rules**:
- Type must be supported strategy type
- Required parameters for strategy type must be present
- Validation and confidence must be valid if provided

### SemanticSelector

Individual selector definition with context, strategies, and validation.

**Attributes**:
- `name`: str - Semantic identifier for the selector
- `description`: str - Human-readable description
- `context`: str - Context scope (e.g., "match.header")
- `strategies`: List[StrategyDefinition] - Resolution strategies
- `validation`: Optional[ValidationRule] - Selector-specific validation
- `confidence`: Optional[ConfidenceConfig] - Confidence scoring configuration

**Validation Rules**:
- Name must be valid semantic identifier
- Context must follow navigation hierarchy
- At least one strategy must be defined
- Strategies must be ordered by priority

### StrategyDefinition

Specific strategy instance with parameters.

**Attributes**:
- `type`: str - Strategy type
- `template`: Optional[str] - Reference to strategy template
- `parameters`: Dict[str, Any] - Strategy-specific parameters
- `priority`: int - Strategy priority (lower = higher priority)

**Validation Rules**:
- Either template reference or parameters must be provided
- If template referenced, it must exist in scope
- Parameters must be valid for strategy type

### ValidationRule

Validation configuration for a selector.

**Attributes**:
- `required`: Optional[bool] - Override for required flag
- `type`: Optional[str] - Override for data type
- `min_length`: Optional[int] - Override for minimum length
- `max_length`: Optional[int] - Override for maximum length
- `pattern`: Optional[str] - Override for regex pattern
- `custom_rules`: Dict[str, Any] - Custom validation rules

**Validation Rules**:
- Overrides must be valid for their type
- Custom rules must be supported by validation engine

### ConfidenceConfig

Confidence scoring configuration for selectors.

**Attributes**:
- `threshold`: Optional[float] - Minimum confidence threshold
- `weight`: Optional[float] - Selector weight in context
- `boost_factors`: Dict[str, float] - Context-specific confidence boosts

**Validation Rules**:
- Threshold must be between 0.0 and 1.0
- Weight must be positive number
- Boost factors must have valid keys and values

## Inheritance Model

### InheritanceChain

Represents the inheritance hierarchy for a configuration.

**Attributes**:
- `child_path`: str - Path to child configuration
- `parent_paths`: List[str] - Ordered list of parent paths
- `resolved_context`: ContextDefaults - Merged context defaults
- `resolved_validation`: ValidationDefaults - Merged validation defaults
- `available_templates`: Dict[str, StrategyTemplate] - All available templates

**Validation Rules**:
- No circular references allowed
- Parent order determines inheritance priority
- Merged configuration must be valid

## Resolution Model

### SemanticIndexEntry

Entry in the semantic index for fast lookup.

**Attributes**:
- `semantic_name`: str - Semantic selector name
- `context`: str - Selector context scope
- `file_path`: str - Source configuration file
- `resolved_selector`: SemanticSelector - Fully resolved selector
- `last_modified`: str - File modification timestamp

**Validation Rules**:
- Semantic name must be unique within context
- File path must exist and be accessible
- Resolved selector must be valid

### ResolutionContext

Context for selector resolution operations.

**Attributes**:
- `current_page`: str - Current page type
- `current_section`: str - Current page section
- `tab_context`: Optional[str] - Current tab context
- `navigation_history`: List[str] - Navigation path history

**Validation Rules**:
- Page type must be supported
- Section must be valid for page type
- Tab context must be valid for section

## State Management

### ConfigurationState

Current state of the configuration system.

**Attributes**:
- `loaded_configurations`: Dict[str, SelectorConfiguration] - Loaded configurations
- `semantic_index`: Dict[str, SemanticIndexEntry] - Semantic lookup index
- `inheritance_cache`: Dict[str, InheritanceChain] - Cached inheritance chains
- `last_reload`: str - Timestamp of last hot-reload
- `error_count`: int - Number of configuration errors encountered

**Validation Rules**:
- All loaded configurations must be valid
- Semantic index must be consistent with loaded configurations
- Inheritance cache must be up-to-date

## Relationships

### Primary Relationships

1. **SelectorConfiguration** contains:
   - ConfigurationMetadata (1:1)
   - ContextDefaults (0:1)
   - ValidationDefaults (0:1)
   - StrategyTemplate (0:N)
   - SemanticSelector (1:N)

2. **SemanticSelector** contains:
   - StrategyDefinition (1:N)
   - ValidationRule (0:1)
   - ConfidenceConfig (0:1)

3. **StrategyDefinition** references:
   - StrategyTemplate (0:1)

### Inheritance Relationships

1. **SelectorConfiguration** inherits from:
   - Parent SelectorConfiguration (0:N)

2. **InheritanceChain** connects:
   - Child SelectorConfiguration (1:1)
   - Parent SelectorConfiguration (1:N)

### Index Relationships

1. **SemanticIndexEntry** references:
   - SemanticSelector (1:1)
   - SelectorConfiguration (1:1)

## Validation Summary

All entities include comprehensive validation rules to ensure:
- Schema compliance for YAML files
- Navigation hierarchy adherence
- Inheritance consistency
- Performance requirements satisfaction
- Constitution principle compliance

The data model supports all specified user stories and functional requirements while maintaining the modular, testable, and resilient characteristics required by the constitution.
