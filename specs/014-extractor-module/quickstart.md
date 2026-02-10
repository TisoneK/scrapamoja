# Extractor Module Quickstart Guide

**Version**: 1.0.0  
**Date**: 2025-01-29  
**Target Audience**: Developers integrating the Extractor Module

## Getting Started

### Installation

The Extractor Module is part of the Scorewise framework. Ensure you have the required dependencies:

```bash
pip install beautifulsoup4 lxml python-dateutil pydantic regex
```

### Basic Import

```python
from src.extractor import Extractor, ExtractionRule, ExtractionType, DataType
from src.extractor.exceptions import ExtractionError
```

## Quick Examples

### 1. Simple Text Extraction

```python
# Initialize extractor
extractor = Extractor()

# Define extraction rule
rule = ExtractionRule(
    name="title",
    field_path="title",
    extraction_type=ExtractionType.TEXT,
    target_type=DataType.TEXT
)

# Extract from HTML element
element = "<h1>Product Title</h1>"
result = extractor.extract(element, rule)

print(result["title"].value)  # Output: "Product Title"
print(result["title"].success)  # Output: True
```

### 2. Attribute Extraction

```python
# Extract attribute value
rule = ExtractionRule(
    name="link",
    field_path="link",
    extraction_type=ExtractionType.ATTRIBUTE,
    attribute_name="href",
    target_type=DataType.TEXT
)

element = "<a href='https://example.com'>Click here</a>"
result = extractor.extract(element, rule)

print(result["link"].value)  # Output: "https://example.com"
```

### 3. Numeric Extraction with Cleaning

```python
# Extract and convert numbers
rule = ExtractionRule(
    name="price",
    field_path="price",
    extraction_type=ExtractionType.TEXT,
    target_type=DataType.FLOAT,
    transformations=["trim", "extract_numbers"],
    default_value=0.0
)

element = "<div class='price'>  $123.45  </div>"
result = extractor.extract(element, rule)

print(result["price"].value)  # Output: 123.45
print(result["price"].target_type)  # Output: DataType.FLOAT
```

### 4. Regex Pattern Extraction

```python
# Extract using regex pattern
rule = ExtractionRule(
    name="email",
    field_path="email",
    extraction_type=ExtractionType.REGEX,
    regex_pattern=r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    target_type=DataType.TEXT
)

element = "<div>Contact: user@example.com for details</div>"
result = extractor.extract(element, rule)

print(result["email"].value)  # Output: "user@example.com"
```

### 5. Date Extraction

```python
# Extract and parse dates
rule = ExtractionRule(
    name="date",
    field_path="date",
    extraction_type=ExtractionType.TEXT,
    target_type=DataType.DATE,
    date_format="%Y-%m-%d"
)

element = "<div>Published: 2024-01-15</div>"
result = extractor.extract(element, rule)

print(result["date"].value)  # Output: datetime(2024, 1, 15)
```

### 6. List Extraction

```python
# Extract multiple values from a list
rule = ExtractionRule(
    name="items",
    field_path="items",
    extraction_type=ExtractionType.LIST,
    target_type=DataType.TEXT
)

element = """
<ul>
    <li>Item 1</li>
    <li>Item 2</li>
    <li>Item 3</li>
</ul>
"""
result = extractor.extract(element, rule)

print(result["items"].value)  # Output: ["Item 1", "Item 2", "Item 3"]
```

## Advanced Usage

### Multiple Rules

```python
# Extract multiple fields at once
rules = [
    ExtractionRule(
        name="title",
        field_path="title",
        extraction_type=ExtractionType.TEXT,
        target_type=DataType.TEXT
    ),
    ExtractionRule(
        name="price",
        field_path="price",
        extraction_type=ExtractionType.REGEX,
        regex_pattern=r"\$(\d+\.\d+)",
        target_type=DataType.FLOAT
    ),
    ExtractionRule(
        name="description",
        field_path="description",
        extraction_type=ExtractionType.TEXT,
        target_type=DataType.TEXT,
        transformations=["trim"]
    )
]

element = """
<div class="product">
    <h2>Widget Pro</h2>
    <div class="price">$99.99</div>
    <p class="description">   A high-quality widget for all your needs.   </p>
</div>
"""

result = extractor.extract(element, rules)

print(f"Title: {result['title'].value}")
print(f"Price: ${result['price'].value}")
print(f"Description: {result['description'].value}")
```

