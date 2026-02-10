# YAML Selector API Contract

**Feature**: 016-wikipedia-extractor-fix  
**Date**: 2026-01-29  
**Version**: 1.0.0  
**Purpose**: API specification for YAML selector loading and management

## Overview

This document defines the API contracts for the YAML selector loading system. The API provides functionality for loading, validating, registering, and managing YAML-based selectors in the Wikipedia extractor integration.

## Core API Endpoints

### Selector Registry API

#### Load Selectors from Directory

```python
async def load_selectors_from_directory(
    directory_path: str,
    recursive: bool = False,
    validation_mode: ValidationMode = ValidationMode.STRICT
) -> LoadResult
```

**Parameters**:
- `directory_path` (str): Path to directory containing YAML selector files
- `recursive` (bool): Whether to search subdirectories recursively
- `validation_mode` (ValidationMode): Validation strictness level

**Returns**: `LoadResult` containing loading statistics and any errors

**ValidationMode Enum**:
- `STRICT`: Fail on any validation error
- `LENIENT`: Skip invalid selectors with warnings
- `PERMISSIVE`: Load all selectors with minimal validation

#### Load Single Selector File

```python
async def load_selector_from_file(
    file_path: str,
    validation_mode: ValidationMode = ValidationMode.STRICT
) -> SelectorLoadResult
```

**Parameters**:
- `file_path` (str): Path to individual YAML selector file
- `validation_mode` (ValidationMode): Validation strictness level

**Returns**: `SelectorLoadResult` containing loaded selector or error details

#### Get Selector by ID

```python
def get_selector(selector_id: str) -> Optional[YAMLSelector]
```

**Parameters**:
- `selector_id` (str): Unique identifier of the selector

**Returns**: `YAMLSelector` if found, `None` otherwise

#### List All Selectors

```python
def list_selectors(
    filter_type: Optional[SelectorType] = None,
    include_disabled: bool = False
) -> List[YAMLSelector]
```

**Parameters**:
- `filter_type` (Optional[SelectorType]): Filter by selector type
- `include_disabled` (bool): Whether to include disabled selectors

**Returns**: List of `YAMLSelector` objects

#### Reload Selectors

```python
async def reload_selectors(
    selector_ids: Optional[List[str]] = None
) -> ReloadResult
```

**Parameters**:
- `selector_ids` (Optional[List[str]]): Specific selectors to reload, None for all

**Returns**: `ReloadResult` with reload statistics and errors

### Validation API

#### Validate Selector

```python
def validate_selector(
    selector: YAMLSelector,
    validation_mode: ValidationMode = ValidationMode.STRICT
) -> ValidationResult
```

**Parameters**:
- `selector` (YAMLSelector): Selector to validate
- `validation_mode` (ValidationMode): Validation strictness level

**Returns**: `ValidationResult` with validation status and errors

#### Validate Selector File

```python
async def validate_selector_file(
    file_path: str,
    validation_mode: ValidationMode = ValidationMode.STRICT
) -> FileValidationResult
```

**Parameters**:
- `file_path` (str): Path to YAML selector file
- `validation_mode` (ValidationMode): Validation strictness level

**Returns**: `FileValidationResult` with file validation status

### Statistics API

#### Get Loading Statistics

```python
def get_loading_statistics() -> LoadingStatistics
```

**Returns**: `LoadingStatistics` with comprehensive loading metrics

#### Get Selector Usage Statistics

```python
def get_usage_statistics(
    time_range: Optional[TimeRange] = None
) -> UsageStatistics
```

**Parameters**:
- `time_range` (Optional[TimeRange]): Time range for usage data

**Returns**: `UsageStatistics` with selector usage metrics

### Configuration API

#### Configure Registry

```python
def configure_registry(
    cache_enabled: bool = True,
    hot_reload_enabled: bool = False,
    validation_mode: ValidationMode = ValidationMode.STRICT,
    performance_monitoring: bool = True
) -> ConfigurationResult
```

**Parameters**:
- `cache_enabled` (bool): Enable selector caching
- `hot_reload_enabled` (bool): Enable hot-reloading for development
- `validation_mode` (ValidationMode): Default validation mode
- `performance_monitoring` (bool): Enable performance monitoring

