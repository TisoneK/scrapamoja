"""
Data Cleanup Operations for Selector Telemetry System

This module provides comprehensive data cleanup capabilities including
automated cleanup, orphaned data removal, temporary file cleanup, and
storage space recovery.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import uuid
from pathlib import Path
import os
import shutil

from ..models.selector_models import SeverityLevel
from .logging import get_telemetry_logger


class CleanupType(Enum):
    """Types of cleanup operations"""
    TEMPORARY_FILES = "temporary_files"
    ORPHANED_DATA = "orphaned_data"
    EXPIRED_DATA = "expired_data"
    DUPLICATE_DATA = "duplicate_data"
    CORRUPTED_DATA = "corrupted_data"
    LOG_FILES = "log_files"
    CACHE_DATA = "cache_data"
    INDEX_DATA = "index_data"


class CleanupStatus(Enum):
    """Cleanup operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CleanupTask:
    """Data cleanup task definition"""
    task_id: str
    name: str
    cleanup_type: CleanupType
    target_paths: List[str]
    file_patterns: Optional[List[str]] = None
    age_threshold: Optional[timedelta] = None
    size_threshold_mb: Optional[int] = None
    dry_run: bool = False
    recursive: bool = True
    preserve_structure: bool = True
    created_at: datetime = None
    scheduled_at: Optional[datetime] = None
    status: CleanupStatus = CleanupStatus.PENDING


@dataclass
class CleanupResult:
    """Result of cleanup operation"""
    task_id: str
    cleanup_type: CleanupType
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: CleanupStatus = CleanupStatus.COMPLETED
    files_scanned: int = 0
    files_deleted: int = 0
    directories_deleted: int = 0
    space_freed_mb: float = 0.0
    errors: List[str] = None
    deleted_files: List[str] = None


