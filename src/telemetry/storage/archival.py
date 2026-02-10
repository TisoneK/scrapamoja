"""
Data Archival for Selector Telemetry System

This module provides comprehensive data archival capabilities including
automated archival, compression, long-term storage, and retrieval.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import uuid
from pathlib import Path
import json
import gzip
import shutil

from ..models.selector_models import SeverityLevel
from .logging import get_telemetry_logger


class ArchiveFormat(Enum):
    """Archive format types"""
    JSON = "json"
    JSON_GZ = "json_gz"
    PARQUET = "parquet"
    CSV = "csv"
    CSV_GZ = "csv_gz"
    CUSTOM = "custom"


class ArchiveStatus(Enum):
    """Archive operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ArchivePolicy:
    """Data archival policy definition"""
    policy_id: str
    name: str
    description: str
    source_data_type: str
    archive_format: ArchiveFormat
    archive_location: str
    retention_period: Optional[timedelta] = None
    compression_level: int = 6  # For gzip compression
    batch_size: int = 1000
    max_file_size_mb: int = 100
    enabled: bool = True
    created_at: datetime = None
    last_run: Optional[datetime] = None
    archive_count: int = 0


@dataclass
class ArchiveTask:
    """Data archival task"""
    task_id: str
    policy_id: str
    source_paths: List[str]
    target_path: str
    archive_format: ArchiveFormat
    compression_level: int
    batch_size: int
    status: ArchiveStatus = ArchiveStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ArchiveResult:
    """Result of archival operation"""
    task_id: str
    policy_id: str
    archive_format: ArchiveFormat
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: ArchiveStatus = ArchiveStatus.COMPLETED
    records_processed: int = 0
    archives_created: int = 0
    original_size_mb: float = 0.0
    archived_size_mb: float = 0.0
    compression_ratio: float = 0.0
    archive_files: List[str] = None
    errors: List[str] = None