### Batch Processing

```python
# Process multiple elements efficiently
elements = [
    "<div>Product A - $10.00</div>",
    "<div>Product B - $20.00</div>",
    "<div>Product C - $30.00</div>"
]

rules = [
    ExtractionRule(
        name="product",
        field_path="product",
        extraction_type=ExtractionType.TEXT,
        regex_pattern=r"([A-Za-z]+ [A-Za-z])"
    ),
    ExtractionRule(
        name="price",
        field_path="price",
        extraction_type=ExtractionType.REGEX,
        regex_pattern=r"\$(\d+\.\d+)",
        target_type=DataType.FLOAT
    )
]

results = extractor.extract_batch(elements, rules)

for i, result in enumerate(results):
    print(f"Product {i+1}: {result['product'].value} - ${result['price'].value}")
```

### Error Handling

```python
# Handle extraction failures gracefully
rule = ExtractionRule(
    name="optional_field",
    field_path="optional_field",
    extraction_type=ExtractionType.TEXT,
    default_value="Not available",
    required=False
)

element = "<div>No matching content here</div>"
result = extractor.extract(element, rule)

if result["optional_field"].success:
    print(f"Value: {result['optional_field'].value}")
else:
    print(f"Error: {result['optional_field'].errors}")
    print(f"Used default: {result['optional_field'].used_default}")
```

### Validation

```python
# Add validation rules
rule = ExtractionRule(
    name="age",
    field_path="age",
    extraction_type=ExtractionType.TEXT,
    target_type=DataType.INTEGER,
    min_value=0,
    max_value=150,
    validation_pattern=r"^\d+$"
)

element = "<div>Age: 25</div>"
result = extractor.extract(element, rule)

if result["age"].validation_passed:
    print(f"Valid age: {result['age'].value}")
else:
    print(f"Validation errors: {result['age'].validation_errors}")
```

## Configuration

### Basic Configuration

```python
from src.extractor import ExtractorConfig

config = ExtractorConfig(
    max_extraction_time_ms=50.0,  # Max time per extraction
    batch_size=100,               # Batch processing size
    enable_caching=True,          # Enable pattern caching
    strict_mode=False,            # Don't raise exceptions
    log_failures=True,            # Log extraction failures
    enable_validation=True        # Enable result validation
)

extractor = Extractor(config)
```

### Performance Configuration

```python
# High-performance configuration
config = ExtractorConfig(
    max_extraction_time_ms=10.0,  # Strict time limit
    batch_size=500,               # Larger batches
    enable_caching=True,          # Enable caching
    log_level="WARNING",          # Minimal logging
    include_performance_metrics=False  # Disable metrics for speed
)

extractor = Extractor(config)
```

### Strict Mode Configuration

```python
# Strict validation configuration
config = ExtractorConfig(
    strict_mode=True,             # Raise exceptions on errors
    enable_validation=True,       # Enable validation
    auto_fix_errors=False,        # Don't auto-fix errors
    log_failures=True,            # Log all failures
    max_errors_per_batch=1        # Stop on first error
)

extractor = Extractor(config)

try:
    result = extractor.extract(element, rule)
except ExtractionError as e:
    print(f"Extraction failed: {e.error_code} - {e.message}")
```

## Integration Examples

### With Selector Engine

```python
from src.selectors import get_selector_engine

# Combine with selector engine
selector_engine = get_selector_engine()
extractor = Extractor()

# Find element with selector engine
element = await selector_engine.find(page, "product_title")

# Extract data
rule = ExtractionRule(name="title", field_path="title", extraction_type=ExtractionType.TEXT)
result = extractor.extract(element, rule)
```

### With Browser Session

```python
from src.browser import get_browser_manager

# Use with browser session
browser_manager = get_browser_manager()
session = await browser_manager.create_session("extraction_session")
page = await session.get_page()

# Extract from page content
element = await page.query_selector(".product-info")
rules = load_extraction_rules_from_yaml("product_rules.yaml")
results = extractor.extract(element, rules)
```

### YAML Rule Definitions

