"""
Storage Configuration Management for Selector Telemetry System

This module provides comprehensive storage configuration capabilities including
storage settings, retention policies, backup configurations, and
storage tier management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import json
from pathlib import Path

from ..models.selector_models import SeverityLevel
from ..storage.retention_manager import RetentionPolicy, RetentionAction
from ..storage.tiered_storage import StorageTier, TieringPolicy
from ..storage.backup import BackupType, BackupPolicy
from .logging import get_storage_logger


class StorageConfigType(Enum):
    """Types of storage configurations"""
    GENERAL = "general"
    RETENTION = "retention"
    BACKUP = "backup"
    TIERED_STORAGE = "tiered_storage"
    MONITORING = "monitoring"
    OPTIMIZATION = "optimization"
    INTEGRITY = "integrity"


@dataclass
class StorageConfig:
    """Storage configuration data"""
    config_id: str
    config_type: StorageConfigType
    name: str
    description: str
    settings: Dict[str, Any]
    enabled: bool = True
    created_at: datetime = None
    updated_at: Optional[datetime] = None
    version: str = "1.0"


@dataclass
class StorageSettings:
    """General storage settings"""
    default_storage_path: str
    temp_storage_path: str
    log_storage_path: str
    backup_storage_path: str
    archive_storage_path: str
    max_storage_gb: int
    cleanup_interval_hours: int
    compression_enabled: bool
    encryption_enabled: bool
    monitoring_enabled: bool


class StorageConfigManager:
    """
    Comprehensive storage configuration management system
    
    This class provides storage configuration capabilities:
    - Configuration creation and management
    - Settings validation and persistence
    - Configuration versioning
    - Environment-specific configurations
    - Configuration templates
    """
    
    def __init__(
        self,
        logger=None,
        config_path: Optional[str] = None
    ):
        """Initialize the storage configuration manager"""
        self.logger = logger or get_storage_logger()
        self.config_path = Path(config_path or "config/storage_config.json")
        
        # Configuration storage
        self._configs = {}
        self._config_lock = asyncio.Lock()
        
        # Default settings
        self._default_settings = StorageSettings(
            default_storage_path="/data/telemetry",
            temp_storage_path="/tmp/telemetry",
            log_storage_path="/data/telemetry/logs",
            backup_storage_path="/data/telemetry/backups",
            archive_storage_path="/data/telemetry/archive",
            max_storage_gb=10000,
            cleanup_interval_hours=24,
            compression_enabled=True,
            encryption_enabled=True,
            monitoring_enabled=True
        )
        
        # Configuration statistics
        self._stats = {
            "total_configs": 0,
            "active_configs": 0,
            "config_updates": 0,
            "last_update": None
        }
        
        # Initialize configuration directory
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing configurations
        asyncio.create_task(self._load_configurations())
    
    async def create_config(
        self,
        name: str,
        description: str,
        config_type: StorageConfigType,
        settings: Dict[str, Any],
        enabled: bool = True
    ) -> str:
        """
        Create a new storage configuration
        
        Args:
            name: Configuration name
            description: Configuration description
            config_type: Type of configuration
            settings: Configuration settings
            enabled: Whether configuration is initially enabled
            
        Returns:
            str: Configuration ID
        """
        config_id = str(uuid.uuid4())
        
        # Validate configuration
        await self._validate_config(config_type, settings)
        
        # Create configuration
        config = StorageConfig(
            config_id=config_id,
            config_type=config_type,
            name=name,
            description=description,
            settings=settings,
            enabled=enabled,
            created_at=datetime.now(),
            version="1.0"
        )
        
        async with self._config_lock:
            self._configs[config_id] = config
            
            # Update statistics
            self._stats["total_configs"] += 1
            if enabled:
                self._stats["active_configs"] += 1
        
        # Save configuration
        await self._save_configurations()
        
        self.logger.info(
            f"Created storage configuration {config_id}: {name}",
            config_id=config_id,
            config_type=config_type.value
        )
        
        return config_id
    
    async def update_config(self, config_id: str, **updates) -> bool:
        """Update an existing storage configuration"""
        async with self._config_lock:
            config = self._configs.get(config_id)
            if not config:
                return False
            
            old_enabled = config.enabled
            old_settings = config.settings.copy()
            
            # Update configuration
            for key, value in updates.items():
                if key == "settings":
                    # Validate new settings
                    await self._validate_config(config.config_type, value)
                    config.settings = value
                elif hasattr(config, key):
                    setattr(config, key, value)
            
            # Update version and timestamp
            config.updated_at = datetime.now()
            
            # Update statistics if enabled status changed
            if old_enabled != config.enabled:
                if config.enabled:
                    self._stats["active_configs"] += 1
                else:
                    self._stats["active_configs"] -= 1
            
            self._stats["config_updates"] += 1
            self._stats["last_update"] = config.updated_at
        
        # Save configuration
        await self._save_configurations()
        
        self.logger.info(f"Updated storage configuration {config_id}")
        return True
    
    async def delete_config(self, config_id: str) -> bool:
        """Delete a storage configuration"""
        async with self._config_lock:
            if config_id not in self._configs:
                return False
            
            config = self._configs[config_id]
            
            # Update statistics
            if config.enabled:
                self._stats["active_configs"] -= 1
            
            del self._configs[config_id]
            self._stats["total_configs"] -= 1
        
        # Save configuration
        await self._save_configurations()
        
        self.logger.info(f"Deleted storage configuration {config_id}")
        return True
    
    async def enable_config(self, config_id: str) -> bool:
        """Enable a storage configuration"""
        return await self.update_config(config_id, enabled=True)
    
    async def disable_config(self, config_id: str) -> bool:
        """Disable a storage configuration"""
        return await self.update_config(config_id, enabled=False)
    
    async def get_config(self, config_id: str) -> Optional[StorageConfig]:
        """Get a storage configuration"""
        async with self._config_lock:
            return self._configs.get(config_id)
    
    async def get_all_configs(self) -> List[StorageConfig]:
        """Get all storage configurations"""
        async with self._config_lock:
            return list(self._configs.values())
    
    async def get_configs_by_type(self, config_type: StorageConfigType) -> List[StorageConfig]:
        """Get configurations by type"""
        async with self._config_lock:
            return [c for c in self._configs.values() if c.config_type == config_type]
    
    async def get_active_configs(self) -> List[StorageConfig]:
        """Get active storage configurations"""
        async with self._config_lock:
            return [c for c in self._configs.values() if c.enabled]
    
    async def create_retention_config(
        self,
        name: str,
        description: str,
        policies: List[Dict[str, Any]]
    ) -> str:
        """Create retention configuration"""
        settings = {
            "policies": policies,
            "default_retention_days": 30,
            "cleanup_interval_hours": 24,
            "auto_cleanup_enabled": True
        }
        
        return await self.create_config(
            name=name,
            description=description,
            config_type=StorageConfigType.RETENTION,
            settings=settings
        )
    
    async def create_backup_config(
        self,
        name: str,
        description: str,
        backup_policies: List[Dict[str, Any]]
    ) -> str:
        """Create backup configuration"""
        settings = {
            "backup_policies": backup_policies,
            "default_backup_type": "full",
            "backup_schedule": "0 2 * * *",  # Daily at 2 AM
            "retention_days": 30,
            "compression_enabled": True,
            "encryption_enabled": True,
            "verification_enabled": True
        }
        
        return await self.create_config(
            name=name,
            description=description,
            config_type=StorageConfigType.BACKUP,
            settings=settings
        )
    
    async def create_tiered_storage_config(
        self,
        name: str,
        description: str,
        tiers: List[Dict[str, Any]],
        tiering_rules: List[Dict[str, Any]]
    ) -> str:
        """Create tiered storage configuration"""
        settings = {
            "tiers": tiers,
            "tiering_rules": tiering_rules,
            "auto_tiering_enabled": True,
            "migration_check_interval_hours": 1
        }
        
        return await self.create_config(
            name=name,
            description=description,
            config_type=StorageConfigType.TIERED_STORAGE,
            settings=settings
        )
    
    async def apply_config(self, config_id: str) -> bool:
        """Apply a storage configuration to the system"""
        config = await self.get_config(config_id)
        if not config:
            raise ValueError(f"Configuration {config_id} not found")
        
        if not config.enabled:
            raise ValueError(f"Configuration {config_id} is disabled")
        
        try:
            self.logger.info(
                f"Applying storage configuration {config_id}: {config.name}",
                config_id=config_id
            )
            
            # Apply configuration based on type
            if config.config_type == StorageConfigType.GENERAL:
                await self._apply_general_settings(config.settings)
            elif config.config_type == StorageConfigType.RETENTION:
                await self._apply_retention_settings(config.settings)
            elif config.config_type == StorageConfigType.BACKUP:
                await self._apply_backup_settings(config.settings)
            elif config.config_type == StorageConfigType.TIERED_STORAGE:
                await self._apply_tiered_storage_settings(config.settings)
            elif config.config_type == StorageConfigType.MONITORING:
                await self._apply_monitoring_settings(config.settings)
            elif config.config_type == StorageConfigType.OPTIMIZATION:
                await self._apply_optimization_settings(config.settings)
            elif config.config_type == StorageConfigType.INTEGRITY:
                await self._apply_integrity_settings(config.settings)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying configuration {config_id}: {e}")
            return False
    
    async def export_config(self, config_id: str, output_path: str) -> bool:
        """Export a configuration to a file"""
        config = await self.get_config(config_id)
        if not config:
            return False
        
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Export configuration as JSON
            config_data = asdict(config)
            config_data['created_at'] = config.created_at.isoformat()
            config_data['updated_at'] = config.updated_at.isoformat() if config.updated_at else None
            
            with open(output_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            self.logger.info(f"Exported configuration {config_id} to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting configuration {config_id}: {e}")
            return False
    
    async def import_config(self, import_path: str) -> str:
        """Import a configuration from a file"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                raise FileNotFoundError(f"Import file not found: {import_path}")
            
            with open(import_file, 'r') as f:
                config_data = json.load(f)
            
            # Convert timestamps
            if config_data.get('created_at'):
                config_data['created_at'] = datetime.fromisoformat(config_data['created_at'])
            if config_data.get('updated_at'):
                config_data['updated_at'] = datetime.fromisoformat(config_data['updated_at'])
            
            # Create configuration object
            config = StorageConfig(**config_data)
            
            # Validate configuration
            await self._validate_config(config.config_type, config.settings)
            
            # Store configuration
            async with self._config_lock:
                self._configs[config.config_id] = config
                self._stats["total_configs"] += 1
                if config.enabled:
                    self._stats["active_configs"] += 1
            
            # Save all configurations
            await self._save_configurations()
            
            self.logger.info(f"Imported configuration {config.config_id} from {import_path}")
            return config.config_id
            
        except Exception as e:
            self.logger.error(f"Error importing configuration from {import_path}: {e}")
            raise
    
    async def get_config_statistics(self) -> Dict[str, Any]:
        """Get configuration management statistics"""
        async with self._config_lock:
            active_configs = len([c for c in self._configs.values() if c.enabled])
        
        return {
            **self._stats,
            "active_configs": active_configs,
            "config_file_path": str(self.config_path)
        }
    
    # Private methods
    
    async def _validate_config(self, config_type: StorageConfigType, settings: Dict[str, Any]) -> None:
        """Validate configuration settings"""
        if config_type == StorageConfigType.GENERAL:
            required_fields = ["default_storage_path"]
            for field in required_fields:
                if field not in settings:
                    raise ValueError(f"Required field '{field}' missing from general settings")
        
        elif config_type == StorageConfigType.RETENTION:
            if "policies" not in settings:
                raise ValueError("Retention policies are required")
            
            # Validate retention policies
            for policy in settings["policies"]:
                if "policy_type" not in policy:
                    raise ValueError("Policy type is required for retention policy")
                if "retention_period" not in policy and "max_size_mb" not in policy and "max_count" not in policy:
                    raise ValueError("Retention period, max_size_mb, or max_count is required")
        
        elif config_type == StorageConfigType.BACKUP:
            if "backup_policies" not in settings:
                raise ValueError("Backup policies are required")
        
        elif config_type == StorageConfigType.TIERED_STORAGE:
            if "tiers" not in settings:
                raise ValueError("Storage tiers are required")
    
    async def _apply_general_settings(self, settings: Dict[str, Any]) -> None:
        """Apply general storage settings"""
        # Mock implementation - would apply to actual storage system
        self.logger.info("Applied general storage settings")
    
    async def _apply_retention_settings(self, settings: Dict[str, Any]) -> None:
        """Apply retention settings"""
        # Mock implementation - would configure retention manager
        self.logger.info("Applied retention settings")
    
    async def _apply_backup_settings(self, settings: Dict[str, Any]) -> None:
        """Apply backup settings"""
        # Mock implementation - would configure backup system
        self.logger.info("Applied backup settings")
    
    async def _apply_tiered_storage_settings(self, settings: Dict[str, Any]) -> None:
        """Apply tiered storage settings"""
        # Mock implementation - would configure tiered storage
        self.logger.info("Applied tiered storage settings")
    
    async def _apply_monitoring_settings(self, settings: Dict[str, Any]) -> None:
        """Apply monitoring settings"""
        # Mock implementation - would configure monitoring system
        self.logger.info("Applied monitoring settings")
    
    async def _apply_optimization_settings(self, settings: Dict[str, Any]) -> None:
        """Apply optimization settings"""
        # Mock implementation - would configure optimization system
        self.logger.info("Applied optimization settings")
    
    async def _apply_integrity_settings(self, settings: Dict[str, Any]) -> None:
        """Apply integrity settings"""
        # Mock implementation - would configure integrity checking
        self.logger.info("Applied integrity settings")
    
    async def _load_configurations(self) -> None:
        """Load configurations from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                
                for config_data in data.get("configurations", []):
                    # Convert timestamps
                    if config_data.get("created_at"):
                        config_data["created_at"] = datetime.fromisoformat(config_data["created_at"])
                    if config_data.get("updated_at"):
                        config_data["updated_at"] = datetime.fromisoformat(config_data["updated_at"])
                    
                    # Create configuration object
                    config = StorageConfig(**config_data)
                    self._configs[config.config_id] = config
                    
                    # Update statistics
                    self._stats["total_configs"] += 1
                    if config.enabled:
                        self._stats["active_configs"] += 1
                
                self.logger.info(f"Loaded {len(self._configs)} storage configurations")
        
        except Exception as e:
            self.logger.error(f"Error loading configurations: {e}")
    
    async def _save_configurations(self) -> None:
        """Save configurations to file"""
        try:
            config_data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "configurations": []
            }
            
            # Add configurations
            for config in self._configs.values():
                config_dict = asdict(config)
                config_dict["created_at"] = config.created_at.isoformat()
                config_dict["updated_at"] = config.updated_at.isoformat() if config.updated_at else None
                config_data["configurations"].append(config_dict)
            
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
        except Exception as e:
            self.logger.error(f"Error saving configurations: {e}")
