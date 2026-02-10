"""
Configuration management for YAML selector system.

This module provides configuration management for selector directories,
validation modes, and other selector system settings.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class SelectorConfig:
    """Configuration for the YAML selector system."""
    
    # Directory configuration
    selector_directories: List[str] = field(default_factory=lambda: ["src/sites/*/selectors/"])
    default_selector_directory: str = "src/sites/wikipedia/selectors/"
    
    # Validation configuration
    validation_mode: str = "strict"  # strict, lenient, permissive
    enable_validation_cache: bool = True
    max_selector_file_size: int = 1024 * 1024  # 1MB
    
    # Loading configuration
    enable_hot_reload: bool = False
    hot_reload_poll_interval: float = 1.0  # seconds
    enable_lazy_loading: bool = True
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds
    
    # Performance configuration
    max_concurrent_loads: int = 10
    loading_timeout: float = 30.0  # seconds
    performance_monitoring: bool = True
    
    # Error handling configuration
    continue_on_error: bool = True
    max_retry_attempts: int = 3
    retry_backoff_factor: float = 2.0
    
    # Logging configuration
    log_level: str = "INFO"
    enable_performance_logging: bool = True
    enable_debug_logging: bool = False
    
    # Security configuration
    allowed_file_extensions: List[str] = field(default_factory=lambda: [".yaml", ".yml"])
    enforce_file_size_limits: bool = True
    validate_file_paths: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate validation mode
        valid_modes = ["strict", "lenient", "permissive"]
        if self.validation_mode not in valid_modes:
            raise ValueError(f"Invalid validation_mode: {self.validation_mode}. Must be one of: {valid_modes}")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(f"Invalid log_level: {self.log_level}. Must be one of: {valid_log_levels}")
        
        # Validate numeric values
        if self.max_selector_file_size <= 0:
            raise ValueError("max_selector_file_size must be positive")
        if self.hot_reload_poll_interval <= 0:
            raise ValueError("hot_reload_poll_interval must be positive")
        if self.cache_ttl < 0:
            raise ValueError("cache_ttl cannot be negative")
        if self.max_concurrent_loads <= 0:
            raise ValueError("max_concurrent_loads must be positive")
        if self.loading_timeout <= 0:
            raise ValueError("loading_timeout must be positive")
        if self.max_retry_attempts < 0:
            raise ValueError("max_retry_attempts cannot be negative")
        if self.retry_backoff_factor <= 1.0:
            raise ValueError("retry_backoff_factor must be greater than 1.0")
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "SelectorConfig":
        """Create configuration from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def from_env(cls) -> "SelectorConfig":
        """Create configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if present
        if os.getenv("SELECTOR_DIRECTORIES"):
            config.selector_directories = os.getenv("SELECTOR_DIRECTORIES").split(",")
        
        if os.getenv("DEFAULT_SELECTOR_DIRECTORY"):
            config.default_selector_directory = os.getenv("DEFAULT_SELECTOR_DIRECTORY")
        
        if os.getenv("SELECTOR_VALIDATION_MODE"):
            config.validation_mode = os.getenv("SELECTOR_VALIDATION_MODE")
        
        if os.getenv("SELECTOR_ENABLE_HOT_RELOAD"):
            config.enable_hot_reload = os.getenv("SELECTOR_ENABLE_HOT_RELOAD").lower() == "true"
        
        if os.getenv("SELECTOR_HOT_RELOAD_INTERVAL"):
            config.hot_reload_poll_interval = float(os.getenv("SELECTOR_HOT_RELOAD_INTERVAL"))
        
        if os.getenv("SELECTOR_ENABLE_LAZY_LOADING"):
            config.enable_lazy_loading = os.getenv("SELECTOR_ENABLE_LAZY_LOADING").lower() == "true"
        
        if os.getenv("SELECTOR_CACHE_ENABLED"):
            config.cache_enabled = os.getenv("SELECTOR_CACHE_ENABLED").lower() == "true"
        
        if os.getenv("SELECTOR_CACHE_TTL"):
            config.cache_ttl = int(os.getenv("SELECTOR_CACHE_TTL"))
        
        if os.getenv("SELECTOR_MAX_CONCURRENT_LOADS"):
            config.max_concurrent_loads = int(os.getenv("SELECTOR_MAX_CONCURRENT_LOADS"))
        
        if os.getenv("SELECTOR_LOADING_TIMEOUT"):
            config.loading_timeout = float(os.getenv("SELECTOR_LOADING_TIMEOUT"))
        
        if os.getenv("SELECTOR_PERFORMANCE_MONITORING"):
            config.performance_monitoring = os.getenv("SELECTOR_PERFORMANCE_MONITORING").lower() == "true"
        
        if os.getenv("SELECTOR_CONTINUE_ON_ERROR"):
            config.continue_on_error = os.getenv("SELECTOR_CONTINUE_ON_ERROR").lower() == "true"
        
        if os.getenv("SELECTOR_LOG_LEVEL"):
            config.log_level = os.getenv("SELECTOR_LOG_LEVEL")
        
        if os.getenv("SELECTOR_MAX_FILE_SIZE"):
            config.max_selector_file_size = int(os.getenv("SELECTOR_MAX_FILE_SIZE"))
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "selector_directories": self.selector_directories,
            "default_selector_directory": self.default_selector_directory,
            "validation_mode": self.validation_mode,
            "enable_validation_cache": self.enable_validation_cache,
            "max_selector_file_size": self.max_selector_file_size,
            "enable_hot_reload": self.enable_hot_reload,
            "hot_reload_poll_interval": self.hot_reload_poll_interval,
            "enable_lazy_loading": self.enable_lazy_loading,
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "max_concurrent_loads": self.max_concurrent_loads,
            "loading_timeout": self.loading_timeout,
            "performance_monitoring": self.performance_monitoring,
            "continue_on_error": self.continue_on_error,
            "max_retry_attempts": self.max_retry_attempts,
            "retry_backoff_factor": self.retry_backoff_factor,
            "log_level": self.log_level,
            "enable_performance_logging": self.enable_performance_logging,
            "enable_debug_logging": self.enable_debug_logging,
            "allowed_file_extensions": self.allowed_file_extensions,
            "enforce_file_size_limits": self.enforce_file_size_limits,
            "validate_file_paths": self.validate_file_paths
        }
    
    def get_selector_directories(self) -> List[str]:
        """Get resolved selector directories."""
        directories = []
        
        for directory in self.selector_directories:
            # Expand glob patterns
            if "*" in directory:
                from glob import glob
                expanded_dirs = glob(directory)
                directories.extend(expanded_dirs)
            else:
                directories.append(directory)
        
        # Resolve relative paths and filter existing directories
        resolved_dirs = []
        for directory in directories:
            path = Path(directory).resolve()
            if path.exists() and path.is_dir():
                resolved_dirs.append(str(path))
            else:
                logger.warning(f"Selector directory does not exist: {directory}")
        
        return resolved_dirs
    
    def is_file_extension_allowed(self, file_path: str) -> bool:
        """Check if file extension is allowed."""
        path = Path(file_path)
        return path.suffix.lower() in self.allowed_file_extensions
    
    def validate_file_path(self, file_path: str) -> bool:
        """Validate file path for security."""
        if not self.validate_file_paths:
            return True
        
        try:
            path = Path(file_path).resolve()
            
            # Check if path is within allowed directories
            allowed_dirs = [Path(d).resolve() for d in self.get_selector_directories()]
            
            for allowed_dir in allowed_dirs:
                try:
                    path.relative_to(allowed_dir)
                    return True
                except ValueError:
                    continue
            
            return False
        except Exception:
            return False
    
    def get_log_level(self) -> int:
        """Get numeric log level."""
        import logging
        return getattr(logging, self.log_level.upper())


class ConfigManager:
    """Manages selector configuration with support for multiple sources."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize config manager."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.config_file = config_file
        self._config: Optional[SelectorConfig] = None
    
    def load_config(self) -> SelectorConfig:
        """Load configuration from all sources."""
        # Start with default configuration
        config_dict = {}
        
        # Load from config file if specified
        if self.config_file:
            config_dict.update(self._load_from_file(self.config_file))
        
        # Override with environment variables
        env_config = SelectorConfig.from_env()
        config_dict.update(env_config.to_dict())
        
        # Create final configuration
        self._config = SelectorConfig.from_dict(config_dict)
        
        self.logger.info(f"Configuration loaded: validation_mode={self._config.validation_mode}, "
                        f"hot_reload={self._config.enable_hot_reload}, "
                        f"cache_enabled={self._config.cache_enabled}")
        
        return self._config
    
    def get_config(self) -> SelectorConfig:
        """Get current configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def reload_config(self) -> SelectorConfig:
        """Reload configuration from sources."""
        self.logger.info("Reloading configuration...")
        return self.load_config()
    
    def _load_from_file(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            import yaml
            
            config_path = Path(config_file)
            if not config_path.exists():
                self.logger.warning(f"Config file not found: {config_file}")
                return {}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not isinstance(config_data, dict):
                self.logger.error(f"Invalid config file format: {config_file}")
                return {}
            
            self.logger.info(f"Loaded configuration from: {config_file}")
            return config_data
            
        except Exception as e:
            self.logger.error(f"Failed to load config from {config_file}: {str(e)}")
            return {}
    
    def save_config(self, config_file: Optional[str] = None) -> bool:
        """Save current configuration to file."""
        try:
            import yaml
            
            if config_file is None:
                config_file = self.config_file
            
            if config_file is None:
                self.logger.error("No config file specified for saving")
                return False
            
            config_path = Path(config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_dict = self.get_config().to_dict()
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to: {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save config to {config_file}: {str(e)}")
            return False
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update configuration with new values."""
        try:
            current_config = self.get_config().to_dict()
            current_config.update(updates)
            
            self._config = SelectorConfig.from_dict(current_config)
            
            self.logger.info(f"Configuration updated with: {list(updates.keys())}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {str(e)}")
            return False


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    return _config_manager


def get_config() -> SelectorConfig:
    """Get current selector configuration."""
    return get_config_manager().get_config()


def reload_config() -> SelectorConfig:
    """Reload selector configuration."""
    return get_config_manager().reload_config()


def update_config(updates: Dict[str, Any]) -> bool:
    """Update selector configuration."""
    return get_config_manager().update_config(updates)
