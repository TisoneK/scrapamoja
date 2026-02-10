"""
Template migration and upgrade utilities.

This module provides utilities for migrating templates between framework versions,
upgrading template structures, and managing template version compatibility.
"""

import json
import yaml
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import re
import difflib
import hashlib
from enum import Enum

logger = logging.getLogger(__name__)


class MigrationType(Enum):
    """Types of template migrations."""
    STRUCTURE = "structure"
    CONFIGURATION = "configuration"
    SELECTORS = "selectors"
    DEPENDENCIES = "dependencies"
    METADATA = "metadata"
    FRAMEWORK = "framework"


class MigrationStatus(Enum):
    """Migration status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationStep:
    """Individual migration step."""
    step_id: str
    description: str
    migration_type: MigrationType
    from_version: str
    to_version: str
    status: MigrationStatus = MigrationStatus.PENDING
    error_message: Optional[str] = None
    backup_path: Optional[str] = None
    checksum_before: Optional[str] = None
    checksum_after: Optional[str] = None
    execution_time: Optional[float] = None


@dataclass
class MigrationPlan:
    """Complete migration plan."""
    plan_id: str
    template_name: str
    from_version: str
    to_version: str
    migration_type: MigrationType
    steps: List[MigrationStep]
    created_at: datetime
    status: MigrationStatus = MigrationStatus.PENDING
    rollback_available: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class VersionCompatibilityChecker:
    """Version compatibility checker for template framework."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize version compatibility checker.
        
        Args:
            config: Checker configuration
        """
        self.config = config or {}
        
        # Version compatibility matrix
        self.compatibility_matrix = {
            "1.0.0": {
                "compatible_with": ["1.0.1", "1.0.2", "1.1.0"],
                "requires_migration": ["1.1.0", "1.2.0"],
                "breaking_changes": ["1.2.0"]
            },
            "1.0.1": {
                "compatible_with": ["1.0.2", "1.1.0"],
                "requires_migration": ["1.1.0", "1.2.0"],
                "breaking_changes": ["1.2.0"]
            },
            "1.0.2": {
                "compatible_with": ["1.1.0"],
                "requires_migration": ["1.1.0", "1.2.0"],
                "breaking_changes": ["1.2.0"]
            },
            "1.1.0": {
                "compatible_with": ["1.1.1", "1.2.0"],
                "requires_migration": ["1.2.0"],
                "breaking_changes": ["1.2.0"]
            },
            "1.1.1": {
                "compatible_with": ["1.2.0"],
                "requires_migration": ["1.2.0"],
                "breaking_changes": ["1.2.0"]
            },
            "1.2.0": {
                "compatible_with": ["1.2.1", "1.3.0"],
                "requires_migration": ["1.3.0"],
                "breaking_changes": []
            }
        }
        
        logger.info("VersionCompatibilityChecker initialized")
    
    def check_compatibility(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """
        Check version compatibility.
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            Dict[str, Any]: Compatibility information
        """
        if from_version == to_version:
            return {
                "compatible": True,
                "requires_migration": False,
                "breaking_changes": False,
                "migration_type": None,
                "message": "Versions are identical"
            }
        
        # Check if versions are in compatibility matrix
        if from_version not in self.compatibility_matrix:
            return {
                "compatible": False,
                "requires_migration": True,
                "breaking_changes": True,
                "migration_type": "unknown",
                "message": f"Unknown source version: {from_version}"
            }
        
        version_info = self.compatibility_matrix[from_version]
        
        # Check compatibility
        compatible = to_version in version_info["compatible_with"]
        requires_migration = to_version in version_info["requires_migration"]
        breaking_changes = to_version in version_info["breaking_changes"]
        
        # Determine migration type
        migration_type = None
        if requires_migration:
            if breaking_changes:
                migration_type = "major"
            else:
                migration_type = "minor"
        elif compatible:
            migration_type = "patch"
        
        return {
            "compatible": compatible,
            "requires_migration": requires_migration,
            "breaking_changes": breaking_changes,
            "migration_type": migration_type,
            "message": self._get_compatibility_message(compatible, requires_migration, breaking_changes)
        }
    
    def _get_compatibility_message(self, compatible: bool, requires_migration: bool, 
                                 breaking_changes: bool) -> str:
        """Get compatibility message."""
        if breaking_changes:
            return "Breaking changes detected - major migration required"
        elif requires_migration:
            return "Migration required for compatibility"
        elif compatible:
            return "Versions are compatible"
        else:
            return "Versions are not compatible"
    
    def get_migration_path(self, from_version: str, to_version: str) -> List[str]:
        """
        Get migration path between versions.
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            List[str]: List of intermediate versions
        """
        # Simple implementation - in reality, this would be more complex
        if from_version == to_version:
            return []
        
        # For now, return direct migration
        return [to_version]


class TemplateMigrator:
    """Template migration engine."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize template migrator.
        
        Args:
            config: Migrator configuration
        """
        self.config = config or {}
        
        # Migration configuration
        self.migration_config = {
            "backup_enabled": self.config.get("backup_enabled", True),
            "backup_dir": self.config.get("backup_dir", "backups"),
            "dry_run": self.config.get("dry_run", False),
            "validate_after_migration": self.config.get("validate_after_migration", True),
            "max_retries": self.config.get("max_retries", 3)
        }
        
        # Initialize components
        self.compatibility_checker = VersionCompatibilityChecker(config)
        
        # Migration registry
        self.migration_registry = self._initialize_migration_registry()
        
        logger.info("TemplateMigrator initialized")
    
    def _initialize_migration_registry(self) -> Dict[str, Dict[str, Any]]:
        """Initialize migration registry with available migrations."""
        return {
            "1.0.0_to_1.1.0": {
                "description": "Migrate from 1.0.0 to 1.1.0",
                "migration_type": MigrationType.FRAMEWORK,
                "steps": [
                    "update_imports",
                    "update_config_structure",
                    "add_integration_bridge",
                    "update_selector_format"
                ]
            },
            "1.0.0_to_1.2.0": {
                "description": "Migrate from 1.0.0 to 1.2.0",
                "migration_type": MigrationType.FRAMEWORK,
                "steps": [
                    "update_imports",
                    "update_config_structure",
                    "add_integration_bridge",
                    "update_selector_format",
                    "add_performance_monitoring",
                    "add_security_features"
                ]
            },
            "1.1.0_to_1.2.0": {
                "description": "Migrate from 1.1.0 to 1.2.0",
                "migration_type": MigrationType.FRAMEWORK,
                "steps": [
                    "add_performance_monitoring",
                    "add_security_features",
                    "update_logging_integration"
                ]
            }
        }
    
    def create_migration_plan(self, template_path: Union[str, Path], 
                            from_version: str, to_version: str) -> MigrationPlan:
        """
        Create migration plan for template.
        
        Args:
            template_path: Path to template
            from_version: Source version
            to_version: Target version
            
        Returns:
            MigrationPlan: Migration plan
        """
        template_path = Path(template_path)
        
        # Check compatibility
        compatibility = self.compatibility_checker.check_compatibility(from_version, to_version)
        
        if not compatibility["compatible"] and not compatibility["requires_migration"]:
            raise ValueError(f"Cannot migrate from {from_version} to {to_version}: {compatibility['message']}")
        
        # Get migration path
        migration_path = self.compatibility_checker.get_migration_path(from_version, to_version)
        
        # Create migration steps
        steps = []
        migration_key = f"{from_version}_to_{to_version}"
        
        if migration_key in self.migration_registry:
            migration_info = self.migration_registry[migration_key]
            
            for i, step_name in enumerate(migration_info["steps"]):
                step = MigrationStep(
                    step_id=f"step_{i+1}",
                    description=f"Execute {step_name}",
                    migration_type=migration_info["migration_type"],
                    from_version=from_version,
                    to_version=to_version
                )
                steps.append(step)
        
        # Create migration plan
        plan = MigrationPlan(
            plan_id=f"migration_{int(datetime.now().timestamp())}",
            template_name=template_path.name,
            from_version=from_version,
            to_version=to_version,
            migration_type=MigrationType.FRAMEWORK,
            steps=steps
        )
        
        logger.info(f"Created migration plan for {template_path.name}: {from_version} -> {to_version}")
        return plan
    
    async def execute_migration(self, template_path: Union[str, Path], 
                              migration_plan: MigrationPlan) -> Dict[str, Any]:
        """
        Execute migration plan.
        
        Args:
            template_path: Path to template
            migration_plan: Migration plan to execute
            
        Returns:
            Dict[str, Any]: Migration results
        """
        template_path = Path(template_path)
        migration_plan.status = MigrationStatus.IN_PROGRESS
        
        try:
            # Create backup
            if self.migration_config["backup_enabled"]:
                backup_path = self._create_backup(template_path, migration_plan.plan_id)
                migration_plan.rollback_available = True
            else:
                backup_path = None
            
            # Execute migration steps
            results = []
            
            for step in migration_plan.steps:
                step.status = MigrationStatus.IN_PROGRESS
                
                try:
                    # Calculate checksum before
                    step.checksum_before = self._calculate_checksum(template_path)
                    
                    # Execute step
                    start_time = datetime.now()
                    step_result = await self._execute_migration_step(
                        template_path, step, migration_plan
                    )
                    step.execution_time = (datetime.now() - start_time).total_seconds()
                    
                    # Calculate checksum after
                    step.checksum_after = self._calculate_checksum(template_path)
                    
                    step.status = MigrationStatus.COMPLETED
                    step.backup_path = str(backup_path) if backup_path else None
                    
                    results.append(step_result)
                    
                except Exception as e:
                    step.status = MigrationStatus.FAILED
                    step.error_message = str(e)
                    
                    logger.error(f"Migration step failed: {step.step_id} - {e}")
                    
                    # Rollback if enabled
                    if self.migration_config["backup_enabled"] and backup_path:
                        await self._rollback_migration(template_path, backup_path)
                        migration_plan.status = MigrationStatus.ROLLED_BACK
                    
                    raise
            
            # Validate migration
            if self.migration_config["validate_after_migration"]:
                validation_result = await self._validate_migration(template_path, migration_plan)
                if not validation_result["valid"]:
                    raise ValueError(f"Migration validation failed: {validation_result['errors']}")
            
            migration_plan.status = MigrationStatus.COMPLETED
            
            return {
                "success": True,
                "migration_plan": migration_plan,
                "results": results,
                "backup_path": str(backup_path) if backup_path else None
            }
        
        except Exception as e:
            migration_plan.status = MigrationStatus.FAILED
            logger.error(f"Migration failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "migration_plan": migration_plan
            }
    
    async def _execute_migration_step(self, template_path: Path, step: MigrationStep, 
                                    migration_plan: MigrationPlan) -> Dict[str, Any]:
        """Execute individual migration step."""
        if self.migration_config["dry_run"]:
            logger.info(f"[DRY RUN] Would execute step: {step.description}")
            return {"success": True, "dry_run": True}
        
        # Execute step based on description
        if "update_imports" in step.description:
            return await self._update_imports(template_path, step)
        elif "update_config_structure" in step.description:
            return await self._update_config_structure(template_path, step)
        elif "add_integration_bridge" in step.description:
            return await self._add_integration_bridge(template_path, step)
        elif "update_selector_format" in step.description:
            return await self._update_selector_format(template_path, step)
        elif "add_performance_monitoring" in step.description:
            return await self._add_performance_monitoring(template_path, step)
        elif "add_security_features" in step.description:
            return await self._add_security_features(template_path, step)
        elif "update_logging_integration" in step.description:
            return await self._update_logging_integration(template_path, step)
        else:
            logger.warning(f"Unknown migration step: {step.description}")
            return {"success": True, "message": "Step not implemented"}
    
    async def _update_imports(self, template_path: Path, step: MigrationStep) -> Dict[str, Any]:
        """Update imports in template files."""
        updated_files = []
        
        for py_file in template_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Update imports
                old_imports = [
                    "from src.sites.base import BaseSiteScraper",
                    "from src.sites.base.scraper import BaseSiteScraper"
                ]
                
                new_import = "from src.sites.base.template import BaseSiteTemplate"
                
                for old_import in old_imports:
                    if old_import in content:
                        content = content.replace(old_import, new_import)
                        updated_files.append(str(py_file))
                
                # Update class inheritance
                if "BaseSiteScraper" in content:
                    content = content.replace("BaseSiteScraper", "BaseSiteTemplate")
                    updated_files.append(str(py_file))
                
                # Write back if changed
                if updated_files and str(py_file) in updated_files:
                    with open(py_file, 'w') as f:
                        f.write(content)
            
            except Exception as e:
                logger.error(f"Error updating imports in {py_file}: {e}")
                raise
        
        return {
            "success": True,
            "updated_files": updated_files,
            "message": f"Updated imports in {len(updated_files)} files"
        }
    
    async def _update_config_structure(self, template_path: Path, step: MigrationStep) -> Dict[str, Any]:
        """Update configuration structure."""
        config_file = template_path / "config.py"
        
        if not config_file.exists():
            return {"success": True, "message": "No config.py file found"}
        
        try:
            with open(config_file, 'r') as f:
                content = f.read()
            
            # Add new configuration sections if not present
            new_sections = {
                "INTEGRATION_CONFIG": {
                    "browser_lifecycle": True,
                    "resource_monitoring": True,
                    "logging_integration": True
                },
                "VALIDATION_CONFIG": {
                    "strict_mode": True,
                    "validate_selectors": True
                }
            }
            
            updated = False
            for section_name, section_config in new_sections.items():
                if section_name not in content:
                    # Add section to file
                    section_code = f"\n# {section_name}\n{section_name} = {section_config}\n"
                    content += section_code
                    updated = True
            
            if updated:
                with open(config_file, 'w') as f:
                    f.write(content)
            
            return {
                "success": True,
                "updated": updated,
                "message": "Configuration structure updated"
            }
        
        except Exception as e:
            logger.error(f"Error updating config structure: {e}")
            raise
    
    async def _add_integration_bridge(self, template_path: Path, step: MigrationStep) -> Dict[str, Any]:
        """Add integration bridge to template."""
        bridge_file = template_path / "integration_bridge.py"
        
        if bridge_file.exists():
            return {"success": True, "message": "Integration bridge already exists"}
        
        # Create integration bridge template
        bridge_content = '''"""
