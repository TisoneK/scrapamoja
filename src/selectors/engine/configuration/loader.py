"""
Configuration loader for YAML-based selector definitions.

This module provides interfaces and implementations for loading,
validating, and managing YAML selector configuration files.
"""

import asyncio
import yaml
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Set
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
    ValidationResult,
    ConfigurationState
)
from ...models.strategy_template import StrategyTemplate


class ConfigurationException(Exception):
    """Base exception for configuration system errors."""
    
    def __init__(self, message: str, file_path: str, correlation_id: str):
        self.message = message
        self.file_path = file_path
        self.correlation_id = correlation_id
        super().__init__(message)


class SchemaValidationException(ConfigurationException):
    """Exception raised when YAML schema validation fails."""
    
    def __init__(self, message: str, file_path: str, validation_errors: List[str], correlation_id: str):
        self.validation_errors = validation_errors
        super().__init__(message, file_path, correlation_id)


class ConfigurationLoaderException(ConfigurationException):
    """Exception raised when configuration loading fails."""
    pass


class IConfigurationLoader(ABC):
    """Interface for loading YAML selector configurations."""
    
    @abstractmethod
    async def load_configuration(self, file_path: Path) -> SelectorConfiguration:
        """Load and validate a single YAML configuration file."""
        pass
    
    @abstractmethod
    async def load_configurations_recursive(self, root_path: Path) -> Dict[str, SelectorConfiguration]:
        """Load all YAML configurations from directory tree."""
        pass
    
    @abstractmethod
    def validate_configuration(self, config: SelectorConfiguration) -> ValidationResult:
        """Validate a configuration against schema."""
        pass
    
    @abstractmethod
    async def reload_configuration(self, file_path: Path) -> Optional[SelectorConfiguration]:
        """Reload a configuration file if it has changed."""
        pass


