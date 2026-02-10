"""
Selector validation framework for YAML selector system.

This module provides comprehensive validation for YAML selectors including
structure validation, rule validation, and error reporting.
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import logging

from .models import (
    YAMLSelector, SelectorStrategy, SelectorValidationError, 
    ValidationResult, ErrorType, Severity, SelectorType, StrategyType
)

logger = logging.getLogger(__name__)


class SelectorValidator:
    """Validates YAML selectors and their configurations."""
    
    def __init__(self):
        """Initialize validator with default validation rules."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._selector_id_cache: Set[str] = set()
    
    def validate_selector(self, selector: YAMLSelector) -> ValidationResult:
        """Validate a single YAML selector."""
        result = ValidationResult(is_valid=True)
        
        try:
            # Basic structure validation
            self._validate_basic_structure(selector, result)
            
            # ID uniqueness validation
            self._validate_selector_id(selector, result)
            
            # Selector type validation
            self._validate_selector_type(selector, result)
            
            # Pattern validation
            self._validate_pattern(selector, result)
            
            # Strategies validation
            self._validate_strategies(selector, result)
            
            # Cross-field validation
            self._validate_cross_fields(selector, result)
            
            # File path validation
            self._validate_file_path(selector, result)
            
            # Validation rules validation
            self._validate_validation_rules(selector, result)
            
            # Metadata validation
            self._validate_metadata(selector, result)
            
        except Exception as e:
            error = SelectorValidationError(
                selector_id=selector.id,
                error_type=ErrorType.VALIDATION_ERROR,
                field_path="root",
                error_message=f"Validation failed with exception: {str(e)}",
                severity=Severity.ERROR,
                suggested_fix="Check selector configuration and try again"
            )
            result.add_error(error)
        
        return result
    
    def validate_selector_file(self, file_path: str) -> ValidationResult:
        """Validate a YAML selector file without loading it."""
        result = ValidationResult(is_valid=True)
        
        try:
            # Check file existence and readability
            path = Path(file_path)
            if not path.exists():
                error = SelectorValidationError(
                    selector_id="unknown",
                    error_type=ErrorType.FILE_ERROR,
                    field_path="file_path",
                    error_message=f"File not found: {file_path}",
                    severity=Severity.ERROR,
                    suggested_fix="Ensure the file path is correct and file exists"
                )
                result.add_error(error)
                return result
            
            if not path.is_file():
                error = SelectorValidationError(
                    selector_id="unknown",
                    error_type=ErrorType.FILE_ERROR,
                    field_path="file_path",
                    error_message=f"Path is not a file: {file_path}",
                    severity=Severity.ERROR,
                    suggested_fix="Ensure the path points to a valid YAML file"
                )
                result.add_error(error)
                return result
            
            # Check file extension
            if path.suffix.lower() not in ['.yaml', '.yml']:
                error = SelectorValidationError(
                    selector_id="unknown",
                    error_type=ErrorType.FILE_ERROR,
                    field_path="file_path",
                    error_message=f"Invalid file extension: {path.suffix}",
                    severity=Severity.ERROR,
                    suggested_fix="Use .yaml or .yml extension for selector files"
                )
                result.add_error(error)
            
            # Check file size (prevent DoS)
            file_size = path.stat().st_size
            max_size = 1024 * 1024  # 1MB limit
            if file_size > max_size:
                error = SelectorValidationError(
                    selector_id="unknown",
                    error_type=ErrorType.FILE_ERROR,
                    field_path="file_path",
                    error_message=f"File too large: {file_size} bytes (max: {max_size})",
                    severity=Severity.ERROR,
                    suggested_fix="Reduce file size or split into multiple files"
                )
                result.add_error(error)
            
        except Exception as e:
            error = SelectorValidationError(
                selector_id="unknown",
                error_type=ErrorType.FILE_ERROR,
                field_path="file_path",
                error_message=f"File validation failed: {str(e)}",
                severity=Severity.ERROR,
                suggested_fix="Check file permissions and path"
            )
            result.add_error(error)
        
        return result
    
    def _validate_basic_structure(self, selector: YAMLSelector, result: ValidationResult):
        """Validate basic selector structure."""
        if not selector.id or not selector.id.strip():
            error = SelectorValidationError(
                selector_id=selector.id or "unknown",
                error_type=ErrorType.STRUCTURE_ERROR,
                field_path="id",
                error_message="Selector ID is required and cannot be empty",
                severity=Severity.ERROR,
                suggested_fix="Add a unique ID for the selector"
            )
            result.add_error(error)
        
        if not selector.name or not selector.name.strip():
            error = SelectorValidationError(
                selector_id=selector.id or "unknown",
                error_type=ErrorType.STRUCTURE_ERROR,
                field_path="name",
                error_message="Selector name is required and cannot be empty",
                severity=Severity.ERROR,
                suggested_fix="Add a descriptive name for the selector"
            )
            result.add_error(error)
        
        if not selector.pattern or not selector.pattern.strip():
            error = SelectorValidationError(
                selector_id=selector.id,
                error_type=ErrorType.STRUCTURE_ERROR,
                field_path="pattern",
                error_message="Selector pattern is required and cannot be empty",
                severity=Severity.ERROR,
                suggested_fix="Add a valid selector pattern"
            )
            result.add_error(error)
        
        if not selector.strategies:
            error = SelectorValidationError(
                selector_id=selector.id,
                error_type=ErrorType.STRUCTURE_ERROR,
                field_path="strategies",
                error_message="At least one strategy is required",
                severity=Severity.ERROR,
                suggested_fix="Add at least one resolution strategy"
            )
            result.add_error(error)
    
    def _validate_selector_id(self, selector: YAMLSelector, result: ValidationResult):
        """Validate selector ID format and uniqueness."""
        if selector.id:
            # Check ID format (alphanumeric, underscores, hyphens)
            if not re.match(r'^[a-zA-Z0-9_-]+$', selector.id):
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path="id",
                    error_message="Selector ID contains invalid characters",
                    severity=Severity.ERROR,
                    suggested_fix="Use only alphanumeric characters, underscores, and hyphens"
                )
                result.add_error(error)
            
            # Check ID length
            if len(selector.id) > 100:
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path="id",
                    error_message="Selector ID is too long (max 100 characters)",
                    severity=Severity.WARNING,
                    suggested_fix="Shorten the selector ID"
                )
                result.add_warning(error)
    
    def _validate_selector_type(self, selector: YAMLSelector, result: ValidationResult):
        """Validate selector type."""
        valid_types = [stype.value for stype in SelectorType]
        if selector.selector_type.value not in valid_types:
            error = SelectorValidationError(
                selector_id=selector.id,
                error_type=ErrorType.VALIDATION_ERROR,
                field_path="selector_type",
                error_message=f"Invalid selector type: {selector.selector_type.value}",
                severity=Severity.ERROR,
                suggested_fix=f"Use one of: {', '.join(valid_types)}"
            )
            result.add_error(error)
    
    def _validate_pattern(self, selector: YAMLSelector, result: ValidationResult):
        """Validate selector pattern based on type."""
        pattern = selector.pattern
        
        if selector.selector_type == SelectorType.CSS:
            # Basic CSS pattern validation
            if not self._is_valid_css_selector(pattern):
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path="pattern",
                    error_message="Invalid CSS selector pattern",
                    severity=Severity.ERROR,
                    suggested_fix="Check CSS selector syntax"
                )
                result.add_error(error)
        
        elif selector.selector_type == SelectorType.XPATH:
            # Basic XPath pattern validation
            if not self._is_valid_xpath_selector(pattern):
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path="pattern",
                    error_message="Invalid XPath selector pattern",
                    severity=Severity.ERROR,
                    suggested_fix="Check XPath selector syntax"
                )
                result.add_error(error)
        
        elif selector.selector_type == SelectorType.TEXT:
            # Text pattern validation
            if not pattern.strip():
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path="pattern",
                    error_message="Text pattern cannot be empty",
                    severity=Severity.ERROR,
                    suggested_fix="Provide text to match"
                )
                result.add_error(error)
        
        elif selector.selector_type == SelectorType.ATTRIBUTE:
            # Attribute pattern validation
            if not re.match(r'^[a-zA-Z_-]+$', pattern):
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path="pattern",
                    error_message="Invalid attribute name pattern",
                    severity=Severity.ERROR,
                    suggested_fix="Use valid HTML attribute name"
                )
                result.add_error(error)
    
    def _validate_strategies(self, selector: YAMLSelector, result: ValidationResult):
        """Validate selector strategies."""
        strategy_priorities = []
        
        for i, strategy in enumerate(selector.strategies):
            # Validate strategy structure
            strategy_errors = strategy.validate()
            for error in strategy_errors:
                validation_error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path=f"strategies[{i}]",
                    error_message=error,
                    severity=Severity.ERROR,
                    suggested_fix="Fix strategy configuration"
                )
                result.add_error(validation_error)
            
            # Check for duplicate priorities
            if strategy.priority in strategy_priorities:
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path=f"strategies[{i}].priority",
                    error_message=f"Duplicate strategy priority: {strategy.priority}",
                    severity=Severity.ERROR,
                    suggested_fix="Use unique priorities for all strategies"
                )
                result.add_error(error)
            else:
                strategy_priorities.append(strategy.priority)
            
            # Validate strategy-specific configuration
            self._validate_strategy_config(selector, strategy, i, result)
    
    def _validate_strategy_config(self, selector: YAMLSelector, strategy: SelectorStrategy, index: int, result: ValidationResult):
        """Validate strategy-specific configuration."""
        field_prefix = f"strategies[{index}].config"
        
        if strategy.type == StrategyType.TEXT_ANCHOR:
            if "anchor_text" not in strategy.config:
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path=f"{field_prefix}.anchor_text",
                    error_message="Text anchor strategy requires 'anchor_text' configuration",
                    severity=Severity.ERROR,
                    suggested_fix="Add 'anchor_text' to strategy configuration"
                )
                result.add_error(error)
        
        elif strategy.type == StrategyType.ATTRIBUTE_MATCH:
            required_fields = ["attribute", "value_pattern"]
            for field in required_fields:
                if field not in strategy.config:
                    error = SelectorValidationError(
                        selector_id=selector.id,
                        error_type=ErrorType.VALIDATION_ERROR,
                        field_path=f"{field_prefix}.{field}",
                        error_message=f"Attribute match strategy requires '{field}' configuration",
                        severity=Severity.ERROR,
                        suggested_fix=f"Add '{field}' to strategy configuration"
                    )
                    result.add_error(error)
        
        elif strategy.type == StrategyType.DOM_RELATIONSHIP:
            required_fields = ["relationship_type", "target_selector"]
            for field in required_fields:
                if field not in strategy.config:
                    error = SelectorValidationError(
                        selector_id=selector.id,
                        error_type=ErrorType.VALIDATION_ERROR,
                        field_path=f"{field_prefix}.{field}",
                        error_message=f"DOM relationship strategy requires '{field}' configuration",
                        severity=Severity.ERROR,
                        suggested_fix=f"Add '{field}' to strategy configuration"
                    )
                    result.add_error(error)
        
        elif strategy.type == StrategyType.ROLE_BASED:
            if "role" not in strategy.config:
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path=f"{field_prefix}.role",
                    error_message="Role-based strategy requires 'role' configuration",
                    severity=Severity.ERROR,
                    suggested_fix="Add 'role' to strategy configuration"
                )
                result.add_error(error)
    
    def _validate_cross_fields(self, selector: YAMLSelector, result: ValidationResult):
        """Validate cross-field dependencies and constraints."""
        # Check confidence thresholds are reasonable
        for i, strategy in enumerate(selector.strategies):
            if strategy.confidence_threshold < 0.0 or strategy.confidence_threshold > 1.0:
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path=f"strategies[{i}].confidence_threshold",
                    error_message="Confidence threshold must be between 0.0 and 1.0",
                    severity=Severity.ERROR,
                    suggested_fix="Set confidence_threshold to a value between 0.0 and 1.0"
                )
                result.add_error(error)
        
        # Check strategy priorities are positive
        for i, strategy in enumerate(selector.strategies):
            if strategy.priority < 1:
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path=f"strategies[{i}].priority",
                    error_message="Strategy priority must be positive integer",
                    severity=Severity.ERROR,
                    suggested_fix="Set priority to a positive integer (1 or higher)"
                )
                result.add_error(error)
    
    def _validate_file_path(self, selector: YAMLSelector, result: ValidationResult):
        """Validate selector file path."""
        if selector.file_path:
            path = Path(selector.file_path)
            if not path.exists():
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.FILE_ERROR,
                    field_path="file_path",
                    error_message=f"Selector file does not exist: {selector.file_path}",
                    severity=Severity.WARNING,
                    suggested_fix="Ensure the file path is correct"
                )
                result.add_warning(error)
            elif not path.is_file():
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.FILE_ERROR,
                    field_path="file_path",
                    error_message=f"Path is not a file: {selector.file_path}",
                    severity=Severity.WARNING,
                    suggested_fix="Ensure the path points to a valid file"
                )
                result.add_warning(error)
    
    def _validate_validation_rules(self, selector: YAMLSelector, result: ValidationResult):
        """Validate validation rules configuration."""
        if selector.validation_rules:
            if not isinstance(selector.validation_rules, dict):
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path="validation_rules",
                    error_message="Validation rules must be a dictionary",
                    severity=Severity.ERROR,
                    suggested_fix="Convert validation_rules to a dictionary"
                )
                result.add_error(error)
            
            # Check for known validation rule keys
            known_rules = ["min_confidence", "required_attributes", "max_results", "timeout"]
            for rule_key in selector.validation_rules:
                if rule_key not in known_rules:
                    error = SelectorValidationError(
                        selector_id=selector.id,
                        error_type=ErrorType.VALIDATION_ERROR,
                        field_path=f"validation_rules.{rule_key}",
                        error_message=f"Unknown validation rule: {rule_key}",
                        severity=Severity.WARNING,
                        suggested_fix=f"Use known validation rules: {', '.join(known_rules)}"
                    )
                    result.add_warning(error)
    
    def _validate_metadata(self, selector: YAMLSelector, result: ValidationResult):
        """Validate metadata configuration."""
        if selector.metadata:
            if not isinstance(selector.metadata, dict):
                error = SelectorValidationError(
                    selector_id=selector.id,
                    error_type=ErrorType.VALIDATION_ERROR,
                    field_path="metadata",
                    error_message="Metadata must be a dictionary",
                    severity=Severity.ERROR,
                    suggested_fix="Convert metadata to a dictionary"
                )
                result.add_error(error)
            
            # Check version in metadata
            if "version" in selector.metadata:
                version = selector.metadata["version"]
                if not isinstance(version, str) or not re.match(r'^\d+\.\d+\.\d+', version):
                    error = SelectorValidationError(
                        selector_id=selector.id,
                        error_type=ErrorType.VALIDATION_ERROR,
                        field_path="metadata.version",
                        error_message="Version must follow semantic versioning (x.y.z)",
                        severity=Severity.ERROR,
                        suggested_fix="Use semantic versioning format (e.g., 1.0.0)"
                    )
                    result.add_error(error)
    
    def _is_valid_css_selector(self, pattern: str) -> bool:
        """Basic CSS selector validation."""
        if not pattern.strip():
            return False
        
        # Very basic validation - could be enhanced with a proper CSS parser
        try:
            # Check for balanced brackets and quotes
            if pattern.count('[') != pattern.count(']'):
                return False
            if pattern.count('(') != pattern.count(')'):
                return False
            if pattern.count('"') % 2 != 0:
                return False
            if pattern.count("'") % 2 != 0:
                return False
            
            return True
        except Exception:
            return False
    
    def _is_valid_xpath_selector(self, pattern: str) -> bool:
        """Basic XPath selector validation."""
        if not pattern.strip():
            return False
        
        # Very basic validation - could be enhanced with a proper XPath parser
        try:
            # Check for balanced quotes and brackets
            if pattern.count('"') % 2 != 0:
                return False
            if pattern.count("'") % 2 != 0:
                return False
            if pattern.count('[') != pattern.count(']'):
                return False
            if pattern.count('(') != pattern.count(')'):
                return False
            
            return True
        except Exception:
            return False
    
    def clear_cache(self):
        """Clear the selector ID cache."""
        self._selector_id_cache.clear()
        self.logger.info("Selector ID cache cleared")
    
    def get_cached_ids(self) -> Set[str]:
        """Get cached selector IDs."""
        return self._selector_id_cache.copy()
