"""
Feature flag management system for the scraper framework.

This module provides comprehensive feature flag management, including dynamic flag
evaluation, environment-specific flags, and remote flag management.
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
import time

from .environment_detector import detect_environment, Environment


class FlagType(Enum):
    """Feature flag type enumeration."""
    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    PERCENTAGE = "percentage"
    JSON = "json"


class FlagStatus(Enum):
    """Feature flag status enumeration."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    CONDITIONAL = "conditional"


@dataclass
class FeatureFlag:
    """Feature flag definition."""
    name: str
    flag_type: FlagType
    default_value: Any
    description: str = ""
    tags: List[str] = field(default_factory=list)
    environment_overrides: Dict[str, Any] = field(default_factory=dict)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    rollout_percentage: float = 100.0
    stale_after: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Post-initialization validation."""
        if self.rollout_percentage < 0 or self.rollout_percentage > 100:
            raise ValueError("Rollout percentage must be between 0 and 100")
        
        if self.flag_type == FlagType.PERCENTAGE:
            if not isinstance(self.default_value, (int, float)):
                raise ValueError("Percentage flag must have numeric default value")
            if self.default_value < 0 or self.default_value > 100:
                raise ValueError("Percentage default value must be between 0 and 100")


@dataclass
class FlagEvaluationResult:
    """Result of feature flag evaluation."""
    flag_name: str
    value: Any
    enabled: bool
    reason: str
    environment: str
    rollout_applied: bool = False
    condition_met: bool = False
    evaluation_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class FeatureFlagManager:
    """Feature flag management system."""
    
    def __init__(self):
        """Initialize feature flag manager."""
        self._flags: Dict[str, FeatureFlag] = {}
        self._flag_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl: timedelta = timedelta(minutes=5)
        self._evaluation_stats: Dict[str, Any] = {
            'total_evaluations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_time_ms': 0.0,
            'average_time_ms': 0.0
        }
        self._lock = threading.RLock()
        self._remote_config_url: Optional[str] = None
        self._remote_sync_interval: timedelta = timedelta(minutes=5)
        self._last_remote_sync: Optional[datetime] = None
        self._sync_task: Optional[asyncio.Task] = None
        
        # Built-in flags
        self._initialize_builtin_flags()
    
    def _initialize_builtin_flags(self) -> None:
        """Initialize built-in feature flags."""
        # Debug mode flag
        self.add_flag(FeatureFlag(
            name="debug_mode",
            flag_type=FlagType.BOOLEAN,
            default_value=False,
            description="Enable debug mode with additional logging",
            tags=["debug", "logging"],
            environment_overrides={
                "development": True,
                "testing": True
            }
        ))
        
        # Headless mode flag
        self.add_flag(FeatureFlag(
            name="headless_mode",
            flag_type=FlagType.BOOLEAN,
            default_value=True,
            description="Run browser in headless mode",
            tags=["browser", "ui"],
            environment_overrides={
                "development": False,
                "testing": True
            }
        ))
        
        # Rate limiting flag
        self.add_flag(FeatureFlag(
            name="rate_limiting_enabled",
            flag_type=FlagType.BOOLEAN,
            default_value=True,
            description="Enable rate limiting",
            tags=["rate_limiting", "performance"],
            environment_overrides={
                "development": False,
                "testing": False
            }
        ))
        
        # Stealth mode flag
        self.add_flag(FeatureFlag(
            name="stealth_mode",
            flag_type=FlagType.BOOLEAN,
            default_value=False,
            description="Enable stealth mode for anti-bot detection",
            tags=["stealth", "anti_bot"],
            environment_overrides={
                "production": True
            }
        ))
        
        # Retry enabled flag
        self.add_flag(FeatureFlag(
            name="retry_enabled",
            flag_type=FlagType.BOOLEAN,
            default_value=True,
            description="Enable retry logic for failed operations",
            tags=["retry", "resilience"]
        ))
        
        # Cache enabled flag
        self.add_flag(FeatureFlag(
            name="cache_enabled",
            flag_type=FlagType.BOOLEAN,
            default_value=True,
            description="Enable caching for performance",
            tags=["cache", "performance"]
        ))
        
        # Monitoring enabled flag
        self.add_flag(FeatureFlag(
            name="monitoring_enabled",
            flag_type=FlagType.BOOLEAN,
            default_value=True,
            description="Enable monitoring and metrics collection",
            tags=["monitoring", "metrics"]
        ))
        
        # Log level flag
        self.add_flag(FeatureFlag(
            name="log_level",
            flag_type=FlagType.STRING,
            default_value="INFO",
            description="Logging level",
            tags=["logging"],
            environment_overrides={
                "development": "DEBUG",
                "testing": "INFO"
            }
        ))
        
        # Timeout multiplier flag
        self.add_flag(FeatureFlag(
            name="timeout_multiplier",
            flag_type=FlagType.FLOAT,
            default_value=1.0,
            description="Multiplier for timeout values",
            tags=["timeout", "performance"],
            environment_overrides={
                "development": 2.0,
                "testing": 0.5
            }
        ))
    
    def add_flag(self, flag: FeatureFlag) -> None:
        """Add a feature flag."""
        with self._lock:
            self._flags[flag.name] = flag
            # Clear cache for this flag
            if flag.name in self._flag_cache:
                del self._flag_cache[flag.name]
                del self._cache_timestamps[flag.name]
    
    def remove_flag(self, flag_name: str) -> bool:
        """Remove a feature flag."""
        with self._lock:
            if flag_name in self._flags:
                del self._flags[flag_name]
                # Clear cache for this flag
                if flag_name in self._flag_cache:
                    del self._flag_cache[flag_name]
                    del self._cache_timestamps[flag_name]
                return True
            return False
    
    def get_flag(self, flag_name: str) -> Optional[FeatureFlag]:
        """Get a feature flag by name."""
        with self._lock:
            return self._flags.get(flag_name)
    
    def get_all_flags(self) -> Dict[str, FeatureFlag]:
        """Get all feature flags."""
        with self._lock:
            return self._flags.copy()
    
    def get_flags_by_tag(self, tag: str) -> Dict[str, FeatureFlag]:
        """Get all flags with a specific tag."""
        with self._lock:
            return {
                name: flag for name, flag in self._flags.items()
                if tag in flag.tags
            }
    
    def evaluate_flag(self, flag_name: str, context: Optional[Dict[str, Any]] = None,
                     environment: Optional[str] = None) -> FlagEvaluationResult:
        """
        Evaluate a feature flag.
        
        Args:
            flag_name: Name of the flag to evaluate
            context: Optional context for conditional evaluation
            environment: Environment for evaluation (auto-detected if None)
            
        Returns:
            Flag evaluation result
        """
        start_time = time.time()
        
        try:
            # Detect environment if not provided
            if environment is None:
                environment = detect_environment().value
            
            # Get flag
            flag = self.get_flag(flag_name)
            if not flag:
                return FlagEvaluationResult(
                    flag_name=flag_name,
                    value=None,
                    enabled=False,
                    reason=f"Flag '{flag_name}' not found",
                    environment=environment,
                    evaluation_time_ms=(time.time() - start_time) * 1000
                )
            
            # Check cache first
            cache_key = f"{flag_name}:{environment}"
            if cache_key in self._flag_cache:
                cache_timestamp = self._cache_timestamps[cache_key]
                if datetime.utcnow() - cache_timestamp < self._cache_ttl:
                    cached_result = self._flag_cache[cache_key]
                    self._evaluation_stats['cache_hits'] += 1
                    return cached_result
            
            self._evaluation_stats['cache_misses'] += 1
            
            # Determine value based on environment overrides
            value = flag.default_value
            if environment in flag.environment_overrides:
                value = flag.environment_overrides[environment]
            
            # Apply rollout percentage
            rollout_applied = False
            if flag.rollout_percentage < 100.0:
                import hashlib
                # Use consistent hashing for rollout
                hash_input = f"{flag_name}:{environment}"
                hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
                rollout_applied = (hash_value % 100) < flag.rollout_percentage
                
                if not rollout_applied:
                    value = self._get_disabled_value(flag.flag_type)
            
            # Apply conditions
            condition_met = False
            if flag.conditions and context:
                condition_met = self._evaluate_conditions(flag.conditions, context)
                if not condition_met:
                    value = self._get_disabled_value(flag.flag_type)
            
            # Determine if flag is enabled
            enabled = self._is_value_enabled(value, flag.flag_type)
            
            # Create result
            result = FlagEvaluationResult(
                flag_name=flag_name,
                value=value,
                enabled=enabled,
                reason=self._get_evaluation_reason(flag, enabled, rollout_applied, condition_met),
                environment=environment,
                rollout_applied=rollout_applied,
                condition_met=condition_met,
                evaluation_time_ms=(time.time() - start_time) * 1000
            )
            
            # Cache result
            with self._lock:
                self._flag_cache[cache_key] = result
                self._cache_timestamps[cache_key] = datetime.utcnow()
            
            # Update stats
            self._evaluation_stats['total_evaluations'] += 1
            self._evaluation_stats['total_time_ms'] += result.evaluation_time_ms
            self._evaluation_stats['average_time_ms'] = (
                self._evaluation_stats['total_time_ms'] / 
                self._evaluation_stats['total_evaluations']
            )
            
            return result
            
        except Exception as e:
            return FlagEvaluationResult(
                flag_name=flag_name,
                value=None,
                enabled=False,
                reason=f"Evaluation failed: {str(e)}",
                environment=environment or "unknown",
                evaluation_time_ms=(time.time() - start_time) * 1000
            )
    
    def _get_disabled_value(self, flag_type: FlagType) -> Any:
        """Get the disabled value for a flag type."""
        disabled_values = {
            FlagType.BOOLEAN: False,
            FlagType.STRING: "",
            FlagType.INTEGER: 0,
            FlagType.FLOAT: 0.0,
            FlagType.PERCENTAGE: 0.0,
            FlagType.JSON: {}
        }
        return disabled_values.get(flag_type, None)
    
    def _is_value_enabled(self, value: Any, flag_type: FlagType) -> bool:
        """Check if a value indicates the flag is enabled."""
        if flag_type == FlagType.BOOLEAN:
            return bool(value)
        elif flag_type == FlagType.STRING:
            return str(value).lower() in ['true', '1', 'yes', 'on', 'enabled']
        elif flag_type in [FlagType.INTEGER, FlagType.FLOAT, FlagType.PERCENTAGE]:
            return float(value) > 0
        elif flag_type == FlagType.JSON:
            return bool(value) and value != {}
        return False
    
    def _evaluate_conditions(self, conditions: List[Dict[str, Any]], 
                            context: Dict[str, Any]) -> bool:
        """Evaluate flag conditions."""
        for condition in conditions:
            try:
                field = condition.get('field')
                operator = condition.get('operator')
                expected_value = condition.get('value')
                
                if field not in context:
                    continue
                
                actual_value = context[field]
                
                if operator == 'equals':
                    if actual_value != expected_value:
                        return False
                elif operator == 'not_equals':
                    if actual_value == expected_value:
                        return False
                elif operator == 'contains':
                    if str(expected_value) not in str(actual_value):
                        return False
                elif operator == 'not_contains':
                    if str(expected_value) in str(actual_value):
                        return False
                elif operator == 'greater_than':
                    if not (isinstance(actual_value, (int, float)) and isinstance(expected_value, (int, float))):
                        return False
                    if actual_value <= expected_value:
                        return False
                elif operator == 'less_than':
                    if not (isinstance(actual_value, (int, float)) and isinstance(expected_value, (int, float))):
                        return False
                    if actual_value >= expected_value:
                        return False
                elif operator == 'in':
                    if expected_value not in actual_value:
                        return False
                elif operator == 'not_in':
                    if expected_value in actual_value:
                        return False
                
            except Exception:
                # If condition evaluation fails, assume condition not met
                return False
        
        return True
    
    def _get_evaluation_reason(self, flag: FeatureFlag, enabled: bool, 
                               rollout_applied: bool, condition_met: bool) -> str:
        """Get evaluation reason."""
        if not enabled:
            if rollout_applied:
                return f"Disabled by rollout ({flag.rollout_percentage}%)"
            elif condition_met:
                return "Disabled by condition"
            else:
                return f"Disabled (value: {flag.default_value})"
        else:
            if rollout_applied:
                return f"Enabled by rollout ({flag.rollout_percentage}%)"
            elif condition_met:
                return "Enabled by condition"
            else:
                return f"Enabled (value: {flag.default_value})"
    
    def is_enabled(self, flag_name: str, context: Optional[Dict[str, Any]] = None,
                   environment: Optional[str] = None) -> bool:
        """Check if a feature flag is enabled."""
        result = self.evaluate_flag(flag_name, context, environment)
        return result.enabled
    
    def get_value(self, flag_name: str, context: Optional[Dict[str, Any]] = None,
                 environment: Optional[str] = None) -> Any:
        """Get the value of a feature flag."""
        result = self.evaluate_flag(flag_name, context, environment)
        return result.value
    
    def set_flag_value(self, flag_name: str, value: Any, environment: Optional[str] = None,
                       persist: bool = False) -> bool:
        """Set the value of a feature flag."""
        try:
            flag = self.get_flag(flag_name)
            if not flag:
                return False
            
            if environment:
                if environment not in flag.environment_overrides:
                    flag.environment_overrides[environment] = {}
                flag.environment_overrides[environment] = value
            else:
                flag.default_value = value
            
            flag.updated_at = datetime.utcnow()
            
            # Clear cache for this flag
            with self._lock:
                for cache_key in list(self._flag_cache.keys()):
                    if cache_key.startswith(f"{flag_name}:"):
                        del self._flag_cache[cache_key]
                        del self._cache_timestamps[cache_key]
            
            # Persist if requested
            if persist:
                self._persist_flags()
            
            return True
            
        except Exception:
            return False
    
    def enable_flag(self, flag_name: str, environment: Optional[str] = None,
                   persist: bool = False) -> bool:
        """Enable a feature flag."""
        flag = self.get_flag(flag_name)
        if flag:
            enabled_value = self._get_enabled_value(flag.flag_type)
            return self.set_flag_value(flag_name, enabled_value, environment, persist)
        return False
    
    def disable_flag(self, flag_name: str, environment: Optional[str] = None,
                    persist: bool = False) -> bool:
        """Disable a feature flag."""
        flag = self.get_flag(flag_name)
        if flag:
            disabled_value = self._get_disabled_value(flag.flag_type)
            return self.set_flag_value(flag_name, disabled_value, environment, persist)
        return False
    
    def _get_enabled_value(self, flag_type: FlagType) -> Any:
        """Get the enabled value for a flag type."""
        enabled_values = {
            FlagType.BOOLEAN: True,
            FlagType.STRING: "true",
            FlagType.INTEGER: 1,
            FlagType.FLOAT: 1.0,
            FlagType.PERCENTAGE: 100.0,
            FlagType.JSON: {"enabled": True}
        }
        return enabled_values.get(flag_type, None)
    
    def set_rollout_percentage(self, flag_name: str, percentage: float, 
                             persist: bool = False) -> bool:
        """Set rollout percentage for a flag."""
        try:
            flag = self.get_flag(flag_name)
            if not flag:
                return False
            
            if percentage < 0 or percentage > 100:
                return False
            
            flag.rollout_percentage = percentage
            flag.updated_at = datetime.utcnow()
            
            # Clear cache for this flag
            with self._lock:
                for cache_key in list(self._flag_cache.keys()):
                    if cache_key.startswith(f"{flag_name}:"):
                        del self._flag_cache[cache_key]
                        del self._cache_timestamps[cache_key]
            
            # Persist if requested
            if persist:
                self._persist_flags()
            
            return True
            
        except Exception:
            return False
    
    def add_condition(self, flag_name: str, field: str, operator: str, 
                     value: Any, persist: bool = False) -> bool:
        """Add a condition to a flag."""
        try:
            flag = self.get_flag(flag_name)
            if not flag:
                return False
            
            condition = {
                'field': field,
                'operator': operator,
                'value': value
            }
            
            flag.conditions.append(condition)
            flag.updated_at = datetime.utcnow()
            
            # Clear cache for this flag
            with self._lock:
                for cache_key in list(self._flag_cache.keys()):
                    if cache_key.startswith(f"{flag_name}:"):
                        del self._flag_cache[cache_key]
                        del self._cache_timestamps[cache_key]
            
            # Persist if requested
            if persist:
                self._persist_flags()
            
            return True
            
        except Exception:
            return False
    
    def clear_cache(self, flag_name: Optional[str] = None) -> None:
        """Clear flag evaluation cache."""
        with self._lock:
            if flag_name:
                # Clear cache for specific flag
                keys_to_remove = [
                    key for key in self._flag_cache.keys()
                    if key.startswith(f"{flag_name}:")
                ]
                for key in keys_to_remove:
                    del self._flag_cache[key]
                    if key in self._cache_timestamps:
                        del self._cache_timestamps[key]
            else:
                # Clear all cache
                self._flag_cache.clear()
                self._cache_timestamps.clear()
    
    def get_evaluation_stats(self) -> Dict[str, Any]:
        """Get evaluation statistics."""
        return self._evaluation_stats.copy()
    
    def get_flag_info(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a flag."""
        flag = self.get_flag(name=flag_name)
        if not flag:
            return None
        
        return {
            'name': flag.name,
            'type': flag.flag_type.value,
            'default_value': flag.default_value,
            'description': flag.description,
            'tags': flag.tags,
            'environment_overrides': flag.environment_overrides,
            'conditions': flag.conditions,
            'rollout_percentage': flag.rollout_percentage,
            'metadata': flag.metadata,
            'created_at': flag.created_at.isoformat(),
            'updated_at': flag.updated_at.isoformat()
        }
    
    def export_flags(self) -> Dict[str, Any]:
        """Export all flags to dictionary format."""
        return {
            name: {
                'type': flag.flag_type.value,
                'default_value': flag.default_value,
                'description': flag.description,
                'tags': flag.tags,
                'environment_overrides': flag.environment_overrides,
                'conditions': flag.conditions,
                'rollout_percentage': flag.rollout_percentage,
                'metadata': flag.metadata,
                'created_at': flag.created_at.isoformat(),
                'updated_at': flag.updated_at.isoformat()
            }
            for name, flag in self._flags.items()
        }
    
    def import_flags(self, flags_data: Dict[str, Any]) -> None:
        """Import flags from dictionary format."""
        for flag_name, flag_data in flags_data.items():
            try:
                flag = FeatureFlag(
                    name=flag_name,
                    flag_type=FlagType(flag_data['type']),
                    default_value=flag_data['default_value'],
                    description=flag_data.get('description', ''),
                    tags=flag_data.get('tags', []),
                    environment_overrides=flag_data.get('environment_overrides', {}),
                    conditions=flag_data.get('conditions', []),
                    rollout_percentage=flag_data.get('rollout_percentage', 100.0),
                    metadata=flag_data.get('metadata', {})
                )
                
                # Set timestamps
                flag.created_at = datetime.fromisoformat(flag_data.get('created_at', datetime.utcnow().isoformat()))
                flag.updated_at = datetime.fromisoformat(flag_data.get('updated_at', datetime.utcnow().isoformat()))
                
                self.add_flag(flag)
                
            except Exception as e:
                print(f"Error importing flag '{flag_name}': {str(e)}")
    
    def _persist_flags(self) -> None:
        """Persist flags to file."""
        try:
            current_dir = Path.cwd()
            flags_file = current_dir / 'feature_flags.json'
            
            flags_data = self.export_flags()
            
            with open(flags_file, 'w', encoding='utf-8') as f:
                json.dump(flags_data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"Error persisting flags: {str(e)}")
    
    def load_flags_from_file(self, file_path: Optional[str] = None) -> bool:
        """Load flags from file."""
        try:
            if file_path is None:
                current_dir = Path.cwd()
                file_path = current_dir / 'feature_flags.json'
            
            with open(file_path, 'r', encoding='utf-8') as f:
                flags_data = json.load(f)
            
            self.import_flags(flags_data)
            return True
            
        except Exception as e:
            print(f"Error loading flags from {file_path}: {str(e)}")
            return False
    
    def start_remote_sync(self, config_url: str, sync_interval: timedelta = None) -> None:
        """Start remote configuration synchronization."""
        self._remote_config_url = config_url
        self._remote_sync_interval = sync_interval or self._remote_sync_interval
        
        if self._sync_task:
            self._sync_task.cancel()
        
        self._sync_task = asyncio.create_task(self._remote_sync_loop())
    
    async def _remote_sync_loop(self) -> None:
        """Remote synchronization loop."""
        while True:
            try:
                await self._sync_from_remote()
                await asyncio.sleep(self._remote_sync_interval.total_seconds())
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Remote sync error: {str(e)}")
                await asyncio.sleep(self._remote_sync_interval.total_seconds())
    
    async def _sync_from_remote(self) -> None:
        """Sync flags from remote configuration."""
        # This would implement remote synchronization logic
        # For now, it's a placeholder
        pass


