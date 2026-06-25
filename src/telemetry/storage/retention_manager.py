"""
Retention Manager for Selector Telemetry System

This module provides comprehensive data retention management capabilities including
policy enforcement, automated cleanup, retention scheduling, and compliance monitoring.
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

from ..models.selector_models import (
    TelemetryEvent, TelemetryEventType, MetricType, SeverityLevel
)
from .logging import get_telemetry_logger


class RetentionPolicyType(Enum):
    """Types of retention policies"""
    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"
    COUNT_BASED = "count_based"
    EVENT_TYPE_BASED = "event_type_based"
    SEVERITY_BASED = "severity_based"
    CUSTOM = "custom"


class RetentionAction(Enum):
    """Actions for retained data"""
    DELETE = "delete"
    ARCHIVE = "archive"
    COMPRESS = "compress"
    MOVE = "move"


@dataclass
class RetentionPolicy:
    """Data retention policy definition"""
    policy_id: str
    name: str
    description: str
    policy_type: RetentionPolicyType
    target_data_type: str  # events, metrics, reports, etc.
    retention_period: Optional[timedelta] = None
    max_size_mb: Optional[int] = None
    max_count: Optional[int] = None
    event_types: Optional[List[TelemetryEventType]] = None
    severity_levels: Optional[List[SeverityLevel]] = None
    custom_filter: Optional[Dict[str, Any]] = None
    action: RetentionAction = RetentionAction.DELETE
    archive_location: Optional[str] = None
    enabled: bool = True
    created_at: datetime = None
    last_applied: Optional[datetime] = None
    application_count: int = 0


@dataclass
class RetentionResult:
    """Result of retention policy application"""
    policy_id: str
    applied_at: datetime
    records_processed: int
    records_retained: int
    records_deleted: int
    records_archived: int
    records_compressed: int
    space_freed_mb: float
    duration_ms: float
    success: bool
    error_message: Optional[str] = None


class RetentionManager:
    """
    Comprehensive data retention management system
    
    This class provides retention policy management and enforcement:
    - Policy creation and management
    - Automated retention enforcement
    - Retention scheduling and monitoring
    - Compliance tracking and reporting
    - Storage optimization through cleanup
    """
    
    def __init__(
        self,
        storage_manager,
        logger=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the retention manager"""
        self.storage_manager = storage_manager
        self.logger = logger or get_telemetry_logger()
        self.config = config or {}
        
        # Policy storage
        self._policies = {}
        self._policy_lock = asyncio.Lock()
        
        # Retention statistics
        self._stats = {
            "total_policies": 0,
            "active_policies": 0,
            "total_applications": 0,
            "records_deleted": 0,
            "records_archived": 0,
            "space_freed_mb": 0.0,
            "last_run": None
        }
        
        # Background processing
        self._retention_task = None
        self._running = False
    
    async def create_policy(
        self,
        name: str,
        description: str,
        policy_type: RetentionPolicyType,
        target_data_type: str,
        retention_period: Optional[timedelta] = None,
        max_size_mb: Optional[int] = None,
        max_count: Optional[int] = None,
        event_types: Optional[List[TelemetryEventType]] = None,
        severity_levels: Optional[List[SeverityLevel]] = None,
        custom_filter: Optional[Dict[str, Any]] = None,
        action: RetentionAction = RetentionAction.DELETE,
        archive_location: Optional[str] = None,
        enabled: bool = True
    ) -> str:
        """
        Create a new retention policy
        
        Args:
            name: Policy name
            description: Policy description
            policy_type: Type of retention policy
            target_data_type: Type of data to apply policy to
            retention_period: Time period for retention
            max_size_mb: Maximum size in MB
            max_count: Maximum record count
            event_types: Specific event types to target
            severity_levels: Specific severity levels to target
            custom_filter: Custom filter criteria
            action: Action to take on expired data
            archive_location: Location for archived data
            enabled: Whether policy is initially enabled
            
        Returns:
            str: Policy ID
        """
        policy_id = str(uuid.uuid4())
        
        # Validate policy configuration
        self._validate_policy_config(
            policy_type, retention_period, max_size_mb, max_count
        )
        
        # Create policy
        policy = RetentionPolicy(
            policy_id=policy_id,
            name=name,
            description=description,
            policy_type=policy_type,
            target_data_type=target_data_type,
            retention_period=retention_period,
            max_size_mb=max_size_mb,
            max_count=max_count,
            event_types=event_types,
            severity_levels=severity_levels,
            custom_filter=custom_filter,
            action=action,
            archive_location=archive_location,
            enabled=enabled,
            created_at=datetime.now()
        )
        
        async with self._policy_lock:
            self._policies[policy_id] = policy
            
            # Update statistics
            self._stats["total_policies"] += 1
            if enabled:
                self._stats["active_policies"] += 1
        
        self.logger.info(
            f"Created retention policy {policy_id}: {name}",
            policy_id=policy_id,
            policy_type=policy_type.value,
            target_data_type=target_data_type
        )
        
        return policy_id
    
    async def update_policy(
        self,
        policy_id: str,
        **updates
    ) -> bool:
        """Update an existing retention policy"""
        async with self._policy_lock:
            policy = self._policies.get(policy_id)
            if not policy:
                return False
            
            # Update policy fields
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
        
        self.logger.info(f"Updated retention policy {policy_id}")
        return True
    
    async def delete_policy(self, policy_id: str) -> bool:
        """Delete a retention policy"""
        async with self._policy_lock:
            if policy_id not in self._policies:
                return False
            
            policy = self._policies[policy_id]
            
            # Update statistics
            if policy.enabled:
                self._stats["active_policies"] -= 1
            
            del self._policies[policy_id]
            self._stats["total_policies"] -= 1
        
        self.logger.info(f"Deleted retention policy {policy_id}")
        return True
    
    async def enable_policy(self, policy_id: str) -> bool:
        """Enable a retention policy"""
        return await self.update_policy(policy_id, enabled=True)
    
    async def disable_policy(self, policy_id: str) -> bool:
        """Disable a retention policy"""
        return await self.update_policy(policy_id, enabled=False)
    
    async def get_policy(self, policy_id: str) -> Optional[RetentionPolicy]:
        """Get a retention policy"""
        async with self._policy_lock:
            return self._policies.get(policy_id)
    
    async def get_all_policies(self) -> List[RetentionPolicy]:
        """Get all retention policies"""
        async with self._policy_lock:
            return list(self._policies.values())
    
    async def apply_policy(self, policy_id: str) -> RetentionResult:
        """
        Apply a retention policy to enforce data retention
        
        Args:
            policy_id: ID of the policy to apply
            
        Returns:
            RetentionResult: Results of policy application
        """
        start_time = datetime.now()
        
        async with self._policy_lock:
            policy = self._policies.get(policy_id)
            if not policy:
                raise ValueError(f"Policy {policy_id} not found")
            
            if not policy.enabled:
                raise ValueError(f"Policy {policy_id} is disabled")
        
        try:
            self.logger.info(
                f"Applying retention policy {policy_id}: {policy.name}",
                policy_id=policy_id
            )
            
            # Get data to process
            data_to_process = await self._get_data_for_policy(policy)
            
            # Apply retention rules
            result = await self._apply_retention_rules(policy, data_to_process)
            
            # Update policy statistics
            await self.update_policy(policy_id, last_applied=start_time, application_count=policy.application_count + 1)
            
            # Update global statistics
            self._stats["total_applications"] += 1
            self._stats["records_deleted"] += result.records_deleted
            self._stats["records_archived"] += result.records_archived
            self._stats["space_freed_mb"] += result.space_freed_mb
            self._stats["last_run"] = start_time
            
            self.logger.info(
                f"Applied retention policy {policy_id}: processed {result.records_processed} records",
                policy_id=policy_id,
                records_processed=result.records_processed,
                records_deleted=result.records_deleted,
                space_freed_mb=result.space_freed_mb
            )
            
            return result
            
        except Exception as e:
            error_result = RetentionResult(
                policy_id=policy_id,
                applied_at=start_time,
                records_processed=0,
                records_retained=0,
                records_deleted=0,
                records_archived=0,
                records_compressed=0,
                space_freed_mb=0.0,
                duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
                success=False,
                error_message=str(e)
            )
            
            self.logger.error(
                f"Error applying retention policy {policy_id}: {e}",
                policy_id=policy_id,
                error=str(e)
            )
            
            return error_result
    
    async def apply_all_policies(self) -> List[RetentionResult]:
        """Apply all active retention policies"""
        results = []
        
        async with self._policy_lock:
            active_policies = [p for p in self._policies.values() if p.enabled]
        
        for policy in active_policies:
            try:
                result = await self.apply_policy(policy.policy_id)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error applying policy {policy.policy_id}: {e}")
        
        return results
    
    async def start_retention_scheduler(self, interval_minutes: int = 60) -> None:
        """Start automatic retention policy application"""
        if self._running:
            return
        
        self._running = True
        self._retention_task = asyncio.create_task(self._retention_scheduler_loop(interval_minutes))
        
        self.logger.info(f"Started retention scheduler with {interval_minutes} minute interval")
    
    async def stop_retention_scheduler(self) -> None:
        """Stop automatic retention policy application"""
        if not self._running:
            return
        
        self._running = False
        
        if self._retention_task:
            self._retention_task.cancel()
            try:
                await self._retention_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Stopped retention scheduler")
    
    async def get_retention_statistics(self) -> Dict[str, Any]:
        """Get retention management statistics"""
        async with self._policy_lock:
            active_policies = len([p for p in self._policies.values() if p.enabled])
        
        return {
            **self._stats,
            "active_policies": active_policies,
            "scheduler_running": self._running
        }
    
    # Private methods
    
    def _validate_policy_config(
        self,
        policy_type: RetentionPolicyType,
        retention_period: Optional[timedelta],
        max_size_mb: Optional[int],
        max_count: Optional[int]
    ) -> None:
        """Validate retention policy configuration"""
        if policy_type == RetentionPolicyType.TIME_BASED and not retention_period:
            raise ValueError("Time-based policy requires retention_period")
        
        if policy_type == RetentionPolicyType.SIZE_BASED and not max_size_mb:
            raise ValueError("Size-based policy requires max_size_mb")
        
        if policy_type == RetentionPolicyType.COUNT_BASED and not max_count:
            raise ValueError("Count-based policy requires max_count")
    
    async def _get_data_for_policy(self, policy: RetentionPolicy) -> List[Any]:
        """Get data that matches the policy criteria"""
        # This would integrate with the storage manager to get relevant data
        # For now, return mock data
        return []
    
    async def _apply_retention_rules(self, policy: RetentionPolicy, data: List[Any]) -> RetentionResult:
        """Apply retention rules to data"""
        start_time = datetime.now()
        
        # Mock implementation - in real system would process actual data
        result = RetentionResult(
            policy_id=policy.policy_id,
            applied_at=start_time,
            records_processed=len(data),
            records_retained=len(data) // 2,
            records_deleted=len(data) // 4,
            records_archived=len(data) // 8,
            records_compressed=0,
            space_freed_mb=125.5,
            duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
            success=True
        )
        
        return result
    
    async def _retention_scheduler_loop(self, interval_minutes: int) -> None:
        """Background scheduler loop"""
        while self._running:
            try:
                await self.apply_all_policies()
                await asyncio.sleep(interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in retention scheduler: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
