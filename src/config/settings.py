"""
Configuration management for Selector Engine.

Provides centralized configuration with environment variable support,
validation, and runtime configuration updates.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field
from dotenv import load_dotenv

from src.utils.exceptions import ConfigurationError


@dataclass
class SelectorEngineConfig:
    """Configuration for selector engine core functionality."""
    default_confidence_threshold: float = 0.8
    max_resolution_time: float = 1000.0  # milliseconds
    snapshot_on_failure: bool = True
    drift_detection_enabled: bool = True
    evolution_enabled: bool = True
    cache_enabled: bool = True
    cache_ttl: int = 30  # seconds
    parallel_resolution: bool = True
    max_concurrent_resolutions: int = 10
    max_strategies_per_selector: int = 10
    strategy_timeout: float = 5000.0  # milliseconds per strategy
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0.0 <= self.default_confidence_threshold <= 1.0:
            raise ConfigurationError(
                "selector_engine", "default_confidence_threshold",
                "Must be between 0.0 and 1.0", self.default_confidence_threshold
            )
        if self.max_resolution_time <= 0:
            raise ConfigurationError(
                "selector_engine", "max_resolution_time",
                "Must be > 0", self.max_resolution_time
            )
        if self.cache_ttl < 0:
            raise ConfigurationError(
                "selector_engine", "cache_ttl", "Must be >= 0", self.cache_ttl
            )
        if self.max_concurrent_resolutions < 1:
            raise ConfigurationError(
                "selector_engine", "max_concurrent_resolutions",
                "Must be >= 1", self.max_concurrent_resolutions
            )


@dataclass
class SnapshotConfig:
    """Configuration for DOM snapshots."""
    compression_enabled: bool = True
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    retention_days: int = 30
    storage_path: str = "data/snapshots"
    auto_cleanup: bool = True
    capture_on_low_confidence: bool = True
    low_confidence_threshold: float = 0.6
    
    def __post_init__(self):
        """Validate snapshot configuration."""
        if self.max_file_size <= 0:
            raise ConfigurationError(
                "snapshots", "max_file_size", "Must be > 0", self.max_file_size
            )
        if self.retention_days < 0:
            raise ConfigurationError(
                "snapshots", "retention_days", "Must be >= 0", self.retention_days
            )
        if not 0.0 <= self.low_confidence_threshold <= 1.0:
            raise ConfigurationError(
                "snapshots", "low_confidence_threshold",
                "Must be between 0.0 and 1.0", self.low_confidence_threshold
            )


@dataclass
class DriftDetectionConfig:
    """Configuration for drift detection."""
    analysis_window_hours: int = 24
    drift_threshold: float = 0.7
    trend_sensitivity: float = 0.1
    min_sample_size: int = 30
    alert_threshold: float = 0.8
    auto_evolution_enabled: bool = True
    evolution_confidence_threshold: float = 0.85
    
    def __post_init__(self):
        """Validate drift detection configuration."""
        if self.analysis_window_hours <= 0:
            raise ConfigurationError(
                "drift_detection", "analysis_window_hours",
                "Must be > 0", self.analysis_window_hours
            )
        if not 0.0 <= self.drift_threshold <= 1.0:
            raise ConfigurationError(
                "drift_detection", "drift_threshold",
                "Must be between 0.0 and 1.0", self.drift_threshold
            )
        if self.min_sample_size < 1:
            raise ConfigurationError(
                "drift_detection", "min_sample_size",
                "Must be >= 1", self.min_sample_size
            )


@dataclass
class StealthConfig:
    """Configuration for stealth and anti-detection."""
    user_agent_rotation: bool = True
    mouse_simulation: bool = True
    fingerprint_normalization: bool = True
    random_delays_enabled: bool = True
    min_delay_ms: float = 100.0
    max_delay_ms: float = 1000.0
    proxy_enabled: bool = False
    proxy_rotation_strategy: str = "per_match"
    
    def __post_init__(self):
        """Validate stealth configuration."""
        if self.min_delay_ms < 0 or self.max_delay_ms < 0:
            raise ConfigurationError(
                "stealth", "delays", "Must be >= 0", 
                f"min={self.min_delay_ms}, max={self.max_delay_ms}"
            )
        if self.min_delay_ms >= self.max_delay_ms:
            raise ConfigurationError(
                "stealth", "delays", "min_delay must be < max_delay",
                f"min={self.min_delay_ms}, max={self.max_delay_ms}"
            )
        valid_strategies = ["per_match", "per_session", "per_request"]
        if self.proxy_rotation_strategy not in valid_strategies:
            raise ConfigurationError(
                "stealth", "proxy_rotation_strategy",
                f"Must be one of {valid_strategies}", self.proxy_rotation_strategy
            )


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    structured_logging: bool = True
    json_output: bool = True
    file_logging: bool = True
    log_file: str = "data/logs/selector_engine.log"
    console_output: bool = True
    correlation_ids: bool = True
    performance_logging: bool = True
    
    def __post_init__(self):
        """Validate logging configuration."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ConfigurationError(
                "logging", "level", f"Must be one of {valid_levels}", self.level
            )


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization."""
    enable_caching: bool = True
    cache_size_limit: int = 1000
    enable_parallel_processing: bool = True
    max_workers: int = 4
    batch_size: int = 50
    enable_metrics: bool = True
    metrics_retention_hours: int = 168  # 1 week
    
    def __post_init__(self):
        """Validate performance configuration."""
        if self.cache_size_limit < 1:
            raise ConfigurationError(
                "performance", "cache_size_limit", "Must be >= 1", self.cache_size_limit
            )
        if self.max_workers < 1:
            raise ConfigurationError(
                "performance", "max_workers", "Must be >= 1", self.max_workers
            )
        if self.batch_size < 1:
            raise ConfigurationError(
                "performance", "batch_size", "Must be >= 1", self.batch_size
            )


@dataclass
class BrowserConfig:
    """Configuration for browser lifecycle management."""
    default_browser_type: str = "chromium"
    default_headless: bool = True
    max_concurrent_sessions: int = 50
    session_timeout_seconds: int = 300
    resource_monitoring_enabled: bool = True
    memory_threshold_mb: float = 1024.0
    cpu_threshold_percent: float = 80.0
    disk_threshold_mb: float = 2048.0
    auto_cleanup_enabled: bool = True
    state_persistence_enabled: bool = True
    state_encryption_enabled: bool = True
    state_retention_days: int = 7
    default_viewport_width: int = 1920
    default_viewport_height: int = 1080
    stealth_enabled: bool = True
    proxy_enabled: bool = False
    
    def __post_init__(self):
        """Validate browser configuration."""
        valid_browsers = ["chromium", "firefox", "webkit"]
        if self.default_browser_type not in valid_browsers:
            raise ConfigurationError(
                "browser", "default_browser_type",
                f"Must be one of {valid_browsers}", self.default_browser_type
            )
        if self.max_concurrent_sessions < 1:
            raise ConfigurationError(
                "browser", "max_concurrent_sessions",
                "Must be >= 1", self.max_concurrent_sessions
            )
        if self.session_timeout_seconds < 0:
            raise ConfigurationError(
                "browser", "session_timeout_seconds",
                "Must be >= 0", self.session_timeout_seconds
            )
        if self.memory_threshold_mb <= 0:
            raise ConfigurationError(
                "browser", "memory_threshold_mb",
                "Must be > 0", self.memory_threshold_mb
            )
        if not 0.0 <= self.cpu_threshold_percent <= 100.0:
            raise ConfigurationError(
                "browser", "cpu_threshold_percent",
                "Must be between 0.0 and 100.0", self.cpu_threshold_percent
            )
        if self.disk_threshold_mb <= 0:
            raise ConfigurationError(
                "browser", "disk_threshold_mb",
                "Must be > 0", self.disk_threshold_mb
            )
        if self.state_retention_days < 0:
            raise ConfigurationError(
                "browser", "state_retention_days",
                "Must be >= 0", self.state_retention_days
            )
        if self.default_viewport_width <= 0 or self.default_viewport_height <= 0:
            raise ConfigurationError(
                "browser", "viewport",
                "Viewport dimensions must be > 0", 
                f"{self.default_viewport_width}x{self.default_viewport_height}"
            )


@dataclass
class AppConfig:
    """Main application configuration."""
    mode: str = "production"  # production, development, research
    debug: bool = False
    environment: str = "default"
    
    selector_engine: SelectorEngineConfig = field(default_factory=SelectorEngineConfig)
    snapshots: SnapshotConfig = field(default_factory=SnapshotConfig)
    drift_detection: DriftDetectionConfig = field(default_factory=DriftDetectionConfig)
    stealth: StealthConfig = field(default_factory=StealthConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    
    def __post_init__(self):
        """Validate application configuration."""
        valid_modes = ["production", "development", "research"]
        if self.mode not in valid_modes:
            raise ConfigurationError(
                "app", "mode", f"Must be one of {valid_modes}", self.mode
            )


class ConfigManager:
    """Manages application configuration with file and environment support."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config.yaml"
        self._config: Optional[AppConfig] = None
        self._load_environment()
    
    def _load_environment(self):
        """Load environment variables from .env file."""
        # Try to load .env from current directory and parent directories
        env_paths = [
            Path(".env"),
            Path("..") / ".env",
            Path("..") / ".." / ".env"
        ]
        
        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                break
    
    def load_config(self) -> AppConfig:
        """Load configuration from file and environment variables."""
        if self._config is not None:
            return self._config
        
        # Start with default configuration
        config_dict = {}
        
        # Load from YAML file if it exists
        config_path = Path(self.config_file)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_dict = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ConfigurationError(
                    "config", "file", f"Invalid YAML: {e}", self.config_file
                )
        
        # Override with environment variables
        config_dict = self._apply_environment_overrides(config_dict)
        
        # Create configuration objects
        try:
            self._config = AppConfig(**config_dict)
        except TypeError as e:
            raise ConfigurationError(
                "config", "parsing", f"Invalid configuration structure: {e}"
            )
        
        return self._config
    
    def _apply_environment_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        # Environment variable mappings
        env_mappings = {
            # App settings
            "SCOREWISE_MODE": ("app", "mode"),
            "SCOREWISE_DEBUG": ("app", "debug"),
            "SCOREWISE_ENVIRONMENT": ("app", "environment"),
            
            # Selector engine
            "SCOREWISE_CONFIDENCE_THRESHOLD": ("selector_engine", "default_confidence_threshold"),
            "SCOREWISE_MAX_RESOLUTION_TIME": ("selector_engine", "max_resolution_time"),
            "SCOREWISE_SNAPSHOT_ON_FAILURE": ("selector_engine", "snapshot_on_failure"),
            "SCOREWISE_DRIFT_DETECTION": ("selector_engine", "drift_detection_enabled"),
            "SCOREWISE_EVOLUTION": ("selector_engine", "evolution_enabled"),
            "SCOREWISE_CACHE_ENABLED": ("selector_engine", "cache_enabled"),
            "SCOREWISE_CACHE_TTL": ("selector_engine", "cache_ttl"),
            "SCOREWISE_PARALLEL_RESOLUTION": ("selector_engine", "parallel_resolution"),
            "SCOREWISE_MAX_CONCURRENT": ("selector_engine", "max_concurrent_resolutions"),
            
            # Snapshots
            "SCOREWISE_SNAPSHOT_COMPRESSION": ("snapshots", "compression_enabled"),
            "SCOREWISE_SNAPSHOT_MAX_SIZE": ("snapshots", "max_file_size"),
            "SCOREWISE_SNAPSHOT_RETENTION": ("snapshots", "retention_days"),
            "SCOREWISE_SNAPSHOT_PATH": ("snapshots", "storage_path"),
            
            # Drift detection
            "SCOREWISE_DRIFT_WINDOW": ("drift_detection", "analysis_window_hours"),
            "SCOREWISE_DRIFT_THRESHOLD": ("drift_detection", "drift_threshold"),
            "SCOREWISE_DRIFT_SENSITIVITY": ("drift_detection", "trend_sensitivity"),
            "SCOREWISE_DRIFT_MIN_SAMPLES": ("drift_detection", "min_sample_size"),
            
            # Stealth
            "SCOREWISE_STEALTH_USER_AGENT": ("stealth", "user_agent_rotation"),
            "SCOREWISE_STEALTH_MOUSE": ("stealth", "mouse_simulation"),
            "SCOREWISE_STEALTH_FINGERPRINT": ("stealth", "fingerprint_normalization"),
            "SCOREWISE_STEALTH_DELAYS": ("stealth", "random_delays_enabled"),
            "SCOREWISE_STEALTH_MIN_DELAY": ("stealth", "min_delay_ms"),
            "SCOREWISE_STEALTH_MAX_DELAY": ("stealth", "max_delay_ms"),
            "SCOREWISE_STEALTH_PROXY": ("stealth", "proxy_enabled"),
            
            # Logging
            "SCOREWISE_LOG_LEVEL": ("logging", "level"),
            "SCOREWISE_LOG_STRUCTURED": ("logging", "structured_logging"),
            "SCOREWISE_LOG_JSON": ("logging", "json_output"),
            "SCOREWISE_LOG_FILE": ("logging", "file_logging"),
            "SCOREWISE_LOG_PATH": ("logging", "log_file"),
            
            # Performance
            "SCOREWISE_PERF_CACHE": ("performance", "enable_caching"),
            "SCOREWISE_PERF_CACHE_SIZE": ("performance", "cache_size_limit"),
            "SCOREWISE_PERF_PARALLEL": ("performance", "enable_parallel_processing"),
            "SCOREWISE_PERF_WORKERS": ("performance", "max_workers"),
            "SCOREWISE_PERF_BATCH_SIZE": ("performance", "batch_size"),
            
            # Browser
            "SCOREWISE_BROWSER_TYPE": ("browser", "default_browser_type"),
            "SCOREWISE_BROWSER_HEADLESS": ("browser", "default_headless"),
            "SCOREWISE_MAX_SESSIONS": ("browser", "max_concurrent_sessions"),
            "SCOREWISE_SESSION_TIMEOUT": ("browser", "session_timeout_seconds"),
            "SCOREWISE_RESOURCE_MONITORING": ("browser", "resource_monitoring_enabled"),
            "SCOREWISE_MEMORY_THRESHOLD": ("browser", "memory_threshold_mb"),
            "SCOREWISE_CPU_THRESHOLD": ("browser", "cpu_threshold_percent"),
            "SCOREWISE_DISK_THRESHOLD": ("browser", "disk_threshold_mb"),
            "SCOREWISE_AUTO_CLEANUP": ("browser", "auto_cleanup_enabled"),
            "SCOREWISE_STATE_PERSISTENCE": ("browser", "state_persistence_enabled"),
            "SCOREWISE_STATE_ENCRYPTION": ("browser", "state_encryption_enabled"),
            "SCOREWISE_STATE_RETENTION": ("browser", "state_retention_days"),
            "SCOREWISE_VIEWPORT_WIDTH": ("browser", "default_viewport_width"),
            "SCOREWISE_VIEWPORT_HEIGHT": ("browser", "default_viewport_height"),
            "SCOREWISE_STEALTH_ENABLED": ("browser", "stealth_enabled"),
            "SCOREWISE_PROXY_ENABLED": ("browser", "proxy_enabled"),
        }
        
        # Apply overrides
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                converted_value = self._convert_env_value(value)
                
                # Ensure section exists
                if section not in config_dict:
                    config_dict[section] = {}
                
                # Apply override
                config_dict[section][key] = converted_value
        
        return config_dict
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def get_config(self) -> AppConfig:
        """Get current configuration."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def update_config(self, section: str, config: Any) -> bool:
        """Update configuration section."""
        if self._config is None:
            self.load_config()
        
        try:
            if hasattr(self._config, section):
                setattr(self._config, section, config)
                return True
            else:
                raise ConfigurationError(
                    "config", "update", f"Unknown section: {section}"
                )
        except Exception as e:
            raise ConfigurationError(
                "config", "update", f"Failed to update {section}: {e}"
            )
    
    def save_config(self, file_path: Optional[str] = None) -> bool:
        """Save current configuration to file."""
        if self._config is None:
            return False
        
        target_file = file_path or self.config_file
        
        try:
            # Convert config to dictionary
            config_dict = {
                "app": {
                    "mode": self._config.mode,
                    "debug": self._config.debug,
                    "environment": self._config.environment
                },
                "selector_engine": self._config.selector_engine.__dict__,
                "snapshots": self._config.snapshots.__dict__,
                "drift_detection": self._config.drift_detection.__dict__,
                "stealth": self._config.stealth.__dict__,
                "logging": self._config.logging.__dict__,
                "performance": self._config.performance.__dict__,
                "browser": self._config.browser.__dict__
            }
            
            # Ensure directory exists
            Path(target_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(target_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            return True
        except Exception as e:
            raise ConfigurationError(
                "config", "save", f"Failed to save config: {e}"
            )
    
    def reload_config(self) -> AppConfig:
        """Reload configuration from file."""
        self._config = None
        return self.load_config()


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """Get application configuration."""
    return config_manager.get_config()


def update_config_section(section: str, config: Any) -> bool:
    """Update configuration section."""
    return config_manager.update_config(section, config)


def save_config(file_path: Optional[str] = None) -> bool:
    """Save configuration to file."""
    return config_manager.save_config(file_path)


def reload_config() -> AppConfig:
    """Reload configuration from file."""
    return config_manager.reload_config()


# Utility functions for common configuration access
def is_development_mode() -> bool:
    """Check if running in development mode."""
    return get_config().mode == "development"


def is_production_mode() -> bool:
    """Check if running in production mode."""
    return get_config().mode == "production"


def is_research_mode() -> bool:
    """Check if running in research mode."""
    return get_config().mode == "research"


def get_confidence_threshold() -> float:
    """Get confidence threshold for current mode."""
    config = get_config()
    if is_research_mode():
        return config.selector_engine.default_confidence_threshold * 0.7  # More lenient
    return config.selector_engine.default_confidence_threshold


def should_enable_snapshots() -> bool:
    """Check if snapshots should be enabled for current mode."""
    config = get_config()
    if is_research_mode():
        return True  # Always enable in research mode
    return config.selector_engine.snapshot_on_failure
