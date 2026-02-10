"""
HTML sample data for testing the extractor module.

This module contains sample HTML elements and test data for
unit and integration testing of the extractor functionality.
"""

# Basic HTML elements for testing
SAMPLE_HTML_ELEMENTS = {
    "simple_text": "<div>Hello World</div>",
    "text_with_whitespace": "<div>   Trim this text   </div>",
    "element_with_attributes": '<div class="product" data-id="123" data-price="99.99">Product Name</div>',
    "nested_element": '<div class="container"><h2>Title</h2><p>Content</p></div>',
    "empty_element": "<div></div>",
    "element_with_numbers": "<div>Price: $123.45</div>",
    "element_with_email": "<div>Contact: user@example.com</div>",
    "element_with_phone": "<div>Call: (555) 123-4567</div>",
    "element_with_list": "<ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul>",
    "element_with_mixed_content": "<div>Product: Widget A - $10.99 - Available</div>",
}

# BeautifulSoup Tag objects (created at runtime)
def create_bs4_elements():
    """Create BeautifulSoup Tag objects for testing."""
    try:
        from bs4 import BeautifulSoup
        
        elements = {}
        for name, html in SAMPLE_HTML_ELEMENTS.items():
            soup = BeautifulSoup(html, 'html.parser')
            elements[name] = soup.find()  # Get the first element
        
        return elements
    except ImportError:
        return {}

# JSON/dict test data
SAMPLE_JSON_DATA = {
    "simple_dict": {
        "title": "Test Title",
        "description": "Test Description"
    },
    "nested_dict": {
        "product": {
            "name": "Widget",
            "price": 99.99,
            "category": "Electronics"
        }
    },
    "dict_with_numbers": {
        "count": "42",
        "price": "$123.45",
        "rating": "4.5 stars"
    }
}

# String test data
SAMPLE_STRINGS = {
    "simple_text": "Hello World",
    "whitespace_text": "   Trim this text   ",
    "numeric_text": "123.45",
    "currency_text": "$99.99",
    "email_text": "user@example.com",
    "phone_text": "(555) 123-4567",
    "mixed_text": "Product: Widget A - $10.99 - Available",
    "empty_text": "",
    "list_text": "Item 1, Item 2, Item 3"
}

# Test cases for extraction scenarios
EXTRACTION_TEST_CASES = [
    {
        "name": "simple_text_extraction",
        "element": "<div>Hello World</div>",
        "rule": {
            "name": "title",
            "field_path": "title",
            "extraction_type": "text",
            "target_type": "text"
        },
        "expected": "Hello World"
    },
    {
        "name": "attribute_extraction",
        "element": '<div class="product" data-id="123">Product</div>',
        "rule": {
            "name": "product_id",
            "field_path": "product_id",
            "extraction_type": "attribute",
            "attribute_name": "data-id",
            "target_type": "text"
        },
        "expected": "123"
    },
    {
        "name": "text_with_transformation",
        "element": "<div>   Trim this text   </div>",
        "rule": {
            "name": "clean_text",
            "field_path": "clean_text",
            "extraction_type": "text",
            "target_type": "text",
            "transformations": ["trim", "clean"]
        },
        "expected": "Trim this text"
    },
    {
        "name": "numeric_extraction",
        "element": "<div>Price: $123.45</div>",
        "rule": {
            "name": "price",
            "field_path": "price",
            "extraction_type": "text",
            "target_type": "float",
            "regex_pattern": r"\$(\d+\.\d+)",
            "transformations": ["trim"]
        },
        "expected": 123.45
    },
    {
        "name": "default_value_fallback",
        "element": "<div></div>",
        "rule": {
            "name": "missing_field",
            "field_path": "missing_field",
            "extraction_type": "text",
            "target_type": "text",
            "default_value": "N/A"
        },
        "expected": "N/A"
    }
]

# Error test cases
ERROR_TEST_CASES = [
    {
        "name": "missing_element",
        "element": "<div></div>",
        "rule": {
            "name": "content",
            "field_path": "content",
            "extraction_type": "text",
            "target_type": "text",
            "required": True
        },
        "expected_error": "Element not found"
    },
    {
        "name": "invalid_regex_pattern",
        "element": "<div>Test</div>",
        "rule": {
            "name": "test",
            "field_path": "test",
            "extraction_type": "text",
            "target_type": "text",
            "regex_pattern": "[invalid regex"
        },
        "expected_error": "Invalid regex pattern"
    },
    {
        "name": "type_conversion_error",
        "element": "<div>not_a_number</div>",
        "rule": {
            "name": "number",
            "field_path": "number",
            "extraction_type": "text",
            "target_type": "integer"
        },
        "expected_error": "Cannot convert"
    }
]

# Performance test data
PERFORMANCE_TEST_DATA = {
    "large_text": "Lorem ipsum " * 1000,  # Large text for performance testing
    "many_elements": ["<div>Item {i}</div>" for i in range(1000)],  # Many elements
    "complex_rules": [
        {
            "name": f"rule_{i}",
            "field_path": f"field_{i}",
            "extraction_type": "text",
            "target_type": "text",
            "transformations": ["trim", "clean"]
        }
        for i in range(100)
    ]
}

# Validation test cases
VALIDATION_TEST_CASES = [
    {
        "name": "valid_string_length",
        "rule": {
            "name": "title",
            "field_path": "title",
            "extraction_type": "text",
            "target_type": "text",
            "min_length": 1,
            "max_length": 100
        },
        "test_value": "Valid Title",
        "should_pass": True
    },
    {
        "name": "invalid_string_length",
        "rule": {
            "name": "title",
            "field_path": "title",
            "extraction_type": "text",
            "target_type": "text",
            "min_length": 10,
            "max_length": 20
        },
        "test_value": "Too short",
        "should_pass": False
    },
    {
        "name": "valid_numeric_range",
        "rule": {
            "name": "price",
            "field_path": "price",
            "extraction_type": "text",
            "target_type": "float",
            "min_value": 0.0,
            "max_value": 1000.0
        },
        "test_value": 99.99,
        "should_pass": True
    },
    {
        "name": "invalid_numeric_range",
        "rule": {
            "name": "price",
            "field_path": "price",
            "extraction_type": "text",
            "target_type": "float",
            "min_value": 100.0,
            "max_value": 200.0
        },
        "test_value": 50.0,
        "should_pass": False
    }
]
