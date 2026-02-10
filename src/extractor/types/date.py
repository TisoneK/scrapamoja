"""
Date extraction handler for the extractor module.

This module provides functionality for extracting and parsing date/time data
from text content with support for various date formats and standardization.
"""

import re
from datetime import datetime, date
from typing import Any, Dict, Optional, Union

from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

from ..core.rules import ExtractionRule, ExtractionResult, ExtractionType, DataType
from ..exceptions import ExtractionError, TypeConversionError
from ..utils.regex_utils import RegexUtils
from ..utils.cleaning import StringCleaner


class DateExtractor:
    """Handler for date extraction and parsing operations."""
    
    def __init__(self):
        """Initialize date extractor with regex utilities."""
        self.regex_utils = RegexUtils()
    
    def extract(
        self,
        element: Union[Any, Dict[str, Any], str],
        rule: ExtractionRule,
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """
        Extract date data from an element.
        
        Args:
            element: Source element (HTML, JSON, or string)
            rule: Extraction rule defining how to extract date data
            context: Additional context information
            
        Returns:
            ExtractionResult with extracted date value or default value
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
            
            # Convert to target date type
            final_value = self._convert_to_date_type(transformed_text, rule)
            
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
            error_message = f"Date extraction failed: {str(e)}"
            
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
            match = self.regex_utils.find_first(
                pattern=rule.regex_pattern,
                text=text,
                flags=rule.regex_flags,
                group=0,  # Full match
                use_cache=True
            )
            
            if match is None:
                return None
            
            return match
            
        except Exception as e:
            from ..exceptions import PatternNotFoundError
            raise PatternNotFoundError(
                f"Regex pattern application failed: {str(e)}",
                pattern=rule.regex_pattern,
                content_sample=text[:100] + "..." if len(text) > 100 else text
            )
    
    def _apply_transformations(self, text: str, rule: ExtractionRule) -> str:
        """Apply date-specific transformations."""
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
        
        return result
    
    def _convert_to_date_type(self, text: str, rule: ExtractionRule) -> Union[date, datetime]:
        """Convert text to the target date type."""
        if rule.target_type == DataType.DATE:
            return self._convert_to_date(text, rule)
        
        elif rule.target_type == DataType.DATETIME:
            return self._convert_to_datetime(text, rule)
        
        else:
            # If not a date type, return as string
            return text
    
    def _convert_to_date(self, text: str, rule: ExtractionRule) -> date:
        """Convert text to date object."""
        try:
            # If date format is specified, use it
            if rule.date_format:
                parsed_date = datetime.strptime(text, rule.date_format).date()
            else:
                # Use dateutil parser for flexible parsing
                parsed_date = date_parser.parse(text).date()
            
            return parsed_date
            
        except (ValueError, TypeError) as e:
            raise TypeConversionError(
                f"Cannot convert '{text}' to date: {str(e)}",
                source_type="string",
                target_type="date",
                value=text
            )
    
    def _convert_to_datetime(self, text: str, rule: ExtractionRule) -> datetime:
        """Convert text to datetime object."""
        try:
            # If date format is specified, use it
            if rule.date_format:
                parsed_datetime = datetime.strptime(text, rule.date_format)
            else:
                # Use dateutil parser for flexible parsing
                parsed_datetime = date_parser.parse(text)
            
            return parsed_datetime
            
        except (ValueError, TypeError) as e:
            raise TypeConversionError(
                f"Cannot convert '{text}' to datetime: {str(e)}",
                source_type="string",
                target_type="datetime",
                value=text
            )
    
    def _validate_result(self, value: Union[date, datetime], rule: ExtractionRule) -> list:
        """Validate the extracted date result."""
        errors = []
        
        # Type validation
        if rule.target_type == DataType.DATE and not isinstance(value, date):
            errors.append(f"Expected date, got {type(value).__name__}")
        
        elif rule.target_type == DataType.DATETIME and not isinstance(value, datetime):
            errors.append(f"Expected datetime, got {type(value).__name__}")
        
        # Date range validation (if min/max dates are provided)
        if isinstance(value, (date, datetime)):
            # Note: min_date and max_date would need to be added to ExtractionRule for this
            # For now, we'll skip date range validation as it's not in the current model
            pass
        
        # Required field validation
        if rule.required and value is None:
            errors.append("Required field is None")
        
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