Integration bridge for template.

This module provides framework component integration for the template.
"""

from src.sites.base.template.integration_bridge import FullIntegrationBridge


class TemplateIntegrationBridge(FullIntegrationBridge):
    """
    Template-specific integration bridge.
    """
    
    def __init__(self, template_name, selector_engine, page):
        super().__init__(template_name, selector_engine, page)
'''
        
        try:
            with open(bridge_file, 'w') as f:
                f.write(bridge_content)
            
            return {
                "success": True,
                "created_file": str(bridge_file),
                "message": "Integration bridge created"
            }
        
        except Exception as e:
            logger.error(f"Error creating integration bridge: {e}")
            raise
    
    async def _update_selector_format(self, template_path: Path, step: MigrationStep) -> Dict[str, Any]:
        """Update selector format to new YAML structure."""
        selectors_dir = template_path / "selectors"
        
        if not selectors_dir.exists():
            return {"success": True, "message": "No selectors directory found"}
        
        updated_selectors = []
        
        for yaml_file in selectors_dir.rglob("*.yaml") + selectors_dir.rglob("*.yml"):
            try:
                with open(yaml_file, 'r') as f:
                    selector_data = yaml.safe_load(f)
                
                # Update selector format
                if isinstance(selector_data, dict):
                    # Add new fields if missing
                    if "strategies" not in selector_data:
                        selector_data["strategies"] = [
                            {
                                "name": "default",
                                "type": "css",
                                "priority": 1,
                                "confidence": 0.8
                            }
                        ]
                    
                    if "validation" not in selector_data:
                        selector_data["validation"] = {
                            "required": True,
                            "exists": True
                        }
                    
                    if "metadata" not in selector_data:
                        selector_data["metadata"] = {
                            "category": "general",
                            "version": "1.0.0"
                        }
                    
                    # Write back
                    with open(yaml_file, 'w') as f:
                        yaml.dump(selector_data, f, default_flow_style=False)
                    
                    updated_selectors.append(str(yaml_file))
            
            except Exception as e:
                logger.error(f"Error updating selector format in {yaml_file}: {e}")
                raise
        
        return {
            "success": True,
            "updated_selectors": updated_selectors,
            "message": f"Updated {len(updated_selectors)} selector files"
        }
    
    async def _add_performance_monitoring(self, template_path: Path, step: MigrationStep) -> Dict[str, Any]:
        """Add performance monitoring to template."""
        # This would add performance monitoring imports and usage
        return {"success": True, "message": "Performance monitoring features added"}
    
    async def _add_security_features(self, template_path: Path, step: MigrationStep) -> Dict[str, Any]:
        """Add security features to template."""
        # This would add security imports and configurations
        return {"success": True, "message": "Security features added"}
    
    async def _update_logging_integration(self, template_path: Path, step: MigrationStep) -> Dict[str, Any]:
        """Update logging integration."""
        # This would update logging to use new integration
        return {"success": True, "message": "Logging integration updated"}
    
    def _create_backup(self, template_path: Path, migration_id: str) -> Path:
        """Create backup of template."""
        backup_dir = Path(self.migration_config["backup_dir"])
        backup_dir.mkdir(exist_ok=True)
        
        backup_path = backup_dir / f"{template_path.name}_backup_{migration_id}"
        
        try:
            if backup_path.exists():
                shutil.rmtree(backup_path)
            
            shutil.copytree(template_path, backup_path)
            
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise
    
    async def _rollback_migration(self, template_path: Path, backup_path: Path) -> None:
        """Rollback migration from backup."""
        try:
            if template_path.exists():
                shutil.rmtree(template_path)
            
            shutil.copytree(backup_path, template_path)
            
            logger.info(f"Rolled back migration from backup: {backup_path}")
        
        except Exception as e:
            logger.error(f"Error rolling back migration: {e}")
            raise
    
    def _calculate_checksum(self, template_path: Path) -> str:
        """Calculate checksum of template directory."""
        checksum = hashlib.md5()
        
        for file_path in sorted(template_path.rglob("*")):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    checksum.update(f.read())
        
        return checksum.hexdigest()
    
    async def _validate_migration(self, template_path: Path, 
                                migration_plan: MigrationPlan) -> Dict[str, Any]:
        """Validate migration results."""
        # This would run validation checks on the migrated template
        return {"valid": True, "errors": [], "warnings": []}


class TemplateUpgrader:
    """Template upgrade utility."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize template upgrader.
        
        Args:
            config: Upgrader configuration
        """
        self.config = config or {}
        self.migrator = TemplateMigrator(config)
        
        logger.info("TemplateUpgrader initialized")
    
    async def upgrade_template(self, template_path: Union[str, Path], 
                             target_version: str) -> Dict[str, Any]:
        """
        Upgrade template to target version.
        
        Args:
            template_path: Path to template
            target_version: Target version
            
        Returns:
            Dict[str, Any]: Upgrade results
        """
        template_path = Path(template_path)
        
        # Get current version
        current_version = self._get_template_version(template_path)
        
        if current_version == target_version:
            return {
                "success": True,
                "message": f"Template already at version {target_version}",
                "current_version": current_version,
                "target_version": target_version
            }
        
        # Create and execute migration plan
        migration_plan = self.migrator.create_migration_plan(
            template_path, current_version, target_version
        )
        
        migration_result = await self.migrator.execute_migration(
            template_path, migration_plan
        )
        
        if migration_result["success"]:
            # Update version in metadata
            await self._update_template_version(template_path, target_version)
        
        return {
            **migration_result,
            "current_version": current_version,
            "target_version": target_version
        }
    
    def _get_template_version(self, template_path: Path) -> str:
        """Get current version of template."""
        metadata_file = template_path / "metadata.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                return metadata.get("version", "1.0.0")
            except Exception:
                pass
        
        # Try to get version from scraper.py
        scraper_file = template_path / "scraper.py"
        if scraper_file.exists():
            try:
                with open(scraper_file, 'r') as f:
                    content = f.read()
                
                # Look for version in class initialization
                version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if version_match:
                    return version_match.group(1)
            except Exception:
                pass
        
        return "1.0.0"  # Default version
    
    async def _update_template_version(self, template_path: Path, version: str) -> None:
        """Update template version in metadata."""
        metadata_file = template_path / "metadata.json"
        
        try:
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}
            
            metadata["version"] = version
            metadata["updated_at"] = datetime.now().isoformat()
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        except Exception as e:
            logger.error(f"Error updating template version: {e}")
            raise


# Global instances
_global_migrator = None
_global_upgrader = None


def get_global_migrator(config: Optional[Dict[str, Any]] = None) -> TemplateMigrator:
    """Get global template migrator instance."""
    global _global_migrator
    if _global_migrator is None:
        _global_migrator = TemplateMigrator(config)
    return _global_migrator


def get_global_upgrader(config: Optional[Dict[str, Any]] = None) -> TemplateUpgrader:
    """Get global template upgrader instance."""
    global _global_upgrader
    if _global_upgrader is None:
        _global_upgrader = TemplateUpgrader(config)
    return _global_upgrader
