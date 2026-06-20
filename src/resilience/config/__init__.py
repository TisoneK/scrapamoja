"""
Resilience Configuration Management

Central configuration management for all resilience components including
checkpointing, retry mechanisms, resource monitoring, and abort policies.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import os
import json
from pathlib import Path


@dataclass
class CheckpointConfiguration:
    """Configuration for checkpointing system."""
    enabled: bool = True
    interval: int = 300  # Checkpoint interval in seconds
    retention_count: int = 10  # Number of checkpoints to retain
    compression_enabled: bool = True  # Enable gzip compression
    encryption_enabled: bool = True  # Enable encryption for sensitive data
    storage_path: str = "./data/checkpoints"  # Checkpoint storage directory
    validation_enabled: bool = True  # Enable checksum validation


@dataclass
class RetryConfiguration:
    """Configuration for retry mechanisms."""
    enabled: bool = True
    default_policy: str = "exponential_backoff"  # Default retry policy ID
    max_concurrent_retries: int = 5  # Maximum concurrent retry operations
    jitter_enabled: bool = True  # Enable jitter in backoff calculations
    failure_classification_enabled: bool = True  # Enable failure classification


@dataclass
class ResourceConfiguration:
    """Configuration for resource monitoring."""
    enabled: bool = True
    monitoring_interval: int = 30  # Monitoring interval in seconds
    default_threshold: str = "production"  # Default resource threshold ID
    auto_cleanup_enabled: bool = True  # Enable automatic cleanup
    browser_restart_enabled: bool = True  # Enable automatic browser restart
    memory_limit_mb: int = 2048  # Memory limit in MB
    cpu_limit_percent: float = 80.0  # CPU limit percentage


@dataclass
class AbortConfiguration:
    """Configuration for abort policies."""
    enabled: bool = True
    default_policy: str = "conservative"  # Default abort policy ID
    evaluation_interval: int = 60  # Evaluation interval in seconds
    min_operations_before_eval: int = 10  # Minimum operations before evaluation
    abort_notification_enabled: bool = True  # Enable abort notifications


@dataclass
class LoggingConfiguration:
    """Configuration for resilience logging."""
    enabled: bool = True
    level: str = "INFO"  # Logging level
    correlation_ids_enabled: bool = True  # Enable correlation ID tracking
    structured_format: bool = True  # Use structured JSON logging
    include_stack_traces: bool = True  # Include stack traces in error logs


@dataclass
class ResilienceConfiguration:
    """Main configuration structure for resilience features."""
    checkpoint: CheckpointConfiguration = field(default_factory=CheckpointConfiguration)
    retry: RetryConfiguration = field(default_factory=RetryConfiguration)
    resource: ResourceConfiguration = field(default_factory=ResourceConfiguration)
    abort: AbortConfiguration = field(default_factory=AbortConfiguration)
    logging: LoggingConfiguration = field(default_factory=LoggingConfiguration)


class ConfigurationLoader:
    """Loads and manages resilience configuration from files and environment."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv("RESILIENCE_CONFIG_PATH", "./resilience_config.json")
        self._config: Optional[ResilienceConfiguration] = None
    
    def load_configuration(self) -> ResilienceConfiguration:
        """Load configuration from file or create default."""
        if self._config is not None:
            return self._config
        
        # Try to load from file
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                self._config = self._parse_configuration(config_data)
            except Exception as e:
                # Fall back to default configuration if file loading fails
                self._config = ResilienceConfiguration()
        else:
            # Create default configuration
            self._config = ResilienceConfiguration()
            # Save default configuration to file
            self.save_configuration(self._config)
        
        return self._config
    
    def save_configuration(self, config: ResilienceConfiguration) -> None:
        """Save configuration to file."""
        config_data = self._serialize_configuration(config)
        
        # Ensure directory exists
        config_path = Path(self.config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def _parse_configuration(self, config_data: Dict[str, Any]) -> ResilienceConfiguration:
        """Parse configuration dictionary into ResilienceConfiguration object."""
        checkpoint_config = CheckpointConfiguration(**config_data.get('checkpoint', {}))
        retry_config = RetryConfiguration(**config_data.get('retry', {}))
        resource_config = ResourceConfiguration(**config_data.get('resource', {}))
        abort_config = AbortConfiguration(**config_data.get('abort', {}))
        logging_config = LoggingConfiguration(**config_data.get('logging', {}))
        
        return ResilienceConfiguration(
            checkpoint=checkpoint_config,
            retry=retry_config,
            resource=resource_config,
            abort=abort_config,
            logging=logging_config
        )
    
    def _serialize_configuration(self, config: ResilienceConfiguration) -> Dict[str, Any]:
        """Serialize ResilienceConfiguration object to dictionary."""
        return {
            'checkpoint': {
                'enabled': config.checkpoint.enabled,
                'interval': config.checkpoint.interval,
                'retention_count': config.checkpoint.retention_count,
                'compression_enabled': config.checkpoint.compression_enabled,
                'encryption_enabled': config.checkpoint.encryption_enabled,
                'storage_path': config.checkpoint.storage_path,
                'validation_enabled': config.checkpoint.validation_enabled,
            },
            'retry': {
                'enabled': config.retry.enabled,
                'default_policy': config.retry.default_policy,
                'max_concurrent_retries': config.retry.max_concurrent_retries,
                'jitter_enabled': config.retry.jitter_enabled,
                'failure_classification_enabled': config.retry.failure_classification_enabled,
            },
            'resource': {
                'enabled': config.resource.enabled,
                'monitoring_interval': config.resource.monitoring_interval,
                'default_threshold': config.resource.default_threshold,
                'auto_cleanup_enabled': config.resource.auto_cleanup_enabled,
                'browser_restart_enabled': config.resource.browser_restart_enabled,
                'memory_limit_mb': config.resource.memory_limit_mb,
                'cpu_limit_percent': config.resource.cpu_limit_percent,
            },
            'abort': {
                'enabled': config.abort.enabled,
                'default_policy': config.abort.default_policy,
                'evaluation_interval': config.abort.evaluation_interval,
                'min_operations_before_eval': config.abort.min_operations_before_eval,
                'abort_notification_enabled': config.abort.abort_notification_enabled,
            },
            'logging': {
                'enabled': config.logging.enabled,
                'level': config.logging.level,
                'correlation_ids_enabled': config.logging.correlation_ids_enabled,
                'structured_format': config.logging.structured_format,
                'include_stack_traces': config.logging.include_stack_traces,
            }
        }


# Global configuration loader instance
_config_loader = ConfigurationLoader()


def get_configuration() -> ResilienceConfiguration:
    """Get the global resilience configuration."""
    return _config_loader.load_configuration()


def reload_configuration() -> ResilienceConfiguration:
    """Reload the global resilience configuration from file."""
    global _config_loader
    _config_loader = ConfigurationLoader()
    return _config_loader.load_configuration()


def update_configuration(updates: Dict[str, Any]) -> None:
    """Update specific configuration values."""
    config = get_configuration()
    
    # Apply updates to configuration
    if 'checkpoint' in updates:
        for key, value in updates['checkpoint'].items():
            if hasattr(config.checkpoint, key):
                setattr(config.checkpoint, key, value)
    
    if 'retry' in updates:
        for key, value in updates['retry'].items():
            if hasattr(config.retry, key):
                setattr(config.retry, key, value)
    
    if 'resource' in updates:
        for key, value in updates['resource'].items():
            if hasattr(config.resource, key):
                setattr(config.resource, key, value)
    
    if 'abort' in updates:
        for key, value in updates['abort'].items():
            if hasattr(config.abort, key):
                setattr(config.abort, key, value)
    
    if 'logging' in updates:
        for key, value in updates['logging'].items():
            if hasattr(config.logging, key):
                setattr(config.logging, key, value)
    
    # Save updated configuration
    _config_loader.save_configuration(config)
