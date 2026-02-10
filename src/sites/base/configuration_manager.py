"""
Configuration manager for the modular site scraper template system.

This module provides multi-environment configuration management with validation,
hot-reloading, and feature flag support.
"""

from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import asyncio
import yaml
import json
import os
from enum import Enum

from .component_interface import ComponentContext


class Environment(Enum):
    """Environment enumeration."""
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"
    TEST = "test"


@dataclass
class ConfigurationSchema:
    """Schema definition for configuration validation."""
    schema_version: str
    fields: Dict[str, Any]
    required_fields: List[str]
    optional_fields: List[str]
    
    def __post_init__(self):
        if self.fields is None:
            self.fields = {}
        if self.required_fields is None:
            self.required_fields = []
        if self.optional_fields is None:
            self.optional_fields = []


@dataclass
class ConfigurationValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validation_time_ms: float
    schema_version: str
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class FeatureFlag:
    """Feature flag definition."""
    name: str
    enabled: bool
    description: str
    rollout_percentage: float = 100.0
    environments: List[str] = field(default_factory=lambda: [env.value for env in Environment])
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.environments is None:
            self.environments = []


@dataclass
class HotReloadEvent:
    """Event for configuration hot-reloading."""
    config_path: str
    old_config: Dict[str, Any]
    new_config: Dict[str, Any]
    timestamp: datetime
    changes: List[str]
    
    def __post_init__(self):
        if self.changes is None:
            self.changes = []
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ConfigurationManager:
    """Manages multi-environment configuration with validation and hot-reloading."""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self._configurations: Dict[str, Dict[str, Any]] = {}
        self._environment_overrides: Dict[str, Dict[str, Any]] = {}
        self._feature_flags: Dict[str, FeatureFlag] = {}
        self._schemas: Dict[str, ConfigurationSchema] = {}
        self._hot_reload_enabled = True
        self._watch_task: Optional[asyncio.Task] = None
        self._validation_cache: Dict[str, ConfigurationValidationResult] = {}
        self._reload_callbacks: List[Callable[[HotReloadEvent], None]] = []
        self._current_environment: Environment = Environment.DEV
        
    async def initialize(
        self,
        environment: Environment = Environment.DEV,
        hot_reload: bool = True
    ) -> bool:
        """
        Initialize the configuration manager.
        
        Args:
            environment: Target environment
            hot_reload: Enable hot-reloading
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self._current_environment = environment
            self._hot_reload_enabled = hot_reload
            
            # Load base configurations
            await self._load_base_configurations()
            
            # Load environment overrides
            await self._load_environment_overrides(environment)
            
            # Load feature flags
            await self._load_feature_flags()
            
            # Load schemas
            await self._load_schemas()
            
            # Start hot-reloading if enabled
            if hot_reload:
                await self._start_hot_reload()
            
            print(f"ConfigurationManager initialized for environment: {environment.value}")
            return True
            
        except Exception as e:
            print(f"Failed to initialize ConfigurationManager: {str(e)}")
            return False
    
    async def get_config(self, environment: Optional[Environment] = None) -> Dict[str, Any]:
        """
        Get configuration for a specific environment.
        
        Args:
            environment: Target environment (uses current if None)
            
        Returns:
            Merged configuration dictionary
        """
        if environment is None:
            environment = self._current_environment
        
        env_name = environment.value
        
        # Start with base configuration
        config = {}
        if "base" in self._configurations:
            config = self._configurations["base"].copy()
        
        # Apply environment overrides
        if env_name in self._environment_overrides:
            config = self._merge_configs(config, self._environment_overrides[env_name])
        
        # Add feature flags
        config["feature_flags"] = self._get_feature_flags_for_environment(environment)
        
        # Add metadata
        config["_metadata"] = {
            "environment": env_name,
            "schema_version": "1.0.0",
            "loaded_at": datetime.utcnow().isoformat()
        }
        
        return config
    
    async def validate_config(
        self,
        config: Dict[str, Any],
        schema_name: str = "default"
    ) -> ConfigurationValidationResult:
        """
        Validate configuration against schema.
        
        Args:
            config: Configuration to validate
            schema_name: Schema name to use for validation
            
        Returns:
            Validation result
        """
        try:
            start_time = datetime.utcnow()
            errors = []
            warnings = []
            
            # Get schema
            schema = self._schemas.get(schema_name)
            if not schema:
                errors.append(f"Schema {schema_name} not found")
                return ConfigurationValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings,
                    validation_time_ms=0.0,
                    schema_version="unknown"
                )
            
            # Validate required fields
            for field in schema.required_fields:
                if field not in config:
                    errors.append(f"Required field '{field}' is missing")
            
            # Validate field types and values
            for field_name, field_schema in schema.fields.items():
                if field_name in config:
                    field_errors = await self._validate_field(
                        config[field_name],
                        field_name,
                        field_schema
                    )
                    errors.extend(field_errors)
            
            end_time = datetime.utcnow()
            validation_time = (end_time - start_time).total_seconds() * 1000
            
            result = ConfigurationValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                validation_time_ms=validation_time,
                schema_version=schema.schema_version
            )
            
            # Cache validation result
            cache_key = f"{schema_name}_{hash(json.dumps(config, sort_keys=True))}"
            self._validation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            return ConfigurationValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                validation_time_ms=0.0,
                schema_version="unknown"
            )
    
    async def get_feature_flag(self, flag_name: str, environment: Optional[Environment] = None) -> bool:
        """
        Get feature flag value.
        
        Args:
            flag_name: Feature flag name
            environment: Target environment
            
        Returns:
            Feature flag value
        """
        if environment is None:
            environment = self._current_environment
        
        flag = self._feature_flags.get(flag_name)
        if not flag:
            return False
        
        # Check if flag is enabled for environment
        if environment.value not in flag.environments:
            return False
        
        # Check rollout percentage (simplified)
        if flag.rollout_percentage < 100.0:
            # In a real implementation, this would use user ID or other criteria
            import random
            if random.random() * 100 > flag.rollout_percentage:
                return False
        
        return flag.enabled
    
    async def set_feature_flag(
        self,
        flag_name: str,
        enabled: bool,
        description: str = "",
        rollout_percentage: float = 100.0,
        environments: Optional[List[str]] = None
    ) -> bool:
        """
        Set a feature flag.
        
        Args:
            flag_name: Feature flag name
            enabled: Flag value
            description: Flag description
            rollout_percentage: Rollout percentage
            environments: Environments where flag applies
            
        Returns:
            True if successful, False otherwise
        """
        try:
            flag = FeatureFlag(
                name=flag_name,
                enabled=enabled,
                description=description,
                rollout_percentage=rollout_percentage,
                environments=environments or [env.value for env in Environment]
            )
            
            self._feature_flags[flag_name] = flag
            
            # Save feature flags
            await self._save_feature_flags()
            
            print(f"Set feature flag {flag_name} to {enabled}")
            return True
            
        except Exception as e:
            print(f"Failed to set feature flag {flag_name}: {str(e)}")
            return False
    
    async def reload_config(self, config_path: str) -> bool:
        """
        Reload configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                print(f"Configuration file not found: {config_path}")
                return False
            
            # Load new configuration
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.suffix.lower() == '.yaml':
                    new_config = yaml.safe_load(f)
                elif config_file.suffix.lower() == '.json':
                    new_config = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_file.suffix}")
            
            # Determine config type and update
            config_name = config_file.stem
            old_config = self._configurations.get(config_name, {})
            
            if config_name == "base":
                self._configurations[config_name] = new_config
            else:
                self._environment_overrides[config_name] = new_config
            
            # Create hot-reload event
            changes = self._detect_config_changes(old_config, new_config)
            event = HotReloadEvent(
                config_path=str(config_file),
                old_config=old_config,
                new_config=new_config,
                timestamp=datetime.utcnow(),
                changes=changes
            )
            
            # Notify callbacks
            for callback in self._reload_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in reload callback: {str(e)}")
            
            print(f"Reloaded configuration from {config_path}")
            return True
            
        except Exception as e:
            print(f"Failed to reload configuration {config_path}: {str(e)}")
            return False
    
    def add_reload_callback(self, callback: Callable[[HotReloadEvent], None]):
        """
        Add a callback for configuration reload events.
        
        Args:
            callback: Callback function
        """
        self._reload_callbacks.append(callback)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get configuration manager statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "configurations_loaded": len(self._configurations),
            "environment_overrides": len(self._environment_overrides),
            "feature_flags": len(self._feature_flags),
            "schemas_loaded": len(self._schemas),
            "validation_cache_size": len(self._validation_cache),
            "hot_reload_enabled": self._hot_reload_enabled,
            "current_environment": self._current_environment.value,
            "config_directory": str(self.config_dir)
        }
    
    async def cleanup(self) -> None:
        """Clean up configuration manager resources."""
        try:
            # Stop hot-reloading
            if self._watch_task:
                self._watch_task.cancel()
                try:
                    await self._watch_task
                except asyncio.CancelledError:
                    pass
            
            # Clear caches
            self._validation_cache.clear()
            self._reload_callbacks.clear()
            
            print("ConfigurationManager cleanup completed")
            
        except Exception as e:
            print(f"Error during ConfigurationManager cleanup: {str(e)}")
    
    async def _load_base_configurations(self) -> None:
        """Load base configuration files."""
        base_config_file = self.config_dir / "base.yaml"
        if base_config_file.exists():
            with open(base_config_file, 'r', encoding='utf-8') as f:
                self._configurations["base"] = yaml.safe_load(f)
    
    async def _load_environment_overrides(self, environment: Environment) -> None:
        """Load environment-specific configuration overrides."""
        env_config_file = self.config_dir / f"{environment.value}.yaml"
        if env_config_file.exists():
            with open(env_config_file, 'r', encoding='utf-8') as f:
                self._environment_overrides[environment.value] = yaml.safe_load(f)
    
    async def _load_feature_flags(self) -> None:
        """Load feature flags configuration."""
        flags_file = self.config_dir / "feature_flags.yaml"
        if flags_file.exists():
            with open(flags_file, 'r', encoding='utf-8') as f:
                flags_data = yaml.safe_load(f)
                
                for flag_name, flag_data in flags_data.items():
                    self._feature_flags[flag_name] = FeatureFlag(
                        name=flag_name,
                        enabled=flag_data.get("enabled", False),
                        description=flag_data.get("description", ""),
                        rollout_percentage=flag_data.get("rollout_percentage", 100.0),
                        environments=flag_data.get("environments", [env.value for env in Environment])
                    )
    
    async def _load_schemas(self) -> None:
        """Load configuration schemas."""
        # Create default schema
        self._schemas["default"] = ConfigurationSchema(
            schema_version="1.0.0",
            fields={
                "site_id": {"type": "string", "required": True},
                "site_name": {"type": "string", "required": True},
                "base_url": {"type": "string", "required": True},
                "version": {"type": "string", "required": True}
            },
            required_fields=["site_id", "site_name", "base_url", "version"],
            optional_fields=[]
        )
    
    async def _start_hot_reload(self) -> None:
        """Start hot-reloading task."""
        self._watch_task = asyncio.create_task(self._watch_config_files())
    
    async def _watch_config_files(self) -> None:
        """Watch configuration files for changes."""
        while self._hot_reload_enabled:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Check for file modifications
                for config_file in self.config_dir.glob("*.yaml"):
                    if config_file.exists():
                        mtime = config_file.stat().st_mtime
                        # In a real implementation, we'd track modification times
                        # For now, we'll just check if files exist
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error watching config files: {str(e)}")
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge base configuration with overrides."""
        result = base.copy()
        
        for key, value in override.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _get_feature_flags_for_environment(self, environment: Environment) -> Dict[str, bool]:
        """Get feature flags for a specific environment."""
        flags = {}
        
        for flag_name, flag in self._feature_flags.items():
            if environment.value in flag.environments:
                # Check if flag is enabled for environment
                if flag.rollout_percentage < 100.0:
                    # In a real implementation, this would use user ID or other criteria
                    import random
                    if random.random() * 100 > flag.rollout_percentage:
                        flags[flag_name] = False
                    else:
                        flags[flag_name] = flag.enabled
                else:
                    flags[flag_name] = flag.enabled
        
        return flags
    
    async def _validate_field(
        self,
        value: Any,
        field_name: str,
        field_schema: Dict[str, Any]
    ) -> List[str]:
        """Validate a single field against its schema."""
        errors = []
        
        field_type = field_schema.get("type")
        if field_type == "string" and not isinstance(value, str):
            errors.append(f"Field '{field_name}' must be a string")
        elif field_type == "number" and not isinstance(value, (int, float)):
            errors.append(f"Field '{field_name}' must be a number")
        elif field_type == "boolean" and not isinstance(value, bool):
            errors.append(f"Field '{field_name}' must be a boolean")
        elif field_type == "array" and not isinstance(value, list):
            errors.append(f"Field '{field_name}' must be an array")
        elif field_type == "object" and not isinstance(value, dict):
            errors.append(f"Field '{field_name}' must be an object")
        
        # Check min/max constraints
        if "min_value" in field_schema and isinstance(value, (int, float)):
            if value < field_schema["min_value"]:
                errors.append(f"Field '{field_name}' must be at least {field_schema['min_value']}")
        
        if "max_value" in field_schema and isinstance(value, (int, float)):
            if value > field_schema["max_value"]:
                errors.append(f"Field '{field_name}' must be at most {field_schema['max_value']}")
        
        return errors
    
    def _detect_config_changes(
        self,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any]
    ) -> List[str]:
        """Detect changes between old and new configuration."""
        changes = []
        
        # Check for added/modified keys
        for key in new_config:
            if key not in old_config:
                changes.append(f"Added field: {key}")
            elif old_config[key] != new_config[key]:
                changes.append(f"Modified field: {key}")
        
        # Check for removed keys
        for key in old_config:
            if key not in new_config:
                changes.append(f"Removed field: {key}")
        
        return changes
    
    async def _save_feature_flags(self) -> None:
        """Save feature flags to file."""
        flags_file = self.config_dir / "feature_flags.yaml"
        
        flags_data = {}
        for flag_name, flag in self._feature_flags.items():
            flags_data[flag_name] = {
                "enabled": flag.enabled,
                "description": flag.description,
                "rollout_percentage": flag.rollout_percentage,
                "environments": flag.environments
            }
        
        with open(flags_file, 'w', encoding='utf-8') as f:
            yaml.dump(flags_data, f, default_flow_style=False)


class ConfigurationError(Exception):
    """Exception raised when configuration operations fail."""
    pass


class ValidationError(ConfigurationError):
    """Exception raised when configuration validation fails."""
    pass


class HotReloadError(ConfigurationError):
    """Exception raised when hot-reloading fails."""
    pass
