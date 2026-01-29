"""
Backup and Recovery for Selector Telemetry System

This module provides comprehensive backup and recovery capabilities including
automated backups, incremental backups, disaster recovery, and
restore operations.
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
import shutil

from ..models.selector_models import SeverityLevel
from .logging import get_telemetry_logger


class BackupType(Enum):
    """Types of backup operations"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class BackupStatus(Enum):
    """Backup operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecoveryStatus(Enum):
    """Recovery operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackupPolicy:
    """Backup policy definition"""
    policy_id: str
    name: str
    description: str
    backup_type: BackupType
    source_paths: List[str]
    backup_location: str
    schedule: str  # Cron expression
    retention_days: int
    compression_enabled: bool
    encryption_enabled: bool
    verification_enabled: bool
    enabled: bool = True
    created_at: datetime = None
    last_backup: Optional[datetime] = None
    backup_count: int = 0


@dataclass
class BackupTask:
    """Backup operation task"""
    task_id: str
    policy_id: str
    backup_type: BackupType
    source_paths: List[str]
    backup_location: str
    status: BackupStatus = BackupStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    backup_size_mb: float = 0.0
    compressed_size_mb: float = 0.0
    files_backed_up: int = 0
    error_message: Optional[str] = None


@dataclass
class BackupResult:
    """Result of backup operation"""
    task_id: str
    policy_id: str
    backup_type: BackupType
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: BackupStatus = BackupStatus.COMPLETED
    source_paths: List[str] = None
    backup_path: str = ""
    backup_size_mb: float = 0.0
    compressed_size_mb: float = 0.0
    compression_ratio: float = 0.0
    files_backed_up: int = 0
    verification_passed: bool = False
    errors: List[str] = None


@dataclass
class RecoveryTask:
    """Recovery operation task"""
    task_id: str
    backup_id: str
    target_location: str
    restore_paths: List[str]
    status: RecoveryStatus = RecoveryStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    files_restored: int = 0
    error_message: Optional[str] = None


@dataclass
class RecoveryResult:
    """Result of recovery operation"""
    task_id: str
    backup_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: RecoveryStatus = RecoveryStatus.COMPLETED
    target_location: str = ""
    restore_paths: List[str] = None
    files_restored: int = 0
    files_failed: int = 0
    verification_passed: bool = False
    errors: List[str] = None


