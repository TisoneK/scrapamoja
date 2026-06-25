"""
Configuration loader with environment support for the scraper framework.

This module provides comprehensive configuration loading capabilities, including
environment-specific configuration loading, file-based configuration, and runtime
configuration management.
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List, Union, Type
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

from .environment_detector import detect_environment, Environment
from .config_schemas import ConfigSchema, get_schema, validate_config_by_schema
from .config_cache import ConfigCache


@dataclass
class ConfigLoadResult:
    """Result of configuration loading operation."""
    success: bool
    config: Dict[str, Any] = field(default_factory=dict)
    environment: str = ""
    source: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    load_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ConfigLoader:
    """Configuration loader with environment support."""
    
    def __init__(self, cache: Optional[ConfigCache] = None):
        """Initialize configuration loader."""
        self.cache = cache or ConfigCache()
        self._load_history: List[ConfigLoadResult] = []
        self._config_sources: List[str] = []
        self._default_config: Dict[str, Any] = {}
        self._environment_overrides: Dict[str, Dict[str, Any]] = {}
        
        # Configuration file patterns
        self._config_file_patterns = [
            'config.{env}.json',
            'config.{env}.yaml',
            'config.{env}.yml',
            'settings.{env}.json',
            'settings.{env}.yaml',
            'settings.{env}.yml',
            '.env.{env}',
            'config.json',
            'config.yaml',
            'config.yml',
            'settings.json',
            'settings.yaml',
            'settings.yml'
        ]
    
    def set_default_config(self, config: Dict[str, Any]) -> None:
        """Set default configuration."""
        self._default_config = config.copy()
    
    def set_environment_override(self, environment: str, config: Dict[str, Any]) -> None:
        """Set environment-specific configuration override."""
        self._environment_overrides[environment] = config.copy()
    
    def load_config(self, environment: Optional[str] = None, 
                    config_path: Optional[Union[str, Path]] = None,
                    schema_name: Optional[str] = None,
                    use_cache: bool = True) -> ConfigLoadResult:
        """
        Load configuration for a specific environment.
        
        Args:
            environment: Target environment (auto-detected if None)
            config_path: Specific config file path
            schema_name: Schema name for validation
            use_cache: Whether to use cached configuration
            
        Returns:
            Configuration load result
        """
        start_time = datetime.utcnow()
        
        try:
            # Detect environment if not provided
            if environment is None:
                detected_env = detect_environment()
                environment = detected_env.value
            else:
                # Validate environment
                try:
                    Environment(environment.lower())
                except ValueError:
                    return ConfigLoadResult(
                        success=False,
                        errors=[f"Invalid environment: {environment}"],
                        environment=environment
                    )
            
            # Check cache first
            if use_cache:
                cached_config = self.cache.get(environment)
                if cached_config:
                    return ConfigLoadResult(
                        success=True,
                        config=cached_config,
                        environment=environment,
                        source="cache",
                        load_time_ms=0
                    )
            
            # Load configuration
            config = self._load_configuration_from_sources(environment, config_path)
            
            # Validate against schema if provided
            if schema_name:
                validation_result = validate_config_by_schema(config, schema_name, environment)
                if not validation_result['valid']:
                    return ConfigLoadResult(
                        success=False,
                        config=config,
                        environment=environment,
                        errors=validation_result['errors'],
                        warnings=validation_result['warnings']
                    )
            
            # Cache the configuration
            if use_cache:
                self.cache.set(environment, config)
            
            # Calculate load time
            end_time = datetime.utcnow()
            load_time_ms = (end_time - start_time).total_seconds() * 1000
            
            result = ConfigLoadResult(
                success=True,
                config=config,
                environment=environment,
                source=self._get_last_source(),
                load_time_ms=load_time_ms
            )
            
            # Record load history
            self._load_history.append(result)
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            load_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return ConfigLoadResult(
                success=False,
                errors=[f"Configuration loading failed: {str(e)}"],
                environment=environment or "unknown",
                load_time_ms=load_time_ms
            )
    
    def _load_configuration_from_sources(self, environment: str, 
                                         config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """Load configuration from various sources."""
        config = {}
        sources = []
        
        # Start with default configuration
        if self._default_config:
            config.update(self._default_config)
            sources.append("default")
        
        # Load from specific file if provided
        if config_path:
            file_config = self._load_from_file(Path(config_path))
            if file_config:
                config.update(file_config)
                sources.append(f"file:{config_path}")
        else:
            # Load from environment-specific files
            env_config = self._load_from_environment_files(environment)
            if env_config:
                config.update(env_config)
                sources.append(f"env_files:{environment}")
            
            # Load from generic config files
            generic_config = self._load_from_generic_files()
            if generic_config:
                config.update(generic_config)
                sources.append("generic_files")
        
        # Apply environment overrides
        if environment in self._environment_overrides:
            config.update(self._environment_overrides[environment])
            sources.append(f"override:{environment}")
        
        # Add environment information
        config['environment'] = environment
        config['config_sources'] = sources
        
        self._config_sources = sources
        return config
    
    def _load_from_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load configuration from a specific file."""
        try:
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() == '.json':
                    return json.load(f)
                elif file_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                else:
                    # Try to parse as JSON first, then YAML
                    content = f.read()
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        try:
                            return yaml.safe_load(content) or {}
                        except yaml.YAMLError:
                            return None
            
        except Exception as e:
            print(f"Error loading config from {file_path}: {str(e)}")
            return None
    
    def _load_from_environment_files(self, environment: str) -> Optional[Dict[str, Any]]:
        """Load configuration from environment-specific files."""
        current_dir = Path.cwd()
        config = {}
        
        # Try environment-specific patterns
        env_patterns = [
            f'config.{environment}.json',
            f'config.{environment}.yaml',
            f'config.{environment}.yml',
            f'settings.{environment}.json',
            f'settings.{environment}.yaml',
            f'settings.{environment}.yml',
            f'.env.{environment}',
            f'.env.{environment[:3]}'  # .env.dev, .env.prod, etc.
        ]
        
        for pattern in env_patterns:
            config_path = current_dir / pattern
            file_config = self._load_from_file(config_path)
            if file_config:
                config.update(file_config)
                break  # Stop at first found
        
        return config if config else None
    
    def _load_from_generic_files(self) -> Optional[Dict[str, Any]]:
        """Load configuration from generic config files."""
        current_dir = Path.cwd()
        config = {}
        
        # Try generic patterns
        generic_patterns = [
            'config.json',
            'config.yaml',
            'config.yml',
            'settings.json',
            'settings.yaml',
            'settings.yml'
        ]
        
        for pattern in generic_patterns:
            config_path = current_dir / pattern
            file_config = self._load_from_file(config_path)
            if file_config:
                config.update(file_config)
                break  # Stop at first found
        
        return config if config else None
    
    def _get_last_source(self) -> str:
        """Get the last configuration source."""
        return " -> ".join(self._config_sources) if self._config_sources else "unknown"
    
    def reload_config(self, environment: Optional[str] = None, 
                     config_path: Optional[Union[str, Path]] = None,
                     schema_name: Optional[str] = None) -> ConfigLoadResult:
        """Reload configuration, bypassing cache."""
        return self.load_config(
            environment=environment,
            config_path=config_path,
            schema_name=schema_name,
            use_cache=False
        )
    
    def load_config_from_dict(self, config_dict: Dict[str, Any], 
                              environment: Optional[str] = None,
                              schema_name: Optional[str] = None) -> ConfigLoadResult:
        """Load configuration from a dictionary."""
        start_time = datetime.utcnow()
        
        try:
            # Detect environment if not provided
            if environment is None:
                detected_env = detect_environment()
                environment = detected_env.value
            
            # Start with default configuration
            config = self._default_config.copy()
            
            # Add provided configuration
            config.update(config_dict)
            
            # Add environment information
            config['environment'] = environment
            config['config_sources'] = ['dict']
            
            # Validate against schema if provided
            if schema_name:
                validation_result = validate_config_by_schema(config, schema_name, environment)
                if not validation_result['valid']:
                    return ConfigLoadResult(
                        success=False,
                        config=config,
                        environment=environment,
                        errors=validation_result['errors'],
                        warnings=validation_result['warnings'],
                        source="dict"
                    )
            
            # Calculate load time
            end_time = datetime.utcnow()
            load_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return ConfigLoadResult(
                success=True,
                config=config,
                environment=environment,
                source="dict",
                load_time_ms=load_time_ms
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            load_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return ConfigLoadResult(
                success=False,
                errors=[f"Dictionary config loading failed: {str(e)}"],
                environment=environment or "unknown",
                source="dict",
                load_time_ms=load_time_ms
            )
    
    def get_config_value(self, key: str, default: Any = None, 
                         environment: Optional[str] = None) -> Any:
        """Get a specific configuration value."""
        if environment is None:
            environment = detect_environment().value
        
        # Try cache first
        cached_config = self.cache.get(environment)
        if cached_config:
            return cached_config.get(key, default)
        
        # Load configuration
        result = self.load_config(environment)
        if result.success:
            return result.config.get(key, default)
        
        return default
    
    def set_config_value(self, key: str, value: Any, 
                         environment: Optional[str] = None,
                         persist: bool = False) -> bool:
        """Set a configuration value."""
        try:
            if environment is None:
                environment = detect_environment().value
            
            # Get current configuration
            cached_config = self.cache.get(environment)
            if not cached_config:
                result = self.load_config(environment)
                if not result.success:
                    return False
                cached_config = result.config
            
            # Update value
            cached_config[key] = value
            
            # Update cache
            self.cache.set(environment, cached_config)
            
            # Persist to file if requested
            if persist:
                return self._persist_config(environment, cached_config)
            
            return True
            
        except Exception as e:
            print(f"Error setting config value {key}: {str(e)}")
            return False
    
    def _persist_config(self, environment: str, config: Dict[str, Any]) -> bool:
        """Persist configuration to file."""
        try:
            current_dir = Path.cwd()
            
            # Find appropriate config file
            config_path = None
            for pattern in self._config_file_patterns:
                if '{env}' in pattern:
                    file_path = current_dir / pattern.format(env=environment)
                    if file_path.exists() or not config_path:
                        config_path = file_path
                        break
            
            if not config_path:
                # Create new config file
                config_path = current_dir / f'config.{environment}.json'
            
            # Write configuration
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            print(f"Error persisting config: {str(e)}")
            return False
    
    def get_load_history(self, limit: Optional[int] = None) -> List[ConfigLoadResult]:
        """Get configuration load history."""
        if limit:
            return self._load_history[-limit:]
        return self._load_history.copy()
    
    def clear_cache(self, environment: Optional[str] = None) -> None:
        """Clear configuration cache."""
        if environment:
            self.cache.delete(environment)
        else:
            self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()
    
    def validate_config_file(self, file_path: Union[str, Path], 
                             schema_name: Optional[str] = None) -> Dict[str, Any]:
        """Validate a configuration file."""
        try:
            config = self._load_from_file(Path(file_path))
            if config is None:
                return {
                    'valid': False,
                    'errors': [f"Could not load config file: {file_path}"],
                    'warnings': []
                }
            
            # Detect environment from filename
            environment = self._detect_environment_from_filename(Path(file_path))
            
            # Validate against schema if provided
            if schema_name:
                validation_result = validate_config_by_schema(config, schema_name, environment)
                return validation_result
            
            return {
                'valid': True,
                'errors': [],
                'warnings': [],
                'environment': environment
            }
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation failed: {str(e)}"],
                'warnings': []
            }
    
    def _detect_environment_from_filename(self, file_path: Path) -> str:
        """Detect environment from filename."""
        filename = file_path.name.lower()
        
        if 'dev' in filename or 'development' in filename:
            return 'development'
        elif 'test' in filename or 'testing' in filename:
            return 'testing'
        elif 'staging' in filename or 'stage' in filename:
            return 'staging'
        elif 'prod' in filename or 'production' in filename:
            return 'production'
        else:
            return detect_environment().value
    
    def merge_configs(self, configs: List[Dict[str, Any]], 
                      environment: Optional[str] = None) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries."""
        if environment is None:
            environment = detect_environment().value
        
        # Start with default configuration
        merged = self._default_config.copy()
        
        # Apply configurations in order
        for config in configs:
            merged.update(config)
        
        # Add environment information
        merged['environment'] = environment
        merged['config_sources'] = ['merged']
        
        return merged
    
    def export_config(self, environment: Optional[str] = None, 
                     format: str = 'json') -> Optional[str]:
        """Export configuration to string."""
        try:
            if environment is None:
                environment = detect_environment().value
            
            result = self.load_config(environment)
            if not result.success:
                return None
            
            if format.lower() == 'json':
                return json.dumps(result.config, indent=2, default=str)
            elif format.lower() == 'yaml':
                return yaml.dump(result.config, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            print(f"Error exporting config: {str(e)}")
            return None


# Global config loader instance
_config_loader = ConfigLoader()


# Convenience functions
def load_config(environment: Optional[str] = None, 
                config_path: Optional[Union[str, Path]] = None,
                schema_name: Optional[str] = None,
                use_cache: bool = True) -> ConfigLoadResult:
    """Load configuration for environment."""
    return _config_loader.load_config(environment, config_path, schema_name, use_cache)


def get_config_value(key: str, default: Any = None, 
                   environment: Optional[str] = None) -> Any:
    """Get configuration value."""
    return _config_loader.get_config_value(key, default, environment)


def set_config_value(key: str, value: Any, 
                   environment: Optional[str] = None,
                   persist: bool = False) -> bool:
    """Set configuration value."""
    return _config_loader.set_config_value(key, value, environment, persist)


def reload_config(environment: Optional[str] = None,
                config_path: Optional[Union[str, Path]] = None,
                schema_name: Optional[str] = None) -> ConfigLoadResult:
    """Reload configuration."""
    return _config_loader.reload_config(environment, config_path, schema_name)


def clear_config_cache(environment: Optional[str] = None) -> None:
    """Clear configuration cache."""
    _config_loader.clear_cache(environment)
