"""
Content validation framework for Selector Engine.

Provides comprehensive validation rules and processors for validating
DOM element content as specified in the data model documentation.
"""

import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field

from src.models.selector_models import (
    ElementInfo, ValidationResult, ValidationRule, ValidationType
)
from src.observability.logger import get_logger
from src.utils.exceptions import ValidationError


class IValidator(ABC):
    """Interface for content validators."""
    
    @abstractmethod
    def validate(self, content: str, rule: Any) -> ValidationResult:
        """Validate content against rule."""
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """Get list of supported validation types."""
        pass


@dataclass
class ValidationContext:
    """Context information for validation."""
    element_info: ElementInfo
    selector_name: str
    strategy_used: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class RegexValidator(IValidator):
    """Validator for regex-based content validation."""
    
    def __init__(self):
        self._logger = get_logger("regex_validator")
        self._compiled_patterns: Dict[str, re.Pattern] = {}
    
    def validate(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate content using regex pattern."""
        try:
            # Get or compile pattern
            pattern = self._get_compiled_pattern(rule.pattern)
            
            # Perform validation
            if pattern.fullmatch(content.strip()):
                return ValidationResult(
                    rule_type=ValidationType.REGEX.value,
                    passed=True,
                    score=rule.weight,
                    message="Content matches regex pattern"
                )
            else:
                return ValidationResult(
                    rule_type=ValidationType.REGEX.value,
                    passed=False,
                    score=0.0,
                    message="Content does not match regex pattern"
                )
                
        except Exception as e:
            self._logger.error(
                "regex_validation_failed",
                pattern=rule.pattern,
                content=content[:50],  # First 50 chars for logging
                error=str(e)
            )
            return ValidationResult(
                rule_type=ValidationType.REGEX.value,
                passed=False,
                score=0.0,
                message=f"Regex validation error: {e}"
            )
    
    def get_supported_types(self) -> List[str]:
        """Get supported validation types."""
        return [ValidationType.REGEX.value]
    
    def _get_compiled_pattern(self, pattern: str) -> re.Pattern:
        """Get or compile regex pattern with caching."""
        if pattern not in self._compiled_patterns:
            try:
                self._compiled_patterns[pattern] = re.compile(pattern)
            except re.error as e:
                raise ValidationError(
                    "regex", "compilation", f"Invalid regex pattern '{pattern}': {e}"
                )
        
        return self._compiled_patterns[pattern]


class DataTypeValidator(IValidator):
    """Validator for data type checking."""
    
    def __init__(self):
        self._logger = get_logger("datatype_validator")
    
    def validate(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate content data type."""
        try:
            content = content.strip()
            
            if rule.pattern == "float":
                return self._validate_float(content, rule)
            elif rule.pattern == "int":
                return self._validate_int(content, rule)
            elif rule.pattern == "string":
                return self._validate_string(content, rule)
            elif rule.pattern == "boolean":
                return self._validate_boolean(content, rule)
            elif rule.pattern == "email":
                return self._validate_email(content, rule)
            elif rule.pattern == "url":
                return self._validate_url(content, rule)
            elif rule.pattern == "phone":
                return self._validate_phone(content, rule)
            elif rule.pattern == "date":
                return self._validate_date(content, rule)
            elif rule.pattern == "time":
                return self._validate_time(content, rule)
            else:
                return ValidationResult(
                    rule_type=ValidationType.DATA_TYPE.value,
                    passed=False,
                    score=0.0,
                    message=f"Unsupported data type: {rule.pattern}"
                )
                
        except Exception as e:
            self._logger.error(
                "datatype_validation_failed",
                data_type=rule.pattern,
                content=content[:50],
                error=str(e)
            )
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=False,
                score=0.0,
                message=f"Data type validation error: {e}"
            )
    
    def get_supported_types(self) -> List[str]:
        """Get supported validation types."""
        return [
            ValidationType.DATA_TYPE.value,
            "float", "int", "string", "boolean",
            "email", "url", "phone", "date", "time"
        ]
    
    def _validate_float(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate float data type."""
        try:
            float(content)
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=True,
                score=rule.weight,
                message="Content is a valid float"
            )
        except ValueError:
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=False,
                score=0.0,
                message="Content is not a valid float"
            )
    
    def _validate_int(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate integer data type."""
        try:
            int(content)
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=True,
                score=rule.weight,
                message="Content is a valid integer"
            )
        except ValueError:
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=False,
                score=0.0,
                message="Content is not a valid integer"
            )
    
    def _validate_string(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate string data type."""
        # String is always valid
        return ValidationResult(
            rule_type=ValidationType.DATA_TYPE.value,
            passed=True,
            score=rule.weight,
            message="Content is a valid string"
        )
    
    def _validate_boolean(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate boolean data type."""
        boolean_values = ['true', 'false', '1', '0', 'yes', 'no', 'on', 'off']
        
        if content.lower() in boolean_values:
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=True,
                score=rule.weight,
                message="Content is a valid boolean"
            )
        else:
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=False,
                score=0.0,
                message="Content is not a valid boolean"
            )
    
    def _validate_email(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate email address."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(email_pattern, content):
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=True,
                score=rule.weight,
                message="Content is a valid email address"
            )
        else:
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=False,
                score=0.0,
                message="Content is not a valid email address"
            )
    
    def _validate_url(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate URL."""
        url_pattern = r'^https?://(?:[-\w.])+(?:\.[a-zA-Z0-9]+)+(?:[/?#][^\s]*)?$'
        
        if re.match(url_pattern, content):
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=True,
                score=rule.weight,
                message="Content is a valid URL"
            )
        else:
            return ValidationResult(
                rule_type=ValidationType.DATA_TYPE.value,
                passed=False,
                score=0.0,
                message="Content is not a valid URL"
            )
    
    def _validate_phone(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate phone number."""
        # Basic phone number patterns
        phone_patterns = [
            r'^\+?1?[-.\s]?\(?:(\(\d{3}\)[-.\s]?\)?\d{3}[-.\s]?\d{4}$',  # US format
            r'^\+?\d{10,15}$',  # International
            r'^\d{3}[-.\s]?\d{3}[-.\s]?\d{4}$',  # Simple format
        ]
        
        for pattern in phone_patterns:
            if re.match(pattern, content.replace('-', '').replace(' ', '')):
                return ValidationResult(
                    rule_type=ValidationType.DATA_TYPE.value,
                    passed=True,
                    score=rule.weight,
                    message="Content is a valid phone number"
                )
        
        return ValidationResult(
            rule_type=ValidationType.DATA_TYPE.value,
            passed=False,
            score=0.0,
            message="Content is not a valid phone number"
        )
    
    def _validate_date(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate date format."""
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{1,2}/\d{1,2}/\d{4}$',  # MM/DD/YYYY
            r'^\d{1,2}-\d{1,2}-\d{4}$',  # MM-DD-YYYY
            r'^\d{4}/\d{2}/\d{2}$',  # YYYY/MM/DD
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, content):
                return ValidationResult(
                    rule_type=ValidationType.DATA_TYPE.value,
                    passed=True,
                    score=rule.weight,
                    message="Content is a valid date"
                )
        
        return ValidationResult(
            rule_type=ValidationType.DATA_TYPE.value,
            passed=False,
            score=0.0,
            message="Content is not a valid date"
        )
    
    def _validate_time(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate time format."""
        time_patterns = [
            r'^\d{1,2}:\d{2}$',  # HH:MM
            r'^\d{1,2}:\d{2}\s*(AM|PM)$',  # HH:MM AM/PM
            r'^\d{1,2}:\d{2}:\d{2}$',  # HH:MM:SS
        ]
        
        for pattern in time_patterns:
            if re.match(pattern, content):
                return ValidationResult(
                    rule_type=ValidationType.DATA_TYPE.value,
                    passed=True,
                    score=rule.weight,
                    message="Content is a valid time"
                )
        
        return ValidationResult(
            rule_type=ValidationType.DATA_TYPE.value,
            passed=False,
            score=0.0,
            message="Content is not a valid time"
        )


class SemanticValidator(IValidator):
    """Validator for semantic content validation."""
    
    def __init__(self):
        self._logger = get_logger("semantic_validator")
    
    def validate(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate content using semantic patterns."""
        try:
            content = content.strip().lower()
            
            if rule.pattern == "team_name":
                return self._validate_team_name(content, rule)
            elif rule.pattern == "score":
                return self._validate_score(content, rule)
            elif rule.pattern == "match_status":
                return self._validate_match_status(content, rule)
            elif rule.pattern == "time_period":
                return self._validate_time_period(content, rule)
            elif rule.pattern == "position":
                return self._validate_position(content, rule)
            elif rule.pattern == "player_name":
                return self._validate_player_name(content, rule)
            elif rule.pattern == "tournament_stage":
                return self._validate_tournament_stage(content, rule)
            elif rule.pattern == "venue":
                return self._validate_venue(content, rule)
            else:
                return ValidationResult(
                    rule_type=ValidationType.SEMANTIC.value,
                    passed=False,
                    score=0.0,
                    message=f"Unsupported semantic pattern: {rule.pattern}"
                )
                
        except Exception as e:
            self._logger.error(
                "semantic_validation_failed",
                pattern=rule.pattern,
                content=content[:50],
                error=str(e)
            )
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message=f"Semantic validation error: {e}"
            )
    
    def get_supported_types(self) -> List[str]:
        """Get supported validation types."""
        return [ValidationType.SEMANTIC.value]
    
    def _validate_team_name(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate team name."""
        # Team name patterns
        if len(content) < 2 or len(content) > 50:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Team name length is invalid"
            )
        
        # Should contain letters and possibly spaces/hyphens
        if not re.match(r'^[a-zA-Z\s\-]+$', content):
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Team name contains invalid characters"
            )
        
        # Should not be just numbers or special characters
        if content.isdigit() or not any(c.isalpha() for c in content):
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Team name must contain letters"
            )
        
        # Common team name indicators
        team_indicators = ['fc', 'afc', 'united', 'city', 'sports', 'club']
        if any(indicator in content for indicator in team_indicators):
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=True,
                score=rule.weight,
                message="Content appears to be a team name"
            )
        else:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=True,
                score=rule.weight * 0.8,  # Lower confidence without indicators
                message="Content could be a team name"
            )
    
    def _validate_score(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate score value."""
        # Score patterns
        if not re.match(r'^\d+$', content):
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Score must be numeric"
            )
        
        try:
            score_value = int(content)
            if 0 <= score_value <= 99:
                return ValidationResult(
                    rule_type=ValidationType.SEMANTIC.value,
                    passed=True,
                    score=rule.weight,
                    message="Content is a valid score"
                )
            else:
                return ValidationResult(
                    rule_type=ValidationType.SEMANTIC.value,
                    passed=False,
                    score=0.0,
                    message="Score value is out of range"
                )
        except ValueError:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Score contains invalid characters"
            )
    
    def _validate_match_status(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate match status."""
        valid_statuses = ['ft', 'aet', 'ht', 'ns', 'postponed', 'cancelled', 'abandoned']
        
        if content.lower() in valid_statuses:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=True,
                score=rule.weight,
                message="Content is a valid match status"
            )
        else:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Content is not a valid match status"
            )
    
    def _validate_time_period(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate time period."""
        valid_periods = ['first_half', 'second_half', 'full_time', 'extra_time', 'penalty_time']
        
        if content.lower() in valid_periods:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=True,
                score=rule.weight,
                message="Content is a valid time period"
            )
        else:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Content is not a valid time period"
            )
    
    def _validate_position(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate position."""
        valid_positions = ['goalkeeper', 'defender', 'midfielder', 'forward', 'striker', 'winger', 'substitute']
        
        if content.lower() in valid_positions:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=True,
                score=rule.weight,
                message="Content is a valid position"
            )
        else:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Content is not a valid position"
            )
    
    def _validate_player_name(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate player name."""
        # Similar to team name validation but with player-specific patterns
        if len(content) < 2 or len(content) > 50:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Player name length is invalid"
            )
        
        # Should contain letters and possibly spaces/hyphens/apostrophes
        if not re.match(r'^[a-zA-Z\s\-\.\']+$', content):
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Player name contains invalid characters"
            )
        
        return ValidationResult(
            rule_type=ValidationType.SEMANTIC.value,
            passed=True,
            score=rule.weight,
            message="Content appears to be a player name"
        )
    
    def _validate_tournament_stage(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate tournament stage."""
        valid_stages = [
            'group_stage', 'round_of_16', 'quarter_finals', 'semi_finals', 'final',
            'preliminary', 'qualifying', 'group_a', 'group_b', 'group_c', 'group_d',
            'round_of_32', 'round_of_64', 'last_16', 'last_8', 'last_4', 'last_2'
        ]
        
        if content.lower().replace('_', ' ') in valid_stages:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=True,
                score=rule.weight,
                message="Content is a valid tournament stage"
            )
        else:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Content is not a valid tournament stage"
            )
    
    def _validate_venue(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate venue name."""
        # Basic venue validation
        if len(content) < 2 or len(content) > 100:
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Venue name length is invalid"
            )
        
        # Should contain letters and possibly spaces/hyphens
        if not re.match(r'^[a-zA-Z\s\-\.\']+$', content):
            return ValidationResult(
                rule_type=ValidationType.SEMANTIC.value,
                passed=False,
                score=0.0,
                message="Venue name contains invalid characters"
            )
        
        return ValidationResult(
            rule_type=ValidationType.SEMANTIC.value,
            passed=True,
            score=rule.weight,
            message="Content appears to be a venue name"
        )


class CustomValidator(IValidator):
    """Validator for custom validation logic."""
    
    def __init__(self):
        self._logger = get_logger("custom_validator")
        self._custom_validators: Dict[str, Callable] = {}
    
    def register_validator(self, name: str, validator: Callable) -> None:
        """Register a custom validator."""
        self._custom_validators[name] = validator
        self._logger.info(
            "custom_validator_registered",
            validator_name=name
        )
    
    def validate(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Validate content using custom validator."""
        try:
            # Check if custom validator exists
            if rule.pattern in self._custom_validators:
                validator = self._custom_validators[rule.pattern]
                result = validator(content, rule)
                
                if isinstance(result, ValidationResult):
                    return result
                else:
                    return ValidationResult(
                        rule_type=ValidationType.CUSTOM.value,
                        passed=bool(result),
                        score=rule.weight if result else 0.0,
                        message="Custom validation completed"
                    )
            else:
                return ValidationResult(
                    rule_type=ValidationType.CUSTOM.value,
                    passed=False,
                    score=0.0,
                    message=f"No custom validator for pattern: {rule.pattern}"
                )
                
        except Exception as e:
            self._logger.error(
                "custom_validation_failed",
                pattern=rule.pattern,
                content=content[:50],
                error=str(e)
            )
            return ValidationResult(
                rule_type=ValidationType.CUSTOM.value,
                passed=False,
                score=0.0,
                message=f"Custom validation error: {e}"
            )
    
    def get_supported_types(self) -> List[str]:
        """Get supported validation types."""
        return [ValidationType.CUSTOM.value] + list(self._custom_validators.keys())


class ValidationEngine:
    """Main validation engine that coordinates all validators."""
    
    def __init__(self):
        self._logger = get_logger("validation_engine")
        
        # Initialize validators
        self._validators = {
            ValidationType.REGEX: RegexValidator(),
            ValidationType.DATA_TYPE: DataTypeValidator(),
            ValidationType.SEMANTIC: SemanticValidator(),
            ValidationType.CUSTOM: CustomValidator()
        }
        
        # Register common custom validators
        self._register_common_custom_validators()
    
    def _register_common_custom_validators(self) -> None:
        """Register commonly used custom validators."""
        custom_validator = self._validators[ValidationType.CUSTOM]
        
        # Length validator
        def validate_length(content: str, rule: ValidationRule) -> ValidationResult:
            min_length = getattr(rule, 'min_length', 0)
            max_length = getattr(rule, 'max_length', 1000)
            
            content_length = len(content.strip())
            
            if min_length <= content_length <= max_length:
                return ValidationResult(
                    rule_type=ValidationType.CUSTOM.value,
                    passed=True,
                    score=rule.weight,
                    message=f"Content length is valid ({content_length} chars)"
                )
            else:
                return ValidationResult(
                    rule_type=ValidationType.CUSTOM.value,
                    passed=False,
                    score=0.0,
                    message=f"Content length {content_length} is not between {min_length} and {max_length}"
                )
        
        custom_validator.register_validator("length", validate_length)
        
        # Range validator
        def validate_range(content: str, rule: ValidationRule) -> ValidationResult:
            try:
                value = float(content)
                min_value = getattr(rule, 'min_value', 0.0)
                max_value = getattr(rule, 'max_value', 100.0)
                
                if min_value <= value <= max_value:
                    return ValidationResult(
                        rule_type=ValidationType.CUSTOM.value,
                        passed=True,
                        score=rule.weight,
                        message=f"Value {value} is in range [{min_value}, {max_value}]"
                    )
                else:
                    return ValidationResult(
                        rule_type=ValidationType.CUSTOM.value,
                        passed=False,
                        score=0.0,
                        message=f"Value {value} is not in range [{min_value}, {max_value}]"
                    )
            except ValueError:
                return ValidationResult(
                    rule_type=ValidationType.CUSTOM.value,
                    passed=False,
                    score=0.0,
                    message="Content is not a valid number"
                )
        
        custom_validator.register_validator("range", validate_range)
    
    def validate_content(self, element_info: ElementInfo, rules: List[ValidationRule]) -> List[ValidationResult]:
        """Validate element content against multiple rules."""
        results = []
        
        for rule in rules:
            try:
                validator = self._validators.get(rule.type)
                if validator:
                    result = validator.validate(element_info.text_content, rule)
                    results.append(result)
                else:
                    self._logger.warning(
                        "unknown_validator_type",
                        validation_type=rule.type,
                        fallback="regex"
                    )
                    # Fallback to regex validator
                    regex_validator = self._validators[ValidationType.REGEX]
                    result = regex_validator.validate(element_info.text_content, rule)
                    results.append(result)
                    
            except Exception as e:
                self._logger.error(
                    "rule_validation_failed",
                    validation_type=rule.type,
                    error=str(e)
                )
                results.append(ValidationResult(
                    rule_type=rule.type.value,
                    passed=False,
                    score=0.0,
                    message=f"Validation error: {e}"
                ))
        
        return results
    
    def get_validator(self, validation_type: ValidationType) -> Optional[IValidator]:
        """Get validator by type."""
        return self._validators.get(validation_type)
    
    def list_validators(self) -> List[IValidator]:
        """List all available validators."""
        return list(self._validators.values())
    
    def register_validator(self, validation_type: ValidationType, validator: IValidator) -> None:
        """Register a validator."""
        self._validators[validation_type] = validator
        self._logger.info(
            "validator_registered",
            validation_type=validation_type.value
        )


# Global validation engine instance
validation_engine = ValidationEngine()


def get_validation_engine() -> ValidationEngine:
    """Get global validation engine instance."""
    return validation_engine


def get_validator(validation_type: ValidationType) -> Optional[IValidator]:
    """Get validator by type."""
    return validation_engine.get_validator(validation_type)


# Utility functions for creating validation rules

def create_regex_rule(pattern: str, required: bool = True, weight: float = 1.0, 
                      message: Optional[str] = None) -> ValidationRule:
    """Create a regex validation rule."""
    return ValidationRule(
        type=ValidationType.REGEX,
        pattern=pattern,
        required=required,
        weight=weight,
        message=message or f"Regex validation for pattern: {pattern}"
    )


def create_datatype_rule(data_type: str, required: bool = True, weight: float = 1.0,
                        message: Optional[str] = None) -> ValidationRule:
    """Create a data type validation rule."""
    return ValidationRule(
        type=ValidationType.DATA_TYPE,
        pattern=data_type,
        required=required,
        weight=weight,
        message=message or f"Data type validation for: {data_type}"
    )


def create_semantic_rule(pattern: str, required: bool = True, weight: float = 1.0,
                         message: Optional[str] = None) -> ValidationRule:
    """Create a semantic validation rule."""
    return ValidationRule(
        type=ValidationType.SEMANTIC,
        pattern=pattern,
        required=required,
        weight=weight,
        message=message or f"Semantic validation for pattern: {pattern}"
    )


def create_custom_rule(pattern: str, required: bool = True, weight: float = 1.0,
                        message: Optional[str] = None, **kwargs) -> ValidationRule:
    """Create a custom validation rule."""
    return ValidationRule(
        type=ValidationType.CUSTOM,
        pattern=pattern,
        required=required,
        weight=weight,
        message=message or f"Custom validation for pattern: {pattern}",
        **kwargs
    )
