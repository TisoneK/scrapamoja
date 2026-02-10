# Extractor Module API Specification

**Version**: 1.0.0  
**Date**: 2025-01-29  
**Status**: Complete

## Overview

The Extractor Module provides a comprehensive API for extracting structured data from HTML elements, JSON objects, and other structured nodes. This specification defines the public interface, input/output formats, and usage patterns.

## Core API

### Main Extractor Class

```python
class Extractor:
    """Main extractor class for structured data extraction."""
    
    def __init__(self, config: Optional[ExtractorConfig] = None):
        """Initialize extractor with optional configuration."""
        pass
    
    def extract(
        self,
        element: Union[Element, Dict[str, Any], str],
        rules: Union[ExtractionRule, List[ExtractionRule], Dict[str, Any]],
        context: Optional[ExtractionContext] = None
    ) -> Union[ExtractionResult, Dict[str, ExtractionResult]]:
        """Extract data from element using provided rules."""
        pass
    
    def extract_batch(
        self,
        elements: List[Union[Element, Dict[str, Any], str]],
        rules: Union[ExtractionRule, List[ExtractionRule], Dict[str, Any]],
        context: Optional[ExtractionContext] = None
    ) -> List[Dict[str, ExtractionResult]]:
        """Extract data from multiple elements efficiently."""
        pass
    
    def validate_rules(
        self,
        rules: Union[ExtractionRule, List[ExtractionRule], Dict[str, Any]]
    ) -> ValidationResult:
        """Validate extraction rules before use."""
        pass
    
    def get_statistics(self) -> ExtractorStatistics:
        """Get extraction performance and usage statistics."""
        pass
```

### Configuration

```python
class ExtractorConfig(BaseModel):
    """Configuration for the Extractor."""
    
    # Performance settings
    max_extraction_time_ms: float = Field(100.0, description="Maximum time per extraction")
    batch_size: int = Field(100, description="Batch size for batch processing")
    enable_caching: bool = Field(True, description="Enable pattern caching")
    
    # Error handling
    strict_mode: bool = Field(False, description="Raise exceptions on errors")
    log_failures: bool = Field(True, description="Log extraction failures")
    max_errors_per_batch: int = Field(10, description="Max errors before stopping batch")
    
    # Validation
    enable_validation: bool = Field(True, description="Enable result validation")
    auto_fix_errors: bool = Field(False, description="Attempt to auto-fix validation errors")
    
    # Logging
    log_level: str = Field("INFO", description="Logging level")
    include_performance_metrics: bool = Field(True, description="Include timing in logs")
    
    # Memory management
    max_memory_mb: int = Field(100, description="Maximum memory usage in MB")
    gc_threshold: int = Field(1000, description="GC trigger threshold")
```

### Context

```python
class ExtractionContext(BaseModel):
    """Context information for extraction operations."""
    
    # Identification
    extraction_id: str = Field(..., description="Unique extraction identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    correlation_id: Optional[str] = Field(None, description="Correlation identifier")
    
    # Source information
    source_url: Optional[str] = Field(None, description="Source URL")
    source_type: str = Field("unknown", description="Source type (html, json, etc.)")
    
    # Metadata
    user_agent: Optional[str] = Field(None, description="User agent string")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    
    # Custom context
    custom_data: Dict[str, Any] = Field(default_factory=dict, description="Custom context data")
```

## Input/Output Formats

### Single Extraction

**Input**:
```python
element = "<div class='price'>$123.45</div>"
rules = {
    "price": ExtractionRule(
        name="price",
        field_path="price",
        extraction_type=ExtractionType.TEXT,
        target_type=DataType.FLOAT,
        transformations=[TransformationType.TRIM, TransformationType.EXTRACT_NUMBERS],
        default_value=0.0
    )
}
```

**Output**:
```python
{
    "price": ExtractionResult(
        value=123.45,
        success=True,
        rule_name="price",
        extraction_type=ExtractionType.TEXT,
        target_type=DataType.FLOAT,
        extraction_time_ms=0.8,
        transformations_applied=[TransformationType.TRIM, TransformationType.EXTRACT_NUMBERS],
        validation_passed=True
    )
}
```

### Batch Extraction

