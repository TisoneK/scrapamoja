"""
Configuration merge logic for environment overrides in the scraper framework.

This module provides comprehensive configuration merging capabilities, including
environment-specific overrides, inheritance, and conflict resolution.
"""

from typing import Dict, Any, List, Optional, Union, Callable, Type
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .environment_detector import detect_environment, Environment
from .config_schemas import ConfigSchema, get_schema


class MergeStrategy(Enum):
    """Configuration merge strategy enumeration."""
    REPLACE = "replace"
    MERGE = "merge"
    APPEND = "append"
    PREPEND = "prepend"
    SMART_MERGE = "smart_merge"


@dataclass
class MergeResult:
    """Result of configuration merge operation."""
    success: bool
    merged_config: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    merge_strategy: str = ""
    merge_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ConfigMerger:
    """Configuration merger with environment override support."""
    
    def __init__(self):
        """Initialize configuration merger."""
        self._merge_strategies = {
            'replace': self._replace_merge,
            'merge': self._deep_merge,
            'append': self._append_merge,
            'prepend': self._prepend_merge,
            'smart_merge': self._smart_merge
        }
        
        self._custom_strategies: Dict[str, Callable] = {}
        self._merge_history: List[MergeResult] = []
        self._performance_stats = {
            'total_merges': 0,
            'total_time_ms': 0.0,
            'average_time_ms': 0.0
        }
        
        # Default merge settings
        self._default_strategy = MergeStrategy.SMART_MERGE
        self._conflict_resolution = "last_wins"
        self._preserve_metadata = True
    
    def set_default_strategy(self, strategy: Union[MergeStrategy, str]) -> None:
        """Set the default merge strategy."""
        if isinstance(strategy, str):
            try:
                strategy = MergeStrategy(strategy.lower())
            except ValueError:
                raise ValueError(f"Invalid merge strategy: {strategy}")
        
        self._default_strategy = strategy
    
    def set_conflict_resolution(self, resolution: str) -> None:
        """Set conflict resolution strategy."""
        if resolution not in ['first_wins', 'last_wins', 'raise_error']:
            raise ValueError(f"Invalid conflict resolution: {resolution}")
        
        self._conflict_resolution = resolution
    
    def set_preserve_metadata(self, preserve: bool) -> None:
        """Set whether to preserve metadata during merges."""
        self._preserve_metadata = preserve
    
    def add_custom_strategy(self, name: str, strategy: Callable) -> None:
        """Add a custom merge strategy."""
        self._custom_strategies[name] = strategy
    
    def remove_custom_strategy(self, name: str) -> bool:
        """Remove a custom merge strategy."""
        if name in self._custom_strategies:
            del self._custom_strategies[name]
            return True
        return False
    
    def merge_configs(self, base_config: Dict[str, Any], 
                     override_configs: List[Dict[str, Any]],
                     environment: Optional[str] = None,
                     strategy: Optional[Union[MergeStrategy, str]] = None,
                     schema_name: Optional[str] = None) -> MergeResult:
        """
        Merge multiple configuration dictionaries.
        
        Args:
            base_config: Base configuration
            override_configs: List of override configurations
            environment: Target environment (auto-detected if None)
            strategy: Merge strategy to use
            schema_name: Schema name for validation
            
        Returns:
            Merge result
        """
        start_time = datetime.utcnow()
        
        try:
            # Detect environment if not provided
            if environment is None:
                environment = detect_environment().value
            
            # Determine merge strategy
            if strategy is None:
                strategy = self._default_strategy
            
            elif isinstance(strategy, str):
                try:
                    strategy = MergeStrategy(strategy.lower())
                except ValueError:
                    return MergeResult(
                        success=False,
                        errors=[f"Invalid merge strategy: {strategy}"]
                    )
            
            # Start with base configuration
            merged_config = base_config.copy()
            
            # Apply overrides in order
            for override_config in override_configs:
                if not override_config:
                    continue
                
                # Validate override config if schema provided
                if schema_name:
                    schema = get_schema(schema_name)
                    if schema:
                        validation_result = schema.validate_config(override_config, environment)
                        if not validation_result['valid']:
                            return MergeResult(
                                success=False,
                                errors=[f"Override config validation failed: {validation_result['errors']}"]
                            )
                
                # Merge configuration
                merged_config = self._merge_two_configs(
                    merged_config, 
                    override_config, 
                    strategy
                )
            
            # Validate final configuration if schema provided
            if schema_name:
                schema = get_schema(schema_name)
                if schema:
                    validation_result = schema.validate_config(merged_config, environment)
                    if not validation_result['valid']:
                        return MergeResult(
                            success=False,
                            errors=[f"Final config validation failed: {validation_result['errors']}"]
                        )
            
            # Calculate merge time
            end_time = datetime.utcnow()
            merge_time_ms = (end_time - start_time).total_seconds() * 1000
            
            result = MergeResult(
                success=True,
                merged_config=merged_config,
                merge_strategy=str(strategy.value),
                environment=environment,
                merge_time_ms=merge_time_ms
            )
            
            # Update stats
            self._update_performance_stats(result)
            
            # Store in history
            self._merge_history.append(result)
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            merge_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return MergeResult(
                success=False,
                errors=[f"Merge failed: {str(e)}"],
                merge_time_ms=merge_time_ms
            )
    
    def merge_two_configs(self, base_config: Dict[str, Any], 
                        override_config: Dict[str, Any],
                        strategy: Union[MergeStrategy, str]) -> Dict[str, Any]:
        """Merge two configuration dictionaries."""
        if isinstance(strategy, str):
            strategy = MergeStrategy(strategy.lower())
        
        if strategy == MergeStrategy.REPLACE:
            return self._replace_merge(base_config, override_config)
        elif strategy == MergeStrategy.MERGE:
            return self._deep_merge(base_config, override_config)
        elif strategy == MergeStrategy.APPEND:
            return self._append_merge(base_config, override_config)
        elif strategy == MergeStrategy.PREPEND:
            return self._prepend_merge(base_config, override_config)
        elif strategy == MergeStrategy.SMART_MERGE:
            return self._smart_merge(base_config, override_config)
        elif strategy in self._custom_strategies:
            return self._custom_strategies[str(strategy)](base_config, override_config)
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")
    
    def _replace_merge(self, base_config: Dict[str, Any], 
                        override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Replace configuration with override."""
        return override_config.copy()
    
    def _deep_merge(self, base_config: Dict[str, Any], 
                   override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base_config.copy()
        
        for key, value in override_config.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._deep_merge(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    def _append_merge(self, base_config: Dict[str, Any], 
                   override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Append configuration items to base configuration."""
        result = base_config.copy()
        
        for key, value in override_config.items():
            if key in result:
                if isinstance(result[key], list):
                    if isinstance(value, list):
                        result[key].extend(value)
                    else:
                        result[key] = [result[key], value]
                else:
                    result[key] = [result[key], value]
            else:
                result[key] = [value]
        
        return result
    
    def _prepend_merge(self, base_config: Dict[str, Any], 
                     override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepend configuration items to base configuration."""
        result = override_config.copy()
        
        for key, value in base_config.items():
            if key in result:
                if isinstance(result[key], list):
                    if isinstance(value, list):
                        result[key] = value + result[key]
                    else:
                        result[key] = [value, result[key]]
                else:
                    result[key] = [value]
            else:
                result[key] = [value]
        
        return result
    
    def _smart_merge(self, base_config: Dict[str, Any], 
                     override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Smart merge based on data types and structure."""
        result = base_config.copy()
        
        for key, value in override_config.items():
            if key in result:
                base_value = result[key]
                
                # Smart merge based on types
                if isinstance(base_value, dict) and isinstance(value, dict):
                    result[key] = self._deep_merge(base_value, value)
                elif isinstance(base_value, list) and isinstance(value, list):
                    # Merge lists intelligently
                    if isinstance(value[0], dict) and isinstance(base_value[0], dict):
                        # List of dictionaries - merge each
                        merged_list = []
                        for i, base_item in enumerate(base_value):
                            if i < len(value) and isinstance(value[i], dict):
                                merged_item = self._deep_merge(base_item, value[i])
                                merged_list.append(merged_item)
                            else:
                                merged_list.append(base_item)
                        
                            result[key] = merged_list
                        else:
                            result[key] = base_value + value
                    else:
                        result[key] = base_value + value
                elif isinstance(base_value, set) and isinstance(value, set):
                    result[key] = list(base_value) + list(value)
                elif isinstance(base_value, (list, tuple)) and isinstance(value, (list, tuple)):
                    result[key] = list(base_value) + list(value)
                else:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    
    def merge_environment_configs(self, base_config: Dict[str, Any], 
                                 environment_overrides: Dict[str, Dict[str, Any]],
                                 target_environment: Optional[str] = None) -> Dict[str, Any]:
        """Merge environment-specific configurations."""
        if target_environment is None:
            target_environment = detect_environment().value
        
        # Start with base configuration
        merged_config = base_config.copy()
        
        # Apply environment overrides
        if target_environment in environment_overrides:
            env_config = environment_overrides[target_environment]
            merged_config = self._deep_merge(merged_config, env_config)
        
        return merged_config
    
    def merge_with_defaults(self, config: Dict[str, Any], 
                             defaults: Dict[str, Any],
                             environment: Optional[str] = None) -> Dict[str, Any]:
        """Merge configuration with defaults."""
        if environment is None:
            environment = detect_environment().value
        
        # Start with defaults
        merged_config = defaults.copy()
        
        # Apply configuration
        merged_config.update(config)
        
        # Add environment information
        merged_config['environment'] = environment
        merged_config['config_sources'].append('defaults')
        
        return merged_config
    
    def resolve_conflicts(self, conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve configuration conflicts."""
        resolved = {}
        
        for conflict in conflicts:
            field_name = conflict['field']
            values = conflict['values']
            
            if self._conflict_resolution == 'first_wins':
                resolved[field_name] = values[0]
            elif self._conflict_resolution == 'last_wins':
                resolved[field_name] = values[-1]
            elif self._conflict_resolution == 'raise_error':
                raise ValueError(f"Configuration conflict for field '{field_name}': {values}")
            else:
                # Default to first value
                resolved[field_name] = values[0]
        
        return resolved
    
    def validate_merge(self, merged_config: Dict[str, Any], 
                       schema_name: Optional[str] = None,
                       environment: Optional[str] = None) -> Dict[str, Any]:
        """Validate merged configuration."""
        if not schema_name:
            return {
                'valid': True,
                'errors': [],
                'warnings': []
            }
        
        schema = get_schema(schema_name)
        if not schema:
            return {
                'valid': False,
                'errors': [f"Schema '{schema_name}' not found"],
                'warnings': []
            }
        
        return schema.validate_config(merged_config, environment)
    
    def create_merge_plan(self, configs: List[Dict[str, Any]], 
                           environment: Optional[str] = None) -> Dict[str, Any]:
        """Create a merge plan for multiple configurations."""
        if environment is None:
            environment = detect_environment().value
        
        plan = {
            'environment': environment,
            'configs': configs,
            'merge_order': list(range(len(configs))),
            'conflicts': [],
            'strategy': self._default_strategy.value,
            'estimated_time_ms': 0
        }
        
        # Analyze conflicts
        all_keys = set()
        for i, config in enumerate(configs):
            config_keys = set(config.keys())
            conflicts = all_keys & set(plan['configs'][i]['keys']) if i < len(plan['configs']) else set()
            all_keys.update(config_keys)
            
            for j in range(i + 1, len(configs)):
                next_keys = set(configs[j].keys())
                conflicts.extend(list(all_keys & next_keys))
                all_keys.update(next_keys)
        
        plan['conflicts'] = [
            {'field': key, 'values': []}
            for key in conflicts
        ]
        
        # Estimate time
        plan['estimated_time_ms'] = len(configs) * 10  # Estimate 10ms per merge
        
        return plan
    
    def execute_merge_plan(self, plan: Dict[str, Any]) -> MergeResult:
        """Execute a merge plan."""
        configs = plan['configs']
        strategy = plan['strategy']
        
        start_time = datetime.utcnow()
        
        # Start with first config
        merged_config = configs[0].copy()
        
        # Merge remaining configs
        for i in range(1, len(configs)):
            merged_config = self._merge_two_configs(merged_config, configs[i], strategy)
        
        # Resolve conflicts
        if plan['conflicts']:
            resolved_config = self.resolve_conflicts(plan['conflicts'])
            for key, value in resolved_config.items():
                merged_config[key] = value
        
        end_time = datetime.utcnow()
        merge_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return MergeResult(
            success=True,
            merged_config=merged_config,
            conflicts=plan['conflicts'],
            merge_strategy=str(strategy),
            merge_time_ms=merge_time_ms
        )
    
    def get_merge_history(self, limit: Optional[int] = None) -> List[MergeResult]:
        """Get merge history."""
        if limit:
            return self._merge_history[-limit:]
        return self._merge_history.copy()
    
    def clear_history(self) -> None:
        """Clear merge history."""
        self._merge_history.clear()
    
    def get_performance_stats(self) -> Dict[str, any]:
        """Get performance statistics."""
        return self._performance_stats.copy()
    
    def export_merge_rules(self) -> Dict[str, Any]:
        """Export merge rules."""
        return {
            'default_strategy': self._default_strategy.value,
            'conflict_resolution': self._conflict_resolution,
            'preserve_metadata': self._preserve_metadata,
            'custom_strategies': list(self._custom_strategies.keys()),
            'performance_stats': self.get_performance_stats()
        }
    
    def import_merge_rules(self, rules: Dict[str, Any]) -> None:
        """Import merge rules."""
        if 'default_strategy' in rules:
            try:
                self._default_strategy = MergeStrategy(rules['default_strategy'])
            except ValueError:
                raise ValueError(f"Invalid default strategy: {rules['default_strategy']}")
        
        if 'conflict_resolution' in rules:
            if rules['conflict_resolution'] not in ['first_wins', 'last_wins', 'raise_error']:
                raise ValueError(f"Invalid conflict resolution: {rules['conflict_resolution']}")
            self._conflict_resolution = rules['conflict_resolution']
        
        if 'preserve_metadata' in rules:
            self._preserve_metadata = rules['preserve_metadata']
        
        if 'custom_strategies' in rules:
            for name, strategy in rules['custom_strategies'].items():
                self._custom_strategies[name] = strategy
    
    def create_field_merger(self, field_name: str, 
                           merge_strategy: Union[MergeStrategy, str] = None,
                           condition: Optional[Callable[[Any, Any], bool]] = None) -> Callable:
        """Create a field-specific merger."""
        def field_merger(base_value: Any, override_value: Any) -> Any:
            # Apply condition if provided
            if condition and not condition(base_value, override_value):
                return base_value
            
            # Use specified strategy
            if merge_strategy is None:
                strategy = self._default_strategy
            
            if isinstance(merge_strategy, str):
                strategy = MergeStrategy(merge_strategy.lower())
            
            return self._merge_two_configs({field_name: base_value}, {field_name: override_value}, strategy)
        
        return field_merger
    
    def create_list_merger(self, field_name: str, 
                         merge_strategy: Union[MergeStrategy, str] = None,
                         unique: bool = False) -> Callable:
        """Create a list field merger."""
        def list_merger(base_value: List[Any], override_value: List[Any]) -> List[Any]:
            # Apply condition if provided
            if not override_value:
                return base_value
            
            # Use specified strategy
            if merge_strategy is None:
                strategy = self._default_strategy
            
            if isinstance(merge_strategy, str):
                strategy = MergeStrategy(merge_strategy.lower())
            
            if strategy == MergeStrategy.APPEND:
                if unique:
                    # Remove duplicates
                    combined = base_value + override_value
                    return list(dict.fromkeys(combined).values())
                else:
                    return base_value + override_value
            elif strategy == MergeStrategy.PREPEND:
                if unique:
                    # Remove duplicates
                    combined = override_value + base_value
                    return list(dict.fromkeys(combined).values())
                else:
                    return override_value + base_value
            elif strategy == MergeStrategy.MERGE:
                if unique:
                    # Merge lists intelligently
                    combined = {}
                    for item in base_value + override_value:
                        if isinstance(item, dict):
                            combined.update(item)
                        else:
                            combined[item] = item
                    return list(combined.values())
                else:
                    return base_value + override_value
            else:
                return self._deep_merge(base_value, override_value)
        
        return list_merger
    
    def create_dict_merger(self, merge_strategy: Union[MergeStrategy, str] = None) -> Callable:
        """Create a dictionary merger."""
        def dict_merger(base_value: Dict[str, Any], override_value: Dict[str, Any]) -> Dict[str, Any]:
            if merge_strategy is None:
                strategy = self._default_strategy
            
            if isinstance(merge_strategy, str):
                strategy = MergeStrategy(merge_strategy.lower())
            
            return self._merge_two_configs(base_value, override_value, strategy)
        
        return dict_merger
    
    def get_merge_summary(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of configuration structure."""
        summary = {
            'total_keys': len(config),
            'nested_levels': self._count_nested_levels(config),
            'data_types': self._get_data_types(config),
            'empty_values': [k for k, v in config.items() if not v],
            'list_values': [k for k, v in config.items() if isinstance(v, list)],
            'dict_values': [k for k, v in config.items() if isinstance(v, dict)]
        }
        
        return summary
    
    def _count_nested_levels(self, config: Dict[str, Any], level: int = 0) -> int:
        """Count nested levels in configuration."""
        max_level = level
        current_level = level
        
        for value in config.values():
            if isinstance(value, dict):
                current_level += 1
                child_level = self._count_nested_levels(value, current_level)
                max_level = max(max_level, child_level)
        
        return max_level
    
    def _get_data_types(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Get data types in configuration."""
        types = {}
        
        for key, value in config.items():
            if isinstance(value, bool):
                types[key] = 'boolean'
            elif isinstance(value, int):
                types[key] = 'integer'
            elif isinstance(value, float):
                types[key] = 'float'
            elif isinstance(value, str):
                types[key] = 'string'
            elif isinstance(value, list):
                types[key] = 'list'
            elif isinstance(value, dict):
                types[key] = 'dict'
            elif value is None:
                types[key] = 'null'
            else:
                types[key] = type(value).__name__
        
        return types


# Global config merger instance
_config_merger = ConfigMerger()


# Convenience functions
def merge_configs(base_config: Dict[str, Any], 
                 override_configs: List[Dict[str, Any]],
                 environment: Optional[str] = None,
                 strategy: Optional[str] = None) -> MergeResult:
    """Merge configuration dictionaries."""
    return _config_merger.merge_configs(
        base_config, override_configs, environment, strategy
    )


def merge_with_defaults(config: Dict[str, Any], 
                     defaults: Dict[str, Any],
                     environment: Optional[str] = None) -> Dict[str, Any]:
    """Merge configuration with defaults."""
    return _config_merger.merge_with_defaults(config, defaults, environment)


def merge_environment_configs(base_config: Dict[str, Any], 
                                 environment_overrides: Dict[str, Dict[str, Any]],
                                 target_environment: Optional[str] = None) -> Dict[str, Any]:
    """Merge environment-specific configurations."""
    return _config_merger.merge_environment_configs(
        base_config, environment_overrides, target_environment
    )


def create_field_merger(field_name: str, 
                   merge_strategy: Optional[str] = None,
                   condition: Optional[Callable[[Any, Any], bool]] = None) -> Callable:
    """Create a field-specific merger."""
    return _config_merger.create_field_merger(field_name, merge_strategy, condition)


def create_list_merger(field_name: str, 
                     merge_strategy: Optional[str] = None,
                     unique: bool = False) -> Callable:
    """Create a list field merger."""
    return _config_merger.create_list_merger(field_name, merge_strategy, unique)


def create_dict_merger(merge_strategy: Optional[str] = None) -> Callable:
    """Create a dictionary merger."""
    return _config_merger.create_dict_merger(merge_strategy)


def get_merge_summary(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get summary of configuration structure."""
    return _config_merger.get_merge_summary(config)


def get_performance_stats() -> Dict[str, Any]:
    """Get merge performance statistics."""
    return _config_merger.get_performance_stats()


def export_merge_rules() -> Dict[str, Any]:
    """Export merge rules."""
    return _config_merger.export_merge_rules()


def import_merge_rules(rules: Dict[str, Any]) -> None:
    """Import merge rules."""
    _config_merger.import_merge_rules(rules)
