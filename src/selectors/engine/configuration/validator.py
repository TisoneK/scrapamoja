"""
YAML schema validator for selector configuration files.

This module provides validation functionality for YAML selector configurations
ensuring they conform to the expected schema and structure.
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from ...models.selector_config import (
    SelectorConfiguration,
    ConfigurationMetadata,
    ContextDefaults,
    ValidationDefaults,
    SemanticSelector,
    StrategyDefinition,
    ValidationRule,
    ConfidenceConfig,
    ValidationResult
)
from ...models.strategy_template import StrategyTemplate


class ConfigurationValidator:
    """Validator for YAML selector configuration schemas."""
    
    def __init__(self):
        """Initialize the configuration validator."""
        self.supported_strategy_types = [
            "text_anchor",
            "attribute_match",
            "css_selector", 
            "xpath",
            "dom_relationship",
            "role_based"
        ]
        
        self.supported_wait_strategies = [
            "network_idle",
            "domcontentloaded", 
            "load"
        ]
        
        self.supported_validation_types = [
            "string",
            "number",
            "boolean",
            "array",
            "object"
        ]
    
    def validate_configuration(self, config: SelectorConfiguration) -> ValidationResult:
        """Validate a complete configuration against schema."""
        errors: List[str] = []
        warnings: List[str] = []
        start_time = datetime.now()
        
        # Validate metadata
        metadata_errors = self._validate_metadata(config.metadata)
        errors.extend(metadata_errors)
        
        # Validate context defaults if present
        if config.context_defaults:
            context_errors = self._validate_context_defaults(config.context_defaults)
            errors.extend(context_errors)
        
        # Validate validation defaults if present
        if config.validation_defaults:
            validation_errors = self._validate_validation_defaults(config.validation_defaults)
            errors.extend(validation_errors)
        
        # Validate strategy templates
        for template_name, template in config.strategy_templates.items():
            template_errors = self._validate_strategy_template(template, template_name)
            errors.extend(template_errors)
        
        # Validate selectors
        for selector_name, selector in config.selectors.items():
            selector_errors = self._validate_selector(selector, selector_name)
            errors.extend(selector_errors)
        
        # Check for required sections
        if not config.selectors and not config.strategy_templates:
            errors.append("Configuration must contain at least selectors or strategy templates")
        
        # Validate file path
        if not config.file_path:
            errors.append("Configuration file path is required")
        elif not config.file_path.endswith('.yaml'):
            warnings.append("Configuration file should have .yaml extension")
        
        validation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            schema_version=config.metadata.version if config.metadata else "unknown",
            validation_time_ms=validation_time
        )
    
    def validate_inheritance_structure(self, config: SelectorConfiguration) -> ValidationResult:
        """Validate inheritance structure for a configuration."""
        errors: List[str] = []
        warnings: List[str] = []
        start_time = datetime.now()
        
        try:
            # Validate parent path if specified
            if config.parent_path:
                parent_file = Path(config.parent_path)
                if not parent_file.exists():
                    errors.append(f"Parent configuration file not found: {config.parent_path}")
                elif not parent_file.suffix.lower() in ['.yaml', '.yml']:
                    errors.append(f"Parent configuration must be YAML file: {config.parent_path}")
            
            # Validate strategy template references
            for selector_name, selector in config.selectors.items():
                for strategy in selector.strategies:
                    if hasattr(strategy, 'template') and strategy.template:
                        if strategy.template not in config.strategy_templates:
                            # Check if template might be inherited
                            warnings.append(f"Strategy template '{strategy.template}' not found in current configuration for selector '{selector_name}' - may be inherited")
            
            # Validate context defaults consistency
            if config.context_defaults:
                context_errors = self._validate_context_defaults(config.context_defaults)
                errors.extend(context_errors)
            
            # Validate validation defaults consistency
            if config.validation_defaults:
                validation_errors = self._validate_validation_defaults(config.validation_defaults)
                errors.extend(validation_errors)
            
            validation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                schema_version=config.metadata.version if config.metadata else "unknown",
                validation_time_ms=validation_time
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Inheritance validation error: {str(e)}"],
                warnings=warnings,
                schema_version="unknown",
                validation_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def validate_template_inheritance(self, 
                                    config: SelectorConfiguration,
                                    available_templates: Dict[str, 'StrategyTemplate']) -> ValidationResult:
        """Validate template inheritance for a configuration."""
        errors: List[str] = []
        warnings: List[str] = []
        start_time = datetime.now()
        
        try:
            # Check for template references in selectors
            for selector_name, selector in config.selectors.items():
                for strategy in selector.strategies:
                    if hasattr(strategy, 'template') and strategy.template:
                        if strategy.template not in available_templates:
                            errors.append(f"Strategy template '{strategy.template}' not found for selector '{selector_name}'")
                        else:
                            # Validate template compatibility
                            template = available_templates[strategy.template]
                            compatibility_errors = self._validate_template_compatibility(template, strategy)
                            errors.extend(compatibility_errors)
            
            # Check for local template overrides
            for template_name, template in config.strategy_templates.items():
                if template_name in available_templates:
                    warnings.append(f"Strategy template '{template_name}' overrides inherited template")
            
            validation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                schema_version=config.metadata.version if config.metadata else "unknown",
                validation_time_ms=validation_time
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Template inheritance validation error: {str(e)}"],
                warnings=warnings,
                schema_version="unknown",
                validation_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def _validate_template_compatibility(self, template: 'StrategyTemplate', strategy: 'StrategyDefinition') -> List[str]:
        """Validate template compatibility with strategy definition."""
        errors: List[str] = []
        
        # Check if strategy type matches template type
        if template.type != strategy.type:
            errors.append(f"Strategy type mismatch: template '{template.type}' vs strategy '{strategy.type}'")
        
        # Check if parameters are compatible
        if strategy.parameters:
            for param_name, param_value in strategy.parameters.items():
                if param_name in template.parameters:
                    # Parameter override - validate type compatibility
                    template_value = template.parameters[param_name]
                    if type(template_value) != type(param_value):
                        errors.append(f"Parameter type mismatch for '{param_name}': template {type(template_value)} vs override {type(param_value)}")
        
        return errors
    
    def validate_configuration_during_reload(self, 
                                            config: SelectorConfiguration,
                                            file_path: str,
                                            previous_config: Optional[SelectorConfiguration] = None) -> ValidationResult:
        """Validate configuration during hot reload with rollback capability."""
        errors: List[str] = []
        warnings: List[str] = []
        start_time = datetime.now()
        
        try:
            # Standard validation
            standard_validation = self.validate_configuration(config)
            errors.extend(standard_validation.errors)
            warnings.extend(standard_validation.warnings)
            
            # Reload-specific validations
            if previous_config:
                # Check for breaking changes
                breaking_changes = self._detect_breaking_changes(previous_config, config)
                if breaking_changes:
                    warnings.extend([f"Breaking change detected: {change}" for change in breaking_changes])
                
                # Check for selector removal
                removed_selectors = set(previous_config.selectors.keys()) - set(config.selectors.keys())
                if removed_selectors:
                    warnings.extend([f"Selector removed: {selector}" for selector in removed_selectors])
                
                # Check for template removal
                removed_templates = set(previous_config.strategy_templates.keys()) - set(config.strategy_templates.keys())
                if removed_templates:
                    warnings.extend([f"Template removed: {template}" for template in removed_templates])
            
            # Validate inheritance structure
            inheritance_validation = self.validate_inheritance_structure(config)
            errors.extend(inheritance_validation.errors)
            warnings.extend(inheritance_validation.warnings)
            
            validation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                schema_version=config.metadata.version if config.metadata else "unknown",
                validation_time_ms=validation_time
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Reload validation error: {str(e)}"],
                warnings=warnings,
                schema_version="unknown",
                validation_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    def _detect_breaking_changes(self, previous_config: SelectorConfiguration, new_config: SelectorConfiguration) -> List[str]:
        """Detect breaking changes between configurations."""
        breaking_changes = []
        
        # Check for selector type changes
        for selector_name in previous_config.selectors:
            if selector_name in new_config.selectors:
                prev_selector = previous_config.selectors[selector_name]
                new_selector = new_config.selectors[selector_name]
                
                # Check context changes
                if prev_selector.context != new_selector.context:
                    breaking_changes.append(f"Selector '{selector_name}' context changed from '{prev_selector.context}' to '{new_selector.context}'")
                
                # Check strategy count changes
                if len(prev_selector.strategies) != len(new_selector.strategies):
                    breaking_changes.append(f"Selector '{selector_name}' strategy count changed")
        
        # Check for context defaults changes
        if previous_config.context_defaults and new_config.context_defaults:
            prev_context = previous_config.context_defaults
            new_context = new_config.context_defaults
            
            if prev_context.page_type != new_context.page_type:
                breaking_changes.append(f"Context page_type changed from '{prev_context.page_type}' to '{new_context.page_type}'")
        
        return breaking_changes
    
    def validate_yaml_structure(self, yaml_data: Dict, file_path: str) -> ValidationResult:
        """Validate raw YAML data structure before parsing."""
        errors: List[str] = []
        warnings: List[str] = []
        start_time = datetime.now()
        
        if not isinstance(yaml_data, dict):
            errors.append("YAML root must be a dictionary/object")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                schema_version="unknown",
                validation_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
        
        # Validate required top-level sections
        if 'metadata' not in yaml_data:
            errors.append("Missing required 'metadata' section")
        elif not isinstance(yaml_data['metadata'], dict):
            errors.append("'metadata' section must be a dictionary")
        
        # Validate selectors section if present
        if 'selectors' in yaml_data:
            if not isinstance(yaml_data['selectors'], dict):
                errors.append("'selectors' section must be a dictionary")
            else:
                for selector_name, selector_data in yaml_data['selectors'].items():
                    selector_errors = self._validate_selector_yaml_structure(selector_data, selector_name)
                    errors.extend(selector_errors)
        
        # Validate strategy templates section if present
        if 'strategy_templates' in yaml_data:
            if not isinstance(yaml_data['strategy_templates'], dict):
                errors.append("'strategy_templates' section must be a dictionary")
            else:
                for template_name, template_data in yaml_data['strategy_templates'].items():
                    template_errors = self._validate_strategy_template_yaml_structure(template_data, template_name)
                    errors.extend(template_errors)
        
        # Validate context defaults if present
        if 'context_defaults' in yaml_data:
            if not isinstance(yaml_data['context_defaults'], dict):
                errors.append("'context_defaults' section must be a dictionary")
            else:
                context_errors = self._validate_context_defaults_yaml_structure(yaml_data['context_defaults'])
                errors.extend(context_errors)
        
        # Validate validation defaults if present
        if 'validation_defaults' in yaml_data:
            if not isinstance(yaml_data['validation_defaults'], dict):
                errors.append("'validation_defaults' section must be a dictionary")
            else:
                validation_errors = self._validate_validation_defaults_yaml_structure(yaml_data['validation_defaults'])
                errors.extend(validation_errors)
        
        validation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            schema_version=yaml_data.get('metadata', {}).get('version', 'unknown'),
            validation_time_ms=validation_time
        )
    
    def _validate_metadata(self, metadata: ConfigurationMetadata) -> List[str]:
        """Validate configuration metadata."""
        errors: List[str] = []
        
        if not metadata.version:
            errors.append("Metadata version is required")
        elif not re.match(r'^\d+\.\d+\.\d+', metadata.version):
            errors.append(f"Invalid version format: {metadata.version}. Expected semantic versioning (e.g., 1.0.0)")
        
        if not metadata.description:
            errors.append("Metadata description is required")
        elif len(metadata.description.strip()) == 0:
            errors.append("Metadata description cannot be empty")
        
        if not metadata.last_updated:
            errors.append("Metadata last_updated is required")
        else:
            # Validate ISO date format
            try:
                datetime.fromisoformat(metadata.last_updated.replace('Z', '+00:00'))
            except ValueError:
                errors.append(f"Invalid date format in last_updated: {metadata.last_updated}")
        
        return errors
    
    def _validate_context_defaults(self, context_defaults: ContextDefaults) -> List[str]:
        """Validate context defaults."""
        errors: List[str] = []
        
        if not context_defaults.page_type:
            errors.append("Context defaults page_type is required")
        elif not re.match(r'^[a-z][a-z0-9_]*$', context_defaults.page_type):
            errors.append(f"Invalid page_type format: {context_defaults.page_type}")
        
        if context_defaults.wait_strategy not in self.supported_wait_strategies:
            errors.append(f"Unsupported wait strategy: {context_defaults.wait_strategy}")
        
        if context_defaults.timeout <= 0:
            errors.append("Context defaults timeout must be positive")
        elif context_defaults.timeout > 60000:  # 60 seconds max
            warnings.append("Context timeout is very high (>60s)")
        
        if context_defaults.section and not re.match(r'^[a-z][a-z0-9_]*$', context_defaults.section):
            errors.append(f"Invalid section format: {context_defaults.section}")
        
        return errors
    
    def _validate_validation_defaults(self, validation_defaults: ValidationDefaults) -> List[str]:
        """Validate validation defaults."""
        errors: List[str] = []
        
        if validation_defaults.type not in self.supported_validation_types:
            errors.append(f"Unsupported validation type: {validation_defaults.type}")
        
        if validation_defaults.min_length is not None:
            if validation_defaults.min_length < 0:
                errors.append("Validation min_length cannot be negative")
            if validation_defaults.min_length > 10000:
                warnings.append("Validation min_length is very large")
        
        if validation_defaults.max_length is not None:
            if validation_defaults.max_length < 0:
                errors.append("Validation max_length cannot be negative")
            if validation_defaults.max_length > 100000:
                warnings.append("Validation max_length is very large")
        
        if (validation_defaults.min_length is not None and 
            validation_defaults.max_length is not None and 
            validation_defaults.min_length > validation_defaults.max_length):
            errors.append("Validation min_length cannot be greater than max_length")
        
        if validation_defaults.pattern:
            try:
                re.compile(validation_defaults.pattern)
            except re.error as e:
                errors.append(f"Invalid regex pattern: {e}")
        
        return errors
    
    def _validate_strategy_template(self, template: StrategyTemplate, template_name: str) -> List[str]:
        """Validate a strategy template."""
        errors: List[str] = []
        
        if not template.type:
            errors.append(f"Strategy template '{template_name}' missing type")
        elif template.type not in self.supported_strategy_types:
            errors.append(f"Strategy template '{template_name}' has unsupported type: {template.type}")
        
        # Validate required parameters based on strategy type
        required_params = {
            "text_anchor": ["pattern"],
            "attribute_match": ["attribute"],
            "css_selector": ["selector"],
            "xpath": ["expression"],
            "dom_relationship": ["relationship_type"],
            "role_based": ["role"]
        }
        
        if template.type in required_params:
            for param in required_params[template.type]:
                if param not in template.parameters:
                    errors.append(f"Strategy template '{template_name}' missing required parameter: {param}")
        
        # Validate validation if present
        if template.validation:
            validation_errors = self._validate_validation_rule(template.validation, f"template '{template_name}'")
            errors.extend(validation_errors)
        
        # Validate confidence if present
        if template.confidence:
            confidence_errors = self._validate_confidence_config(template.confidence, f"template '{template_name}'")
            errors.extend(confidence_errors)
        
        return errors
    
    def _validate_selector(self, selector: SemanticSelector, selector_name: str) -> List[str]:
        """Validate a semantic selector."""
        errors: List[str] = []
        
        if not selector.name:
            errors.append(f"Selector '{selector_name}' missing name")
        elif not re.match(r'^[a-z][a-z0-9_]*$', selector.name):
            errors.append(f"Invalid selector name format: {selector.name}")
        
        if not selector.description:
            errors.append(f"Selector '{selector_name}' missing description")
        elif len(selector.description.strip()) == 0:
            errors.append(f"Selector '{selector_name}' description cannot be empty")
        
        if not selector.context:
            errors.append(f"Selector '{selector_name}' missing context")
        elif not re.match(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$', selector.context):
            errors.append(f"Invalid context format: {selector.context}")
        
        if not selector.strategies:
            errors.append(f"Selector '{selector_name}' must have at least one strategy")
        else:
            # Validate strategies
            for i, strategy in enumerate(selector.strategies):
                strategy_errors = self._validate_strategy_definition(strategy, f"selector '{selector_name}' strategy {i}")
                errors.extend(strategy_errors)
            
            # Check strategy priorities are unique and ordered
            priorities = [s.priority for s in selector.strategies]
            if len(priorities) != len(set(priorities)):
                errors.append(f"Selector '{selector_name}' has duplicate strategy priorities")
            
            if priorities != sorted(priorities):
                errors.append(f"Selector '{selector_name}' strategies must be ordered by priority")
        
        # Validate validation if present
        if selector.validation:
            validation_errors = self._validate_validation_rule(selector.validation, f"selector '{selector_name}'")
            errors.extend(validation_errors)
        
        # Validate confidence if present
        if selector.confidence:
            confidence_errors = self._validate_confidence_config(selector.confidence, f"selector '{selector_name}'")
            errors.extend(confidence_errors)
        
        return errors
    
    def _validate_strategy_definition(self, strategy: StrategyDefinition, context: str) -> List[str]:
        """Validate a strategy definition."""
        errors: List[str] = []
        
        if not strategy.type:
            errors.append(f"{context} missing strategy type")
        elif strategy.type not in self.supported_strategy_types:
            errors.append(f"{context} has unsupported strategy type: {strategy.type}")
        
        if strategy.template and strategy.parameters:
            errors.append(f"{context} cannot specify both template and parameters")
        
        if strategy.priority <= 0:
            errors.append(f"{context} strategy priority must be positive")
        
        return errors
    
    def _validate_validation_rule(self, validation: ValidationRule, context: str) -> List[str]:
        """Validate a validation rule."""
        errors: List[str] = []
        
        if validation.type and validation.type not in self.supported_validation_types:
            errors.append(f"{context} has unsupported validation type: {validation.type}")
        
        if validation.min_length is not None and validation.min_length < 0:
            errors.append(f"{context} validation min_length cannot be negative")
        
        if validation.max_length is not None and validation.max_length < 0:
            errors.append(f"{context} validation max_length cannot be negative")
        
        if (validation.min_length is not None and 
            validation.max_length is not None and 
            validation.min_length > validation.max_length):
            errors.append(f"{context} validation min_length cannot be greater than max_length")
        
        if validation.pattern:
            try:
                re.compile(validation.pattern)
            except re.error as e:
                errors.append(f"{context} has invalid regex pattern: {e}")
        
        return errors
    
    def _validate_confidence_config(self, confidence: ConfidenceConfig, context: str) -> List[str]:
        """Validate confidence configuration."""
        errors: List[str] = []
        
        if confidence.threshold is not None:
            if confidence.threshold < 0.0 or confidence.threshold > 1.0:
                errors.append(f"{context} confidence threshold must be between 0.0 and 1.0")
        
        if confidence.weight is not None:
            if confidence.weight <= 0:
                errors.append(f"{context} confidence weight must be positive")
            elif confidence.weight > 10.0:
                warnings.append(f"{context} confidence weight is very high")
        
        # Validate boost factors
        for key, value in confidence.boost_factors.items():
            if not isinstance(key, str):
                errors.append(f"{context} boost factor key must be string: {key}")
            if not isinstance(value, (int, float)):
                errors.append(f"{context} boost factor value must be number: {value}")
            elif value < 0:
                errors.append(f"{context} boost factor cannot be negative: {value}")
        
        return errors
    
    def _validate_selector_yaml_structure(self, selector_data: Dict, selector_name: str) -> List[str]:
        """Validate selector YAML structure."""
        errors: List[str] = []
        
        if not isinstance(selector_data, dict):
            errors.append(f"Selector '{selector_name}' must be a dictionary")
            return errors
        
        required_fields = ['description', 'context', 'strategies']
        for field in required_fields:
            if field not in selector_data:
                errors.append(f"Selector '{selector_name}' missing required field: {field}")
        
        # Validate strategies array
        if 'strategies' in selector_data:
            if not isinstance(selector_data['strategies'], list):
                errors.append(f"Selector '{selector_name}' strategies must be an array")
            elif len(selector_data['strategies']) == 0:
                errors.append(f"Selector '{selector_name}' must have at least one strategy")
        
        return errors
    
    def _validate_strategy_template_yaml_structure(self, template_data: Dict, template_name: str) -> List[str]:
        """Validate strategy template YAML structure."""
        errors: List[str] = []
        
        if not isinstance(template_data, dict):
            errors.append(f"Strategy template '{template_name}' must be a dictionary")
            return errors
        
        if 'type' not in template_data:
            errors.append(f"Strategy template '{template_name}' missing required field: type")
        
        return errors
    
    def _validate_context_defaults_yaml_structure(self, context_data: Dict) -> List[str]:
        """Validate context defaults YAML structure."""
        errors: List[str] = []
        
        if not isinstance(context_data, dict):
            errors.append("Context defaults must be a dictionary")
            return errors
        
        if 'page_type' not in context_data:
            errors.append("Context defaults missing required field: page_type")
        
        return errors
    
    def _validate_validation_defaults_yaml_structure(self, validation_data: Dict) -> List[str]:
        """Validate validation defaults YAML structure."""
        errors: List[str] = []
        
        if not isinstance(validation_data, dict):
            errors.append("Validation defaults must be a dictionary")
            return errors
        
        # No required fields for validation defaults
        
        return errors