**Returns**: `ConfigurationResult` with configuration status

## Data Models

### YAMLSelector

```python
@dataclass
class YAMLSelector:
    id: str
    name: str
    description: Optional[str]
    selector_type: SelectorType
    pattern: str
    strategies: List[SelectorStrategy]
    validation_rules: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    file_path: str
    loaded_at: datetime
    version: str
    
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'YAMLSelector': ...
    def validate(self) -> ValidationResult: ...
```

### SelectorStrategy

```python
@dataclass
class SelectorStrategy:
    type: StrategyType
    priority: int
    config: Dict[str, Any]
    confidence_threshold: float
    enabled: bool = True
    
    def validate(self) -> ValidationResult: ...
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SelectorStrategy': ...
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[SelectorValidationError]
    warnings: List[SelectorValidationError]
    
    @property
    def has_errors(self) -> bool: ...
    @property
    def has_warnings(self) -> bool: ...
```

### SelectorValidationError

```python
@dataclass
class SelectorValidationError:
    selector_id: str
    error_type: ErrorType
    field_path: str
    error_message: str
    suggested_fix: Optional[str]
    severity: Severity
    timestamp: datetime
```

### LoadResult

```python
@dataclass
class LoadResult:
    success: bool
    selectors_loaded: int
    selectors_failed: int
    errors: List[SelectorValidationError]
    warnings: List[SelectorValidationError]
    loading_time_ms: float
    
    @property
    def total_selectors(self) -> int: ...
    @property
    def success_rate(self) -> float: ...
```

### LoadingStatistics

```python
@dataclass
class LoadingStatistics:
    total_selectors: int
    enabled_selectors: int
    disabled_selectors: int
    selectors_by_type: Dict[SelectorType, int]
    average_loading_time_ms: float
    last_loaded: datetime
    cache_hit_rate: float
    validation_errors: int
    validation_warnings: int
```

## Enums

### SelectorType

```python
class SelectorType(Enum):
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ATTRIBUTE = "attribute"
```

### StrategyType

```python
class StrategyType(Enum):
    TEXT_ANCHOR = "text_anchor"
    ATTRIBUTE_MATCH = "attribute_match"
    DOM_RELATIONSHIP = "dom_relationship"
    ROLE_BASED = "role_based"
```

### ErrorType

```python
class ErrorType(Enum):
    SYNTAX_ERROR = "syntax_error"
    STRUCTURE_ERROR = "structure_error"
    VALIDATION_ERROR = "validation_error"
    FILE_ERROR = "file_error"
    CONFIGURATION_ERROR = "configuration_error"
```

### Severity

```python
class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
```

### ValidationMode

```python
class ValidationMode(Enum):
    STRICT = "strict"
    LENIENT = "lenient"
    PERMISSIVE = "permissive"
```

## Events

### Selector Loading Events

#### SelectorLoaded

```python
@dataclass
class SelectorLoadedEvent:
    selector_id: str
    selector_type: SelectorType
    file_path: str
    loading_time_ms: float
    timestamp: datetime
```

#### SelectorLoadFailed

```python
@dataclass
class SelectorLoadFailedEvent:
    selector_id: Optional[str]
    file_path: str
    error_type: ErrorType
    error_message: str
    timestamp: datetime
```

#### SelectorValidationFailed

```python
@dataclass
class SelectorValidationFailedEvent:
    selector_id: str
    validation_errors: List[SelectorValidationError]
    validation_warnings: List[SelectorValidationError]
    timestamp: datetime
```

### Registry Events

#### RegistryConfigured

```python
@dataclass
class RegistryConfiguredEvent:
    cache_enabled: bool
    hot_reload_enabled: bool
    validation_mode: ValidationMode
    timestamp: datetime
```

#### SelectorsReloaded

```python
@dataclass
class SelectorsReloadedEvent:
    selectors_reloaded: int
    reload_time_ms: float
    errors: List[SelectorValidationError]
    timestamp: datetime
```

## Error Handling

### Error Response Format

All API methods that can fail should return structured error information:

```python
@dataclass
class APIError:
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]]
    timestamp: datetime
    retry_after: Optional[float] = None
```

