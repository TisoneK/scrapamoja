"""
Telemetry Configuration Interface

Abstract interface for telemetry system configuration management
following the contract specification.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class ITelemetryConfiguration(ABC):
    """
    Interface for telemetry system configuration management.
    
    This interface defines the contract for configuration management,
    including settings, thresholds, and runtime configuration.
    """
    
    @abstractmethod
    async def get_configuration(self) -> Dict[str, Any]:
        """
        Get current telemetry configuration.
        
        Returns:
            Current configuration dictionary
        """
        pass
    
    @abstractmethod
    async def update_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Update telemetry configuration.
        
        Args:
            config: New configuration values
            
        Returns:
            True if successfully updated, False otherwise
            
        Raises:
            TelemetryConfigurationError: If update fails
        """
        pass
    
    @abstractmethod
    async def reset_configuration(self) -> bool:
        """
        Reset configuration to defaults.
        
        Returns:
            True if successfully reset, False otherwise
            
        Raises:
            TelemetryConfigurationError: If reset fails
        """
        pass
    
    @abstractmethod
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration setting.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        pass
    
    @abstractmethod
    async def set_setting(self, key: str, value: Any) -> bool:
        """
        Set a specific configuration setting.
        
        Args:
            key: Configuration key
            value: Configuration value
            
        Returns:
            True if successfully set, False otherwise
            
        Raises:
            TelemetryConfigurationError: If setting fails
        """
        pass
    
    @abstractmethod
    async def delete_setting(self, key: str) -> bool:
        """
        Delete a configuration setting.
        
        Args:
            key: Configuration key
            
        Returns:
            True if successfully deleted, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_collection_settings(self) -> Dict[str, Any]:
        """
        Get collection-specific settings.
        
        Returns:
            Collection configuration
        """
        pass
    
    @abstractmethod
    async def get_storage_settings(self) -> Dict[str, Any]:
        """
        Get storage-specific settings.
        
        Returns:
            Storage configuration
        """
        pass
    
    @abstractmethod
    async def get_processing_settings(self) -> Dict[str, Any]:
        """
        Get processing-specific settings.
        
        Returns:
            Processing configuration
        """
        pass
    
    @abstractmethod
    async def get_alerting_settings(self) -> Dict[str, Any]:
        """
        Get alerting-specific settings.
        
        Returns:
            Alerting configuration
        """
        pass
    
    @abstractmethod
    async def get_reporting_settings(self) -> Dict[str, Any]:
        """
        Get reporting-specific settings.
        
        Returns:
            Reporting configuration
        """
        pass
    
    @abstractmethod
    async def validate_configuration(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration values.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        pass
    
    @abstractmethod
    async def export_configuration(self, format: str = "json") -> str:
        """
        Export current configuration.
        
        Args:
            format: Export format (json, yaml)
            
        Returns:
            Exported configuration string
            
        Raises:
            TelemetryConfigurationError: If export fails
        """
        pass
    
    @abstractmethod
    async def import_configuration(self, config_data: str, format: str = "json") -> bool:
        """
        Import configuration.
        
        Args:
            config_data: Configuration data
            format: Import format (json, yaml)
            
        Returns:
            True if successfully imported, False otherwise
            
        Raises:
            TelemetryConfigurationError: If import fails
        """
        pass
    
    @abstractmethod
    async def backup_configuration(self, backup_path: str) -> bool:
        """
        Backup current configuration.
        
        Args:
            backup_path: Path for backup file
            
        Returns:
            True if backup successful
            
        Raises:
            TelemetryConfigurationError: If backup fails
        """
        pass
    
    @abstractmethod
    async def restore_configuration(self, backup_path: str) -> bool:
        """
        Restore configuration from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if restore successful
            
        Raises:
            TelemetryConfigurationError: If restore fails
        """
        pass
    
    @abstractmethod
    async def get_configuration_history(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get configuration change history.
        
        Args:
            limit: Optional limit on number of changes
            
        Returns:
            List of configuration changes
        """
        pass
    
    @abstractmethod
    async def rollback_configuration(self, version: str) -> bool:
        """
        Rollback configuration to previous version.
        
        Args:
            version: Configuration version to rollback to
            
        Returns:
            True if successfully rolled back, False otherwise
            
        Raises:
            TelemetryConfigurationError: If rollback fails
        """
        pass
    
    @abstractmethod
    async def get_environment_overrides(self) -> Dict[str, Any]:
        """
        Get environment variable overrides.
        
        Returns:
            Environment overrides dictionary
        """
        pass
    
    @abstractmethod
    async def apply_environment_overrides(self) -> None:
        """
        Apply environment variable overrides.
        
        Raises:
            TelemetryConfigurationError: If application fails
        """
        pass
    
    @abstractmethod
    async def reload_configuration(self) -> bool:
        """
        Reload configuration from source.
        
        Returns:
            True if successfully reloaded, False otherwise
            
        Raises:
            TelemetryConfigurationError: If reload fails
        """
        pass
    
    @abstractmethod
    async def is_configuration_valid(self) -> bool:
        """
        Check if current configuration is valid.
        
        Returns:
            True if configuration is valid
        """
        pass
    
    @abstractmethod
    async def get_configuration_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema.
        
        Returns:
            Configuration schema dictionary
        """
        pass
    
    @abstractmethod
    async def get_default_configuration(self) -> Dict[str, Any]:
        """
        Get default configuration.
        
        Returns:
            Default configuration dictionary
        """
        pass
    
    @abstractmethod
    async def merge_configuration(
        self,
        base_config: Dict[str, Any],
        override_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge configuration dictionaries.
        
        Args:
            base_config: Base configuration
            override_config: Override configuration
            
        Returns:
            Merged configuration
        """
        pass
    
    @abstractmethod
    async def watch_configuration_changes(self, callback) -> None:
        """
        Watch for configuration changes.
        
        Args:
            callback: Callback function for changes
        """
        pass
    
    @abstractmethod
    async def stop_watching_configuration(self) -> None:
        """
        Stop watching configuration changes.
        """
        pass