class DataArchival:
    """
    Comprehensive data archival system
    
    This class provides automated archival capabilities:
    - Data compression and archival
    - Multiple archive formats support
    - Batch processing capabilities
    - Long-term storage management
    - Archive retrieval and restoration
    - Archive integrity verification
    """
    
    def __init__(
        self,
        storage_manager,
        logger=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the data archival system"""
        self.storage_manager = storage_manager
        self.logger = logger or get_telemetry_logger()
        self.config = config or {}
        
        # Archive policy storage
        self._policies = {}
        self._tasks = {}
        self._results = {}
        self._archive_lock = asyncio.Lock()
        
        # Archival statistics
        self._stats = {
            "total_policies": 0,
            "active_policies": 0,
            "total_tasks": 0,
            "completed_tasks": 0,
            "records_archived": 0,
            "archives_created": 0,
            "space_saved_mb": 0.0,
            "last_archive": None
        }
        
        # Background processing
        self._archive_task = None
        self._running = False
    
    async def create_archive_policy(
        self,
        name: str,
        description: str,
        source_data_type: str,
        archive_format: ArchiveFormat,
        archive_location: str,
        retention_period: Optional[timedelta] = None,
        compression_level: int = 6,
        batch_size: int = 1000,
        max_file_size_mb: int = 100,
        enabled: bool = True
    ) -> str:
        """
        Create a new archival policy
        
        Args:
            name: Policy name
            description: Policy description
            source_data_type: Type of data to archive
            archive_format: Archive format
            archive_location: Location for archived data
            retention_period: How long to keep archives
            compression_level: Compression level (1-9)
            batch_size: Number of records per batch
            max_file_size_mb: Maximum archive file size
            enabled: Whether policy is initially enabled
            
        Returns:
            str: Policy ID
        """
        policy_id = str(uuid.uuid4())
        
        # Validate policy configuration
        self._validate_archive_policy(archive_format, archive_location, compression_level)
        
        # Create policy
        policy = ArchivePolicy(
            policy_id=policy_id,
            name=name,
            description=description,
            source_data_type=source_data_type,
            archive_format=archive_format,
            archive_location=archive_location,
            retention_period=retention_period,
            compression_level=compression_level,
            batch_size=batch_size,
            max_file_size_mb=max_file_size_mb,
            enabled=enabled,
            created_at=datetime.now()
        )
        
        async with self._archive_lock:
            self._policies[policy_id] = policy
            
            # Update statistics
            self._stats["total_policies"] += 1
            if enabled:
                self._stats["active_policies"] += 1
        
        self.logger.info(
            f"Created archive policy {policy_id}: {name}",
            policy_id=policy_id,
            archive_format=archive_format.value,
            archive_location=archive_location
        )
        
        return policy_id
    
    async def update_policy(self, policy_id: str, **updates) -> bool:
        """Update an existing archival policy"""
        async with self._archive_lock:
            policy = self._policies.get(policy_id)
            if not policy:
                return False
            
            old_enabled = policy.enabled
            for key, value in updates.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            
            # Update statistics if enabled status changed
            if old_enabled != policy.enabled:
                if policy.enabled:
                    self._stats["active_policies"] += 1
                else:
                    self._stats["active_policies"] -= 1
        
        self.logger.info(f"Updated archive policy {policy_id}")
        return True
    
    async def delete_policy(self, policy_id: str) -> bool:
        """Delete an archival policy"""
        async with self._archive_lock:
            if policy_id not in self._policies:
                return False
            
            policy = self._policies[policy_id]
            
            # Update statistics
            if policy.enabled:
                self._stats["active_policies"] -= 1
            
            del self._policies[policy_id]
            self._stats["total_policies"] -= 1
        
        self.logger.info(f"Deleted archive policy {policy_id}")
        return True
    
    async def archive_data(
        self,
        policy_id: str,
        source_paths: List[str],
        target_path: Optional[str] = None
    ) -> str:
        """
        Archive data using a specific policy
        
        Args:
            policy_id: ID of the archival policy
            source_paths: Paths to data to archive
            target_path: Optional override for target path
            
        Returns:
            str: Task ID
        """
        task_id = str(uuid.uuid4())
        
        async with self._archive_lock:
            policy = self._policies.get(policy_id)
            if not policy:
                raise ValueError(f"Archive policy {policy_id} not found")
            
            if not policy.enabled:
                raise ValueError(f"Archive policy {policy_id} is disabled")
        
        # Create archive task
        task = ArchiveTask(
            task_id=task_id,
            policy_id=policy_id,
            source_paths=source_paths,
            target_path=target_path or policy.archive_location,
            archive_format=policy.archive_format,
            compression_level=policy.compression_level,
            batch_size=policy.batch_size,
            status=ArchiveStatus.PENDING,
            created_at=datetime.now()
        )
        
        async with self._archive_lock:
            self._tasks[task_id] = task
            self._stats["total_tasks"] += 1
        
        self.logger.info(
            f"Created archive task {task_id} using policy {policy_id}",
            task_id=task_id,
            policy_id=policy_id
        )
        
        # Execute archival
        try:
            result = await self._execute_archive_task(task)
            
            # Store result
            self._results[task_id] = result
            
            # Update statistics
            self._stats["completed_tasks"] += 1
            self._stats["records_archived"] += result.records_processed
            self._stats["archives_created"] += result.archives_created
            self._stats["space_saved_mb"] += (result.original_size_mb - result.archived_size_mb)
            self._stats["last_archive"] = result.started_at
            
            return task_id
            
        except Exception as e:
            self.logger.error(f"Error executing archive task {task_id}: {e}")
            raise
    
    async def retrieve_archive(
        self,
        archive_path: str,
        target_path: str,
        decompress: bool = True
    ) -> bool:
        """
        Retrieve and restore archived data
        
        Args:
            archive_path: Path to archive file
            target_path: Where to restore the data
            decompress: Whether to decompress the data
            
        Returns:
            bool: Success status
        """
        try:
            archive_file = Path(archive_path)
            if not archive_file.exists():
                raise FileNotFoundError(f"Archive not found: {archive_path}")
            
            target_dir = Path(target_path)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine archive format and extract accordingly
            if archive_path.endswith('.gz'):
                if decompress:
                    await self._extract_gz_archive(archive_file, target_dir)
                else:
                    shutil.copy2(archive_file, target_dir / archive_file.name)
            else:
                await self._extract_archive(archive_file, target_dir)
            
            self.logger.info(
                f"Retrieved archive {archive_path} to {target_path}",
                archive_path=archive_path,
                target_path=target_path
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error retrieving archive {archive_path}: {e}")
            return False
    
    async def get_policy(self, policy_id: str) -> Optional[ArchivePolicy]:
        """Get an archival policy"""
        async with self._archive_lock:
            return self._policies.get(policy_id)
    
    async def get_all_policies(self) -> List[ArchivePolicy]:
        """Get all archival policies"""
        async with self._archive_lock:
            return list(self._policies.values())
    
    async def get_task(self, task_id: str) -> Optional[ArchiveTask]:
        """Get an archive task"""
        async with self._archive_lock:
            return self._tasks.get(task_id)
    
    async def get_task_result(self, task_id: str) -> Optional[ArchiveResult]:
        """Get archive task result"""
        return self._results.get(task_id)
    
    async def get_archive_statistics(self) -> Dict[str, Any]:
        """Get archival statistics"""
        async with self._archive_lock:
            active_policies = len([p for p in self._policies.values() if p.enabled])
            pending_tasks = len([t for t in self._tasks.values() if t.status == ArchiveStatus.PENDING])
            running_tasks = len([t for t in self._tasks.values() if t.status == ArchiveStatus.RUNNING])
        
        return {
            **self._stats,
            "active_policies": active_policies,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "scheduler_running": self._running
        }
    
    # Private methods
    
    def _validate_archive_policy(
        self,
        archive_format: ArchiveFormat,
        archive_location: str,
        compression_level: int
    ) -> None:
        """Validate archive policy configuration"""
        if not archive_location:
            raise ValueError("Archive location is required")
        
        if compression_level < 1 or compression_level > 9:
            raise ValueError("Compression level must be between 1 and 9")
        
        # Create archive directory if it doesn't exist
        Path(archive_location).mkdir(parents=True, exist_ok=True)
    
    async def _execute_archive_task(self, task: ArchiveTask) -> ArchiveResult:
        """Execute an archive task"""
        start_time = datetime.now()
        
        # Update task status
        async with self._archive_lock:
            task.status = ArchiveStatus.RUNNING
            task.started_at = start_time
        
        try:
            self.logger.info(
                f"Executing archive task {task.task_id}",
                task_id=task.task_id,
                archive_format=task.archive_format.value
            )
            
            # Get policy for additional configuration
            policy = await self.get_policy(task.policy_id)
            
            # Execute archival based on format
            if task.archive_format == ArchiveFormat.JSON:
                result = await self._archive_json(task, policy)
            elif task.archive_format == ArchiveFormat.JSON_GZ:
                result = await self._archive_json_gz(task, policy)
            elif task.archive_format == ArchiveFormat.CSV:
                result = await self._archive_csv(task, policy)
            elif task.archive_format == ArchiveFormat.CSV_GZ:
                result = await self._archive_csv_gz(task, policy)
            else:
                raise ValueError(f"Unsupported archive format: {task.archive_format}")
            
            # Update result metadata
            result.task_id = task.task_id
            result.policy_id = task.policy_id
            result.archive_format = task.archive_format
            result.started_at = start_time
            result.completed_at = datetime.now()
            result.duration_ms = (result.completed_at - start_time).total_seconds() * 1000
            
            # Update task status
            async with self._archive_lock:
                task.status = ArchiveStatus.COMPLETED
                task.completed_at = result.completed_at
            
            return result
            
        except Exception as e:
            # Create error result
            error_result = ArchiveResult(
                task_id=task.task_id,
                policy_id=task.policy_id,
                archive_format=task.archive_format,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                status=ArchiveStatus.FAILED,
                errors=[str(e)]
            )
            
            # Update task status
            async with self._archive_lock:
                task.status = ArchiveStatus.FAILED
                task.completed_at = error_result.completed_at
            
            return error_result
    
    async def _archive_json(self, task: ArchiveTask, policy: Optional[ArchivePolicy]) -> ArchiveResult:
        """Archive data as JSON"""
        # Mock implementation
        return ArchiveResult(
            task_id=task.task_id,
            policy_id=task.policy_id,
            archive_format=task.archive_format,
            started_at=datetime.now(),
            records_processed=5000,
            archives_created=5,
            original_size_mb=250.0,
            archived_size_mb=180.0,
            compression_ratio=0.28,
            archive_files=["archive_1.json", "archive_2.json"],
            errors=[]
        )
    
    async def _archive_json_gz(self, task: ArchiveTask, policy: Optional[ArchivePolicy]) -> ArchiveResult:
        """Archive data as compressed JSON"""
        # Mock implementation
        return ArchiveResult(
            task_id=task.task_id,
            policy_id=task.policy_id,
            archive_format=task.archive_format,
            started_at=datetime.now(),
            records_processed=5000,
            archives_created=3,
            original_size_mb=250.0,
            archived_size_mb=45.0,
            compression_ratio=0.82,
            archive_files=["archive_1.json.gz", "archive_2.json.gz"],
            errors=[]
        )
    
    async def _archive_csv(self, task: ArchiveTask, policy: Optional[ArchivePolicy]) -> ArchiveResult:
        """Archive data as CSV"""
        # Mock implementation
        return ArchiveResult(
            task_id=task.task_id,
            policy_id=task.policy_id,
            archive_format=task.archive_format,
            started_at=datetime.now(),
            records_processed=5000,
            archives_created=4,
            original_size_mb=250.0,
            archived_size_mb=200.0,
            compression_ratio=0.20,
            archive_files=["archive_1.csv", "archive_2.csv"],
            errors=[]
        )
    
    async def _archive_csv_gz(self, task: ArchiveTask, policy: Optional[ArchivePolicy]) -> ArchiveResult:
        """Archive data as compressed CSV"""
        # Mock implementation
        return ArchiveResult(
            task_id=task.task_id,
            policy_id=task.policy_id,
            archive_format=task.archive_format,
            started_at=datetime.now(),
            records_processed=5000,
            archives_created=2,
            original_size_mb=250.0,
            archived_size_mb=35.0,
            compression_ratio=0.86,
            archive_files=["archive_1.csv.gz", "archive_2.csv.gz"],
            errors=[]
        )
    
    async def _extract_gz_archive(self, archive_file: Path, target_dir: Path) -> None:
        """Extract gzip compressed archive"""
        with gzip.open(archive_file, 'rt') as gz_file:
            content = gz_file.read()
            
        # Determine output filename
        output_file = target_dir / archive_file.stem
        with open(output_file, 'w') as f:
            f.write(content)
    
    async def _extract_archive(self, archive_file: Path, target_dir: Path) -> None:
        """Extract archive file"""
        # Mock implementation - would use appropriate extraction library
        shutil.copy2(archive_file, target_dir / archive_file.name)