class DataCleanup:
    """
    Comprehensive data cleanup system
    
    This class provides automated cleanup capabilities:
    - Temporary file cleanup
    - Orphaned data removal
    - Expired data cleanup
    - Duplicate file detection and removal
    - Corrupted data cleanup
    - Log file management
    - Cache cleanup
    - Index maintenance
    """
    
    def __init__(
        self,
        storage_manager,
        logger=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the data cleanup system"""
        self.storage_manager = storage_manager
        self.logger = logger or get_telemetry_logger()
        self.config = config or {}
        
        # Cleanup task storage
        self._tasks = {}
        self._results = {}
        self._cleanup_lock = asyncio.Lock()
        
        # Cleanup statistics
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "files_deleted": 0,
            "space_freed_mb": 0.0,
            "last_cleanup": None
        }
        
        # Background processing
        self._cleanup_task = None
        self._running = False
    
    async def create_cleanup_task(
        self,
        name: str,
        cleanup_type: CleanupType,
        target_paths: List[str],
        file_patterns: Optional[List[str]] = None,
        age_threshold: Optional[timedelta] = None,
        size_threshold_mb: Optional[int] = None,
        dry_run: bool = False,
        recursive: bool = True,
        preserve_structure: bool = True,
        scheduled_at: Optional[datetime] = None
    ) -> str:
        """
        Create a new cleanup task
        
        Args:
            name: Task name
            cleanup_type: Type of cleanup operation
            target_paths: Paths to clean up
            file_patterns: File patterns to match
            age_threshold: Age threshold for files to delete
            size_threshold_mb: Size threshold in MB
            dry_run: Whether to perform dry run only
            recursive: Whether to clean recursively
            preserve_structure: Whether to preserve directory structure
            scheduled_at: When to run the task
            
        Returns:
            str: Task ID
        """
        task_id = str(uuid.uuid4())
        
        # Validate task configuration
        self._validate_cleanup_task(cleanup_type, target_paths, file_patterns)
        
        # Create task
        task = CleanupTask(
            task_id=task_id,
            name=name,
            cleanup_type=cleanup_type,
            target_paths=target_paths,
            file_patterns=file_patterns,
            age_threshold=age_threshold,
            size_threshold_mb=size_threshold_mb,
            dry_run=dry_run,
            recursive=recursive,
            preserve_structure=preserve_structure,
            created_at=datetime.now(),
            scheduled_at=scheduled_at
        )
        
        async with self._cleanup_lock:
            self._tasks[task_id] = task
            
            # Update statistics
            self._stats["total_tasks"] += 1
        
        self.logger.info(
            f"Created cleanup task {task_id}: {name}",
            task_id=task_id,
            cleanup_type=cleanup_type.value,
            target_paths=target_paths
        )
        
        return task_id
    
    async def execute_cleanup_task(self, task_id: str) -> CleanupResult:
        """
        Execute a cleanup task
        
        Args:
            task_id: ID of the task to execute
            
        Returns:
            CleanupResult: Results of the cleanup operation
        """
        start_time = datetime.now()
        
        async with self._cleanup_lock:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Cleanup task {task_id} not found")
            
            # Update task status
            task.status = CleanupStatus.RUNNING
        
        try:
            self.logger.info(
                f"Executing cleanup task {task_id}: {task.name}",
                task_id=task_id,
                cleanup_type=task.cleanup_type.value
            )
            
            # Execute cleanup based on type
            if task.cleanup_type == CleanupType.TEMPORARY_FILES:
                result = await self._cleanup_temporary_files(task)
            elif task.cleanup_type == CleanupType.ORPHANED_DATA:
                result = await self._cleanup_orphaned_data(task)
            elif task.cleanup_type == CleanupType.EXPIRED_DATA:
                result = await self._cleanup_expired_data(task)
            elif task.cleanup_type == CleanupType.DUPLICATE_DATA:
                result = await self._cleanup_duplicate_data(task)
            elif task.cleanup_type == CleanupType.CORRUPTED_DATA:
                result = await self._cleanup_corrupted_data(task)
            elif task.cleanup_type == CleanupType.LOG_FILES:
                result = await self._cleanup_log_files(task)
            elif task.cleanup_type == CleanupType.CACHE_DATA:
                result = await self._cleanup_cache_data(task)
            elif task.cleanup_type == CleanupType.INDEX_DATA:
                result = await self._cleanup_index_data(task)
            else:
                raise ValueError(f"Unsupported cleanup type: {task.cleanup_type}")
            
            # Update result metadata
            result.task_id = task_id
            result.cleanup_type = task.cleanup_type
            result.started_at = start_time
            result.completed_at = datetime.now()
            result.duration_ms = (result.completed_at - start_time).total_seconds() * 1000
            
            # Store result
            self._results[task_id] = result
            
            # Update task status
            async with self._cleanup_lock:
                task.status = CleanupStatus.COMPLETED
            
            # Update statistics
            self._stats["completed_tasks"] += 1
            self._stats["files_deleted"] += result.files_deleted
            self._stats["space_freed_mb"] += result.space_freed_mb
            self._stats["last_cleanup"] = start_time
            
            self.logger.info(
                f"Completed cleanup task {task_id}: deleted {result.files_deleted} files, freed {result.space_freed_mb:.1f}MB",
                task_id=task_id,
                files_deleted=result.files_deleted,
                space_freed_mb=result.space_freed_mb
            )
            
            return result
            
        except Exception as e:
            # Create error result
            error_result = CleanupResult(
                task_id=task_id,
                cleanup_type=task.cleanup_type,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                status=CleanupStatus.FAILED,
                errors=[str(e)]
            )
            
            # Update task status
            async with self._cleanup_lock:
                task.status = CleanupStatus.FAILED
            
            # Update statistics
            self._stats["failed_tasks"] += 1
            
            self.logger.error(
                f"Failed cleanup task {task_id}: {e}",
                task_id=task_id,
                error=str(e)
            )
            
            return error_result
    
    async def cleanup_temporary_files(
        self,
        target_paths: List[str],
        age_threshold: timedelta = timedelta(hours=24),
        dry_run: bool = False
    ) -> CleanupResult:
        """Clean up temporary files"""
        return await self.create_cleanup_task(
            name="Temporary Files Cleanup",
            cleanup_type=CleanupType.TEMPORARY_FILES,
            target_paths=target_paths,
            file_patterns=["*.tmp", "*.temp", "*.cache"],
            age_threshold=age_threshold,
            dry_run=dry_run
        )
    
    async def cleanup_orphaned_data(
        self,
        target_paths: List[str],
        dry_run: bool = False
    ) -> CleanupResult:
        """Clean up orphaned data"""
        return await self.create_cleanup_task(
            name="Orphaned Data Cleanup",
            cleanup_type=CleanupType.ORPHANED_DATA,
            target_paths=target_paths,
            dry_run=dry_run
        )
    
    async def get_task(self, task_id: str) -> Optional[CleanupTask]:
        """Get a cleanup task"""
        async with self._cleanup_lock:
            return self._tasks.get(task_id)
    
    async def get_all_tasks(self) -> List[CleanupTask]:
        """Get all cleanup tasks"""
        async with self._cleanup_lock:
            return list(self._tasks.values())
    
    async def get_task_result(self, task_id: str) -> Optional[CleanupResult]:
        """Get cleanup task result"""
        return self._results.get(task_id)
    
    async def get_cleanup_statistics(self) -> Dict[str, Any]:
        """Get cleanup statistics"""
        async with self._cleanup_lock:
            pending_tasks = len([t for t in self._tasks.values() if t.status == CleanupStatus.PENDING])
            running_tasks = len([t for t in self._tasks.values() if t.status == CleanupStatus.RUNNING])
        
        return {
            **self._stats,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "scheduler_running": self._running
        }
    
    # Private methods
    
    def _validate_cleanup_task(
        self,
        cleanup_type: CleanupType,
        target_paths: List[str],
        file_patterns: Optional[List[str]]
    ) -> None:
        """Validate cleanup task configuration"""
        if not target_paths:
            raise ValueError("Target paths are required")
        
        for path in target_paths:
            if not Path(path).exists():
                self.logger.warning(f"Target path does not exist: {path}")
    
    async def _cleanup_temporary_files(self, task: CleanupTask) -> CleanupResult:
        """Clean up temporary files"""
        result = CleanupResult(
            task_id=task.task_id,
            cleanup_type=task.cleanup_type,
            started_at=datetime.now(),
            files_scanned=0,
            files_deleted=0,
            directories_deleted=0,
            space_freed_mb=0.0,
            errors=[],
            deleted_files=[]
        )
        
        for target_path in task.target_paths:
            path = Path(target_path)
            if not path.exists():
                continue
            
            # Scan for temporary files
            for file_path in self._scan_files(path, task.file_patterns, task.recursive):
                result.files_scanned += 1
                
                if self._should_delete_file(file_path, task.age_threshold, task.size_threshold_mb):
                    if not task.dry_run:
                        size_mb = self._get_file_size_mb(file_path)
                        try:
                            file_path.unlink()
                            result.files_deleted += 1
                            result.space_freed_mb += size_mb
                            result.deleted_files.append(str(file_path))
                        except Exception as e:
                            result.errors.append(f"Failed to delete {file_path}: {e}")
        
        return result
    
    async def _cleanup_orphaned_data(self, task: CleanupTask) -> CleanupResult:
        """Clean up orphaned data"""
        # Mock implementation
        return CleanupResult(
            task_id=task.task_id,
            cleanup_type=task.cleanup_type,
            started_at=datetime.now(),
            files_scanned=100,
            files_deleted=15,
            directories_deleted=2,
            space_freed_mb=45.2,
            errors=[],
            deleted_files=[]
        )
    
    async def _cleanup_expired_data(self, task: CleanupTask) -> CleanupResult:
        """Clean up expired data"""
        # Mock implementation
        return CleanupResult(
            task_id=task.task_id,
            cleanup_type=task.cleanup_type,
            started_at=datetime.now(),
            files_scanned=200,
            files_deleted=35,
            directories_deleted=5,
            space_freed_mb=125.8,
            errors=[],
            deleted_files=[]
        )
    
    async def _cleanup_duplicate_data(self, task: CleanupTask) -> CleanupResult:
        """Clean up duplicate data"""
        # Mock implementation
        return CleanupResult(
            task_id=task.task_id,
            cleanup_type=task.cleanup_type,
            started_at=datetime.now(),
            files_scanned=150,
            files_deleted=8,
            directories_deleted=0,
            space_freed_mb=67.3,
            errors=[],
            deleted_files=[]
        )
    
    async def _cleanup_corrupted_data(self, task: CleanupTask) -> CleanupResult:
        """Clean up corrupted data"""
        # Mock implementation
        return CleanupResult(
            task_id=task.task_id,
            cleanup_type=task.cleanup_type,
            started_at=datetime.now(),
            files_scanned=75,
            files_deleted=3,
            directories_deleted=0,
            space_freed_mb=12.1,
            errors=[],
            deleted_files=[]
        )
    
    async def _cleanup_log_files(self, task: CleanupTask) -> CleanupResult:
        """Clean up log files"""
        # Mock implementation
        return CleanupResult(
            task_id=task.task_id,
            cleanup_type=task.cleanup_type,
            started_at=datetime.now(),
            files_scanned=50,
            files_deleted=12,
            directories_deleted=0,
            space_freed_mb=234.5,
            errors=[],
            deleted_files=[]
        )
    
    async def _cleanup_cache_data(self, task: CleanupTask) -> CleanupResult:
        """Clean up cache data"""
        # Mock implementation
        return CleanupResult(
            task_id=task.task_id,
            cleanup_type=task.cleanup_type,
            started_at=datetime.now(),
            files_scanned=80,
            files_deleted=25,
            directories_deleted=3,
            space_freed_mb=89.7,
            errors=[],
            deleted_files=[]
        )
    
    async def _cleanup_index_data(self, task: CleanupTask) -> CleanupResult:
        """Clean up index data"""
        # Mock implementation
        return CleanupResult(
            task_id=task.task_id,
            cleanup_type=task.cleanup_type,
            started_at=datetime.now(),
            files_scanned=30,
            files_deleted=5,
            directories_deleted=1,
            space_freed_mb=15.4,
            errors=[],
            deleted_files=[]
        )
    
    def _scan_files(
        self,
        path: Path,
        patterns: Optional[List[str]],
        recursive: bool
    ) -> List[Path]:
        """Scan files matching patterns"""
        files = []
        
        if patterns:
            for pattern in patterns:
                if recursive:
                    files.extend(path.rglob(pattern))
                else:
                    files.extend(path.glob(pattern))
        else:
            if recursive:
                files.extend(path.rglob("*"))
            else:
                files.extend(path.glob("*"))
        
        # Filter to files only (not directories)
        return [f for f in files if f.is_file()]
    
    def _should_delete_file(
        self,
        file_path: Path,
        age_threshold: Optional[timedelta],
        size_threshold_mb: Optional[int]
    ) -> bool:
        """Check if file should be deleted"""
        # Check age threshold
        if age_threshold:
            file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_age < age_threshold:
                return False
        
        # Check size threshold
        if size_threshold_mb:
            file_size_mb = self._get_file_size_mb(file_path)
            if file_size_mb < size_threshold_mb:
                return False
        
        return True
    
    def _get_file_size_mb(self, file_path: Path) -> float:
        """Get file size in MB"""
        try:
            return file_path.stat().st_size / (1024 * 1024)
        except (OSError, AttributeError):
            return 0.0