### Error Codes

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| SELECTOR_NOT_FOUND | Selector with specified ID not found | 404 |
| INVALID_SELECTOR_FORMAT | Selector data format is invalid | 400 |
| VALIDATION_FAILED | Selector validation failed | 422 |
| FILE_NOT_FOUND | Selector file not found | 404 |
| PERMISSION_DENIED | Insufficient permissions to access file | 403 |
| CONFIGURATION_ERROR | Registry configuration error | 500 |
| INTERNAL_ERROR | Internal server error | 500 |

### Retry Strategy

For transient errors, implement exponential backoff:

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay_ms: float = 100.0
    max_delay_ms: float = 5000.0
    backoff_multiplier: float = 2.0
```

## Performance Requirements

### Response Time Requirements

- **Selector Loading**: <100ms per selector file
- **Selector Retrieval**: <10ms for cached selectors
- **Validation**: <50ms per selector
- **Statistics**: <200ms for comprehensive statistics

### Throughput Requirements

- **Concurrent Loading**: Support up to 10 concurrent selector loading operations
- **Cache Hit Rate**: >95% for frequently accessed selectors
- **Memory Usage**: <10MB for selector cache (100 selectors)

### Monitoring Requirements

- **Performance Metrics**: Track loading times, cache hit rates, error rates
- **Health Checks**: Registry health status with detailed diagnostics
- **Alerting**: Alert on high error rates (>5%) or slow loading (>500ms)

## Security Requirements

### Input Validation

- **File Path Validation**: Prevent directory traversal attacks
- **YAML Validation**: Use safe YAML loading to prevent code injection
- **Size Limits**: Limit selector file size to prevent DoS attacks
- **Rate Limiting**: Limit loading operations to prevent abuse

### Access Control

- **File Permissions**: Validate file access permissions before loading
- **Directory Restrictions**: Restrict loading to approved directories
- **Audit Logging**: Log all selector loading operations for audit trails

## Integration Requirements

### Selector Engine Integration

```python
# Extend existing SelectorEngine interface
class SelectorEngine:
    def register_yaml_selector(self, selector: YAMLSelector) -> bool: ...
    def load_yaml_selectors(self, directory_path: str) -> LoadResult: ...
    def get_yaml_selector(self, selector_id: str) -> Optional[YAMLSelector]: ...
    def list_yaml_selectors(self) -> List[YAMLSelector]: ...
```

### Component System Integration

```python
# Component context integration
class ComponentContext:
    def get_selector_registry(self) -> SelectorRegistry: ...
    def configure_selector_loading(self, config: RegistryConfig) -> bool: ...
```

### Logging Integration

```python
# Structured logging for selector operations
logger.info("selector_loaded", extra={
    "selector_id": selector.id,
    "selector_type": selector.selector_type.value,
    "loading_time_ms": loading_time,
    "file_path": selector.file_path
})
```

## Testing Requirements

### Unit Testing

- **Selector Validation**: Test all validation rules and error cases
- **Loading Logic**: Test file discovery, parsing, and registration
- **Error Handling**: Test all error scenarios and recovery mechanisms
- **Performance**: Test performance requirements and benchmarks

### Integration Testing

- **End-to-End Loading**: Test complete selector loading workflows
- **Selector Engine Integration**: Test integration with existing selector engine
- **Component Integration**: Test component context initialization
- **Real Browser Testing**: Test with actual Wikipedia pages

### Performance Testing

- **Load Testing**: Test loading performance with large selector sets
- **Memory Testing**: Test memory usage and leak detection
- **Concurrency Testing**: Test concurrent loading operations
- **Cache Performance**: Test cache hit rates and performance

## Versioning

### API Versioning

- **Semantic Versioning**: Use semantic versioning for API changes
- **Backward Compatibility**: Maintain backward compatibility for minor versions
- **Deprecation Policy**: Provide deprecation warnings for breaking changes
- **Migration Guide**: Provide migration guides for major version changes

### Schema Versioning

- **Selector Schema**: Version selector schema for compatibility tracking
- **Migration Support**: Support automatic schema migration where possible
- **Validation Rules**: Update validation rules for new schema versions
- **Documentation**: Maintain documentation for all supported schema versions
