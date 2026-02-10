"""
Data transformation engine for the extractor module.

This module provides a pipeline system for applying transformations
to extracted data during the extraction process.
"""

from typing import Any, Dict, List, Optional, Union

from .rules import TransformationRule, TransformationType
from ..utils.cleaning import StringCleaner
from ..utils.regex_utils import RegexUtils


class TransformationEngine:
    """Engine for applying data transformations."""
    
    def __init__(self):
        """Initialize transformation engine with utilities."""
        self.string_cleaner = StringCleaner()
        self.regex_utils = RegexUtils()
    
    def apply_transformations(
        self,
        value: Any,
        transformations: List[TransformationType],
        rules: Optional[List[TransformationRule]] = None
    ) -> Any:
        """
        Apply a list of transformations to a value.
        
        Args:
            value: The value to transform
            transformations: List of transformation types to apply
            rules: Optional list of detailed transformation rules
            
        Returns:
            Transformed value
        """
        if not transformations and not rules:
            return value
        
        # Convert to string for text-based transformations
        if not isinstance(value, str):
            current_value = str(value)
        else:
            current_value = value
        
        # Apply transformation rules if provided
        if rules:
            # Sort rules by order
            sorted_rules = sorted(rules, key=lambda r: r.order)
            
            for rule in sorted_rules:
                # Check condition if specified
                if rule.condition and not self._evaluate_condition(rule.condition, current_value):
                    continue
                
                # Check if rule should only apply to successful extractions
                if rule.apply_if_success and value is None:
                    continue
                
                current_value = self._apply_single_transformation(
                    current_value,
                    rule.transformation_type,
                    rule.parameters
                )
        else:
            # Apply simple transformations
            for transformation in transformations:
                current_value = self._apply_single_transformation(
                    current_value,
                    transformation,
                    {}
                )
        
        return current_value
    
    def _apply_single_transformation(
        self,
        value: str,
        transformation_type: TransformationType,
        parameters: Dict[str, Any]
    ) -> str:
        """Apply a single transformation to a value."""
        if transformation_type == TransformationType.TRIM:
            return self.string_cleaner.trim(value)
        
        elif transformation_type == TransformationType.CLEAN:
            return self.string_cleaner.clean_whitespace(value)
        
        elif transformation_type == TransformationType.NORMALIZE:
            return self.string_cleaner.normalize(value)
        
        elif transformation_type == TransformationType.LOWERCASE:
            return self.string_cleaner.lowercase(value)
        
        elif transformation_type == TransformationType.UPPERCASE:
            return self.string_cleaner.uppercase(value)
        
        elif transformation_type == TransformationType.REMOVE_WHITESPACE:
            return self.string_cleaner.remove_all_whitespace(value)
        
        elif transformation_type == TransformationType.EXTRACT_NUMBERS:
            numbers = self.regex_utils.extract_numbers(
                value,
                decimal_places=parameters.get('decimal_places')
            )
            return str(numbers[0]) if numbers else ''
        
        elif transformation_type == TransformationType.EXTRACT_EMAILS:
            emails = self.regex_utils.extract_emails(value)
            return emails[0] if emails else ''
        
        elif transformation_type == TransformationType.EXTRACT_PHONES:
            country_code = parameters.get('country_code', 'US')
            phones = self.regex_utils.extract_phone_numbers(value, country_code)
            return phones[0] if phones else ''
        
        else:
            return value
    
    def _evaluate_condition(self, condition: str, value: str) -> bool:
        """Evaluate a condition string against a value."""
        # Simple condition evaluation - can be extended
        try:
            # Basic conditions like "contains('text')" or "length > 10"
            if condition.startswith("contains(") and condition.endswith(")"):
                search_text = condition[10:-1].strip('\'"')
                return search_text in value
            
            elif condition.startswith("length >"):
                min_length = int(condition.split(">")[1].strip())
                return len(value) > min_length
            
            elif condition.startswith("length <"):
                max_length = int(condition.split("<")[1].strip())
                return len(value) < max_length
            
            elif condition.startswith("length =="):
                exact_length = int(condition.split("==")[1].strip())
                return len(value) == exact_length
            
            elif condition.startswith("startswith(") and condition.endswith(")"):
                prefix = condition[11:-1].strip('\'"')
                return value.startswith(prefix)
            
            elif condition.startswith("endswith(") and condition.endswith(")"):
                suffix = condition[9:-1].strip('\'"')
                return value.endswith(suffix)
            
            else:
                # Default to True if condition cannot be evaluated
                return True
                
        except Exception:
            # If condition evaluation fails, default to True
            return True
    
    def create_transformation_rule(
        self,
        transformation_type: TransformationType,
        order: int = 0,
        condition: Optional[str] = None,
        apply_if_success: bool = True,
        parameters: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> TransformationRule:
        """Create a transformation rule with the specified parameters."""
        return TransformationRule(
            transformation_type=transformation_type,
            order=order,
            condition=condition,
            apply_if_success=apply_if_success,
            parameters=parameters or {},
            description=description
        )
    
    def get_available_transformations(self) -> List[Dict[str, Any]]:
        """Get list of available transformations with descriptions."""
        return [
            {
                "type": TransformationType.TRIM,
                "name": "Trim",
                "description": "Remove leading and trailing whitespace",
                "parameters": {}
            },
            {
                "type": TransformationType.CLEAN,
                "name": "Clean",
                "description": "Normalize whitespace by replacing multiple spaces with single space",
                "parameters": {}
            },
            {
                "type": TransformationType.NORMALIZE,
                "name": "Normalize",
                "description": "Normalize Unicode text and remove diacritics",
                "parameters": {}
            },
            {
                "type": TransformationType.LOWERCASE,
                "name": "Lowercase",
                "description": "Convert text to lowercase",
                "parameters": {}
            },
            {
                "type": TransformationType.UPPERCASE,
                "name": "Uppercase",
                "description": "Convert text to uppercase",
                "parameters": {}
            },
            {
                "type": TransformationType.REMOVE_WHITESPACE,
                "name": "Remove Whitespace",
                "description": "Remove all whitespace characters",
                "parameters": {}
            },
            {
                "type": TransformationType.EXTRACT_NUMBERS,
                "name": "Extract Numbers",
                "description": "Extract numbers from text",
                "parameters": {
                    "decimal_places": "Optional: Number of decimal places to round to"
                }
            },
            {
                "type": TransformationType.EXTRACT_EMAILS,
                "name": "Extract Emails",
                "description": "Extract email addresses from text",
                "parameters": {}
            },
            {
                "type": TransformationType.EXTRACT_PHONES,
                "name": "Extract Phone Numbers",
                "description": "Extract phone numbers from text",
                "parameters": {
                    "country_code": "Country code for pattern matching (default: US)"
                }
            }
        ]
    
    def validate_transformation_rule(self, rule: TransformationRule) -> List[str]:
        """Validate a transformation rule and return any errors."""
        errors = []
        
        # Check if transformation type is valid
        if not isinstance(rule.transformation_type, TransformationType):
            errors.append(f"Invalid transformation type: {rule.transformation_type}")
        
        # Validate parameters based on transformation type
        if rule.transformation_type == TransformationType.EXTRACT_NUMBERS:
            if 'decimal_places' in rule.parameters:
                try:
                    decimal_places = rule.parameters['decimal_places']
                    if not isinstance(decimal_places, int) or decimal_places < 0:
                        errors.append("decimal_places must be a non-negative integer")
                except (ValueError, TypeError):
                    errors.append("decimal_places must be an integer")
        
        elif rule.transformation_type == TransformationType.EXTRACT_PHONES:
            if 'country_code' in rule.parameters:
                country_code = rule.parameters['country_code']
                if not isinstance(country_code, str):
                    errors.append("country_code must be a string")
        
        # Validate order
        if not isinstance(rule.order, int) or rule.order < 0:
            errors.append("order must be a non-negative integer")
        
        # Validate condition syntax (basic check)
        if rule.condition:
            try:
                # Try to evaluate condition with a test value
                self._evaluate_condition(rule.condition, "test")
            except Exception:
                errors.append(f"Invalid condition syntax: {rule.condition}")
        
        return errors
