"""
Tiered Storage Management for Selector Telemetry System

This module provides comprehensive tiered storage capabilities including
automatic data tiering, storage optimization, cost management, and
performance-based data placement.
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

from ..models.selector_models import SeverityLevel
from .logging import get_telemetry_logger


class StorageTier(Enum):
    """Storage tier types"""
    HOT = "hot"           # Frequently accessed, high performance
    WARM = "warm"         # Moderately accessed, balanced performance
    COLD = "cold"         # Infrequently accessed, cost optimized
    ARCHIVE = "archive"   # Rarely accessed, long-term storage


class TieringPolicy(Enum):
    """Tiering policy types"""
    AGE_BASED = "age_based"
    ACCESS_FREQUENCY = "access_frequency"
    SIZE_BASED = "size_based"
    IMPORTANCE_BASED = "importance_based"
    COST_OPTIMIZED = "cost_optimized"
    PERFORMANCE_OPTIMIZED = "performance_optimized"


class MigrationStatus(Enum):
    """Data migration status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StorageTierConfig:
    """Storage tier configuration"""
    tier: StorageTier
    storage_type: str  # ssd, hdd, cloud, tape, etc.
    location: str
    max_capacity_gb: int
    current_usage_gb: int
    performance_tier: int  # 1=highest, 4=lowest
    cost_per_gb: float
    access_latency_ms: float
    retention_period: Optional[timedelta] = None
    compression_enabled: bool = False
    encryption_enabled: bool = True


@dataclass
class TieringRule:
    """Data tiering rule"""
    rule_id: str
    name: str
    policy: TieringPolicy
    source_tier: StorageTier
    target_tier: StorageTier
    conditions: Dict[str, Any]
    priority: int
    enabled: bool = True
    created_at: datetime = None


@dataclass
class DataMigration:
    """Data migration task"""
    migration_id: str
    rule_id: str
    source_tier: StorageTier
    target_tier: StorageTier
    data_paths: List[str]
    status: MigrationStatus = MigrationStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    bytes_migrated: int = 0
    error_message: Optional[str] = None