```yaml
# product_rules.yaml
rules:
  - name: title
    field_path: title
    extraction_type: text
    target_type: text
    transformations: [trim]
    
  - name: price
    field_path: price
    extraction_type: regex
    regex_pattern: "\$(\\d+\\.\\d+)"
    target_type: float
    default_value: 0.0
    
  - name: availability
    field_path: availability
    extraction_type: text
    target_type: boolean
    validation_pattern: "^(in stock|out of stock)$"
```

```python
import yaml

def load_extraction_rules_from_yaml(file_path):
    with open(file_path, 'r') as f:
        data = yaml.safe_load(f)
    
    rules = []
    for rule_data in data['rules']:
        rule = ExtractionRule(**rule_data)
        rules.append(rule)
    
    return rules

# Load and use rules
rules = load_extraction_rules_from_yaml("product_rules.yaml")
result = extractor.extract(element, rules)
```

## Testing

### Unit Testing

```python
import pytest
from src.extractor import Extractor, ExtractionRule, ExtractionType, DataType

def test_text_extraction():
    extractor = Extractor()
    rule = ExtractionRule(
        name="title",
        field_path="title",
        extraction_type=ExtractionType.TEXT,
        target_type=DataType.TEXT
    )
    
    element = "<h1>Test Title</h1>"
    result = extractor.extract(element, rule)
    
    assert result["title"].success == True
    assert result["title"].value == "Test Title"

def test_extraction_with_default():
    extractor = Extractor()
    rule = ExtractionRule(
        name="missing",
        field_path="missing",
        extraction_type=ExtractionType.TEXT,
        default_value="default_value"
    )
    
    element = "<div>No matching content</div>"
    result = extractor.extract(element, rule)
    
    assert result["missing"].success == False
    assert result["missing"].value == "default_value"
    assert result["missing"].used_default == True
```

### Performance Testing

```python
import time

def test_extraction_performance():
    extractor = Extractor()
    rule = ExtractionRule(
        name="content",
        field_path="content",
        extraction_type=ExtractionType.TEXT
    )
    
    element = "<div>Test content</div>"
    
    # Measure extraction time
    start_time = time.time()
    for _ in range(1000):
        result = extractor.extract(element, rule)
    end_time = time.time()
    
    avg_time = (end_time - start_time) / 1000 * 1000  # Convert to milliseconds
    assert avg_time < 10.0  # Should be under 10ms per extraction
```

## Troubleshooting

### Common Issues

1. **Extraction returns None**
   - Check if element exists
   - Verify regex pattern matches
   - Ensure attribute name is correct

2. **Type conversion fails**
   - Verify target_type matches expected format
   - Check date_format for date extraction
   - Ensure numeric strings contain valid numbers

3. **Performance issues**
   - Enable caching for repeated patterns
   - Use batch processing for multiple elements
   - Optimize regex patterns

4. **Validation errors**
   - Check validation patterns
   - Verify min/max constraints
   - Ensure required fields are present

### Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Extract with detailed logging
config = ExtractorConfig(
    log_level="DEBUG",
    include_performance_metrics=True
)

extractor = Extractor(config)
result = extractor.extract(element, rule)
```

### Statistics Monitoring

```python
# Get extraction statistics
stats = extractor.get_statistics()

print(f"Total extractions: {stats.total_extractions}")
print(f"Success rate: {stats.successful_extractions / stats.total_extractions * 100:.1f}%")
print(f"Average time: {stats.average_extraction_time_ms:.2f}ms")
print(f"Cache hit rate: {stats.cache_hit_rate * 100:.1f}%")
```

## Next Steps

1. **Explore Advanced Features**: Custom transformations, validation rules
2. **Integration**: Connect with selector engine and browser sessions
3. **Performance Optimization**: Caching, batch processing, configuration tuning
4. **Testing**: Comprehensive unit and integration tests
5. **Production Deployment**: Error handling, monitoring, logging

## Additional Resources

- [API Specification](contracts/extractor-api.md) - Detailed API documentation
- [Data Model](data-model.md) - Entity definitions and relationships
- [Implementation Plan](plan.md) - Technical decisions and architecture
- [Constitution](../../../.specify/memory/constitution.md) - Development guidelines and principles