# Global feature flag manager instance
_feature_flag_manager = FeatureFlagManager()


# Convenience functions
def is_enabled(flag_name: str, context: Optional[Dict[str, Any]] = None,
               environment: Optional[str] = None) -> bool:
    """Check if a feature flag is enabled."""
    return _feature_flag_manager.is_enabled(flag_name, context, environment)


def get_value(flag_name: str, context: Optional[Dict[str, Any]] = None,
                 environment: Optional[str] = None) -> Any:
    """Get the value of a feature flag."""
    return _feature_flag_manager.get_value(flag_name, context, environment)


def add_flag(flag: FeatureFlag) -> None:
    """Add a feature flag."""
    _feature_flag_manager.add_flag(flag)


def get_flag(flag_name: str) -> Optional[FeatureFlag]:
    """Get a feature flag."""
    return _feature_flag_manager.get_flag(flag_name)


def enable_flag(flag_name: str, environment: Optional[str] = None, persist: bool = False) -> bool:
    """Enable a feature flag."""
    return _feature_flag_manager.enable_flag(flag_name, environment, persist)


def disable_flag(flag_name: str, environment: Optional[str] = None, persist: bool = False) -> bool:
    """Disable a feature flag."""
    return _feature_flag_manager.disable_flag(flag_name, environment, persist)


def get_all_flags() -> Dict[str, FeatureFlag]:
    """Get all feature flags."""
    return _feature_flag_manager.get_all_flags()


def get_flags_by_tag(tag: str) -> Dict[str, FeatureFlag]:
    """Get all flags with a specific tag."""
    return _feature_flag_manager.get_flags_by_tag(tag)


def export_flags() -> Dict[str, Any]:
    """Export all flags."""
    return _feature_flag_manager.export_flags()


def import_flags(flags_data: Dict[str, Any]) -> None:
    """Import flags from dictionary."""
    _feature_flag_manager.import_flags(flags_data)


def get_evaluation_stats() -> Dict[str, Any]:
    """Get evaluation statistics."""
    return _feature_flag_manager.get_evaluation_stats()
