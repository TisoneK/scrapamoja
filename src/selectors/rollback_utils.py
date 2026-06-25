"""
Rollback utilities for failed selector migrations.

This module provides utilities to rollback from a failed migration
to the previous working state using backup files.
"""

import asyncio
import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .migration_utils import BackupResult, SelectorBackupManager


logger = logging.getLogger(__name__)


@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    success: bool
    files_restored: int
    files_failed: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    rollback_time_ms: float = 0.0
    backup_used: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackPoint:
    """Represents a rollback point with metadata."""
    timestamp: datetime
    backup_path: Path
    description: str
    migration_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RollbackManager:
    """
    Manages rollback operations for failed migrations.
    """
    
    def __init__(self, backup_root: Path):
        """
        Initialize rollback manager.
        
        Args:
            backup_root: Root directory containing backups
        """
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        
        # Rollback history
        self.rollback_history: List[RollbackPoint] = []
        self.rollback_log_file = self.backup_root / "rollback_history.json"
        
        logger.info(f"RollbackManager initialized with backup root: {backup_root}")
        
        # Load existing rollback history
        self._load_rollback_history()
    
    def _load_rollback_history(self) -> None:
        """Load rollback history from file."""
        if self.rollback_log_file.exists():
            try:
                with open(self.rollback_log_file, 'r') as f:
                    data = json.load(f)
                    
                # Convert dict entries to RollbackPoint objects
                for entry in data.get("rollbacks", []):
                    rollback_point = RollbackPoint(
                        timestamp=datetime.fromisoformat(entry["timestamp"]),
                        backup_path=Path(entry["backup_path"]),
                        description=entry["description"],
                        migration_id=entry.get("migration_id"),
                        metadata=entry.get("metadata", {})
                    )
                    self.rollback_history.append(rollback_point)
                    
                logger.info(f"Loaded {len(self.rollback_history)} rollback points from history")
                
            except Exception as e:
                logger.warning(f"Failed to load rollback history: {e}")
    
    def _save_rollback_history(self) -> None:
        """Save rollback history to file."""
        try:
            history_data = {
                "last_updated": datetime.utcnow().isoformat(),
                "rollbacks": [
                    {
                        "timestamp": point.timestamp.isoformat(),
                        "backup_path": str(point.backup_path),
                        "description": point.description,
                        "migration_id": point.migration_id,
                        "metadata": point.metadata
                    }
                    for point in self.rollback_history
                ]
            }
            
            with open(self.rollback_log_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save rollback history: {e}")
    
    async def list_available_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups for rollback.
        
        Returns:
            List[Dict[str, Any]]: List of available backups
        """
        backup_manager = SelectorBackupManager(self.backup_root)
        return await backup_manager.list_backups()
    
    async def create_rollback_point(
        self,
        backup_path: Path,
        description: str,
        migration_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RollbackPoint:
        """
        Create a rollback point record.
        
        Args:
            backup_path: Path to the backup
            description: Description of the rollback point
            migration_id: ID of the migration being rolled back
            metadata: Additional metadata
            
        Returns:
            RollbackPoint: Created rollback point
        """
        rollback_point = RollbackPoint(
            timestamp=datetime.utcnow(),
            backup_path=backup_path,
            description=description,
            migration_id=migration_id,
            metadata=metadata or {}
        )
        
        self.rollback_history.append(rollback_point)
        self._save_rollback_history()
        
        logger.info(f"Created rollback point: {description}")
        return rollback_point
    
    async def rollback_to_backup(
        self,
        backup_name: str,
        target_dir: Path,
        create_rollback_point: bool = True,
        backup_description: str = "Manual rollback"
    ) -> RollbackResult:
        """
        Rollback to a specific backup.
        
        Args:
            backup_name: Name of the backup to rollback to
            target_dir: Directory to restore to
            create_rollback_point: Whether to create a rollback point record
            backup_description: Description for the rollback point
            
        Returns:
            RollbackResult: Result of rollback operation
        """
        start_time = datetime.utcnow()
        
        try:
            # Find backup directory
            backup_path = self.backup_root / backup_name
            
            if not backup_path.exists():
                return RollbackResult(
                    success=False,
                    files_restored=0,
                    files_failed=0,
                    errors=[f"Backup directory does not exist: {backup_name}"]
                )
            
            # Validate backup integrity
            validation_result = await self._validate_backup_integrity(backup_path)
            if not validation_result["valid"]:
                return RollbackResult(
                    success=False,
                    files_restored=0,
                    files_failed=0,
                    errors=[f"Backup validation failed: {validation_result['error']}"]
                )
            
            # Clear target directory
            if target_dir.exists():
                # Create backup of current state before rollback
                current_backup = target_dir.parent / f"pre_rollback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                shutil.move(str(target_dir), str(current_backup))
                logger.info(f"Current state backed up to: {current_backup}")
            
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Restore files from backup
            files_restored = 0
            files_failed = 0
            
            for item in backup_path.iterdir():
                if item.name == 'backup_metadata.json':
                    continue  # Skip metadata file
                
                try:
                    if item.is_file():
                        shutil.copy2(item, target_dir / item.name)
                        files_restored += 1
                    elif item.is_dir():
                        shutil.copytree(item, target_dir / item.name)
                        files_restored += 1  # Count directory as one item
                        
                except Exception as e:
                    files_failed += 1
                    logger.error(f"Failed to restore {item.name}: {e}")
            
            # Create rollback point record
            if create_rollback_point:
                await self.create_rollback_point(
                    backup_path=backup_path,
                    description=backup_description,
                    migration_id=self._extract_migration_id_from_backup(backup_path)
                )
            
            rollback_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Create rollback metadata
            rollback_metadata = {
                "rollback_completed_at": datetime.utcnow().isoformat(),
                "backup_name": backup_name,
                "target_directory": str(target_dir),
                "files_restored": files_restored,
                "files_failed": files_failed,
                "rollback_time_ms": rollback_time,
                "backup_validation": validation_result
            }
            
            metadata_file = target_dir / "rollback_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(rollback_metadata, f, indent=2)
            
            logger.info(
                f"Rollback completed: {files_restored} files restored, {files_failed} failed "
                f"in {rollback_time:.2f}ms"
            )
            
            return RollbackResult(
                success=files_failed == 0,
                files_restored=files_restored,
                files_failed=files_failed,
                rollback_time_ms=rollback_time,
                backup_used=backup_name,
                metadata=rollback_metadata
            )
            
        except Exception as e:
            rollback_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Rollback failed: {e}")
            
            return RollbackResult(
                success=False,
                files_restored=0,
                files_failed=0,
                errors=[f"Rollback operation failed: {e}"],
                rollback_time_ms=rollback_time
            )
    
    async def rollback_to_latest_backup(self, target_dir: Path) -> RollbackResult:
        """
        Rollback to the most recent backup.
        
        Args:
            target_dir: Directory to restore to
            
        Returns:
            RollbackResult: Result of rollback operation
        """
        try:
            # Get available backups
            backups = await self.list_available_backups()
            
            if not backups:
                return RollbackResult(
                    success=False,
                    files_restored=0,
                    files_failed=0,
                    errors=["No backups available for rollback"]
                )
            
            # Find the most recent backup
            latest_backup = max(backups, key=lambda b: b.get('created_at', 0))
            backup_name = latest_backup['name']
            
            logger.info(f"Rolling back to latest backup: {backup_name}")
            return await self.rollback_to_backup(backup_name, target_dir)
            
        except Exception as e:
            logger.error(f"Failed to rollback to latest backup: {e}")
            return RollbackResult(
                success=False,
                files_restored=0,
                files_failed=0,
                errors=[f"Rollback to latest failed: {e}"]
            )
    
    async def rollback_to_point(
        self,
        rollback_point: RollbackPoint,
        target_dir: Path
    ) -> RollbackResult:
        """
        Rollback to a specific rollback point.
        
        Args:
            rollback_point: Rollback point to restore to
            target_dir: Directory to restore to
            
        Returns:
            RollbackResult: Result of rollback operation
        """
        logger.info(f"Rolling back to point: {rollback_point.description}")
        
        return await self.rollback_to_backup(
            backup_name=rollback_point.backup_path.name,
            target_dir=target_dir,
            create_rollback_point=False,  # Don't create duplicate record
            backup_description=f"Rollback to: {rollback_point.description}"
        )
    
    async def _validate_backup_integrity(self, backup_path: Path) -> Dict[str, Any]:
        """
        Validate the integrity of a backup.
        
        Args:
            backup_path: Path to the backup directory
            
        Returns:
            Dict[str, Any]: Validation result
        """
        try:
            # Check for metadata file
            metadata_file = backup_path / 'backup_metadata.json'
            if not metadata_file.exists():
                return {
                    "valid": False,
                    "error": "Missing backup_metadata.json"
                }
            
            # Load metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Verify files exist
            expected_files = metadata.get('files_backed_up', 0)
            actual_files = 0
            
            yaml_files = list(backup_path.glob("*.yaml")) + list(backup_path.glob("*.yml"))
            for yaml_file in yaml_files:
                if yaml_file.is_file():
                    actual_files += 1
            
            # Verify checksum if available
            expected_checksum = metadata.get('checksum')
            if expected_checksum:
                from .migration_utils import SelectorBackupManager
                backup_manager = SelectorBackupManager(self.backup_root)
                actual_checksum = await backup_manager._calculate_directory_checksum(backup_path)
                
                if actual_checksum != expected_checksum:
                    return {
                        "valid": False,
                        "error": f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}"
                    }
            
            # Check file count
            if actual_files != expected_files:
                return {
                    "valid": False,
                    "error": f"File count mismatch: expected {expected_files}, got {actual_files}"
                }
            
            return {
                "valid": True,
                "metadata": metadata,
                "files_found": actual_files
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {e}"
            }
    
    def _extract_migration_id_from_backup(self, backup_path: Path) -> Optional[str]:
        """Extract migration ID from backup metadata."""
        try:
            metadata_file = backup_path / 'backup_metadata.json'
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    
                # Look for migration info in nested metadata
                backup_info = metadata.get('backup_info', {})
                if isinstance(backup_info, dict):
                    return backup_info.get('migration_id')
                    
        except Exception as e:
            logger.warning(f"Failed to extract migration ID from backup: {e}")
        
        return None
    
    async def get_rollback_history(self, limit: int = 10) -> List[RollbackPoint]:
        """
        Get recent rollback history.
        
        Args:
            limit: Maximum number of rollback points to return
            
        Returns:
            List[RollbackPoint]: Recent rollback points
        """
        # Sort by timestamp (most recent first)
        sorted_history = sorted(
            self.rollback_history,
            key=lambda rp: rp.timestamp,
            reverse=True
        )
        
        return sorted_history[:limit]
    
    async def cleanup_old_backups(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """
        Clean up old backups beyond the retention period.
        
        Args:
            days_to_keep: Number of days to keep backups
            
        Returns:
            Dict[str, Any]: Cleanup results
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        try:
            backups = await self.list_available_backups()
            deleted_backups = []
            total_space_freed = 0
            
            for backup in backups:
                backup_path = self.backup_root / backup['name']
                
                # Check creation time
                created_at = datetime.fromtimestamp(backup.get('created_at', 0))
                
                if created_at < cutoff_date:
                    # Calculate space to be freed
                    backup_size = self._calculate_directory_size(backup_path)
                    total_space_freed += backup_size
                    
                    # Delete backup
                    shutil.rmtree(backup_path)
                    deleted_backups.append(backup['name'])
                    
                    logger.info(f"Deleted old backup: {backup['name']} ({backup_size:.2f}MB)")
            
            # Update rollback history to remove deleted backup references
            self.rollback_history = [
                rp for rp in self.rollback_history
                if rp.backup_path.name not in deleted_backups
            ]
            self._save_rollback_history()
            
            return {
                "success": True,
                "deleted_backups": deleted_backups,
                "total_space_freed_mb": total_space_freed,
                "remaining_backups": len(backups) - len(deleted_backups)
            }
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_directory_size(self, directory: Path) -> float:
        """Calculate directory size in MB."""
        total_size = 0
        
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception:
            pass
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    async def analyze_rollback_feasibility(
        self,
        target_dir: Path,
        backup_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze the feasibility of a rollback operation.
        
        Args:
            target_dir: Directory to rollback to
            backup_name: Specific backup to analyze (latest if None)
            
        Returns:
            Dict[str, Any]: Feasibility analysis
        """
        analysis = {
            "feasible": False,
            "warnings": [],
            "recommendations": [],
            "backup_info": None
        }
        
        try:
            # Get available backups
            backups = await self.list_available_backups()
            
            if not backups:
                analysis["warnings"].append("No backups available for rollback")
                return analysis
            
            # Select backup
            if backup_name:
                backup_info = next((b for b in backups if b['name'] == backup_name), None)
                if not backup_info:
                    analysis["warnings"].append(f"Specified backup not found: {backup_name}")
                    return analysis
            else:
                backup_info = max(backups, key=lambda b: b.get('created_at', 0))
            
            analysis["backup_info"] = backup_info
            
            # Check target directory
            if target_dir.exists():
                # Check if target has uncommitted changes
                analysis["warnings"].append("Target directory exists - current changes will be overwritten")
                analysis["recommendations"].append("Consider committing or backing up current changes first")
            
            # Check backup age
            backup_age = datetime.utcnow() - datetime.fromtimestamp(backup_info.get('created_at', 0))
            if backup_age.days > 90:
                analysis["warnings"].append(f"Backup is quite old ({backup_age.days} days)")
                analysis["recommendations"].append("Consider creating a fresh backup before rollback")
            
            # Check backup integrity
            backup_path = self.backup_root / backup_info['name']
            validation_result = await self._validate_backup_integrity(backup_path)
            
            if not validation_result["valid"]:
                analysis["warnings"].append(f"Backup integrity issues: {validation_result['error']}")
                analysis["recommendations"].append("Use a different backup or recreate from source")
                return analysis
            
            analysis["feasible"] = True
            
        except Exception as e:
            analysis["warnings"].append(f"Analysis failed: {e}")
        
        return analysis


# Convenience functions
async def create_rollback_manager(backup_root: Path) -> RollbackManager:
    """Create a rollback manager instance."""
    return RollbackManager(backup_root)


async def rollback_to_backup(
    backup_root: Path,
    backup_name: str,
    target_dir: Path
) -> RollbackResult:
    """Perform rollback to a specific backup."""
    manager = await create_rollback_manager(backup_root)
    return await manager.rollback_to_backup(backup_name, target_dir)


async def rollback_to_latest_backup(backup_root: Path, target_dir: Path) -> RollbackResult:
    """Rollback to the most recent backup."""
    manager = await create_rollback_manager(backup_root)
    return await manager.rollback_to_latest_backup(target_dir)