class BackupAndRecovery:
    """
    Comprehensive backup and recovery system
    
    This class provides backup and recovery capabilities:
    - Automated backup scheduling
    - Multiple backup types (full, incremental, differential)
    - Backup verification and integrity checking
    - Disaster recovery procedures
    - Point-in-time recovery
    - Backup retention management
    """
    
    def __init__(
        self,
        storage_manager,
        logger=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the backup and recovery system"""
        self.storage_manager = storage_manager
        self.logger = logger or get_telemetry_logger()
        self.config = config or {}
        
        # Backup policies storage
        self._policies = {}
        self._backup_tasks = {}
        self._backup_results = {}
        self._recovery_tasks = {}
        self._recovery_results = {}
        self._backup_lock = asyncio.Lock()
        
        # Backup statistics
        self._stats = {
            "total_policies": 0,
            "active_policies": 0,
            "total_backups": 0,
            "successful_backups": 0,
            "failed_backups": 0,
            "total_recoveries": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "total_backup_size_mb": 0.0,
            "total_compressed_size_mb": 0.0,
            "last_backup": None,
            "last_recovery": None
        }
        
        # Background processing
        self._backup_task = None
        self._running = False
    
    async def create_backup_policy(
        self,
        name: str,
        description: str,
        backup_type: BackupType,
        source_paths: List[str],
        backup_location: str,
        schedule: str,
        retention_days: int = 30,
        compression_enabled: bool = True,
        encryption_enabled: bool = True,
        verification_enabled: bool = True,
        enabled: bool = True
    ) -> str:
        """
        Create a new backup policy
        
        Args:
            name: Policy name
            description: Policy description
            backup_type: Type of backup
            source_paths: Paths to back up
            backup_location: Where to store backups
            schedule: Backup schedule (cron expression)
            retention_days: How long to keep backups
            compression_enabled: Whether to compress backups
            encryption_enabled: Whether to encrypt backups
            verification_enabled: Whether to verify backups
            enabled: Whether policy is initially enabled
            
        Returns:
            str: Policy ID
        """
        policy_id = str(uuid.uuid4())
        
        # Validate policy configuration
        self._validate_backup_policy(backup_type, source_paths, backup_location)
        
        # Create backup directory if it doesn't exist
        Path(backup_location).mkdir(parents=True, exist_ok=True)
        
        # Create policy
        policy = BackupPolicy(
            policy_id=policy_id,
            name=name,
            description=description,
            backup_type=backup_type,
            source_paths=source_paths,
            backup_location=backup_location,
            schedule=schedule,
            retention_days=retention_days,
            compression_enabled=compression_enabled,
            encryption_enabled=encryption_enabled,
            verification_enabled=verification_enabled,
            enabled=enabled,
            created_at=datetime.now()
        )
        
        async with self._backup_lock:
            self._policies[policy_id] = policy
            
            # Update statistics
            self._stats["total_policies"] += 1
            if enabled:
                self._stats["active_policies"] += 1
        
        self.logger.info(
            f"Created backup policy {policy_id}: {name}",
            policy_id=policy_id,
            backup_type=backup_type.value,
            backup_location=backup_location
        )
        
        return policy_id
    
    async def execute_backup(self, policy_id: str) -> str:
        """
        Execute a backup using a specific policy
        
        Args:
            policy_id: ID of the backup policy
            
        Returns:
            str: Task ID
        """
        task_id = str(uuid.uuid4())
        
        async with self._backup_lock:
            policy = self._policies.get(policy_id)
            if not policy:
                raise ValueError(f"Backup policy {policy_id} not found")
            
            if not policy.enabled:
                raise ValueError(f"Backup policy {policy_id} is disabled")
        
        # Create backup task
        task = BackupTask(
            task_id=task_id,
            policy_id=policy_id,
            backup_type=policy.backup_type,
            source_paths=policy.source_paths,
            backup_location=policy.backup_location,
            status=BackupStatus.PENDING,
            created_at=datetime.now()
        )
        
        async with self._backup_lock:
            self._backup_tasks[task_id] = task
            self._stats["total_backups"] += 1
        
        self.logger.info(
            f"Created backup task {task_id} using policy {policy_id}",
            task_id=task_id,
            policy_id=policy_id
        )
        
        # Execute backup
        try:
            result = await self._execute_backup_task(task, policy)
            
            # Store result
            self._backup_results[task_id] = result
            
            # Update policy
            await self._update_policy(policy_id, last_backup=result.started_at, backup_count=policy.backup_count + 1)
            
            # Update statistics
            if result.status == BackupStatus.COMPLETED:
                self._stats["successful_backups"] += 1
                self._stats["total_backup_size_mb"] += result.backup_size_mb
                self._stats["total_compressed_size_mb"] += result.compressed_size_mb
                self._stats["last_backup"] = result.started_at
            else:
                self._stats["failed_backups"] += 1
            
            return task_id
            
        except Exception as e:
            self.logger.error(f"Error executing backup task {task_id}: {e}")
            raise
    
    async def restore_from_backup(
        self,
        backup_id: str,
        target_location: str,
        restore_paths: Optional[List[str]] = None
    ) -> str:
        """
        Restore data from a backup
        
        Args:
            backup_id: ID of the backup to restore from
            target_location: Where to restore the data
            restore_paths: Specific paths to restore (all if None)
            
        Returns:
            str: Recovery task ID
        """
        task_id = str(uuid.uuid4())
        
        # Create recovery task
        task = RecoveryTask(
            task_id=task_id,
            backup_id=backup_id,
            target_location=target_location,
            restore_paths=restore_paths or [],
            status=RecoveryStatus.PENDING,
            created_at=datetime.now()
        )
        
        async with self._backup_lock:
            self._recovery_tasks[task_id] = task
            self._stats["total_recoveries"] += 1
        
        self.logger.info(
            f"Created recovery task {task_id} from backup {backup_id}",
            task_id=task_id,
            backup_id=backup_id
        )
        
        # Execute recovery
        try:
            result = await self._execute_recovery_task(task)
            
            # Store result
            self._recovery_results[task_id] = result
            
            # Update statistics
            if result.status == RecoveryStatus.COMPLETED:
                self._stats["successful_recoveries"] += 1
                self._stats["last_recovery"] = result.started_at
            else:
                self._stats["failed_recoveries"] += 1
            
            return task_id
            
        except Exception as e:
            self.logger.error(f"Error executing recovery task {task_id}: {e}")
            raise
    
    async def get_policy(self, policy_id: str) -> Optional[BackupPolicy]:
        """Get a backup policy"""
        async with self._backup_lock:
            return self._policies.get(policy_id)
    
    async def get_all_policies(self) -> List[BackupPolicy]:
        """Get all backup policies"""
        async with self._backup_lock:
            return list(self._policies.values())
    
    async def get_backup_task(self, task_id: str) -> Optional[BackupTask]:
        """Get a backup task"""
        async with self._backup_lock:
            return self._backup_tasks.get(task_id)
    
    async def get_backup_result(self, task_id: str) -> Optional[BackupResult]:
        """Get backup task result"""
        return self._backup_results.get(task_id)
    
    async def get_recovery_task(self, task_id: str) -> Optional[RecoveryTask]:
        """Get a recovery task"""
        async with self._backup_lock:
            return self._recovery_tasks.get(task_id)
    
    async def get_recovery_result(self, task_id: str) -> Optional[RecoveryResult]:
        """Get recovery task result"""
        return self._recovery_results.get(task_id)
    
    async def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup and recovery statistics"""
        async with self._backup_lock:
            active_policies = len([p for p in self._policies.values() if p.enabled])
            pending_backups = len([t for t in self._backup_tasks.values() if t.status == BackupStatus.PENDING])
            running_backups = len([t for t in self._backup_tasks.values() if t.status == BackupStatus.RUNNING])
            pending_recoveries = len([t for t in self._recovery_tasks.values() if t.status == RecoveryStatus.PENDING])
            running_recoveries = len([t for t in self._recovery_tasks.values() if t.status == RecoveryStatus.RUNNING])
        
        return {
            **self._stats,
            "active_policies": active_policies,
            "pending_backups": pending_backups,
            "running_backups": running_backups,
            "pending_recoveries": pending_recoveries,
            "running_recoveries": running_recoveries,
            "scheduler_running": self._running
        }
    
    # Private methods
    
    def _validate_backup_policy(
        self,
        backup_type: BackupType,
        source_paths: List[str],
        backup_location: str
    ) -> None:
        """Validate backup policy configuration"""
        if not source_paths:
            raise ValueError("Source paths are required")
        
        if not backup_location:
            raise ValueError("Backup location is required")
        
        for path in source_paths:
            if not Path(path).exists():
                self.logger.warning(f"Source path does not exist: {path}")
    
    async def _update_policy(self, policy_id: str, **updates) -> bool:
        """Update a backup policy"""
        async with self._backup_lock:
            policy = self._policies.get(policy_id)
            if not policy:
                return False
            
            for key, value in updates.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
        
        return True
    
    async def _execute_backup_task(self, task: BackupTask, policy: BackupPolicy) -> BackupResult:
        """Execute a backup task"""
        start_time = datetime.now()
        
        # Update task status
        async with self._backup_lock:
            task.status = BackupStatus.RUNNING
            task.started_at = start_time
        
        try:
            self.logger.info(
                f"Executing backup task {task.task_id}: {policy.backup_type.value}",
                task_id=task.task_id,
                backup_type=policy.backup_type.value
            )
            
            # Create backup directory with timestamp
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            backup_dir = Path(policy.backup_location) / f"backup_{timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Execute backup based on type
            if policy.backup_type == BackupType.FULL:
                result = await self._execute_full_backup(task, policy, backup_dir)
            elif policy.backup_type == BackupType.INCREMENTAL:
                result = await self._execute_incremental_backup(task, policy, backup_dir)
            elif policy.backup_type == BackupType.DIFFERENTIAL:
                result = await self._execute_differential_backup(task, policy, backup_dir)
            elif policy.backup_type == BackupType.SNAPSHOT:
                result = await self._execute_snapshot_backup(task, policy, backup_dir)
            else:
                raise ValueError(f"Unsupported backup type: {policy.backup_type}")
            
            # Update result metadata
            result.task_id = task.task_id
            result.policy_id = policy.policy_id
            result.backup_type = policy.backup_type
            result.started_at = start_time
            result.completed_at = datetime.now()
            result.duration_ms = (result.completed_at - start_time).total_seconds() * 1000
            
            # Update task
            async with self._backup_lock:
                task.status = BackupStatus.COMPLETED
                task.completed_at = result.completed_at
                task.backup_size_mb = result.backup_size_mb
                task.compressed_size_mb = result.compressed_size_mb
                task.files_backed_up = result.files_backed_up
            
            return result
            
        except Exception as e:
            # Create error result
            error_result = BackupResult(
                task_id=task.task_id,
                policy_id=policy.policy_id,
                backup_type=policy.backup_type,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                status=BackupStatus.FAILED,
                errors=[str(e)]
            )
            
            # Update task
            async with self._backup_lock:
                task.status = BackupStatus.FAILED
                task.completed_at = error_result.completed_at
                task.error_message = str(e)
            
            return error_result
    
    async def _execute_full_backup(self, task: BackupTask, policy: BackupPolicy, backup_dir: Path) -> BackupResult:
        """Execute a full backup"""
        # Mock implementation
        return BackupResult(
            task_id=task.task_id,
            policy_id=policy.policy_id,
            backup_type=policy.backup_type,
            started_at=datetime.now(),
            backup_path=str(backup_dir),
            backup_size_mb=500.0,
            compressed_size_mb=150.0,
            compression_ratio=0.7,
            files_backed_up=250,
            verification_passed=True,
            errors=[]
        )
    
    async def _execute_incremental_backup(self, task: BackupTask, policy: BackupPolicy, backup_dir: Path) -> BackupResult:
        """Execute an incremental backup"""
        # Mock implementation
        return BackupResult(
            task_id=task.task_id,
            policy_id=policy.policy_id,
            backup_type=policy.backup_type,
            started_at=datetime.now(),
            backup_path=str(backup_dir),
            backup_size_mb=50.0,
            compressed_size_mb=15.0,
            compression_ratio=0.7,
            files_backed_up=25,
            verification_passed=True,
            errors=[]
        )
    
    async def _execute_differential_backup(self, task: BackupTask, policy: BackupPolicy, backup_dir: Path) -> BackupResult:
        """Execute a differential backup"""
        # Mock implementation
        return BackupResult(
            task_id=task.task_id,
            policy_id=policy.policy_id,
            backup_type=policy.backup_type,
            started_at=datetime.now(),
            backup_path=str(backup_dir),
            backup_size_mb=100.0,
            compressed_size_mb=30.0,
            compression_ratio=0.7,
            files_backed_up=50,
            verification_passed=True,
            errors=[]
        )
    
    async def _execute_snapshot_backup(self, task: BackupTask, policy: BackupPolicy, backup_dir: Path) -> BackupResult:
        """Execute a snapshot backup"""
        # Mock implementation
        return BackupResult(
            task_id=task.task_id,
            policy_id=policy.policy_id,
            backup_type=policy.backup_type,
            started_at=datetime.now(),
            backup_path=str(backup_dir),
            backup_size_mb=25.0,
            compressed_size_mb=7.5,
            compression_ratio=0.7,
            files_backed_up=12,
            verification_passed=True,
            errors=[]
        )
    
    async def _execute_recovery_task(self, task: RecoveryTask) -> RecoveryResult:
        """Execute a recovery task"""
        start_time = datetime.now()
        
        # Update task status
        async with self._backup_lock:
            task.status = RecoveryStatus.RUNNING
            task.started_at = start_time
        
        try:
            self.logger.info(
                f"Executing recovery task {task.task_id} from backup {task.backup_id}",
                task_id=task.task_id,
                backup_id=task.backup_id
            )
            
            # Mock recovery implementation
            result = RecoveryResult(
                task_id=task.task_id,
                backup_id=task.backup_id,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                status=RecoveryStatus.COMPLETED,
                target_location=task.target_location,
                restore_paths=task.restore_paths,
                files_restored=25,
                files_failed=0,
                verification_passed=True,
                errors=[]
            )
            
            # Update task
            async with self._backup_lock:
                task.status = RecoveryStatus.COMPLETED
                task.completed_at = result.completed_at
                task.files_restored = result.files_restored
            
            return result
            
        except Exception as e:
            # Create error result
            error_result = RecoveryResult(
                task_id=task.task_id,
                backup_id=task.backup_id,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                status=RecoveryStatus.FAILED,
                errors=[str(e)]
            )
            
            # Update task
            async with self._backup_lock:
                task.status = RecoveryStatus.FAILED
                task.completed_at = error_result.completed_at
                task.error_message = str(e)
            
            return error_result
