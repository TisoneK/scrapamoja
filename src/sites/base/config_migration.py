"""
Configuration migration support for the scraper framework.

This module provides comprehensive configuration migration capabilities, including
version management, schema migrations, and rollback functionality.
"""

import json
import yaml
from typing import Dict, Any, List, Optional, Callable, Type, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import shutil

from .config_schemas import get_schema, validate_config_by_schema
from .config_validator import validate_config
from .config_io import ConfigIO, ExportOptions, ImportOptions


class MigrationDirection(Enum):
    """Migration direction enumeration."""
    UP = "up"
    DOWN = "down"


class MigrationStatus(Enum):
    """Migration status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationStep:
    """Single migration step."""
    version: str
    description: str
    up_migration: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    down_migration: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    dependencies: List[str] = field(default_factory=list)
    checksum: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    applied_at: Optional[datetime] = None
    status: MigrationStatus = MigrationStatus.PENDING


@dataclass
class MigrationResult:
    """Migration operation result."""
    success: bool
    from_version: str
    to_version: str
    direction: str
    applied_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    rollback_available: bool = False
    migration_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class MigrationPlan:
    """Migration execution plan."""
    from_version: str
    to_version: str
    steps: List[MigrationStep]
    estimated_time_ms: float = 0.0
    rollback_possible: bool = True
    dependencies_resolved: bool = True
    validation_required: bool = True


class ConfigMigration:
    """Configuration migration manager."""
    
    def __init__(self, config_io: Optional[ConfigIO] = None):
        """Initialize configuration migration manager."""
        self.config_io = config_io or ConfigIO()
        self._migrations: Dict[str, MigrationStep] = {}
        self._migration_history: List[MigrationResult] = []
        self._migration_registry: Dict[str, List[MigrationStep]] = {}
        
        # Migration settings
        self._auto_backup = True
        self._validate_after_migration = True
        self._dry_run_by_default = False
        self._max_migration_time_seconds = 300
        
        # Built-in migrations
        self._register_builtin_migrations()
    
    def register_migration(self, step: MigrationStep) -> None:
        """Register a migration step."""
        # Calculate checksum if not provided
        if not step.checksum:
            step.checksum = self._calculate_migration_checksum(step)
        
        self._migrations[step.version] = step
        
        # Update registry
        if step.version not in self._migration_registry:
            self._migration_registry[step.version] = []
        self._migration_registry[step.version].append(step)
    
    def unregister_migration(self, version: str) -> bool:
        """Unregister a migration step."""
        if version in self._migrations:
            del self._migrations[version]
            if version in self._migration_registry:
                del self._migration_registry[version]
            return True
        return False
    
    def get_migration(self, version: str) -> Optional[MigrationStep]:
        """Get a migration step by version."""
        return self._migrations.get(version)
    
    def get_all_migrations(self) -> Dict[str, MigrationStep]:
        """Get all registered migrations."""
        return self._migrations.copy()
    
    def get_migration_plan(self, from_version: str, to_version: str) -> MigrationPlan:
        """Create a migration plan."""
        try:
            # Get migration path
            migration_path = self._get_migration_path(from_version, to_version)
            
            # Validate dependencies
            dependencies_resolved = self._validate_dependencies(migration_path)
            
            # Estimate time
            estimated_time = len(migration_path) * 100  # 100ms per step
            
            # Check rollback possibility
            rollback_possible = all(step.down_migration is not None for step in migration_path)
            
            return MigrationPlan(
                from_version=from_version,
                to_version=to_version,
                steps=migration_path,
                estimated_time_ms=estimated_time,
                rollback_possible=rollback_possible,
                dependencies_resolved=dependencies_resolved,
                validation_required=self._validate_after_migration
            )
            
        except Exception as e:
            return MigrationPlan(
                from_version=from_version,
                to_version=to_version,
                steps=[],
                dependencies_resolved=False,
                validation_required=True
            )
    
    def migrate_config(self, config: Dict[str, Any], 
                      from_version: str, to_version: str,
                      dry_run: bool = None) -> MigrationResult:
        """
        Migrate configuration from one version to another.
        
        Args:
            config: Configuration to migrate
            from_version: Current version
            to_version: Target version
            dry_run: Whether to perform dry run
            
        Returns:
            Migration result
        """
        start_time = datetime.utcnow()
        
        try:
            dry_run = dry_run if dry_run is not None else self._dry_run_by_default
            
            # Create migration plan
            plan = self.get_migration_plan(from_version, to_version)
            
            if not plan.dependencies_resolved:
                return MigrationResult(
                    success=False,
                    from_version=from_version,
                    to_version=to_version,
                    direction="up",
                    errors=["Migration dependencies not resolved"]
                )
            
            # Create backup if requested
            backup_path = None
            if self._auto_backup and not dry_run:
                backup_path = self._create_migration_backup(config, from_version, to_version)
            
            # Apply migrations
            current_config = config.copy()
            applied_steps = []
            failed_steps = []
            errors = []
            warnings = []
            
            for step in plan.steps:
                try:
                    step.status = MigrationStatus.RUNNING
                    
                    if step.up_migration:
                        current_config = step.up_migration(current_config)
                        applied_steps.append(step.version)
                        step.status = MigrationStatus.COMPLETED
                        step.applied_at = datetime.utcnow()
                    else:
                        failed_steps.append(step.version)
                        step.status = MigrationStatus.FAILED
                        errors.append(f"No up migration for version {step.version}")
                        break
                        
                except Exception as e:
                    failed_steps.append(step.version)
                    step.status = MigrationStatus.FAILED
                    errors.append(f"Migration {step.version} failed: {str(e)}")
                    break
            
            # Validate result if requested
            if self._validate_after_migration and not failed_steps:
                validation_result = validate_config(current_config)
                if not validation_result['valid']:
                    errors.extend(validation_result['errors'])
                    warnings.extend(validation_result['warnings'])
            
            # Calculate migration time
            end_time = datetime.utcnow()
            migration_time_ms = (end_time - start_time).total_seconds() * 1000
            
            success = len(failed_steps) == 0 and len(errors) == 0
            
            result = MigrationResult(
                success=success,
                from_version=from_version,
                to_version=to_version,
                direction="up",
                applied_steps=applied_steps,
                failed_steps=failed_steps,
                errors=errors,
                warnings=warnings,
                rollback_available=plan.rollback_possible,
                migration_time_ms=migration_time_ms
            )
            
            # Store in history
            self._migration_history.append(result)
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            migration_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return MigrationResult(
                success=False,
                from_version=from_version,
                to_version=to_version,
                direction="up",
                errors=[f"Migration failed: {str(e)}"],
                migration_time_ms=migration_time_ms
            )
    
    def rollback_migration(self, config: Dict[str, Any],
                          from_version: str, to_version: str,
                          dry_run: bool = None) -> MigrationResult:
        """
        Rollback migration from one version to another.
        
        Args:
            config: Configuration to rollback
            from_version: Current version
            to_version: Target version
            dry_run: Whether to perform dry run
            
        Returns:
            Migration result
        """
        start_time = datetime.utcnow()
        
        try:
            dry_run = dry_run if dry_run is not None else self._dry_run_by_default
            
            # Get rollback path (reverse of migration path)
            migration_path = self._get_migration_path(to_version, from_version)
            rollback_path = list(reversed(migration_path))
            
            # Check if rollback is possible
            if not all(step.down_migration for step in rollback_path):
                return MigrationResult(
                    success=False,
                    from_version=from_version,
                    to_version=to_version,
                    direction="down",
                    errors=["Rollback not possible - missing down migrations"]
                )
            
            # Apply rollback migrations
            current_config = config.copy()
            applied_steps = []
            failed_steps = []
            errors = []
            
            for step in rollback_path:
                try:
                    step.status = MigrationStatus.RUNNING
                    
                    if step.down_migration:
                        current_config = step.down_migration(current_config)
                        applied_steps.append(step.version)
                        step.status = MigrationStatus.ROLLED_BACK
                    else:
                        failed_steps.append(step.version)
                        step.status = MigrationStatus.FAILED
                        errors.append(f"No down migration for version {step.version}")
                        break
                        
                except Exception as e:
                    failed_steps.append(step.version)
                    step.status = MigrationStatus.FAILED
                    errors.append(f"Rollback {step.version} failed: {str(e)}")
                    break
            
            # Calculate rollback time
            end_time = datetime.utcnow()
            migration_time_ms = (end_time - start_time).total_seconds() * 1000
            
            success = len(failed_steps) == 0 and len(errors) == 0
            
            result = MigrationResult(
                success=success,
                from_version=from_version,
                to_version=to_version,
                direction="down",
                applied_steps=applied_steps,
                failed_steps=failed_steps,
                errors=errors,
                rollback_available=False,
                migration_time_ms=migration_time_ms
            )
            
            # Store in history
            self._migration_history.append(result)
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            migration_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return MigrationResult(
                success=False,
                from_version=from_version,
                to_version=to_version,
                direction="down",
                errors=[f"Rollback failed: {str(e)}"],
                migration_time_ms=migration_time_ms
            )
    
    def _get_migration_path(self, from_version: str, to_version: str) -> List[MigrationStep]:
        """Get migration path from one version to another."""
        # This is a simplified implementation
        # In a real scenario, this would use semantic version comparison
        # and dependency resolution
        
        all_versions = sorted(self._migrations.keys())
        
        try:
            from_index = all_versions.index(from_version)
            to_index = all_versions.index(to_version)
        except ValueError:
            raise ValueError(f"Version not found: {from_version} or {to_version}")
        
        if from_index < to_index:
            # Forward migration
            path_versions = all_versions[from_index + 1:to_index + 1]
        else:
            # Rollback migration
            path_versions = all_versions[to_index:from_index]
        
        return [self._migrations[version] for version in path_versions]
    
    def _validate_dependencies(self, migration_path: List[MigrationStep]) -> bool:
        """Validate migration dependencies."""
        for step in migration_path:
            for dependency in step.dependencies:
                if dependency not in self._migrations:
                    return False
        
        return True
    
    def _calculate_migration_checksum(self, step: MigrationStep) -> str:
        """Calculate checksum for migration step."""
        content = f"{step.version}{step.description}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _create_migration_backup(self, config: Dict[str, Any], 
                               from_version: str, to_version: str) -> str:
        """Create backup before migration."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_name = f"migration_backup_{from_version}_to_{to_version}_{timestamp}"
        
        backup_dir = Path("config_backups")
        backup_dir.mkdir(exist_ok=True)
        
        backup_path = backup_dir / backup_name
        
        # Export configuration
        export_options = ExportOptions(
            include_sensitive=True,
            pretty_print=True
        )
        
        self.config_io.export_config(config, backup_path, export_options)
        
        return str(backup_path)
    
    def _register_builtin_migrations(self) -> None:
        """Register built-in migrations."""
        
        # Migration 1.0.0 -> 1.1.0
        def migrate_1_0_0_to_1_1_0(config: Dict[str, Any]) -> Dict[str, Any]:
            """Migrate from 1.0.0 to 1.1.0."""
            # Add new fields
            if 'environment' not in config:
                config['environment'] = 'development'
            
            # Update existing fields
            if 'timeout' in config and isinstance(config['timeout'], int):
                config['timeout_ms'] = config['timeout'] * 1000
            
            return config
        
        def rollback_1_1_0_to_1_0_0(config: Dict[str, Any]) -> Dict[str, Any]:
            """Rollback from 1.1.0 to 1.0.0."""
            # Remove new fields
            config.pop('environment', None)
            
            # Revert existing fields
            if 'timeout_ms' in config:
                config['timeout'] = config['timeout_ms'] // 1000
                config.pop('timeout_ms', None)
            
            return config
        
        self.register_migration(MigrationStep(
            version="1.1.0",
            description="Add environment support and timeout in milliseconds",
            up_migration=migrate_1_0_0_to_1_1_0,
            down_migration=rollback_1_1_0_to_1_0_0
        ))
        
        # Migration 1.1.0 -> 1.2.0
        def migrate_1_1_0_to_1_2_0(config: Dict[str, Any]) -> Dict[str, Any]:
            """Migrate from 1.1.0 to 1.2.0."""
            # Add feature flags support
            if 'feature_flags' not in config:
                config['feature_flags'] = {
                    'debug_mode': False,
                    'headless_mode': True,
                    'rate_limiting_enabled': True
                }
            
            # Add rate limiting configuration
            if 'rate_limiting' not in config:
                config['rate_limiting'] = {
                    'enabled': True,
                    'max_requests_per_minute': 60,
                    'strategy': 'token_bucket'
                }
            
            return config
        
        def rollback_1_2_0_to_1_1_0(config: Dict[str, Any]) -> Dict[str, Any]:
            """Rollback from 1.2.0 to 1.1.0."""
            # Remove feature flags
            config.pop('feature_flags', None)
            
            # Remove rate limiting
            config.pop('rate_limiting', None)
            
            return config
        
        self.register_migration(MigrationStep(
            version="1.2.0",
            description="Add feature flags and rate limiting support",
            up_migration=migrate_1_1_0_to_1_2_0,
            down_migration=rollback_1_2_0_to_1_1_0,
            dependencies=["1.1.0"]
        ))
        
        # Migration 1.2.0 -> 1.3.0
        def migrate_1_2_0_to_1_3_0(config: Dict[str, Any]) -> Dict[str, Any]:
            """Migrate from 1.2.0 to 1.3.0."""
            # Add browser configuration
            if 'browser' not in config:
                config['browser'] = {
                    'headless': True,
                    'browser_type': 'chromium',
                    'viewport_width': 1920,
                    'viewport_height': 1080
                }
            
            # Add stealth configuration
            if 'stealth' not in config:
                config['stealth'] = {
                    'enabled': False,
                    'randomize_user_agent': True,
                    'randomize_viewport': True
                }
            
            return config
        
        def rollback_1_3_0_to_1_2_0(config: Dict[str, Any]) -> Dict[str, Any]:
            """Rollback from 1.3.0 to 1.2.0."""
            # Remove browser configuration
            config.pop('browser', None)
            
            # Remove stealth configuration
            config.pop('stealth', None)
            
            return config
        
        self.register_migration(MigrationStep(
            version="1.3.0",
            description="Add browser and stealth configuration",
            up_migration=migrate_1_2_0_to_1_3_0,
            down_migration=rollback_1_3_0_to_1_2_0,
            dependencies=["1.2.0"]
        ))
    
    def get_migration_history(self, limit: Optional[int] = None) -> List[MigrationResult]:
        """Get migration history."""
        if limit:
            return self._migration_history[-limit:]
        return self._migration_history.copy()
    
    def clear_migration_history(self) -> None:
        """Clear migration history."""
        self._migration_history.clear()
    
    def set_auto_backup(self, auto_backup: bool) -> None:
        """Set automatic backup setting."""
        self._auto_backup = auto_backup
    
    def set_validate_after_migration(self, validate: bool) -> None:
        """Set validation after migration setting."""
        self._validate_after_migration = validate
    
    def set_dry_run_by_default(self, dry_run: bool) -> None:
        """Set dry run by default setting."""
        self._dry_run_by_default = dry_run
    
    def get_pending_migrations(self, current_version: str) -> List[MigrationStep]:
        """Get pending migrations for current version."""
        all_versions = sorted(self._migrations.keys())
        
        try:
            current_index = all_versions.index(current_version)
            pending_versions = all_versions[current_index + 1:]
            return [self._migrations[version] for version in pending_versions]
        except ValueError:
            return []
    
    def get_latest_version(self) -> str:
        """Get the latest migration version."""
        if not self._migrations:
            return "1.0.0"
        
        return max(self._migrations.keys())
    
    def validate_config_version(self, config: Dict[str, Any], 
                               expected_version: str) -> bool:
        """Validate configuration version."""
        config_version = config.get('version', '1.0.0')
        
        try:
            # Simple version comparison
            config_parts = [int(x) for x in config_version.split('.')]
            expected_parts = [int(x) for x in expected_version.split('.')]
            
            return config_parts >= expected_parts
        except (ValueError, AttributeError):
            return False
    
    def export_migrations(self, output_path: Union[str, Path]) -> bool:
        """Export all migrations to file."""
        try:
            output_path = Path(output_path)
            
            migrations_data = {
                'migrations': {},
                'exported_at': datetime.utcnow().isoformat()
            }
            
            for version, step in self._migrations.items():
                migrations_data['migrations'][version] = {
                    'version': step.version,
                    'description': step.description,
                    'dependencies': step.dependencies,
                    'checksum': step.checksum,
                    'created_at': step.created_at.isoformat(),
                    'applied_at': step.applied_at.isoformat() if step.applied_at else None,
                    'status': step.status.value
                }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(migrations_data, f, indent=2, default=str)
            
            return True
            
        except Exception:
            return False
    
    def import_migrations(self, input_path: Union[str, Path]) -> bool:
        """Import migrations from file."""
        try:
            input_path = Path(input_path)
            
            with open(input_path, 'r', encoding='utf-8') as f:
                migrations_data = json.load(f)
            
            for version, step_data in migrations_data.get('migrations', {}).items():
                step = MigrationStep(
                    version=step_data['version'],
                    description=step_data['description'],
                    dependencies=step_data.get('dependencies', []),
                    checksum=step_data.get('checksum'),
                    created_at=datetime.fromisoformat(step_data['created_at'])
                )
                
                if step_data.get('applied_at'):
                    step.applied_at = datetime.fromisoformat(step_data['applied_at'])
                
                if step_data.get('status'):
                    step.status = MigrationStatus(step_data['status'])
                
                self.register_migration(step)
            
            return True
            
        except Exception:
            return False


