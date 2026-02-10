"""
YAML selector validation for template framework.

This module provides validation for YAML selector files, ensuring they follow
the correct schema and contain all required fields for proper functionality.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set
from enum import Enum
import yaml
import jsonschema
from jsonschema import validate, ValidationError, Draft7Validator

from .interfaces import IValidationFramework


logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation levels."""
    STRICT = "strict"
    LENIENT = "lenient"
    DISABLED = "disabled"


class YAMLSelectorValidator:
    """
    YAML selector validator for template framework.
    
    This class validates YAML selector files against the expected schema
    and provides detailed error reporting for validation failures.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize YAML selector validator.
        
        Args:
            config: Validator configuration
        """
        self.config = config or {}
        
        # Validation configuration
        self.validation_config = {
            "strict_mode": self.config.get("strict_mode", True),
            "allow_extra_fields": self.config.get("allow_extra_fields", False),
            "require_all_fields": self.config.get("require_all_fields", True),
            "validate_selectors": self.config.get("validate_selectors", True),
            "validate_strategies": self.config.get("validate_strategies", True),
            "validate_validation_rules": self.config.get("validate_validation_rules", True)
        }
        
        # YAML schema for selectors
        self.yaml_schema = self._get_yaml_selector_schema()
        self.validator = Draft7Validator(self.yaml_schema)
        
        logger.info("YAMLSelectorValidator initialized")
    
    def _get_yaml_selector_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for YAML selector validation."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["name", "selector", "strategies"],
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "selector": {"type": "string"},
                "strategies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "type"],
                        "properties": {
                            "name": {"type": "string", "enum": ["css", "xpath", "text", "attribute", "hybrid"]},
                            "type": {"type": "string", "enum": ["css", "xpath", "text", "attribute", "hybrid"]},
                            "priority": {"type": "integer", "minimum": 1, "maximum": 100},
                            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                        },
                        "additionalProperties": False
                    },
                    "minItems": 1
                },
                "validation": {
                    "type": "object",
                    "properties": {
                        "required": {"type": "boolean"},
                        "exists": {"type": "boolean"},
                        "text_pattern": {"type": "string"},
                        "min_length": {"type": "integer", "minimum": 0},
                        "max_length": {"type": "integer", "minimum": 0}
                    },
                    "additionalProperties": False
                }
            },
            "additionalProperties": False
        }
    
    async def validate_selector_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Validate a YAML selector file."""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {
                    "valid": False,
                    "errors": [f"File not found: {file_path}"],
                    "warnings": []
                }
            
            if not file_path.suffix.lower() in ['.yaml', '.yml']:
                return {
                    "valid": False,
                    "errors": [f"Invalid file extension: {file_path.suffix}"],
                    "warnings": []
                }
            
            # Read and parse YAML file
            with open(file_path, 'r', encoding='utf-8') as f:
                selector_data = yaml.safe_load(f)
            
            # Validate against schema
            validation_result = await self._validate_selector_data(selector_data, str(file_path))
            
            # Add file-specific information
            validation_result["file_path"] = str(file_path)
            validation_result["file_name"] = file_path.name
            validation_result["file_size"] = file_path.stat().st_size
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Failed to validate selector file {file_path}: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "file_path": str(file_path)
            }
    
    async def _validate_selector_data(self, selector_data: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Validate selector data against schema and business rules."""
        errors = []
        warnings = []
        
        try:
            # Schema validation
            if self.validation_config.get("strict_mode", True):
                try:
                    validate(instance=selector_data, schema=self.yaml_schema)
                except ValidationError as e:
                    errors.extend(self._format_validation_errors(e))
            else:
                try:
                    self.validator.validate(selector_data)
                except ValidationError as e:
                    errors.extend(self._format_validation_errors(e))
            
            # Business rule validation
            business_errors, business_warnings = await self._validate_business_rules(selector_data, file_path)
            errors.extend(business_errors)
            warnings.extend(business_warnings)
            
            # Strategy validation
            if self.validation_config.get("validate_strategies", True):
                strategy_errors, strategy_warnings = await self._validate_strategies(selector_data)
                errors.extend(strategy_errors)
                warnings.extend(strategy_warnings)
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "selector_name": selector_data.get("name", "unknown"),
                "strategies_count": len(selector_data.get("strategies", [])),
                "has_validation": "validation" in selector_data
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation processing error: {str(e)}"],
                "warnings": warnings
            }
    
    def _format_validation_errors(self, validation_error: ValidationError) -> List[str]:
        """Format JSON schema validation errors into readable messages."""
        errors = []
        
        for error in validation_error.errors:
            path = " -> ".join(str(p) for p in error.path) if error.path else "root"
            message = f"Field '{path}': {error.message}"
            errors.append(message)
        
        return errors
    
    async def _validate_business_rules(self, selector_data: Dict[str, Any], file_path: str) -> tuple[List[str], List[str]]:
        """Validate business rules for selector data."""
        errors = []
        warnings = []
        
        # Validate selector name
        name = selector_data.get("name", "")
        if not name:
            errors.append("Selector name is required")
        elif not name.replace("_", "").replace("-", "").isalnum():
            errors.append("Selector name must contain only alphanumeric characters, hyphens, and underscores")
        
        # Validate selector expression
        selector = selector_data.get("selector", "")
        if not selector:
            errors.append("Selector expression is required")
        else:
            if selector.count("'") != selector.count("'") // 2 * 2:
                errors.append("Unmatched quotes in selector expression")
            elif len(selector) > 1000:
                warnings.append("Selector expression is very long (>1000 characters)")
        
        # Validate strategies
        strategies = selector_data.get("strategies", [])
        if not strategies:
            errors.append("At least one strategy is required")
        else:
            strategy_names = [s.get("name") for s in strategies]
            if len(strategy_names) != len(set(strategy_names)):
                errors.append("Duplicate strategy names found")
            
            # Check strategy confidence scores
            for strategy in strategies:
                confidence = strategy.get("confidence")
                if confidence is not None and (confidence < 0.0 or confidence > 1.0):
                    errors.append(f"Strategy '{strategy.get('name')}' has invalid confidence score: {confidence}")
        
        return errors, warnings
    
    async def _validate_strategies(self, selector_data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate strategy configurations."""
        errors = []
        warnings = []
        
        strategies = selector_data.get("strategies", [])
        
        for i, strategy in enumerate(strategies):
            strategy_name = strategy.get("name", f"strategy_{i}")
            
            # Validate strategy type
            strategy_type = strategy.get("type")
            if strategy_type not in ["css", "xpath", "text", "attribute", "hybrid"]:
                errors.append(f"Strategy '{strategy_name}' has invalid type: {strategy_type}")
            
            # Validate confidence
            confidence = strategy.get("confidence")
            if confidence is not None and (confidence < 0.0 or confidence > 1.0):
                errors.append(f"Strategy '{strategy_name}' has invalid confidence: {confidence}")
            
            # Validate priority
            priority = strategy.get("priority")
            if priority is not None and (not isinstance(priority, int) or priority < 1 or priority > 100):
                errors.append(f"Strategy '{strategy_name}' has invalid priority: {priority}")
        
        return errors, warnings
    
    async def validate_selector_directory(self, directory_path: Union[str, Path]) -> Dict[str, Any]:
        """Validate all YAML selector files in a directory."""
        try:
            directory_path = Path(directory_path)
            
            if not directory_path.exists():
                return {
                    "valid": False,
                    "errors": [f"Directory not found: {directory_path}"],
                    "warnings": [],
                    "file_results": []
                }
            
            # Find all YAML files
            yaml_files = list(directory_path.glob("*.yaml")) + list(directory_path.glob("*.yml"))
            
            if not yaml_files:
                return {
                    "valid": True,
                    "errors": [],
                    "warnings": [f"No YAML files found in {directory_path}"],
                    "file_results": []
                }
            
            # Validate each file
            file_results = []
            total_errors = 0
            total_warnings = 0
            
            for yaml_file in yaml_files:
                result = await self.validate_selector_file(yaml_file)
                file_results.append(result)
                
                if not result["valid"]:
                    total_errors += len(result["errors"])
                total_warnings += len(result["warnings"])
            
            return {
                "valid": total_errors == 0,
                "errors": [f"Total errors: {total_errors}"] if total_errors > 0 else [],
                "warnings": [f"Total warnings: {total_warnings}"] if total_warnings > 0 else [],
                "file_count": len(yaml_files),
                "valid_files": len([r for r in file_results if r["valid"]]),
                "invalid_files": len([r for r in file_results if not r["valid"]]),
                "file_results": file_results
            }
            
        except Exception as e:
            logger.error(f"Failed to validate selector directory {directory_path}: {e}")
            return {
                "valid": False,
                "errors": [f"Directory validation error: {str(e)}"],
                "warnings": [],
                "file_results": []
            }
    
    def _is_valid_css_selector(self, selector: str) -> bool:
        """Check if a CSS selector is syntactically valid."""
        try:
            if not selector:
                return False
            
            # Check for balanced brackets
            if selector.count('[') != selector.count(']') or selector.count('(') != selector.count(')'):
                return False
            
            # Check for balanced quotes
            if selector.count("'") != selector.count("'") // 2 * 2:
                return False
            if selector.count('"') != selector.count('"') // 2 * 2:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _is_valid_xpath_selector(self, selector: str) -> bool:
        """Check if an XPath selector is syntactically valid."""
        try:
            if not selector:
                return False
            
            # XPath should start with /, //, ., or ./
            if not selector.startswith(('/', '//', '.', './')):
                return False
            
            # Check for balanced quotes and brackets
            if selector.count("'") != selector.count("'") // 2 * 2:
                return False
            if selector.count('"') != selector.count('"') // 2 * 2:
                return False
            if selector.count('[') != selector.count(']') or selector.count('(') != selector.count(')'):
                return False
            
            return True
            
        except Exception:
            return False


class ExtractionRuleValidator:
    """
    Extraction rule validator for template framework.
    
    This class validates extraction rule configurations against expected schemas
    and ensures they follow framework conventions.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize extraction rule validator.
        
        Args:
            config: Validator configuration
        """
        self.config = config or {}
        
        # Validation configuration
        self.validation_config = {
            "strict_mode": self.config.get("strict_mode", True),
            "require_all_fields": self.config.get("require_all_fields", True),
            "validate_transformations": self.config.get("validate_transformations", True),
            "validate_types": self.config.get("validate_types", True),
            "validate_extraction_logic": self.config.get("validate_extraction_logic", True)
        }
        
        # Extraction rule schemas
        self.extraction_schemas = self._get_extraction_rule_schemas()
        
        logger.info("ExtractionRuleValidator initialized")
    
    def _get_extraction_rule_schemas(self) -> Dict[str, Any]:
        """Get JSON schemas for extraction rule validation."""
        return {
            "text_extraction": {
                "type": "object",
                "required": ["name", "selector", "extraction_type"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "selector": {"type": "string"},
                    "extraction_type": {"type": "string", "enum": ["text", "attribute", "href", "src", "alt", "title", "data-*"]},
                    "transformations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["type"],
                            "properties": {
                                "type": {"type": "string", "enum": ["trim", "clean", "normalize", "lowercase", "uppercase", "title_case", "sentence_case", "snake_case", "kebab_case", "constant", "regex_replace", "date_format"]},
                                "parameters": {"type": "object"}
                            },
                            "additionalProperties": False
                        }
                    },
                    "default_value": {"type": ["string", "number", "boolean", "null"]},
                    "required": {"type": "boolean"},
                    "multi_value": {"type": "boolean"}
                },
                "additionalProperties": False
            },
            "attribute_extraction": {
                "type": "object",
                "required": ["name", "selector", "extraction_type"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "selector": {"type": "string"},
                    "extraction_type": {"type": "string", "enum": ["attribute"]},
                    "attribute": {"type": "string"},
                    "transformations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["type"],
                            "properties": {
                                "type": {"type": "string", "enum": ["trim", "clean", "normalize", "lowercase", "uppercase", "title_case", "sentence_case", "snake_case", "kebabay_case", "constant", "regex_replace", "date_format"]},
                                "parameters": {"type": "object"}
                            },
                            "additionalProperties": False
                        }
                    },
                    "default_value": {"type": ["string", "number", "boolean", "null"]},
                    "required": {"type": "boolean"},
                    "multi_value": {"type": "boolean"}
                },
                "additionalProperties": False
            },
            "link_extraction": {
                "type": "object",
                "required": ["name", "selector", "extraction_type"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "selector": {"type": "string"},
                    "extraction_type": {"type": "string", "enum": ["href", "src", "srcset", "data-*"]},
                    "transformations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["type"],
                            "properties": {
                                "type": {"type": "string", "enum": ["trim", "clean", "normalize", "lowercase", "uppercase", "title_case", "sentence_case", "snake_case", "kebabay_case", "constant", "regex_replace", "date_format"]},
                                "parameters": {"type": "object"}
                            },
                            "additionalProperties": False
                        }
                    },
                    "default_value": {"type": ["string", "null"]},
                    "required": {"type": "boolean"},
                    "multi_value": {"type": "boolean"}
                },
                "additionalProperties": False
            }
        }
    
    async def validate_extraction_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an extraction rule configuration.
        
        Args:
            rule_data: Extraction rule data
            
        Returns:
            Dict[str, Any]: Validation result
        """
        try:
            logger.info(f"Validating extraction rule: {rule_data.get('name', 'unknown')}")
            
            # Determine rule type
            extraction_type = rule_data.get("extraction_type", "text")
            
            # Get appropriate schema
            schema = self.extraction_schemas.get(extraction_type)
            if not schema:
                return {
                    "valid": False,
                    "errors": [f"Unsupported extraction type: {extraction_type}"],
                    "warnings": []
                }
            
            # Validate against schema
            errors = []
            warnings = []
            
            try:
                if self.validation_config.get("strict_mode", True):
                    validate(instance=rule_data, schema=schema)
                else:
                    # Non-strict validation - check required fields only
                    required_fields = schema.get("required", [])
                    for field in required_fields:
                        if field not in rule_data:
                            errors.append(f"Missing required field: {field}")
            
            except ValidationError as e:
                errors.extend(self._format_validation_errors(e))
            
            # Business rule validation
            business_errors, business_warnings = await self._validate_extraction_business_rules(rule_data, extraction_type)
            errors.extend(business_errors)
            warnings.extend(business_warnings)
            
            # Transformation validation
            if self.validation_config.get("validate_transformations", True):
                transform_errors, transform_warnings = await self._validate_transformations(rule_data, extraction_type)
                errors.extend(transform_errors)
                warnings.extend(transform_warnings)
            
            # Type validation
            if self.validation_config.get("validate_types", True):
                type_errors, type_warnings = await self._validate_extraction_types(rule_data, extraction_type)
                errors.extend(type_errors)
                warnings.extend(type_warnings)
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "rule_name": rule_data.get("name", "unknown"),
                "extraction_type": extraction_type,
                "transformations_count": len(rule_data.get("transformations", [])),
                "has_default_value": "default_value" in rule_data
            }
            
        except Exception as e:
            logger.error(f"Failed to validate extraction rule: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "rule_name": rule_data.get("name", "unknown")
            }
    
    async def _validate_extraction_business_rules(self, rule_data: Dict[str, Any], extraction_type: str) -> tuple[List[str], List[str]]:
        """Validate business rules for extraction rules."""
        errors = []
        warnings = []
        
        # Validate rule name
        name = rule_data.get("name", "")
        if not name:
            errors.append("Extraction rule name is required")
        elif not name.replace("_", "").replace("-", "").isalnum():
            errors.append("Extraction rule name must contain only alphanumeric characters, hyphens, and underscores")
        
        # Validate selector
        selector = rule_data.get("selector", "")
        if not selector:
            errors.append("Selector is required for extraction rule")
        
        # Validate based on extraction type
        if extraction_type == "attribute":
            attribute = rule_data.get("attribute")
            if not attribute:
                errors.append("Attribute name is required for attribute extraction")
        
        elif extraction_type in ["href", "src", "srcset", "data-*"]:
            # Link extraction should have href, src, or data-* attribute
            has_standard_attr = any(rule_data.get(attr) for attr in ["href", "src", "srcset"])
            has_data_attr = any(rule_data.get(attr) for attr in rule_data.keys() if attr.startswith("data-"))
            if not (has_standard_attr or has_data_attr):
                warnings.append(f"Link extraction should specify href, src, or data-* attribute")
        
        # Validate transformations
        transformations = rule_data.get("transformations", [])
        for i, transformation in enumerate(transformations):
            transform_name = transformation.get("name", f"transform_{i}")
            
            # Check transformation type
            transform_type = transformation.get("type")
            valid_types = ["trim", "clean", "normalize", "lowercase", "uppercase", "title_case", "sentence_case", "snake_case", "kebabay_case", "constant", "regex_replace", "date_format"]
            if transform_type not in valid_types:
                errors.append(f"Transformation '{transform_name}' has invalid type: {transform_type}")
            
            # Validate regex parameters
            if transform_type == "regex_replace":
                parameters = transformation.get("parameters", {})
                if "pattern" not in parameters:
                    errors.append(f"Regex transformation '{transform_name}' requires 'pattern' parameter")
                elif "replacement" not in parameters:
                    errors.append(f"Regex transformation '{transform_name}' requires 'replacement' parameter")
                elif not isinstance(parameters["pattern"], str) or not isinstance(parameters["replacement"], str):
                    errors.append(f"Regex transformation '{transform_name}' requires string pattern and replacement")
            
            # Validate date format parameters
            if transform_type == "date_format":
                parameters = transformation.get("parameters", {})
                if "format" not in parameters:
                    errors.append(f"Date format transformation '{transform_name}' requires 'format' parameter")
                elif not isinstance(parameters["format"], str):
                    errors.append(f"Date format transformation '{transform_name}' requires string format")
        
        # Validate default value type
        default_value = rule_data.get("default_value")
        if default_value is not None:
            expected_type = self._get_expected_default_type(extraction_type)
            if expected_type and not isinstance(default_value, expected_type):
                warnings.append(f"Default value type mismatch for {extraction_type} extraction: expected {expected_type}, got {type(default_value)}")
        
        return errors, warnings
    
    async def _validate_transformations(self, rule_data: Dict[str, Any], extraction_type: str) -> tuple[List[str], List[str]]:
        """Validate transformation configurations."""
        errors = []
        warnings = []
        
        transformations = rule_data.get("transformations", [])
        
        for i, transformation in enumerate(transformations):
            transform_name = transformation.get("name", f"transform_{i}")
            
            # Check for duplicate transformation names
            transform_names = [t.get("name") for t in transformations]
            if transform_names.count(transform_name) > 1:
                errors.append(f"Duplicate transformation name: {transform_name}")
            
            # Validate transformation type
            transform_type = transformation.get("type")
            valid_types = ["trim", "clean", "normalize", "lowercase", "uppercase", "title_case", "sentence_case", "snake_case", "kebabay_case", "constant", "regex_replace", "date_format"]
            if transform_type not in valid_types:
                errors.append(f"Transformation '{transform_name}' has invalid type: {transform_type}")
            
            # Validate parameters based on type
            if transform_type == "regex_replace":
                parameters = transformation.get("parameters", {})
                if "pattern" not in parameters:
                    errors.append(f"Regex transformation '{transform_name}' requires 'pattern' parameter")
                elif "replacement" not in parameters:
                    errors.append(f"Regex transformation '{transform_name}' requires 'replacement' parameter")
            
            elif transform_type == "date_format":
                parameters = transformation.get("parameters", {})
                if "format" not in parameters:
                    errors.append(f"Date format transformation '{transform_name}' requires 'format' parameter")
                elif not isinstance(parameters["format"], str):
                    errors.append(f"Date format transformation '{transform_name}' requires string format parameter")
            
            elif transform_type == "constant":
                parameters = transformation.get("parameters", {})
                if "value" not in parameters:
                    errors.append(f"Constant transformation '{transform_name}' requires 'value' parameter")
                elif not isinstance(parameters["value"], (str, int, float, bool)):
                    errors.append(f"Constant transformation '{transform_name}' requires string, int, float, or boolean value")
        
        return errors, warnings
    
    async def _validate_extraction_types(self, rule_data: Dict[str, Any], extraction_type: str) -> tuple[List[str], List[str]]:
        """Validate extraction type-specific requirements."""
        errors = []
        warnings = []
        
        if extraction_type == "text":
            # Text extraction can have any default value
            pass
        
        elif extraction_type == "attribute":
            # Attribute extraction requires attribute name
            attribute = rule_data.get("attribute")
            if not attribute:
                errors.append("Attribute extraction requires 'attribute' field")
            elif not isinstance(attribute, str):
                errors.append("Attribute name must be a string")
        
        elif extraction_type in ["href", "src", "srcset", "data-*"]:
            # Link extraction should have appropriate attributes
            has_standard_attr = any(rule_data.get(attr) for attr in ["href", "src", "srcset"])
            has_data_attr = any(rule_data.get(attr) for attr in rule_data.keys() if attr.startswith("data-"))
            if not (has_standard_attr or has_data_attr):
                warnings.append(f"Link extraction should specify href, src, srcset, or data-* attribute")
        
        return errors, warnings
    
    def _get_expected_default_type(self, extraction_type: str) -> type:
        """Get expected default value type for extraction type."""
        type_mapping = {
            "text": str,
            "attribute": str,
            "href": str,
            "src": str,
            "srcset": List[str],
            "data-*": str,
            "alt": str,
            "title": str
        }
        return type_mapping.get(extraction_type, str)
    
    def _format_validation_errors(self, validation_error: ValidationError) -> List[str]:
        """Format JSON schema validation errors."""
        errors = []
        
        for error in validation_error.errors:
            path = " -> ".join(str(p) for p in error.path) if error.path else "root"
            message = f"Field '{path}': {error.message}"
            errors.append(message)
        
        return errors
    
    async def validate_extraction_rules_directory(self, directory_path: Union[str, Path]) -> Dict[str, Any]:
        """Validate all extraction rule files in a directory."""
        try:
            directory_path = Path(directory_path)
            
            if not directory_path.exists():
                return {
                    "valid": False,
                    "errors": [f"Directory not found: {directory_path}"],
                    "warnings": [],
                    "file_results": []
                }
            
            # Find rule files (could be Python files with extraction rules)
            rule_files = []
            
            # Look for extraction rules in Python files
            for py_file in directory_path.glob("*.py"):
                content = py_file.read_text(encoding='utf-8')
                if "ExtractionRule" in content or "extraction_rules" in content:
                    rule_files.append(py_file)
            
            if not rule_files:
                return {
                    "valid": True,
                    "errors": [],
                    "warnings": [f"No extraction rule files found in {directory_path}"],
                    "file_results": []
                }
            
            # Validate each file
            file_results = []
            total_errors = 0
            total_warnings = 0
            
            for rule_file in rule_files:
                # Extract extraction rules from file
                try:
                    # This would need to parse Python files to extract extraction rules
                    # For now, return a placeholder result
                    file_results.append({
                        "file_path": str(rule_file),
                        "valid": True,
                        "errors": [],
                        "warnings": ["Extraction rule validation not fully implemented yet"],
                        "rule_count": 0
                    })
                except Exception as e:
                    file_results.append({
                        "file_path": str(rule_file),
                        "valid": False,
                        "errors": [f"Failed to parse extraction rules: {str(e)}"],
                        "warnings": [],
                        "rule_count": 0
                    })
            
            return {
                "valid": total_errors == 0,
                "errors": [f"Total errors: {total_errors}"] if total_errors > 0 else [],
                "warnings": [f"Total warnings: {total_warnings}"] if total_warnings > 0 else [],
                "file_count": len(rule_files),
                "valid_files": len([r for r in file_results if r["valid"]]),
                "invalid_files": len([r for r in file_results if not r["valid"]]),
                "file_results": file_results
            }
            
        except Exception as e:
            logger.error(f"Failed to validate extraction rules directory {directory_path}: {e}")
            return {
                "valid": False,
                "errors": [f"Directory validation error: {str(e)}"],
                "warnings": [],
                "file_results": []
            }
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update validation configuration."""
        self.validation_config.update(new_config)
        logger.info(f"Extraction rule validation configuration updated: {list(new_config.keys())}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current validation configuration."""
        return self.validation_config.copy()