class TieredStorage:
    """
    Comprehensive tiered storage management system
    
    This class provides automated tiered storage capabilities:
    - Multi-tier storage management
    - Automatic data tiering based on policies
    - Storage optimization and cost management
    - Performance-based data placement
    - Data migration between tiers
    - Storage capacity monitoring
    """
    
    def __init__(
        self,
        storage_manager,
        logger=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the tiered storage system"""
        self.storage_manager = storage_manager
        self.logger = logger or get_telemetry_logger()
        self.config = config or {}
        
        # Storage tier configurations
        self._tiers = {}
        self._tiering_rules = {}
        self._migrations = {}
        self._storage_lock = asyncio.Lock()
        
        # Initialize default tiers
        self._initialize_default_tiers()
        
        # Tiering statistics
        self._stats = {
            "total_tiers": len(self._tiers),
            "active_rules": 0,
            "total_migrations": 0,
            "completed_migrations": 0,
            "failed_migrations": 0,
            "bytes_migrated": 0,
            "last_migration": None
        }
        
        # Background processing
        self._tiering_task = None
        self._running = False
    
    def _initialize_default_tiers(self) -> None:
        """Initialize default storage tiers"""
        self._tiers[StorageTier.HOT] = StorageTierConfig(
            tier=StorageTier.HOT,
            storage_type="ssd",
            location="/data/telemetry/hot",
            max_capacity_gb=100,
            current_usage_gb=25,
            performance_tier=1,
            cost_per_gb=0.25,
            access_latency_ms=1.0,
            retention_period=timedelta(days=30),
            compression_enabled=False,
            encryption_enabled=True
        )
        
        self._tiers[StorageTier.WARM] = StorageTierConfig(
            tier=StorageTier.WARM,
            storage_type="ssd",
            location="/data/telemetry/warm",
            max_capacity_gb=500,
            current_usage_gb=125,
            performance_tier=2,
            cost_per_gb=0.15,
            access_latency_ms=5.0,
            retention_period=timedelta(days=90),
            compression_enabled=True,
            encryption_enabled=True
        )
        
        self._tiers[StorageTier.COLD] = StorageTierConfig(
            tier=StorageTier.COLD,
            storage_type="hdd",
            location="/data/telemetry/cold",
            max_capacity_gb=2000,
            current_usage_gb=450,
            performance_tier=3,
            cost_per_gb=0.05,
            access_latency_ms=50.0,
            retention_period=timedelta(days=365),
            compression_enabled=True,
            encryption_enabled=True
        )
        
        self._tiers[StorageTier.ARCHIVE] = StorageTierConfig(
            tier=StorageTier.ARCHIVE,
            storage_type="cloud",
            location="s3://telemetry-archive",
            max_capacity_gb=10000,
            current_usage_gb=1200,
            performance_tier=4,
            cost_per_gb=0.01,
            access_latency_ms=1000.0,
            retention_period=timedelta(days=2555),  # 7 years
            compression_enabled=True,
            encryption_enabled=True
        )
    
    async def create_tiering_rule(
        self,
        name: str,
        policy: TieringPolicy,
        source_tier: StorageTier,
        target_tier: StorageTier,
        conditions: Dict[str, Any],
        priority: int = 5,
        enabled: bool = True
    ) -> str:
        """
        Create a new tiering rule
        
        Args:
            name: Rule name
            policy: Tiering policy type
            source_tier: Source storage tier
            target_tier: Target storage tier
            conditions: Conditions for tiering
            priority: Rule priority (1-10, 1=highest)
            enabled: Whether rule is initially enabled
            
        Returns:
            str: Rule ID
        """
        rule_id = str(uuid.uuid4())
        
        # Validate rule configuration
        self._validate_tiering_rule(source_tier, target_tier, policy, conditions)
        
        # Create rule
        rule = TieringRule(
            rule_id=rule_id,
            name=name,
            policy=policy,
            source_tier=source_tier,
            target_tier=target_tier,
            conditions=conditions,
            priority=priority,
            enabled=enabled,
            created_at=datetime.now()
        )
        
        async with self._storage_lock:
            self._tiering_rules[rule_id] = rule
            
            # Update statistics
            if enabled:
                self._stats["active_rules"] += 1
        
        self.logger.info(
            f"Created tiering rule {rule_id}: {name}",
            rule_id=rule_id,
            policy=policy.value,
            source_tier=source_tier.value,
            target_tier=target_tier.value
        )
        
        return rule_id
    
    async def update_rule(self, rule_id: str, **updates) -> bool:
        """Update an existing tiering rule"""
        async with self._storage_lock:
            rule = self._tiering_rules.get(rule_id)
            if not rule:
                return False
            
            old_enabled = rule.enabled
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            
            # Update statistics if enabled status changed
            if old_enabled != rule.enabled:
                if rule.enabled:
                    self._stats["active_rules"] += 1
                else:
                    self._stats["active_rules"] -= 1
        
        self.logger.info(f"Updated tiering rule {rule_id}")
        return True
    
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a tiering rule"""
        async with self._storage_lock:
            if rule_id not in self._tiering_rules:
                return False
            
            rule = self._tiering_rules[rule_id]
            
            # Update statistics
            if rule.enabled:
                self._stats["active_rules"] -= 1
            
            del self._tiering_rules[rule_id]
        
        self.logger.info(f"Deleted tiering rule {rule_id}")
        return True
    
    async def evaluate_tiering_rules(self) -> List[DataMigration]:
        """Evaluate all active tiering rules and create migrations"""
        migrations = []
        
        async with self._storage_lock:
            active_rules = [r for r in self._tiering_rules.values() if r.enabled]
        
        # Sort rules by priority
        active_rules.sort(key=lambda r: r.priority)
        
        for rule in active_rules:
            try:
                rule_migrations = await self._evaluate_rule(rule)
                migrations.extend(rule_migrations)
            except Exception as e:
                self.logger.error(f"Error evaluating tiering rule {rule.rule_id}: {e}")
        
        return migrations
    
    async def execute_migration(self, migration_id: str) -> bool:
        """Execute a data migration"""
        start_time = datetime.now()
        
        async with self._storage_lock:
            migration = self._migrations.get(migration_id)
            if not migration:
                raise ValueError(f"Migration {migration_id} not found")
            
            # Update migration status
            migration.status = MigrationStatus.IN_PROGRESS
            migration.started_at = start_time
        
        try:
            self.logger.info(
                f"Executing migration {migration_id}: {migration.source_tier.value} -> {migration.target_tier.value}",
                migration_id=migration_id
            )
            
            # Get tier configurations
            source_config = self._tiers[migration.source_tier]
            target_config = self._tiers[migration.target_tier]
            
            # Execute migration
            bytes_migrated = await self._migrate_data(
                migration.data_paths,
                source_config,
                target_config
            )
            
            # Update migration
            migration.bytes_migrated = bytes_migrated
            migration.status = MigrationStatus.COMPLETED
            migration.completed_at = datetime.now()
            
            # Update tier usage
            source_config.current_usage_gb -= bytes_migrated // (1024 * 1024 * 1024)
            target_config.current_usage_gb += bytes_migrated // (1024 * 1024 * 1024)
            
            # Update statistics
            self._stats["completed_migrations"] += 1
            self._stats["bytes_migrated"] += bytes_migrated
            self._stats["last_migration"] = start_time
            
            self.logger.info(
                f"Completed migration {migration_id}: {bytes_migrated} bytes",
                migration_id=migration_id,
                bytes_migrated=bytes_migrated
            )
            
            return True
            
        except Exception as e:
            migration.status = MigrationStatus.FAILED
            migration.error_message = str(e)
            migration.completed_at = datetime.now()
            
            # Update statistics
            self._stats["failed_migrations"] += 1
            
            self.logger.error(
                f"Failed migration {migration_id}: {e}",
                migration_id=migration_id,
                error=str(e)
            )
            
            return False
    
    async def get_tier_config(self, tier: StorageTier) -> Optional[StorageTierConfig]:
        """Get storage tier configuration"""
        return self._tiers.get(tier)
    
    async def get_all_tiers(self) -> Dict[StorageTier, StorageTierConfig]:
        """Get all storage tier configurations"""
        return self._tiers.copy()
    
    async def get_rule(self, rule_id: str) -> Optional[TieringRule]:
        """Get a tiering rule"""
        async with self._storage_lock:
            return self._tiering_rules.get(rule_id)
    
    async def get_all_rules(self) -> List[TieringRule]:
        """Get all tiering rules"""
        async with self._storage_lock:
            return list(self._tiering_rules.values())
    
    async def get_migration(self, migration_id: str) -> Optional[DataMigration]:
        """Get a data migration"""
        async with self._storage_lock:
            return self._migrations.get(migration_id)
    
    async def get_all_migrations(self) -> List[DataMigration]:
        """Get all data migrations"""
        async with self._storage_lock:
            return list(self._migrations.values())
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """Get tiered storage statistics"""
        tier_stats = {}
        total_capacity = 0
        total_usage = 0
        total_cost = 0
        
        for tier, config in self._tiers.items():
            tier_stats[tier.value] = {
                "capacity_gb": config.max_capacity_gb,
                "usage_gb": config.current_usage_gb,
                "utilization_percent": (config.current_usage_gb / config.max_capacity_gb) * 100,
                "cost_per_gb": config.cost_per_gb,
                "monthly_cost": config.current_usage_gb * config.cost_per_gb
            }
            
            total_capacity += config.max_capacity_gb
            total_usage += config.current_usage_gb
            total_cost += config.current_usage_gb * config.cost_per_gb
        
        async with self._storage_lock:
            active_rules = len([r for r in self._tiering_rules.values() if r.enabled])
            pending_migrations = len([m for m in self._migrations.values() if m.status == MigrationStatus.PENDING])
            running_migrations = len([m for m in self._migrations.values() if m.status == MigrationStatus.IN_PROGRESS])
        
        return {
            **self._stats,
            "active_rules": active_rules,
            "pending_migrations": pending_migrations,
            "running_migrations": running_migrations,
            "total_capacity_gb": total_capacity,
            "total_usage_gb": total_usage,
            "overall_utilization_percent": (total_usage / total_capacity) * 100 if total_capacity > 0 else 0,
            "total_monthly_cost": total_cost,
            "tier_statistics": tier_stats,
            "scheduler_running": self._running
        }
    
    # Private methods
    
    def _validate_tiering_rule(
        self,
        source_tier: StorageTier,
        target_tier: StorageTier,
        policy: TieringPolicy,
        conditions: Dict[str, Any]
    ) -> None:
        """Validate tiering rule configuration"""
        if source_tier == target_tier:
            raise ValueError("Source and target tiers must be different")
        
        if not conditions:
            raise ValueError("Conditions are required")
        
        # Validate conditions based on policy
        if policy == TieringPolicy.AGE_BASED and "age_days" not in conditions:
            raise ValueError("Age-based policy requires 'age_days' condition")
        
        if policy == TieringPolicy.ACCESS_FREQUENCY and "access_count" not in conditions:
            raise ValueError("Access frequency policy requires 'access_count' condition")
    
    async def _evaluate_rule(self, rule: TieringRule) -> List[DataMigration]:
        """Evaluate a tiering rule and create migrations"""
        migrations = []
        
        # Get data that matches rule conditions
        matching_data = await self._find_matching_data(rule)
        
        if matching_data:
            migration_id = str(uuid.uuid4())
            
            migration = DataMigration(
                migration_id=migration_id,
                rule_id=rule.rule_id,
                source_tier=rule.source_tier,
                target_tier=rule.target_tier,
                data_paths=matching_data,
                status=MigrationStatus.PENDING,
                created_at=datetime.now()
            )
            
            async with self._storage_lock:
                self._migrations[migration_id] = migration
                self._stats["total_migrations"] += 1
            
            migrations.append(migration)
        
        return migrations
    
    async def _find_matching_data(self, rule: TieringRule) -> List[str]:
        """Find data that matches tiering rule conditions"""
        # Mock implementation - in real system would query storage
        matching_paths = []
        
        if rule.policy == TieringPolicy.AGE_BASED:
            age_days = rule.conditions.get("age_days", 30)
            # Find data older than age_days in source tier
            matching_paths = [f"/data/telemetry/{rule.source_tier.value}/old_data_{i}.json" for i in range(5)]
        
        elif rule.policy == TieringPolicy.ACCESS_FREQUENCY:
            access_count = rule.conditions.get("access_count", 10)
            # Find data with access count below threshold
            matching_paths = [f"/data/telemetry/{rule.source_tier.value}/low_access_{i}.json" for i in range(3)]
        
        return matching_paths
    
    async def _migrate_data(
        self,
        data_paths: List[str],
        source_config: StorageTierConfig,
        target_config: StorageTierConfig
    ) -> int:
        """Migrate data between storage tiers"""
        total_bytes = 0
        
        for data_path in data_paths:
            try:
                # Mock migration - in real system would copy/move files
                source_path = Path(source_config.location) / Path(data_path).name
                target_path = Path(target_config.location) / Path(data_path).name
                
                # Simulate file size
                file_size = 1024 * 1024 * 10  # 10MB per file
                total_bytes += file_size
                
                # Create target directory if needed
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Simulate migration
                await asyncio.sleep(0.1)  # Simulate migration time
                
            except Exception as e:
                self.logger.error(f"Error migrating {data_path}: {e}")
        
        return total_bytes