**Input**:
```python
elements = [
    "<div class='product'>Widget A - $10.99</div>",
    "<div class='product'>Widget B - $15.99</div>",
    "<div class='product'>Widget C - $20.99</div>"
]
rules = [
    ExtractionRule(
        name="product_name",
        field_path="name",
        extraction_type=ExtractionType.TEXT,
        transformations=[TransformationType.TRIM]
    ),
    ExtractionRule(
        name="price",
        field_path="price",
        extraction_type=ExtractionType.REGEX,
        regex_pattern=r"\$(\d+\.\d+)",
        target_type=DataType.FLOAT
    )
]
```

**Output**:
```python
[
    {
        "name": ExtractionResult(value="Widget A", success=True, ...),
        "price": ExtractionResult(value=10.99, success=True, ...)
    },
    {
        "name": ExtractionResult(value="Widget B", success=True, ...),
        "price": ExtractionResult(value=15.99, success=True, ...)
    },
    {
        "name": ExtractionResult(value="Widget C", success=True, ...),
        "price": ExtractionResult(value=20.99, success=True, ...)
    }
]
```

### Rule Definition Formats

#### Object Format
```python
rule = ExtractionRule(
    name="title",
    field_path="title",
    extraction_type=ExtractionType.TEXT,
    target_type=DataType.TEXT,
    transformations=[TransformationType.TRIM]
)
```

#### Dictionary Format
```python
rule = {
    "name": "title",
    "field_path": "title",
    "extraction_type": "text",
    "target_type": "text",
    "transformations": ["trim"]
}
```

#### YAML Format
```yaml
name: title
field_path: title
extraction_type: text
target_type: text
transformations:
  - trim
```

## Error Handling

### Error Response Format

```python
class ExtractionError(Exception):
    """Base exception for extraction errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        rule_name: Optional[str] = None,
        element_info: Optional[Dict[str, Any]] = None,
        context: Optional[ExtractionContext] = None
    ):
        self.message = message
        self.error_code = error_code
        self.rule_name = rule_name
        self.element_info = element_info
        self.context = context
        super().__init__(message)

class ValidationError(ExtractionError):
    """Raised when validation fails."""
    pass

class ExtractionTimeoutError(ExtractionError):
    """Raised when extraction times out."""
    pass

class RuleValidationError(ExtractionError):
    """Raised when rule validation fails."""
    pass
```

### Error Codes

| Error Code | Description | Severity |
|------------|-------------|----------|
| EXTRACT_001 | Element not found | ERROR |
| EXTRACT_002 | Pattern not found | WARNING |
| EXTRACT_003 | Type conversion failed | ERROR |
| EXTRACT_004 | Validation failed | ERROR |
| EXTRACT_005 | Extraction timeout | ERROR |
| RULE_001 | Invalid rule definition | ERROR |
| RULE_002 | Invalid regex pattern | ERROR |
| RULE_003 | Invalid date format | ERROR |
| VALID_001 | Required field missing | ERROR |
| VALID_002 | Pattern mismatch | ERROR |
| VALID_003 | Value out of range | ERROR |

## Performance Metrics

### Statistics

```python
class ExtractorStatistics(BaseModel):
    """Extractor performance and usage statistics."""
    
    # Usage metrics
    total_extractions: int = Field(0, description="Total extractions performed")
    successful_extractions: int = Field(0, description="Successful extractions")
    failed_extractions: int = Field(0, description="Failed extractions")
    
    # Performance metrics
    average_extraction_time_ms: float = Field(0.0, description="Average extraction time")
    min_extraction_time_ms: float = Field(0.0, description="Minimum extraction time")
    max_extraction_time_ms: float = Field(0.0, description="Maximum extraction time")
    
    # Cache metrics
    cache_hits: int = Field(0, description="Cache hits")
    cache_misses: int = Field(0, description="Cache misses")
    cache_hit_rate: float = Field(0.0, description="Cache hit rate")
    
    # Memory metrics
    current_memory_mb: float = Field(0.0, description="Current memory usage")
    peak_memory_mb: float = Field(0.0, description="Peak memory usage")
    
    # Error metrics
    error_counts: Dict[str, int] = Field(default_factory=dict, description="Error counts by type")
    warning_counts: Dict[str, int] = Field(default_factory=dict, description="Warning counts by type")
    
    # Timestamps
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Start time")
    last_extraction_time: Optional[datetime] = Field(None, description="Last extraction time")
```

## Usage Examples

### Basic Text Extraction

