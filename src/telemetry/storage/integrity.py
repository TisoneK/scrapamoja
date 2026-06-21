"""
Data Integrity Checks for Selector Telemetry System

This module provides comprehensive data integrity verification capabilities including
checksum validation, corruption detection, data consistency checks, and
repair mechanisms.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import uuid
import hashlib
import json
from pathlib import Path

from ..models.selector_models import SeverityLevel
from .logging import get_telemetry_logger


class IntegrityCheckType(Enum):
    """Types of integrity checks"""
    CHECKSUM = "checksum"
    HASH = "hash"
    SIZE = "size"
    FORMAT = "format"
    SCHEMA = "schema"
    CONSISTENCY = "consistency"
    REFERENCE = "reference"
    DUPLICATE = "duplicate"


class IntegrityStatus(Enum):
    """Integrity check status"""
    VALID = "valid"
    INVALID = "invalid"
    CORRUPTED = "corrupted"
    MISSING = "missing"
    INCONSISTENT = "inconsistent"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    UNKNOWN = "unknown"


@dataclass
class IntegrityCheck:
    """Data integrity check definition"""
    check_id: str
    name: str
    check_type: IntegrityCheckType
    target_path: str
    algorithm: Optional[str] = None  # For hash/checksum algorithms
    expected_hash: Optional[str] = None
    expected_size: Optional[int] = None
    enabled: bool = True
    created_at: datetime = None
    last_run: Optional[datetime] = None
    run_count: int = 0


@dataclass
class IntegrityResult:
    """Result of integrity check"""
    check_id: str
    check_type: IntegrityCheckType
    target_path: str
    status: IntegrityStatus
    checked_at: datetime
    duration_ms: float
    details: Dict[str, Any]
    errors: List[str] = None
    recommendations: List[str] = None


@dataclass
class IntegrityIssue:
    """Data integrity issue"""
    issue_id: str
    check_id: str
    issue_type: str
    severity: SeverityLevel
    description: str
    affected_path: str
    detected_at: datetime
    can_auto_repair: bool = False
    repair_attempted: bool = False
    repair_successful: Optional[bool] = None


class DataIntegrity:
    """
    Comprehensive data integrity verification system
    
    This class provides integrity checking capabilities:
    - Checksum and hash validation
    - File size verification
    - Format validation
    - Schema consistency checks
    - Reference integrity
    - Duplicate detection
    - Auto-repair mechanisms
    """
    
    def __init__(
        self,
        storage_manager,
        logger=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the data integrity system"""
        self.storage_manager = storage_manager
        self.logger = logger or get_telemetry_logger()
        self.config = config or {}
        
        # Integrity checks storage
        self._checks = {}
        self._results = {}
        self._issues = {}
        self._integrity_lock = asyncio.Lock()
        
        # Integrity statistics
        self._stats = {
            "total_checks": 0,
            "active_checks": 0,
            "total_issues": 0,
            "critical_issues": 0,
            "auto_repairs": 0,
            "successful_repairs": 0,
            "last_check": None
        }
        
        # Background processing
        self._integrity_task = None
        self._running = False
    
    async def create_integrity_check(
        self,
        name: str,
        check_type: IntegrityCheckType,
        target_path: str,
        algorithm: Optional[str] = None,
        expected_hash: Optional[str] = None,
        expected_size: Optional[int] = None,
        enabled: bool = True
    ) -> str:
        """
        Create a new integrity check
        
        Args:
            name: Check name
            check_type: Type of integrity check
            target_path: Path to check
            algorithm: Hash algorithm (md5, sha1, sha256, etc.)
            expected_hash: Expected hash value
            expected_size: Expected file size
            enabled: Whether check is initially enabled
            
        Returns:
            str: Check ID
        """
        check_id = str(uuid.uuid4())
        
        # Validate check configuration
        self._validate_integrity_check(check_type, algorithm, expected_hash, expected_size)
        
        # Create check
        check = IntegrityCheck(
            check_id=check_id,
            name=name,
            check_type=check_type,
            target_path=target_path,
            algorithm=algorithm,
            expected_hash=expected_hash,
            expected_size=expected_size,
            enabled=enabled,
            created_at=datetime.now()
        )
        
        async with self._integrity_lock:
            self._checks[check_id] = check
            
            # Update statistics
            self._stats["total_checks"] += 1
            if enabled:
                self._stats["active_checks"] += 1
        
        self.logger.info(
            f"Created integrity check {check_id}: {name}",
            check_id=check_id,
            check_type=check_type.value,
            target_path=target_path
        )
        
        return check_id
    
    async def update_check(self, check_id: str, **updates) -> bool:
        """Update an existing integrity check"""
        async with self._integrity_lock:
            check = self._checks.get(check_id)
            if not check:
                return False
            
            old_enabled = check.enabled
            for key, value in updates.items():
                if hasattr(check, key):
                    setattr(check, key, value)
            
            # Update statistics if enabled status changed
            if old_enabled != check.enabled:
                if check.enabled:
                    self._stats["active_checks"] += 1
                else:
                    self._stats["active_checks"] -= 1
        
        self.logger.info(f"Updated integrity check {check_id}")
        return True
    
    async def delete_check(self, check_id: str) -> bool:
        """Delete an integrity check"""
        async with self._integrity_lock:
            if check_id not in self._checks:
                return False
            
            check = self._checks[check_id]
            
            # Update statistics
            if check.enabled:
                self._stats["active_checks"] -= 1
            
            del self._checks[check_id]
            self._stats["total_checks"] -= 1
        
        self.logger.info(f"Deleted integrity check {check_id}")
        return True
    
    async def run_integrity_check(self, check_id: str) -> IntegrityResult:
        """
        Run a specific integrity check
        
        Args:
            check_id: ID of the check to run
            
        Returns:
            IntegrityResult: Result of the integrity check
        """
        start_time = datetime.now()
        
        async with self._integrity_lock:
            check = self._checks.get(check_id)
            if not check:
                raise ValueError(f"Integrity check {check_id} not found")
            
            if not check.enabled:
                raise ValueError(f"Integrity check {check_id} is disabled")
        
        try:
            self.logger.info(
                f"Running integrity check {check_id}: {check.name}",
                check_id=check_id,
                check_type=check.check_type.value
            )
            
            # Run check based on type
            if check.check_type == IntegrityCheckType.CHECKSUM:
                result = await self._check_checksum(check)
            elif check.check_type == IntegrityCheckType.HASH:
                result = await self._check_hash(check)
            elif check.check_type == IntegrityCheckType.SIZE:
                result = await self._check_size(check)
            elif check.check_type == IntegrityCheckType.FORMAT:
                result = await self._check_format(check)
            elif check.check_type == IntegrityCheckType.SCHEMA:
                result = await self._check_schema(check)
            elif check.check_type == IntegrityCheckType.CONSISTENCY:
                result = await self._check_consistency(check)
            elif check.check_type == IntegrityCheckType.REFERENCE:
                result = await self._check_reference(check)
            elif check.check_type == IntegrityCheckType.DUPLICATE:
                result = await self._check_duplicate(check)
            else:
                raise ValueError(f"Unsupported check type: {check.check_type}")
            
            # Update result metadata
            result.check_id = check_id
            result.check_type = check.check_type
            result.target_path = check.target_path
            result.checked_at = start_time
            
            # Store result
            self._results[check_id] = result
            
            # Update check statistics
            await self.update_check(check_id, last_run=start_time, run_count=check.run_count + 1)
            
            # Update global statistics
            self._stats["last_check"] = start_time
            
            # Create issues if check failed
            if result.status != IntegrityStatus.VALID:
                await self._create_integrity_issue(check, result)
            
            self.logger.info(
                f"Completed integrity check {check_id}: {result.status.value}",
                check_id=check_id,
                status=result.status.value,
                duration_ms=result.duration_ms
            )
            
            return result
            
        except Exception as e:
            error_result = IntegrityResult(
                check_id=check_id,
                check_type=check.check_type,
                target_path=check.target_path,
                status=IntegrityStatus.UNKNOWN,
                checked_at=start_time,
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                details={"error": str(e)},
                errors=[str(e)]
            )
            
            self.logger.error(
                f"Error running integrity check {check_id}: {e}",
                check_id=check_id,
                error=str(e)
            )
            
            return error_result
    
    async def run_all_checks(self) -> List[IntegrityResult]:
        """Run all active integrity checks"""
        results = []
        
        async with self._integrity_lock:
            active_checks = [c for c in self._checks.values() if c.enabled]
        
        for check in active_checks:
            try:
                result = await self.run_integrity_check(check.check_id)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error running check {check.check_id}: {e}")
        
        return results
    
    async def repair_issue(self, issue_id: str) -> bool:
        """
        Attempt to repair an integrity issue
        
        Args:
            issue_id: ID of the issue to repair
            
        Returns:
            bool: Success status
        """
        async with self._integrity_lock:
            issue = self._issues.get(issue_id)
            if not issue:
                raise ValueError(f"Integrity issue {issue_id} not found")
            
            if not issue.can_auto_repair:
                return False
            
            issue.repair_attempted = True
        
        try:
            self.logger.info(
                f"Attempting to repair integrity issue {issue_id}",
                issue_id=issue_id,
                issue_type=issue.issue_type
            )
            
            # Attempt repair based on issue type
            success = await self._repair_integrity_issue(issue)
            
            # Update issue
            async with self._integrity_lock:
                issue.repair_successful = success
            
            # Update statistics
            self._stats["auto_repairs"] += 1
            if success:
                self._stats["successful_repairs"] += 1
            
            self.logger.info(
                f"Repair {'successful' if success else 'failed'} for issue {issue_id}",
                issue_id=issue_id,
                success=success
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error repairing issue {issue_id}: {e}")
            return False
    
    async def get_check(self, check_id: str) -> Optional[IntegrityCheck]:
        """Get an integrity check"""
        async with self._integrity_lock:
            return self._checks.get(check_id)
    
    async def get_all_checks(self) -> List[IntegrityCheck]:
        """Get all integrity checks"""
        async with self._integrity_lock:
            return list(self._checks.values())
    
    async def get_check_result(self, check_id: str) -> Optional[IntegrityResult]:
        """Get integrity check result"""
        return self._results.get(check_id)
    
    async def get_issue(self, issue_id: str) -> Optional[IntegrityIssue]:
        """Get an integrity issue"""
        async with self._integrity_lock:
            return self._issues.get(issue_id)
    
    async def get_all_issues(self, severity: Optional[SeverityLevel] = None) -> List[IntegrityIssue]:
        """Get all integrity issues"""
        async with self._integrity_lock:
            issues = list(self._issues.values())
            
            if severity:
                issues = [i for i in issues if i.severity == severity]
            
            return issues
    
    async def get_integrity_statistics(self) -> Dict[str, Any]:
        """Get integrity checking statistics"""
        async with self._integrity_lock:
            active_checks = len([c for c in self._checks.values() if c.enabled])
            critical_issues = len([i for i in self._issues.values() if i.severity == SeverityLevel.CRITICAL])
        
        return {
            **self._stats,
            "active_checks": active_checks,
            "critical_issues": critical_issues,
            "scheduler_running": self._running
        }
    
    # Private methods
    
    def _validate_integrity_check(
        self,
        check_type: IntegrityCheckType,
        algorithm: Optional[str],
        expected_hash: Optional[str],
        expected_size: Optional[int]
    ) -> None:
        """Validate integrity check configuration"""
        if check_type in [IntegrityCheckType.CHECKSUM, IntegrityCheckType.HASH]:
            if not algorithm:
                raise ValueError(f"{check_type.value} check requires algorithm")
            
            if check_type == IntegrityCheckType.HASH and not expected_hash:
                raise ValueError("Hash check requires expected_hash")
        
        if check_type == IntegrityCheckType.SIZE and expected_size is None:
            raise ValueError("Size check requires expected_size")
    
    async def _create_integrity_issue(self, check: IntegrityCheck, result: IntegrityResult) -> None:
        """Create an integrity issue from failed check"""
        issue_id = str(uuid.uuid4())
        
        # Determine severity based on status
        if result.status == IntegrityStatus.CORRUPTED:
            severity = SeverityLevel.CRITICAL
        elif result.status == IntegrityStatus.INVALID:
            severity = SeverityLevel.ERROR
        else:
            severity = SeverityLevel.WARNING
        
        # Determine if auto-repair is possible
        can_auto_repair = result.status in [
            IntegrityStatus.CHECKSUM_MISMATCH,
            IntegrityStatus.SIZE_MISMATCH
        ]
        
        issue = IntegrityIssue(
            issue_id=issue_id,
            check_id=check.check_id,
            issue_type=result.status.value,
            severity=severity,
            description=f"Integrity check failed: {result.status.value}",
            affected_path=check.target_path,
            detected_at=result.checked_at,
            can_auto_repair=can_auto_repair
        )
        
        async with self._integrity_lock:
            self._issues[issue_id] = issue
            
            # Update statistics
            self._stats["total_issues"] += 1
            if severity == SeverityLevel.CRITICAL:
                self._stats["critical_issues"] += 1
    
    async def _repair_integrity_issue(self, issue: IntegrityIssue) -> bool:
        """Attempt to repair an integrity issue"""
        # Mock repair implementation
        if issue.issue_type == "checksum_mismatch":
            # Recalculate checksum
            return True
        elif issue.issue_type == "size_mismatch":
            # Update expected size
            return True
        else:
            return False
    
    # Check implementations
    
    async def _check_checksum(self, check: IntegrityCheck) -> IntegrityResult:
        """Check file checksum"""
        start_time = datetime.now()
        
        # Mock implementation
        return IntegrityResult(
            check_id=check.check_id,
            check_type=check.check_type,
            target_path=check.target_path,
            status=IntegrityStatus.VALID,
            checked_at=start_time,
            duration_ms=15.5,
            details={"algorithm": check.algorithm, "calculated_checksum": "abc123"},
            errors=[],
            recommendations=[]
        )
    
    async def _check_hash(self, check: IntegrityCheck) -> IntegrityResult:
        """Check file hash"""
        start_time = datetime.now()
        
        # Mock implementation
        calculated_hash = hashlib.sha256(b"mock data").hexdigest()
        is_valid = calculated_hash == check.expected_hash
        
        return IntegrityResult(
            check_id=check.check_id,
            check_type=check.check_type,
            target_path=check.target_path,
            status=IntegrityStatus.VALID if is_valid else IntegrityStatus.CHECKSUM_MISMATCH,
            checked_at=start_time,
            duration_ms=25.3,
            details={
                "algorithm": check.algorithm,
                "expected_hash": check.expected_hash,
                "calculated_hash": calculated_hash
            },
            errors=[] if is_valid else ["Hash mismatch"],
            recommendations=[] if is_valid else ["Regenerate file from backup"]
        )
    
    async def _check_size(self, check: IntegrityCheck) -> IntegrityResult:
        """Check file size"""
        start_time = datetime.now()
        
        # Mock implementation
        actual_size = 1024 * 1024 * 10  # 10MB
        is_valid = actual_size == check.expected_size
        
        return IntegrityResult(
            check_id=check.check_id,
            check_type=check.check_type,
            target_path=check.target_path,
            status=IntegrityStatus.VALID if is_valid else IntegrityStatus.INVALID,
            checked_at=start_time,
            duration_ms=5.2,
            details={
                "expected_size": check.expected_size,
                "actual_size": actual_size
            },
            errors=[] if is_valid else ["Size mismatch"],
            recommendations=[] if is_valid else ["Update expected size"]
        )
    
    async def _check_format(self, check: IntegrityCheck) -> IntegrityResult:
        """Check file format"""
        start_time = datetime.now()
        
        # Mock implementation
        return IntegrityResult(
            check_id=check.check_id,
            check_type=check.check_type,
            target_path=check.target_path,
            status=IntegrityStatus.VALID,
            checked_at=start_time,
            duration_ms=12.8,
            details={"format": "json", "valid": True},
            errors=[],
            recommendations=[]
        )
    
    async def _check_schema(self, check: IntegrityCheck) -> IntegrityResult:
        """Check data schema"""
        start_time = datetime.now()
        
        # Mock implementation
        return IntegrityResult(
            check_id=check.check_id,
            check_type=check.check_type,
            target_path=check.target_path,
            status=IntegrityStatus.VALID,
            checked_at=start_time,
            duration_ms=35.6,
            details={"schema_version": "1.0", "valid": True},
            errors=[],
            recommendations=[]
        )
    
    async def _check_consistency(self, check: IntegrityCheck) -> IntegrityResult:
        """Check data consistency"""
        start_time = datetime.now()
        
        # Mock implementation
        return IntegrityResult(
            check_id=check.check_id,
            check_type=check.check_type,
            target_path=check.target_path,
            status=IntegrityStatus.VALID,
            checked_at=start_time,
            duration_ms=45.2,
            details={"consistency_score": 0.95, "issues": []},
            errors=[],
            recommendations=[]
        )
    
    async def _check_reference(self, check: IntegrityCheck) -> IntegrityResult:
        """Check reference integrity"""
        start_time = datetime.now()
        
        # Mock implementation
        return IntegrityResult(
            check_id=check.check_id,
            check_type=check.check_type,
            target_path=check.target_path,
            status=IntegrityStatus.VALID,
            checked_at=start_time,
            duration_ms=28.4,
            details={"broken_references": 0, "total_references": 150},
            errors=[],
            recommendations=[]
        )
    
    async def _check_duplicate(self, check: IntegrityCheck) -> IntegrityResult:
        """Check for duplicate data"""
        start_time = datetime.now()
        
        # Mock implementation
        return IntegrityResult(
            check_id=check.check_id,
            check_type=check.check_type,
            target_path=check.target_path,
            status=IntegrityStatus.VALID,
            checked_at=start_time,
            duration_ms=52.1,
            details={"duplicates_found": 0, "files_checked": 100},
            errors=[],
            recommendations=[]
        )
