"""
Migration utilities for flat to hierarchical selector structure transformation.

This module provides utilities to backup, migrate, and validate selector files
when transitioning from flat YAML structure to hierarchical organization.
"""

import asyncio
import json
import logging
import shutil
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field
import hashlib

from .context_manager import SelectorContext, get_context_manager
from .hierarchical_structure_validator import validate_selector_structure
from .naming_convention_validator import validate_selector_naming


logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    success: bool
    files_migrated: int
    files_failed: int
    errors: List[str]
    warnings: List[str]
    backup_path: Optional[Path] = None
    migration_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackupResult:
    """Result of a backup operation."""
    success: bool
    backup_path: Path
    files_backed_up: int
    backup_size_mb: float
    checksum: str
    errors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


class SelectorBackupManager:
    """
    Manages backup operations for existing flat selector files.
    """
    
    def __init__(self, backup_root: Path):
        """
        Initialize backup manager.
        
        Args:
            backup_root: Root directory for backups
        """
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped backup directories
        self.current_backup_dir = self.backup_root / f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"BackupManager initialized with root: {backup_root}")
    
    async def create_backup(
        self,
        source_dir: Path,
        include_metadata: bool = True
    ) -> BackupResult:
        """
        Create a backup of existing selector files.
        
        Args:
            source_dir: Directory containing flat selector files
            include_metadata: Whether to include migration metadata
            
        Returns:
            BackupResult: Backup operation result
        """
        start_time = datetime.utcnow()
        
        try:
            # Create backup directory
            self.current_backup_dir.mkdir(exist_ok=True)
            
            # Copy all YAML files
            yaml_files = list(source_dir.glob("*.yaml")) + list(source_dir.glob("*.yml"))
            files_backed_up = 0
            
            for yaml_file in yaml_files:
                try:
                    dest_file = self.current_backup_dir / yaml_file.name
                    shutil.copy2(yaml_file, dest_file)
                    files_backed_up += 1
                    
                except Exception as e:
                    logger.error(f"Failed to backup {yaml_file}: {e}")
                    return BackupResult(
                        success=False,
                        backup_path=self.current_backup_dir,
                        files_backed_up=0,
                        backup_size_mb=0.0,
                        checksum="",
                        errors=[f"Failed to copy {yaml_file}: {e}"]
                    )
            
            # Calculate backup size
            backup_size = self._calculate_directory_size(self.current_backup_dir)
            
            # Create metadata file
            if include_metadata:
                metadata = {
                    "backup_created_at": start_time.isoformat(),
                    "source_directory": str(source_dir),
                    "files_backed_up": files_backed_up,
                    "backup_size_mb": backup_size,
                    "migration_version": "1.0.0",
                    "original_structure": "flat"
                }
                
                metadata_file = self.current_backup_dir / "backup_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            # Calculate checksum
            checksum = await self._calculate_directory_checksum(self.current_backup_dir)
            
            backup_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info(
                f"Backup completed: {files_backed_up} files, {backup_size:.2f}MB in {backup_time:.2f}ms"
            )
            
            return BackupResult(
                success=True,
                backup_path=self.current_backup_dir,
                files_backed_up=files_backed_up,
                backup_size_mb=backup_size,
                checksum=checksum,
                created_at=start_time
            )
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return BackupResult(
                success=False,
                backup_path=self.current_backup_dir,
                files_backed_up=0,
                backup_size_mb=0.0,
                checksum="",
                errors=[f"Backup operation failed: {e}"]
            )
    
    def _calculate_directory_size(self, directory: Path) -> float:
        """Calculate directory size in MB."""
        total_size = 0
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    async def _calculate_directory_checksum(self, directory: Path) -> str:
        """Calculate SHA-256 checksum of directory contents."""
        hash_sha256 = hashlib.sha256()
        
        # Sort files for consistent checksum
        files = sorted(directory.rglob('*'))
        
        for file_path in files:
            if file_path.is_file():
                # Include relative path and file content
                relative_path = str(file_path.relative_to(directory))
                hash_sha256.update(relative_path.encode('utf-8'))
                
                with open(file_path, 'rb') as f:
                    while chunk := f.read(8192):
                        hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List[Dict[str, Any]]: List of backup information
        """
        backups = []
        
        for backup_dir in self.backup_root.iterdir():
            if backup_dir.is_dir() and backup_dir.name.startswith('backup_'):
                metadata_file = backup_dir / 'backup_metadata.json'
                
                backup_info = {
                    "name": backup_dir.name,
                    "path": str(backup_dir),
                    "created_at": backup_dir.stat().st_mtime
                }
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        backup_info.update(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to read backup metadata for {backup_dir.name}: {e}")
                
                backups.append(backup_info)
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda b: b.get('created_at', 0), reverse=True)
        return backups
    
    async def restore_backup(self, backup_name: str, target_dir: Path) -> bool:
        """
        Restore a backup to the target directory.
        
        Args:
            backup_name: Name of backup to restore
            target_dir: Directory to restore to
            
        Returns:
            bool: True if restore was successful
        """
        try:
            backup_dir = self.backup_root / backup_name
            
            if not backup_dir.exists():
                logger.error(f"Backup directory does not exist: {backup_dir}")
                return False
            
            # Clear target directory
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all files except metadata
            for file_path in backup_dir.iterdir():
                if file_path.name != 'backup_metadata.json':
                    if file_path.is_file():
                        shutil.copy2(file_path, target_dir / file_path.name)
                    elif file_path.is_dir():
                        shutil.copytree(file_path, target_dir / file_path.name)
            
            logger.info(f"Backup {backup_name} restored to {target_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False


class FlatToHierarchicalMigrator:
    """
    Migrates flat YAML selector files to hierarchical structure.
    """
    
    def __init__(self, source_dir: Path, target_dir: Path):
        """
        Initialize migrator.
        
        Args:
            source_dir: Directory with flat YAML files
            target_dir: Target directory for hierarchical structure
        """
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        
        # Mapping of file patterns to target contexts
        self.context_mappings = self._create_context_mappings()
        
        logger.info(f"Migrator initialized: {source_dir} -> {target_dir}")
    
    def _create_context_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Create mappings from file patterns to target contexts."""
        return {
            # Authentication context
            'auth': {
                'primary': 'authentication',
                'patterns': [r'login', r'signin', r'auth', r'consent', r'cookie']
            },
            
            # Navigation context
            'nav': {
                'primary': 'navigation',
                'patterns': [r'nav', r'menu', r'sport', r'category', r'filter', r'search']
            },
            
            # Extraction contexts
            'match_list': {
                'primary': 'extraction',
                'secondary': 'match_list',
                'patterns': [r'match.*list', r'fixture', r'schedule', r'live.*match']
            },
            'match_summary': {
                'primary': 'extraction',
                'secondary': 'match_summary',
                'patterns': [r'summary', r'overview', r'details', r'info']
            },
            'match_h2h': {
                'primary': 'extraction',
                'secondary': 'match_h2h',
                'patterns': [r'h2h', r'head.to.head', r'history', r'versus', r'vs']
            },
            'match_odds': {
                'primary': 'extraction',
                'secondary': 'match_odds',
                'patterns': [r'odds', r'betting', r'price', r'market', r'bookmaker']
            },
            'match_stats': {
                'primary': 'extraction',
                'secondary': 'match_stats',
                'patterns': [r'stats', r'statistics', r'performance', r'analysis']
            },
            
            # Filtering context
            'filter': {
                'primary': 'filtering',
                'patterns': [r'filter', r'date', r'competition', r'league', r'country']
            }
        }
    
    async def migrate(
        self,
        create_backup: bool = True,
        validate_after: bool = True
    ) -> MigrationResult:
        """
        Perform the migration from flat to hierarchical structure.
        
        Args:
            create_backup: Whether to create backup before migration
            validate_after: Whether to validate the result after migration
            
        Returns:
            MigrationResult: Migration operation result
        """
        start_time = datetime.utcnow()
        
        try:
            # Create backup if requested
            backup_result = None
            if create_backup:
                backup_manager = SelectorBackupManager(self.target_dir.parent / 'backups')
                backup_result = await backup_manager.create_backup(self.source_dir)
                
                if not backup_result.success:
                    return MigrationResult(
                        success=False,
                        files_migrated=0,
                        files_failed=0,
                        errors=backup_result.errors,
                        warnings=["Backup creation failed"]
                    )
            
            # Ensure target directory structure exists
            await self._ensure_target_structure()
            
            # Migrate files
            migration_result = await self._migrate_files()
            
            # Validate result if requested
            if validate_after:
                validation_errors = await self._validate_migration()
                migration_result.errors.extend(validation_errors)
            
            # Create migration metadata
            await self._create_migration_metadata(migration_result, backup_result)
            
            migration_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            migration_result.migration_time_ms = migration_time
            migration_result.backup_path = backup_result.backup_path if backup_result else None
            
            logger.info(
                f"Migration completed: {migration_result.files_migrated} files migrated, "
                f"{migration_result.files_failed} failed in {migration_time:.2f}ms"
            )
            
            return migration_result
            
        except Exception as e:
            migration_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Migration failed: {e}")
            
            return MigrationResult(
                success=False,
                files_migrated=0,
                files_failed=0,
                errors=[f"Migration failed: {e}"],
                migration_time_ms=migration_time
            )
    
    async def _ensure_target_structure(self) -> None:
        """Ensure the target hierarchical directory structure exists."""
        # Primary folders
        primary_folders = ['authentication', 'navigation', 'extraction', 'filtering']
        for folder in primary_folders:
            (self.target_dir / folder).mkdir(parents=True, exist_ok=True)
        
        # Secondary folders in extraction
        secondary_folders = ['match_list', 'match_summary', 'match_h2h', 'match_odds', 'match_stats']
        extraction_dir = self.target_dir / 'extraction'
        for folder in secondary_folders:
            (extraction_dir / folder).mkdir(parents=True, exist_ok=True)
        
        # Tertiary folders in match_stats
        tertiary_folders = ['inc_ot', 'ft', 'q1', 'q2', 'q3', 'q4']
        match_stats_dir = extraction_dir / 'match_stats'
        for folder in tertiary_folders:
            (match_stats_dir / folder).mkdir(parents=True, exist_ok=True)
    
    async def _migrate_files(self) -> MigrationResult:
        """Migrate individual files from flat to hierarchical structure."""
        files_migrated = 0
        files_failed = 0
        errors = []
        warnings = []
        
        # Get all YAML files
        yaml_files = list(self.source_dir.glob("*.yaml")) + list(self.source_dir.glob("*.yml"))
        
        for yaml_file in yaml_files:
            try:
                # Determine target context
                target_context = self._determine_target_context(yaml_file)
                
                if target_context:
                    success = await self._migrate_single_file(yaml_file, target_context)
                    if success:
                        files_migrated += 1
                    else:
                        files_failed += 1
                        errors.append(f"Failed to migrate {yaml_file.name}")
                else:
                    # Unknown context - place in navigation as fallback
                    target_context = {
                        'primary': 'navigation',
                        'secondary': None,
                        'tertiary': None
                    }
                    success = await self._migrate_single_file(yaml_file, target_context)
                    if success:
                        files_migrated += 1
                        warnings.append(f"Context unclear for {yaml_file.name}, placed in navigation")
                    else:
                        files_failed += 1
                        errors.append(f"Failed to migrate {yaml_file.name}")
                        
            except Exception as e:
                files_failed += 1
                errors.append(f"Error migrating {yaml_file.name}: {e}")
                logger.error(f"Migration error for {yaml_file.name}: {e}")
        
        return MigrationResult(
            success=files_failed == 0,
            files_migrated=files_migrated,
            files_failed=files_failed,
            errors=errors,
            warnings=warnings
        )
    
    def _determine_target_context(self, yaml_file: Path) -> Optional[Dict[str, Any]]:
        """Determine the target context for a file based on its name and content."""
        filename = yaml_file.stem.lower()
        
        # Check filename patterns
        for context_name, context_info in self.context_mappings.items():
            for pattern in context_info['patterns']:
                import re
                if re.search(pattern, filename):
                    return {
                        'primary': context_info['primary'],
                        'secondary': context_info.get('secondary'),
                        'tertiary': context_info.get('tertiary')
                    }
        
        # Check file content for additional clues
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            # Look for context indicators in content
            for context_name, context_info in self.context_mappings.items():
                for pattern in context_info['patterns']:
                    if re.search(pattern, content):
                        return {
                            'primary': context_info['primary'],
                            'secondary': context_info.get('secondary'),
                            'tertiary': context_info.get('tertiary')
                        }
        
        except Exception as e:
            logger.warning(f"Failed to read {yaml_file.name} for context detection: {e}")
        
        return None
    
    async def _migrate_single_file(
        self,
        source_file: Path,
        target_context: Dict[str, Any]
    ) -> bool:
        """
        Migrate a single file to its target context.
        
        Args:
            source_file: Source file path
            target_context: Target context information
            
        Returns:
            bool: True if migration was successful
        """
        try:
            # Determine target directory
            target_dir = self.target_dir / target_context['primary']
            if target_context.get('secondary'):
                target_dir = target_dir / target_context['secondary']
            if target_context.get('tertiary'):
                target_dir = target_dir / target_context['tertiary']
            
            # Copy file
            target_file = target_dir / source_file.name
            
            # Read and potentially modify the file content
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add migration metadata
            modified_content = await self._add_migration_metadata(content, target_context)
            
            # Write to target location
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            logger.debug(f"Migrated {source_file.name} -> {target_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate {source_file.name}: {e}")
            return False
    
    async def _add_migration_metadata(
        self,
        content: str,
        target_context: Dict[str, Any]
    ) -> str:
        """
        Add migration metadata to YAML content.
        
        Args:
            content: Original YAML content
            target_context: Target context information
            
        Returns:
            str: Modified content with migration metadata
        """
        try:
            # Parse YAML
            data = yaml.safe_load(content) or {}
            
            # Add migration metadata
            migration_metadata = {
                'migrated_from_flat': True,
                'migration_date': datetime.utcnow().isoformat(),
                'original_context': 'flat',
                'target_context': {
                    'primary': target_context['primary'],
                    'secondary': target_context.get('secondary'),
                    'tertiary': target_context.get('tertiary')
                }
            }
            
            if 'metadata' not in data:
                data['metadata'] = {}
            
            data['metadata'].update(migration_metadata)
            
            # Convert back to YAML
            return yaml.dump(data, default_flow_style=False, sort_keys=False)
            
        except Exception as e:
            logger.error(f"Failed to add migration metadata: {e}")
            return content
    
    async def _validate_migration(self) -> List[str]:
        """Validate the migrated structure."""
        errors = []
        
        try:
            # Validate hierarchical structure
            structure_report = validate_selector_structure(self.target_dir)
            
            if not structure_report.is_valid:
                for error in structure_report.errors:
                    errors.append(f"Structure validation: {error.message}")
            
            # Validate naming conventions
            naming_report = validate_selector_naming(self.target_dir)
            
            if not naming_report.is_valid:
                for violation in naming_report.violations:
                    if violation.severity == "error":
                        errors.append(f"Naming convention: {violation.violation_type} - {violation.actual_name}")
        
        except Exception as e:
            errors.append(f"Validation failed: {e}")
        
        return errors
    
    async def _create_migration_metadata(
        self,
        migration_result: MigrationResult,
        backup_result: Optional[BackupResult]
    ) -> None:
        """Create metadata file for the migration."""
        metadata = {
            "migration_completed_at": datetime.utcnow().isoformat(),
            "source_directory": str(self.source_dir),
            "target_directory": str(self.target_dir),
            "files_migrated": migration_result.files_migrated,
            "files_failed": migration_result.files_failed,
            "migration_time_ms": migration_result.migration_time_ms,
            "errors": migration_result.errors,
            "warnings": migration_result.warnings,
            "backup_info": {
                "backup_path": str(backup_result.backup_path) if backup_result else None,
                "files_backed_up": backup_result.files_backed_up if backup_result else 0,
                "backup_size_mb": backup_result.backup_size_mb if backup_result else 0.0,
                "checksum": backup_result.checksum if backup_result else None
            } if backup_result else None
        }
        
        metadata_file = self.target_dir / 'migration_metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)


