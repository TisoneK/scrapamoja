"""
Base Telemetry Configuration

Configuration management for the telemetry system including
settings, defaults, and validation.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ..exceptions import TelemetryConfigurationError


class TelemetryConfiguration:
    """
    Configuration management for the telemetry system.
    
    Provides centralized configuration with validation, defaults,
    and environment variable support.
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
        # Collection settings
        "collection_enabled": True,
        "buffer_size": 1000,
        "flush_interval_seconds": 30,
        "max_batch_size": 100,
        "collection_timeout_seconds": 5,
        
        # Storage settings
        "storage_type": "json",  # json, influxdb
        "storage_path": "data/telemetry",
        "retention_days": 30,
        "compression_enabled": True,
        "encryption_enabled": False,
        
        # Processing settings
        "processing_enabled": True,
        "processing_batch_size": 50,
        "processing_interval_seconds": 10,
        "anomaly_detection_enabled": True,
        
        # Alerting settings
        "alerting_enabled": True,
        "alert_thresholds": {
            "resolution_time_ms": 5000,
            "confidence_score": 0.5,
            "error_rate_percent": 10,
            "memory_usage_mb": 100
        },
        "alert_cooldown_minutes": 5,
        
        # Reporting settings
        "reporting_enabled": True,
        "report_retention_days": 90,
        "auto_report_generation": False,
        
        # Performance settings
        "performance_overhead_threshold": 0.02,  # 2%
        "max_concurrent_collections": 10,
        
        # Correlation settings
        "correlation_id_enabled": True,
        "correlation_id_length": 16,
        
        # Logging settings
        "logging_enabled": True,
        "log_level": "INFO",
        "structured_logging": True,
        
        # Integration settings
        "integration_enabled": True,
        "selector_hooks_enabled": True,
        "auto_registration": True,
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize telemetry configuration.
        
        Args:
            config: Optional configuration overrides
        """
        self._config = self.DEFAULT_CONFIG.copy()
        self._load_environment_overrides()
        
        if config:
            self.update_configuration(config)
        
        self._validate_configuration()
    
    def _load_environment_overrides(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            "TELEMETRY_ENABLED": ("collection_enabled", self._parse_bool),
            "TELEMETRY_STORAGE_TYPE": ("storage_type", str),
            "TELEMETRY_STORAGE_PATH": ("storage_path", str),
            "TELEMETRY_RETENTION_DAYS": ("retention_days", int),
            "TELEMETRY_BUFFER_SIZE": ("buffer_size", int),
            "TELEMETRY_FLUSH_INTERVAL": ("flush_interval_seconds", int),
            "TELEMETRY_LOG_LEVEL": ("log_level", str.upper),
            "TELEMETRY_ALERTING_ENABLED": ("alerting_enabled", self._parse_bool),
            "TELEMETRY_PROCESSING_ENABLED": ("processing_enabled", self._parse_bool),
            "TELEMETRY_REPORTING_ENABLED": ("reporting_enabled", self._parse_bool),
            "TELEMETRY_CORRELATION_ENABLED": ("correlation_id_enabled", self._parse_bool),
        }
        
        for env_var, (config_key, converter) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    self._config[config_key] = converter(env_value)
                except (ValueError, TypeError) as e:
                    raise TelemetryConfigurationError(
                        f"Invalid environment variable {env_var}: {e}",
                        error_code="TEL-101"
                    )
    
    def _parse_bool(self, value: str) -> bool:
        """Parse boolean value from string."""
        return value.lower() in ("true", "1", "yes", "on", "enabled")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        keys = key.split(".")
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self._validate_key(key, value)
    
    def update_configuration(self, config: Dict[str, Any]) -> None:
        """
        Update configuration with new values.
        
        Args:
            config: Configuration updates
        """
        self._deep_merge(self._config, config)
        self._validate_configuration()
    
    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> None:
        """Deep merge configuration dictionaries."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _validate_configuration(self) -> None:
        """Validate entire configuration."""
        errors = []
        
        # Validate collection settings
        if not isinstance(self._config.get("collection_enabled"), bool):
            errors.append("collection_enabled must be boolean")
        
        if not isinstance(self._config.get("buffer_size"), int) or self._config.get("buffer_size") <= 0:
            errors.append("buffer_size must be positive integer")
        
        if not isinstance(self._config.get("flush_interval_seconds"), int) or self._config.get("flush_interval_seconds") <= 0:
            errors.append("flush_interval_seconds must be positive integer")
        
        # Validate storage settings
        storage_type = self._config.get("storage_type")
        if storage_type not in ["json", "influxdb"]:
            errors.append("storage_type must be 'json' or 'influxdb'")
        
        if not isinstance(self._config.get("retention_days"), int) or self._config.get("retention_days") <= 0:
            errors.append("retention_days must be positive integer")
        
        # Validate performance settings
        overhead = self._config.get("performance_overhead_threshold")
        if not isinstance(overhead, (int, float)) or not 0 <= overhead <= 1:
            errors.append("performance_overhead_threshold must be between 0 and 1")
        
        # Validate log level
        log_level = self._config.get("log_level")
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_levels:
            errors.append(f"log_level must be one of {valid_levels}")
        
        if errors:
            raise TelemetryConfigurationError(
                f"Configuration validation failed: {'; '.join(errors)}",
                error_code="TEL-102"
            )
    
    def _validate_key(self, key: str, value: Any) -> None:
        """Validate a specific configuration key."""
        if key == "performance_overhead_threshold":
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise TelemetryConfigurationError(
                    "performance_overhead_threshold must be between 0 and 1",
                    error_code="TEL-103"
                )
        elif key == "buffer_size":
            if not isinstance(value, int) or value <= 0:
                raise TelemetryConfigurationError(
                    "buffer_size must be positive integer",
                    error_code="TEL-104"
                )
        elif key == "storage_type":
            if value not in ["json", "influxdb"]:
                raise TelemetryConfigurationError(
                    "storage_type must be 'json' or 'influxdb'",
                    error_code="TEL-105"
                )
    
    def is_collection_enabled(self) -> bool:
        """Check if telemetry collection is enabled."""
        return self.get("collection_enabled", False)
    
    def is_storage_enabled(self) -> bool:
        """Check if telemetry storage is enabled."""
        return self.is_collection_enabled() and self.get("storage_type") is not None
    
    def is_processing_enabled(self) -> bool:
        """Check if telemetry processing is enabled."""
        return self.get("processing_enabled", False)
    
    def is_alerting_enabled(self) -> bool:
        """Check if telemetry alerting is enabled."""
        return self.get("alerting_enabled", False)
    
    def is_reporting_enabled(self) -> bool:
        """Check if telemetry reporting is enabled."""
        return self.get("reporting_enabled", False)
    
    def is_correlation_enabled(self) -> bool:
        """Check if correlation IDs are enabled."""
        return self.get("correlation_id_enabled", False)
    
    def get_storage_path(self) -> str:
        """Get storage path."""
        return self.get("storage_path", "data/telemetry")
    
    def get_retention_period(self) -> timedelta:
        """Get retention period as timedelta."""
        days = self.get("retention_days", 30)
        return timedelta(days=days)
    
    def get_alert_thresholds(self) -> Dict[str, float]:
        """Get alert thresholds."""
        return self.get("alert_thresholds", {})
    
    def get_buffer_size(self) -> int:
        """Get buffer size."""
        return self.get("buffer_size", 1000)
    
    def get_flush_interval(self) -> timedelta:
        """Get flush interval as timedelta."""
        seconds = self.get("flush_interval_seconds", 30)
        return timedelta(seconds=seconds)
    
    def get_log_level(self) -> str:
        """Get log level."""
        return self.get("log_level", "INFO")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self._config.copy()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self._config = self.DEFAULT_CONFIG.copy()
        self._load_environment_overrides()
        self._validate_configuration()
    
    def get_effective_config(self) -> Dict[str, Any]:
        """
        Get effective configuration after all overrides.
        
        Returns:
            Effective configuration dictionary
        """
        return self.to_dict()
    
    def validate_storage_path(self) -> bool:
        """
        Validate storage path is accessible.
        
        Returns:
            True if path is valid and accessible
        """
        try:
            import os
            path = self.get_storage_path()
            os.makedirs(path, exist_ok=True)
            return os.access(path, os.W_OK)
        except Exception:
            return False
    
    def get_performance_overhead_limit(self) -> float:
        """Get performance overhead limit."""
        return self.get("performance_overhead_threshold", 0.02)
    
    def should_compress_storage(self) -> bool:
        """Check if storage compression should be used."""
        return self.get("compression_enabled", True)
    
    def should_encrypt_storage(self) -> bool:
        """Check if storage encryption should be used."""
        return self.get("encryption_enabled", False)