```python
from src.extractor import Extractor, ExtractionRule, ExtractionType, DataType

extractor = Extractor()

# Simple text extraction
rule = ExtractionRule(
    name="title",
    field_path="title",
    extraction_type=ExtractionType.TEXT,
    target_type=DataType.TEXT
)

element = "<h1>Product Title</h1>"
result = extractor.extract(element, rule)
print(result["title"].value)  # "Product Title"
```

### Advanced Extraction with Transformations

```python
# Complex extraction with transformations
rule = ExtractionRule(
    name="price",
    field_path="price",
    extraction_type=ExtractionType.TEXT,
    target_type=DataType.FLOAT,
    regex_pattern=r"\$(\d+\.\d+)",
    transformations=[TransformationType.TRIM],
    default_value=0.0
)

element = "<div class='price'>  $123.45  </div>"
result = extractor.extract(element, rule)
print(result["price"].value)  # 123.45
print(result["price"].transformations_applied)  # ["trim"]
```

### Batch Processing

```python
# Batch extraction
elements = [
    "<div>Item 1 - $10.00</div>",
    "<div>Item 2 - $20.00</div>",
    "<div>Item 3 - $30.00</div>"
]

rules = [
    ExtractionRule(name="item", field_path="item", extraction_type=ExtractionType.TEXT),
    ExtractionRule(name="price", field_path="price", extraction_type=ExtractionType.REGEX, 
                   regex_pattern=r"\$(\d+\.\d+)", target_type=DataType.FLOAT)
]

results = extractor.extract_batch(elements, rules)
for result in results:
    print(f"Item: {result['item'].value}, Price: ${result['price'].value}")
```

### Error Handling

```python
# Error handling with defaults
rule = ExtractionRule(
    name="optional_field",
    field_path="optional_field",
    extraction_type=ExtractionType.TEXT,
    default_value="N/A",
    required=False
)

element = "<div>No matching content</div>"
result = extractor.extract(element, rule)
print(result["optional_field"].value)  # "N/A"
print(result["optional_field"].used_default)  # True
```

## Integration Guidelines

### With Selector Engine

```python
from src.selectors import get_selector_engine
from src.extractor import Extractor

# Integration with selector engine
selector_engine = get_selector_engine()
extractor = Extractor()

# Find element with selector engine
element = await selector_engine.find(page, "product_title")

# Extract data with extractor
rule = ExtractionRule(name="title", field_path="title", extraction_type=ExtractionType.TEXT)
result = extractor.extract(element, rule)
```

### With Browser Session

```python
from src.browser import get_browser_manager

# Integration with browser session
browser_manager = get_browser_manager()
session = await browser_manager.create_session("extraction_session")
page = await session.get_page()

# Extract from current page
element = await page.query_selector(".product-info")
rules = load_extraction_rules("product_rules.yaml")
results = extractor.extract(element, rules)
```

## Configuration Examples

### Performance Configuration

```python
config = ExtractorConfig(
    max_extraction_time_ms=50.0,
    batch_size=50,
    enable_caching=True,
    log_level="INFO",
    include_performance_metrics=True
)

extractor = Extractor(config)
```

### Strict Mode Configuration

```python
config = ExtractorConfig(
    strict_mode=True,
    enable_validation=True,
    auto_fix_errors=False,
    log_failures=True
)

extractor = Extractor(config)
```

## Testing Support

### Mock Elements

```python
# Test with mock elements
mock_element = {
    "tag": "div",
    "text": "Test Content",
    "attributes": {"class": "test", "data-id": "123"}
}

rule = ExtractionRule(name="content", field_path="content", extraction_type=ExtractionType.TEXT)
result = extractor.extract(mock_element, rule)
```

### Test Fixtures

```python
# Test fixtures for validation
test_cases = [
    {
        "element": "<div>$123.45</div>",
        "rules": [{"name": "price", "extraction_type": "regex", "pattern": r"\$(\d+\.\d+)"}],
        "expected": {"price": 123.45}
    }
]

for case in test_cases:
    result = extractor.extract(case["element"], case["rules"])
    assert result["price"].value == case["expected"]["price"]
```

## Version Compatibility

### API Versioning

- **Version 1.0.0**: Initial release with core extraction functionality
- **Backward Compatibility**: Maintained for minor version updates
- **Breaking Changes**: Reserved for major version updates

### Migration Guide

```python
# Version 1.0.x usage
extractor = Extractor()
result = extractor.extract(element, rule)

# Future version 2.0.x (hypothetical breaking change)
# extractor = ExtractorV2()  # New class name
# result = extractor.extract(element, rule)  # Same interface
```