class FrameworkComplianceValidator:
    """
    Framework integration compliance validator for template framework.
    
    This class validates that templates follow framework conventions and constitutional principles.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize framework compliance validator.
        
        Args:
            config: Validator configuration
        """
        self.config = config or {}
        
        # Compliance configuration
        self.compliance_config = {
            "strict_mode": self.config.get("strict_mode", True),
            "validate_constitutional_compliance": self.config.get("validate_constitutional_compliance", True),
            "validate_framework_integration": self.config.get("validate_framework_integration", True),
            "validate_async_first": self.config.get("validate_async_first", True),
            "validate_selector_centric": self.config.get("validate_selector_centric", True),
            "validate_modularity": self.config.get("validate_modularity", True)
        }
        
        # Constitutional compliance areas
        self.compliance_areas = {
            ComplianceArea.SELECTOR_CENTRIC: {
                "description": "Templates must use existing selector engine, no hardcoded selectors",
                "validation_rules": [
                    "no_hardcoded_selectors",
                    "uses_selector_engine",
                    "selector_engine_available"
                ],
                "implementation": [
                    "check_selector_engine_usage",
                    "validate_selector_registration",
                    "ensure_selector_engine_available"
                ]
            },
            ComplianceArea.MODULARITY: {
                "description": "Templates follow modular patterns with distinct components",
                "validation_rules": [
                    "single_responsibility",
                    "clear_separation",
                    "minimal_dependencies"
                ],
                "implementation": [
                    "check_component_separation",
                    "validate_interface_adherence",
                    "ensure_dependency_minimal"
                ]
            },
            ComplianceArea.ASYNC_FIRST: {
                "description": "Templates use async-first design with Playwright",
                "validation_rules": [
                    "async_implementation",
                    "no_blocking_operations",
                    "proper_error_handling"
                ],
                "implementation": [
                    "check_async_methods",
                    "validate_no_blocking_calls",
                    "ensure_await_usage"
                ]
            },
            ComplianceArea.STEALTH_AWARE: {
                "description": "Templates include stealth and anti-bot detection",
                "validation_rules": [
                    "stealth_configuration",
                    "human_behavior_emulation",
                    "anti_bot_detection"
                ],
                "implementation": [
                    "check_stealth_config",
                    "validate_stealth_features"
                ]
            },
            ComplianceArea.TAB_AWARE: {
                "description": "Templates use tab-aware context scoping",
                "validation_rules": [
                    "tab_management",
                    "context_scoping",
                    "state_isolation"
                ],
                "implementation": [
                    "check_tab_usage",
                    "validate_context_isolation",
                    "ensure_state_management"
                ]
            },
            ComplianceArea.DATA_INTEGRITY: {
                "description": "Templates ensure data integrity and schema versioning",
                "validation_rules": [
                    "schema_validation",
                    "type_safety",
                    "error_handling"
                ],
                "implementation": [
                    "check_schema_usage",
                    "validate_type_safety",
                    "ensure_error_handling"
                ]
            },
            ComplianceArea.FAULT_TOLERANCE: {
                "description": "Templates have graceful degradation and error recovery",
                "validation_rules": [
                    "graceful_degradation",
                    "retry_logic",
                    "error_recovery"
                ],
                "implementation": [
                    "check_error_handling",
                    "validate_retry_logic",
                    "ensure_recovery_mechanisms"
                ]
            },
            ComplianceArea.OBSERVABILITY: {
                "description": "Templates provide structured logging and performance monitoring",
                "validation_rules": [
                    "structured_logging",
                    "performance_monitoring",
                    "error_tracking"
                ],
                "implementation": [
                    "check_logging_usage",
                    "check_performance_monitoring",
                    "ensure_error_tracking"
                ]
            }
        }
        
        logger.info("FrameworkComplianceValidator initialized")
    
    async def validate_template_compliance(self, template_path: str) -> Dict[str, Any]:
        """
        Validate a complete template.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Dict[str, Any]: Validation results
        """
        try:
            start_time = datetime.now()
            logger.info(f"Validating template: {template_path}")
            
            # Check cache first
            cache_key = f"template_{template_path}_{datetime.now().date()}"
            if cache_key in self.validation_cache:
                cached_result = self.validation_cache[cache_key]
                logger.debug(f"Using cached validation result for {template_path}")
                return {
                    "is_valid": cached_result.is_valid,
                    "errors": cached_result.errors,
                    "warnings": cached_result.warnings,
                    "compliance_score": cached_result.compliance_score,
                    "validation_details": cached_result.validation_details,
                    "cached": True
                }
            
            # Perform validation
            validation_result = await self._validate_template_complete(template_path)
            
            # Cache result
            self.validation_cache[cache_key] = validation_result
            
            # Record performance
            validation_time = (datetime.now() - start_time).total_seconds()
            self.validation_times[f"template_{template_path}"] = validation_time
            
            logger.info(f"Template validation completed for {template_path} in {validation_time:.3f}s")
            
            return {
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "compliance_score": validation_result.compliance_score,
                "validation_details": validation_result.validation_details,
                "validation_time": validation_time,
                "cached": False
            }
            
        except Exception as e:
            logger.error(f"Failed to validate template {template_path}: {e}")
            return {
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "compliance_score": 0.0,
                "validation_details": {"error": str(e)},
                "validation_time": 0.0,
                "cached": False
            }
    
    async def validate_selectors(self, selector_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate YAML selector configurations.
        
        Args:
            selector_configs: List of selector configurations
            
        Returns:
            Dict[str, Any]: Validation results
        """
        try:
            start_time = datetime.now()
            logger.info(f"Validating {len(selector_configs)} selector configurations")
            
            all_errors = []
            all_warnings = []
            selector_results = {}
            
            for i, config in enumerate(selector_configs):
                selector_name = config.get("name", f"selector_{i}")
                
                try:
                    result = await self._validate_single_selector(config)
                    selector_results[selector_name] = result
                    
                    all_errors.extend([f"{selector_name}: {error}" for error in result["errors"]])
                    all_warnings.extend([f"{selector_name}: {warning}" for warning in result["warnings"]])
                    
                except Exception as e:
                    error_msg = f"{selector_name}: Validation error - {str(e)}"
                    all_errors.append(error_msg)
                    selector_results[selector_name] = {
                        "is_valid": False,
                        "errors": [str(e)],
                        "warnings": []
                    }
            
            # Calculate overall compliance score
            total_selectors = len(selector_configs)
            valid_selectors = sum(1 for result in selector_results.values() if result.get("is_valid", False))
            compliance_score = valid_selectors / max(total_selectors, 1)
            
            validation_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "is_valid": len(all_errors) == 0,
                "errors": all_errors,
                "warnings": all_warnings,
                "compliance_score": compliance_score,
                "validation_details": {
                    "total_selectors": total_selectors,
                    "valid_selectors": valid_selectors,
                    "selector_results": selector_results
                },
                "validation_time": validation_time
            }
            
        except Exception as e:
            logger.error(f"Failed to validate selectors: {e}")
            return {
                "is_valid": False,
                "errors": [f"Selector validation error: {str(e)}"],
                "warnings": [],
                "compliance_score": 0.0,
                "validation_details": {"error": str(e)},
                "validation_time": 0.0
            }
    
    async def validate_extraction_rules(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate extraction rule configurations.
        
        Args:
            rules: List of extraction rules
            
        Returns:
            Dict[str, Any]: Validation results
        """
        try:
            start_time = datetime.now()
            logger.info(f"Validating {len(rules)} extraction rules")
            
            all_errors = []
            all_warnings = []
            rule_results = {}
            
            for i, rule in enumerate(rules):
                rule_name = rule.get("name", f"rule_{i}")
                
                try:
                    result = await self._validate_single_extraction_rule(rule)
                    rule_results[rule_name] = result
                    
                    all_errors.extend([f"{rule_name}: {error}" for error in result["errors"]])
                    all_warnings.extend([f"{rule_name}: {warning}" for warning in result["warnings"]])
                    
                except Exception as e:
                    error_msg = f"{rule_name}: Validation error - {str(e)}"
                    all_errors.append(error_msg)
                    rule_results[rule_name] = {
                        "is_valid": False,
                        "errors": [str(e)],
                        "warnings": []
                    }
            
            # Calculate overall compliance score
            total_rules = len(rules)
            valid_rules = sum(1 for result in rule_results.values() if result.get("is_valid", False))
            compliance_score = valid_rules / max(total_rules, 1)
            
            validation_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "is_valid": len(all_errors) == 0,
                "errors": all_errors,
                "warnings": all_warnings,
                "compliance_score": compliance_score,
                "validation_details": {
                    "total_rules": total_rules,
                    "valid_rules": valid_rules,
                    "rule_results": rule_results
                },
                "validation_time": validation_time
            }
            
        except Exception as e:
            logger.error(f"Failed to validate extraction rules: {e}")
            return {
                "is_valid": False,
                "errors": [f"Extraction rule validation error: {str(e)}"],
                "warnings": [],
                "compliance_score": 0.0,
                "validation_details": {"error": str(e)},
                "validation_time": 0.0
            }
    
    async def check_framework_compliance(self, template_path: str) -> Dict[str, Any]:
        """
        Check template compliance with framework constitution.
        
        Args:
            template_path: Path to template directory
            
        Returns:
            Dict[str, Any]: Compliance check results
        """
        try:
            start_time = datetime.now()
            logger.info(f"Checking framework compliance for {template_path}")
            
            compliance_results = {}
            all_violations = []
            total_checks = 0
            passed_checks = 0
            
            for area in ComplianceArea:
                try:
                    result = await self._check_compliance_area(template_path, area)
                    compliance_results[area.value] = result
                    
                    total_checks += 1
                    if result["compliant"]:
                        passed_checks += 1
                    else:
                        all_violations.extend([f"{area.value}: {violation}" for violation in result["violations"]])
                        
                except Exception as e:
                    logger.error(f"Error checking compliance for {area.value}: {e}")
                    compliance_results[area.value] = {
                        "compliant": False,
                        "violations": [f"Check error: {str(e)}"],
                        "warnings": []
                    }
                    total_checks += 1
            
            # Calculate overall compliance score
            compliance_score = passed_checks / max(total_checks, 1)
            
            validation_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "is_compliant": len(all_violations) == 0,
                "compliance_score": compliance_score,
                "violations": all_violations,
                "compliance_details": compliance_results,
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "validation_time": validation_time
            }
            
        except Exception as e:
            logger.error(f"Failed to check framework compliance for {template_path}: {e}")
            return {
                "is_compliant": False,
                "compliance_score": 0.0,
                "violations": [f"Compliance check error: {str(e)}"],
                "compliance_details": {},
                "total_checks": 0,
                "passed_checks": 0,
                "validation_time": 0.0
            }
    
    def _load_validation_schemas(self) -> Dict[str, Any]:
        """Load validation schemas."""
        return {
            "template": {
                "type": "object",
                "required": ["name", "version", "framework_version", "site_domain"],
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^[a-z][a-z0-9_-]*$",
                        "minLength": 2,
                        "maxLength": 50
                    },
                    "version": {
                        "type": "string",
                        "pattern": "^\\d+\\.\\d+\\.\\d+$"
                    },
                    "framework_version": {
                        "type": "string",
                        "pattern": "^\\d+\\.\\d+\\.\\d+$"
                    },
                    "site_domain": {
                        "type": "string",
                        "format": "hostname"
                    }
                }
            },
            "selector": {
                "type": "object",
                "required": ["name", "strategies"],
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^[a-z][a-z0-9_]*$"
                    },
                    "strategies": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["type", "weight"],
                            "properties": {
                                "type": {"type": "string"},
                                "weight": {
                                    "type": "number",
                                    "minimum": 0.0,
                                    "maximum": 1.0
                                }
                            }
                        }
                    },
                    "confidence_threshold": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    }
                }
            }
        }
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules."""
        return {
            "template": {
                "naming_conventions": True,
                "structure_requirements": True,
                "dependency_validation": True
            },
            "selector": {
                "strategy_validation": True,
                "confidence_threshold_check": True,
                "multi_strategy_requirement": True
            },
            "extraction": {
                "rule_completeness": True,
                "type_validation": True,
                "transformation_validation": True
            }
        }
    
    def _load_compliance_checks(self) -> Dict[str, Any]:
        """Load constitutional compliance checks."""
        return {
            ComplianceArea.SELECTOR_CENTRIC: {
                "no_hardcoded_selectors": True,
                "semantic_selector_usage": True,
                "multi_strategy_implementation": True
            },
            ComplianceArea.MODULARITY: {
                "single_responsibility": True,
                "clear_separation": True,
                "minimal_dependencies": True
            },
            ComplianceArea.ASYNC_FIRST: {
                "async_implementation": True,
                "no_blocking_operations": True,
                "proper_error_handling": True
            },
            ComplianceArea.STEALTH_AWARE: {
                "stealth_configuration": True,
                "human_behavior_emulation": True,
                "anti_bot_detection": True
            },
            ComplianceArea.TAB_AWARE: {
                "tab_management": True,
                "context_scoping": True,
                "state_isolation": True
            },
            ComplianceArea.DATA_INTEGRITY: {
                "schema_validation": True,
                "type_safety": True,
                "error_handling": True
            },
            ComplianceArea.FAULT_TOLERANCE: {
                "graceful_degradation": True,
                "retry_logic": True,
                "error_recovery": True
            },
            ComplianceArea.OBSERVABILITY: {
                "structured_logging": True,
                "performance_monitoring": True,
                "error_tracking": True
            }
        }
    
    async def _validate_template_complete(self, template_path: str) -> ValidationResult:
        """Validate complete template."""
        errors = []
        warnings = []
        
        # Validate template structure
        if not await self._validate_template_structure(template_path):
            errors.append("Invalid template structure")
        
        # Validate template metadata
        metadata_errors, metadata_warnings = await self._validate_template_metadata(template_path)
        errors.extend(metadata_errors)
        warnings.extend(metadata_warnings)
        
        # Validate template files
        file_errors, file_warnings = await self._validate_template_files(template_path)
        errors.extend(file_errors)
        warnings.extend(file_warnings)
        
        # Calculate compliance score
        compliance_score = 1.0 - (len(errors) / max(len(errors) + len(warnings), 1))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            compliance_score=compliance_score,
            validation_details={
                "template_path": template_path,
                "validation_level": self.validation_level.value,
                "structure_valid": await self._validate_template_structure(template_path)
            }
        )
    
    async def _validate_template_structure(self, template_path: str) -> bool:
        """Validate template directory structure."""
        try:
            path_obj = Path(template_path)
            
            if not path_obj.is_dir():
                return False
            
            # Required files
            required_files = ["scraper.py"]
            for required_file in required_files:
                if not (path_obj / required_file).exists():
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating template structure: {e}")
            return False
    
    async def _validate_template_metadata(self, template_path: str) -> Tuple[List[str], List[str]]:
        """Validate template metadata."""
        errors = []
        warnings = []
        
        try:
            # Check for config.py and extract metadata
            config_file = Path(template_path) / "config.py"
            if config_file.exists():
                # Simple validation - in real implementation, this would be more sophisticated
                content = config_file.read_text(encoding='utf-8')
                
                # Check for required constants
                if "SITE_DOMAIN" not in content:
                    warnings.append("SITE_DOMAIN not defined in config.py")
                
                # Check naming conventions
                if re.search(r'\b[A-Z]{2,}\b', content):  # All caps constants
                    pass  # This is actually good practice
                else:
                    warnings.append("Consider using ALL_CAPS for constants")
            
        except Exception as e:
            errors.append(f"Error reading template metadata: {e}")
        
        return errors, warnings
    
    async def _validate_template_files(self, template_path: str) -> Tuple[List[str], List[str]]:
        """Validate template files."""
        errors = []
        warnings = []
        
        try:
            path_obj = Path(template_path)
            
            # Validate Python files
            for py_file in path_obj.glob("*.py"):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    
                    # Check for common issues
                    if "import *" in content:
                        warnings.append(f"Wildcard import in {py_file.name}")
                    
                    if "eval(" in content or "exec(" in content:
                        errors.append(f"Use of eval/exec in {py_file.name}")
                    
                    # Check for async/await usage
                    if py_file.name != "__init__.py" and "async def" not in content:
                        warnings.append(f"No async functions found in {py_file.name}")
                        
                except Exception as e:
                    errors.append(f"Error reading {py_file.name}: {e}")
            
            # Validate YAML files
            selectors_dir = path_obj / "selectors"
            if selectors_dir.exists():
                for yaml_file in selectors_dir.glob("*.yaml"):
                    try:
                        import yaml
                        with open(yaml_file, 'r', encoding='utf-8') as f:
                            yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        errors.append(f"Invalid YAML in {yaml_file.name}: {e}")
                    except Exception as e:
                        errors.append(f"Error reading {yaml_file.name}: {e}")
            
        except Exception as e:
            errors.append(f"Error validating template files: {e}")
        
        return errors, warnings
    
    async def _validate_single_selector(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single selector configuration."""
        errors = []
        warnings = []
        
        try:
            # Schema validation
            jsonschema.validate(config, self.schemas["selector"])
            
            # Additional checks
            strategies = config.get("strategies", [])
            if len(strategies) == 1:
                warnings.append("Single strategy selector - consider adding fallback strategies")
            
            # Check strategy weights
            total_weight = sum(s.get("weight", 0) for s in strategies)
            if total_weight > 1.0:
                warnings.append(f"Strategy weights sum to {total_weight} - consider normalization")
            
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def _validate_single_extraction_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single extraction rule."""
        errors = []
        warnings = []
        
        try:
            # Check required fields
            required_fields = ["selector", "extraction_type"]
            for field in required_fields:
                if field not in rule:
                    errors.append(f"Missing required field: {field}")
            
            # Validate extraction type
            extraction_type = rule.get("extraction_type")
            valid_types = ["TEXT", "ATTRIBUTE", "HTML", "LIST"]
            if extraction_type not in valid_types:
                errors.append(f"Invalid extraction_type: {extraction_type}")
            
            # Validate data type
            data_type = rule.get("data_type")
            if data_type:
                valid_data_types = ["STRING", "INTEGER", "FLOAT", "BOOLEAN", "DATETIME"]
                if data_type not in valid_data_types:
                    errors.append(f"Invalid data_type: {data_type}")
            
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def _check_compliance_area(self, template_path: str, area: ComplianceArea) -> Dict[str, Any]:
        """Check compliance for a specific area."""
        violations = []
        warnings = []
        
        try:
            checks = self.compliance_checks.get(area, {})
            
            # Implement specific compliance checks based on area
            if area == ComplianceArea.SELECTOR_CENTRIC:
                violations.extend(await self._check_selector_centric_compliance(template_path))
            elif area == ComplianceArea.ASYNC_FIRST:
                violations.extend(await self._check_async_first_compliance(template_path))
            elif area == ComplianceArea.MODULARITY:
                violations.extend(await self._check_modularity_compliance(template_path))
            # Add other areas as needed
            
        except Exception as e:
            violations.append(f"Compliance check error: {e}")
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "warnings": warnings
        }
    
    async def _check_selector_centric_compliance(self, template_path: str) -> List[str]:
        """Check selector-centric compliance."""
        violations = []
        
        try:
            # Check for hardcoded selectors in Python files
            path_obj = Path(template_path)
            for py_file in path_obj.glob("*.py"):
                content = py_file.read_text(encoding='utf-8')
                
                # Look for hardcoded CSS selectors
                hardcoded_patterns = [
                    r'page\.query_selector\(["\'][^"\']*["\']',
                    r'page\.querySelector\(["\'][^"\']*["\']',
                    r'\.get_by_text\(["\'][^"\']*["\']',
                ]
                
                for pattern in hardcoded_patterns:
                    if re.search(pattern, content):
                        violations.append(f"Hardcoded selector found in {py_file.name}")
                        break
                        
        except Exception as e:
            violations.append(f"Error checking selector compliance: {e}")
        
        return violations
    
    async def _check_async_first_compliance(self, template_path: str) -> List[str]:
        """Check async-first compliance."""
        violations = []
        
        try:
            path_obj = Path(template_path)
            scraper_file = path_obj / "scraper.py"
            
            if scraper_file.exists():
                content = scraper_file.read_text(encoding='utf-8')
                
                # Check for synchronous operations
                if "time.sleep(" in content:
                    violations.append("Synchronous sleep found - use asyncio.sleep")
                
                if "requests." in content or "urllib." in content:
                    violations.append("Synchronous HTTP requests found - use async HTTP client")
                
                # Check for proper async/await usage
                if "def scrape(" in content and "async def scrape(" not in content:
                    violations.append("scrape method should be async")
                        
        except Exception as e:
            violations.append(f"Error checking async compliance: {e}")
        
        return violations
    
    async def _check_modularity_compliance(self, template_path: str) -> List[str]:
        """Check modularity compliance."""
        violations = []
        
        try:
            path_obj = Path(template_path)
            
            # Check for proper file organization
            required_structure = ["scraper.py"]
            for required_file in required_structure:
                if not (path_obj / required_file).exists():
                    violations.append(f"Missing required file: {required_file}")
            
            # Check for overly large files (indicates poor modularity)
            for py_file in path_obj.glob("*.py"):
                if py_file.stat().st_size > 10000:  # 10KB limit
                    violations.append(f"Large file detected: {py_file.name} ({py_file.stat().st_size} bytes)")
                        
        except Exception as e:
            violations.append(f"Error checking modularity compliance: {e}")
        
        return violations
