"""
Simple configuration for the snapshot system.

This module provides straightforward configuration settings without the complexity
of feature flags, rollout stages, or percentage-based enabling.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class SnapshotSettings:
    """Global snapshot system settings."""
    
    # Storage configuration
    base_path: str = "data/snapshots"
    enable_partitioning: bool = True
    partition_threshold: int = 10000
    max_files_per_directory: int = 1000
    max_directory_size_mb: int = 100
    
    # Performance settings
    enable_async_save: bool = True
    enable_deduplication: bool = True
    dedup_cache_size: int = 1000
    
    # Rate limiting
    rate_limit_per_minute: int = 5
    
    # Monitoring
    enable_metrics: bool = True
    metrics_retention_days: int = 30
    metrics_max_history_size: int = 10000
    
    # Capture defaults
    default_capture_html: bool = True
    default_capture_screenshot: bool = True
    default_capture_console: bool = True
    default_capture_network: bool = False
    
    # Cleanup settings
    cleanup_old_bundles_days: int = 30
    enable_auto_cleanup: bool = False
    
    # Environment-specific overrides
    environment_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize settings from environment variables."""
        self._load_from_environment()
    
    def _load_from_environment(self):
        """Load settings from environment variables."""
        # Storage settings
        if os.getenv("SNAPSHOT_BASE_PATH"):
            self.base_path = os.getenv("SNAPSHOT_BASE_PATH")
        
        if os.getenv("SNAPSHOT_ENABLE_PARTITIONING"):
            self.enable_partitioning = os.getenv("SNAPSHOT_ENABLE_PARTITIONING").lower() == "true"
        
        if os.getenv("SNAPSHOT_PARTITION_THRESHOLD"):
            self.partition_threshold = int(os.getenv("SNAPSHOT_PARTITION_THRESHOLD"))
        
        # Performance settings
        if os.getenv("SNAPSHOT_ENABLE_ASYNC_SAVE"):
            self.enable_async_save = os.getenv("SNAPSHOT_ENABLE_ASYNC_SAVE").lower() == "true"
        
        if os.getenv("SNAPSHOT_ENABLE_DEDUPLICATION"):
            self.enable_deduplication = os.getenv("SNAPSHOT_ENABLE_DEDUPLICATION").lower() == "true"
        
        if os.getenv("SNAPSHOT_DEDUP_CACHE_SIZE"):
            self.dedup_cache_size = int(os.getenv("SNAPSHOT_DEDUP_CACHE_SIZE"))
        
        # Rate limiting
        if os.getenv("SNAPSHOT_RATE_LIMIT_PER_MINUTE"):
            self.rate_limit_per_minute = int(os.getenv("SNAPSHOT_RATE_LIMIT_PER_MINUTE"))
        
        # Monitoring
        if os.getenv("SNAPSHOT_ENABLE_METRICS"):
            self.enable_metrics = os.getenv("SNAPSHOT_ENABLE_METRICS").lower() == "true"
        
        if os.getenv("SNAPSHOT_METRICS_RETENTION_DAYS"):
            self.metrics_retention_days = int(os.getenv("SNAPSHOT_METRICS_RETENTION_DAYS"))
        
        # Capture defaults
        if os.getenv("SNAPSHOT_DEFAULT_CAPTURE_SCREENSHOT"):
            self.default_capture_screenshot = os.getenv("SNAPSHOT_DEFAULT_CAPTURE_SCREENSHOT").lower() == "true"
        
        if os.getenv("SNAPSHOT_DEFAULT_CAPTURE_CONSOLE"):
            self.default_capture_console = os.getenv("SNAPSHOT_DEFAULT_CAPTURE_CONSOLE").lower() == "true"
        
        if os.getenv("SNAPSHOT_DEFAULT_CAPTURE_NETWORK"):
            self.default_capture_network = os.getenv("SNAPSHOT_DEFAULT_CAPTURE_NETWORK").lower() == "true"
        
        # Cleanup
        if os.getenv("SNAPSHOT_CLEANUP_OLD_BUNDLES_DAYS"):
            self.cleanup_old_bundles_days = int(os.getenv("SNAPSHOT_CLEANUP_OLD_BUNDLES_DAYS"))
        
        if os.getenv("SNAPSHOT_ENABLE_AUTO_CLEANUP"):
            self.enable_auto_cleanup = os.getenv("SNAPSHOT_ENABLE_AUTO_CLEANUP").lower() == "true"
    
    def get_environment_settings(self, environment: str = "production") -> "SnapshotSettings":
        """Get settings for a specific environment."""
        if environment not in self.environment_overrides:
            return self
        
        # Create a copy and apply overrides
        settings = SnapshotSettings(**self.__dict__)
        overrides = self.environment_overrides[environment]
        
        for key, value in overrides.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        return settings
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "base_path": self.base_path,
            "enable_partitioning": self.enable_partitioning,
            "partition_threshold": self.partition_threshold,
            "max_files_per_directory": self.max_files_per_directory,
            "max_directory_size_mb": self.max_directory_size_mb,
            "enable_async_save": self.enable_async_save,
            "enable_deduplication": self.enable_deduplication,
            "dedup_cache_size": self.dedup_cache_size,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "enable_metrics": self.enable_metrics,
            "metrics_retention_days": self.metrics_retention_days,
            "metrics_max_history_size": self.metrics_max_history_size,
            "default_capture_html": self.default_capture_html,
            "default_capture_screenshot": self.default_capture_screenshot,
            "default_capture_console": self.default_capture_console,
            "default_capture_network": self.default_capture_network,
            "cleanup_old_bundles_days": self.cleanup_old_bundles_days,
            "enable_auto_cleanup": self.enable_auto_cleanup,
            "environment_overrides": self.environment_overrides
        }