class ConfigurationLoader(IConfigurationLoader):
    """Implementation for loading YAML selector configurations."""
    
    def __init__(self):
        """Initialize the configuration loader."""
        self._loaded_files: Dict[str, datetime] = {}
        self._correlation_counter = 0
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for tracking operations."""
        self._correlation_counter += 1
        return f"config_load_{self._correlation_counter}_{datetime.now().isoformat()}"
    
    async def load_configuration(self, file_path: Path) -> SelectorConfiguration:
        """Load and validate a single YAML configuration file."""
        correlation_id = self._generate_correlation_id()
        
        try:
            if not file_path.exists():
                raise ConfigurationLoaderException(
                    f"Configuration file not found: {file_path}",
                    str(file_path),
                    correlation_id
                )
            
            # Read and parse YAML file
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            if not yaml_data:
                raise ConfigurationLoaderException(
                    f"Empty configuration file: {file_path}",
                    str(file_path),
                    correlation_id
                )
            
            # Parse configuration components
            config = self._parse_yaml_configuration(yaml_data, str(file_path), correlation_id)
            
            # Validate configuration
            validation_result = self.validate_configuration(config)
            if not validation_result.is_valid:
                raise SchemaValidationException(
                    f"Configuration validation failed: {validation_result.errors}",
                    str(file_path),
                    validation_result.errors,
                    correlation_id
                )
            
            # Track loaded file
            self._loaded_files[str(file_path)] = datetime.now()
            
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationLoaderException(
                f"YAML parsing error in {file_path}: {str(e)}",
                str(file_path),
                correlation_id
            )
        except Exception as e:
            if isinstance(e, ConfigurationException):
                raise
            raise ConfigurationLoaderException(
                f"Unexpected error loading {file_path}: {str(e)}",
                str(file_path),
                correlation_id
            )
    
    async def load_configurations_recursive(self, root_path: Path) -> Dict[str, SelectorConfiguration]:
        """Load all YAML configurations from directory tree."""
        correlation_id = self._generate_correlation_id()
        configurations: Dict[str, SelectorConfiguration] = {}
        
        if not root_path.exists():
            raise ConfigurationLoaderException(
                f"Configuration root directory not found: {root_path}",
                str(root_path),
                correlation_id
            )
        
        # Find all YAML files recursively
        yaml_files = list(root_path.rglob("*.yaml"))
        
        # Load configurations in parallel
        load_tasks = []
        for yaml_file in yaml_files:
            # Skip context files (they start with underscore)
            if yaml_file.name.startswith('_'):
                continue
            load_tasks.append(self.load_configuration(yaml_file))
        
        if load_tasks:
            results = await asyncio.gather(*load_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Log error but continue loading other files
                    print(f"Error loading {yaml_files[i]}: {result}")
                else:
                    configurations[str(yaml_files[i])] = result
        
        return configurations
    
    def validate_configuration(self, config: SelectorConfiguration) -> ValidationResult:
        """Validate a configuration against schema."""
        errors: List[str] = []
        warnings: List[str] = []
        start_time = datetime.now()
        
        try:
            # Validate metadata
            if not config.metadata:
                errors.append("Configuration metadata is required")
            else:
                # Validate metadata fields
                if not config.metadata.version:
                    errors.append("Metadata version is required")
                if not config.metadata.description:
                    errors.append("Metadata description is required")
            
            # Validate selectors
            for selector_name, selector in config.selectors.items():
                selector_errors = self._validate_selector(selector, selector_name)
                errors.extend(selector_errors)
            
            # Validate strategy templates
            for template_name, template in config.strategy_templates.items():
                template_errors = self._validate_strategy_template(template, template_name)
                errors.extend(template_errors)
            
            # Validate context defaults if present
            if config.context_defaults:
                context_errors = self._validate_context_defaults(config.context_defaults)
                errors.extend(context_errors)
            
            # Validate validation defaults if present
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
                errors=[f"Validation error: {str(e)}"],
                warnings=warnings,
                schema_version="unknown",
                validation_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    async def reload_configuration(self, file_path: Path) -> Optional[SelectorConfiguration]:
        """Reload a configuration file if it has changed."""
        if not file_path.exists():
            return None
        
        file_path_str = str(file_path)
        current_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        
        # Check if file has been modified since last load
        if file_path_str in self._loaded_files:
            if self._loaded_files[file_path_str] >= current_mtime:
                return None  # File hasn't changed
        
        # Reload the configuration
        return await self.load_configuration(file_path)
    
    def _parse_yaml_configuration(self, yaml_data: Dict, file_path: str, correlation_id: str) -> SelectorConfiguration:
        """Parse YAML data into configuration objects."""
        # Parse metadata
        metadata = self._parse_metadata(yaml_data.get('metadata', {}), file_path, correlation_id)
        
        # Parse context defaults
        context_defaults = None
        if 'context_defaults' in yaml_data:
            context_defaults = self._parse_context_defaults(yaml_data['context_defaults'], file_path, correlation_id)
        
        # Parse validation defaults
        validation_defaults = None
        if 'validation_defaults' in yaml_data:
            validation_defaults = self._parse_validation_defaults(yaml_data['validation_defaults'], file_path, correlation_id)
        
        # Parse strategy templates
        strategy_templates = {}
        if 'strategy_templates' in yaml_data:
            for name, template_data in yaml_data['strategy_templates'].items():
                strategy_templates[name] = self._parse_strategy_template(template_data, name, file_path, correlation_id)
        
        # Parse selectors
        selectors = {}
        if 'selectors' in yaml_data:
            for name, selector_data in yaml_data['selectors'].items():
                selectors[name] = self._parse_selector(selector_data, name, file_path, correlation_id)
        
        return SelectorConfiguration(
            file_path=file_path,
            metadata=metadata,
            selectors=selectors,
            context_defaults=context_defaults,
            validation_defaults=validation_defaults,
            strategy_templates=strategy_templates
        )
    
    def _parse_metadata(self, metadata_data: Dict, file_path: str, correlation_id: str) -> ConfigurationMetadata:
        """Parse configuration metadata."""
        return ConfigurationMetadata(
            version=metadata_data.get('version', '1.0'),
            last_updated=metadata_data.get('last_updated', datetime.now().isoformat()),
            description=metadata_data.get('description', '')
        )
    
    def _parse_context_defaults(self, context_data: Dict, file_path: str, correlation_id: str) -> ContextDefaults:
        """Parse context defaults."""
        return ContextDefaults(
            page_type=context_data['page_type'],
            wait_strategy=context_data.get('wait_strategy', 'network_idle'),
            timeout=context_data.get('timeout', 10000),
            section=context_data.get('section')
        )
    
    def _parse_validation_defaults(self, validation_data: Dict, file_path: str, correlation_id: str) -> ValidationDefaults:
        """Parse validation defaults."""
        return ValidationDefaults(
            required=validation_data.get('required', False),
            type=validation_data.get('type', 'string'),
            min_length=validation_data.get('min_length'),
            max_length=validation_data.get('max_length'),
            pattern=validation_data.get('pattern')
        )
    
    def _parse_strategy_template(self, template_data: Dict, name: str, file_path: str, correlation_id: str) -> StrategyTemplate:
        """Parse strategy template."""
        # Parse validation if present
        validation = None
        if 'validation' in template_data:
            validation = self._parse_validation_rule(template_data['validation'], file_path, correlation_id)
        
        # Parse confidence if present
        confidence = None
        if 'confidence' in template_data:
            confidence = self._parse_confidence_config(template_data['confidence'], file_path, correlation_id)
        
        return StrategyTemplate(
            type=template_data['type'],
            parameters=template_data.get('parameters', {}),
            validation=validation,
            confidence=confidence
        )
    
    def _parse_selector(self, selector_data: Dict, name: str, file_path: str, correlation_id: str) -> SemanticSelector:
        """Parse semantic selector."""
        # Parse strategies
        strategies = []
        for strategy_data in selector_data['strategies']:
            strategies.append(self._parse_strategy_definition(strategy_data, file_path, correlation_id))
        
        # Parse validation if present
        validation = None
        if 'validation' in selector_data:
            validation = self._parse_validation_rule(selector_data['validation'], file_path, correlation_id)
        
        # Parse confidence if present
        confidence = None
        if 'confidence' in selector_data:
            confidence = self._parse_confidence_config(selector_data['confidence'], file_path, correlation_id)
        
        return SemanticSelector(
            name=name,
            description=selector_data['description'],
            context=selector_data['context'],
            strategies=strategies,
            validation=validation,
            confidence=confidence
        )
    
    def _parse_strategy_definition(self, strategy_data: Dict, file_path: str, correlation_id: str) -> StrategyDefinition:
        """Parse strategy definition."""
        return StrategyDefinition(
            type=strategy_data['type'],
            template=strategy_data.get('template'),
            parameters=strategy_data.get('parameters', {}),
            priority=strategy_data.get('priority', 1)
        )
    
    def _parse_validation_rule(self, validation_data: Dict, file_path: str, correlation_id: str) -> ValidationRule:
        """Parse validation rule."""
        return ValidationRule(
            required=validation_data.get('required'),
            type=validation_data.get('type'),
            min_length=validation_data.get('min_length'),
            max_length=validation_data.get('max_length'),
            pattern=validation_data.get('pattern'),
            custom_rules=validation_data.get('custom_rules', {})
        )
    
    def _parse_confidence_config(self, confidence_data: Dict, file_path: str, correlation_id: str) -> ConfidenceConfig:
        """Parse confidence configuration."""
        return ConfidenceConfig(
            threshold=confidence_data.get('threshold'),
            weight=confidence_data.get('weight'),
            boost_factors=confidence_data.get('boost_factors', {})
        )
    
    def _validate_selector(self, selector: SemanticSelector, selector_name: str) -> List[str]:
        """Validate a semantic selector."""
        errors: List[str] = []
        
        if not selector.name:
            errors.append(f"Selector '{selector_name}' has no name")
        
        if not selector.description:
            errors.append(f"Selector '{selector_name}' has no description")
        
        if not selector.context:
            errors.append(f"Selector '{selector_name}' has no context")
        
        if not selector.strategies:
            errors.append(f"Selector '{selector_name}' has no strategies")
        
        # Validate strategies
        for i, strategy in enumerate(selector.strategies):
            if not strategy.type:
                errors.append(f"Selector '{selector_name}' strategy {i} has no type")
        
        return errors
    
    def _validate_strategy_template(self, template: StrategyTemplate, template_name: str) -> List[str]:
        """Validate a strategy template."""
        errors: List[str] = []
        
        if not template.type:
            errors.append(f"Template '{template_name}' has no type")
        
        return errors
    
    def _validate_context_defaults(self, context_defaults: ContextDefaults) -> List[str]:
        """Validate context defaults."""
        errors: List[str] = []
        
        if not context_defaults.page_type:
            errors.append("Context defaults missing page_type")
        
        if context_defaults.timeout <= 0:
            errors.append("Context defaults timeout must be positive")
        
        return errors
    
    def _validate_validation_defaults(self, validation_defaults: ValidationDefaults) -> List[str]:
        """Validate validation defaults."""
        errors: List[str] = []
        
        valid_types = ["string", "number", "boolean", "array", "object"]
        if validation_defaults.type not in valid_types:
            errors.append(f"Invalid validation type: {validation_defaults.type}")
        
        return errors