# Global migration instance
_config_migration = ConfigMigration()


# Convenience functions
def register_migration(step: MigrationStep) -> None:
    """Register a migration step."""
    _config_migration.register_migration(step)


def migrate_config(config: Dict[str, Any], 
                  from_version: str, to_version: str,
                  dry_run: bool = None) -> MigrationResult:
    """Migrate configuration."""
    return _config_migration.migrate_config(config, from_version, to_version, dry_run)


def rollback_migration(config: Dict[str, Any],
                     from_version: str, to_version: str,
                     dry_run: bool = None) -> MigrationResult:
    """Rollback migration."""
    return _config_migration.rollback_migration(config, from_version, to_version, dry_run)


def get_migration_plan(from_version: str, to_version: str) -> MigrationPlan:
    """Get migration plan."""
    return _config_migration.get_migration_plan(from_version, to_version)


def get_migration_history(limit: Optional[int] = None) -> List[MigrationResult]:
    """Get migration history."""
    return _config_migration.get_migration_history(limit)


def get_pending_migrations(current_version: str) -> List[MigrationStep]:
    """Get pending migrations."""
    return _config_migration.get_pending_migrations(current_version)


def get_latest_version() -> str:
    """Get latest migration version."""
    return _config_migration.get_latest_version()


def validate_config_version(config: Dict[str, Any], 
                          expected_version: str) -> bool:
    """Validate configuration version."""
    return _config_migration.validate_config_version(config, expected_version)
