"""
Retry Configuration Manager

Manages centralized retry configuration with validation, loading, and hot-reload support.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime

import yaml
from pydantic import BaseModel, Field, validator, ValidationError

from ..logging.resilience_logger import get_logger
from ..exceptions import RetryConfigurationError


logger = get_logger("retry_config")


class RetryPolicyConfig(BaseModel):
    """Retry policy configuration model."""
    
    id: str = Field(..., description="Unique identifier for retry policy")
    name: str = Field(..., description="Human-readable name for policy")
    description: Optional[str] = Field(None, description="Description of when and why to use this policy")
    max_attempts: int = Field(..., gt=0, description="Maximum number of retry attempts")
    backoff_type: str = Field(..., description="Type of backoff strategy")
    base_delay: float = Field(..., ge=0.0, description="Base delay in seconds")
    max_delay: float = Field(..., ge=0.0, description="Maximum delay in seconds")
    jitter_type: Optional[str] = Field("none", description="Type of jitter to apply")
    jitter_amount: Optional[float] = Field(0.1, ge=0.0, le=1.0, description="Amount of jitter to apply")
    enable_circuit_breaker: Optional[bool] = Field(False, description="Whether to enable circuit breaker")
    circuit_breaker_threshold: Optional[int] = Field(None, gt=0, description="Number of failures before opening circuit")
    circuit_breaker_timeout: Optional[float] = Field(None, gt=0.0, description="Time in seconds before attempting to close circuit")
    retryable_exceptions: Optional[List[str]] = Field(None, description="List of exception types that should trigger retry")
    enabled: bool = Field(True, description="Whether policy is active")
    
    @validator('backoff_type')
    def validate_backoff_type(cls, v):
        """Validate backoff type is one of the allowed values."""
        allowed_types = ['exponential', 'linear', 'fixed', 'immediate']
        if v not in allowed_types:
            raise ValueError(f"backoff_type must be one of {allowed_types}, got '{v}'")
        return v
    
    @validator('jitter_type')
    def validate_jitter_type(cls, v):
        """Validate jitter type is one of the allowed values."""
        if v is None:
            return v
        allowed_types = ['none', 'full', 'decorrelated', 'equal']
        if v not in allowed_types:
            raise ValueError(f"jitter_type must be one of {allowed_types}, got '{v}'")
        return v
    
    @validator('max_delay')
    def validate_max_delay(cls, v, values):
        """Validate max_delay is greater than or equal to base_delay."""
        if 'base_delay' in values and v < values['base_delay']:
            raise ValueError(f"max_delay ({v}) must be greater than or equal to base_delay ({values['base_delay']})")
        return v


class GlobalDefaultsConfig(BaseModel):
    """Global defaults configuration model."""
    
    jitter_type: Optional[str] = Field("none", description="Default jitter type")
    jitter_amount: Optional[float] = Field(0.1, ge=0.0, le=1.0, description="Default jitter amount")
    enable_circuit_breaker: Optional[bool] = Field(False, description="Default circuit breaker enabled")


class SubsystemMappingsConfig(BaseModel):
    """Subsystem mappings configuration model."""
    
    browser: Optional[Dict[str, Any]] = Field(None, description="Browser subsystem mappings")
    navigation: Optional[Dict[str, Any]] = Field(None, description="Navigation subsystem mappings")
    telemetry: Optional[Dict[str, Any]] = Field(None, description="Telemetry subsystem mappings")


class RetryConfiguration(BaseModel):
    """Complete retry configuration model."""
    
    version: str = Field(..., description="Configuration schema version")
    global_defaults: Optional[GlobalDefaultsConfig] = Field(None, description="Global defaults applied to all policies")
    policies: Dict[str, RetryPolicyConfig] = Field(default_factory=dict, description="Retry policies")
    subsystem_mappings: Optional[SubsystemMappingsConfig] = Field(None, description="Subsystem mappings to policy IDs")
    
    @validator('version')
    def validate_version(cls, v):
        """Validate configuration version."""
        # Simple version validation - can be enhanced later
        if not v or not isinstance(v, str):
            raise ValueError("version must be a non-empty string")
        return v


@dataclass
class ConfigChange:
    """Represents a configuration change event."""
    
    timestamp: datetime = field(default_factory=datetime.utcnow)
    old_config: Optional[Dict[str, Any]] = None
    new_config: Optional[Dict[str, Any]] = None
    change_type: str = "unknown"  # 'added', 'modified', 'removed', 'reloaded'


class RetryConfigManager:
    """Manages retry configuration with loading, validation, and hot-reload support."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize retry configuration manager.
        
        Args:
            config_path: Path to configuration file. If None, uses default path.
        """
        self.config_path = Path(config_path) if config_path else self._get_default_config_path()
        self._config: Optional[RetryConfiguration] = None
        self._change_callbacks: List[Callable[[ConfigChange], None]] = []
        self._watcher_task: Optional[asyncio.Task] = None
        self._last_modified: Optional[float] = None
        self._debounce_delay: float = 1.0  # Debounce file changes within 1 second
        
        logger.info(
            "Retry config manager initialized",
            config_path=str(self.config_path),
            component="retry_config_manager"
        )
    
    def _get_default_config_path(self) -> Path:
        """Get default configuration file path."""
        # Default to src/config/retry_config.yaml relative to repository root
        repo_root = Path(__file__).parent.parent.parent.parent
        return repo_root / "src" / "config" / "retry_config.yaml"
    
    async def load_config(self) -> RetryConfiguration:
        """
        Load retry configuration from file.
        
        Returns:
            Validated retry configuration
            
        Raises:
            RetryConfigurationError: If configuration is invalid or cannot be loaded
        """
        try:
            logger.info(
                "Loading retry configuration",
                config_path=str(self.config_path),
                component="retry_config_manager"
            )
            
            if not self.config_path.exists():
                raise RetryConfigurationError(
                    f"Configuration file not found: {self.config_path}",
                    context={"config_path": str(self.config_path)}
                )
            
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Validate configuration
            config = RetryConfiguration(**config_data)
            
            # Apply global defaults to policies
            if config.global_defaults:
                self._apply_global_defaults(config)
            
            self._config = config
            
            logger.info(
                "Retry configuration loaded successfully",
                version=config.version,
                policies_count=len(config.policies),
                component="retry_config_manager"
            )
            
            return config
            
        except yaml.YAMLError as e:
            raise RetryConfigurationError(
                f"Failed to parse YAML configuration: {e}",
                context={"config_path": str(self.config_path), "error": str(e)}
            )
        except ValidationError as e:
            raise RetryConfigurationError(
                f"Configuration validation failed: {e}",
                context={"config_path": str(self.config_path), "validation_errors": str(e)}
            )
        except Exception as e:
            raise RetryConfigurationError(
                f"Failed to load configuration: {e}",
                context={"config_path": str(self.config.path), "error": str(e)}
            )
    
    def _apply_global_defaults(self, config: RetryConfiguration) -> None:
        """Apply global defaults to policies that don't specify them."""
        if not config.global_defaults:
            return
        
        for policy_id, policy in config.policies.items():
            # Apply jitter defaults
            if policy.jitter_type is None and config.global_defaults.jitter_type:
                policy.jitter_type = config.global_defaults.jitter_type
            if policy.jitter_amount is None and config.global_defaults.jitter_amount is not None:
                policy.jitter_amount = config.global_defaults.jitter_amount
            
            # Apply circuit breaker defaults
            if policy.enable_circuit_breaker is None and config.global_defaults.enable_circuit_breaker is not None:
                policy.enable_circuit_breaker = config.global_defaults.enable_circuit_breaker
    
    async def reload_config(self) -> None:
        """
        Reload configuration from file.
        
        Raises:
            RetryConfigurationError: If configuration is invalid
        """
        logger.info(
            "Reloading retry configuration",
            config_path=str(self.config_path),
            component="retry_config_manager"
        )
        
        old_config = self._config
        new_config = await self.load_config()
        
        # Notify callbacks of configuration change
        change = ConfigChange(
            timestamp=datetime.utcnow(),
            old_config=old_config.dict() if old_config else None,
            new_config=new_config.dict(),
            change_type="reloaded"
        )
        
        await self._notify_change_callbacks(change)
        
        logger.info(
            "Retry configuration reloaded successfully",
            version=new_config.version,
            component="retry_config_manager"
        )
    
    async def watch_config(self, callback: Optional[Callable[[ConfigChange], None]] = None) -> None:
        """
        Watch configuration file for changes and trigger callback.
        
        Args:
            callback: Callback function to invoke on changes
            
        Raises:
            RetryConfigurationError: If file watching cannot be started
        """
        if callback:
            self._change_callbacks.append(callback)
        
        # Start watching task
        self._watcher_task = asyncio.create_task(self._watch_config_loop())
        
        logger.info(
            "Configuration file watching started",
            config_path=str(self.config_path),
            component="retry_config_manager"
        )
    
    async def _watch_config_loop(self) -> None:
        """Watch configuration file for changes."""
        while True:
            try:
                # Check if file exists and get modification time
                if self.config_path.exists():
                    current_modified = self.config_path.stat().st_mtime
                    
                    # Check if file was modified (with debounce)
                    if self._last_modified is None or \
                       (current_modified - self._last_modified) >= self._debounce_delay:
                        
                        # File was modified, reload configuration
                        logger.info(
                            "Configuration file modified, reloading",
                            config_path=str(self.config_path),
                            component="retry_config_manager"
                        )
                        
                        await self.reload_config()
                        self._last_modified = current_modified
                
                # Wait before checking again
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                logger.info(
                    "Configuration file watching stopped",
                    component="retry_config_manager"
                )
                break
            except Exception as e:
                logger.error(
                    f"Error watching configuration file: {e}",
                    config_path=str(self.config_path),
                    component="retry_config_manager"
                )
                await asyncio.sleep(5.0)  # Wait before retrying
    
    async def _notify_change_callbacks(self, change: ConfigChange) -> None:
        """Notify all registered callbacks of configuration change."""
        for callback in self._change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(change)
                else:
                    callback(change)
            except Exception as e:
                logger.error(
                    f"Error in configuration change callback: {e}",
                    component="retry_config_manager"
                )
    
    def register_change_callback(self, callback: Callable[[ConfigChange], None]) -> None:
        """
        Register a callback to be invoked on configuration changes.
        
        Args:
            callback: Callback function to invoke on changes
        """
        self._change_callbacks.append(callback)
        logger.info(
            "Configuration change callback registered",
            callbacks_count=len(self._change_callbacks),
            component="retry_config_manager"
        )
    
    async def stop_watching(self) -> None:
        """Stop watching configuration file."""
        if self._watcher_task and not self._watcher_task.done():
            self._watcher_task.cancel()
            try:
                await self._watcher_task
            except asyncio.CancelledError:
                pass
            
            logger.info(
                "Configuration file watching stopped",
                component="retry_config_manager"
            )
    
    @property
    def config(self) -> Optional[RetryConfiguration]:
        """Get current configuration."""
        return self._config
    
    @property
    def policies(self) -> Dict[str, RetryPolicyConfig]:
        """Get all retry policies."""
        return self._config.policies if self._config else {}
    
    @property
    def subsystem_mappings(self) -> Optional[SubsystemMappingsConfig]:
        """Get subsystem mappings."""
        return self._config.subsystem_mappings if self._config else None
    
    def get_policy(self, policy_id: str) -> Optional[RetryPolicyConfig]:
        """
        Get a specific retry policy by ID.
        
        Args:
            policy_id: ID of retry policy
            
        Returns:
            Retry policy configuration or None if not found
        """
        return self._config.policies.get(policy_id) if self._config else None
    
    def get_subsystem_policy(self, subsystem: str, operation: str) -> Optional[str]:
        """
        Get retry policy ID for a subsystem operation.
        
        Args:
            subsystem: Subsystem name (browser, navigation, telemetry)
            operation: Operation name within subsystem
            
        Returns:
            Policy ID or None if not found
        """
        if not self._config or not self._config.subsystem_mappings:
            return None
        
        subsystem_mappings = getattr(self._config.subsystem_mappings, subsystem, None)
        if not subsystem_mappings:
            return None
        
        return subsystem_mappings.get(operation)
    
    async def shutdown(self) -> None:
        """Shutdown configuration manager gracefully."""
        await self.stop_watching()
        
        logger.info(
            "Retry config manager shutdown",
            component="retry_config_manager"
        )


# Global configuration manager instance
_config_manager: Optional[RetryConfigManager] = None


async def get_config_manager(config_path: Optional[str] = None) -> RetryConfigManager:
    """
    Get or create the global retry configuration manager.
    
    Args:
        config_path: Path to configuration file. If None, uses default path.
        
    Returns:
        Retry configuration manager instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = RetryConfigManager(config_path)
        await _config_manager.load_config()
    
    return _config_manager


async def reload_config() -> None:
    """
    Reload the global retry configuration.
    
    Raises:
        RetryConfigurationError: If configuration is invalid
    """
    global _config_manager
    
    if _config_manager is None:
        raise RetryConfigurationError(
            "Configuration manager not initialized. Call get_config_manager() first.",
            context={}
        )
    
    await _config_manager.reload_config()


async def watch_config(callback: Optional[Callable[[ConfigChange], None]] = None) -> None:
    """
    Watch the global retry configuration for changes.
    
    Args:
        callback: Callback function to invoke on changes
    """
    global _config_manager
    
    if _config_manager is None:
        raise RetryConfigurationError(
            "Configuration manager not initialized. Call get_config_manager() first.",
            context={}
        )
    
    await _config_manager.watch_config(callback)
