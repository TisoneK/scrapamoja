"""
Text extraction handler for the extractor module.

This module provides functionality for extracting text content from
HTML elements, JSON objects, and other structured nodes.
"""

import re
from typing import Any, Dict, Optional, Union

from bs4 import BeautifulSoup, Tag, NavigableString

from ..core.rules import ExtractionRule, ExtractionResult, ExtractionType, DataType
from ..exceptions import ExtractionError, ElementNotFoundError, PatternNotFoundError
from ..utils.regex_utils import RegexUtils
from ..utils.cleaning import StringCleaner


class TextExtractor:
    """Handler for text extraction operations."""
    
    def __init__(self):
        """Initialize text extractor with regex utilities."""
        self.regex_utils = RegexUtils()
    
    def extract(
        self,
        element: Union[Any, Dict[str, Any], str],
        rule: ExtractionRule,
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """
        Extract text content from an element.
        
        Args:
            element: Source element (HTML, JSON, or string)
            rule: Extraction rule defining how to extract text
            context: Additional context information
            
        Returns:
            ExtractionResult with extracted text or default value
        """
        start_time = self._get_time_ms()
        
        try:
            # Extract raw text based on element type
            raw_text = self._extract_raw_text(element, rule)
            
            if raw_text is None:
                if rule.default_value is not None:
                    return self._create_result(
                        rule=rule,
                        value=rule.default_value,
                        success=False,
                        extraction_time_ms=self._get_time_ms() - start_time,
                        used_default=True,
                        warnings=["Element not found, using default value"],
                        context=context
                    )
                else:
                    return self._create_result(
                        rule=rule,
                        value=None,
                        success=False,
                        extraction_time_ms=self._get_time_ms() - start_time,
                        errors=["Element not found and no default value provided"],
                        context=context
                    )
            
            # Apply regex pattern if specified
            if rule.regex_pattern:
                raw_text = self._apply_regex_pattern(raw_text, rule)
                if raw_text is None:
                    if rule.default_value is not None:
                        return self._create_result(
                            rule=rule,
                            value=rule.default_value,
                            success=False,
                            extraction_time_ms=self._get_time_ms() - start_time,
                            used_default=True,
                            warnings=["Pattern not found, using default value"],
                            context=context
                        )
                    else:
                        return self._create_result(
                            rule=rule,
                            value=None,
                            success=False,
                            extraction_time_ms=self._get_time_ms() - start_time,
                            errors=["Pattern not found and no default value provided"],
                            context=context
                        )
            
            # Apply transformations
            transformed_text = self._apply_transformations(raw_text, rule)
            
            # Convert to target type
            final_value = self._convert_to_target_type(transformed_text, rule)
            
            # Validate result
            validation_errors = self._validate_result(final_value, rule)
            
            extraction_time_ms = self._get_time_ms() - start_time
            
            return self._create_result(
                rule=rule,
                value=final_value,
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
            error_message = f"Text extraction failed: {str(e)}"
            
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
    
    def _extract_raw_text(
        self,
        element: Union[Any, Dict[str, Any], str],
        rule: ExtractionRule
    ) -> Optional[str]:
        """Extract raw text from different element types."""
        if isinstance(element, str):
            # Direct string input
            return element
        
        elif isinstance(element, dict):
            # JSON/dict input
            if rule.field_path in element:
                return str(element[rule.field_path])
            else:
                # Try nested path access
                return self._get_nested_value(element, rule.field_path)
        
        elif hasattr(element, 'get_text'):
            # BeautifulSoup Tag or similar
            return element.get_text(strip=True)
        
        elif hasattr(element, 'text'):
            # Element with text attribute
            return str(getattr(element, 'text', ''))
        
        elif hasattr(element, '__str__'):
            # Fallback to string representation
            return str(element)
        
        else:
            return None
    
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
    
    def _apply_regex_pattern(self, text: str, rule: ExtractionRule) -> Optional[str]:
        """Apply regex pattern to extract specific content."""
        try:
            # Use enhanced regex utilities for better pattern matching
            if hasattr(rule, 'extract_all') and rule.extract_all:
                # Extract all matches
                matches = self.regex_utils.extract_all_matches(
                    pattern=rule.regex_pattern,
                    text=text,
                    flags=rule.regex_flags,
                    group=rule.regex_group if hasattr(rule, 'regex_group') else 0,
                    use_cache=True
                )
                return matches[0] if matches else None
            elif hasattr(rule, 'extract_named_groups') and rule.extract_named_groups:
                # Extract named groups
                named_matches = self.regex_utils.extract_named_groups(
                    pattern=rule.regex_pattern,
                    text=text,
                    flags=rule.regex_flags,
                    use_cache=True
                )
                return str(named_matches[0]) if named_matches else None
            else:
                # Standard single match extraction
                match = self.regex_utils.find_first(
                    pattern=rule.regex_pattern,
                    text=text,
                    flags=rule.regex_flags,
                    group=rule.regex_group if hasattr(rule, 'regex_group') else 0,
                    use_cache=True
                )
                return match
            
        except Exception as e:
            from ..exceptions import PatternNotFoundError
            raise PatternNotFoundError(
                f"Regex pattern application failed: {str(e)}",
                pattern=rule.regex_pattern,
                content_sample=text[:100] + "..." if len(text) > 100 else text
            )
    
    def _apply_transformations(self, text: str, rule: ExtractionRule) -> str:
        """Apply text transformations."""
        result = text
        
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
            elif transformation == "extract_numbers":
                numbers = self.regex_utils.extract_numbers(result)
                result = str(numbers[0]) if numbers else ""
            elif transformation == "extract_emails":
                emails = self.regex_utils.extract_emails(result)
                result = emails[0] if emails else ""
            elif transformation == "extract_phones":
                phones = self.regex_utils.extract_phone_numbers(result)
                result = phones[0] if phones else ""
        
        return result
    
    def _convert_to_target_type(self, text: str, rule: ExtractionRule) -> Any:
        """Convert text to the target data type."""
        if rule.target_type == DataType.TEXT:
            return text
        
        elif rule.target_type == DataType.INTEGER:
            try:
                # Extract numbers first if text contains non-numeric characters
                if not text.isdigit():
                    numbers = self.regex_utils.extract_numbers(text)
                    if numbers:
                        return int(numbers[0])
                    else:
                        raise ValueError(f"Cannot convert '{text}' to integer")
                return int(text)
            except ValueError as e:
                raise ValueError(f"Cannot convert '{text}' to integer: {str(e)}")
        
        elif rule.target_type == DataType.FLOAT:
            try:
                # Extract numbers first if text contains non-numeric characters
                if not re.match(r'^-?\d+\.?\d*$', text):
                    numbers = self.regex_utils.extract_numbers(text)
                    if numbers:
                        return float(numbers[0])
                    else:
                        raise ValueError(f"Cannot convert '{text}' to float")
                return float(text)
            except ValueError as e:
                raise ValueError(f"Cannot convert '{text}' to float: {str(e)}")
        
        elif rule.target_type == DataType.BOOLEAN:
            text_lower = text.lower().strip()
            if text_lower in ('true', 'yes', '1', 'on', 'enabled'):
                return True
            elif text_lower in ('false', 'no', '0', 'off', 'disabled'):
                return False
            else:
                raise ValueError(f"Cannot convert '{text}' to boolean")
        
        elif rule.target_type == DataType.LIST:
            # Split by common delimiters
            items = re.split(r'[,;|]\s*', text)
            return [item.strip() for item in items if item.strip()]
        
        elif rule.target_type == DataType.DICT:
            # Simple key=value parsing
            result = {}
            pairs = re.split(r'[,;]\s*', text)
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    result[key.strip()] = value.strip()
            return result
        
        else:
            return text
    
    def _validate_result(self, value: Any, rule: ExtractionRule) -> list:
        """Validate the extracted result against rule constraints."""
        errors = []
        
        # Type validation
        if rule.target_type == DataType.TEXT and not isinstance(value, str):
            errors.append(f"Expected string, got {type(value).__name__}")
        
        elif rule.target_type == DataType.INTEGER and not isinstance(value, int):
            errors.append(f"Expected integer, got {type(value).__name__}")
        
        elif rule.target_type == DataType.FLOAT and not isinstance(value, (int, float)):
            errors.append(f"Expected number, got {type(value).__name__}")
        
        elif rule.target_type == DataType.BOOLEAN and not isinstance(value, bool):
            errors.append(f"Expected boolean, got {type(value).__name__}")
        
        elif rule.target_type == DataType.LIST and not isinstance(value, list):
            errors.append(f"Expected list, got {type(value).__name__}")
        
        elif rule.target_type == DataType.DICT and not isinstance(value, dict):
            errors.append(f"Expected dict, got {type(value).__name__}")
        
        # String-specific validations
        if isinstance(value, str):
            if rule.min_length is not None and len(value) < rule.min_length:
                errors.append(f"String length {len(value)} is less than minimum {rule.min_length}")
            
            if rule.max_length is not None and len(value) > rule.max_length:
                errors.append(f"String length {len(value)} exceeds maximum {rule.max_length}")
            
            if rule.validation_pattern:
                if not re.match(rule.validation_pattern, value):
                    errors.append(f"String does not match validation pattern: {rule.validation_pattern}")
        
        # Numeric validations
        if isinstance(value, (int, float)):
            if rule.min_value is not None and value < rule.min_value:
                errors.append(f"Value {value} is less than minimum {rule.min_value}")
            
            if rule.max_value is not None and value > rule.max_value:
                errors.append(f"Value {value} exceeds maximum {rule.max_value}")
        
        # Required field validation
        if rule.required and (value is None or value == ''):
            errors.append("Required field is empty or None")
        
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
            extraction_type=ExtractionType.TEXT,
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
