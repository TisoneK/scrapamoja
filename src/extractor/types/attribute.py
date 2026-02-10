"""
Attribute extraction handler for the extractor module.

This module provides functionality for extracting attribute values
from HTML elements and other structured nodes.
"""

from typing import Any, Dict, Optional, Union

from bs4 import Tag

from ..core.rules import ExtractionRule, ExtractionResult, ExtractionType, DataType
from ..exceptions import ExtractionError, ElementNotFoundError
from ..utils.cleaning import StringCleaner


class AttributeExtractor:
    """Handler for attribute extraction operations."""
    
    def extract(
        self,
        element: Union[Any, Dict[str, Any], str],
        rule: ExtractionRule,
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """
        Extract attribute value from an element.
        
        Args:
            element: Source element (HTML element, JSON, or string)
            rule: Extraction rule defining which attribute to extract
            context: Additional context information
            
        Returns:
            ExtractionResult with extracted attribute value or default value
        """
        start_time = self._get_time_ms()
        
        try:
            # Validate rule
            if not rule.attribute_name:
                raise ValueError("Attribute extraction requires attribute_name to be specified")
            
            # Extract attribute value
            attribute_value = self._extract_attribute_value(element, rule)
            
            if attribute_value is None:
                if rule.default_value is not None:
                    return self._create_result(
                        rule=rule,
                        value=rule.default_value,
                        success=False,
                        extraction_time_ms=self._get_time_ms() - start_time,
                        used_default=True,
                        warnings=["Attribute not found, using default value"],
                        context=context
                    )
                else:
                    return self._create_result(
                        rule=rule,
                        value=None,
                        success=False,
                        extraction_time_ms=self._get_time_ms() - start_time,
                        errors=[f"Attribute '{rule.attribute_name}' not found and no default value provided"],
                        context=context
                    )
            
            # Convert to string for processing
            if not isinstance(attribute_value, str):
                attribute_value = str(attribute_value)
            
            # Apply transformations
            transformed_value = self._apply_transformations(attribute_value, rule)
            
            # Convert to target type
            final_value = self._convert_to_target_type(transformed_value, rule)
            
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
            error_message = f"Attribute extraction failed: {str(e)}"
            
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
    
    def _extract_attribute_value(
        self,
        element: Union[Any, Dict[str, Any], str],
        rule: ExtractionRule
    ) -> Optional[str]:
        """Extract attribute value from different element types."""
        attribute_name = rule.attribute_name
        
        # Handle BeautifulSoup Tag objects
        if isinstance(element, Tag):
            if element.has_attr(attribute_name):
                return element[attribute_name]
            else:
                return None
        
        # Handle dictionary objects
        elif isinstance(element, dict):
            if attribute_name in element:
                return str(element[attribute_name])
            else:
                # Try nested path access
                return self._get_nested_value(element, attribute_name)
        
        # Handle objects with attribute access
        elif hasattr(element, attribute_name):
            value = getattr(element, attribute_name)
            return str(value) if value is not None else None
        
        # Handle objects with get_attr method
        elif hasattr(element, 'get_attr'):
            value = element.get_attr(attribute_name)
            return str(value) if value is not None else None
        
        # Handle objects with get method
        elif hasattr(element, 'get'):
            value = element.get(attribute_name)
            return str(value) if value is not None else None
        
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
    
    def _apply_transformations(self, value: str, rule: ExtractionRule) -> str:
        """Apply attribute value transformations."""
        result = value
        
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
    
    def _convert_to_target_type(self, value: str, rule: ExtractionRule) -> Any:
        """Convert attribute value to the target data type."""
        if rule.target_type == DataType.TEXT:
            return value
        
        elif rule.target_type == DataType.INTEGER:
            try:
                return int(value)
            except ValueError:
                # Try to extract numbers from string
                import re
                numbers = re.findall(r'-?\d+', value)
                if numbers:
                    return int(numbers[0])
                else:
                    raise ValueError(f"Cannot convert '{value}' to integer")
        
        elif rule.target_type == DataType.FLOAT:
            try:
                return float(value)
            except ValueError:
                # Try to extract numbers from string
                import re
                numbers = re.findall(r'-?\d+\.?\d*', value)
                if numbers:
                    return float(numbers[0])
                else:
                    raise ValueError(f"Cannot convert '{value}' to float")
        
        elif rule.target_type == DataType.BOOLEAN:
            value_lower = value.lower().strip()
            if value_lower in ('true', 'yes', '1', 'on', 'enabled'):
                return True
            elif value_lower in ('false', 'no', '0', 'off', 'disabled'):
                return False
            else:
                raise ValueError(f"Cannot convert '{value}' to boolean")
        
        elif rule.target_type == DataType.LIST:
            # Split by common delimiters
            import re
            items = re.split(r'[,;|]\s*', value)
            return [item.strip() for item in items if item.strip()]
        
        elif rule.target_type == DataType.DICT:
            # Simple key=value parsing
            import re
            result = {}
            pairs = re.split(r'[,;]\s*', value)
            for pair in pairs:
                if '=' in pair:
                    key, val = pair.split('=', 1)
                    result[key.strip()] = val.strip()
            return result
        
        else:
            return value
    
    def _validate_result(self, value: Any, rule: ExtractionRule) -> list:
        """Validate the extracted attribute value."""
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
                import re
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
            extraction_type=ExtractionType.ATTRIBUTE,
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
