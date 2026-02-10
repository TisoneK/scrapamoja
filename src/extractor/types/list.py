"""
List extraction handler for the extractor module.

This module provides functionality for extracting multiple values from list-like
elements and handling list data structures.
"""

import re
from typing import Any, Dict, List, Optional, Union

from bs4 import BeautifulSoup, Tag, NavigableString

from ..core.rules import ExtractionRule, ExtractionResult, ExtractionType, DataType
from ..exceptions import ExtractionError, ElementNotFoundError
from ..utils.cleaning import StringCleaner


class ListExtractor:
    """Handler for list extraction operations."""
    
    def __init__(self):
        """Initialize list extractor."""
        pass
    
    def extract(
        self,
        element: Union[Any, Dict[str, Any], str],
        rule: ExtractionRule,
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """
        Extract list data from an element.
        
        Args:
            element: Source element (HTML, JSON, or string)
            rule: Extraction rule defining how to extract list data
            context: Additional context information
            
        Returns:
            ExtractionResult with extracted list value or default value
        """
        start_time = self._get_time_ms()
        
        try:
            # Extract raw list based on element type
            raw_list = self._extract_raw_list(element, rule)
            
            if raw_list is None:
                if rule.default_value is not None:
                    return self._create_result(
                        rule=rule,
                        value=rule.default_value,
                        success=False,
                        extraction_time_ms=self._get_time_ms() - start_time,
                        used_default=True,
                        warnings=["List not found, using default value"],
                        context=context
                    )
                else:
                    return self._create_result(
                        rule=rule,
                        value=None,
                        success=False,
                        extraction_time_ms=self._get_time_ms() - start_time,
                        errors=["List not found and no default value provided"],
                        context=context
                    )
            
            # Apply transformations to each item
            transformed_list = []
            for item in raw_list:
                transformed_item = self._apply_transformations(str(item), rule)
                transformed_list.append(transformed_item)
            
            # Convert to target type (list items)
            final_list = self._convert_list_items(transformed_list, rule)
            
            # Validate result
            validation_errors = self._validate_result(final_list, rule)
            
            extraction_time_ms = self._get_time_ms() - start_time
            
            return self._create_result(
                rule=rule,
                value=final_list,
                success=True,
                extraction_time_ms=extraction_time_ms,
                transformations_applied=rule.transformations,
                validation_errors=validation_errors,
                validation_passed=len(validation_errors) == 0,
                element_info=self._get_element_info(element),
                context=context
            )
            
        except Exception as e:
            extraction_time_ms = self._get_time_ms() - start_time
            error_message = f"List extraction failed: {str(e)}"
            
            if rule.default_value is not None:
                return self._create_result(
                    rule=rule,
                    value=rule.default_value,
                    success=False,
                    extraction_time_ms=extraction_time_ms,
                    used_default=True,
                    errors=[error_message],
                    warnings=["Using default value due to extraction error"],
                    context=context
                )
            else:
                return self._create_result(
                    rule=rule,
                    value=None,
                    success=False,
                    extraction_time_ms=extraction_time_ms,
                    errors=[error_message],
                    context=context
                )
    
    def _extract_raw_list(
        self,
        element: Union[Any, Dict[str, Any], str],
        rule: ExtractionRule
    ) -> Optional[List[str]]:
        """Extract raw list from different element types."""
        if isinstance(element, str):
            # Try to parse string as list
            return self._parse_string_as_list(element)
        
        elif isinstance(element, dict):
            # JSON/dict input
            if rule.field_path in element:
                value = element[rule.field_path]
                if isinstance(value, list):
                    return [str(item) for item in value]
                elif isinstance(value, str):
                    return self._parse_string_as_list(value)
                else:
                    return None
            else:
                # Try nested path access
                nested_value = self._get_nested_value(element, rule.field_path)
                if nested_value:
                    return self._parse_string_as_list(nested_value)
                else:
                    return None
        
        elif hasattr(element, 'find_all'):
            # BeautifulSoup Tag - find all child elements
            # Enhanced list extraction with better selectors
            list_selectors = [
                'li', 'option', 'dt', 'dd', 'tr', 'td', 'th',
                '[class*="item"]', '[class*="list"]', '[class*="row"]'
            ]
            items = []
            
            # Try specific selectors first
            if hasattr(rule, 'list_selector') and rule.list_selector:
                found_elements = element.select(rule.list_selector)
                for found_element in found_elements:
                    text = found_element.get_text(strip=True)
                    if text:
                        items.append(text)
                
                if items:
                    return items
            
            # Try common list selectors
            for selector in list_selectors:
                found_elements = element.find_all(selector)
                for found_element in found_elements:
                    text = found_element.get_text(strip=True)
                    if text:
                        items.append(text)
                
                if items:
                    return items
            
            # Try regex-based extraction from text content
            if hasattr(rule, 'list_regex_pattern') and rule.list_regex_pattern:
                text_content = element.get_text()
                from ..utils.regex_utils import RegexUtils
                regex_utils = RegexUtils()
                matches = regex_utils.extract_all_matches(
                    pattern=rule.list_regex_pattern,
                    text=text_content,
                    flags=rule.regex_flags if hasattr(rule, 'regex_flags') else 0,
                    use_cache=True
                )
                return matches
            
            # If no list items found, try to extract from text content
            text_content = element.get_text(strip=True)
            if text_content:
                return self._parse_string_as_list(text_content)
            
            return None
        
        elif hasattr(element, 'text'):
            # Element with text attribute
            text_content = str(getattr(element, 'text', ''))
            return self._parse_string_as_list(text_content)
        
        elif hasattr(element, '__str__'):
            # Fallback to string representation
            text_content = str(element)
            return self._parse_string_as_list(text_content)
        
        else:
            return None
    
    def _parse_string_as_list(self, text: str) -> List[str]:
        """Parse a string as a list using common delimiters."""
        if not text or not text.strip():
            return []
        
        # Common list delimiters
        delimiters = [',', ';', '|', '\n', '\t']
        
        # Try each delimiter
        for delimiter in delimiters:
            if delimiter in text:
                items = text.split(delimiter)
                # Clean and filter empty items
                cleaned_items = [item.strip() for item in items if item.strip()]
                if cleaned_items:
                    return cleaned_items
        
        # If no delimiters found, return single item
        return [text.strip()] if text.strip() else []
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Optional[str]:
        """Get value from nested dictionary using dot notation."""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return str(current) if current is not None else None
    
    def _apply_transformations(self, item: str, rule: ExtractionRule) -> str:
        """Apply transformations to a single list item."""
        result = item
        
        for transformation in rule.transformations:
            if transformation == "trim":
                result = StringCleaner.trim(result)
            elif transformation == "clean":
                result = StringCleaner.clean_whitespace(result)
            elif transformation == "normalize":
                result = StringCleaner.normalize(result)
            elif transformation == "lowercase":
                result = StringCleaner.lowercase(result)
            elif transformation == "uppercase":
                result = StringCleaner.uppercase(result)
            elif transformation == "remove_whitespace":
                result = StringCleaner.remove_all_whitespace(result)
        
        return result
    
    def _convert_list_items(self, items: List[str], rule: ExtractionRule) -> List[Any]:
        """Convert list items to the target type."""
        if rule.target_type == DataType.LIST:
            # Keep as strings
            return items
        
        elif rule.target_type == DataType.INTEGER:
            # Convert to integers
            converted_items = []
            for item in items:
                try:
                    if item.isdigit():
                        converted_items.append(int(item))
                    else:
                        # Try to extract numbers
                        import re
                        numbers = re.findall(r'-?\d+', item)
                        if numbers:
                            converted_items.append(int(numbers[0]))
                        else:
                            converted_items.append(0)  # Default to 0 if no numbers found
                except (ValueError, TypeError):
                    converted_items.append(0)  # Default to 0 on error
            return converted_items
        
        elif rule.target_type == DataType.FLOAT:
            # Convert to floats
            converted_items = []
            for item in items:
                try:
                    if re.match(r'^-?\d+\.?\d*$', item):
                        converted_items.append(float(item))
                    else:
                        # Try to extract numbers
                        import re
                        numbers = re.findall(r'-?\d+\.?\d*', item)
                        if numbers:
                            converted_items.append(float(numbers[0]))
                        else:
                            converted_items.append(0.0)  # Default to 0.0 if no numbers found
                except (ValueError, TypeError):
                    converted_items.append(0.0)  # Default to 0.0 on error
            return converted_items
        
        elif rule.target_type == DataType.BOOLEAN:
            # Convert to booleans
            converted_items = []
            for item in items:
                item_lower = item.lower().strip()
                if item_lower in ('true', 'yes', '1', 'on', 'enabled'):
                    converted_items.append(True)
                elif item_lower in ('false', 'no', '0', 'off', 'disabled'):
                    converted_items.append(False)
                else:
                    converted_items.append(False)  # Default to False if unclear
            return converted_items
        
        elif rule.target_type == DataType.DICT:
            # Parse key=value pairs
            converted_items = []
            for item in items:
                if '=' in item:
                    key, value = item.split('=', 1)
                    converted_items.append({key.strip(): value.strip()})
                else:
                    converted_items.append({item: True})  # Default to True if no =
            return converted_items
        
        else:
            # Keep as strings for unknown types
            return items
    
    def _validate_result(self, value: List[Any], rule: ExtractionRule) -> list:
        """Validate the extracted list result."""
        errors = []
        
        # Type validation
        if not isinstance(value, list):
            errors.append(f"Expected list, got {type(value).__name__}")
        
        # Length validation
        if isinstance(value, list):
            if rule.min_length is not None and len(value) < rule.min_length:
                errors.append(f"List length {len(value)} is less than minimum {rule.min_length}")
            
            if rule.max_length is not None and len(value) > rule.max_length:
                errors.append(f"List length {len(value)} exceeds maximum {rule.max_length}")
        
        # Required field validation
        if rule.required and (value is None or len(value) == 0):
            errors.append("Required list is empty")
        
        return errors
    
    def _create_result(
        self,
        rule: ExtractionRule,
        value: Any,
        success: bool,
        extraction_time_ms: float,
        used_default: bool = False,
        errors: Optional[list] = None,
        warnings: Optional[list] = None,
        transformations_applied: Optional[list] = None,
        validation_errors: Optional[list] = None,
        validation_passed: bool = True,
        element_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """Create an ExtractionResult object."""
        return ExtractionResult(
            value=value,
            success=success,
            rule_name=rule.name,
            extraction_type=ExtractionType.LIST,
            target_type=rule.target_type,
            extraction_time_ms=extraction_time_ms,
            transformations_applied=transformations_applied or [],
            errors=errors or [],
            warnings=warnings or [],
            used_default=used_default,
            validation_passed=validation_passed,
            validation_errors=validation_errors or [],
            element_info=element_info,
            extraction_context=context
        )
    
    def _get_element_info(self, element: Any) -> Dict[str, Any]:
        """Get information about the source element."""
        info = {"type": type(element).__name__}
        
        if hasattr(element, 'name'):
            info["tag_name"] = element.name
        
        if hasattr(element, 'attrs'):
            info["attributes"] = element.attrs
        
        if isinstance(element, str):
            info["length"] = len(element)
            info["preview"] = element[:100] + "..." if len(element) > 100 else element
        
        return info
    
    def _get_time_ms(self) -> float:
        """Get current time in milliseconds."""
        import time
        return time.time() * 1000