class MigrationValidator:
    """
    Validates migration results and detects conflicts.
    """
    
    def __init__(self, target_dir: Path):
        """
        Initialize migration validator.
        
        Args:
            target_dir: Directory containing migrated selectors
        """
        self.target_dir = Path(target_dir)
    
    async def validate_migration(
        self,
        source_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Validate the migration result.
        
        Args:
            source_dir: Original source directory for comparison
            
        Returns:
            Dict[str, Any]: Validation results
        """
        validation_results = {
            "structure_valid": False,
            "naming_valid": False,
            "completeness": {},
            "conflicts": [],
            "recommendations": []
        }
        
        try:
            # Validate structure
            structure_report = validate_selector_structure(self.target_dir)
            validation_results["structure_valid"] = structure_report.is_valid
            validation_results["structure_errors"] = [
                {
                    "level": error.level.value,
                    "message": error.message,
                    "path": str(error.path) if error.path else None,
                    "suggestion": error.suggestion
                }
                for error in structure_report.errors
            ]
            
            # Validate naming conventions
            naming_report = validate_selector_naming(self.target_dir)
            validation_results["naming_valid"] = naming_report.is_valid
            validation_results["naming_violations"] = [
                {
                    "file": str(violation.file_path),
                    "type": violation.violation_type,
                    "actual": violation.actual_name,
                    "suggestion": violation.suggestion
                }
                for violation in naming_report.violations
            ]
            
            # Check completeness
            validation_results["completeness"] = await self._check_completeness()
            
            # Detect conflicts
            if source_dir:
                validation_results["conflicts"] = await self._detect_conflicts(source_dir)
            
            # Generate recommendations
            validation_results["recommendations"] = self._generate_recommendations(validation_results)
            
        except Exception as e:
            validation_results["validation_error"] = str(e)
        
        return validation_results
    
    async def _check_completeness(self) -> Dict[str, Any]:
        """Check if all required contexts have selectors."""
        completeness = {
            "primary_contexts": {},
            "secondary_contexts": {},
            "tertiary_contexts": {},
            "missing_contexts": []
        }
        
        # Check primary contexts
        required_primary = ['authentication', 'navigation', 'extraction', 'filtering']
        for context in required_primary:
            context_dir = self.target_dir / context
            if context_dir.exists():
                yaml_files = list(context_dir.glob("*.yaml")) + list(context_dir.glob("*.yml"))
                completeness["primary_contexts"][context] = len(yaml_files)
            else:
                completeness["primary_contexts"][context] = 0
                completeness["missing_contexts"].append(f"Primary: {context}")
        
        # Check secondary contexts in extraction
        extraction_dir = self.target_dir / 'extraction'
        if extraction_dir.exists():
            required_secondary = ['match_list', 'match_summary', 'match_h2h', 'match_odds', 'match_stats']
            for context in required_secondary:
                context_dir = extraction_dir / context
                if context_dir.exists():
                    yaml_files = list(context_dir.glob("*.yaml")) + list(context_dir.glob("*.yml"))
                    completeness["secondary_contexts"][context] = len(yaml_files)
                else:
                    completeness["secondary_contexts"][context] = 0
                    completeness["missing_contexts"].append(f"Secondary: {context}")
            
            # Check tertiary contexts in match_stats
            match_stats_dir = extraction_dir / 'match_stats'
            if match_stats_dir.exists():
                required_tertiary = ['inc_ot', 'ft', 'q1', 'q2', 'q3', 'q4']
                for context in required_tertiary:
                    context_dir = match_stats_dir / context
                    if context_dir.exists():
                        yaml_files = list(context_dir.glob("*.yaml")) + list(context_dir.glob("*.yml"))
                        completeness["tertiary_contexts"][context] = len(yaml_files)
                    else:
                        completeness["tertiary_contexts"][context] = 0
                        completeness["missing_contexts"].append(f"Tertiary: {context}")
        
        return completeness
    
    async def _detect_conflicts(self, source_dir: Path) -> List[Dict[str, Any]]:
        """Detect potential conflicts between source and migrated files."""
        conflicts = []
        
        try:
            # Get source files
            source_files = list(source_dir.glob("*.yaml")) + list(source_dir.glob("*.yml"))
            source_names = {f.name for f in source_files}
            
            # Get migrated files
            migrated_files = list(self.target_dir.rglob("*.yaml")) + list(self.target_dir.rglob("*.yml"))
            migrated_names = {f.name for f in migrated_files}
            
            # Check for duplicate names
            duplicate_names = source_names & migrated_names
            for name in duplicate_names:
                conflicts.append({
                    "type": "duplicate_name",
                    "filename": name,
                    "source_path": str(source_dir / name),
                    "target_paths": [str(f) for f in migrated_files if f.name == name]
                })
            
            # Check for content conflicts
            for source_file in source_files:
                if source_file.name in migrated_names:
                    # Compare content
                    source_content = source_file.read_text(encoding='utf-8')
                    
                    for migrated_file in migrated_files:
                        if migrated_file.name == source_file.name:
                            migrated_content = migrated_file.read_text(encoding='utf-8')
                            
                            if source_content != migrated_content:
                                conflicts.append({
                                    "type": "content_difference",
                                    "filename": source_file.name,
                                    "source_path": str(source_file),
                                    "target_path": str(migrated_file)
                                })
                            break
        
        except Exception as e:
            conflicts.append({
                "type": "detection_error",
                "error": str(e)
            })
        
        return conflicts
    
    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Structure recommendations
        if not validation_results.get("structure_valid", True):
            recommendations.append("Fix structural issues identified in validation")
        
        # Naming recommendations
        if not validation_results.get("naming_valid", True):
            recommendations.append("Update file naming to follow kebab-case convention")
        
        # Completeness recommendations
        completeness = validation_results.get("completeness", {})
        missing_contexts = completeness.get("missing_contexts", [])
        if missing_contexts:
            recommendations.append(f"Add missing contexts: {', '.join(missing_contexts)}")
        
        # Conflict recommendations
        conflicts = validation_results.get("conflicts", [])
        if conflicts:
            recommendations.append("Resolve file conflicts between source and target")
        
        return recommendations


# Convenience functions
async def create_backup(source_dir: Path, backup_root: Path) -> BackupResult:
    """Create a backup of selector files."""
    backup_manager = SelectorBackupManager(backup_root)
    return await backup_manager.create_backup(source_dir)


async def migrate_flat_to_hierarchical(
    source_dir: Path,
    target_dir: Path,
    create_backup: bool = True
) -> MigrationResult:
    """Migrate from flat to hierarchical structure."""
    migrator = FlatToHierarchicalMigrator(source_dir, target_dir)
    return await migrator.migrate(create_backup=create_backup)


async def validate_migration(target_dir: Path, source_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Validate migration results."""
    validator = MigrationValidator(target_dir)
    return await validator.validate_migration(source_dir)
