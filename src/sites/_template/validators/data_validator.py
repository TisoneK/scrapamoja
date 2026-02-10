"""
Data validator template for the modular site scraper template.

This module provides data validation functionality with configurable
rules for validating scraped data quality and business rules.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
import re
from urllib.parse import urlparse

from src.sites.base.base_validator import BaseValidator
from src.sites.base.component_interface import ComponentResult


class DataValidator(BaseValidator):
    """Data validator with configurable validation rules for scraped data."""
    
    def __init__(
        self,
        component_id: str = "data_validator",
        name: str = "Data Validator",
        version: str = "1.0.0",
        description: str = "Validates scraped data quality and business rules with configurable rules"
    ):
        """
        Initialize data validator.
        
        Args:
            component_id: Unique identifier for the validator
            name: Human-readable name for the validator
            version: Validator version
            description: Validator description
        """
        super().__init__(
            component_id=component_id,
            name=name,
            version=version,
            description=description,
            validator_type="DATA"
        )
        
        # Validation configuration
        self._strict_mode: bool = False
        self._validate_data_integrity: bool = True
        self._validate_business_rules: bool = True
        self._validate_data_quality: bool = True
        self._validate_data_consistency: bool = True
        self._validate_data_completeness: bool = True
        
        # Validation rules
        self._integrity_rules: Dict[str, List[Dict[str, Any]]] = {}
        self._business_rules: Dict[str, List[Dict[str, Any]]] = {}
        self._quality_rules: Dict[str, List[Dict[str, Any]]] = {}
        self._consistency_rules: Dict[str, List[Dict[str, Any]]] = {}
        self._completeness_rules: Dict[str, List[Dict[str, Any]]] = {}
        self._custom_validators: Dict[str, Callable] = {}
        
        # Validation statistics
        self._validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'validation_errors': [],
            'quality_scores': {},
            'completeness_scores': {}
        }
    
    async def execute(self, target: Any, **kwargs) -> ComponentResult:
        """
        Execute data validation.
        
        Args:
            target: Data to validate
            **kwargs: Additional validation parameters
            
        Returns:
            Validation result
        """
        try:
            start_time = datetime.utcnow()
            
            # Reset validation stats
            self._validation_stats = {
                'total_validations': 0,
                'passed_validations': 0,
                'failed_validations': 0,
                'validation_errors': [],
                'quality_scores': {},
                'completeness_scores': {}
            }
            
            # Handle different data types
            if isinstance(target, list):
                validation_result = await self._validate_data_list(target)
            elif isinstance(target, dict):
                validation_result = await self._validate_data_dict(target)
            else:
                validation_result = await self._validate_data_item(target)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Determine overall success
            is_valid = (
                self._validation_stats['failed_validations'] == 0 or
                (not self._strict_mode and self._validation_stats['passed_validations'] > 0)
            )
            
            return ComponentResult(
                success=is_valid,
                data={
                    'is_valid': is_valid,
                    'validation_result': validation_result,
                    'validation_stats': self._validation_stats,
                    'validation_rules_applied': self._get_applied_rules(),
                    'execution_time_ms': execution_time
                },
                execution_time_ms=execution_time,
                errors=self._validation_stats['validation_errors'] if not is_valid else []
            )
            
        except Exception as e:
            self._log_operation("execute", f"Data validation failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def _validate_data_list(self, data_list: List[Any]) -> Dict[str, Any]:
        """Validate a list of data items."""
        validation_results = []
        
        for index, item in enumerate(data_list):
            item_result = await self._validate_data_item(item, f"item_{index}")
            validation_results.append({
                'index': index,
                'result': item_result
            })
        
        # Calculate overall statistics
        total_items = len(validation_results)
        valid_items = sum(1 for item in validation_results if item['result'].get('is_valid', True))
        
        return {
            'type': 'list',
            'total_items': total_items,
            'valid_items': valid_items,
            'invalid_items': total_items - valid_items,
            'validation_rate': (valid_items / total_items * 100) if total_items > 0 else 0,
            'items': validation_results,
            'is_valid': valid_items == total_items
        }
    
    async def _validate_data_dict(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a dictionary of data."""
        validation_results = {}
        
        for key, value in data_dict.items():
            field_result = await self._validate_data_field(key, value)
            validation_results[key] = field_result
        
        # Calculate overall statistics
        total_fields = len(validation_results)
        valid_fields = sum(1 for field in validation_results.values() if field.get('is_valid', True))
        
        return {
            'type': 'dict',
            'total_fields': total_fields,
            'valid_fields': valid_fields,
            'invalid_fields': total_fields - valid_fields,
            'validation_rate': (valid_fields / total_fields * 100) if total_fields > 0 else 0,
            'fields': validation_results,
            'is_valid': valid_fields == total_fields
        }
    
    async def _validate_data_item(self, item: Any, item_name: str = "item") -> Dict[str, Any]:
        """Validate a single data item."""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'quality_score': 0.0,
            'completeness_score': 0.0,
            'validation_details': {}
        }
        
        # Data integrity validation
        if self._validate_data_integrity:
            integrity_result = await self._validate_data_integrity_rules(item, item_name)
            validation_result['validation_details']['integrity'] = integrity_result
            validation_result['errors'].extend(integrity_result.get('errors', []))
            validation_result['warnings'].extend(integrity_result.get('warnings', []))
            if not integrity_result.get('is_valid', True):
                validation_result['is_valid'] = False
        
        # Business rules validation
        if self._validate_business_rules:
            business_result = await self._validate_business_rules_rules(item, item_name)
            validation_result['validation_details']['business'] = business_result
            validation_result['errors'].extend(business_result.get('errors', []))
            validation_result['warnings'].extend(business_result.get('warnings', []))
            if not business_result.get('is_valid', True):
                validation_result['is_valid'] = False
        
        # Data quality validation
        if self._validate_data_quality:
            quality_result = await self._validate_data_quality_rules(item, item_name)
            validation_result['validation_details']['quality'] = quality_result
            validation_result['quality_score'] = quality_result.get('score', 0.0)
            validation_result['warnings'].extend(quality_result.get('warnings', []))
        
        # Data consistency validation
        if self._validate_data_consistency:
            consistency_result = await self._validate_data_consistency_rules(item, item_name)
            validation_result['validation_details']['consistency'] = consistency_result
            validation_result['errors'].extend(consistency_result.get('errors', []))
            validation_result['warnings'].extend(consistency_result.get('warnings', []))
            if not consistency_result.get('is_valid', True):
                validation_result['is_valid'] = False
        
        # Data completeness validation
        if self._validate_data_completeness:
            completeness_result = await self._validate_data_completeness_rules(item, item_name)
            validation_result['validation_details']['completeness'] = completeness_result
            validation_result['completeness_score'] = completeness_result.get('score', 0.0)
            validation_result['warnings'].extend(completeness_result.get('warnings', []))
        
        # Apply custom validators
        for validator_name, validator in self._custom_validators.items():
            try:
                custom_result = validator(item, item_name)
                if isinstance(custom_result, dict):
                    validation_result['validation_details'][validator_name] = custom_result
                    validation_result['errors'].extend(custom_result.get('errors', []))
                    validation_result['warnings'].extend(custom_result.get('warnings', []))
                    if not custom_result.get('is_valid', True):
                        validation_result['is_valid'] = False
            except Exception as e:
                validation_result['warnings'].append(f"Custom validator {validator_name} failed: {str(e)}")
        
        # Update statistics
        self._validation_stats['total_validations'] += 1
        if validation_result['is_valid']:
            self._validation_stats['passed_validations'] += 1
        else:
            self._validation_stats['failed_validations'] += 1
            self._validation_stats['validation_errors'].extend(validation_result['errors'])
        
        return validation_result
    
    async def _validate_data_field(self, field_name: str, value: Any) -> Dict[str, Any]:
        """Validate a specific data field."""
        return await self._validate_data_item(value, field_name)
    
    async def _validate_data_integrity_rules(self, data: Any, item_name: str) -> Dict[str, Any]:
        """Validate data integrity rules."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        # Check for null/None values
        if data is None:
            result['warnings'].append(f"{item_name}: Data is None")
            return result
        
        # Check for empty strings
        if isinstance(data, str) and not data.strip():
            result['warnings'].append(f"{item_name}: Data is empty string")
        
        # Check for corrupted data patterns
        if isinstance(data, str):
            # Check for HTML entities that weren't decoded
            if '&amp;' in data or '&lt;' in data or '&gt;' in data:
                result['warnings'].append(f"{item_name}: Contains undecoded HTML entities")
            
            # Check for encoding issues
            try:
                data.encode('utf-8').decode('utf-8')
            except UnicodeError:
                result['is_valid'] = False
                result['errors'].append(f"{item_name}: Encoding issues detected")
        
        # Apply integrity-specific rules
        for rule_name, rules in self._integrity_rules.items():
            for rule in rules:
                if await self._evaluate_integrity_rule(rule, data, item_name):
                    result['warnings'].append(f"{item_name}: Integrity rule '{rule_name}' triggered")
        
        return result
    
    async def _validate_business_rules_rules(self, data: Any, item_name: str) -> Dict[str, Any]:
        """Validate business rules."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        # Apply business-specific rules
        for rule_name, rules in self._business_rules.items():
            for rule in rules:
                rule_result = await self._evaluate_business_rule(rule, data, item_name)
                if not rule_result.get('is_valid', True):
                    result['is_valid'] = False
                    result['errors'].extend(rule_result.get('errors', []))
                result['warnings'].extend(rule_result.get('warnings', []))
        
        return result
    
    async def _validate_data_quality_rules(self, data: Any, item_name: str) -> Dict[str, Any]:
        """Validate data quality."""
        result = {'is_valid': True, 'warnings': [], 'score': 0.0}
        score = 100.0
        
        if isinstance(data, str):
            # Check for quality indicators
            if len(data.strip()) < 10:
                score -= 20
                result['warnings'].append(f"{item_name}: Very short text")
            
            # Check for excessive whitespace
            if data.count('  ') > len(data) * 0.1:
                score -= 10
                result['warnings'].append(f"{item_name}: Excessive whitespace")
            
            # Check for special characters ratio
            special_chars = sum(1 for c in data if not c.isalnum() and not c.isspace())
            if special_chars > len(data) * 0.3:
                score -= 15
                result['warnings'].append(f"{item_name}: High special character ratio")
        
        elif isinstance(data, (int, float)):
            # Check for reasonable numeric values
            if data < 0:
                score -= 10
                result['warnings'].append(f"{item_name}: Negative value")
            
            if isinstance(data, float) and abs(data) > 1e10:
                score -= 15
                result['warnings'].append(f"{item_name}: Extremely large value")
        
        # Apply quality-specific rules
        for rule_name, rules in self._quality_rules.items():
            for rule in rules:
                rule_result = await self._evaluate_quality_rule(rule, data, item_name)
                score -= rule_result.get('score_penalty', 0)
                result['warnings'].extend(rule_result.get('warnings', []))
        
        result['score'] = max(0.0, score)
        return result
    
    async def _validate_data_consistency_rules(self, data: Any, item_name: str) -> Dict[str, Any]:
        """Validate data consistency."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        # Apply consistency-specific rules
        for rule_name, rules in self._consistency_rules.items():
            for rule in rules:
                rule_result = await self._evaluate_consistency_rule(rule, data, item_name)
                if not rule_result.get('is_valid', True):
                    result['is_valid'] = False
                    result['errors'].extend(rule_result.get('errors', []))
                result['warnings'].extend(rule_result.get('warnings', []))
        
        return result
    
    async def _validate_data_completeness_rules(self, data: Any, item_name: str) -> Dict[str, Any]:
        """Validate data completeness."""
        result = {'is_valid': True, 'warnings': [], 'score': 100.0}
        
        if isinstance(data, dict):
            total_fields = len(data)
            non_empty_fields = sum(1 for v in data.values() if v is not None and (not isinstance(v, str) or v.strip()))
            
            if total_fields > 0:
                completeness_score = (non_empty_fields / total_fields) * 100
                result['score'] = completeness_score
                
                if completeness_score < 80:
                    result['warnings'].append(f"{item_name}: Low completeness ({completeness_score:.1f}%)")
        
        elif isinstance(data, str):
            if not data.strip():
                result['score'] = 0.0
                result['warnings'].append(f"{item_name}: Empty string")
            elif len(data.strip()) < 5:
                result['score'] = 50.0
                result['warnings'].append(f"{item_name}: Very short content")
        
        # Apply completeness-specific rules
        for rule_name, rules in self._completeness_rules.items():
            for rule in rules:
                rule_result = await self._evaluate_completeness_rule(rule, data, item_name)
                result['score'] -= rule_result.get('score_penalty', 0)
                result['warnings'].extend(rule_result.get('warnings', []))
        
        result['score'] = max(0.0, result['score'])
        return result
    
    async def _evaluate_integrity_rule(self, rule: Dict[str, Any], data: Any, item_name: str) -> bool:
        """Evaluate an integrity rule."""
        rule_type = rule.get('type')
        
        if rule_type == 'not_null':
            return data is None
        elif rule_type == 'not_empty':
            return isinstance(data, str) and not data.strip()
        elif rule_type == 'valid_encoding':
            try:
                if isinstance(data, str):
                    data.encode('utf-8').decode('utf-8')
                return False
            except UnicodeError:
                return True
        elif rule_type == 'custom':
            custom_evaluator = rule.get('evaluator')
            if custom_evaluator and callable(custom_evaluator):
                return custom_evaluator(data, item_name)
        
        return False
    
    async def _evaluate_business_rule(self, rule: Dict[str, Any], data: Any, item_name: str) -> Dict[str, Any]:
        """Evaluate a business rule."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        rule_type = rule.get('type')
        
        if rule_type == 'range':
            min_val = rule.get('min')
            max_val = rule.get('max')
            if isinstance(data, (int, float)):
                if min_val is not None and data < min_val:
                    result['is_valid'] = False
                    result['errors'].append(f"{item_name}: Value {data} below minimum {min_val}")
                if max_val is not None and data > max_val:
                    result['is_valid'] = False
                    result['errors'].append(f"{item_name}: Value {data} above maximum {max_val}")
        
        elif rule_type == 'allowed_values':
            allowed = rule.get('values', [])
            if data not in allowed:
                result['is_valid'] = False
                result['errors'].append(f"{item_name}: Value {data} not in allowed values {allowed}")
        
        elif rule_type == 'pattern':
            pattern = rule.get('pattern')
            if isinstance(data, str) and not re.match(pattern, data):
                result['is_valid'] = False
                result['errors'].append(f"{item_name}: Value '{data}' does not match pattern {pattern}")
        
        elif rule_type == 'custom':
            custom_evaluator = rule.get('evaluator')
            if custom_evaluator and callable(custom_evaluator):
                custom_result = custom_evaluator(data, item_name)
                if isinstance(custom_result, dict):
                    result.update(custom_result)
        
        return result
    
    async def _evaluate_quality_rule(self, rule: Dict[str, Any], data: Any, item_name: str) -> Dict[str, Any]:
        """Evaluate a quality rule."""
        result = {'score_penalty': 0, 'warnings': []}
        
        rule_type = rule.get('type')
        penalty = rule.get('penalty', 10)
        
        if rule_type == 'length_check':
            if isinstance(data, str):
                min_len = rule.get('min_length', 0)
                max_len = rule.get('max_length', float('inf'))
                if len(data) < min_len or len(data) > max_len:
                    result['score_penalty'] = penalty
                    result['warnings'].append(f"{item_name}: Length check failed")
        
        elif rule_type == 'format_check':
            if isinstance(data, str):
                pattern = rule.get('pattern')
                if pattern and not re.match(pattern, data):
                    result['score_penalty'] = penalty
                    result['warnings'].append(f"{item_name}: Format check failed")
        
        elif rule_type == 'custom':
            custom_evaluator = rule.get('evaluator')
            if custom_evaluator and callable(custom_evaluator):
                custom_result = custom_evaluator(data, item_name)
                if isinstance(custom_result, dict):
                    result.update(custom_result)
        
        return result
    
    async def _evaluate_consistency_rule(self, rule: Dict[str, Any], data: Any, item_name: str) -> Dict[str, Any]:
        """Evaluate a consistency rule."""
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        rule_type = rule.get('type')
        
        if rule_type == 'cross_field':
            # This would require access to the full data object
            # For now, just a placeholder
            pass
        
        elif rule_type == 'temporal':
            if isinstance(data, str):
                # Check for reasonable date formats
                date_patterns = [
                    r'\d{4}-\d{2}-\d{2}',
                    r'\d{2}/\d{2}/\d{4}',
                    r'\d{2}-\d{2}-\d{4}'
                ]
                if not any(re.match(pattern, data) for pattern in date_patterns):
                    result['is_valid'] = False
                    result['errors'].append(f"{item_name}: Invalid date format")
        
        elif rule_type == 'custom':
            custom_evaluator = rule.get('evaluator')
            if custom_evaluator and callable(custom_evaluator):
                custom_result = custom_evaluator(data, item_name)
                if isinstance(custom_result, dict):
                    result.update(custom_result)
        
        return result
    
    async def _evaluate_completeness_rule(self, rule: Dict[str, Any], data: Any, item_name: str) -> Dict[str, Any]:
        """Evaluate a completeness rule."""
        result = {'score_penalty': 0, 'warnings': []}
        
        rule_type = rule.get('type')
        penalty = rule.get('penalty', 10)
        
        if rule_type == 'required_fields':
            if isinstance(data, dict):
                required_fields = rule.get('fields', [])
                missing_fields = [f for f in required_fields if f not in data or data[f] is None]
                if missing_fields:
                    result['score_penalty'] = len(missing_fields) * penalty
                    result['warnings'].append(f"{item_name}: Missing required fields: {missing_fields}")
        
        elif rule_type == 'custom':
            custom_evaluator = rule.get('evaluator')
            if custom_evaluator and callable(custom_evaluator):
                custom_result = custom_evaluator(data, item_name)
                if isinstance(custom_result, dict):
                    result.update(custom_result)
        
        return result
    
    def _get_applied_rules(self) -> List[str]:
        """Get list of applied validation rules."""
        rules = []
        
        if self._validate_data_integrity:
            rules.append("data_integrity")
        if self._validate_business_rules:
            rules.append("business_rules")
        if self._validate_data_quality:
            rules.append("data_quality")
        if self._validate_data_consistency:
            rules.append("data_consistency")
        if self._validate_data_completeness:
            rules.append("data_completeness")
        
        rules.extend(self._custom_validators.keys())
        
        return rules
    
    def configure_validation(
        self,
        strict_mode: Optional[bool] = None,
        validate_data_integrity: Optional[bool] = None,
        validate_business_rules: Optional[bool] = None,
        validate_data_quality: Optional[bool] = None,
        validate_data_consistency: Optional[bool] = None,
        validate_data_completeness: Optional[bool] = None
    ) -> None:
        """
        Configure validation settings.
        
        Args:
            strict_mode: Enable strict validation mode
            validate_data_integrity: Enable data integrity validation
            validate_business_rules: Enable business rules validation
            validate_data_quality: Enable data quality validation
            validate_data_consistency: Enable data consistency validation
            validate_data_completeness: Enable data completeness validation
        """
        if strict_mode is not None:
            self._strict_mode = strict_mode
        if validate_data_integrity is not None:
            self._validate_data_integrity = validate_data_integrity
        if validate_business_rules is not None:
            self._validate_business_rules = validate_business_rules
        if validate_data_quality is not None:
            self._validate_data_quality = validate_data_quality
        if validate_data_consistency is not None:
            self._validate_data_consistency = validate_data_consistency
        if validate_data_completeness is not None:
            self._validate_data_completeness = validate_data_completeness
    
    def add_integrity_rule(self, rule_name: str, rule: Dict[str, Any]) -> None:
        """Add an integrity rule."""
        if rule_name not in self._integrity_rules:
            self._integrity_rules[rule_name] = []
        self._integrity_rules[rule_name].append(rule)
    
    def add_business_rule(self, rule_name: str, rule: Dict[str, Any]) -> None:
        """Add a business rule."""
        if rule_name not in self._business_rules:
            self._business_rules[rule_name] = []
        self._business_rules[rule_name].append(rule)
    
    def add_quality_rule(self, rule_name: str, rule: Dict[str, Any]) -> None:
        """Add a quality rule."""
        if rule_name not in self._quality_rules:
            self._quality_rules[rule_name] = []
        self._quality_rules[rule_name].append(rule)
    
    def add_consistency_rule(self, rule_name: str, rule: Dict[str, Any]) -> None:
        """Add a consistency rule."""
        if rule_name not in self._consistency_rules:
            self._consistency_rules[rule_name] = []
        self._consistency_rules[rule_name].append(rule)
    
    def add_completeness_rule(self, rule_name: str, rule: Dict[str, Any]) -> None:
        """Add a completeness rule."""
        if rule_name not in self._completeness_rules:
            self._completeness_rules[rule_name] = []
        self._completeness_rules[rule_name].append(rule)
    
    def add_custom_validator(self, name: str, validator: Callable) -> None:
        """Add a custom validator function."""
        self._custom_validators[name] = validator
    
    def get_validation_configuration(self) -> Dict[str, Any]:
        """Get current validation configuration."""
        return {
            'strict_mode': self._strict_mode,
            'validate_data_integrity': self._validate_data_integrity,
            'validate_business_rules': self._validate_business_rules,
            'validate_data_quality': self._validate_data_quality,
            'validate_data_consistency': self._validate_data_consistency,
            'validate_data_completeness': self._validate_data_completeness,
            'integrity_rules': self._integrity_rules,
            'business_rules': self._business_rules,
            'quality_rules': self._quality_rules,
            'consistency_rules': self._consistency_rules,
            'completeness_rules': self._completeness_rules,
            'custom_validators': list(self._custom_validators.keys()),
            **self.get_configuration()
        }