# Default settings instance
default_settings = SnapshotSettings()


def get_settings(environment: str = "production") -> SnapshotSettings:
    """Get settings for the specified environment."""
    return default_settings.get_environment_settings(environment)


def load_settings_from_file(config_path: str) -> SnapshotSettings:
    """Load settings from a JSON configuration file."""
    import json
    
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        return SnapshotSettings(**config_data)
        
    except FileNotFoundError:
        # Return default settings if file doesn't exist
        return default_settings
    except Exception as e:
        print(f"Error loading settings from {config_path}: {e}")
        return default_settings


def save_settings_to_file(settings: SnapshotSettings, config_path: str) -> bool:
    """Save settings to a JSON configuration file."""
    import json
    from .models import EnumEncoder
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(settings.to_dict(), f, indent=2, cls=EnumEncoder)
        
        return True
        
    except Exception as e:
        print(f"Error saving settings to {config_path}: {e}")
        return False


# Preset configurations for common use cases
def get_development_settings() -> SnapshotSettings:
    """Get settings optimized for development."""
    settings = SnapshotSettings()
    settings.enable_metrics = True
    settings.metrics_retention_days = 7
    settings.default_capture_screenshot = True
    settings.default_capture_console = True
    settings.default_capture_network = True
    settings.enable_auto_cleanup = False
    return settings


def get_testing_settings() -> SnapshotSettings:
    """Get settings optimized for testing."""
    settings = SnapshotSettings()
    settings.base_path = "test_data/snapshots"
    settings.enable_metrics = False
    settings.enable_async_save = False  # More predictable for testing
    settings.enable_deduplication = False  # More predictable for testing
    settings.rate_limit_per_minute = 100  # Higher limit for testing
    settings.enable_auto_cleanup = True
    settings.cleanup_old_bundles_days = 1
    return settings


def get_production_settings() -> SnapshotSettings:
    """Get settings optimized for production."""
    settings = SnapshotSettings()
    settings.enable_metrics = True
    settings.enable_async_save = True
    settings.enable_deduplication = True
    settings.default_capture_screenshot = False  # Reduce storage cost
    settings.default_capture_console = False  # Reduce storage cost
    settings.default_capture_network = False  # Reduce storage cost
    settings.enable_auto_cleanup = True
    settings.cleanup_old_bundles_days = 90
    return settings
